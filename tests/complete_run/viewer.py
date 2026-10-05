"""An HTML page for reviewing image differences.

The image checker already writes ``<name>_actual.png``, ``<name>_expected.png``,
``<name>_diff.png`` and ``image_scores.json`` into a web-served directory, but
leaves a reviewer to browse a directory listing of thousands of files. This
renders an ``index.html`` beside them that puts each changed plot next to its
baseline and diff, worst first, with filters.

The page is self-contained: the portal serves static files only, so there are no
external stylesheets or scripts.
"""

from __future__ import annotations

import html
import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from tests.complete_run.envdiff import EnvironmentDiff
from tests.integration.image_severity import REVIEWABLE_SEVERITIES, SEVERITY_ORDER

logger: logging.Logger = logging.getLogger(__name__)

VIEWER_FILENAME: str = "index.html"
# The run-level page that summarizes every package's image checks.
REVIEW_SUMMARY_FILENAME: str = "index.html"

# SEVERITY_ORDER runs least to most severe, so a higher index is worse. This
# matches how image_severity.Comparison sorts itself.
_RANK: Dict[str, int] = {
    severity: index for index, severity in enumerate(SEVERITY_ORDER)
}

_STYLE: str = """
:root {
  --bg: #ffffff; --fg: #1a1a1a; --muted: #666; --line: #d8d8d8;
  --card: #fafafa; --accent: #0b5fff;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #15171a; --fg: #e8e8e8; --muted: #9aa0a6; --line: #333;
    --card: #1e2125; --accent: #79a8ff;
  }
}
* { box-sizing: border-box; }
body { margin: 0; padding: 0 16px 48px; background: var(--bg); color: var(--fg);
  font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
header { padding: 24px 0 8px; border-bottom: 1px solid var(--line); }
h1 { margin: 0 0 4px; font-size: 20px; }
.sub { color: var(--muted); font-size: 13px; }
.counts { display: flex; flex-wrap: wrap; gap: 8px; margin: 16px 0; padding: 0; list-style: none; }
.counts li { border: 1px solid var(--line); border-radius: 999px; padding: 3px 10px;
  font-size: 12px; color: var(--muted); background: var(--card); }
.counts b { color: var(--fg); }
.controls { display: flex; flex-wrap: wrap; gap: 12px; align-items: center;
  margin: 16px 0; padding: 12px; background: var(--card);
  border: 1px solid var(--line); border-radius: 8px; position: sticky; top: 0; z-index: 2; }
.controls label { font-size: 12px; color: var(--muted); }
select, input[type="search"] { font: inherit; padding: 4px 6px; background: var(--bg);
  color: var(--fg); border: 1px solid var(--line); border-radius: 6px; }
figure { margin: 0 0 28px; border: 1px solid var(--line); border-radius: 8px;
  overflow: hidden; background: var(--card); }
figcaption { padding: 10px 12px; border-bottom: 1px solid var(--line);
  display: flex; flex-wrap: wrap; gap: 10px; align-items: baseline; }
.name { font-weight: 600; word-break: break-all; }
.sev { font-size: 11px; letter-spacing: .04em; text-transform: uppercase;
  border-radius: 4px; padding: 2px 6px; border: 1px solid var(--line); }
.sev-MISSING, .sev-STRUCTURAL { background: #b3261e; color: #fff; border-color: #b3261e; }
.sev-MAJOR { background: #c25e00; color: #fff; border-color: #c25e00; }
.sev-MODERATE { background: #8a6d00; color: #fff; border-color: #8a6d00; }
.sev-MINOR { background: #3a6ea5; color: #fff; border-color: #3a6ea5; }
.cause { color: var(--muted); font-size: 12px; }
.metrics { color: var(--muted); font-size: 12px; margin-left: auto; }
.grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1px;
  background: var(--line); }
.grid > div { background: var(--bg); padding: 8px; }
.grid h3 { margin: 0 0 6px; font-size: 11px; text-transform: uppercase;
  letter-spacing: .04em; color: var(--muted); font-weight: 600; }
.grid img { width: 100%; height: auto; display: block; border: 1px solid var(--line); }
.missing { color: var(--muted); font-style: italic; padding: 24px 8px; text-align: center; }
a { color: var(--accent); }
#empty { padding: 32px 0; color: var(--muted); }
.env { margin: 16px 0; border: 1px solid var(--line); border-radius: 8px;
  background: var(--card); overflow: hidden; }
.env.warn { border-color: #b3261e; }
.env > summary { padding: 12px; cursor: pointer; font-weight: 600; }
.env.warn > summary { color: #b3261e; }
.env .body { padding: 0 12px 12px; }
.env p { margin: 0 0 10px; font-weight: 400; color: var(--fg); }
.env table { border-collapse: collapse; width: 100%; font-size: 12px; }
.env th, .env td { text-align: left; padding: 4px 8px; border-bottom: 1px solid var(--line); }
.env th { color: var(--muted); font-weight: 600; }
.env td.pkg { font-weight: 600; }
.env tr.notable td.pkg::after { content: ' \\2022'; color: #c25e00; }
@media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }
.back { font-size: 13px; }
h2 { font-size: 16px; margin: 28px 0 8px; }
.table-wrap { overflow-x: auto; border: 1px solid var(--line); border-radius: 8px; }
table.summary { border-collapse: collapse; width: 100%; font-size: 13px; }
table.summary th, table.summary td { padding: 6px 10px; text-align: left;
  border-bottom: 1px solid var(--line); white-space: nowrap; }
table.summary th { color: var(--muted); font-weight: 600; background: var(--card); }
table.summary td.num, table.summary th.num { text-align: right;
  font-variant-numeric: tabular-nums; }
table.summary td.zero { color: var(--muted); }
table.summary tr:last-child td { border-bottom: none; }
table.summary tfoot td { font-weight: 600; background: var(--card); }
.result { font-size: 11px; letter-spacing: .04em; text-transform: uppercase;
  border-radius: 4px; padding: 2px 6px; border: 1px solid var(--line); }
.result-clean { background: #1e7a3d; color: #fff; border-color: #1e7a3d; }
.result-unchecked { color: var(--muted); }
"""

_SCRIPT: str = """
const severity = document.getElementById('severity');
const cause = document.getElementById('cause');
const search = document.getElementById('search');
const figures = Array.from(document.querySelectorAll('figure'));
const empty = document.getElementById('empty');

function apply() {
  const wantSeverity = severity.value;
  const wantCause = cause.value;
  const text = search.value.trim().toLowerCase();
  let shown = 0;
  for (const figure of figures) {
    const matches =
      (wantSeverity === 'all' || figure.dataset.severity === wantSeverity) &&
      (wantCause === 'all' || figure.dataset.cause === wantCause) &&
      (text === '' || figure.dataset.name.toLowerCase().includes(text));
    figure.hidden = !matches;
    if (matches) shown++;
  }
  empty.hidden = shown > 0;
}

for (const control of [severity, cause, search]) {
  control.addEventListener('input', apply);
}
apply();
"""


def render_viewer(
    scores: List[Dict[str, Any]],
    cfg: str,
    task: str,
    diff_dir_name: str = "",
    environment_diffs: List[EnvironmentDiff] | None = None,
    environment_note: str = "",
    summary_href: str = "",
) -> str:
    """Render the review page for one task's image comparisons.

    ``environment_diffs`` and ``environment_note`` describe how this run's
    dependencies differed from the baseline's. They are shown above the images
    because they decide how to read them: a plot that changed because a
    dependency moved is a different finding from one that changed because zppy
    did.
    """
    reviewable: List[Dict[str, Any]] = [
        entry for entry in scores if str(entry.get("severity")) in REVIEWABLE_SEVERITIES
    ]
    reviewable.sort(
        key=lambda entry: (
            -_RANK.get(str(entry.get("severity")), 0),
            -float(entry.get("content_fraction") or 0.0),
            str(entry.get("name", "")),
        )
    )

    counts: Dict[str, int] = count_severities(scores)

    causes: List[str] = sorted(
        {str(entry.get("cause") or "unknown") for entry in reviewable}
    )

    parts: List[str] = [
        "<!doctype html>",
        '<html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{html.escape(cfg)} / {html.escape(task)} image diffs</title>",
        f"<style>{_STYLE}</style></head><body>",
        "<header>",
        (
            f"<a class='back' href='{html.escape(summary_href)}'>"
            "\u2190 All packages</a>"
            if summary_href
            else ""
        ),
        f"<h1>{html.escape(task)} <span class='sub'>{html.escape(cfg)}</span></h1>",
        f"<div class='sub'>{len(reviewable)} of {len(scores)} images need review."
        " Images that are identical or look cosmetic are counted below but not"
        " shown.</div>",
        "</header>",
        _render_environment(environment_diffs or [], environment_note),
        _render_counts(counts),
    ]

    if reviewable:
        parts.append(_render_controls(causes))
        parts.extend(_render_figure(entry, diff_dir_name) for entry in reviewable)
        parts.append("<p id='empty' hidden>Nothing matches these filters.</p>")
        parts.append(f"<script>{_SCRIPT}</script>")
    else:
        parts.append(
            "<p id='empty'>No image needs review. Every comparison was"
            " identical or looked cosmetic.</p>"
        )

    parts.append("</body></html>")
    return "\n".join(parts)


def count_severities(scores: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    """Count comparisons by severity, including severities that did not occur."""
    counts: Dict[str, int] = {severity: 0 for severity in SEVERITY_ORDER}
    for entry in scores:
        severity = str(entry.get("severity"))
        if severity in counts:
            counts[severity] += 1
    return counts


def _render_counts(counts: Dict[str, int]) -> str:
    """Render the severity tally, including severities that did not occur."""
    items: List[str] = []
    for severity in reversed(SEVERITY_ORDER):
        note: str = "" if severity in REVIEWABLE_SEVERITIES else " (not a failure)"
        items.append(
            f"<li>{html.escape(severity)}{note}: <b>{counts.get(severity, 0)}</b></li>"
        )
    return "<ul class='counts'>" + "".join(items) + "</ul>"


def _render_controls(causes: List[str]) -> str:
    """Render the severity, cause, and name filters."""
    severity_options: str = "".join(
        f"<option value='{html.escape(severity)}'>{html.escape(severity)}</option>"
        for severity in reversed(REVIEWABLE_SEVERITIES)
    )
    cause_options: str = "".join(
        f"<option value='{html.escape(cause)}'>{html.escape(cause)}</option>"
        for cause in causes
    )
    return (
        "<div class='controls'>"
        "<label for='severity'>Severity</label>"
        f"<select id='severity'><option value='all'>all</option>{severity_options}</select>"
        "<label for='cause'>Likely cause</label>"
        f"<select id='cause'><option value='all'>all</option>{cause_options}</select>"
        "<label for='search'>Name</label>"
        "<input id='search' type='search' placeholder='filter by image name'>"
        "</div>"
    )


def _render_figure(entry: Dict[str, Any], diff_dir_name: str) -> str:
    """Render one image's actual, expected, and diff panels."""
    name: str = str(entry.get("name", "unknown"))
    severity: str = str(entry.get("severity", "unknown"))
    cause: str = str(entry.get("cause") or "unknown")
    prefix: str = f"{diff_dir_name}/{name}" if diff_dir_name else name

    if severity == "MISSING":
        # There is no actual image to show; that absence is the finding.
        panels: str = (
            "<div><h3>Actual</h3>"
            "<p class='missing'>This image was not produced.</p></div>"
            f"<div><h3>Expected</h3>{_image(prefix, 'expected')}</div>"
            "<div><h3>Difference</h3><p class='missing'>Not applicable.</p></div>"
        )
    else:
        panels = (
            f"<div><h3>Actual</h3>{_image(prefix, 'actual')}</div>"
            f"<div><h3>Expected</h3>{_image(prefix, 'expected')}</div>"
            f"<div><h3>Difference</h3>{_image(prefix, 'diff')}</div>"
        )

    return (
        f"<figure data-severity='{html.escape(severity)}' "
        f"data-cause='{html.escape(cause)}' data-name='{html.escape(name)}'>"
        "<figcaption>"
        f"<span class='sev sev-{html.escape(severity)}'>{html.escape(severity)}</span>"
        f"<span class='name'>{html.escape(name)}</span>"
        f"<span class='cause'>{html.escape(cause)}</span>"
        f"<span class='metrics'>{_metrics(entry)}</span>"
        "</figcaption>"
        f"<div class='grid'>{panels}</div>"
        "</figure>"
    )


def _image(prefix: str, kind: str) -> str:
    """Render one panel's image, linking to it at full size."""
    source: str = html.escape(f"{prefix}_{kind}.png")
    return f"<a href='{source}'><img loading='lazy' src='{source}' alt='{kind}'></a>"


def _metrics(entry: Dict[str, Any]) -> str:
    """Render the numbers behind a severity, for someone checking the call."""
    content: float = float(entry.get("content_fraction") or 0.0)
    raw: float = float(entry.get("raw_fraction") or 0.0)
    localized = entry.get("localized_pixels")
    pieces: List[str] = [
        f"content {content * 100:.2f}%",
        f"raw {raw * 100:.2f}%",
    ]
    if localized:
        pieces.append(f"{localized} px changed")
    return html.escape(" \u00b7 ".join(pieces))


def write_viewer(
    diff_subdir: str,
    cfg: str,
    task: str,
    environment_diffs: List[EnvironmentDiff] | None = None,
    environment_note: str = "",
    summary_href: str = "",
) -> str:
    """Render and write the viewer for one task's diff directory.

    Returns the viewer's path, or an empty string when there are no scores to
    render -- a run that produced no comparisons should not leave a misleading
    empty page behind.
    """
    scores = load_scores(diff_subdir)
    if scores is None:
        return ""

    path: str = os.path.join(diff_subdir, VIEWER_FILENAME)
    _write_page(
        path,
        render_viewer(
            scores,
            cfg,
            task,
            # The image checker names each image relative to the cfg's diff
            # directory (e.g. "e3sm_diags/..."), which is the parent of the
            # task's diff_subdir where this page lives.
            diff_dir_name="..",
            environment_diffs=environment_diffs,
            environment_note=environment_note,
            summary_href=summary_href,
        ),
    )
    logger.info("Wrote image diff viewer: %s", path)
    return path


def load_scores(diff_subdir: str) -> Optional[List[Dict[str, Any]]]:
    """Read a task's ``image_scores.json``, or None if it is absent or malformed."""
    scores_path: str = os.path.join(diff_subdir, "image_scores.json")
    try:
        with open(scores_path) as stream:
            scores = json.load(stream)
    except (OSError, json.JSONDecodeError) as error:
        logger.warning("Could not read %s: %s", scores_path, error)
        return None
    if not isinstance(scores, list):
        logger.warning("Unexpected contents in %s", scores_path)
        return None
    return [entry for entry in scores if isinstance(entry, dict)]


def _write_page(path: str, content: str) -> None:
    """Write a page the web portal can serve."""
    with open(path, "w") as stream:
        stream.write(content)
    try:
        os.chmod(path, 0o644)
    except OSError as error:
        logger.warning("Could not set mode on %s: %s", path, error)


# Run summary #################################################################
# One page across every package, so a reviewer starts from where the problems
# are instead of opening each task's page in turn.


@dataclass
class SummaryRow:
    """One cfg/task image check, as the run summary shows it."""

    package: str
    task: str
    cfg: str
    # By severity. Empty when the task was expected to be checked but no
    # comparison was recorded -- itself a finding.
    counts: Dict[str, int] = field(default_factory=dict)
    # The task's review page, relative to the summary page.
    viewer_href: str = ""
    # What the package was tested at: "main @ 1a2b3c4d", "E3SM-Unified".
    tested_at: str = ""

    @property
    def checked(self) -> bool:
        return bool(self.counts)

    @property
    def total(self) -> int:
        return sum(self.counts.values())

    @property
    def reviewable(self) -> int:
        return sum(self.counts.get(severity, 0) for severity in REVIEWABLE_SEVERITIES)

    @property
    def worst(self) -> str:
        """The most severe reviewable severity present, or ""."""
        for severity in reversed(SEVERITY_ORDER):
            if severity in REVIEWABLE_SEVERITIES and self.counts.get(severity):
                return severity
        return ""


def render_summary(
    rows: Sequence[SummaryRow],
    tag: str,
    baseline: str = "",
    environment_diffs: List[EnvironmentDiff] | None = None,
    environment_note: str = "",
) -> str:
    """Render the run-level summary: every package, then every check."""
    checked: List[SummaryRow] = [row for row in rows if row.checked]
    needing_review: List[SummaryRow] = [row for row in checked if row.reviewable]
    unchecked: List[SummaryRow] = [row for row in rows if not row.checked]

    headline: str = (
        f"{len(needing_review)} of {len(rows)} checks need review"
        f" ({sum(row.reviewable for row in checked)} images)."
    )
    if unchecked:
        headline += f" {len(unchecked)} recorded no comparison."
    baseline_text: str = (
        f"Compared against baseline <b>{html.escape(baseline)}</b>."
        if baseline
        else "No baseline was recorded for this run."
    )

    parts: List[str] = [
        "<!doctype html>",
        '<html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{html.escape(tag)} image review</title>",
        f"<style>{_STYLE}</style></head><body>",
        "<header>",
        f"<h1>Image review <span class='sub'>{html.escape(tag)}</span></h1>",
        f"<div class='sub'>{html.escape(headline)} {baseline_text}"
        " See also <a href='complete-run-report.md'>the run report</a>.</div>",
        "</header>",
        _render_environment(environment_diffs or [], environment_note),
        "<h2>By package</h2>",
        _render_package_table(rows),
        "<h2>By check</h2>",
        _render_check_table(rows),
        "</body></html>",
    ]
    return "\n".join(part for part in parts if part)


def _render_package_table(rows: Sequence[SummaryRow]) -> str:
    """One row per package, rolling up every cfg and task it covers."""
    packages: Dict[str, List[SummaryRow]] = {}
    for row in rows:
        packages.setdefault(row.package, []).append(row)

    body: List[str] = []
    for package, group in packages.items():
        checked = [row for row in group if row.checked]
        counts = _sum_counts(checked)
        tested_at = sorted({row.tested_at for row in group if row.tested_at})
        body.append(
            "<tr>"
            f"<td><b><a href='#{_package_anchor(package)}'>"
            f"{html.escape(package)}</a></b></td>"
            f"<td>{html.escape(', '.join(tested_at)) or '—'}</td>"
            f"<td>{html.escape(', '.join(sorted({row.task for row in group})))}</td>"
            f"<td>{_result_badge(_worst(counts), bool(checked), len(checked) < len(group))}</td>"
            + _num(sum(1 for row in checked if row.reviewable))
            + _num(len(group))
            + _num(sum(counts.get(s, 0) for s in REVIEWABLE_SEVERITIES))
            + _num(sum(counts.values()))
            + "</tr>"
        )

    return (
        "<div class='table-wrap'><table class='summary'><thead><tr>"
        "<th>Package</th><th>Tested at</th><th>Tasks</th><th>Result</th>"
        "<th class='num'>Checks needing review</th><th class='num'>Checks</th>"
        "<th class='num'>Images needing review</th><th class='num'>Images</th>"
        "</tr></thead><tbody>" + "".join(body) + "</tbody></table></div>"
    )


def _render_check_table(rows: Sequence[SummaryRow]) -> str:
    """One row per cfg and task, with its full severity breakdown."""
    severities: List[str] = list(reversed(REVIEWABLE_SEVERITIES))
    header: str = (
        "<tr><th>Package</th><th>Task</th><th>Cfg</th><th>Result</th>"
        + "".join(f"<th class='num'>{html.escape(s)}</th>" for s in severities)
        + "<th class='num'>Cosmetic</th><th class='num'>Total</th></tr>"
    )

    body: List[str] = []
    anchored: set[str] = set()
    for row in rows:
        # The first row of each package is where its name in the package table
        # jumps to.
        row_id: str = ""
        if row.package not in anchored:
            anchored.add(row.package)
            row_id = f" id='{_package_anchor(row.package)}'"
        # The task links to its review page. It is in the first columns so it
        # is never scrolled out of view on a narrow window.
        task: str = (
            f"<a href='{html.escape(row.viewer_href)}'>"
            f"{html.escape(row.task)} \u2192</a>"
            if row.viewer_href
            else html.escape(row.task)
        )
        cells: str = "".join(
            _num(row.counts.get(s, 0)) if row.checked else "<td class='num zero'>—</td>"
            for s in severities
        )
        cosmetic: int = row.total - row.reviewable
        body.append(
            f"<tr{row_id}>"
            f"<td>{html.escape(row.package)}</td>"
            f"<td>{task}</td>"
            f"<td>{html.escape(row.cfg)}</td>"
            f"<td>{_result_badge(row.worst, row.checked)}</td>"
            + cells
            + (
                _num(cosmetic) + _num(row.total)
                if row.checked
                else "<td></td><td></td>"
            )
            + "</tr>"
        )

    totals = _sum_counts([row for row in rows if row.checked])
    reviewable_total: int = sum(totals.get(s, 0) for s in REVIEWABLE_SEVERITIES)
    footer: str = (
        "<tr><td colspan='4'>All checks</td>"
        + "".join(_num(totals.get(s, 0)) for s in severities)
        + _num(sum(totals.values()) - reviewable_total)
        + _num(sum(totals.values()))
        + "</tr>"
    )
    return (
        "<div class='table-wrap'><table class='summary'>"
        f"<thead>{header}</thead><tbody>{''.join(body)}</tbody>"
        f"<tfoot>{footer}</tfoot></table></div>"
    )


def _package_anchor(package: str) -> str:
    """An element id for a package's rows in the check table."""
    return "pkg-" + (re.sub(r"[^a-z0-9]+", "-", package.lower()).strip("-") or "x")


def _sum_counts(rows: Sequence[SummaryRow]) -> Dict[str, int]:
    totals: Dict[str, int] = {severity: 0 for severity in SEVERITY_ORDER}
    for row in rows:
        for severity, count in row.counts.items():
            totals[severity] = totals.get(severity, 0) + count
    return totals


def _worst(counts: Dict[str, int]) -> str:
    for severity in reversed(SEVERITY_ORDER):
        if severity in REVIEWABLE_SEVERITIES and counts.get(severity):
            return severity
    return ""


def _result_badge(worst: str, checked: bool, partly_unchecked: bool = False) -> str:
    """Show the worst finding, "clean", or that nothing was compared."""
    if not checked:
        return "<span class='result result-unchecked'>not checked</span>"
    suffix: str = (
        " <span class='sub'>(some not checked)</span>" if partly_unchecked else ""
    )
    if worst:
        return f"<span class='sev sev-{html.escape(worst)}'>{html.escape(worst)}</span>{suffix}"
    return f"<span class='result result-clean'>clean</span>{suffix}"


def _num(value: int) -> str:
    css: str = "num zero" if value == 0 else "num"
    return f"<td class='{css}'>{value}</td>"


def write_summary(
    path: str,
    rows: Sequence[SummaryRow],
    tag: str,
    baseline: str = "",
    environment_diffs: List[EnvironmentDiff] | None = None,
    environment_note: str = "",
) -> str:
    """Write the run-level summary page and return its path."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    _write_page(
        path,
        render_summary(rows, tag, baseline, environment_diffs, environment_note),
    )
    logger.info("Wrote image review summary: %s", path)
    return path


def _render_environment(diffs: List[EnvironmentDiff], note: str) -> str:
    """Render how this run's dependencies differed from the baseline's.

    Shown whether or not anything changed: "nothing changed" is the statement
    that makes an image difference attributable to code, so its absence would
    leave a reviewer guessing.
    """
    if not diffs and not note:
        return ""

    comparable = [diff for diff in diffs if diff.available]
    unavailable = [diff for diff in diffs if not diff.available]
    differing = [diff for diff in comparable if diff.differs]
    total = sum(len(diff.changes) for diff in differing)

    # A run that meant to reproduce the baseline but did not is the case a
    # reviewer must not miss.
    warn = "not** attributable" in note or "not attributable" in note
    if differing:
        heading = (
            f"Environment: {total} dependency change"
            f"{'s' if total != 1 else ''} in "
            + ", ".join(diff.repo for diff in differing)
        )
    elif comparable and unavailable:
        heading = (
            "Environment: no dependency changed in those compared"
            f" ({len(unavailable)} not compared)"
        )
    elif comparable:
        heading = "Environment: no dependency changed"
    else:
        heading = "Environment: not compared"

    body: List[str] = []
    if note:
        body.append(f"<p>{_note_html(note)}</p>")
    for diff in unavailable:
        body.append(f"<p>{html.escape(diff.repo)}: {html.escape(diff.detail)}</p>")
    for diff in differing:
        body.append(f"<h3>{html.escape(diff.repo)}</h3>")
        if diff.detail:
            body.append(f"<p>{html.escape(diff.detail)}</p>")
        body.append(
            "<table><tr><th>Package</th><th>Baseline</th><th>This run</th></tr>"
            + "".join(
                f"<tr class='{'notable' if change.notable else ''}'>"
                f"<td class='pkg'>{html.escape(change.name)}</td>"
                f"<td>{html.escape(change.baseline or '—')}</td>"
                f"<td>{html.escape(change.candidate or '—')}</td></tr>"
                for change in diff.changes
            )
            + "</table>"
        )

    if not body:
        return (
            f"<details class='env'><summary>{html.escape(heading)}</summary>"
            "<div class='body'><p>Every package matched the baseline.</p></div>"
            "</details>"
        )

    # Open by default when something needs attention.
    open_attribute = " open" if warn or differing else ""
    css = "env warn" if warn else "env"
    return (
        f"<details class='{css}'{open_attribute}>"
        f"<summary>{html.escape(heading)}</summary>"
        f"<div class='body'>{''.join(body)}</div></details>"
    )


def _note_html(note: str) -> str:
    """Escape a note, keeping its backtick and bold emphasis."""
    escaped = html.escape(note)
    escaped = escaped.replace("**", "\x00")
    parts = escaped.split("\x00")
    rebuilt = ""
    for index, part in enumerate(parts):
        rebuilt += f"<strong>{part}</strong>" if index % 2 else part
    while "`" in rebuilt:
        rebuilt = rebuilt.replace("`", "<code>", 1).replace("`", "</code>", 1)
    return rebuilt
