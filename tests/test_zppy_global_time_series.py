import os
from typing import Any, Dict, List

import pytest
from configobj import ConfigObj
from validate import Validator

from zppy.global_time_series import determine_and_add_dependencies, determine_components
from zppy.mpas_analysis import (
    _get_referenced_comparison_type,
    _resolve_mpas_analysis_config_file,
    get_mpas_analysis_prefixes,
)


def test_determine_components():
    c: Dict[str, Any]
    # Test non-legacy
    c = {
        "plots_original": "",
        "plots_atm": ["a"],
        "plots_ice": "",
        "plots_lnd": "",
        "plots_ocn": "",
    }
    determine_components(c)
    assert c["use_atm"] == True
    assert c["use_ice"] == False
    assert c["use_lnd"] == False
    assert c["use_ocn"] == False
    assert c["plots_atm"] == ["a"]
    assert c["plots_ice"] == "None"
    assert c["plots_lnd"] == "None"
    assert c["plots_ocn"] == "None"

    c = {
        "plots_original": "",
        "plots_atm": "",
        "plots_ice": ["a"],
        "plots_lnd": "",
        "plots_ocn": "",
    }
    determine_components(c)
    assert c["use_atm"] == False
    assert c["use_ice"] == True
    assert c["use_lnd"] == False
    assert c["use_ocn"] == False
    assert c["plots_atm"] == "None"
    assert c["plots_ice"] == ["a"]
    assert c["plots_lnd"] == "None"
    assert c["plots_ocn"] == "None"

    c = {
        "plots_original": "",
        "plots_atm": "",
        "plots_ice": "",
        "plots_lnd": ["a"],
        "plots_ocn": "",
    }
    determine_components(c)
    assert c["use_atm"] == False
    assert c["use_ice"] == False
    assert c["use_lnd"] == True
    assert c["use_ocn"] == False
    assert c["plots_atm"] == "None"
    assert c["plots_ice"] == "None"
    assert c["plots_lnd"] == ["a"]
    assert c["plots_ocn"] == "None"

    c = {
        "plots_original": "",
        "plots_atm": "",
        "plots_ice": "",
        "plots_lnd": "",
        "plots_ocn": ["a"],
    }
    determine_components(c)
    assert c["use_atm"] == False
    assert c["use_ice"] == False
    assert c["use_lnd"] == False
    assert c["use_ocn"] == True
    assert c["plots_atm"] == "None"
    assert c["plots_ice"] == "None"
    assert c["plots_lnd"] == "None"
    assert c["plots_ocn"] == ["a"]


def test_determine_and_add_dependencies():
    c: Dict[str, Any]
    c = {
        "use_atm": True,
        "use_lnd": False,
        "use_ocn": False,
        "year1": 1980,
        "year2": 1990,
        "ts_num_years": 5,
    }
    dependencies: List[str] = []
    determine_and_add_dependencies(c, dependencies, "script_dir")
    expected = [
        "script_dir/ts_atm_monthly_glb_1980-1984-0005.status",
        "script_dir/ts_atm_monthly_glb_1985-1989-0005.status",
    ]
    assert dependencies == expected

    c = {
        "use_atm": False,
        "use_lnd": True,
        "use_ocn": False,
        "year1": 1980,
        "year2": 1990,
        "ts_num_years": 5,
    }
    dependencies = []
    determine_and_add_dependencies(c, dependencies, "script_dir")
    expected = [
        "script_dir/ts_lnd_monthly_glb_1980-1984-0005.status",
        "script_dir/ts_lnd_monthly_glb_1985-1989-0005.status",
    ]
    assert dependencies == expected

    c = {
        "use_atm": False,
        "use_lnd": False,
        "use_ocn": True,
        "ts_years": "1980:1990:10",
        "climo_years": "1980:1990:10",
    }
    dependencies = []
    determine_and_add_dependencies(c, dependencies, "script_dir")
    expected = ["script_dir/mpas_analysis_ts_1980-1989_climo_1980-1989.status"]
    assert dependencies == expected

    c = {
        "use_atm": False,
        "use_lnd": False,
        "use_ocn": True,
        "mpas_analysis_subsections": ["reference", "test"],
    }
    dependencies = []
    determine_and_add_dependencies(
        c,
        dependencies,
        "script_dir",
        mpas_analysis_prefixes={
            "reference": ["mpas_analysis_reference_ts_1980-1989_climo_1980-1989"],
            "test": ["mpas_analysis_test_ts_1980-1999_climo_1990-1999"],
        },
    )
    expected = [
        "script_dir/mpas_analysis_reference_ts_1980-1989_climo_1980-1989.status",
        "script_dir/mpas_analysis_test_ts_1980-1999_climo_1990-1999.status",
    ]
    assert dependencies == expected

    c = {
        "use_atm": False,
        "use_lnd": False,
        "use_ocn": True,
        "ts_years": "",
        "climo_years": "1980:1990:10",
    }
    dependencies = []
    with pytest.raises(Exception):
        determine_and_add_dependencies(c, dependencies, "script_dir")

    c = {
        "use_atm": False,
        "use_lnd": False,
        "use_ocn": True,
        "ts_years": "1980:1990:10",
        "climo_years": "",
    }
    dependencies = []
    with pytest.raises(Exception):
        determine_and_add_dependencies(c, dependencies, "script_dir")

    c = {
        "use_atm": False,
        "use_lnd": False,
        "use_ocn": True,
        "mpas_analysis_subsections": ["missing"],
    }
    dependencies = []
    with pytest.raises(ValueError):
        determine_and_add_dependencies(
            c,
            dependencies,
            "script_dir",
            mpas_analysis_prefixes={
                "reference": ["mpas_analysis_reference_ts_1980-1989_climo_1980-1989"]
            },
        )


def test_get_mpas_analysis_prefixes(tmp_path):
    config_path = tmp_path / "mpas_analysis.cfg"
    config_path.write_text(
        """
[default]
case = "case_name"
input = "input_dir"
output = "output_dir"
www = "www_dir"

[mpas_analysis]
active = True
mesh = "EC30to60E2r2"

  [[ reference ]]
  ts_years = "1985-1989",
  climo_years = "1985-1989",
  enso_years = "1985-1989",

  [[ test ]]
  ts_years = "1985-1995",
  climo_years = "1990-1995",
  enso_years = "1990-1995",

  [[ mvm ]]
  reference_data_path = [[ reference ]]
  test_data_path = [[ test ]]
""".strip()
    )

    config = ConfigObj(
        str(config_path), configspec=os.path.join("zppy", "defaults", "default.ini")
    )
    validator = Validator()
    assert config.validate(validator)

    prefixes = get_mpas_analysis_prefixes(config)

    assert prefixes == {
        "reference": ["mpas_analysis_reference_ts_1985-1989_climo_1985-1989"],
        "test": ["mpas_analysis_test_ts_1985-1995_climo_1990-1995"],
        "mvm": [
            "mpas_analysis_mvm_ts_1985-1995_climo_1990-1995_vs_ref_ts_1985-1989_climo_1985-1989"
        ],
    }


def test_resolve_mpas_analysis_config_file_uses_comparison_type(tmp_path):
    config_file = _resolve_mpas_analysis_config_file(
        str(tmp_path), "ts_1985-1989_climo_1985-1989", comparison_type="mvm"
    )

    assert config_file == os.path.join(
        str(tmp_path.resolve()),
        "post",
        "analysis",
        "mpas_analysis",
        "mvm",
        "cfg",
        "mpas_analysis_ts_1985-1989_climo_1985-1989.cfg",
    )


def test_get_referenced_comparison_type_infers_from_subsection():
    comparison_type = _get_referenced_comparison_type(
        "auto",
        "/unused",
        "reference",
        "ts_1985-1989_climo_1985-1989",
        {"reference": "mvm"},
        "reference_data_path",
    )

    assert comparison_type == "mvm"


def test_get_referenced_comparison_type_raises_on_subsection_mismatch():
    with pytest.raises(ValueError, match="which is a mvo run, not mvm"):
        _get_referenced_comparison_type(
            "mvm",
            "/unused",
            "reference",
            "ts_1985-1989_climo_1985-1989",
            {"reference": "mvo"},
            "reference_data_path",
        )


def test_get_referenced_comparison_type_auto_prefers_mvo_if_cfg_missing(tmp_path):
    comparison_type = _get_referenced_comparison_type(
        "auto",
        str(tmp_path),
        "",
        "ts_1985-1989_climo_1985-1989",
        {},
        "reference_data_path",
    )

    assert comparison_type == "mvo"


def test_get_referenced_comparison_type_auto_detects_mvm(tmp_path):
    cfg_dir = tmp_path / "post" / "analysis" / "mpas_analysis" / "mvm" / "cfg"
    cfg_dir.mkdir(parents=True)
    (cfg_dir / "mpas_analysis_ts_1985-1989_climo_1985-1989.cfg").write_text("")

    comparison_type = _get_referenced_comparison_type(
        "auto",
        str(tmp_path),
        "",
        "ts_1985-1989_climo_1985-1989",
        {},
        "reference_data_path",
    )

    assert comparison_type == "mvm"


def test_get_referenced_comparison_type_auto_raises_if_ambiguous(tmp_path):
    for comparison_type in ["mvo", "mvm"]:
        cfg_dir = (
            tmp_path / "post" / "analysis" / "mpas_analysis" / comparison_type / "cfg"
        )
        cfg_dir.mkdir(parents=True, exist_ok=True)
        (cfg_dir / "mpas_analysis_ts_1985-1989_climo_1985-1989.cfg").write_text("")

    with pytest.raises(ValueError, match="reference_comparison_type"):
        _get_referenced_comparison_type(
            "auto",
            str(tmp_path),
            "",
            "ts_1985-1989_climo_1985-1989",
            {},
            "reference_data_path",
        )
