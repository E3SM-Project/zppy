"""Machine profiles, repository specifications, and defaults for complete runs."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List, Tuple

from tests.integration.weekly_cfgs import (  # noqa: F401 - re-exported
    WEEKLY_CFGS,
    case_name_for_cfg,
)

# The pytest files run during the validate stage, in the documented order. The
# image checker is excluded; it needs a compute node and is submitted separately.
INTEGRATION_TEST_FILES: Tuple[str, ...] = (
    "tests/integration/test_last_year.py",
    "tests/integration/test_bash_generation.py",
    "tests/integration/test_campaign.py",
    "tests/integration/test_defaults.py",
    "tests/integration/test_bundles.py",
)

# "Tests of the tests" -- the unit tests covering the image checker itself.
IMAGE_HELPER_TEST_FILES: Tuple[str, ...] = (
    "tests/images/test_image_checker.py",
    "tests/images/test_image_severity.py",
)

DEFAULT_CFGS_TO_RUN: Tuple[str, ...] = tuple(cfg.name for cfg in WEEKLY_CFGS)

DEFAULT_TASKS_TO_RUN: Tuple[str, ...] = (
    "e3sm_diags",
    "mpas_analysis",
    "global_time_series",
    "ilamb",
    "livvkit",
    "pcmdi_diags",
)


@dataclass(frozen=True)
class MachineProfile:
    """Per-machine settings that the complete run cannot derive from mache."""

    name: str
    # Per-user scratch space for a run's intermediate data: worktrees and
    # zppy's post-processing output. "{initial}" is the username's first letter,
    # for Perlmutter's /pscratch/sd/<initial>/<user> layout.
    scratch_template: str
    conda_activation_cmd: str
    unified_env_cmd: str
    # Directives appended to the image-checker batch script. These mirror the
    # `salloc` command documented for running the image checker by hand. The
    # account comes from the command line, not from here.
    sbatch_directives: Tuple[str, ...]
    # Generated cfg files are suffixed with this, which is not always the
    # machine name: Perlmutter's cfgs are suffixed "pm-cpu".
    cfg_suffix: str

    def scratch_workspace(self, username: str) -> str:
        """Return the user's scratch directory on this machine."""
        return self.scratch_template.format(username=username, initial=username[:1])


MACHINE_PROFILES: Dict[str, MachineProfile] = {
    "chrysalis": MachineProfile(
        name="chrysalis",
        scratch_template="/lcrc/globalscratch/{username}",
        conda_activation_cmd="lcrc_conda",
        unified_env_cmd=(
            "source /lcrc/soft/climate/e3sm-unified/"
            "load_latest_e3sm_unified_chrysalis.sh"
        ),
        sbatch_directives=(
            "#SBATCH --partition=debug",
            "#SBATCH --time=02:00:00",
        ),
        cfg_suffix="chrysalis",
    ),
    "compy": MachineProfile(
        name="compy",
        # Compy has no separate global scratch filesystem.
        scratch_template="/compyfs/{username}",
        conda_activation_cmd="compy_conda",
        unified_env_cmd=(
            "source /share/apps/E3SM/conda_envs/load_latest_e3sm_unified_compy.sh"
        ),
        sbatch_directives=(
            "#SBATCH --partition=short",
            "#SBATCH --time=01:00:00",
        ),
        cfg_suffix="compy",
    ),
    "perlmutter": MachineProfile(
        name="perlmutter",
        scratch_template="/pscratch/sd/{initial}/{username}",
        conda_activation_cmd="nersc_conda",
        unified_env_cmd=(
            "source /global/common/software/e3sm/anaconda_envs/"
            "load_latest_e3sm_unified_pm-cpu.sh"
        ),
        sbatch_directives=(
            "#SBATCH --qos=debug",
            "#SBATCH --time=01:00:00",
            "#SBATCH --constraint=cpu",
        ),
        cfg_suffix="pm-cpu",
    ),
}


@dataclass(frozen=True)
class RepoSpec:
    """One repository the complete run builds an environment from."""

    # Key used in config, status.json, and the report.
    name: str
    # Branch considered "official" upstream for this repository.
    default_branch: str
    # Directory holding dev.yml, relative to the repo root. "none" means the
    # repo pins its environment with dev-spec.txt instead (MPAS-Analysis).
    conda_dir: str
    # zppy tasks whose environment_commands point at this repo's environment.
    # zppy itself owns no task, since zppy is what launches them.
    tasks: Tuple[str, ...] = ()
    # The clone's directory name, when it differs from ``name``.
    directory: str = ""

    @property
    def clone_dirname(self) -> str:
        """Return the directory the clone lives in under the repo root."""
        return self.directory or self.name

    @property
    def uses_dev_spec(self) -> bool:
        """Whether the environment comes from dev-spec.txt rather than dev.yml."""
        return self.conda_dir == "none"

    def env_file(self) -> str:
        """Return the environment file path, relative to the repo root."""
        if self.uses_dev_spec:
            return "dev-spec.txt"
        return f"{self.conda_dir}/dev.yml"


REPO_SPECS: Tuple[RepoSpec, ...] = (
    RepoSpec(
        name="e3sm_to_cmip",
        default_branch="master",
        conda_dir="conda-env",
        tasks=("e3sm_to_cmip",),
    ),
    RepoSpec(
        name="e3sm_diags",
        default_branch="main",
        conda_dir="conda-env",
        tasks=("e3sm_diags",),
    ),
    RepoSpec(
        name="mpas_analysis",
        default_branch="develop",
        conda_dir="none",
        tasks=("mpas_analysis",),
        directory="MPAS-Analysis",
    ),
    RepoSpec(
        name="zppy_interfaces",
        default_branch="main",
        conda_dir="conda",
        tasks=("global_time_series", "pcmdi_diags"),
        directory="zppy-interfaces",
    ),
    RepoSpec(
        name="zppy",
        default_branch="main",
        conda_dir="conda",
    ),
)

REPO_SPECS_BY_NAME: Dict[str, RepoSpec] = {spec.name: spec for spec in REPO_SPECS}

# Tasks run from the E3SM-Unified environment rather than a dev environment.
UNIFIED_ONLY_TASKS: Tuple[str, ...] = ("livvkit",)

# Display names for packages with no repository in the run: their tasks always
# come from E3SM-Unified.
_UNIFIED_PACKAGES: Dict[str, str] = {"ilamb": "ILAMB", "livvkit": "LIVVkit"}


def repo_for_task(task: str) -> RepoSpec | None:
    """Return the repository whose environment a task runs in, if any."""
    for spec in REPO_SPECS:
        if task in spec.tasks:
            return spec
    return None


def package_for_task(task: str) -> str:
    """Return the package that produces a task's plots, for display."""
    spec = repo_for_task(task)
    if spec is not None:
        return spec.clone_dirname
    return _UNIFIED_PACKAGES.get(task, task)


def generated_cfg_path(zppy_worktree: str, cfg: str, cfg_suffix: str) -> str:
    """Return where cfg generation writes a machine-specific cfg."""
    return os.path.join(
        zppy_worktree,
        "tests",
        "integration",
        "generated",
        f"test_{cfg}_{cfg_suffix}.cfg",
    )


def is_bundles_cfg(cfg: str) -> bool:
    """Whether a cfg is a bundles cfg, which must be submitted twice."""
    return "bundle" in cfg


def resolve_machine(name: str) -> MachineProfile:
    """Look up a machine profile, raising a helpful error for a bad name."""
    try:
        return MACHINE_PROFILES[name]
    except KeyError:
        valid: List[str] = sorted(MACHINE_PROFILES)
        raise ValueError(
            f"Unknown machine={name}. Valid values: {' | '.join(valid)}"
        ) from None
