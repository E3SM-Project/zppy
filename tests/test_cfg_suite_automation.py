"""Tests for cfg suite orchestration."""

import argparse
import json
import os
from pathlib import Path
from typing import List, Sequence, Tuple

import pytest

from tests.cfg_suite import automation
from tests.cfg_suite import environments as environments_module
from tests.cfg_suite import provenance, worktrees
from tests.cfg_suite.environments import Environment
from tests.cfg_suite.params import (
    INTEGRATION_TEST_FILES,
    REPO_SPECS_BY_NAME,
    resolve_machine,
)


def _make_run(
    tmp_path: Path,
    argv: Sequence[str] = (),
    status: dict | None = None,
) -> automation._Run:
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
    run_root = tmp_path / "shared" / "runs" / args.tag
    run_root.mkdir(parents=True, exist_ok=True)
    status_path = run_root / "status.json"
    if not status_path.exists():
        status_path.write_text(json.dumps({"created_at": "2026-09-01T00:00:00+00:00"}))
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


def test_broad_integration_tests_run_only_for_full_task_selection() -> None:
    assert automation.integration_test_files_for_tasks(["e3sm_to_cmip"]) == ()
    assert (
        automation.integration_test_files_for_tasks(automation.TASK_NAMES)
        == INTEGRATION_TEST_FILES
    )


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


def test_default_tag_is_a_timestamp_with_optional_label() -> None:
    import re

    assert re.fullmatch(r"\d{8}_\d{6}", automation._default_tag())
    assert re.fullmatch(r"\d{8}_\d{6}_manual", automation._default_tag("manual"))


def test_new_run_refuses_to_reuse_a_timestamped_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tag = "20261013_120000"
    monkeypatch.setattr(automation, "_default_tag", lambda label="": tag)
    args = automation._build_parser().parse_args(
        ["--machine", "chrysalis", "--shared-root", str(tmp_path)]
    )
    (tmp_path / "runs" / tag).mkdir(parents=True)

    with pytest.raises(ValueError, match="already exists"):
        automation._start_run(args)


def test_new_run_reserves_its_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tag = "20261013_120001"
    monkeypatch.setattr(automation, "_default_tag", lambda label="": tag)
    args = automation._build_parser().parse_args(
        ["--machine", "chrysalis", "--shared-root", str(tmp_path)]
    )

    run = automation._start_run(args)

    assert os.path.isdir(run.layout.root)
    assert run.status["created_at"]


def test_explicit_tag_requires_an_existing_run_to_resume(tmp_path: Path) -> None:
    args = automation._build_parser().parse_args(
        [
            "--machine",
            "chrysalis",
            "--shared-root",
            str(tmp_path),
            "--tag",
            "20261013_120000",
        ]
    )

    with pytest.raises(ValueError, match="only for resuming"):
        automation._start_run(args)


def test_missing_cfg_baselines_are_recorded_as_not_compared(tmp_path) -> None:
    cfg = "weekly_legacy_3.2.0_comprehensive_v3"
    run = _make_run(tmp_path, ["--cfg", cfg, "--task", "global_time_series"])
    baseline_root = tmp_path / "shared"
    previous_run = baseline_root / "runs" / "previous"
    previous_run.mkdir(parents=True)
    with open(previous_run / "manifest.json", "w") as stream:
        json.dump(
            {"tag": "previous", "cfgs": ["weekly_legacy_3.1.0_comprehensive_v3"]},
            stream,
        )
    (baseline_root / "baselines").mkdir()
    (baseline_root / "baselines" / "latest-main").symlink_to("../runs/previous")

    assert automation._record_baseline(run) is not None

    entries = automation._mapping(run.status.get("baseline_by_cfg_task"))
    entry = automation._mapping(entries.get(f"{cfg}:global_time_series"))
    assert entry == {
        "state": "not-compared",
        "reason": "new cfg",
        "tag": "",
        "run_dir": "",
        "generated": "",
        "repos": {},
    }
    assert automation._mapping(run.status.get("baseline"))["tag"] == "previous"


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
    assert resumed.selected_tasks == ["e3sm_diags"]
    assert resumed.tasks == ["climo", "ts", "tc_analysis", "e3sm_diags"]


def test_a_resumed_run_keeps_its_unified_load_script(tmp_path) -> None:
    script = tmp_path / "load_unified.sh"
    script.write_text("#!/bin/bash\n")
    first = _make_run(
        tmp_path, ["--unified-load-script", str(script), "--env-type", "zppy=unified"]
    )
    first.write_status()

    resumed = _make_run(tmp_path)

    assert resumed.args.unified_load_script == str(script)
    assert resumed.machine.unified_env_cmd == f"source {script}"


def test_zppy_worktree_comes_from_the_status_file(tmp_path) -> None:
    run = _make_run(
        tmp_path, status={"repos": {"zppy": {"worktree": "/scratch/wt/zppy"}}}
    )
    assert run.zppy_worktree == "/scratch/wt/zppy"


def test_zppy_worktree_raises_when_prepare_never_ran(tmp_path) -> None:
    run = _make_run(tmp_path)
    with pytest.raises(automation.StageError, match="prepare stage first"):
        run.zppy_worktree


def test_environment_returns_unified_runtime_without_conda_name(tmp_path) -> None:
    run = _make_run(tmp_path)
    run.environments["zppy"] = environments_module.unified_environment(
        "zppy", run.machine
    )

    assert run.environment("zppy").env_type == "unified"


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


def test_wait_tracks_only_job_ids_from_submitted_cfgs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run = _make_run(
        tmp_path,
        [
            "--task",
            "e3sm_to_cmip",
            "--cfg",
            "weekly_comprehensive_v3",
            "--scratch-root",
            str(tmp_path / "scratch"),
        ],
    )
    submitted_status = os.path.join(
        run.layout.status_dir("weekly_comprehensive_v3"), "e3sm_to_cmip_atm.status"
    )
    unrelated_status = os.path.join(
        run.layout.status_dir("weekly_comprehensive_v3"), "e3sm_diags.status"
    )
    other_cfg_status = os.path.join(
        run.layout.status_dir("weekly_bundles"), "e3sm_to_cmip_atm.status"
    )
    os.makedirs(os.path.dirname(submitted_status), exist_ok=True)
    with open(submitted_status, "w") as stream:
        stream.write("WAITING 111\n")
    with open(unrelated_status, "w") as stream:
        stream.write("WAITING 999\n")
    os.makedirs(os.path.dirname(other_cfg_status), exist_ok=True)
    with open(other_cfg_status, "w") as stream:
        stream.write("WAITING 888\n")

    seen: dict[str, object] = {}

    def wait_for_jobs(user: str, **kwargs: object) -> str:
        seen.update(kwargs)
        return "drained"

    monkeypatch.setattr(automation, "wait_for_user_jobs", wait_for_jobs)
    automation._wait(run, 10, ["weekly_comprehensive_v3"])

    assert seen["job_ids"] == {"111"}


def test_bundle_status_is_not_expected_without_a_selected_task(
    tmp_path: Path,
) -> None:
    run = _make_run(
        tmp_path,
        [
            "--task",
            "tc_analysis",
            "--cfg",
            "weekly_bundles",
            "--scratch-root",
            str(tmp_path / "scratch"),
        ],
    )

    assert automation._tasks_by_cfg(run) == {"weekly_bundles": set()}


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


def test_report_refreshes_package_snapshot_and_environment_export(
    tmp_path, monkeypatch
) -> None:
    run = _make_run(tmp_path)
    run.tasks = ["e3sm_to_cmip"]
    run.environments = {
        "e3sm_to_cmip": Environment(
            "e3sm_to_cmip", "dev", "test-e3sm_to_cmip", "activate"
        )
    }
    run.status["environment_snapshots_prepare"] = {
        "e3sm_to_cmip": {"numpy": "2.1.0 py313_0 conda-forge"}
    }
    description = Path(run.layout.env_descriptions) / "e3sm_to_cmip.txt"
    description.parent.mkdir(parents=True, exist_ok=True)
    description.write_text(
        "Task: e3sm_to_cmip\nGenerated: 2026-10-01 12:00:00\n\n"
        "Package versions:\n-----------------\n"
        "# Name Version Build Channel\n"
        "numpy 2.1.0 py313_0 conda-forge\n",
        encoding="utf-8",
    )
    package_list = (
        "# Name Version Build Channel\n"
        "numpy 2.2.0 py313_0 conda-forge\n"
        "métrique 1.0.0 build-é dépôt\n"
    )
    exports: List[Tuple[str, str]] = []

    def record_export(environment: Environment, path: str) -> str:
        exports.append((environment.repo_name, path))
        return path

    monkeypatch.setattr(
        automation.provenance,
        "conda_package_list",
        lambda environment: package_list,
    )
    monkeypatch.setattr(
        automation.provenance,
        "export_environment_file",
        record_export,
    )

    automation._refresh_environment_snapshots(run)

    snapshots = automation._mapping(run.status.get("environment_snapshots_final"))
    e3sm_snapshot = automation._mapping(snapshots.get("e3sm_to_cmip"))
    assert e3sm_snapshot["numpy"] == (
        "2.2.0 py313_0 conda-forge"
    )
    drift = automation._mapping(run.status.get("environment_drift"))
    assert automation._string_list(drift.get("changed_environments")) == [
        "e3sm_to_cmip"
    ]
    assert exports == [("e3sm_to_cmip", run.layout.environment_file("e3sm_to_cmip"))]
    refreshed = description.read_text(encoding="utf-8")
    assert "Generated: 2026-10-01 12:00:00" in refreshed
    assert "métrique 1.0.0 build-é dépôt" in refreshed
    report = automation.report_module.render_report(run.status, run.layout)
    markdown = automation.report_module.render_markdown(report)
    assert "métrique" in markdown
    assert "2.2.0 py313_0 conda-forge" in markdown


def test_unified_e3sm_to_cmip_environment_is_compared(tmp_path) -> None:
    run = _make_run(tmp_path)
    run.environments = {
        "e3sm_to_cmip": Environment("e3sm_to_cmip", "unified", "", "source unified.sh")
    }
    cfg = run.cfgs[0]
    baseline_dir = tmp_path / "baseline"
    baseline = automation.RunLayout(str(baseline_dir))
    Path(baseline.env_descriptions).mkdir(parents=True)
    Path(baseline.env_descriptions, "e3sm_to_cmip.txt").write_text(
        "Task: e3sm_to_cmip\nPackage versions:\n-----------------\n"
        "# Name Version Build Channel\nnumpy 2.1.0 py313_0 conda-forge\n",
        encoding="utf-8",
    )
    Path(run.layout.environments).mkdir(parents=True)
    Path(run.layout.environment_file("e3sm_to_cmip")).write_text(
        "name: env\ndependencies:\n  - numpy=2.2.0=py313_0\n",
        encoding="utf-8",
    )
    run.status["baseline_by_cfg_task"] = {
        f"{cfg}:e3sm_to_cmip": {"run_dir": str(baseline_dir), "tag": "baseline"}
    }

    diffs, _ = automation._compare_environments(run)

    assert len(diffs) == 1
    assert diffs[0].repo == "e3sm_to_cmip"
    assert diffs[0].differs


def test_a_validated_run_reports_passed(tmp_path) -> None:
    run = _make_run(tmp_path, status={"stage": "validate"})
    automation._stage_report(run, stages_run=["validate", "report"])
    assert run.status["stage"] == "passed"


def test_a_failed_stage_is_never_overwritten_with_passed(tmp_path) -> None:
    for stage in automation.FAILURE_STAGES:
        run = _make_run(tmp_path, status={"stage": stage})
        automation._stage_report(run, stages_run=list(automation.STAGES))
        assert run.status["stage"] == stage


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
        for test_file in (
            *automation.ZPPY_UNIT_TESTS,
            *(
                test
                for tests in automation.ZPPY_TASK_UNIT_TESTS.values()
                for test in tests
            ),
            *automation.IMAGE_HELPER_TEST_FILES,
        ):
            target = Path(path, test_file)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.touch()
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
        if "import json" in " ".join(args):
            return 0, json.dumps(
                {
                    "executable": "/unified/bin/zppy",
                    "version": "3.3.0",
                    "path": "/unified/lib/python3.13/site-packages/zppy/__init__.py",
                    "python": "/unified/bin/python",
                }
            )
        return 0, ""

    monkeypatch.setattr(automation, "create_checkout", fake_checkout)
    monkeypatch.setattr(automation, "create_environment", fake_environment)
    monkeypatch.setattr(automation, "run_command", fake_command)
    monkeypatch.setattr(automation, "run_command_status", fake_command_status)
    monkeypatch.setattr(provenance, "run_command", fake_command)
    monkeypatch.setattr(environments_module, "run_command", fake_command)
    return commands


def _cli(tmp_path: Path, *extra: str) -> int:
    run_dir = tmp_path / "shared" / "runs" / "tag"
    run_dir.mkdir(parents=True, exist_ok=True)
    status_path = run_dir / "status.json"
    if not status_path.exists():
        status_path.write_text("{}")
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
    assert (run_dir / "cfg-suite-report.md").is_file()
    assert (run_dir / "manifest.json").is_file()
    assert status["configuration"]["machine"] == "chrysalis"
    manifest = json.loads((run_dir / "manifest.json").read_text())
    assert manifest["username"] == "me"
    assert manifest["created_at"] == status["created_at"]


def test_configuration_file_values_and_cli_overrides_are_recorded(
    tmp_path, fake_prepare
) -> None:
    config = tmp_path / "run.cfg"
    config.write_text(
        "[cfg_suite]\n"
        "machine = chrysalis\n"
        "account = config-account\n"
        "cfg = weekly_bundles\n"
        "task = e3sm_diags\n"
    )

    assert (
        _cli(
            tmp_path,
            "--config",
            str(config),
            "--cfg",
            "weekly_comprehensive_v3",
            "--stop-after",
            "prepare",
            "--skip-unit-tests",
        )
        == 0
    )
    status = json.loads(
        (tmp_path / "shared" / "runs" / "tag" / "status.json").read_text()
    )
    assert status["configuration"]["account"] == "config-account"
    assert status["cfgs"] == ["weekly_comprehensive_v3"]
    assert status["selected_tasks"] == ["e3sm_diags"]
    assert status["tasks"] == ["climo", "ts", "tc_analysis", "e3sm_diags"]


def test_config_supports_a_run_label(tmp_path: Path) -> None:
    config = tmp_path / "label.cfg"
    config.write_text("[cfg_suite]\nlabel = weekly\n")

    values = automation._read_config(str(config))

    assert values["label"] == "weekly"


def test_cli_can_override_true_config_boolean(tmp_path) -> None:
    config = tmp_path / "run.cfg"
    config.write_text(
        "[cfg_suite]\n" "machine = chrysalis\n" "skip_unit_tests = true\n"
    )

    args = automation._build_parser(automation._read_config(str(config))).parse_args(
        ["--config", str(config), "--no-skip-unit-tests"]
    )

    assert args.skip_unit_tests is False


def test_configuration_rejects_unknown_keys_by_name(tmp_path, capsys) -> None:
    config = tmp_path / "invalid.cfg"
    config.write_text("[cfg_suite]\nmystery_option = true\n")

    with pytest.raises(SystemExit):
        automation.main(["--config", str(config)])
    assert "Unknown configuration key: mystery_option" in capsys.readouterr().err


def test_unified_load_script_must_exist_at_startup(tmp_path) -> None:
    with pytest.raises(SystemExit):
        automation.main(
            [
                "--machine",
                "chrysalis",
                "--unified-load-script",
                str(tmp_path / "missing.sh"),
            ]
        )


def test_dependency_pins_are_recorded_and_applied_to_mutable_environments(
    tmp_path, fake_prepare
) -> None:
    assert (
        _cli(
            tmp_path,
            "--pin",
            "nco<5.4.0",
            "--pin",
            "e3sm_diags:xarray==2025.1.0",
            "--stop-after",
            "prepare",
            "--skip-unit-tests",
        )
        == 0
    )

    status = json.loads(
        (tmp_path / "shared" / "runs" / "tag" / "status.json").read_text()
    )
    assert status["pin_dependencies"] == [
        "nco<5.4.0",
        "e3sm_diags:xarray==2025.1.0",
    ]
    assert status["applied_pins"]["e3sm_diags"] == [
        "nco<5.4.0",
        "xarray==2025.1.0",
    ]
    install_commands = [
        args for args in fake_prepare if "install" in args and "conda" in args
    ]
    assert install_commands
    assert all("--yes" in args for args in install_commands)
    manifest = json.loads(
        (tmp_path / "shared" / "runs" / "tag" / "manifest.json").read_text()
    )
    assert manifest["requested_pins"] == status["pin_dependencies"]
    assert manifest["pins"] == status["applied_pins"]


def test_dependency_pin_failure_fails_prepare_clearly(
    tmp_path, fake_prepare, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_pin(args, **kwargs):
        if "install" in args:
            raise automation.CommandError(args, 1, "solver failed")
        return ""

    monkeypatch.setattr(environments_module, "run_command", fail_pin)
    assert (
        _cli(
            tmp_path,
            "--pin",
            "nco<5.4.0",
            "--stop-after",
            "prepare",
            "--skip-unit-tests",
        )
        == 1
    )
    status = json.loads(
        (tmp_path / "shared" / "runs" / "tag" / "status.json").read_text()
    )
    assert status["stage"] == "prepare_failed"
    assert "Could not apply dependency pins to e3sm_diags" in status["error"]


def test_zppy_can_run_from_unified_using_its_test_worktree(
    tmp_path, fake_prepare
) -> None:
    unified_script = tmp_path / "load_unified.sh"
    unified_script.write_text("#!/bin/bash\n")
    assert (
        _cli(
            tmp_path,
            "--env-type",
            "zppy=unified",
            "--unified-load-script",
            str(unified_script),
            "--pin",
            "zppy:nco<5.4.0",
            "--stop-after",
            "prepare",
        )
        == 0
    )
    status = json.loads(
        (tmp_path / "shared" / "runs" / "tag" / "status.json").read_text()
    )
    assert status["repos"]["zppy"]["environment_type"] == "unified"
    assert status["repos"]["zppy"]["sha"] == "a" * 40
    assert status["zppy_runtime"]["version"] == "3.3.0"
    assert status["unified_load_script"] == str(unified_script)
    assert status["applied_pins"] == {}
    zppy_test = next(
        args for args in fake_prepare if "tests/test_smoke.py" in " ".join(args)
    )
    assert zppy_test[0:2] == ["bash", "-c"]
    assert "source " in zppy_test[2]
    assert "python -m pytest" in zppy_test[2]
    assert not any("pip" in args for args in fake_prepare)
    manifest = json.loads(
        (tmp_path / "shared" / "runs" / "tag" / "manifest.json").read_text()
    )
    assert manifest["unified_load_script"] == str(unified_script)
    assert (
        str(unified_script)
        in (
            tmp_path / "shared" / "runs" / "tag" / "env_descriptions" / "livvkit.txt"
        ).read_text()
    )


def test_unified_zppy_requires_importable_pytest(
    tmp_path, fake_prepare, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        automation,
        "run_command_status",
        lambda args, **kwargs: (1, "No module named pytest"),
    )
    assert (
        _cli(
            tmp_path,
            "--env-type",
            "zppy=unified",
            "--stop-after",
            "prepare",
        )
        == 1
    )
    status = json.loads(
        (tmp_path / "shared" / "runs" / "tag" / "status.json").read_text()
    )
    assert status["stage"] == "prepare_failed"
    assert "must provide importable pytest" in status["error"]


def test_prepare_builds_and_tests_only_task_repositories(
    tmp_path, fake_prepare
) -> None:
    assert _cli(tmp_path, "--task", "e3sm_to_cmip", "--stop-after", "prepare") == 0
    status = json.loads(
        (tmp_path / "shared" / "runs" / "tag" / "status.json").read_text()
    )
    assert set(status["repos"]) == {"zppy", "e3sm_to_cmip"}
    pytest_runs = [args for args in fake_prepare if "pytest" in args]
    zppy_run = next(args for args in pytest_runs if "tests/test_zppy_main.py" in args)
    assert "tests/test_zppy_e3sm_to_cmip.py" in zppy_run
    assert "tests/test_zppy_e3sm_diags.py" not in zppy_run
    assert not any("tests/unit" in arg for args in pytest_runs for arg in args)
    # And it runs in zppy's own environment.
    assert zppy_run[:5] == [
        "conda",
        "run",
        "--no-capture-output",
        "-n",
        "test-zppy-main-tag",
    ]


def test_unit_test_globs_are_expanded(
    tmp_path, fake_prepare, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        automation, "ZPPY_UNIT_TESTS", ("tests/test_one.py", "tests/test_two.py")
    )

    assert _cli(tmp_path, "--stop-after", "prepare") == 0

    pytest_runs = [args for args in fake_prepare if "pytest" in args]
    zppy_run = next(args for args in pytest_runs if "tests/test_one.py" in args)
    assert "tests/test_two.py" in zppy_run
    assert not any("*" in arg for args in pytest_runs for arg in args)


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


def _status_dir(run: automation._Run, cfg: str) -> str:
    """Create and return a cfg's status directory."""
    path = run.layout.status_dir(cfg)
    os.makedirs(path, exist_ok=True)
    return path


def _write_status(run: automation._Run, cfg: str, name: str, contents: str) -> str:
    path = os.path.join(_status_dir(run, cfg), f"{name}.status")
    with open(path, "w") as stream:
        stream.write(contents)
    return path


def test_stale_waiting_status_files_are_cleared_before_resubmitting(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # zppy skips WAITING and RUNNING, so a cancelled run's leftovers would
    # otherwise make a resume skip exactly the tasks that never ran.
    run = _make_run(
        tmp_path,
        [
            "--cfg",
            "weekly_comprehensive_v3",
            "--scratch-root",
            str(tmp_path / "scratch"),
        ],
    )
    waiting = _write_status(run, "weekly_comprehensive_v3", "ts", "WAITING 111")
    running = _write_status(run, "weekly_comprehensive_v3", "climo", "RUNNING 222")
    monkeypatch.setattr(automation, "queued_job_ids", lambda user: set())

    assert automation._clear_stale_status_files(run, run.cfgs) == 2
    assert not os.path.exists(waiting)
    assert not os.path.exists(running)


def test_finished_status_files_survive_a_resume(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # OK means the work is done and ERROR is resubmitted by zppy itself.
    run = _make_run(
        tmp_path,
        [
            "--cfg",
            "weekly_comprehensive_v3",
            "--scratch-root",
            str(tmp_path / "scratch"),
        ],
    )
    done = _write_status(run, "weekly_comprehensive_v3", "ts", "OK")
    failed = _write_status(run, "weekly_comprehensive_v3", "climo", "ERROR (1)")
    monkeypatch.setattr(automation, "queued_job_ids", lambda user: set())

    assert automation._clear_stale_status_files(run, run.cfgs) == 0
    assert os.path.exists(done)
    assert os.path.exists(failed)


def test_a_genuinely_queued_job_keeps_its_status_file(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Deleting a live job's file would let zppy submit the same task twice.
    run = _make_run(
        tmp_path,
        [
            "--cfg",
            "weekly_comprehensive_v3",
            "--scratch-root",
            str(tmp_path / "scratch"),
        ],
    )
    live = _write_status(run, "weekly_comprehensive_v3", "ts", "WAITING 111")
    stale = _write_status(run, "weekly_comprehensive_v3", "climo", "WAITING 222")
    monkeypatch.setattr(automation, "queued_job_ids", lambda user: {"111"})

    assert automation._clear_stale_status_files(run, run.cfgs) == 1
    assert os.path.exists(live)
    assert not os.path.exists(stale)


def test_an_unreadable_queue_leaves_every_status_file_alone(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Machines without SLURM, where every WAITING file would look stale.
    run = _make_run(
        tmp_path,
        [
            "--cfg",
            "weekly_comprehensive_v3",
            "--scratch-root",
            str(tmp_path / "scratch"),
        ],
    )
    waiting = _write_status(run, "weekly_comprehensive_v3", "ts", "WAITING 111")

    def unavailable(user: str) -> set:
        raise automation.CommandError(["squeue"], -1, "No such file or directory")

    monkeypatch.setattr(automation, "queued_job_ids", unavailable)

    assert automation._clear_stale_status_files(run, run.cfgs) == 0
    assert os.path.exists(waiting)


def test_submitting_clears_stale_status_files_first(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    worktree = _worktree_with_cfgs(tmp_path, ["weekly_comprehensive_v3"])
    run = _make_run(
        tmp_path,
        [
            "--cfg",
            "weekly_comprehensive_v3",
            "--scratch-root",
            str(tmp_path / "scratch"),
        ],
        status={"repos": {"zppy": {"worktree": worktree}}},
    )
    run.environments["zppy"] = _zppy_env()
    stale = _write_status(run, "weekly_comprehensive_v3", "ts", "WAITING 111")
    monkeypatch.setattr(automation, "run_command", _recording([]))
    monkeypatch.setattr(automation, "wait_for_user_jobs", lambda *a, **k: "drained")
    monkeypatch.setattr(automation, "queued_job_ids", lambda user: set())

    automation._stage_submit(run)

    assert not os.path.exists(stale)
