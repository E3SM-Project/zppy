"""The weekly cfgs, and what the image checker compares for each.

This is the one place that says which weekly cfgs exist, which case each runs
against, and which tasks' plots are image-checked. cfg generation, the complete
run test, and ``test_images.py`` all read it, so a cfg cannot be submitted but
never checked, or checked against the wrong case.
"""

from dataclasses import dataclass
from typing import Dict, Tuple

V2_CASE_NAME: str = "v2.LR.historical_0201"
V3_CASE_NAME: str = "v3.LR.historical_0051"


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
        "weekly_legacy_3.1.0_comprehensive_v3",
        V3_CASE_NAME,
        ("e3sm_diags", "mpas_analysis", "global_time_series", "ilamb", "pcmdi_diags"),
    ),
    WeeklyCfg(
        "weekly_legacy_3.0.0_comprehensive_v3",
        V3_CASE_NAME,
        ("e3sm_diags", "mpas_analysis", "global_time_series", "ilamb"),
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
