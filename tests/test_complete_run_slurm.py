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
    queued = iter([{"123": "Priority"}, {"123": "None"}, {}])
    monkeypatch.setattr(slurm, "queued_jobs", lambda user: next(queued, {}))

    assert (
        slurm.wait_for_user_jobs(
            "me", job_ids={"123"}, check_interval=1, max_wait=10, sleep=lambda _: None
        )
        == "drained"
    )


def test_wait_for_user_jobs_cancels_directly_blocked_run_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queued = iter(
        [
            {"111": slurm.DEPENDENCY_NEVER_SATISFIED, "999": "Priority"},
            {"999": "Priority"},
            {},
        ]
    )
    cancelled: List[str] = []
    monkeypatch.setattr(slurm, "queued_jobs", lambda user: next(queued, {}))
    monkeypatch.setattr(slurm, "cancel_job", cancelled.append)

    outcome = slurm.wait_for_user_jobs(
        "me", job_ids={"111"}, check_interval=1, max_wait=10, sleep=lambda _: None
    )
    assert outcome == "dependency_never_satisfied"
    assert cancelled == ["111"]


def test_wait_for_user_jobs_cancels_cascading_dependency_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queued = iter(
        [
            {
                "111": slurm.DEPENDENCY_NEVER_SATISFIED,
                "222": "Dependency",
                "333": "Priority",
            },
            {"222": slurm.DEPENDENCY_NEVER_SATISFIED, "333": "Priority"},
            {"333": "Priority"},
            {},
        ]
    )
    cancelled: List[str] = []
    monkeypatch.setattr(slurm, "queued_jobs", lambda user: next(queued, {}))
    monkeypatch.setattr(slurm, "cancel_job", cancelled.append)

    assert slurm.wait_for_user_jobs(
        "me",
        job_ids={"111", "222", "333"},
        check_interval=1,
        max_wait=10,
        sleep=lambda _: None,
    ) == "dependency_never_satisfied"
    assert cancelled == ["111", "222"]


def test_wait_for_user_jobs_preserves_healthy_and_unrelated_jobs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queued = iter(
        [
            {
                "111": "Priority",
                "222": "Dependency",
                "999": slurm.DEPENDENCY_NEVER_SATISFIED,
            },
            {
                "111": "Priority",
                "222": "None",
                "999": slurm.DEPENDENCY_NEVER_SATISFIED,
            },
            {},
        ]
    )
    monkeypatch.setattr(slurm, "queued_jobs", lambda user: next(queued, {}))
    monkeypatch.setattr(
        slurm, "cancel_job", lambda job_id: pytest.fail("should not cancel")
    )

    assert slurm.wait_for_user_jobs(
        "me",
        job_ids={"111", "222"},
        check_interval=1,
        max_wait=10,
        sleep=lambda _: None,
    ) == "drained"


def test_wait_for_user_jobs_times_out(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(slurm, "queued_jobs", lambda user: {"123": "Priority"})
    assert (
        slurm.wait_for_user_jobs(
            "me", job_ids={"123"}, check_interval=1, max_wait=2, sleep=lambda _: None
        )
        == "timed_out"
    )


def test_batch_script_initializes_conda_before_activating() -> None:
    script = slurm.build_batch_script(
        job_name="zppy_image_checker_x",
        output_prefix="/results/image_checker_x",
        directives=("#SBATCH --partition=debug", "#SBATCH --account=e3sm"),
        conda_profile="/home/me/conda/etc/profile.d/conda.sh",
        env_name="test-zppy-main-x",
        workdir="/worktree/zppy",
        body="python -m pytest tests/integration/test_images.py",
    )

    # A batch shell is not a login shell, so activation must come first.
    assert script.index("source /home/me/conda/etc/profile.d/conda.sh") < script.index(
        "conda activate test-zppy-main-x"
    )
    # Nothing from the submitter's personal shell setup: an alias such as
    # `lcrc_conda` exists only in some people's ~/.bashrc.
    assert "bashrc" not in script
    assert "lcrc_conda" not in script
    # Running from elsewhere would silently test the installed zppy instead.
    assert "cd /worktree/zppy" in script
    assert "#SBATCH --partition=debug" in script
    assert "#SBATCH --job-name=zppy_image_checker_x" in script


def test_queued_job_ids_parses_the_queue(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(slurm, "run_command", lambda args, **kwargs: "111\n222\n333")
    assert slurm.queued_job_ids("me") == {"111", "222", "333"}


def test_queued_job_ids_is_empty_for_a_drained_queue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(slurm, "run_command", lambda args, **kwargs: "\n  \n")
    assert slurm.queued_job_ids("me") == set()


def test_queued_job_ids_asks_only_for_the_users_ids(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: List[List[str]] = []

    def record(args, **kwargs) -> str:
        seen.append(list(args))
        return ""

    monkeypatch.setattr(slurm, "run_command", record)
    slurm.queued_job_ids("me")
    assert seen == [["squeue", "-h", "-u", "me", "-o", "%i"]]


def test_queued_jobs_parses_job_ids_and_reasons(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        slurm,
        "run_command",
        lambda args, **kwargs: "111|DependencyNeverSatisfied\n222|Priority",
    )
    assert slurm.queued_jobs("me") == {
        "111": "DependencyNeverSatisfied",
        "222": "Priority",
    }
