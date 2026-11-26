"""Snapshot tests for the scripts that zppy renders from its templates.

The scenarios in `tests/rendering/scenarios.py` render every task's scripts
without an HPC machine. The rendered `.bash` files, plus a manifest of each
job's dependencies, are compared with the snapshots checked into
`tests/rendering/snapshots/<scenario>/`, so template changes can be checked
locally and in CI. When a change to the rendered scripts is intended,
regenerate the snapshots and review the result with `git diff`:

    ZPPY_UPDATE_SNAPSHOTS=1 pytest tests/test_rendered_scripts.py
    git diff tests/rendering/snapshots
"""

import configparser
import difflib
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List

import pytest

from tests.rendering.scenarios import (
    SCENARIOS,
    SNAPSHOT_DIR,
    Scenario,
    bash_scripts,
    render_scenario,
)

UPDATE_ENV_VAR = "ZPPY_UPDATE_SNAPSHOTS"
# The maximum number of diff lines to show for each file that differs.
MAX_DIFF_LINES = 60

UPDATE_HINT = (
    "If this change to the rendered scripts is intended, regenerate the "
    f"snapshots with `{UPDATE_ENV_VAR}=1 pytest tests/test_rendered_scripts.py` "
    "and review them with `git diff tests/rendering/snapshots`."
)

# Python files written by a heredoc in a rendered script, e.g. `parameterfile.py`.
PYTHON_HEREDOC = re.compile(
    r"^cat > (?P<name>\S+\.py) << EOF\n(?P<body>.*?)^EOF$", re.MULTILINE | re.DOTALL
)


def _read_snapshots(snapshot_dir: Path) -> Dict[str, str]:
    if not snapshot_dir.is_dir():
        return {}
    return {path.name: path.read_text() for path in sorted(snapshot_dir.iterdir())}


def _write_snapshots(snapshot_dir: Path, files: Dict[str, str]) -> None:
    # Start from an empty directory so snapshots of jobs that are no longer
    # generated are removed.
    if snapshot_dir.exists():
        shutil.rmtree(snapshot_dir)
    snapshot_dir.mkdir(parents=True)
    for name, text in files.items():
        (snapshot_dir / name).write_text(text)


def _compare(expected: Dict[str, str], actual: Dict[str, str]) -> List[str]:
    problems: List[str] = []
    for name in sorted(set(expected) - set(actual)):
        problems.append(f"{name}: in the snapshots but no longer generated")
    for name in sorted(set(actual) - set(expected)):
        problems.append(f"{name}: generated but not in the snapshots")
    for name in sorted(set(expected) & set(actual)):
        if expected[name] == actual[name]:
            continue
        diff = list(
            difflib.unified_diff(
                expected[name].splitlines(),
                actual[name].splitlines(),
                fromfile=f"snapshot/{name}",
                tofile=f"rendered/{name}",
                lineterm="",
            )
        )
        if len(diff) > MAX_DIFF_LINES:
            omitted = len(diff) - MAX_DIFF_LINES
            diff = diff[:MAX_DIFF_LINES] + [f"... ({omitted} more diff lines)"]
        problems.append(f"{name}: differs from the snapshot\n" + "\n".join(diff))
    return problems


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.name)
def test_rendered_scripts_match_snapshots(scenario: Scenario) -> None:
    actual = render_scenario(scenario)
    snapshot_dir = SNAPSHOT_DIR / scenario.name
    if os.environ.get(UPDATE_ENV_VAR):
        _write_snapshots(snapshot_dir, actual)
        return
    problems = _compare(_read_snapshots(snapshot_dir), actual)
    assert not problems, "\n\n".join(problems + [UPDATE_HINT])


def test_no_stale_snapshot_directories() -> None:
    scenario_names = {scenario.name for scenario in SCENARIOS}
    snapshot_dirs = (
        {path.name for path in SNAPSHOT_DIR.iterdir() if path.is_dir()}
        if SNAPSHOT_DIR.is_dir()
        else set()
    )
    stale = sorted(snapshot_dirs - scenario_names)
    if os.environ.get(UPDATE_ENV_VAR):
        for name in stale:
            shutil.rmtree(SNAPSHOT_DIR / name)
        return
    assert not stale, f"Snapshot directories without a scenario: {stale}"


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash is not available")
@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.name)
def test_rendered_scripts_are_valid_bash(scenario: Scenario) -> None:
    failures: List[str] = []
    for name, text in bash_scripts(render_scenario(scenario)).items():
        result = subprocess.run(
            ["bash", "-n"], input=text, capture_output=True, text=True
        )
        if result.returncode != 0:
            failures.append(f"{name}:\n{result.stderr}")
    assert not failures, "\n".join(failures)


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.name)
def test_python_files_compile(scenario: Scenario) -> None:
    files = render_scenario(scenario)
    failures: List[str] = []
    for name, text in files.items():
        if not name.endswith(".py"):
            continue
        try:
            compile(text, name, "exec")
        except SyntaxError as error:
            failures.append(f"{name}: {error}")
    # Bash expands `${...}` in these heredocs when the job runs, but zppy only
    # places such expansions inside Python string literals, so the rendered
    # text must already be valid Python.
    for name, text in bash_scripts(files).items():
        for match in PYTHON_HEREDOC.finditer(text):
            try:
                compile(match.group("body"), f"{name}:{match.group('name')}", "exec")
            except SyntaxError as error:
                failures.append(f"{name}: {match.group('name')}: {error}")
    assert not failures, "\n".join(failures)


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.name)
def test_mpas_analysis_config_parses(scenario: Scenario) -> None:
    failures: List[str] = []
    for name, text in render_scenario(scenario).items():
        if not (name.startswith("mpas_analysis_") and name.endswith(".cfg")):
            continue
        parser = configparser.ConfigParser(interpolation=None, strict=True)
        try:
            parser.read_string(text)
        except configparser.Error as error:
            failures.append(f"{name}: {error}")
    assert not failures, "\n".join(failures)
