"""Tests for SLURM submission and monitoring."""

from typing import List

import pytest

from tests.complete_run import slurm
from tests.complete_run.commands import CommandError


def test_submit_returns_the_job_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(slurm, "run_command", lambda args, **kwargs: "123456")
    assert slurm.submit("/tmp/job.sbatch") == "123456"


def test_submit_strips_the_cluster_suffix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(slurm, "run_command", lambda args, **kwargs: "123456;chrysalis")
    assert slurm.submit("/tmp/job.sbatch") == "123456"


def test_submit_raises_when_no_job_id_comes_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(slurm, "run_command", lambda args, **kwargs: "")
    with pytest.raises(CommandError, match="no job ID"):
        slurm.submit("/tmp/job.sbatch")


@pytest.mark.parametrize(
    ("state", "terminal"),
    [
        ("COMPLETED", True),
        ("FAILED", True),
        ("CANCELLED by 1234", True),
        ("TIMEOUT", True),
        ("OUT_OF_MEMORY", True),
        ("NODE_FAIL", True),
        ("PREEMPTED", True),
        ("BOOT_FAIL", True),
        ("DEADLINE", True),
        ("SPECIAL_EXIT", True),
        ("RUNNING", False),
        ("PENDING", False),
        ("COMPLETING", False),
    ],
)
def test_terminal_state_classification(state: str, terminal: bool) -> None:
    assert slurm.is_terminal_state(state) is terminal


@pytest.mark.parametrize(
    ("state", "exit_code", "passed"),
    [
        ("COMPLETED", "0:0", True),
        ("COMPLETED", "1:0", False),
        ("FAILED", "1:0", False),
        ("TIMEOUT", "N/A", False),
    ],
)
def test_job_outcome_passed(state: str, exit_code: str, passed: bool) -> None:
    assert slurm.JobOutcome("1", state, exit_code).passed is passed


def test_job_status_matches_the_requested_job(monkeypatch: pytest.MonkeyPatch) -> None:
    # sacct can return sibling rows; only the exact job ID counts.
    output = "999|RUNNING|0:0\n123|COMPLETED|0:0\n"
    monkeypatch.setattr(slurm, "run_command", lambda args, **kwargs: output)
    assert slurm.job_status("123") == ("COMPLETED", "0:0")


def test_job_status_is_none_before_accounting_catches_up(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(slurm, "run_command", lambda args, **kwargs: "")
    assert slurm.job_status("123") is None


def test_wait_for_job_returns_the_terminal_outcome(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = iter(["RUNNING", "", ""])
    monkeypatch.setattr(
        slurm, "run_command", lambda args, **kwargs: next(responses, "")
    )
    monkeypatch.setattr(slurm, "job_status", lambda job_id: ("COMPLETED", "0:0"))

    outcome = slurm.wait_for_job(
        "123", check_interval=1, max_wait=10, sleep=lambda _: None
    )
    assert outcome.state == "COMPLETED"
    assert outcome.passed


def test_wait_for_job_times_out_without_cancelling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(slurm, "run_command", lambda args, **kwargs: "RUNNING")
    outcome = slurm.wait_for_job(
        "123", check_interval=1, max_wait=3, sleep=lambda _: None
    )
    assert outcome.state == "TIMEOUT"


def test_wait_for_user_jobs_returns_drained(monkeypatch: pytest.MonkeyPatch) -> None:
    counts = iter([5, 2, 0])
    monkeypatch.setattr(slurm, "queued_job_count", lambda user: next(counts))
    monkeypatch.setattr(slurm, "queued_reasons", lambda user: ["Priority"])

    assert (
        slurm.wait_for_user_jobs(
            "me", check_interval=1, max_wait=10, sleep=lambda _: None
        )
        == "drained"
    )


def test_wait_for_user_jobs_cancels_permanently_blocked_jobs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cancelled: List[str] = []
    monkeypatch.setattr(slurm, "queued_job_count", lambda user: 3)
    monkeypatch.setattr(
        slurm,
        "queued_reasons",
        lambda user: [slurm.DEPENDENCY_NEVER_SATISFIED] * 3,
    )
    monkeypatch.setattr(slurm, "cancel_all", lambda user: cancelled.append(user))

    outcome = slurm.wait_for_user_jobs(
        "me", check_interval=1, max_wait=10, sleep=lambda _: None
    )
    assert outcome == "dependency_never_satisfied"
    assert cancelled == ["me"]


def test_wait_for_user_jobs_keeps_waiting_when_only_some_are_blocked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    counts = iter([3, 0])
    monkeypatch.setattr(slurm, "queued_job_count", lambda user: next(counts))
    monkeypatch.setattr(
        slurm,
        "queued_reasons",
        lambda user: [slurm.DEPENDENCY_NEVER_SATISFIED, "Priority"],
    )
    monkeypatch.setattr(
        slurm, "cancel_all", lambda user: pytest.fail("should not cancel")
    )

    assert (
        slurm.wait_for_user_jobs(
            "me", check_interval=1, max_wait=10, sleep=lambda _: None
        )
        == "drained"
    )


def test_wait_for_user_jobs_times_out(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(slurm, "queued_job_count", lambda user: 4)
    monkeypatch.setattr(slurm, "queued_reasons", lambda user: ["Priority"])
    assert (
        slurm.wait_for_user_jobs(
            "me", check_interval=1, max_wait=2, sleep=lambda _: None
        )
        == "timed_out"
    )


def test_batch_script_initializes_conda_before_activating() -> None:
    script = slurm.build_batch_script(
        job_name="zppy_image_checker_x",
        output_prefix="/results/image_checker_x",
        directives=("#SBATCH --partition=debug", "#SBATCH --account=e3sm"),
        conda_activation_cmd="lcrc_conda",
        env_name="test-zppy-main-x",
        workdir="/worktree/zppy",
        body="python -m pytest tests/integration/test_images.py",
    )

    # A batch shell is not a login shell, so activation must come first.
    assert script.index("lcrc_conda") < script.index("conda activate test-zppy-main-x")
    # Running from elsewhere would silently test the installed zppy instead.
    assert "cd /worktree/zppy" in script
    assert "#SBATCH --partition=debug" in script
    assert "#SBATCH --job-name=zppy_image_checker_x" in script
