"""Deterministic reports for the complete run test.

Two artifacts come out of every run, including one that failed partway:
``complete-run-report.json`` for machines and ``complete-run-report.md`` for
the weekly testing log. Both are written under the run's results directory.

Rendering never raises on a missing input. A run that died before producing an
artifact is exactly the run whose report a maintainer most needs.
"""

from __future__ import annotations

import argparse
import logging
import os
from collections import OrderedDict
from typing import Any, Dict, List, Sequence

from tests.complete_run.layout import RunLayout, read_json_object, write_json
from tests.complete_run.slurm import job_passed
from tests.complete_run.validate import reviewable_count
from tests.integration.image_severity import REVIEWABLE_SEVERITIES

logger: logging.Logger = logging.getLogger(__name__)

SCHEMA_VERSION: int = 2
JSON_FILENAME: str = "complete-run-report.json"
MARKDOWN_FILENAME: str = "complete-run-report.md"

# Written so the web portal can serve the report, matching how zppy sets the
# mode on its own provenance files.
REPORT_MODE: int = 0o644

_PASSED: str = "passed"


def render_report(status: Dict[str, Any], layout: RunLayout) -> Dict[str, Any]:
    """Build the report for one run from its status file."""
    stage: str = str(status.get("stage", "unknown"))
    image_check: Dict[str, Any] = _mapping(status.get("image_check"))
    sweep: Dict[str, Any] = _mapping(status.get("status_sweep"))
    pytest_results: List[Dict[str, Any]] = _sequence(status.get("pytest_results"))

    severity_counts: "OrderedDict[str, int]" = OrderedDict(
        (str(name), int(count))
        for name, count in _mapping(image_check.get("severity_counts")).items()
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "status": _report_status(stage, sweep, pytest_results, image_check),
        "stage": stage,
        "tag": status.get("tag"),
        "machine": status.get("machine"),
        "baseline": _mapping(status.get("baseline")),
        "error": status.get("error"),
        "cfgs": list(status.get("cfgs") or []),
        "tasks": list(status.get("tasks") or []),
        "repos": _mapping(status.get("repos")),
        "status_sweep": {
            "ran": bool(sweep),
            "passed": bool(sweep.get("passed", False)),
            "failure_count": int(sweep.get("failure_count", 0) or 0),
            "failures_by_cfg": _mapping(sweep.get("failures_by_cfg")),
            "missing_dirs": list(sweep.get("missing_dirs") or []),
        },
        "pytest_results": [
            {
                "path": result.get("path"),
                "passed": result.get("returncode") == 0,
                "returncode": result.get("returncode"),
            }
            for result in pytest_results
        ],
        "image_check": {
            "job_id": image_check.get("job_id", ""),
            "state": image_check.get("state", "NOT_RUN"),
            "exit_code": image_check.get("exit_code", "N/A"),
            "summary_source": image_check.get("summary_source", "missing"),
            "summary_path": image_check.get("summary_path", ""),
            "severity_counts": severity_counts,
            "reviewable_count": reviewable_count(severity_counts),
        },
        "environment_diff": _mapping(status.get("environment_diff")),
        "environment_note": status.get("environment_note", ""),
        "paths": {
            "results_dir": layout.root,
            "output": status.get("output_dir", ""),
            "image_review": status.get("image_review", ""),
            "status": layout.status,
            "env_descriptions": layout.env_descriptions,
            "worktrees": status.get("worktree_root", ""),
            "www_root_by_cfg": _mapping(status.get("www_root_by_cfg")),
        },
    }


def write_report(report: Dict[str, Any], output_dir: str) -> tuple[str, str]:
    """Write the JSON and Markdown reports, returning both paths."""
    json_path: str = write_json(os.path.join(output_dir, JSON_FILENAME), report)
    markdown_path: str = os.path.join(output_dir, MARKDOWN_FILENAME)

    with open(markdown_path, "w") as stream:
        stream.write(render_markdown(report))

    for path in (json_path, markdown_path):
        try:
            os.chmod(path, REPORT_MODE)
        except OSError as error:
            logger.warning("Could not set mode on %s: %s", path, error)

    return json_path, markdown_path


def render_markdown(report: Dict[str, Any]) -> str:
    """Render the report as Markdown for the weekly testing log."""
    lines: List[str] = [
        f"# zppy complete run test -- {report.get('tag') or 'unknown'}",
        "",
        f"* Status: **{report.get('status') or 'unknown'}**",
        f"* Terminal stage: `{report.get('stage') or 'unknown'}`",
        f"* Machine: `{report.get('machine') or 'unknown'}`",
        _baseline_line(_mapping(report.get("baseline"))),
        "",
    ]

    if report.get("error"):
        lines.extend(["> " + str(report["error"]), ""])

    lines.extend(_repos_section(report))
    lines.extend(_environment_section(report))
    lines.extend(_status_section(report))
    lines.extend(_pytest_section(report))
    lines.extend(_image_section(report))
    lines.extend(
        [
            "## Next steps",
            "",
            "Failures above are for human review. A complete run never promotes "
            "expected results; that remains the separate, explicit "
            "`update_*_expected_files_<machine>.sh` step.",
            "",
        ]
    )
    return "\n".join(lines)


def _baseline_line(baseline: Dict[str, Any]) -> str:
    """Say which promoted run this one was compared against, and its age.

    The baseline's production date, not its promotion date, is what matters:
    results normally sit under review before promotion.
    """
    if not baseline.get("tag"):
        return "* Baseline: _none promoted_"
    produced: str = str(baseline.get("generated") or "unknown")[:10]
    return f"* Baseline: `{baseline['tag']}` (produced {produced})"


def _repos_section(report: Dict[str, Any]) -> List[str]:
    """Render what each repository was tested at."""
    repos: Dict[str, Any] = _mapping(report.get("repos"))
    lines: List[str] = ["## What was tested", ""]
    if not repos:
        return lines + ["_No repository information was recorded._", ""]

    lines.extend(
        [
            "| Repository | Branch | Commit | Environment |",
            "| --- | --- | --- | --- |",
        ]
    )
    for name in sorted(repos):
        entry: Dict[str, Any] = _mapping(repos[name])
        sha: str = str(entry.get("sha", "")) or "n/a"
        lines.append(
            f"| `{name}` | `{entry.get('branch', 'n/a')}` | `{sha[:12]}` | "
            f"`{entry.get('environment') or entry.get('environment_type', 'n/a')}` |"
        )
    lines.append("")
    return lines


def _environment_section(report: Dict[str, Any]) -> List[str]:
    """Render how this run's dependencies differed from the baseline's.

    Placed before the results, because it decides how to read them: an image
    that changed because a dependency moved is a different finding from one
    that changed because zppy did.
    """
    diff: Dict[str, Any] = _mapping(report.get("environment_diff"))
    note: str = str(report.get("environment_note") or "")
    if not diff and not note:
        return []

    lines: List[str] = ["## Environment", ""]
    if note:
        lines.extend([note, ""])

    unavailable: List[Any] = list(diff.get("unavailable") or [])
    if unavailable:
        lines.extend(
            [
                "Not compared for: "
                + ", ".join(f"`{repo}`" for repo in sorted(unavailable)),
                "",
            ]
        )

    repos: List[Dict[str, Any]] = _sequence(diff.get("repos"))
    changed = [entry for entry in repos if entry.get("change_count")]
    if not changed:
        if diff.get("compared"):
            lines.extend(["No dependency changed.", ""])
        return lines

    lines.extend(
        ["| Repository | Package | Baseline | This run |", "| --- | --- | --- | --- |"]
    )
    for entry in changed:
        repo = str(entry.get("repo", ""))
        for change in _sequence(entry.get("changes")):
            marker = " *" if change.get("notable") else ""
            lines.append(
                f"| `{repo}` | `{change.get('name')}`{marker} | "
                f"`{change.get('baseline') or '—'}` | "
                f"`{change.get('candidate') or '—'}` |"
            )
    lines.extend(["", "\\* Packages that most often move results.", ""])
    return lines


def _status_section(report: Dict[str, Any]) -> List[str]:
    """Render the job status-file sweep."""
    sweep: Dict[str, Any] = _mapping(report.get("status_sweep"))
    lines: List[str] = ["## Job status files", ""]
    if not sweep.get("ran", True):
        return lines + ["_The status sweep did not run._", ""]
    if sweep.get("passed"):
        lines.extend(["All status files reported OK.", ""])
        return lines

    failures: Dict[str, Any] = _mapping(sweep.get("failures_by_cfg"))
    missing: List[Any] = list(sweep.get("missing_dirs") or [])
    lines.append(f"{sweep.get('failure_count', 0)} non-OK entries.")
    lines.append("")
    for cfg in sorted(failures):
        entries: List[Any] = list(failures[cfg] or [])
        lines.extend([f"`{cfg}`:", "", "```"])
        lines.extend(str(entry) for entry in entries)
        lines.extend(["```", ""])
    if missing:
        lines.extend(
            [
                "Status directories not found for: "
                + ", ".join(f"`{cfg}`" for cfg in sorted(missing)),
                "",
            ]
        )
    output: str = str(_mapping(report.get("paths")).get("output") or "")
    if output:
        lines.extend(
            [
                f"Job scripts and logs are under `{output}`. That is scratch "
                "space, so look before it is purged.",
                "",
            ]
        )
    return lines


def _pytest_section(report: Dict[str, Any]) -> List[str]:
    """Render the integration test outcomes."""
    results: List[Dict[str, Any]] = _sequence(report.get("pytest_results"))
    lines: List[str] = ["## Integration tests", ""]
    if not results:
        return lines + ["_The integration tests did not run._", ""]

    lines.extend(["| Test | Result |", "| --- | --- |"])
    for result in results:
        outcome: str = "pass" if result.get("passed") else "**FAIL**"
        lines.append(f"| `{result.get('path')}` | {outcome} |")
    lines.append("")
    return lines


def _image_section(report: Dict[str, Any]) -> List[str]:
    """Render the image checker outcome and its severity breakdown."""
    image: Dict[str, Any] = _mapping(report.get("image_check"))
    lines: List[str] = [
        "## Image checker",
        "",
        f"* SLURM job: `{image.get('job_id') or 'not submitted'}`",
        f"* Terminal state: `{image.get('state', 'unknown')}`",
        f"* Exit code: `{image.get('exit_code', 'unknown')}`",
        f"* Summary source: `{image.get('summary_source', 'unknown')}`",
        "",
    ]

    counts: Dict[str, Any] = _mapping(image.get("severity_counts"))
    if not counts:
        return lines + ["_No image scores were recorded._", ""]

    lines.extend(["| Severity | Images | Reviewable |", "| --- | --- | --- |"])
    for severity, count in counts.items():
        reviewable: str = "yes" if severity in REVIEWABLE_SEVERITIES else "no"
        lines.append(f"| {severity} | {count} | {reviewable} |")
    lines.extend(
        [
            "",
            f"{image.get('reviewable_count', 0)} images need review.",
            "",
        ]
    )
    if image.get("summary_path"):
        lines.extend([f"Full summary: `{image['summary_path']}`", ""])
    review: str = str(_mapping(report.get("paths")).get("image_review") or "")
    if review:
        lines.extend(
            [
                f"Review page, with a table across every package: `{review}`",
                "",
            ]
        )
    return lines


def _report_status(
    stage: str,
    sweep: Dict[str, Any],
    pytest_results: Sequence[Dict[str, Any]],
    image_check: Dict[str, Any],
) -> str:
    """Map a run's stage and findings onto one overall status."""
    if stage not in (_PASSED, "validate", "report", "validation_failed"):
        return "incomplete"

    if sweep and not sweep.get("passed", False):
        return "jobs_failed"
    if pytest_results and not all(
        result.get("returncode") == 0 for result in pytest_results
    ):
        return "tests_failed"

    state: str = str(image_check.get("state", "NOT_RUN"))
    if state == "NOT_RUN":
        return "incomplete"
    if not job_passed(state, str(image_check.get("exit_code", "N/A"))):
        return "images_failed"

    return _PASSED


def _mapping(value: Any) -> Dict[str, Any]:
    """Return a dict, whatever the input was."""
    return value if isinstance(value, dict) else {}


def _sequence(value: Any) -> List[Dict[str, Any]]:
    """Return a list of dicts, whatever the input was."""
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def main(argv: Sequence[str] | None = None) -> int:
    """Render a report from an existing status file."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", required=True, help="Path to status.json.")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)

    status: Dict[str, Any] = read_json_object(args.status)
    if not status:
        logger.error("Could not read a status object from %s", args.status)

    layout = RunLayout(str(status.get("run_dir") or args.output_dir))
    report = render_report(status, layout)
    write_report(report, args.output_dir)
    return 0 if report["status"] == _PASSED else 1


if __name__ == "__main__":
    raise SystemExit(main())
