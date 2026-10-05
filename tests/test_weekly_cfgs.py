"""The weekly cfg table must agree with the templates it describes.

A task that a cfg runs but the table omits is silently never image-checked;
that is how livvkit and legacy 3.1.0's pcmdi_diags went unchecked.
"""

import glob
import os
import re
from typing import Set

import pytest

from tests.integration.weekly_cfgs import (
    V2_CASE_NAME,
    V3_CASE_NAME,
    WEEKLY_CFGS,
    case_name_for_cfg,
)

INTEGRATION_DIR = os.path.join(os.path.dirname(__file__), "integration")

# Tasks that produce plots for the image checker to compare.
PLOTTING_TASKS: Set[str] = {
    "e3sm_diags",
    "mpas_analysis",
    "global_time_series",
    "ilamb",
    "livvkit",
    "pcmdi_diags",
}


def _template(name: str) -> str:
    with open(os.path.join(INTEGRATION_DIR, f"template_{name}.cfg")) as stream:
        return stream.read()


def test_every_weekly_template_is_in_the_table() -> None:
    on_disk = {
        os.path.basename(path)[len("template_") : -len(".cfg")]
        for path in glob.glob(os.path.join(INTEGRATION_DIR, "template_weekly_*.cfg"))
    }
    assert on_disk == {cfg.name for cfg in WEEKLY_CFGS}


@pytest.mark.parametrize("cfg", WEEKLY_CFGS, ids=lambda cfg: cfg.name)
def test_every_plotting_task_a_cfg_runs_is_image_checked(cfg) -> None:
    sections = set(re.findall(r"^\[([a-z0-9_]+)\]", _template(cfg.name), re.M))
    assert set(cfg.image_tasks) == sections & PLOTTING_TASKS


@pytest.mark.parametrize("cfg", WEEKLY_CFGS, ids=lambda cfg: cfg.name)
def test_the_case_matches_the_template(cfg) -> None:
    template = _template(cfg.name)
    expected = "case_name_v2" if cfg.case == V2_CASE_NAME else "case_name#"
    assert expected in template


def test_non_weekly_cfgs_fall_back_to_their_name() -> None:
    assert case_name_for_cfg("min_case_tc_analysis_v2_simultaneous_1") == V2_CASE_NAME
    assert case_name_for_cfg("min_case_nco") == V3_CASE_NAME


def test_image_checks_follow_the_table() -> None:
    from tests.integration.test_images import prepare_test_configs

    expansions = {"cfgs_to_run": ["weekly_comprehensive_v3", "weekly_bundles"]}
    configs = prepare_test_configs(expansions, "", ["livvkit", "mpas_analysis"])
    by_name = {config[0]: config for config in configs}
    assert by_name["comprehensive_v3"][1] == V3_CASE_NAME
    assert by_name["comprehensive_v3"][4] == ["livvkit", "mpas_analysis"]
    # Bundles runs no mpas_analysis or livvkit, so nothing is requested of it.
    assert by_name["bundles"][4] == []
