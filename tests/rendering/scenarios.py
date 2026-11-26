"""Render zppy's scripts for fixed scenarios, without an HPC machine.

Each scenario runs zppy's own task functions in `dry_run` mode on a
configuration file in this directory, using fixed, made-up machine information
in place of mache. `tests/test_rendered_scripts.py` compares the results with
the snapshots in `snapshots/`, and other tests use them to check specific
behavior of the rendered scripts.
"""

import ast
import configparser
import functools
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

from configobj import ConfigObj
from validate import Validator

from zppy.__main__ import _determine_parameters, _launch_scripts

REPO_ROOT = Path(__file__).resolve().parents[2]
RENDERING_DIR = REPO_ROOT / "tests" / "rendering"
SNAPSHOT_DIR = RENDERING_DIR / "snapshots"
# Render the templates in this working tree, not those of an installed zppy.
TEMPLATE_DIR = REPO_ROOT / "zppy" / "templates"
DEFAULT_INI = REPO_ROOT / "zppy" / "defaults" / "default.ini"

# The temporary directory each scenario runs in is written as this path in
# the rendered files, so that they do not depend on where the tests run.
PLACEHOLDER_ROOT = "/zppy_snapshot"
DEPENDENCIES_FILE = "dependencies.json"
# Files zppy renders into the scripts directory
RENDERED_PATTERNS = ["*.bash", "*.py", "*.cfg"]


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


# Paths match those in mache's machine config files, so the rendered scripts
# look like the scripts zppy generates on each machine.
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
SCENARIOS_BY_NAME: Dict[str, Scenario] = {s.name: s for s in SCENARIOS}


def render_scenario(scenario: Scenario) -> Dict[str, str]:
    """Return the rendered files and dependency manifest by file name.

    The rendered files are the job scripts (`.bash`) and the files zppy writes
    next to them for the jobs to use (`.py` and `.cfg`).

    Each scenario is rendered only once per test session.
    """
    return dict(_render_scenario(scenario))


def read_dependencies(files: Dict[str, str]) -> Dict[str, List[str]]:
    """Return each job's dependencies from a scenario's rendered files."""
    return json.loads(files[DEPENDENCIES_FILE])


def bash_scripts(files: Dict[str, str]) -> Dict[str, str]:
    """Return only the rendered `.bash` files."""
    return {name: text for name, text in files.items() if name.endswith(".bash")}


@functools.lru_cache(maxsize=None)
def _render_scenario(scenario: Scenario) -> Dict[str, str]:
    with tempfile.TemporaryDirectory() as work_dir:
        return _render_in(scenario, Path(work_dir))


def _render_in(scenario: Scenario, work_dir: Path) -> Dict[str, str]:
    # Resolve symlinks (e.g. /var -> /private/var on macOS) so that every path
    # zppy derives from `output` starts with `root`.
    root = work_dir.resolve()
    config = ConfigObj(str(RENDERING_DIR / scenario.cfg), configspec=str(DEFAULT_INI))
    validation = config.validate(Validator())
    if validation is not True:
        raise ValueError(f"{scenario.cfg} failed validation: {validation}")

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
    for pattern in RENDERED_PATTERNS:
        for rendered in sorted(script_dir.glob(pattern)):
            files[rendered.name] = _normalize(rendered.read_text(), root)
    files[DEPENDENCIES_FILE] = _dependency_manifest(script_dir, root)
    return files


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
