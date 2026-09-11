"""Helpers for rendering the failing-only image-summary report section."""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import DefaultDict, List, Sequence, Tuple

TableRow = Tuple[str, List[str]]


def _parse_summary_table(lines: Sequence[str]) -> Tuple[str | None, List[str], List[TableRow]]:
    header: str | None = None
    header_cols: List[str] = []
    rows: List[TableRow] = []
    in_table: bool = False

    for line in lines:
        stripped: str = line.strip()
        if stripped.startswith("| Test name"):
            header = line.rstrip("\n")
            header_cols = [col.strip() for col in stripped.strip("|").split("|")]
            in_table = True
            continue
        if in_table and stripped.startswith("| ---"):
            continue
        if in_table and stripped.startswith("|"):
            cols: List[str] = [col.strip() for col in stripped.strip("|").split("|")]
            rows.append((line.rstrip("\n"), cols))
        elif in_table and not stripped.startswith("|"):
            in_table = False

    return header, header_cols, rows


def _has_failures(value: str) -> bool:
    digits: str = ""
    for char in value:
        if char.isdigit():
            digits += char
        else:
            break
    return digits not in ("", "0")


def _match_task(name: str, tasks: Sequence[str]) -> str:
    tokens = {
        token for token in re.split(r"[^A-Za-z0-9_]+", name) if token
    }
    for task in tasks:
        if task in tokens:
            return task
    return "other"


def render_failing_image_summary(summary_file: str, tasks: Sequence[str]) -> str:
    """Render the failing-only summary table grouped by task."""

    lines: List[str] = Path(summary_file).read_text().splitlines()
    header, header_cols, rows = _parse_summary_table(lines)

    if (
        header is None
        or "Missing images" not in header_cols
        or "Needs review" not in header_cols
    ):
        return "Unable to identify failing image-check columns.\n"

    missing_idx: int = header_cols.index("Missing images")
    needs_review_idx: int = header_cols.index("Needs review")
    separator: str = "| " + " | ".join(["---"] * len(header_cols)) + " |"

    failing: List[Tuple[str, str]] = []
    for line, cols in rows:
        if len(cols) <= max(missing_idx, needs_review_idx):
            continue
        if _has_failures(cols[missing_idx]) or _has_failures(cols[needs_review_idx]):
            failing.append((line, cols[0]))

    if not failing:
        return "No failing image-check tests.\n"

    by_task: DefaultDict[str, List[str]] = defaultdict(list)
    for line, name in failing:
        by_task[_match_task(name, tasks)].append(line)

    output_lines: List[str] = []
    for task in sorted(by_task):
        output_lines.extend([f"`{task}`", "", header, separator, *by_task[task], ""])

    return "\n".join(output_lines).rstrip() + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    args: Sequence[str] = sys.argv[1:] if argv is None else argv
    if not args:
        raise SystemExit("Usage: python -m tests.integration.image_summary_report <summary_file> [task...]")

    summary_file: str = args[0]
    tasks: Sequence[str] = args[1:]
    sys.stdout.write(render_failing_image_summary(summary_file, tasks))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
