"""Compare the environments two runs were produced with.

An image difference is only interpretable once you know whether the environment
changed underneath it:

* In a fresh-solve run, the environment difference **is** the result -- it names
  the dependency that moved.
* In a run that rebuilt the baseline's environment, the difference should be
  empty. A non-empty one means the reproduction did not take, so the image
  differences are *not* attributable to the code under review.

Package lists are parsed out of ``conda env export`` output. ``name:`` and
``prefix:`` are ignored: every run builds its own environment, so those always
differ and would bury the changes worth seeing.

A baseline whose repository ran from E3SM-Unified has no export for it. Its
``env_descriptions/<task>.txt`` still carries that environment's ``conda list``,
so the comparison falls back to that, by version only.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from tests.complete_run.layout import RunLayout
from tests.complete_run.params import REPO_SPECS_BY_NAME

logger: logging.Logger = logging.getLogger(__name__)

# Lines that identify one run rather than describe its dependencies.
_IDENTITY_KEYS: Tuple[str, ...] = ("name:", "prefix:")

# Reported first, because these move results most often. Anything else that
# changed is still reported, just after these.
NOTABLE_PACKAGES: Tuple[str, ...] = (
    "python",
    "numpy",
    "scipy",
    "xarray",
    "dask",
    "netcdf4",
    "matplotlib",
    "matplotlib-base",
    "cartopy",
    "nco",
    "esmf",
    "esmpy",
    "e3sm_diags",
    "e3sm-diags",
    "e3sm_to_cmip",
    "mpas-analysis",
    "mpas_analysis",
    "zppy-interfaces",
    "zppy_interfaces",
)


@dataclass
class PackageChange:
    """One package that differs between two environments."""

    name: str
    baseline: str
    candidate: str

    @property
    def kind(self) -> str:
        if not self.baseline:
            return "added"
        if not self.candidate:
            return "removed"
        return "changed"

    @property
    def notable(self) -> bool:
        return self.name.lower() in NOTABLE_PACKAGES


@dataclass
class EnvironmentDiff:
    """How one repository's environment differs from the baseline's."""

    repo: str
    # False when either side has no export to compare.
    available: bool = True
    detail: str = ""
    changes: List[PackageChange] = field(default_factory=list)

    @property
    def differs(self) -> bool:
        return bool(self.changes)

    @property
    def notable_changes(self) -> List[PackageChange]:
        return [change for change in self.changes if change.notable]

    def as_dict(self) -> Dict[str, object]:
        return {
            "repo": self.repo,
            "available": self.available,
            "detail": self.detail,
            "change_count": len(self.changes),
            "changes": [
                {
                    "name": change.name,
                    "baseline": change.baseline,
                    "candidate": change.candidate,
                    "kind": change.kind,
                    "notable": change.notable,
                }
                for change in self.changes
            ],
        }


def parse_environment_export(text: str) -> Dict[str, str]:
    """Parse ``conda env export`` output into package -> version.

    Hand-parsed rather than pulling in a YAML dependency: the format is fixed
    and only the dependency list matters. Pip requirements are prefixed so a
    package installed both ways cannot silently collide.
    """
    packages: Dict[str, str] = {}
    in_dependencies: bool = False
    in_pip: bool = False

    for raw_line in text.splitlines():
        line: str = raw_line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if any(line.startswith(key) for key in _IDENTITY_KEYS):
            continue
        if line.startswith("dependencies:"):
            in_dependencies, in_pip = True, False
            continue
        if not line.startswith(" ") and line.endswith(":"):
            # A new top-level block: channels, variables, and so on.
            in_dependencies, in_pip = False, False
            continue
        if not in_dependencies:
            continue

        stripped: str = line.strip()
        if stripped in ("- pip:", "-pip:"):
            in_pip = True
            continue
        if not stripped.startswith("- "):
            continue

        spec: str = stripped[2:].strip()
        indent: int = len(line) - len(line.lstrip())
        if in_pip and indent <= 2:
            # Dedented back out of the pip block.
            in_pip = False

        name, version = _split_spec(spec)
        if not name:
            continue
        packages[f"pip:{name}" if in_pip else name] = version

    return packages


def _split_spec(spec: str) -> Tuple[str, str]:
    """Split ``package=version=build`` or ``package==version`` into name, version."""
    for separator in ("==", "="):
        if separator in spec:
            name, _, remainder = spec.partition(separator)
            return name.strip(), remainder.strip()
    return spec.strip(), ""


def parse_package_list(text: str) -> Dict[str, str]:
    """Parse ``conda list`` output into package -> version.

    This is the list an ``env_description.txt`` carries, below its own header
    lines, so parsing starts at ``conda list``'s ``# Name`` header. Packages
    from PyPI get the same ``pip:`` prefix as in an export.
    """
    packages: Dict[str, str] = {}
    in_list: bool = False
    for line in text.splitlines():
        if line.startswith("# Name"):
            in_list = True
            continue
        fields: List[str] = line.split()
        if not in_list or len(fields) < 2 or fields[0].startswith("#"):
            continue
        name: str = fields[0]
        if len(fields) >= 4 and fields[3] == "pypi":
            name = f"pip:{name}"
        packages[name] = fields[1]
    return packages


def diff_environments(baseline_text: str, candidate_text: str) -> List[PackageChange]:
    """Return every package that differs between two exports."""
    return _diff_packages(
        parse_environment_export(baseline_text),
        parse_environment_export(candidate_text),
    )


def _diff_packages(
    baseline: Dict[str, str], candidate: Dict[str, str]
) -> List[PackageChange]:
    """Return every package whose version differs between two package maps."""
    changes: List[PackageChange] = []
    for name in sorted(set(baseline) | set(candidate)):
        before: str = baseline.get(name, "")
        after: str = candidate.get(name, "")
        if before != after:
            changes.append(PackageChange(name=name, baseline=before, candidate=after))

    # Notable packages first; the rest alphabetically after them.
    changes.sort(key=lambda change: (not change.notable, change.name))
    return changes


def compare_run_environments(
    candidate: RunLayout, baseline: RunLayout, repos: List[str]
) -> List[EnvironmentDiff]:
    """Compare every repository's environment against the baseline's."""
    results: List[EnvironmentDiff] = []
    for repo in repos:
        candidate_path: str = candidate.environment_file(repo)
        baseline_path: str = baseline.environment_file(repo)
        candidate_text: str = _read(candidate_path)
        baseline_text: str = _read(baseline_path)

        if candidate_text and not baseline_text:
            fallback: Tuple[str, Dict[str, str]] | None = _baseline_package_list(
                baseline, repo
            )
            if fallback is not None:
                task, baseline_packages = fallback
                # conda list has no build strings, so compare versions only.
                candidate_packages: Dict[str, str] = {
                    name: version.split("=")[0]
                    for name, version in parse_environment_export(
                        candidate_text
                    ).items()
                }
                # A dev environment pip-installs the package under test, which
                # E3SM-Unified has from conda-forge: pip:e3sm-diags there is
                # e3sm_diags here. Match by package, not by how it was installed.
                baseline_packages = _by_package(baseline_packages)
                candidate_packages = _by_package(candidate_packages)
                # E3SM-Unified bundles every tool, so most of its packages are
                # not in this repository's environment at all. Listing them as
                # removed would bury the dependencies that actually differ.
                unified_only: int = len(
                    set(baseline_packages) - set(candidate_packages)
                )
                results.append(
                    EnvironmentDiff(
                        repo=repo,
                        detail=(
                            f"The baseline ran {repo} from E3SM-Unified, compared"
                            f" by version against env_descriptions/{task}.txt."
                            " Only packages in this run's environment are listed;"
                            f" {unified_only} more in E3SM-Unified are not."
                        ),
                        changes=[
                            change
                            for change in _diff_packages(
                                baseline_packages, candidate_packages
                            )
                            if change.candidate
                        ],
                    )
                )
                continue

        if not candidate_text or not baseline_text:
            missing: List[str] = []
            if not baseline_text:
                missing.append("the baseline")
            if not candidate_text:
                missing.append("this run")
            results.append(
                EnvironmentDiff(
                    repo=repo,
                    available=False,
                    detail=(
                        f"No environment export for {' and '.join(missing)}; "
                        "dependency changes could not be compared."
                    ),
                )
            )
            continue

        results.append(
            EnvironmentDiff(
                repo=repo, changes=diff_environments(baseline_text, candidate_text)
            )
        )

    return results


def _by_package(packages: Dict[str, str]) -> Dict[str, str]:
    """Key packages by normalized name, dropping how they were installed.

    Where a package is installed both ways, the conda one is kept.
    """
    normalized: Dict[str, str] = {}
    for name in sorted(packages, key=lambda name: name.startswith("pip:")):
        key: str = name.removeprefix("pip:").lower().replace("_", "-")
        normalized.setdefault(key, packages[name])
    return normalized


def _baseline_package_list(
    baseline: RunLayout, repo: str
) -> Tuple[str, Dict[str, str]] | None:
    """Return a task and the packages its baseline env_description lists.

    Any of the repository's tasks will do: they all ran in its environment.
    """
    spec = REPO_SPECS_BY_NAME.get(repo)
    for task in spec.tasks if spec else ():
        packages = parse_package_list(
            _read(os.path.join(baseline.env_descriptions, f"{task}.txt"))
        )
        if packages:
            return task, packages
    return None


def summarize(diffs: List[EnvironmentDiff]) -> Dict[str, object]:
    """Summarize environment differences for a report."""
    comparable: List[EnvironmentDiff] = [diff for diff in diffs if diff.available]
    return {
        "compared": len(comparable),
        "unavailable": [diff.repo for diff in diffs if not diff.available],
        "repos_differing": [diff.repo for diff in comparable if diff.differs],
        "change_count": sum(len(diff.changes) for diff in comparable),
        "notable_change_count": sum(len(diff.notable_changes) for diff in comparable),
        "repos": [diff.as_dict() for diff in diffs],
    }


def interpretation(
    diffs: List[EnvironmentDiff], environment_modes: Dict[str, str]
) -> str:
    """Say what the environment differences mean for this run's image diffs.

    The same difference means opposite things depending on what the run was
    holding fixed, so the report states which one applies rather than leaving a
    reader to work it out.
    """
    differing: List[str] = [
        diff.repo for diff in diffs if diff.available and diff.differs
    ]
    reproduced: List[str] = [
        repo for repo, mode in environment_modes.items() if mode == "baseline"
    ]
    broken: List[str] = sorted(set(differing) & set(reproduced))

    if broken:
        return (
            "The environment for "
            + ", ".join(f"`{repo}`" for repo in broken)
            + " was meant to reproduce the baseline's but does not. Image "
            "differences in this run are **not** attributable to the code "
            "under review until that is resolved."
        )
    unavailable: List[str] = sorted(diff.repo for diff in diffs if not diff.available)
    if not differing and unavailable:
        # "Could not check" must never read as "nothing changed".
        return (
            "No dependency changed in the environments compared, but "
            + ", ".join(f"`{repo}`" for repo in unavailable)
            + " could not be compared, so image differences are not necessarily "
            "attributable to the code under test."
        )
    if not differing:
        return (
            "No dependency changed. Image differences are attributable to the "
            "code under test."
        )

    return (
        "Dependencies changed in "
        + ", ".join(f"`{repo}`" for repo in sorted(differing))
        + ". Image differences may come from those changes rather than from "
        "zppy itself."
    )


def _read(path: str) -> str:
    """Read an export, returning an empty string when it is absent."""
    if not os.path.isfile(path):
        return ""
    try:
        with open(path) as stream:
            return stream.read()
    except OSError as error:
        logger.warning("Could not read %s: %s", path, error)
        return ""
