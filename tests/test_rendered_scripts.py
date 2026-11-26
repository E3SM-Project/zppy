"""Snapshot tests for the scripts that zppy renders from its templates.

Each scenario below runs zppy's own task functions in `dry_run` mode on a
configuration file in `tests/rendering/`, using fixed, made-up machine
information instead of mache. The rendered `.bash` files, plus a manifest of
each job's dependencies, are compared with the snapshots checked into
`tests/rendering/snapshots/<scenario>/`.

Nothing here needs an HPC machine, so template changes can be checked locally
and in CI. When a change to the rendered scripts is intended, regenerate the
snapshots and review the result with `git diff`:

    ZPPY_UPDATE_SNAPSHOTS=1 pytest tests/test_rendered_scripts.py
    git diff tests/rendering/snapshots
"""

import ast
import configparser
import difflib
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from unittest.mock import MagicMock

import pytest
from configobj import ConfigObj
from validate import Validator

from zppy.__main__ import _determine_parameters, _launch_scripts

REPO_ROOT = Path(__file__).resolve().parent.parent
RENDERING_DIR = REPO_ROOT / "tests" / "rendering"
SNAPSHOT_DIR = RENDERING_DIR / "snapshots"
TEMPLATE_DIR = REPO_ROOT / "zppy" / "templates"
DEFAULT_INI = REPO_ROOT / "zppy" / "defaults" / "default.ini"

UPDATE_ENV_VAR = "ZPPY_UPDATE_SNAPSHOTS"
# The temporary directory each scenario runs in is written as this path in
# the snapshots, so that they do not depend on where the tests run.
PLACEHOLDER_ROOT = "/zppy_snapshot"
DEPENDENCIES_FILE = "dependencies.json"
# The maximum number of diff lines to show for each file that differs.
MAX_DIFF_LINES = 60

UPDATE_HINT = (
    "If this change to the rendered scripts is intended, regenerate the "
    f"snapshots with `{UPDATE_ENV_VAR}=1 pytest tests/test_rendered_scripts.py` "
    "and review them with `git diff tests/rendering/snapshots`."
)


@dataclass(frozen=True)
class FakeMachine:
    """Stand-in for the values zppy normally gets from mache."""

    name: str
    account: str
    partition: str
    constraint: str
    unified_base_path: str
    diagnostics_base_path: str
    web_portal_base_path: str
    web_portal_base_url: str


# Paths match those in mache's machine config files, so the snapshots look like
# the scripts zppy generates on each machine.
MACHINES: Dict[str, FakeMachine] = {
    "chrysalis": FakeMachine(
        name="chrysalis",
        account="e3sm",
        partition="compute",
        constraint="",
        unified_base_path="/lcrc/soft/climate/e3sm-unified",
        diagnostics_base_path="/lcrc/group/e3sm/diagnostics",
        web_portal_base_path="/lcrc/group/e3sm/public_html/diagnostic_output",
        web_portal_base_url="https://web.lcrc.anl.gov/public/e3sm/diagnostic_output",
    ),
    "compy": FakeMachine(
        name="compy",
        account="e3sm",
        partition="slurm",
        constraint="",
        unified_base_path="/share/apps/E3SM/conda_envs",
        diagnostics_base_path="/compyfs/diagnostics",
        web_portal_base_path="/compyfs/www",
        web_portal_base_url="https://compy-dtn.pnl.gov",
    ),
    "dane": FakeMachine(
        name="dane",
        account="e3sm",
        partition="pbatch",
        constraint="",
        unified_base_path="/usr/workspace/e3sm/apps/e3sm-unified",
        diagnostics_base_path="/usr/workspace/e3sm/data/diagnostics",
        web_portal_base_path="/usr/global/web-pages/lc/www/e3sm/diagnostic_output",
        web_portal_base_url="https://lc.llnl.gov/e3sm/diagnostic_output",
    ),
    "pm-cpu": FakeMachine(
        name="pm-cpu",
        account="e3sm",
        partition="",
        constraint="cpu",
        unified_base_path="/global/common/software/e3sm/anaconda_envs",
        diagnostics_base_path="/global/cfs/cdirs/e3sm/diagnostics",
        web_portal_base_path="/global/cfs/cdirs/e3sm/www",
        web_portal_base_url="https://portal.nersc.gov/cfs/e3sm",
    ),
}


@dataclass(frozen=True)
class Scenario:
    """A configuration file rendered as if zppy were run on a given machine."""

    name: str
    cfg: str
    machine: str
    last_year: Optional[int] = None


SCENARIOS: List[Scenario] = [
    Scenario("comprehensive_chrysalis", "comprehensive.cfg", "chrysalis"),
    Scenario("machines_compy", "machines.cfg", "compy"),
    Scenario("machines_dane", "machines.cfg", "dane"),
    Scenario("machines_pm-cpu", "machines.cfg", "pm-cpu"),
    Scenario("last_year_chrysalis", "last_year.cfg", "chrysalis", last_year=1986),
]

# Python files written by a heredoc in a rendered script, e.g. `e3sm.py`.
PYTHON_HEREDOC = re.compile(
    r"^cat > (?P<name>\S+\.py) << EOF\n(?P<body>.*?)^EOF$", re.MULTILINE | re.DOTALL
)
# MPAS-Analysis config files written by a heredoc in a rendered script.
MPAS_ANALYSIS_CFG_HEREDOC = re.compile(
    r"^cat > (?P<name>\S*mpas_analysis_\S+\.cfg) << EOF\n(?P<body>.*?)^EOF$",
    re.MULTILINE | re.DOTALL,
)


def _fake_machine_info(machine: FakeMachine) -> MagicMock:
    config = configparser.ConfigParser()
    config["e3sm_unified"] = {"base_path": machine.unified_base_path}
    config["diagnostics"] = {"base_path": machine.diagnostics_base_path}
    config["web_portal"] = {
        "base_path": machine.web_portal_base_path,
        "base_url": machine.web_portal_base_url,
    }
    machine_info = MagicMock()
    machine_info.machine = machine.name
    machine_info.config = config
    machine_info.get_account_defaults.return_value = (
        machine.account,
        machine.partition,
        machine.constraint,
        None,
    )
    return machine_info


def _normalize(text: str, root: Path) -> str:
    return text.replace(str(root), PLACEHOLDER_ROOT)


def _read_task_settings(settings_file: Path) -> Dict[str, Any]:
    # A `.settings` file holds the pretty-printed task dictionary followed by
    # the pretty-printed year set, so the first expression is the dictionary.
    module = ast.parse(settings_file.read_text())
    first = module.body[0]
    if not isinstance(first, ast.Expr):
        raise ValueError(f"Unexpected contents in {settings_file}")
    task_settings = ast.literal_eval(first.value)
    if not isinstance(task_settings, dict):
        raise ValueError(f"Unexpected contents in {settings_file}")
    return task_settings


def _dependency_manifest(script_dir: Path, root: Path) -> str:
    manifest: Dict[str, List[str]] = {}
    for settings_file in sorted(script_dir.glob("*.settings")):
        dependencies: List[str] = _read_task_settings(settings_file).get(
            "dependencies", []
        )
        entries: List[str] = []
        for dependency in dependencies:
            if os.path.dirname(dependency) == str(script_dir):
                entries.append(os.path.basename(dependency))
            else:
                entries.append(_normalize(dependency, root))
        manifest[settings_file.stem] = entries
    return json.dumps(manifest, indent=2, sort_keys=True) + "\n"


def _render_scenario(scenario: Scenario, work_dir: Path) -> Dict[str, str]:
    """Render a scenario and return the snapshot contents by file name."""
    # Resolve symlinks (e.g. /var -> /private/var on macOS) so that every path
    # zppy derives from `output` starts with `root`.
    root = work_dir.resolve()
    config = ConfigObj(str(RENDERING_DIR / scenario.cfg), configspec=str(DEFAULT_INI))
    validation = config.validate(Validator())
    assert validation is True, f"{scenario.cfg} failed validation: {validation}"

    output = root / "output"
    config["default"]["output"] = str(output)
    config["default"]["templateDir"] = str(TEMPLATE_DIR)
    config = _determine_parameters(
        _fake_machine_info(MACHINES[scenario.machine]), config
    )
    if scenario.last_year is not None:
        config["default"]["last_year"] = scenario.last_year

    script_dir = output / "post" / "scripts"
    script_dir.mkdir(parents=True)
    _launch_scripts(config, str(script_dir), str(script_dir / "jobids.txt"), [])

    files: Dict[str, str] = {}
    for script in sorted(script_dir.glob("*.bash")):
        files[script.name] = _normalize(script.read_text(), root)
    files[DEPENDENCIES_FILE] = _dependency_manifest(script_dir, root)
    return files


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


@pytest.fixture(scope="module")
def render(
    tmp_path_factory: pytest.TempPathFactory,
) -> Callable[[Scenario], Dict[str, str]]:
    """Render each scenario at most once per test module."""
    cache: Dict[str, Dict[str, str]] = {}

    def _render(scenario: Scenario) -> Dict[str, str]:
        if scenario.name not in cache:
            work_dir = tmp_path_factory.mktemp(scenario.name)
            cache[scenario.name] = _render_scenario(scenario, work_dir)
        return cache[scenario.name]

    return _render


def _bash_scripts(files: Dict[str, str]) -> Dict[str, str]:
    return {name: text for name, text in files.items() if name.endswith(".bash")}


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.name)
def test_rendered_scripts_match_snapshots(
    scenario: Scenario, render: Callable[[Scenario], Dict[str, str]]
) -> None:
    actual = render(scenario)
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
def test_rendered_scripts_are_valid_bash(
    scenario: Scenario, render: Callable[[Scenario], Dict[str, str]]
) -> None:
    failures: List[str] = []
    for name, text in _bash_scripts(render(scenario)).items():
        result = subprocess.run(
            ["bash", "-n"], input=text, capture_output=True, text=True
        )
        if result.returncode != 0:
            failures.append(f"{name}:\n{result.stderr}")
    assert not failures, "\n".join(failures)


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.name)
def test_embedded_python_compiles(
    scenario: Scenario, render: Callable[[Scenario], Dict[str, str]]
) -> None:
    # Bash expands `${...}` in these heredocs when the job runs, but zppy only
    # places such expansions inside Python string literals, so the rendered
    # text must already be valid Python.
    failures: List[str] = []
    for name, text in _bash_scripts(render(scenario)).items():
        for match in PYTHON_HEREDOC.finditer(text):
            try:
                compile(match.group("body"), f"{name}:{match.group('name')}", "exec")
            except SyntaxError as error:
                failures.append(f"{name}: {match.group('name')}: {error}")
    assert not failures, "\n".join(failures)


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.name)
def test_mpas_analysis_config_parses(
    scenario: Scenario, render: Callable[[Scenario], Dict[str, str]]
) -> None:
    failures: List[str] = []
    for name, text in _bash_scripts(render(scenario)).items():
        for match in MPAS_ANALYSIS_CFG_HEREDOC.finditer(text):
            parser = configparser.ConfigParser(interpolation=None, strict=True)
            try:
                parser.read_string(match.group("body"))
            except configparser.Error as error:
                failures.append(f"{name}: {match.group('name')}: {error}")
    assert not failures, "\n".join(failures)
