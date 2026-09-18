"""Tests for complete run reports.

Rendering must survive every partial run: the run that died halfway is the one
whose report a maintainer most needs.
"""

import json
from typing import Any, Dict

import pytest

from tests.complete_run import report as report_module
from tests.complete_run.layout import run_layout


@pytest.fixture
def paths():
    return run_layout("/lcrc/group/e3sm/public_html/zppy_complete_run", "20260804_run1")


def _passing_status() -> Dict[str, Any]:
    return {
        "stage": "passed",
        "tag": "20260804_run1",
        "machine": "chrysalis",
        "cfgs": ["weekly_comprehensive_v3"],
        "tasks": ["e3sm_diags"],
        "repos": {
            "zppy": {
                "sha": "a" * 40,
                "branch": "main",
                "environment": "test-zppy-main-20260804_run1",
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
    assert "zppy complete run test" in report_module.render_markdown(report)


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
    assert "# zppy complete run test -- 20260804_run1" in markdown
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
    assert "test-zppy-main-20260804_run1" in markdown


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
        "tag": "20260701_run1",
        "generated": "2026-07-01T08:00:00+00:00",
    }
    markdown = report_module.render_markdown(report_module.render_report(status, paths))
    assert "* Baseline: `20260701_run1` (produced 2026-07-01)" in markdown


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
    markdown = report_module.render_markdown(report_module.render_report(status, paths))

    # It decides how to read everything below it.
    assert markdown.index("## Environment") < markdown.index("## Job status files")
    assert "numpy" in markdown
    assert "2.1.3" in markdown


def test_environment_section_is_absent_when_not_compared(paths) -> None:
    markdown = report_module.render_markdown(
        report_module.render_report(_passing_status(), paths)
    )
    assert "## Environment" not in markdown


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
