"""SLURM submission and monitoring for the complete run test."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Sequence, Set

from tests.complete_run.commands import CommandError, run_command

logger: logging.Logger = logging.getLogger(__name__)

# States from which a job will never leave on its own.
TERMINAL_STATE_PREFIXES: tuple[str, ...] = (
    "COMPLETED",
    "FAILED",
    "CANCELLED",
    "TIMEOUT",
    "OUT_OF_MEMORY",
    "NODE_FAIL",
    "PREEMPTED",
    "BOOT_FAIL",
    "DEADLINE",
    "SPECIAL_EXIT",
)

# A job whose dependency can never be satisfied will sit in the queue forever.
DEPENDENCY_NEVER_SATISFIED: str = "DependencyNeverSatisfied"


def job_passed(state: str, exit_code: str) -> bool:
    """Whether a job completed and its script exited zero."""
    return state.startswith("COMPLETED") and exit_code.split(":")[0] == "0"


@dataclass
class JobOutcome:
    """The terminal result of one monitored job."""

    job_id: str
    state: str
    exit_code: str

    @property
    def passed(self) -> bool:
        return job_passed(self.state, self.exit_code)


def is_terminal_state(state: str) -> bool:
    """Whether a SLURM state means the job has finished for good."""
    return state.startswith(TERMINAL_STATE_PREFIXES)


def submit(script_path: str) -> str:
    """Submit a batch script and return its job ID.

    Raises
    ------
    CommandError
        If sbatch fails, or returns no job ID.
    """
    job_id: str = run_command(["sbatch", "--parsable", script_path])
    # `--parsable` returns "<jobid>" or "<jobid>;<cluster>".
    job_id = job_id.split(";", 1)[0].strip()
    if not job_id:
        raise CommandError(["sbatch", script_path], 1, "sbatch returned no job ID.")
    logger.info("Submitted job %s from %s", job_id, script_path)
    return job_id


def job_status(job_id: str) -> tuple[str, str] | None:
    """Return one job's ``(state, exit_code)`` from the accounting database.

    Returns None while accounting data has not caught up, which happens for a
    short window after a job leaves the queue.
    """
    output: str = run_command(
        [
            "sacct",
            "-X",
            "--parsable2",
            "--noheader",
            "-j",
            job_id,
            "--format=JobIDRaw,State,ExitCode",
        ],
        check=False,
    )
    for line in output.splitlines():
        fields: List[str] = line.split("|")
        if len(fields) >= 3 and fields[0] == job_id:
            return fields[1], fields[2]
    return None


def queued_job_count(user: str) -> int:
    """Return how many jobs the user currently has in the queue."""
    output: str = run_command(["squeue", "-h", "-u", user], check=False)
    return len([line for line in output.splitlines() if line.strip()])


def queued_job_ids(user: str) -> Set[str]:
    """Return the IDs of the jobs the user currently has in the queue."""
    output: str = run_command(["squeue", "-h", "-u", user, "-o", "%i"], check=False)
    return {line.strip() for line in output.splitlines() if line.strip()}


def queued_reasons(user: str) -> List[str]:
    """Return the pending reason for each of the user's queued jobs."""
    output: str = run_command(["squeue", "-h", "-u", user, "-o", "%r"], check=False)
    return [line.strip() for line in output.splitlines() if line.strip()]


def queued_jobs(user: str) -> Dict[str, str]:
    """Return each queued job ID and its pending reason."""
    output: str = run_command(["squeue", "-h", "-u", user, "-o", "%i|%r"], check=False)
    jobs: Dict[str, str] = {}
    for line in output.splitlines():
        job_id, separator, reason = line.partition("|")
        if separator and job_id.strip():
            jobs[job_id.strip()] = reason.strip()
    return jobs


def cancel_job(job_id: str) -> None:
    """Cancel one job without affecting other jobs owned by the user."""
    try:
        run_command(["scancel", job_id])
    except CommandError as error:
        logger.warning("Could not cancel job %s: %s", job_id, error)


def cancel_all(user: str) -> None:
    """Cancel every job belonging to the user."""
    try:
        run_command(["scancel", "-u", user])
    except CommandError as error:
        logger.warning("Could not cancel jobs for %s: %s", user, error)


def wait_for_job(
    job_id: str,
    *,
    check_interval: int = 120,
    max_wait: int = 7200,
    sleep: Callable[[float], None] = time.sleep,
) -> JobOutcome:
    """Wait for one job to reach a terminal state.

    A job that outlives ``max_wait`` is reported as ``TIMEOUT`` without being
    cancelled; the run may still be salvageable and the job's own artifacts are
    left for review.
    """
    elapsed: int = 0
    while elapsed < max_wait:
        queue_state: str = run_command(
            ["squeue", "-h", "-j", job_id, "-o", "%T"], check=False
        )
        if queue_state:
            logger.info(
                "Job %s state: %s (elapsed %ss / max %ss)",
                job_id,
                queue_state.splitlines()[0],
                elapsed,
                max_wait,
            )
        else:
            status = job_status(job_id)
            if status is not None:
                state, exit_code = status
                if is_terminal_state(state):
                    logger.info(
                        "Job %s finished: %s (ExitCode %s)", job_id, state, exit_code
                    )
                    return JobOutcome(job_id=job_id, state=state, exit_code=exit_code)
            else:
                logger.info("Job %s left the queue; awaiting accounting data", job_id)

        sleep(check_interval)
        elapsed += check_interval

    logger.error("Timed out waiting for job %s", job_id)
    return JobOutcome(job_id=job_id, state="TIMEOUT", exit_code="N/A")


def wait_for_user_jobs(
    user: str,
    *,
    job_ids: Set[str],
    check_interval: int = 600,
    max_wait: int = 14400,
    sleep: Callable[[float], None] = time.sleep,
) -> str:
    """Wait for this run's jobs to leave the queue.

    zppy submits a dependency graph rather than one job, so the run waits on the
    queue draining rather than on individual IDs. Jobs with permanently
    unsatisfiable dependencies are cancelled individually; downstream jobs can
    then acquire the same reason on a later poll.

    Returns
    -------
    str
        ``"drained"`` when the queue empties, ``"dependency_never_satisfied"``
        when any job was cancelled for an unsatisfiable dependency, or
        ``"timed_out"``.
    """
    elapsed: int = 0
    cancelled_dependency_job: bool = False
    while elapsed < max_wait:
        queued: Dict[str, str] = queued_jobs(user)
        remaining: Dict[str, str] = {
            job_id: reason for job_id, reason in queued.items() if job_id in job_ids
        }
        if not remaining:
            logger.info("Queue drained after %ss", elapsed)
            return (
                "dependency_never_satisfied" if cancelled_dependency_job else "drained"
            )

        blocked: List[str] = [
            job_id
            for job_id, reason in remaining.items()
            if reason == DEPENDENCY_NEVER_SATISFIED
        ]
        if blocked:
            logger.error(
                "%s run job(s) have unsatisfiable dependencies; cancelling",
                len(blocked),
            )
            for job_id in blocked:
                cancel_job(job_id)
            cancelled_dependency_job = True

        logger.info(
            "Run jobs remaining: %s (elapsed %ss / max %ss)",
            len(remaining),
            elapsed,
            max_wait,
        )
        sleep(check_interval)
        elapsed += check_interval

    logger.error("Timed out waiting for jobs to finish")
    return "timed_out"


def build_batch_script(
    job_name: str,
    output_prefix: str,
    directives: Sequence[str],
    conda_profile: str,
    env_name: str,
    workdir: str,
    body: str,
) -> str:
    """Build a batch script that activates an environment and runs ``body``.

    A batch shell is not a login shell, so conda has to be initialized from its
    profile script before ``conda activate`` works. Nothing is taken from the
    submitter's own shell setup (``~/.bashrc``, aliases), which differs from
    person to person. ``set +u`` brackets it because conda's own initialization
    references unset variables.
    """
    directive_block: str = "\n".join(directives)
    return f"""#!/bin/bash
#SBATCH --job-name={job_name}
#SBATCH --nodes=1
#SBATCH --output={output_prefix}.o%j
#SBATCH --error={output_prefix}.e%j
{directive_block}

set -e
set +u
source {conda_profile}
conda activate {env_name}
set -u
cd {workdir}
{body}
"""
