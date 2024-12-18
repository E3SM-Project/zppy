from typing import Any, Dict, List

import pytest

from zppy.global_time_series import determine_and_add_dependencies, determine_components


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
