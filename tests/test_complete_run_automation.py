"""Tests for complete run orchestration."""

import argparse
import json
import os
from typing import List, Sequence, Tuple

import pytest

from tests.complete_run import automation
from tests.complete_run import environments as environments_module
from tests.complete_run import provenance, worktrees
from tests.complete_run.environments import Environment
from tests.complete_run.params import REPO_SPECS_BY_NAME, resolve_machine


def _make_run(tmp_path, argv: Sequence[str] = (), status=None) -> automation._Run:
    """Build a run the way the CLI does, rooted in a scratch directory."""
    args = automation._build_parser().parse_args(
        [
            "--machine",
            "chrysalis",
            "--shared-root",
            str(tmp_path / "shared"),
            "--username",
            "me",
            "--tag",
            "tag",
            "--poll-seconds",
            "1",
            *argv,
        ]
    )
    run = automation._start_run(args)
    if status:
        run.status.update(status)
    return run


def _recording(calls: List[List[str]]):
    """Return a stand-in for run_command that records what it was asked to run."""

    def run(args: List[str], **kwargs) -> str:
        calls.append(list(args))
        return ""

    return run


def _zppy_env() -> Environment:
    return Environment("zppy", "dev", "test-zppy-main-tag", "activate")


def test_stages_run_in_order() -> None:
    assert automation._stages_to_run("prepare", None) == list(automation.STAGES)
    assert automation._stages_to_run("validate", None) == ["validate", "report"]
    assert automation._stages_to_run("prepare", "generate") == ["prepare", "generate"]


def test_stop_before_start_is_rejected() -> None:
    with pytest.raises(ValueError, match="comes before"):
        automation._stages_to_run("validate", "prepare")


def test_cli_rejects_a_backwards_stage_range(tmp_path) -> None:
    with pytest.raises(SystemExit):
        automation.main(
            [
                "--machine",
                "chrysalis",
                "--shared-root",
                str(tmp_path),
                "--start-stage",
                "validate",
                "--stop-after",
                "prepare",
            ]
        )


def test_default_tag_includes_the_run_number() -> None:
    tag = automation._default_tag(3)
    assert tag.endswith("_run3")
    assert len(tag.split("_")[0]) == 8


def test_repo_path_uses_the_real_directory_names() -> None:
    args = argparse.Namespace(repo_root="/home/me/ez", repo_paths={})
    # The config keys are not the directory names on disk.
    assert (
        automation._repo_path(args, REPO_SPECS_BY_NAME["mpas_analysis"])
        == "/home/me/ez/MPAS-Analysis"
    )
    assert (
        automation._repo_path(args, REPO_SPECS_BY_NAME["zppy_interfaces"])
        == "/home/me/ez/zppy-interfaces"
    )
    assert automation._repo_path(args, REPO_SPECS_BY_NAME["zppy"]) == "/home/me/ez/zppy"


def test_repo_path_override_wins() -> None:
    args = argparse.Namespace(
        repo_root="/home/me/ez", repo_paths={"zppy": "/scratch/zppy-clone"}
    )
    assert (
        automation._repo_path(args, REPO_SPECS_BY_NAME["zppy"]) == "/scratch/zppy-clone"
    )


def test_start_run_uses_the_shared_root_and_records_it(tmp_path) -> None:
    run = _make_run(tmp_path)
    assert run.layout.root == str(tmp_path / "shared" / "runs" / "tag")
    assert run.status["shared_root"] == str(tmp_path / "shared")


def test_intermediate_data_goes_to_scratch(tmp_path) -> None:
    # Worktrees and zppy's post-processing output are large and worthless once
    # the run is validated; only the plots belong under the shared root.
    run = _make_run(tmp_path)
    scratch = "/lcrc/globalscratch/me/zppy_complete_run/tag"
    assert run.worktree_root == f"{scratch}/worktrees"
    assert run.layout.output == f"{scratch}/output"
    assert run.layout.www == str(tmp_path / "shared" / "runs" / "tag" / "www")
    assert run.status["output_dir"] == f"{scratch}/output"


def test_scratch_root_can_be_overridden(tmp_path) -> None:
    run = _make_run(tmp_path, ["--scratch-root", str(tmp_path / "scratch")])
    assert run.layout.output == str(tmp_path / "scratch" / "tag" / "output")


def test_a_resumed_run_keeps_its_selections(tmp_path) -> None:
    first = _make_run(tmp_path, ["--cfg", "weekly_bundles", "--task", "e3sm_diags"])
    first.write_status()

    resumed = _make_run(tmp_path, ["--start-stage", "submit"])
    assert resumed.cfgs == ["weekly_bundles"]
    assert resumed.tasks == ["e3sm_diags"]


def test_zppy_worktree_comes_from_the_status_file(tmp_path) -> None:
    run = _make_run(
        tmp_path, status={"repos": {"zppy": {"worktree": "/scratch/wt/zppy"}}}
    )
    assert run.zppy_worktree == "/scratch/wt/zppy"


def test_zppy_worktree_raises_when_prepare_never_ran(tmp_path) -> None:
    run = _make_run(tmp_path)
    with pytest.raises(automation.StageError, match="prepare stage first"):
        run.zppy_worktree


def test_key_value_action_rejects_an_unknown_repository() -> None:
    parser = automation._build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--machine", "chrysalis", "--branch", "not_a_repo=main"])


def test_key_value_action_rejects_a_bad_env_type() -> None:
    parser = automation._build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--machine", "chrysalis", "--env-type", "zppy=frozen"])


def test_key_value_action_collects_repeated_values() -> None:
    parser = automation._build_parser()
    args = parser.parse_args(
        [
            "--machine",
            "chrysalis",
            "--branch",
            "zppy=main",
            "--branch",
            "e3sm_diags=my-feature",
        ]
    )
    assert args.branches == {"zppy": "main", "e3sm_diags": "my-feature"}


def test_machine_lookup_rejects_an_unknown_machine() -> None:
    with pytest.raises(ValueError, match="Unknown machine"):
        resolve_machine("summit")


def test_perlmutter_cfgs_are_suffixed_pm_cpu() -> None:
    # The machine is called perlmutter but its generated cfgs say pm-cpu.
    assert resolve_machine("perlmutter").cfg_suffix == "pm-cpu"
    assert resolve_machine("chrysalis").cfg_suffix == "chrysalis"


@pytest.mark.parametrize(
    "outcome, stage",
    [
        ("dependency_never_satisfied", "dependency_never_satisfied"),
        ("timed_out", "timed_out"),
    ],
)
def test_wait_maps_outcomes_to_terminal_stages(
    tmp_path, monkeypatch: pytest.MonkeyPatch, outcome: str, stage: str
) -> None:
    monkeypatch.setattr(automation, "wait_for_user_jobs", lambda *a, **k: outcome)
    with pytest.raises(automation.StageError) as error:
        automation._wait(_make_run(tmp_path), 10)
    assert error.value.stage == stage


def test_wait_returns_quietly_when_the_queue_drains(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(automation, "wait_for_user_jobs", lambda *a, **k: "drained")
    automation._wait(_make_run(tmp_path), 10)


def test_submit_stage_names_the_missing_cfg(tmp_path) -> None:
    worktree = tmp_path / "wt" / "zppy"
    worktree.mkdir(parents=True)
    run = _make_run(
        tmp_path,
        ["--cfg", "weekly_comprehensive_v3"],
        status={"repos": {"zppy": {"worktree": str(worktree)}}},
    )
    run.environments["zppy"] = _zppy_env()

    with pytest.raises(automation.StageError) as error:
        automation._stage_submit(run)
    assert error.value.stage == "submission_failed"
    assert "test_weekly_comprehensive_v3_chrysalis.cfg" in str(error.value)


def _worktree_with_cfgs(tmp_path, cfgs: List[str]) -> str:
    worktree = tmp_path / "wt" / "zppy"
    generated = worktree / "tests" / "integration" / "generated"
    generated.mkdir(parents=True)
    for cfg in cfgs:
        (generated / f"test_{cfg}_chrysalis.cfg").write_text("")
    return str(worktree)


def test_submission_uses_the_zppy_under_test(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A bare `zppy` would be the controller's, not the revision being tested.
    worktree = _worktree_with_cfgs(tmp_path, ["weekly_bundles"])
    run = _make_run(
        tmp_path,
        ["--cfg", "weekly_bundles"],
        status={"repos": {"zppy": {"worktree": worktree}}},
    )
    run.environments["zppy"] = _zppy_env()
    submitted: List[List[str]] = []
    monkeypatch.setattr(automation, "run_command", _recording(submitted))
    monkeypatch.setattr(automation, "wait_for_user_jobs", lambda *a, **k: "drained")

    automation._stage_submit(run)

    assert submitted[0][:5] == [
        "conda",
        "run",
        "--no-capture-output",
        "-n",
        "test-zppy-main-tag",
    ]
    assert submitted[0][5:7] == ["zppy", "-c"]


def test_bundles_stage_only_resubmits_bundle_cfgs(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfgs = ["weekly_bundles", "weekly_comprehensive_v3", "min_case_bundles"]
    worktree = _worktree_with_cfgs(tmp_path, cfgs)
    run = _make_run(
        tmp_path,
        [arg for cfg in cfgs for arg in ("--cfg", cfg)],
        status={"repos": {"zppy": {"worktree": worktree}}},
    )
    run.environments["zppy"] = _zppy_env()
    submitted: List[List[str]] = []
    monkeypatch.setattr(automation, "run_command", _recording(submitted))
    monkeypatch.setattr(automation, "wait_for_user_jobs", lambda *a, **k: "drained")

    automation._stage_bundles(run)

    resubmitted = [args[-1] for args in submitted]
    assert any("weekly_bundles" in path for path in resubmitted)
    assert any("min_case_bundles" in path for path in resubmitted)
    assert not any("comprehensive_v3" in path for path in resubmitted)


def test_bundles_stage_is_a_no_op_without_bundle_cfgs(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        automation, "run_command", lambda *a, **k: pytest.fail("submitted")
    )
    automation._stage_bundles(_make_run(tmp_path, ["--cfg", "weekly_comprehensive_v3"]))


def test_stopping_early_does_not_report_passed(tmp_path) -> None:
    # A run that only prepared has validated nothing; calling it "passed" would
    # be a false all-clear.
    run = _make_run(tmp_path, status={"stage": "prepare"})
    automation._stage_report(run, stages_run=["prepare"])
    assert run.status["stage"] == "prepare"


def test_a_validated_run_reports_passed(tmp_path) -> None:
    run = _make_run(tmp_path, status={"stage": "validate"})
    automation._stage_report(run, stages_run=["validate", "report"])
    assert run.status["stage"] == "passed"


def test_a_failed_stage_is_never_overwritten_with_passed(tmp_path) -> None:
    for stage in automation.FAILURE_STAGES:
        run = _make_run(tmp_path, status={"stage": stage})
        automation._stage_report(run, stages_run=list(automation.STAGES))
        assert run.status["stage"] == stage


def test_zppy_cannot_run_from_unified(tmp_path) -> None:
    # The run installs the revision under test and runs pytest from its
    # worktree, so zppy itself always needs a dev build.
    run = _make_run(tmp_path, ["--env-type", "zppy=unified", "--skip-unit-tests"])
    with pytest.raises(automation.StageError, match="cannot run from E3SM-Unified"):
        automation._stage_prepare(run)


def test_baseline_env_requires_a_promoted_baseline(tmp_path) -> None:
    # Reproducing a baseline's dependencies is meaningless with no baseline.
    run = _make_run(tmp_path, ["--env-type", "e3sm_diags=baseline"])
    with pytest.raises(automation.StageError, match="No baseline is promoted"):
        automation._stage_prepare(run)


def test_env_type_accepts_baseline() -> None:
    parser = automation._build_parser()
    args = parser.parse_args(
        ["--machine", "chrysalis", "--env-type", "e3sm_diags=baseline"]
    )
    assert args.env_types == {"e3sm_diags": "baseline"}


# End to end through the real CLI ##############################################
# These go through argv exactly as the controller does. Building a Namespace by
# hand is how a flag the parser never defined went unnoticed.


@pytest.fixture
def fake_prepare(tmp_path, monkeypatch: pytest.MonkeyPatch):
    """Stub out git and conda so prepare runs without touching either."""
    commands: List[List[str]] = []

    def fake_checkout(name, repo, branch, worktree_root):
        path = os.path.join(str(tmp_path / "wt"), name)
        os.makedirs(os.path.join(path, "tests"), exist_ok=True)
        return worktrees.Checkout(
            name=name,
            source_repo=repo,
            path=path,
            sha="a" * 40,
            short_sha="a" * 8,
            branch=branch,
            remote="upstream",
        )

    def fake_environment(spec, checkout, tag, conda_profile, **kwargs):
        name = f"test-{spec.name}-{checkout.branch}-{tag}"
        return Environment(spec.name, "dev", name, f"conda activate {name}")

    def fake_command(args, **kwargs):
        commands.append(list(args))
        return ""

    def fake_command_status(args, **kwargs) -> Tuple[int, str]:
        commands.append(list(args))
        return 0, ""

    monkeypatch.setattr(automation, "create_checkout", fake_checkout)
    monkeypatch.setattr(automation, "create_environment", fake_environment)
    monkeypatch.setattr(automation, "run_command", fake_command)
    monkeypatch.setattr(automation, "run_command_status", fake_command_status)
    monkeypatch.setattr(provenance, "run_command", fake_command)
    monkeypatch.setattr(environments_module, "run_command", fake_command)
    return commands


def _cli(tmp_path, *extra: str) -> int:
    return automation.main(
        [
            "--machine",
            "chrysalis",
            "--shared-root",
            str(tmp_path / "shared"),
            "--scratch-root",
            str(tmp_path / "scratch"),
            "--username",
            "me",
            "--tag",
            "tag",
            *extra,
        ]
    )


def test_cli_runs_prepare_and_leaves_a_report(tmp_path, fake_prepare) -> None:
    assert _cli(tmp_path, "--stop-after", "prepare") == 0

    run_dir = tmp_path / "shared" / "runs" / "tag"
    status = json.loads((run_dir / "status.json").read_text())
    assert status["stage"] == "prepare"
    assert status["repos"]["zppy"]["environment"] == "test-zppy-main-tag"
    assert (run_dir / "complete-run-report.md").is_file()
    assert (run_dir / "manifest.json").is_file()


def test_unit_test_globs_are_expanded(tmp_path, fake_prepare) -> None:
    # No shell runs these commands, so pytest would be handed "tests/test_*.py"
    # literally and find nothing.
    zppy_tests = tmp_path / "wt" / "zppy" / "tests"
    zppy_tests.mkdir(parents=True)
    (zppy_tests / "test_one.py").write_text("")
    (zppy_tests / "test_two.py").write_text("")

    assert _cli(tmp_path, "--stop-after", "prepare") == 0

    pytest_runs = [args for args in fake_prepare if "pytest" in args]
    zppy_run = next(args for args in pytest_runs if "tests/test_one.py" in args)
    assert "tests/test_two.py" in zppy_run
    assert not any("*" in arg for args in pytest_runs for arg in args)
    # And it runs in zppy's own environment.
    assert zppy_run[:5] == [
        "conda",
        "run",
        "--no-capture-output",
        "-n",
        "test-zppy-main-tag",
    ]


def test_a_partial_run_keeps_its_worktrees_to_resume_from(
    tmp_path, fake_prepare, monkeypatch: pytest.MonkeyPatch
) -> None:
    removed: List[object] = []
    monkeypatch.setattr(automation, "remove_checkouts", removed.extend)
    assert _cli(tmp_path, "--stop-after", "prepare", "--skip-unit-tests") == 0
    assert removed == []


def test_resuming_at_generate_uses_the_recorded_environments(
    tmp_path, fake_prepare
) -> None:
    # Resuming without prepare must not silently fall back to E3SM-Unified.
    assert _cli(tmp_path, "--stop-after", "prepare", "--skip-unit-tests") == 0
    fake_prepare.clear()

    assert _cli(tmp_path, "--start-stage", "generate", "--stop-after", "generate") == 0

    generate = next(args for args in fake_prepare if "tests.integration.utils" in args)
    assert generate[4] == "test-zppy-main-tag"
    # zppy's output goes to scratch, not into the shared run directory.
    output_dir = generate[generate.index("--output-dir") + 1]
    assert output_dir == str(tmp_path / "scratch" / "tag" / "output")
    env_cmds = [generate[i + 1] for i, arg in enumerate(generate) if arg == "--env-cmd"]
    diags = next(cmd for cmd in env_cmds if cmd.startswith("e3sm_diags="))
    assert diags.endswith("conda activate test-e3sm_diags-main-tag")


def test_an_unexpected_error_fails_the_stage_it_happened_in(
    tmp_path, fake_prepare, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert _cli(tmp_path, "--stop-after", "prepare", "--skip-unit-tests") == 0

    def boom(args, **kwargs):
        raise automation.CommandError(args, 1, "zppy exploded")

    monkeypatch.setattr(automation, "run_command", boom)
    assert _cli(tmp_path, "--start-stage", "generate", "--stop-after", "generate") == 1

    status = json.loads(
        (tmp_path / "shared" / "runs" / "tag" / "status.json").read_text()
    )
    assert status["stage"] == "submission_failed"
    assert "zppy exploded" in status["error"]
