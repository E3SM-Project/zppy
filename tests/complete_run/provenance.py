"""Environment descriptions and the run manifest.

Two kinds of provenance come out of a complete run:

``env_description.txt``
    One per task, copied next to that task's diagnostic output and promoted
    alongside it into the expected-results directory. A later run reads the
    ``Generated:`` line back to date the baselines it is testing against, so
    **this file's format is a contract with every promoted baseline on disk**.
    Do not reorder or rename its lines.

``manifest.json``
    One per run, machine-readable, recording the resolved SHAs, environments,
    and selections that produced the results.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
from datetime import datetime, timezone
from typing import Dict, List, Sequence

from tests.complete_run.commands import run_command
from tests.complete_run.environments import ENV_TYPE_DEV, Environment
from tests.complete_run.layout import write_json
from tests.complete_run.params import case_name_for_cfg, generated_cfg_path
from tests.complete_run.worktrees import Checkout

logger: logging.Logger = logging.getLogger(__name__)

ENV_DESCRIPTION_FILENAME: str = "env_description.txt"
MANIFEST_FILENAME: str = "manifest.json"

# The format `Generated:` is written in, and parsed back out of, promoted
# baselines. Kept as a module constant so the writer and reader cannot drift.
GENERATED_FORMAT: str = "%Y-%m-%d %H:%M:%S"
_GENERATED_PATTERN = re.compile(r"^Generated:\s*(\S+)")

_UNIFIED_REPOSITORY_LINE: str = (
    "Repository: N/A (uses a released package via the unified environment)"
)


def render_env_description(
    task: str,
    checkout: Checkout | None,
    environment: Environment,
    package_list: str,
    generated: datetime | None = None,
) -> str:
    """Render one task's environment description.

    Parameters
    ----------
    task : str
        The zppy task this environment runs.
    checkout : Checkout | None
        The repository under test, or None for a task backed by E3SM-Unified.
    environment : Environment
        The environment the task runs in.
    package_list : str
        Output of ``conda list`` for that environment.
    generated : datetime | None
        Timestamp to record; defaults to now. Injectable so tests are stable.
    """
    stamp: datetime = generated or datetime.now()
    lines: List[str] = [
        f"Task: {task}",
        f"Generated: {stamp.strftime(GENERATED_FORMAT)}",
        "",
    ]

    if environment.env_type == ENV_TYPE_DEV and checkout is not None:
        lines.extend(
            [
                f"Repository: {checkout.source_repo}",
                f"Commit: {checkout.sha}",
                f"Commit (short): {checkout.short_sha}",
                f"Branch: {checkout.branch}",
            ]
        )
    else:
        lines.append(_UNIFIED_REPOSITORY_LINE)

    lines.append("")
    if environment.env_type == ENV_TYPE_DEV:
        lines.append(f"Conda environment (dev): {environment.name}")
    else:
        lines.append("Conda environment: E3SM-Unified")

    lines.extend(["", "Package versions:", "-----------------", package_list])
    return "\n".join(lines).rstrip("\n") + "\n"


def conda_package_list(environment: Environment) -> str:
    """Return ``conda list`` output for an environment.

    A failure here must not abort a run that has already consumed hours of
    compute, so the inability to list packages is recorded in the file itself.
    """
    if environment.env_type == ENV_TYPE_DEV:
        args: List[str] = ["conda", "list", "-n", environment.name]
        label: str = environment.name
    else:
        # A bare `conda list` would describe the controller's own environment.
        # E3SM-Unified has to be loaded first, by its own script.
        args = [
            "bash",
            "-c",
            f"{environment.activation_command} >/dev/null 2>&1 && conda list",
        ]
        label = "the unified environment"

    output: str = run_command(args, check=False)
    if not output:
        return f"(unable to list packages for {label})"
    return output


def export_environment_file(environment: Environment, destination: str) -> str:
    """Export an environment so a later run can rebuild it.

    ``conda list`` output, which `env_description.txt` carries, is readable but
    cannot recreate an environment. This writes a full ``conda env export``,
    which can -- that is what lets a later run hold dependencies fixed and
    attribute a difference to code rather than to a dependency bump.

    Returns the path written, or an empty string if the export failed. A run
    that cannot export its environment is still a valid run; it just cannot be
    reproduced exactly later.
    """
    if environment.env_type != ENV_TYPE_DEV or not environment.name:
        # E3SM-Unified is versioned and loaded by its own script; exporting it
        # would record a snapshot nothing rebuilds from.
        return ""

    exported: str = run_command(
        ["conda", "env", "export", "-n", environment.name], check=False
    )
    if not exported or "dependencies:" not in exported:
        logger.warning(
            "Could not export environment %s; this run will not be exactly "
            "reproducible.",
            environment.name,
        )
        return ""

    os.makedirs(os.path.dirname(destination), exist_ok=True)
    with open(destination, "w") as stream:
        stream.write(exported)
        if not exported.endswith("\n"):
            stream.write("\n")
    logger.info("Exported environment %s -> %s", environment.name, destination)
    return destination


def write_env_description(
    env_description_dir: str,
    task: str,
    checkout: Checkout | None,
    environment: Environment,
    generated: datetime | None = None,
    package_list: str | None = None,
) -> str:
    """Write one task's environment description to the run's cache directory.

    ``package_list`` lets a caller describing several tasks that share one
    environment list its packages once rather than once per task.
    """
    os.makedirs(env_description_dir, exist_ok=True)
    path: str = os.path.join(env_description_dir, f"{task}.txt")
    if package_list is None:
        package_list = conda_package_list(environment)
    content: str = render_env_description(
        task, checkout, environment, package_list, generated
    )
    with open(path, "w") as stream:
        stream.write(content)
    logger.info("Wrote environment description for task %s -> %s", task, path)
    return path


def read_generated_date(path: str) -> str | None:
    """Read the ``Generated:`` date out of an environment description.

    Returns the ``YYYY-MM-DD`` portion, or None if the file is absent or
    predates environment descriptions. Callers treat None as "unknown", never
    as an error: baselines promoted before this file existed are still valid.
    """
    try:
        with open(path) as stream:
            for line in stream:
                match = _GENERATED_PATTERN.match(line.strip())
                if match:
                    return match.group(1)
    except OSError:
        return None
    return None


def www_root_from_cfg(cfg_path: str) -> str | None:
    """Read the resolved ``www`` root out of a generated cfg.

    The value in a generated cfg is already fully resolved -- it bakes in
    ``zppy_<cfg>_www/<unique_id>`` -- so callers append only ``<case>/<task>``.
    Appending the prefix again creates a duplicate subtree that the
    expected-results updater never picks up.
    """
    try:
        with open(cfg_path) as stream:
            for line in stream:
                stripped: str = line.strip()
                if not stripped.startswith("www"):
                    continue
                key, _, value = stripped.partition("=")
                if key.strip() != "www":
                    continue
                return value.strip().strip('"').strip("'") or None
    except OSError:
        return None
    return None


def distribute_env_descriptions(
    env_description_dir: str,
    zppy_worktree: str,
    cfgs: Sequence[str],
    tasks: Sequence[str],
    cfg_suffix: str,
) -> Dict[str, str]:
    """Copy each task's environment description into every cfg's www tree.

    Returns the www root found for each cfg, for the report to cite.
    """
    www_root_by_cfg: Dict[str, str] = {}
    for cfg in cfgs:
        cfg_path: str = generated_cfg_path(zppy_worktree, cfg, cfg_suffix)
        www_root: str | None = www_root_from_cfg(cfg_path)
        if www_root is None:
            logger.warning(
                "Could not determine www root from %s; skipping environment "
                "descriptions for %s",
                cfg_path,
                cfg,
            )
            continue

        www_root_by_cfg[cfg] = www_root
        case: str = case_name_for_cfg(cfg)
        for task in tasks:
            source: str = os.path.join(env_description_dir, f"{task}.txt")
            if not os.path.isfile(source):
                continue
            target_dir: str = os.path.join(www_root.rstrip("/"), case, task)
            try:
                os.makedirs(target_dir, exist_ok=True)
                shutil.copy(source, os.path.join(target_dir, ENV_DESCRIPTION_FILENAME))
            except OSError as error:
                logger.warning(
                    "Could not write environment description to %s: %s",
                    target_dir,
                    error,
                )

    return www_root_by_cfg


def build_manifest(
    tag: str,
    machine: str,
    checkouts: Sequence[Checkout],
    environments: Dict[str, Environment],
    cfgs: Sequence[str],
    tasks: Sequence[str],
    zppy_version: str,
) -> Dict[str, object]:
    """Build the machine-readable record of what this run tested."""
    repos: Dict[str, Dict[str, str]] = {}
    for checkout in checkouts:
        environment = environments.get(checkout.name)
        repos[checkout.name] = {
            "sha": checkout.sha,
            "short_sha": checkout.short_sha,
            "branch": checkout.branch,
            "remote": checkout.remote,
            "source_repo": checkout.source_repo,
            "worktree": checkout.path,
            "environment": environment.name if environment else "",
            "environment_type": environment.env_type if environment else "",
        }

    return {
        "schema_version": 2,
        "tag": tag,
        "machine": machine,
        "generated": datetime.now(timezone.utc).isoformat(),
        "zppy_version": zppy_version,
        "cfgs": list(cfgs),
        "tasks": list(tasks),
        "repos": repos,
    }


def write_manifest(results_dir: str, manifest: Dict[str, object]) -> str:
    """Write the run manifest as sorted JSON."""
    return write_json(os.path.join(results_dir, MANIFEST_FILENAME), manifest)
