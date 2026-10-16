"""The weekly cfgs, and what the image checker compares for each.

This is the one place that says which weekly cfgs exist, which case each runs
against, and which tasks' plots are image-checked. cfg generation, the complete
run test, and ``test_images.py`` all read it, so a cfg cannot be submitted but
never checked, or checked against the wrong case.
"""

import os
import re
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

V2_CASE_NAME: str = "v2.LR.historical_0201"
V3_CASE_NAME: str = "v3.LR.historical_0051"

TASK_NAMES: Tuple[str, ...] = (
    "climo",
    "ts",
    "e3sm_to_cmip",
    "tc_analysis",
    "e3sm_diags",
    "mpas_analysis",
    "global_time_series",
    "ilamb",
    "livvkit",
    "pcmdi_diags",
)

PLOTTING_TASKS: Tuple[str, ...] = (
    "e3sm_diags",
    "mpas_analysis",
    "global_time_series",
    "ilamb",
    "livvkit",
    "pcmdi_diags",
)

# Task -> tasks that must also run to produce its inputs.
TASK_DEPENDENCIES: Dict[str, Tuple[str, ...]] = {
    "climo": (),
    "ts": (),
    "e3sm_to_cmip": (),
    "tc_analysis": (),
    "e3sm_diags": ("climo", "ts", "tc_analysis"),
    "mpas_analysis": (),
    "global_time_series": ("ts", "mpas_analysis"),
    "ilamb": ("ts", "e3sm_to_cmip"),
    "livvkit": ("climo", "ts"),
    "pcmdi_diags": ("ts", "e3sm_to_cmip"),
}


def expand_task_selection(
    tasks: Sequence[str],
) -> Tuple[List[str], Dict[str, List[str]]]:
    """Return requested tasks and their dependencies in dependency-first order."""
    unknown: List[str] = sorted(set(tasks) - set(TASK_NAMES))
    if unknown:
        raise ValueError(
            f"Unknown task(s): {', '.join(unknown)}; expected one of "
            f"{', '.join(TASK_NAMES)}"
        )

    expanded: List[str] = []
    required_by: Dict[str, List[str]] = {}

    def add(task: str, parent: str = "") -> None:
        if parent:
            parents = required_by.setdefault(task, [])
            if parent not in parents:
                parents.append(parent)
        if task in expanded:
            return
        for dependency in TASK_DEPENDENCIES[task]:
            add(dependency, task)
        expanded.append(task)

    for task in tasks:
        add(task)
    return expanded, required_by


def task_sections_for_cfg(cfg: str) -> Tuple[str, ...]:
    """Return the supported task sections in a cfg template."""
    path: str = os.path.join(os.path.dirname(__file__), f"template_{cfg}.cfg")
    try:
        with open(path) as stream:
            sections = re.findall(r"^\[([a-z0-9_]+)\]\s*$", stream.read(), re.M)
    except OSError:
        return ()
    return tuple(task for task in TASK_NAMES if task in sections)


def task_for_status_file(filename: str) -> str | None:
    """Return the task owning a generated status filename."""
    stem: str = os.path.basename(filename)
    if stem.startswith("bundle") and stem.endswith(".status"):
        return "bundle"
    for task in sorted((*TASK_NAMES, "bundle"), key=len, reverse=True):
        if stem == f"{task}.status" or stem.startswith(f"{task}_"):
            return task
    return None


@dataclass(frozen=True)
class WeeklyCfg:
    # The template name: tests/integration/template_<name>.cfg.
    name: str
    case: str
    # Tasks whose plots the image checker compares. Every task the cfg runs that
    # produces plots belongs here; a task left out is never checked.
    image_tasks: Tuple[str, ...]

    @property
    def test_name(self) -> str:
        """The name the image checker uses, without the "weekly_" prefix."""
        return checker_name(self.name)


# Legacy cfgs exist to check that zppy still accepts older cfg syntax. Keep one
# only while it differs from the current cfgs in more than its paths: a copy
# of a current cfg doubles the compute and the image checks and tests nothing
# new. See the note in docs/source/dev_guide/tests/automated_test.rst.
WEEKLY_CFGS: Tuple[WeeklyCfg, ...] = (
    WeeklyCfg(
        "weekly_bundles",
        V3_CASE_NAME,
        # No mpas_analysis in the bundles cfg.
        ("e3sm_diags", "global_time_series", "ilamb"),
    ),
    WeeklyCfg(
        "weekly_comprehensive_v2",
        V2_CASE_NAME,
        ("e3sm_diags", "mpas_analysis", "global_time_series", "ilamb"),
    ),
    WeeklyCfg(
        "weekly_comprehensive_v3",
        V3_CASE_NAME,
        (
            "e3sm_diags",
            "mpas_analysis",
            "global_time_series",
            "ilamb",
            "livvkit",
            "pcmdi_diags",
        ),
    ),
    WeeklyCfg(
        "weekly_legacy_3.2.0_comprehensive_v3",
        V3_CASE_NAME,
        (
            "e3sm_diags",
            "mpas_analysis",
            "global_time_series",
            "ilamb",
            "livvkit",
            "pcmdi_diags",
        ),
    ),
)

WEEKLY_CFGS_BY_NAME: Dict[str, WeeklyCfg] = {cfg.name: cfg for cfg in WEEKLY_CFGS}


def case_name_for_cfg(cfg: str) -> str:
    """Return the case a cfg runs against.

    A cfg outside the weekly set (a ``min_case_*`` one, say) falls back to its
    name: one mentioning "v2" runs the v2 case, anything else the v3 case.
    """
    weekly = WEEKLY_CFGS_BY_NAME.get(cfg)
    if weekly is not None:
        return weekly.case
    return V2_CASE_NAME if "v2" in cfg else V3_CASE_NAME


def checker_name(cfg: str) -> str:
    """Return the name the image checker uses for a cfg.

    The checker drops the "weekly_" prefix, so the diffs for
    ``weekly_bundles`` land in ``image_check_failures_bundles``.
    """
    return cfg[len("weekly_") :] if cfg.startswith("weekly_") else cfg
