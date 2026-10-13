"""Deterministic reports for the complete run test.

Two artifacts come out of every run, including one that failed partway:
``complete-run-report.json`` for machines and ``complete-run-report.md`` for
the weekly testing log. Both are written under the run's results directory.

Rendering never raises on a missing input. A run that died before producing an
artifact is exactly the run whose report a maintainer most needs.
"""

from __future__ import annotations

import argparse
import html
import logging
import os
from collections import OrderedDict
from typing import Any, Dict, List, Sequence

from tests.complete_run.layout import RunLayout, read_json_object, write_json
from tests.complete_run.provenance import REPO_CONDA_PACKAGES
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
    repos: Dict[str, Any] = _mapping(status.get("repos"))
    uses_unified: bool = bool(status.get("unified")) or any(
        _mapping(entry).get("environment_type") == "unified"
        for entry in repos.values()
    )

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
        "baseline_by_cfg_task": _mapping(status.get("baseline_by_cfg_task")),
        "error": status.get("error"),
        "cfgs": list(status.get("cfgs") or []),
        "tasks": list(status.get("tasks") or []),
        "repos": repos,
        "unified": _mapping(status.get("unified")),
        "pins": list(status.get("pin_dependencies") or []),
        "applied_pins": _mapping(status.get("applied_pins")),
        "unified_load_script": (
            status.get("unified_load_script", "") if uses_unified else ""
        ),
        "zppy_runtime": _mapping(status.get("zppy_runtime")),
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
        "environment_drift": _mapping(status.get("environment_drift")),
        "changes_since_baseline": list(status.get("changes_since_baseline") or []),
        "changes_since_baseline_note": status.get(
            "changes_since_baseline_note", ""
        ),
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

    with open(markdown_path, "w", encoding="utf-8") as stream:
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
        _baseline_line(
            _mapping(report.get("baseline")),
            _mapping(report.get("baseline_by_cfg_task")),
        ),
        *filter(None, [_unified_line(_mapping(report.get("unified")))]),
        "",
    ]

    if report.get("error"):
        lines.extend(["> " + str(report["error"]), ""])

    lines.extend(_repos_section(report))
    lines.extend(_baseline_selection_section(report))
    lines.extend(_changes_since_baseline_section(report))
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


def _baseline_line(
    baseline: Dict[str, Any], selected: Dict[str, Any] | None = None
) -> str:
    """Say which promoted run this one was compared against, and its age.

    The baseline's production date, not its promotion date, is what matters:
    results normally sit under review before promotion.
    """
    tags = {
        str(_mapping(entry).get("tag") or "")
        for entry in (selected or {}).values()
        if _mapping(entry).get("tag")
    }
    if len(tags) > 1:
        return f"* Baseline: mixed per cfg/task ({len(tags)} runs; see selections below)"
    if tags:
        tag = next(iter(tags))
        produced_values = {
            str(_mapping(entry).get("generated") or "")[:10]
            for entry in (selected or {}).values()
            if str(_mapping(entry).get("tag") or "") == tag
        }
        produced = next(iter(produced_values)) if len(produced_values) == 1 else "varies"
        return f"* Baseline: `{tag}` (produced {produced})"
    if not baseline.get("tag"):
        return "* Baseline: _none promoted_"
    produced: str = str(baseline.get("generated") or "unknown")[:10]
    return f"* Baseline: `{baseline['tag']}` (produced {produced})"


def _baseline_selection_section(report: Dict[str, Any]) -> List[str]:
    """List the baseline run and package commits selected for each cfg/task."""
    selected: Dict[str, Any] = _mapping(report.get("baseline_by_cfg_task"))
    if not selected:
        return []
    lines: List[str] = [
        "## Baseline by cfg/task",
        "",
        "| Cfg | Task | Run | Produced | Repository commits |",
        "| --- | --- | --- | --- | --- |",
    ]
    for key, value in sorted(selected.items()):
        cfg, separator, task = key.partition(":")
        if not separator:
            continue
        entry = _mapping(value)
        repos = _mapping(entry.get("repos"))
        if entry.get("state") == "not-compared":
            run = "new cfg: no baseline (not compared)"
            produced = "—"
            commits = "—"
            lines.append(
                f"| `{cfg}` | `{task}` | {run} | {produced} | {commits} |"
            )
            continue
        commits = ", ".join(
            f"`{name}` {str(_mapping(repo).get('sha') or 'n/a')[:12]}"
            for name, repo in sorted(repos.items())
            if _mapping(repo).get("sha")
        ) or "—"
        lines.append(
            f"| `{cfg}` | `{task}` | `{entry.get('tag') or 'unknown'}` | "
            f"{str(entry.get('generated') or 'unknown')[:10]} | {commits} |"
        )
    lines.append("")
    return lines


def _changes_since_baseline_section(report: Dict[str, Any]) -> List[str]:
    """List first-parent commits or Unified package changes since each baseline."""
    changes: List[Dict[str, Any]] = _sequence(
        report.get("changes_since_baseline")
    )
    if not changes:
        return []

    lines: List[str] = ["## Changes since the baseline", ""]
    note = str(report.get("changes_since_baseline_note") or "")
    if note:
        lines.extend([note, ""])

    for entry in changes:
        baseline = _mapping(entry.get("baseline"))
        tested = _mapping(entry.get("tested"))
        repo = str(entry.get("repo") or "unknown")
        tasks = ", ".join(str(task) for task in entry.get("tasks", []))
        if entry.get("task"):
            tasks = str(entry["task"])
        lines.extend(
            [
                f"### `{repo}`" + (f" ({tasks})" if tasks else ""),
                "",
                f"* Baseline: `{baseline.get('tag') or 'unknown'}` "
                f"(produced {str(baseline.get('generated') or 'unknown')[:10]}); "
                f"commit `{str(baseline.get('commit') or 'date-based')[:12]}`",
                f"* Tested: `{tested.get('branch') or 'unknown'}` "
                f"@ `{str(tested.get('commit') or 'E3SM-Unified')[:12]}`",
                f"* Changes: {int(entry.get('count', 0) or 0)} "
                f"({entry.get('range_type') or 'unknown'})",
                "",
            ]
        )
        if entry.get("note"):
            lines.extend([str(entry["note"]), ""])
        if entry.get("warning"):
            lines.extend([f"Warning: {entry['warning']}", ""])
        if entry.get("error"):
            lines.extend([f"Could not list changes: {entry['error']}", ""])

        for change in _sequence(entry.get("commits")):
            subject = str(change.get("subject") or "")
            subject = subject.replace("|", "\\|").replace("[", "\\[").replace("]", "\\]")
            url = str(change.get("url") or "")
            linked = f"[{subject}]({url})" if url else subject
            lines.append(
                f"* `{str(change.get('sha') or '')[:12]}` "
                f"({change.get('date') or 'date unknown'}): {linked}"
            )
        for change in _sequence(entry.get("changes")):
            lines.append(
                f"* `{change.get('name')}`: "
                f"`{change.get('baseline') or 'unknown'}` → "
                f"`{change.get('tested') or 'unknown'}`"
            )
        if not entry.get("commits") and not entry.get("changes") and not entry.get("error"):
            lines.append("_No changes since the baseline._")
        lines.append("")
    return lines


def _unified_line(unified: Dict[str, Any]) -> str:
    """Name the E3SM-Unified release the run's released packages came from."""
    if not unified.get("version"):
        return ""
    script: str = str(unified.get("resolved_load_script") or "")
    suffix: str = f" (`{os.path.basename(script)}`)" if script else ""
    return f"* E3SM-Unified: {unified['version']}{suffix}"


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
    unified: Dict[str, Any] = _mapping(report.get("unified"))
    packages: Dict[str, Any] = _mapping(unified.get("packages"))
    for name in sorted(repos):
        entry: Dict[str, Any] = _mapping(repos[name])
        if entry.get("environment_type") == "unified":
            package: str = str(REPO_CONDA_PACKAGES.get(name, name))
            version: str = str(packages.get(package, "")) or "unknown"
            if name == "zppy":
                runtime: Dict[str, Any] = _mapping(report.get("zppy_runtime"))
                version = str(packages.get(package) or runtime.get("version") or version)
                commit: str = str(entry.get("sha", ""))[:12] or "n/a"
                lines.append(
                    f"| `{name}` | `{entry.get('branch', 'n/a')}` | `{commit}` | "
                    f"E3SM-Unified {unified.get('version') or '?'} "
                    f"(`{package}` {version}; `{runtime.get('path') or 'path unknown'}`) |"
                )
                continue
            lines.append(
                f"| `{name}` | — | — | E3SM-Unified {unified.get('version') or '?'}"
                f" (`{package}` {version}) |"
            )
            continue
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
    drift: Dict[str, Any] = _mapping(report.get("environment_drift"))
    note: str = str(report.get("environment_note") or "")
    pins: List[Any] = list(report.get("pins") or [])
    applied_pins: Dict[str, Any] = _mapping(report.get("applied_pins"))
    load_script: str = str(report.get("unified_load_script") or "")
    if (
        not diff
        and not drift
        and not note
        and not pins
        and not applied_pins
        and not load_script
    ):
        return []

    changed_during_run: List[str] = list(drift.get("changed_environments") or [])
    drift_count: int = int(drift.get("change_count", 0) or 0)
    diff_count: int = int(diff.get("change_count", 0) or 0)
    unavailable_count: int = len(list(diff.get("unavailable") or []))
    if "meant to reproduce" in note and "does not." in note:
        heading: str = (
            f"Environment: WARNING reproduction failed, {diff_count} package"
            f"{'s' if diff_count != 1 else ''} "
            f"{'differs' if diff_count == 1 else 'differ'}"
        )
    elif diff_count:
        heading = (
            f"Environment: WARNING {diff_count} dependenc"
            f"{'y' if diff_count == 1 else 'ies'} differ"
            f"{'s' if diff_count == 1 else ''} from baseline"
        )
    elif drift_count:
        heading = (
            f"Environment: WARNING {drift_count} package"
            f"{'s' if drift_count != 1 else ''} changed during this run"
        )
    elif unavailable_count:
        heading = (
            f"Environment: WARNING {unavailable_count} environments not compared"
        )
    elif drift:
        heading = "Environment: no package changed during this run"
    elif diff.get("compared"):
        heading = "Environment: no dependency changed"
    else:
        heading = "Environment: not compared"

    lines: List[str] = [
        "## Environment",
        "",
        "<details>",
        f"<summary>{html.escape(heading)}</summary>",
        "",
    ]
    if note:
        lines.extend([note, ""])
    if changed_during_run:
        lines.extend(["Environment changed during run:", ""])
        drift_environments = _mapping(drift.get("environments"))
        for environment in changed_during_run:
            lines.append(f"* `{html.escape(str(environment))}`:")
            for change in _sequence(drift_environments.get(environment)):
                lines.append(
                    f"  * `{html.escape(str(change.get('name', '')))}`: "
                    f"`{html.escape(str(change.get('prepared') or '—'))}` → "
                    f"`{html.escape(str(change.get('final') or '—'))}`"
                )
        lines.append("")
    if load_script:
        lines.extend(
            [f"E3SM-Unified load script: `{html.escape(load_script)}`", ""]
        )
    if pins:
        lines.extend(["Requested dependency pins:", ""])
        for spec in pins:
            lines.append(f"* `{html.escape(str(spec))}`")
        lines.append("")
    if applied_pins:
        lines.extend(["Applied dependency pins:", ""])
        for repo, specs in sorted(applied_pins.items()):
            values: List[Any] = specs if isinstance(specs, list) else [specs]
            lines.append(
                f"* `{html.escape(str(repo))}`: "
                + ", ".join(f"`{html.escape(str(spec))}`" for spec in values)
            )
        lines.append("")

    unavailable: List[Any] = list(diff.get("unavailable") or [])
    repos: List[Dict[str, Any]] = _sequence(diff.get("repos"))
    if unavailable:
        details_by_repo: Dict[str, str] = {
            str(entry.get("repo", "")): str(entry.get("detail") or "")
            for entry in repos
            if not entry.get("available")
        }
        lines.extend(["Not compared for:", ""])
        for repo in sorted(unavailable):
            detail = details_by_repo.get(str(repo), "")
            lines.append(
                f"* `{html.escape(str(repo))}`"
                + (f": {html.escape(detail)}" if detail else "")
            )
        lines.append("")

    changed = [entry for entry in repos if entry.get("change_count")]
    if not changed:
        if diff.get("compared"):
            lines.extend(
                [
                    (
                        "No dependency changed in those compared."
                        if unavailable
                        else "No dependency changed."
                    ),
                    "",
                ]
            )
        lines.extend(["</details>", ""])
        return lines

    lines.extend(
        ["| Repository | Package | Baseline | This run |", "| --- | --- | --- | --- |"]
    )
    for entry in changed:
        repo = str(entry.get("repo", ""))
        for change in _sequence(entry.get("changes")):
            marker = " *" if change.get("notable") else ""
            lines.append(
                f"| `{html.escape(repo)}` | "
                f"`{html.escape(str(change.get('name', '')))}`{marker} | "
                f"`{html.escape(str(change.get('baseline') or '—'))}` | "
                f"`{html.escape(str(change.get('candidate') or '—'))}` |"
            )
    lines.extend(["", "\\* Packages that most often move results.", ""])
    lines.extend(["</details>", ""])
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
    if image.get("state") == "NOT_APPLICABLE":
        return [
            "## Image checker",
            "",
            "Image check not applicable: no plotting tasks selected.",
            "",
        ]
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
    if state == "NOT_APPLICABLE":
        return _PASSED
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
