"""Tests for the validation stage."""

import glob
import json
import os
from typing import List, Tuple

import pytest

from tests.complete_run import validate
from tests.complete_run.layout import RunLayout
from tests.complete_run.params import MACHINE_PROFILES


def _write_status_dir(root, cfg, case, entries):
    status_dir = os.path.join(
        root, "output", f"zppy_{cfg}_output", "run", case, "post", "scripts"
    )
    os.makedirs(status_dir, exist_ok=True)
    for name, content in entries.items():
        with open(os.path.join(status_dir, name), "w") as stream:
            stream.write(content)
    return status_dir


def test_sweep_passes_when_every_status_is_ok(tmp_path) -> None:
    _write_status_dir(
        str(tmp_path),
        "weekly_comprehensive_v3",
        "v3.LR.historical_0051",
        {"climo.status": "OK\n", "ts.status": "OK\n"},
    )
    sweep = validate.sweep_status_files(
        RunLayout(str(tmp_path)), ["weekly_comprehensive_v3"]
    )
    assert sweep.passed
    assert sweep.failure_count == 0


def test_sweep_reports_non_ok_entries(tmp_path) -> None:
    _write_status_dir(
        str(tmp_path),
        "weekly_comprehensive_v3",
        "v3.LR.historical_0051",
        {"climo.status": "OK\n", "e3sm_diags.status": "ERROR\n"},
    )
    sweep = validate.sweep_status_files(
        RunLayout(str(tmp_path)), ["weekly_comprehensive_v3"]
    )
    assert not sweep.passed
    assert sweep.failure_count == 1
    assert "ERROR" in sweep.failures_by_cfg["weekly_comprehensive_v3"][0]


def test_sweep_uses_the_v2_case_for_v2_cfgs(tmp_path) -> None:
    _write_status_dir(
        str(tmp_path),
        "weekly_comprehensive_v2",
        "v2.LR.historical_0201",
        {"climo.status": "OK\n"},
    )
    sweep = validate.sweep_status_files(
        RunLayout(str(tmp_path)), ["weekly_comprehensive_v2"]
    )
    assert sweep.passed


def test_sweep_records_a_missing_directory(tmp_path) -> None:
    sweep = validate.sweep_status_files(RunLayout(str(tmp_path)), ["weekly_bundles"])
    assert not sweep.passed
    assert sweep.missing_dirs == ["weekly_bundles"]


def test_summarize_severities_covers_every_severity(tmp_path) -> None:
    scores_dir = tmp_path / "image_check_failures" / "e3sm_diags"
    scores_dir.mkdir(parents=True)
    (scores_dir / "image_scores.json").write_text(
        json.dumps(
            [
                {"name": "a.png", "severity": "IDENTICAL"},
                {"name": "b.png", "severity": "MINOR"},
                {"name": "c.png", "severity": "MISSING"},
                {"name": "d.png", "severity": "MINOR"},
            ]
        )
    )

    counts = validate.summarize_severities(str(tmp_path))
    assert counts["IDENTICAL"] == 1
    assert counts["MINOR"] == 2
    assert counts["MISSING"] == 1
    # Every severity is present, even at zero, so two reports line up.
    assert counts["STRUCTURAL"] == 0
    assert list(counts) == [
        "IDENTICAL",
        "NEGLIGIBLE",
        "MINOR",
        "MODERATE",
        "MAJOR",
        "STRUCTURAL",
        "MISSING",
    ]


def test_summarize_severities_tolerates_unreadable_scores(tmp_path) -> None:
    bad = tmp_path / "image_scores.json"
    bad.write_text("{not json")
    counts = validate.summarize_severities(str(tmp_path))
    assert sum(counts.values()) == 0


def test_image_check_reviewable_count_excludes_cosmetic() -> None:
    result = validate.ImageCheckResult()
    result.severity_counts = validate.OrderedDict(
        [
            ("IDENTICAL", 100),
            ("NEGLIGIBLE", 20),
            ("MINOR", 3),
            ("MODERATE", 1),
            ("MAJOR", 0),
            ("STRUCTURAL", 0),
            ("MISSING", 2),
        ]
    )
    # IDENTICAL and NEGLIGIBLE do not fail the test.
    assert result.reviewable_count == 6


def test_collect_artifacts_copies_in_repo_output(tmp_path) -> None:
    workdir = tmp_path / "worktree"
    (workdir / "images_logs").mkdir(parents=True)
    (workdir / "images_logs" / "test_x.log").write_text("log")
    (workdir / "test_images_summary.md").write_text("| Test name |\n")

    results_dir = tmp_path / "results"
    collected = validate.collect_artifacts(str(workdir), str(results_dir))

    # The worktree is removed after a run, so these must be copied out first.
    assert (results_dir / "artifacts" / "test_images_summary.md").is_file()
    assert (results_dir / "artifacts" / "images_logs" / "test_x.log").is_file()
    assert len(collected) == 2


def test_collect_artifacts_skips_what_was_never_written(tmp_path) -> None:
    workdir = tmp_path / "worktree"
    workdir.mkdir()
    assert validate.collect_artifacts(str(workdir), str(tmp_path / "results")) == []


def test_image_checker_removes_stale_summaries_before_submitting(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workdir = tmp_path / "worktree"
    workdir.mkdir()
    stale = workdir / "test_images_summary.md"
    stale.write_text("from a previous attempt")

    monkeypatch.setattr(validate, "submit", lambda path: "424242")
    monkeypatch.setattr(
        validate,
        "wait_for_job",
        lambda job_id, **kwargs: validate.JobOutcome(job_id, "COMPLETED", "0:0"),
    )

    result = validate.run_image_checker(
        str(workdir),
        str(tmp_path / "results"),
        "20260804_run1",
        MACHINE_PROFILES["chrysalis"],
        "test-zppy-main-20260804_run1",
    )

    # A stale summary would otherwise be reported as this run's result.
    assert result.summary_source == "missing"
    assert result.job_id == "424242"
    assert result.passed


def test_image_checker_charges_the_requested_account(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workdir = tmp_path / "worktree"
    workdir.mkdir()
    scripts: List[str] = []

    def submit(path: str) -> str:
        scripts.append(open(path).read())
        return "1"

    monkeypatch.setattr(validate, "submit", submit)
    monkeypatch.setattr(
        validate,
        "wait_for_job",
        lambda job_id, **kwargs: validate.JobOutcome(job_id, "COMPLETED", "0:0"),
    )
    validate.run_image_checker(
        str(workdir),
        str(tmp_path / "results"),
        "tag",
        MACHINE_PROFILES["chrysalis"],
        "env",
        account="myproject",
    )
    assert "#SBATCH --account=myproject" in scripts[0]
    assert "--account=e3sm" not in scripts[0]


def test_integration_tests_run_in_the_environment_under_test(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # They call `zppy -c` themselves, which must be the revision being tested.
    from tests.complete_run.environments import Environment

    seen: List[List[str]] = []

    def run(args: List[str], **kwargs) -> Tuple[int, str]:
        seen.append(args)
        return 0, ""

    monkeypatch.setattr(validate, "run_command_status", run)
    environment = Environment("zppy", "dev", "test-zppy", "activate")
    results = validate.run_pytest_files("/wt", environment, ["tests/a.py"])
    assert results[0].passed
    assert seen[0][:5] == ["conda", "run", "--no-capture-output", "-n", "test-zppy"]


def test_image_checker_records_a_submission_failure(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workdir = tmp_path / "worktree"
    workdir.mkdir()

    def fail(path):
        raise RuntimeError("sbatch: error: Batch job submission failed")

    monkeypatch.setattr(validate, "submit", fail)
    result = validate.run_image_checker(
        str(workdir),
        str(tmp_path / "results"),
        "tag",
        MACHINE_PROFILES["chrysalis"],
        "env",
    )
    assert result.state == "SUBMISSION_FAILED"
    assert not result.passed


def test_image_checker_prefers_a_final_summary_over_an_early_one(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workdir = tmp_path / "worktree"
    workdir.mkdir()
    monkeypatch.setattr(validate, "submit", lambda path: "1")
    monkeypatch.setattr(
        validate,
        "wait_for_job",
        lambda job_id, **kwargs: validate.JobOutcome(job_id, "COMPLETED", "0:0"),
    )

    def write_summaries(*args, **kwargs):
        (workdir / "early_test_images_summary.md").write_text("early")
        (workdir / "test_images_summary.md").write_text("final")
        return validate.JobOutcome("1", "COMPLETED", "0:0")

    monkeypatch.setattr(validate, "wait_for_job", write_summaries)
    result = validate.run_image_checker(
        str(workdir),
        str(tmp_path / "results"),
        "tag",
        MACHINE_PROFILES["chrysalis"],
        "env",
    )
    assert result.summary_source == "final"


def test_image_checker_falls_back_to_an_early_summary(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workdir = tmp_path / "worktree"
    workdir.mkdir()
    monkeypatch.setattr(validate, "submit", lambda path: "1")

    def write_early(*args, **kwargs):
        (workdir / "early_test_images_summary.md").write_text("early")
        return validate.JobOutcome("1", "FAILED", "1:0")

    monkeypatch.setattr(validate, "wait_for_job", write_early)
    result = validate.run_image_checker(
        str(workdir),
        str(tmp_path / "results"),
        "tag",
        MACHINE_PROFILES["chrysalis"],
        "env",
    )
    assert result.summary_source == "early"
    assert not result.passed


# Baseline material ###########################################################


def _make_images(layout, cfg, case, names):
    case_dir = layout.www_case_dir(cfg, case)
    for name in names:
        path = os.path.join(case_dir, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as stream:
            stream.write("x")
    return case_dir


def test_image_list_describes_what_the_run_produced(tmp_path) -> None:
    from tests.complete_run.layout import run_layout

    layout = run_layout(str(tmp_path), "tag")
    _make_images(
        layout,
        "weekly_comprehensive_v3",
        "v3.LR.historical_0051",
        ["e3sm_diags/a.png", "e3sm_diags/b.png", "ilamb/c.png", "notes.txt"],
    )

    counts = validate.write_image_lists(layout, ["weekly_comprehensive_v3"])

    assert counts == {"weekly_comprehensive_v3": 3}
    listed = open(layout.image_list("weekly_comprehensive_v3")).read().splitlines()
    assert listed == ["./e3sm_diags/a.png", "./e3sm_diags/b.png", "./ilamb/c.png"]


def test_image_list_excludes_this_run_s_own_diffs(tmp_path) -> None:
    from tests.complete_run.layout import run_layout

    layout = run_layout(str(tmp_path), "tag")
    _make_images(
        layout,
        "weekly_bundles",
        "v3.LR.historical_0051",
        [
            "e3sm_diags/a.png",
            "image_check_failures_bundles/e3sm_diags/a_diff.png",
        ],
    )

    validate.write_image_lists(layout, ["weekly_bundles"])
    listed = open(layout.image_list("weekly_bundles")).read()

    # Diff output is this run's review material, not baseline material.
    assert "image_check_failures" not in listed
    assert listed.strip() == "./e3sm_diags/a.png"


def test_image_list_records_zero_rather_than_skipping(tmp_path) -> None:
    from tests.complete_run.layout import run_layout

    layout = run_layout(str(tmp_path), "tag")
    counts = validate.write_image_lists(layout, ["weekly_bundles"])

    # Promoting an empty run should be visible, not silent.
    assert counts == {"weekly_bundles": 0}
    assert open(layout.image_list("weekly_bundles")).read() == ""


def test_settings_baselines_are_captured_from_the_worktree(tmp_path) -> None:
    from tests.complete_run.layout import run_layout

    layout = run_layout(str(tmp_path), "tag")
    workdir = tmp_path / "worktree"
    scripts = workdir / "test_bash_generation_output" / "post" / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "climo.bash").write_text("#!/bin/bash\n")
    (scripts / "provenance.20260918.settings").write_text("case_name = x\n")

    validate.capture_settings_baselines(str(workdir), layout, [])

    captured = layout.settings_baseline("expected_bash_files")
    assert os.path.isfile(os.path.join(captured, "climo.bash"))
    # Provenance carries a timestamp, so it would differ on every run.
    assert not glob.glob(os.path.join(captured, "provenance*"))


def _scored_task(case_dir, diff_dir_name, task, severities):
    diff_subdir = os.path.join(case_dir, diff_dir_name, task)
    os.makedirs(diff_subdir, exist_ok=True)
    with open(os.path.join(diff_subdir, "image_scores.json"), "w") as stream:
        json.dump(
            [
                {"name": f"img{i}", "severity": severity}
                for i, severity in enumerate(severities)
            ],
            stream,
        )
    return diff_subdir


def test_viewers_are_written_for_each_task(tmp_path) -> None:
    from tests.complete_run.layout import run_layout

    layout = run_layout(str(tmp_path), "tag")
    case_dir = layout.www_case_dir("weekly_bundles", "v3.LR.historical_0051")
    # The image checker drops the "weekly_" prefix from its diff directories.
    for task in ("e3sm_diags", "ilamb"):
        _scored_task(case_dir, "image_check_failures_bundles", task, ["MAJOR"])

    written = validate.write_viewers(
        layout, ["weekly_bundles"], tasks=["e3sm_diags", "ilamb"]
    )

    viewers, summary = written[:-1], written[-1]
    assert len(viewers) == 2
    assert all(path.endswith("index.html") for path in viewers)
    assert summary == os.path.join(layout.root, "index.html")


def test_summary_covers_every_package_and_flags_unchecked_tasks(tmp_path) -> None:
    from tests.complete_run.layout import run_layout

    layout = run_layout(str(tmp_path), "tag")
    case_dir = layout.www_case_dir("weekly_comprehensive_v3", "v3.LR.historical_0051")
    name = "image_check_failures_comprehensive_v3"
    _scored_task(case_dir, name, "e3sm_diags", ["IDENTICAL", "MAJOR", "MINOR"])
    _scored_task(case_dir, name, "global_time_series", ["IDENTICAL", "NEGLIGIBLE"])
    # livvkit was expected to be checked but recorded nothing.

    written = validate.write_viewers(
        layout,
        ["weekly_comprehensive_v3"],
        tasks=["e3sm_diags", "global_time_series", "livvkit"],
        repos={
            "e3sm_diags": {"sha": "1234567890abcdef", "branch": "main"},
            "zppy_interfaces": {"environment_type": "unified"},
        },
        baseline="20260901_run1",
    )
    page = open(written[-1]).read()

    assert "e3sm_diags" in page and "zppy-interfaces" in page and "LIVVkit" in page
    assert "main @ 12345678" in page
    assert "E3SM-Unified" in page
    assert "not checked" in page
    assert "20260901_run1" in page
    # Every checked task links to its own page, relative to the summary.
    assert (
        "www/zppy_weekly_comprehensive_v3_www/run/v3.LR.historical_0051/"
        "image_check_failures_comprehensive_v3/e3sm_diags/index.html"
    ) in page
    # And each task page links back up to the summary.
    task_page = open(os.path.join(case_dir, name, "e3sm_diags", "index.html")).read()
    assert "All packages" in task_page
    assert "../../../../../../index.html" in task_page


def test_summary_shows_the_newest_rerun(tmp_path) -> None:
    from tests.complete_run.layout import run_layout

    layout = run_layout(str(tmp_path), "tag")
    case_dir = layout.www_case_dir("weekly_bundles", "v3.LR.historical_0051")
    first = _scored_task(case_dir, "image_check_failures_bundles", "ilamb", ["MAJOR"])
    rerun = _scored_task(
        case_dir, "image_check_failures_bundles_try2", "ilamb", ["IDENTICAL"]
    )
    os.utime(os.path.join(first, "image_scores.json"), (1, 1))

    written = validate.write_viewers(layout, ["weekly_bundles"], tasks=["ilamb"])

    assert os.path.join(rerun, "index.html") in written
    assert os.path.join(first, "index.html") not in written
    assert "clean" in open(written[-1]).read()
