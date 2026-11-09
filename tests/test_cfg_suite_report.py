"""Tests for cfg suite reports.

Rendering must survive every partial run: the run that died halfway is the one
whose report a maintainer most needs.
"""

import json
from typing import Any, Dict

import pytest

from tests.cfg_suite import report as report_module
from tests.cfg_suite.layout import run_layout


@pytest.fixture
def paths():
    return run_layout(
        "/lcrc/group/e3sm/public_html/zppy_complete_run", "20260804_000001"
    )


def _passing_status() -> Dict[str, Any]:
    return {
        "stage": "passed",
        "tag": "20260804_000001",
        "machine": "chrysalis",
        "cfgs": ["weekly_comprehensive_v3"],
        "tasks": ["e3sm_diags"],
        "repos": {
            "zppy": {
                "sha": "a" * 40,
                "branch": "main",
                "environment": "test-zppy-main-20260804_000001",
                "environment_type": "dev",
            }
        },
        "status_sweep": {"passed": True, "failure_count": 0, "failures_by_cfg": {}},
        "pytest_results": [
            {"path": "tests/integration/test_bundles.py", "returncode": 0}
        ],
        "image_check": {
            "job_id": "123",
            "state": "COMPLETED",
            "exit_code": "0:0",
            "summary_source": "final",
            "severity_counts": {"IDENTICAL": 900, "MINOR": 0, "MISSING": 0},
        },
    }


def test_passing_run_reports_passed(paths) -> None:
    report = report_module.render_report(_passing_status(), paths)
    assert report["status"] == "passed"
    assert report["image_check"]["reviewable_count"] == 0


def test_non_ok_status_files_fail_the_report(paths) -> None:
    status = _passing_status()
    status["status_sweep"] = {
        "passed": False,
        "failure_count": 2,
        "failures_by_cfg": {"weekly_bundles": ["climo.status: ERROR"]},
    }
    report = report_module.render_report(status, paths)
    assert report["status"] == "jobs_failed"


def test_failing_integration_test_fails_the_report(paths) -> None:
    status = _passing_status()
    status["pytest_results"] = [
        {"path": "tests/integration/test_bundles.py", "returncode": 1}
    ]
    report = report_module.render_report(status, paths)
    assert report["status"] == "tests_failed"


def test_failing_image_checker_fails_the_report(paths) -> None:
    status = _passing_status()
    status["image_check"]["state"] = "FAILED"
    status["image_check"]["exit_code"] = "1:0"
    report = report_module.render_report(status, paths)
    assert report["status"] == "images_failed"


def test_no_plot_run_reports_job_failure_and_output_location(paths) -> None:
    status = _passing_status()
    status["stage"] = "validation_failed"
    status["tasks"] = ["e3sm_to_cmip"]
    status["status_sweep"] = {
        "passed": False,
        "failure_count": 1,
        "failures_by_cfg": {
            "weekly_comprehensive_v3": ["e3sm_to_cmip_atm.status: ERROR"]
        },
    }
    status["image_check"] = {"state": "NOT_APPLICABLE"}
    status["output_dir"] = "/scratch/zppy_complete_run/tag/output"

    report = report_module.render_report(status, paths)
    markdown = report_module.render_markdown(report)

    assert report["status"] == "jobs_failed"
    assert "Image check not applicable: no plotting tasks selected." in markdown
    assert (
        "Job scripts and logs are under `/scratch/zppy_complete_run/tag/output`"
        in markdown
    )


@pytest.mark.parametrize(
    "stage",
    [
        "dependency_never_satisfied",
        "timed_out",
        "submission_failed",
        "prepare_failed",
    ],
)
def test_interrupted_runs_report_incomplete(paths, stage: str) -> None:
    report = report_module.render_report({"stage": stage}, paths)
    assert report["status"] == "incomplete"


def test_empty_status_renders_rather_than_raising(paths) -> None:
    report = report_module.render_report({}, paths)
    assert report["status"] == "incomplete"
    assert report["schema_version"] == report_module.SCHEMA_VERSION
    # Markdown must render too; a traceback here would hide the real failure.
    assert "zppy cfg suite test" in report_module.render_markdown(report)


def test_malformed_status_fields_do_not_raise(paths) -> None:
    status = {
        "stage": "validate",
        "status_sweep": "not a mapping",
        "pytest_results": "not a list",
        "image_check": None,
        "repos": 42,
    }
    report = report_module.render_report(status, paths)
    assert report["pytest_results"] == []
    assert report["repos"] == {}
    report_module.render_markdown(report)


def test_write_report_emits_both_artifacts(tmp_path, paths) -> None:
    report = report_module.render_report(_passing_status(), paths)
    json_path, markdown_path = report_module.write_report(report, str(tmp_path))

    with open(json_path) as stream:
        written = json.load(stream)
    assert written["status"] == "passed"

    markdown = open(markdown_path).read()
    assert "# zppy cfg suite test -- 20260804_000001" in markdown
    assert "never promotes" in markdown


def test_json_is_stable_across_renders(tmp_path, paths) -> None:
    status = _passing_status()
    first = json.dumps(
        report_module.render_report(status, paths), sort_keys=True, default=str
    )
    second = json.dumps(
        report_module.render_report(status, paths), sort_keys=True, default=str
    )
    assert first == second


def test_markdown_lists_the_tested_commits(paths) -> None:
    markdown = report_module.render_markdown(
        report_module.render_report(_passing_status(), paths)
    )
    assert "`zppy`" in markdown
    assert "a" * 12 in markdown
    assert "test-zppy-main-20260804_000001" in markdown


def test_changes_since_baseline_are_in_json_and_markdown(paths) -> None:
    status = _passing_status()
    status["changes_since_baseline"] = [
        {
            "repo": "zppy",
            "tasks": ["climo"],
            "baseline": {
                "tag": "20260701_000001",
                "generated": "2026-07-01T00:00:00Z",
                "commit": "b" * 40,
            },
            "tested": {"branch": "feature", "commit": "c" * 40},
            "range_type": "commit",
            "count": 1,
            "commits": [
                {
                    "sha": "c" * 40,
                    "date": "2026-07-02",
                    "subject": "Fix issue (#42)",
                    "url": "https://github.com/E3SM-Project/zppy/pull/42",
                }
            ],
        }
    ]
    status["changes_since_baseline_note"] = "Worktree caveat."

    report = report_module.render_report(status, paths)
    markdown = report_module.render_markdown(report)

    assert report["changes_since_baseline"][0]["count"] == 1
    assert "## Changes since the baseline" in markdown
    assert "Worktree caveat." in markdown
    assert "[Fix issue (#42)](https://github.com/E3SM-Project/zppy/pull/42)" in markdown


def test_new_cfg_baseline_is_reported_as_not_compared(paths) -> None:
    status = _passing_status()
    status["baseline_by_cfg_task"] = {
        "weekly_legacy_3.2.0_comprehensive_v3:e3sm_diags": {
            "state": "not-compared",
            "reason": "new cfg",
            "tag": "",
            "run_dir": "",
            "generated": "",
            "repos": {},
        }
    }

    report = report_module.render_report(status, paths)
    markdown = report_module.render_markdown(report)

    assert (
        report["baseline_by_cfg_task"][
            "weekly_legacy_3.2.0_comprehensive_v3:e3sm_diags"
        ]["state"]
        == "not-compared"
    )
    assert "new cfg: no baseline (not compared)" in markdown


def test_environment_section_records_pins_and_unified_script(paths) -> None:
    status = _passing_status()
    status["repos"]["zppy"]["environment_type"] = "unified"
    status["pin_dependencies"] = ["nco<5.4.0", "e3sm_diags:xarray==2025.1.0"]
    status["applied_pins"] = {"e3sm_diags": ["nco<5.4.0"]}
    status["unified_load_script"] = "/opt/e3sm/load-unified.sh"
    markdown = report_module.render_markdown(report_module.render_report(status, paths))
    assert "Requested dependency pins:" in markdown
    assert "`nco<5.4.0`" in markdown
    assert "Applied dependency pins:" in markdown
    assert "E3SM-Unified load script: `/opt/e3sm/load-unified.sh`" in markdown


def test_unified_zppy_report_identifies_the_tested_commit_and_runtime(paths) -> None:
    status = _passing_status()
    status["repos"]["zppy"]["environment_type"] = "unified"
    status["unified"] = {
        "version": "1.13.0",
        "packages": {"zppy": "3.3.0"},
    }
    status["zppy_runtime"] = {
        "path": "/opt/unified/lib/python3.13/site-packages/zppy/__init__.py",
        "version": "3.3.0",
    }
    markdown = report_module.render_markdown(report_module.render_report(status, paths))
    assert "E3SM-Unified 1.13.0" in markdown
    assert "a" * 12 in markdown
    assert "/opt/unified/lib/python3.13/site-packages/zppy/__init__.py" in markdown


def test_markdown_shows_the_error_when_a_run_died(paths) -> None:
    status = {
        "stage": "timed_out",
        "error": "Jobs did not finish within 14400 seconds.",
    }
    markdown = report_module.render_markdown(report_module.render_report(status, paths))
    assert "Jobs did not finish" in markdown


def test_markdown_flags_reviewable_images(paths) -> None:
    status = _passing_status()
    status["image_check"]["severity_counts"] = {
        "IDENTICAL": 500,
        "NEGLIGIBLE": 20,
        "MINOR": 4,
        "MISSING": 1,
    }
    report = report_module.render_report(status, paths)
    assert report["image_check"]["reviewable_count"] == 5
    markdown = report_module.render_markdown(report)
    assert "5 images need review." in markdown


def test_markdown_names_the_baseline_and_when_it_was_produced(paths) -> None:
    status = _passing_status()
    status["baseline"] = {
        "tag": "20260701_000001",
        "generated": "2026-07-01T08:00:00+00:00",
    }
    markdown = report_module.render_markdown(report_module.render_report(status, paths))
    assert "* Baseline: `20260701_000001` (produced 2026-07-01)" in markdown


def test_markdown_lists_mixed_baselines_by_cfg_and_task(paths) -> None:
    status = _passing_status()
    status["baseline_by_cfg_task"] = {
        "weekly_comprehensive_v3:climo": {
            "tag": "20260701_000001",
            "generated": "2026-07-01T08:00:00+00:00",
            "repos": {"zppy": {"sha": "a" * 40}},
        },
        "weekly_comprehensive_v3:e3sm_diags": {
            "tag": "20260708_000001",
            "generated": "2026-07-08T08:00:00+00:00",
            "repos": {"e3sm_diags": {"sha": "b" * 40}},
        },
    }

    markdown = report_module.render_markdown(report_module.render_report(status, paths))

    assert "* Baseline: mixed per cfg/task (2 runs; see selections below)" in markdown
    assert (
        "| `weekly_comprehensive_v3` | `climo` | `20260701_000001` | 2026-07-01 |"
        in markdown
    )
    assert (
        "| `weekly_comprehensive_v3` | `e3sm_diags` | `20260708_000001` | 2026-07-08 |"
        in markdown
    )
    assert "`zppy` aaaaaaaaaaaa" in markdown
    assert "`e3sm_diags` bbbbbbbbbbbb" in markdown


def test_markdown_says_when_there_is_no_baseline(paths) -> None:
    markdown = report_module.render_markdown(
        report_module.render_report(_passing_status(), paths)
    )
    assert "* Baseline: _none promoted_" in markdown


def test_report_cli_renders_from_a_status_file(tmp_path) -> None:
    status = _passing_status()
    status["run_dir"] = str(tmp_path / "run")
    status_path = tmp_path / "status.json"
    status_path.write_text(json.dumps(status))

    assert (
        report_module.main(
            ["--status", str(status_path), "--output-dir", str(tmp_path / "out")]
        )
        == 0
    )
    written = json.loads((tmp_path / "out" / report_module.JSON_FILENAME).read_text())
    assert written["paths"]["results_dir"] == str(tmp_path / "run")

    # A truncated status still yields a report, never a traceback.
    status_path.write_text("{truncated")
    assert (
        report_module.main(
            ["--status", str(status_path), "--output-dir", str(tmp_path / "out2")]
        )
        == 1
    )
    assert (tmp_path / "out2" / report_module.MARKDOWN_FILENAME).is_file()


def test_environment_section_precedes_the_results(paths) -> None:
    status = _passing_status()
    status["environment_diff"] = {
        "compared": 1,
        "unavailable": [],
        "repos_differing": ["e3sm_diags"],
        "change_count": 1,
        "notable_change_count": 1,
        "repos": [
            {
                "repo": "e3sm_diags",
                "available": True,
                "change_count": 1,
                "changes": [
                    {
                        "name": "numpy",
                        "baseline": "2.1.3",
                        "candidate": "2.2.0",
                        "kind": "changed",
                        "notable": True,
                    }
                ],
            }
        ],
    }
    status["environment_note"] = "Dependencies changed in `e3sm_diags`."
    status["environment_drift"] = {
        "changed_environments": ["e3sm_diags"],
        "change_count": 1,
        "environments": {
            "e3sm_diags": [
                {
                    "name": "métrique",
                    "prepared": "1.0 build-é conda-forge",
                    "final": "2.0 build-é dépôt",
                }
            ]
        },
    }
    markdown = report_module.render_markdown(report_module.render_report(status, paths))

    # It decides how to read everything below it.
    assert markdown.index("## Environment") < markdown.index("## Job status files")
    assert (
        "<summary>Environment: WARNING 1 dependency differs from baseline</summary>"
        in markdown
    )
    assert "<details>" in markdown and "<details open>" not in markdown
    assert "Environment changed during run:" in markdown
    assert "métrique" in markdown
    assert "build-é dépôt" in markdown
    assert "2.1.3" in markdown


def test_environment_section_is_absent_when_not_compared(paths) -> None:
    markdown = report_module.render_markdown(
        report_module.render_report(_passing_status(), paths)
    )
    assert "## Environment" not in markdown


def test_unavailable_environment_explains_why_in_report(paths) -> None:
    status = _passing_status()
    status["environment_diff"] = {
        "compared": 0,
        "unavailable": ["e3sm_to_cmip"],
        "repos": [
            {
                "repo": "e3sm_to_cmip",
                "available": False,
                "detail": "No environment export or package listing for this run.",
                "changes": [],
            }
        ],
    }

    markdown = report_module.render_markdown(report_module.render_report(status, paths))

    assert "Not compared for:" in markdown
    assert "No environment export or package listing for this run." in markdown


def test_environment_note_survives_into_json(paths) -> None:
    status = _passing_status()
    status["environment_note"] = "No dependency changed."
    report = report_module.render_report(status, paths)
    assert report["environment_note"] == "No dependency changed."


def test_failed_jobs_point_at_their_logs_on_scratch(paths) -> None:
    status = _passing_status()
    status["output_dir"] = "/lcrc/globalscratch/me/zppy_complete_run/tag/output"
    status["status_sweep"] = {
        "passed": False,
        "failure_count": 1,
        "failures_by_cfg": {"weekly_bundles": ["climo.status: ERROR"]},
    }
    markdown = report_module.render_markdown(report_module.render_report(status, paths))
    assert "/lcrc/globalscratch/me/zppy_complete_run/tag/output" in markdown
    assert "scratch" in markdown


def test_report_names_the_unified_release(paths) -> None:
    status = _passing_status()
    status["repos"]["e3sm_diags"] = {"environment_type": "unified"}
    status["unified"] = {
        "version": "1.13.0",
        "resolved_load_script": "/lcrc/soft/load_e3sm_unified_1.13.0_chrysalis.sh",
        "packages": {"e3sm_diags": "3.2.0"},
    }
    markdown = report_module.render_markdown(report_module.render_report(status, paths))
    assert (
        "* E3SM-Unified: 1.13.0 (`load_e3sm_unified_1.13.0_chrysalis.sh`)" in markdown
    )
    assert (
        "| `e3sm_diags` | — | — | E3SM-Unified 1.13.0 (`e3sm_diags` 3.2.0) |"
        in markdown
    )
