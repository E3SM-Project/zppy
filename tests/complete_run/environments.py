"""Conda environments for the complete run test.

Each repository under test gets its own environment, built from that
repository's worktree so the installed code is the resolved SHA rather than
whatever the developer's clone happens to contain.
"""

from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass
from typing import Dict, List

from tests.complete_run.commands import run_command
from tests.complete_run.params import (
    REPO_SPECS,
    UNIFIED_ONLY_TASKS,
    MachineProfile,
    RepoSpec,
)
from tests.complete_run.worktrees import Checkout

logger: logging.Logger = logging.getLogger(__name__)

ENV_TYPE_DEV: str = "dev"
ENV_TYPE_UNIFIED: str = "unified"
# Rebuild the environment the baseline was produced with, so a difference is
# attributable to code rather than to a dependency that moved underneath it.
ENV_TYPE_BASELINE: str = "baseline"

ENV_TYPES: tuple = (ENV_TYPE_DEV, ENV_TYPE_UNIFIED, ENV_TYPE_BASELINE)

# Tools that can solve and create an environment. Only creation uses them:
# activating, running in, listing, and exporting environments always use
# conda, whose output formats the run parses and compares across runs.
SOLVERS: tuple = ("mamba", "conda")


def resolve_solver(requested: str) -> str:
    """Return the solver to create environments with.

    mamba solves the dev environments in about a minute where conda's classic
    solver can take over fifteen, but it is not installed everywhere, so a
    missing mamba falls back to conda rather than failing the run.
    """
    if requested != "conda" and shutil.which(requested) is None:
        logger.warning("%s is not on PATH; creating environments with conda", requested)
        return "conda"
    return requested


@dataclass(frozen=True)
class Environment:
    """The environment a set of tasks runs in."""

    repo_name: str
    env_type: str
    # Empty when env_type is "unified"; that environment has no name we own.
    name: str
    # The shell snippet a generated cfg uses as its environment_commands.
    activation_command: str
    # True when this environment already existed and was reused as-is.
    reused: bool = False

    def run_args(self, args: List[str]) -> List[str]:
        """Wrap a command so it runs inside this environment.

        The controller runs from its own environment, so a bare ``zppy`` or
        ``python -m pytest`` would exercise whatever zppy is installed there
        rather than the revision under test.
        """
        if not self.name:
            raise ValueError(
                f"The {self.env_type} environment for {self.repo_name} has no "
                "name to run commands in."
            )
        return ["conda", "run", "--no-capture-output", "-n", self.name, *args]


def environment_name(repo_name: str, branch: str, tag: str) -> str:
    """Return the conda environment name for one repo in one run."""
    return f"test-{repo_name}-{branch}-{tag}"


def unified_environment(repo_name: str, machine: MachineProfile) -> Environment:
    """Return an Environment backed by E3SM-Unified rather than a dev build."""
    return Environment(
        repo_name=repo_name,
        env_type=ENV_TYPE_UNIFIED,
        name="",
        activation_command=machine.unified_env_cmd,
    )


def environment_exists(name: str) -> bool:
    """Whether a conda environment of this name already exists."""
    output: str = run_command(["conda", "env", "list"], check=False)
    for line in output.splitlines():
        stripped: str = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.split()[0] == name:
            return True
    return False


def activation_command(conda_profile: str, env_name: str) -> str:
    """Build the environment_commands string a generated cfg will run.

    Tasks run inside batch scripts, which are not login shells, so the conda
    profile has to be sourced explicitly before ``conda activate`` works.
    """
    return f"source {conda_profile}; conda activate {env_name}"


def create_environment(
    spec: RepoSpec,
    checkout: Checkout,
    tag: str,
    conda_profile: str,
    *,
    existing_env: str = "",
    allow_existing: bool = False,
    environment_file: str = "",
    solver: str = "conda",
) -> Environment:
    """Create (or reuse) the environment for one repository.

    The package is always installed from the worktree, including when an
    existing environment is reused or rebuilt from an export, so the
    environment reflects the SHA under test while its dependencies come from
    wherever the caller asked.

    Parameters
    ----------
    environment_file : str
        An exported environment to rebuild from, instead of solving the
        repository's ``dev.yml`` afresh. Used to reproduce a baseline's
        dependencies so a difference is attributable to code.
    solver : str
        ``conda`` or ``mamba``, used only to create the environment.

    Raises
    ------
    FileExistsError
        If the environment already exists and was not explicitly nominated for
        reuse. Silently reusing an environment would make the run's provenance
        a guess.
    FileNotFoundError
        If ``environment_file`` was requested but does not exist.
    """
    if existing_env:
        logger.info("Reusing nominated environment %s for %s", existing_env, spec.name)
        _pip_install(existing_env, checkout.path)
        return Environment(
            repo_name=spec.name,
            env_type=ENV_TYPE_DEV,
            name=existing_env,
            activation_command=activation_command(conda_profile, existing_env),
            reused=True,
        )

    name: str = environment_name(spec.name, checkout.branch, tag)
    exists: bool = environment_exists(name)
    if exists and not allow_existing:
        raise FileExistsError(
            f"Conda environment {name!r} already exists. Remove it, or pass it "
            f"as the existing environment for {spec.name}, before rerunning."
        )

    if exists:
        logger.info("Environment %s already exists; reusing it", name)
    elif environment_file:
        if not os.path.isfile(environment_file):
            raise FileNotFoundError(
                f"No exported environment for {spec.name} at {environment_file}. "
                "The baseline predates environment exports, so its dependencies "
                "cannot be reproduced; run against a fresh solve instead."
            )
        logger.info("Rebuilding environment %s from %s", name, environment_file)
        run_command(
            [solver, "env", "create", "-f", environment_file, "-n", name]
            + _assume_yes(solver)
        )
    else:
        logger.info("Creating environment %s from %s", name, spec.env_file())
        if spec.uses_dev_spec:
            channel_args: List[str] = []
            for channel in spec.channels:
                channel_args.extend(["-c", channel])
            if channel_args:
                channel_args.extend(
                    ["--override-channels", "--strict-channel-priority"]
                )
            run_command(
                [solver, "create", "--name", name, "--file", spec.env_file()]
                + channel_args
                + ["--yes"],
                cwd=checkout.path,
            )
        else:
            run_command(
                [solver, "env", "create", "-f", spec.env_file(), "-n", name]
                + _assume_yes(solver),
                cwd=checkout.path,
            )

    _pip_install(name, checkout.path)
    return Environment(
        repo_name=spec.name,
        env_type=ENV_TYPE_DEV,
        name=name,
        activation_command=activation_command(conda_profile, name),
        reused=exists,
    )


def _assume_yes(solver: str) -> List[str]:
    """mamba's ``env create`` asks for confirmation; conda's never does."""
    return ["--yes"] if solver == "mamba" else []


def _pip_install(env_name: str, worktree: str) -> None:
    """Install the worktree's package into an environment."""
    run_command(
        ["conda", "run", "-n", env_name, "python", "-m", "pip", "install", "."],
        cwd=worktree,
    )
    logger.info("Installed %s into %s", worktree, env_name)


def environment_from_status(
    repo_name: str,
    entry: Dict[str, object],
    machine: MachineProfile,
    conda_profile: str,
) -> Environment:
    """Rebuild an Environment from what the prepare stage recorded.

    A run resumed with ``--start-stage`` skips prepare, but later stages still
    need to know which environment each task runs in.
    """
    if entry.get("environment_type") == ENV_TYPE_UNIFIED:
        return unified_environment(repo_name, machine)
    name: str = str(entry.get("environment") or "")
    return Environment(
        repo_name=repo_name,
        env_type=str(entry.get("environment_type") or ENV_TYPE_DEV),
        name=name,
        activation_command=activation_command(conda_profile, name),
        reused=True,
    )


def environments_by_task(
    environments: Dict[str, Environment], machine: MachineProfile
) -> Dict[str, Environment]:
    """Map each zppy task to the environment it runs in.

    Tasks with no dev repository of their own (livvkit) run from E3SM-Unified.
    """
    by_task: Dict[str, Environment] = {}
    for spec in REPO_SPECS:
        environment = environments.get(spec.name)
        if environment is None:
            continue
        for task in spec.tasks:
            by_task[task] = environment

    for task in UNIFIED_ONLY_TASKS:
        by_task[task] = unified_environment(task, machine)

    return by_task
