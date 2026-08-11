#!/usr/bin/env python3
"""
pin_dev_env_to_unified.py

Cross-references a component's dev.yml (or dev-spec.txt-style yaml) against
the resolved package versions from the E3SM-Unified environment used to
generate the expected results, and produces:

  1. A modified copy of the dev env file, with each dependency resolved into
     one of four buckets (see below). Only the version portion of a changed
     line is rewritten -- comments, indentation, and every unrelated line
     (name:, channels:, etc.) are left exactly as they were.
  2. A Markdown report explaining what was decided for every package and why.

Standard library only -- no PyYAML, no `packaging`. The dev.yml files this
targets have a narrow, predictable shape (a `dependencies:` list, optionally
with a nested `pip:` sub-list), so a small line-based editor handles them
without pulling in a full YAML parser, and without the side effect a
YAML round-trip has of discarding every comment in the file.

Resolution logic per package:

  - unconstrained in dev.yml (e.g. "numpy")
      -> pinned to Unified's version. Nothing in dev.yml objects to this.

  - a range constraint in dev.yml (e.g. "numpy>=1.24", "numpy>=1.24,<2.0")
      -> if Unified's version satisfies the constraint, pinned to Unified's
         version.
      -> if it does NOT satisfy the constraint, this is a genuine, provable
         forced deviation: dev.yml's own requirement rules out Unified's
         version, so the original dev.yml spec is kept, unchanged, and
         called out as a forced deviation in the report.
      -> if the versions involved aren't plain dotted-numeric (e.g. they
         contain letters like "rc1" or "dev0"), the comparison can't be made
         confidently without a real version-parsing library -- flagged for
         manual review instead of guessing.

  - an exact pin in dev.yml (e.g. "numpy=1.24.3") that differs from
    Unified's version
      -> this is NOT automatically resolvable regardless of version format.
         Nothing in the file says whether the exact pin is an intentional
         "must be this version" requirement or just whatever conda happened
         to solve last time the file was regenerated. The original dev.yml
         spec is kept and the package is flagged for manual review.

  - not present in Unified at all
      -> left as-is (nothing to reconcile against).

This narrows -- but does not eliminate -- the dev-env-vs-Unified dependency
gap: even where versions are matched, conda and Unified's solver can still
resolve the same top-level pin to different transitive dependencies.

Usage:
    python pin_dev_env_to_unified.py \\
        --unified unified_versions.json \\
        --devyml /path/to/dev.yml \\
        --out-devyml pinned-dev.yml \\
        --out-report report.md \\
        --component e3sm_diags
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List


def normalize(name: str) -> str:
    return name.strip().lower().replace("_", "-")


# ---------------------------------------------------------------------------
# Loading Unified's resolved versions (JSON from get_unified_versions.sh, or
# plain-text table output as a fallback) -- stdlib json only, no yaml needed
# here since this is not a yaml file.
# ---------------------------------------------------------------------------


def parse_unified_json(path: Path) -> dict:
    data = json.loads(path.read_text())
    versions = {}
    if isinstance(data, dict):
        for key in ("packages", "data", "items"):
            if key in data and isinstance(data[key], list):
                data = data[key]
                break
    for entry in data:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name") or entry.get("Package") or entry.get("package")
        version = entry.get("version") or entry.get("Version")
        if name and version:
            versions[normalize(str(name))] = str(version)
    return versions


def parse_unified_text(path: Path) -> dict:
    """Fallback parser for `pixi list` / similar plain-text table output."""
    versions = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.lower().startswith("package"):
            continue
        if set(line) <= set("-+ "):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        name, version = parts[0], parts[1]
        if not re.match(r"^[A-Za-z0-9]", version):
            continue
        versions[normalize(name)] = version
    return versions


def load_unified_versions(path: Path) -> dict:
    if path.suffix == ".json":
        try:
            return parse_unified_json(path)
        except json.JSONDecodeError:
            pass
    return parse_unified_text(path)


# ---------------------------------------------------------------------------
# Minimal version comparison (stdlib only). Handles plain dotted-numeric
# versions (the vast majority of conda-forge packages: "1.26.4", "3.8.2",
# "2024.1.1", etc.). Anything else (letters, pre/post/dev suffixes, epochs)
# is deliberately NOT guessed at -- callers get None back and should treat
# that as "can't confidently determine", not as a pass/fail.
# ---------------------------------------------------------------------------


def parse_simple_version(v: str):
    parts = v.strip().split(".")
    try:
        return tuple(int(p) for p in parts)
    except ValueError:
        return None


def _compare_tuples(a: tuple, b: tuple) -> int:
    length = max(len(a), len(b))
    a = a + (0,) * (length - len(a))
    b = b + (0,) * (length - len(b))
    if a < b:
        return -1
    if a > b:
        return 1
    return 0


CLAUSE_RE = re.compile(r"(==|!=|>=|<=|>|<)\s*([^,]+)")


def check_constraint(unified_version: str, constraint: str):
    """
    Returns True/False if the constraint's clauses are all plain
    dotted-numeric and thus confidently comparable; returns None if any
    version involved can't be parsed that simply, meaning the caller should
    not treat this as a resolved answer.
    """
    uv = parse_simple_version(unified_version)
    if uv is None:
        return None
    clauses = CLAUSE_RE.findall(constraint)
    if not clauses:
        return None
    for op, verstr in clauses:
        cv = parse_simple_version(verstr.strip())
        if cv is None:
            return None
        cmp = _compare_tuples(uv, cv)
        if op == "==" and cmp != 0:
            return False
        if op == "!=" and cmp == 0:
            return False
        if op == ">=" and cmp < 0:
            return False
        if op == "<=" and cmp > 0:
            return False
        if op == ">" and cmp <= 0:
            return False
        if op == "<" and cmp >= 0:
            return False
    return True


# ---------------------------------------------------------------------------
# Parsing a single dev.yml dependency spec
# ---------------------------------------------------------------------------

NAME_RE = re.compile(r"^([A-Za-z0-9_.\-]+)\s*(.*)$")


def parse_dep_spec(spec: str):
    """
    Split a dependency spec into (name, kind, detail).

    kind is one of:
      'unconstrained' - bare package name, no version info      detail=None
      'exact'         - pinned to one exact version              detail=version string
      'range'         - a comparison constraint (>=, >, <=, <, !=, or a
                         comma-separated combination of these)    detail=constraint string
      'wildcard'      - a conda build-string selector where the version
                         itself is '*' (e.g. "esmf=*=mpi_mpich_*") -- this
                         is not a version pin at all, just a build-variant
                         selector, so there's nothing to compare against
                         Unified.                                 detail=raw remainder
      'unparseable'   - didn't match a recognized shape           detail=raw remainder
    """
    spec = spec.strip()
    m = NAME_RE.match(spec)
    if not m:
        return spec, "unparseable", None
    name, rest = m.group(1), m.group(2).strip()

    if not rest:
        return name, "unconstrained", None

    # Conda-style single '=' exact pin, possibly with a build string:
    # e.g. "numpy=1.24.3" or "numpy=1.24.3=py311h1234abc_0"
    if rest.startswith("=") and not rest.startswith("=="):
        version = rest[1:].split("=")[0].strip()
        if version == "*":
            # e.g. "esmf=*=mpi_mpich_*" -- selecting a build variant, not a
            # version. Nothing to compare against Unified here.
            return name, "wildcard", rest
        return name, "exact", version

    if rest.startswith("=="):
        version = rest[2:].split(",")[0].strip()
        return name, "exact", version

    if rest[0] in "<>!":
        return name, "range", rest

    return name, "unparseable", rest


# ---------------------------------------------------------------------------
# Resolving each package
# ---------------------------------------------------------------------------


def resolve_dependency(spec: str, unified_versions: dict, buckets: dict) -> str:
    """
    Decide what to do with one dependency spec string (no surrounding
    quotes/comments -- callers strip those). Appends a record to the
    appropriate list in `buckets` and returns the spec string to use in the
    output file (same as input if nothing changes).
    """
    name, kind, detail = parse_dep_spec(spec)
    key = normalize(name)
    unified_version = unified_versions.get(key)

    if unified_version is None:
        buckets["no_match"].append((name, spec))
        return spec

    if kind == "unconstrained":
        buckets["pinned"].append((name, spec, unified_version, None))
        return f"{name}={unified_version}"

    if kind == "exact":
        if detail == unified_version:
            buckets["pinned"].append((name, spec, unified_version, "already matched"))
            return f"{name}={unified_version}"
        buckets["flagged"].append(
            (
                name,
                spec,
                unified_version,
                f"dev.yml pins exactly {detail}; Unified has {unified_version}. "
                "Cannot tell from the file alone whether the exact pin is "
                "required -- kept dev.yml's version pending manual review.",
            )
        )
        return spec

    if kind == "range":
        satisfied = check_constraint(unified_version, detail)
        if satisfied is True:
            buckets["pinned"].append(
                (
                    name,
                    spec,
                    unified_version,
                    f"Unified's version satisfies dev.yml's constraint '{detail}'.",
                )
            )
            return f"{name}={unified_version}"
        elif satisfied is False:
            buckets["forced_deviation"].append(
                (
                    name,
                    spec,
                    unified_version,
                    f"Unified's version {unified_version} does NOT satisfy "
                    f"dev.yml's constraint '{detail}'. Kept dev.yml's own "
                    "constraint as a forced deviation.",
                )
            )
            return spec
        else:
            buckets["flagged"].append(
                (
                    name,
                    spec,
                    unified_version,
                    f"Could not confidently compare constraint '{detail}' against "
                    f"version '{unified_version}' (non-numeric version component) "
                    "-- kept dev.yml's spec pending manual review.",
                )
            )
            return spec

    if kind == "wildcard":
        buckets["flagged"].append(
            (
                name,
                spec,
                unified_version,
                f"'{detail}' is a build-string selector (version is '*'), not a "
                "version pin -- there's nothing to compare against Unified's "
                "version. Left as-is.",
            )
        )
        return spec

    # unparseable
    buckets["flagged"].append(
        (
            name,
            spec,
            unified_version,
            "Could not parse this dependency spec's format -- kept dev.yml's "
            "spec pending manual review.",
        )
    )
    return spec


# ---------------------------------------------------------------------------
# Line-based dev.yml editing (no YAML library). Only rewrites the version
# portion of dependency lines under the `dependencies:` key; every other
# line, and every comment, is passed through unchanged.
# ---------------------------------------------------------------------------

PIP_KEY_RE = re.compile(r"^pip\s*:\s*$")


def _line_indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _strip_quotes(s: str):
    """Return (unquoted, quote_char_or_None)."""
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "'\"":
        return s[1:-1], s[0]
    return s, None


def process_block(lines, start_idx, base_indent, unified_versions, buckets):
    """
    Process a YAML list block (the items of `dependencies:` or a nested
    `pip:` list) starting at start_idx, whose items are indented at
    base_indent. Returns (rewritten_lines, index_after_block).
    """
    out = []
    i = start_idx
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Blank lines and full-line comments (e.g. section-divider comments
        # like "# Base" / "# ===...===", or a commented-out dependency like
        # "# - somepkg 1.2.3") don't affect YAML structure -- pass them
        # through and keep scanning for the next real item rather than
        # treating them as the end of the list.
        if stripped == "" or stripped.startswith("#"):
            out.append(line)
            i += 1
            continue

        indent = _line_indent(line)
        if indent < base_indent or not stripped.startswith("-"):
            break

        item_text = stripped[1:].strip()

        if PIP_KEY_RE.match(item_text):
            out.append(line)
            i += 1
            # Skip/pass through any blank or comment-only lines before the
            # nested block.
            while i < len(lines) and (
                lines[i].strip() == "" or lines[i].strip().startswith("#")
            ):
                out.append(lines[i])
                i += 1
            if i < len(lines) and _line_indent(lines[i]) > base_indent:
                nested_out, i = process_block(
                    lines, i, _line_indent(lines[i]), unified_versions, buckets
                )
                out.extend(nested_out)
            continue

        # Plain dependency spec line. Split off an inline comment if present.
        comment = ""
        spec_text = item_text
        hash_idx = spec_text.find("#")
        if hash_idx != -1:
            comment = spec_text[hash_idx:]
            spec_text = spec_text[:hash_idx].strip()

        spec_text, quote_char = _strip_quotes(spec_text)
        new_spec = resolve_dependency(spec_text, unified_versions, buckets)

        dash_pos = line.index("-")
        prefix = line[: dash_pos + 1]  # leading whitespace + '-'
        rendered_spec = (
            f"{quote_char}{new_spec}{quote_char}" if quote_char else new_spec
        )
        rebuilt = f"{prefix} {rendered_spec}"
        if comment:
            rebuilt += f"  {comment}"
        out.append(rebuilt)
        i += 1

    return out, i


DEPENDENCIES_KEY_RE = re.compile(r"^dependencies\s*:\s*$")


def process_devyml_text(text: str, unified_versions: dict, buckets: dict) -> str:
    had_trailing_newline = text.endswith("\n")
    lines = text.splitlines()

    dep_idx = None
    for idx, line in enumerate(lines):
        if _line_indent(line) == 0 and DEPENDENCIES_KEY_RE.match(line.strip()):
            dep_idx = idx
            break
    if dep_idx is None:
        raise ValueError("Could not find a top-level 'dependencies:' key in this file.")

    # Find the indentation of the first list item after the key, skipping
    # any blank or comment-only lines (e.g. a "# Base" section-divider
    # comment right after "dependencies:").
    j = dep_idx + 1
    while j < len(lines) and (
        lines[j].strip() == "" or lines[j].strip().startswith("#")
    ):
        j += 1
    if j >= len(lines) or not lines[j].strip().startswith("-"):
        raise ValueError("'dependencies:' key has no list items after it.")
    base_indent = _line_indent(lines[j])

    body, end_idx = process_block(lines, j, base_indent, unified_versions, buckets)

    # lines[:j] includes the 'dependencies:' line itself plus any blank/
    # comment lines we skipped over while locating the first real item
    # (e.g. a "# Base" section-divider comment) -- keep them.
    new_lines = lines[:j] + body + lines[end_idx:]
    result = "\n".join(new_lines)
    if had_trailing_newline:
        result += "\n"
    return result


def process_flat_spec_text(text: str, unified_versions: dict, buckets: dict) -> str:
    """
    Handle the other real dev-env format in use here: a plain spec-list file
    consumed via `conda create --file dev-spec.txt` (as MPAS-Analysis does).
    One package spec per line, comment lines start with '#', operators are
    typically space-separated from the name (e.g. "python >=3.11"). No YAML
    structure at all -- just rewrite each non-comment, non-blank line in
    place.
    """
    had_trailing_newline = text.endswith("\n")
    lines = text.splitlines()
    out = []
    for line in lines:
        stripped = line.strip()
        if stripped == "" or stripped.startswith("#"):
            out.append(line)
            continue

        indent_len = len(line) - len(line.lstrip(" "))
        leading_ws = line[:indent_len]
        content = line[indent_len:]

        comment = ""
        hash_idx = content.find("#")
        if hash_idx != -1:
            comment = content[hash_idx:]
            content = content[:hash_idx].rstrip()

        new_spec = resolve_dependency(content.strip(), unified_versions, buckets)
        rebuilt = f"{leading_ws}{new_spec}"
        if comment:
            rebuilt += f"  {comment}"
        out.append(rebuilt)

    result = "\n".join(out)
    if had_trailing_newline:
        result += "\n"
    return result


def process_env_file_text(text: str, unified_versions: dict, buckets: dict) -> str:
    """
    Dispatch to the right format handler. The two dev-env formats actually
    in use here are a YAML `dependencies:` list (dev.yml, conda/dev.yml,
    conda-env/dev.yml) and a flat one-spec-per-line file consumed via
    `conda create --file ...` (dev-spec.txt). Detect which one this is by
    checking for a top-level `dependencies:` key.
    """
    lines = text.splitlines()
    has_dependencies_key = any(
        _line_indent(line) == 0 and DEPENDENCIES_KEY_RE.match(line.strip())
        for line in lines
    )
    if has_dependencies_key:
        return process_devyml_text(text, unified_versions, buckets)
    return process_flat_spec_text(text, unified_versions, buckets)


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def build_report(component: str, buckets: dict, unified_versions: dict) -> str:
    handled_keys = {
        normalize(n)
        for group in ("pinned", "forced_deviation", "flagged")
        for (n, *_rest) in buckets[group]
    }
    no_match_keys = {normalize(n) for n, _ in buckets["no_match"]}
    unified_only = sorted(set(unified_versions) - handled_keys - no_match_keys)

    lines = [f"# Dev-env vs Unified version pinning report: {component}", ""]

    lines.append("## Pinned to Unified's version (no conflict)")
    lines.append("")
    lines.append("| Package | Original dev.yml spec | Unified version | Note |")
    lines.append("| --- | --- | --- | --- |")
    for name, spec, uv, note in sorted(buckets["pinned"]):
        lines.append(f"| {name} | {spec} | {uv} | {note or ''} |")
    if not buckets["pinned"]:
        lines.append("| _(none)_ | | | |")
    lines.append("")

    lines.append(
        "## Forced deviations (Unified's version fails dev.yml's own constraint)"
    )
    lines.append("")
    lines.append(
        "These are kept at dev.yml's spec automatically -- dev.yml's own "
        "range constraint rules out Unified's version, so this isn't a "
        "guess."
    )
    lines.append("")
    lines.append("| Package | Original dev.yml spec | Unified version | Why |")
    lines.append("| --- | --- | --- | --- |")
    for name, spec, uv, note in sorted(buckets["forced_deviation"]):
        lines.append(f"| {name} | {spec} | {uv} | {note} |")
    if not buckets["forced_deviation"]:
        lines.append("| _(none)_ | | | |")
    lines.append("")

    lines.append("## Flagged for manual review (ambiguous -- please check by hand)")
    lines.append("")
    lines.append(
        "Either an exact pin that differs from Unified's version (file alone "
        "can't say whether that's intentional), or a version comparison that "
        "couldn't be made confidently without a full version-parsing library "
        "(e.g. a non-numeric version like a pre/dev release). Decide by hand, "
        "then edit the pinned file directly if needed."
    )
    lines.append("")
    lines.append("| Package | Original dev.yml spec | Unified version | Why |")
    lines.append("| --- | --- | --- | --- |")
    for name, spec, uv, note in sorted(buckets["flagged"]):
        lines.append(f"| {name} | {spec} | {uv} | {note} |")
    if not buckets["flagged"]:
        lines.append("| _(none)_ | | | |")
    lines.append("")

    lines.append("## Left as-is (in dev.yml, not found in Unified)")
    lines.append("")
    lines.append("| Package | Original dev.yml spec |")
    lines.append("| --- | --- |")
    for name, spec in sorted(buckets["no_match"]):
        lines.append(f"| {name} | {spec} |")
    if not buckets["no_match"]:
        lines.append("| _(none)_ | |")
    lines.append("")

    lines.append("## In Unified but not in dev.yml (informational only, not acted on)")
    lines.append("")
    lines.append(", ".join(unified_only) if unified_only else "(none)")
    lines.append("")

    lines.append(
        "**Caveat:** matching shared top-level packages by version does not "
        "guarantee identical transitive dependencies -- conda and Unified's "
        "solver can resolve the same top-level pin to different "
        "sub-dependencies or builds. This narrows the dev-vs-Unified gap, "
        "it does not eliminate it."
    )

    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--unified",
        required=True,
        type=Path,
        help="Output file from get_unified_versions.sh (.json or .txt)",
    )
    ap.add_argument(
        "--devyml",
        required=True,
        type=Path,
        help="Path to the component's dev.yml / dev-spec.txt",
    )
    ap.add_argument(
        "--out-devyml",
        required=True,
        type=Path,
        help="Where to write the resolved copy",
    )
    ap.add_argument(
        "--out-report",
        required=True,
        type=Path,
        help="Where to write the Markdown report",
    )
    ap.add_argument(
        "--component",
        default="component",
        help="Name for the report header (e.g. e3sm_diags)",
    )
    args = ap.parse_args()

    unified_versions = load_unified_versions(args.unified)
    if not unified_versions:
        sys.exit(f"Could not parse any package versions from {args.unified}")

    buckets: Dict[str, List[Any]] = {
        "pinned": [],
        "forced_deviation": [],
        "flagged": [],
        "no_match": [],
    }

    original_text = args.devyml.read_text()
    try:
        new_text = process_env_file_text(original_text, unified_versions, buckets)
    except ValueError as e:
        sys.exit(f"Could not process {args.devyml}: {e}")

    header = (
        "# Lines below were resolved by pin_dev_env_to_unified.py.\n"
        "# Packages with no conflicting dev.yml constraint were pinned to\n"
        "# Unified's resolved version. Packages where dev.yml's own\n"
        "# constraint rules out Unified's version, or where an exact pin's\n"
        "# intent is ambiguous, were left as-is -- see the report for which\n"
        "# ones need a manual look. All other lines/comments are untouched.\n"
    )
    args.out_devyml.write_text(header + new_text)

    report = build_report(args.component, buckets, unified_versions)
    args.out_report.write_text(report)

    print(f"Pinned to Unified:         {len(buckets['pinned'])}")
    print(f"Forced deviations:         {len(buckets['forced_deviation'])}")
    print(f"Flagged for manual review: {len(buckets['flagged'])}")
    print(f"No Unified match:          {len(buckets['no_match'])}")
    print(f"Wrote resolved dev env file -> {args.out_devyml}")
    print(f"Wrote report                -> {args.out_report}")


if __name__ == "__main__":
    main()
