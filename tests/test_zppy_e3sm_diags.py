from typing import Any, Dict, List

import pytest

from zppy.e3sm_diags import (
    add_climo_dependencies,
    add_ts_dependencies,
    check_and_define_parameters,
    check_mvm_only_parameters_for_bash,
    check_parameter_defined,
    check_parameters_for_bash,
    check_set_specific_parameter,
)
from zppy.utils import ParameterNotProvidedError


def test_check_parameter_defined():
    c = {"a": 1, "b": 2, "c": ""}
    check_parameter_defined(c, "a")
    with pytest.raises(ParameterNotProvidedError):
        check_parameter_defined(c, "c")
    with pytest.raises(ParameterNotProvidedError):
        check_parameter_defined(c, "d")


def test_check_set_specific_parameter():
    # Parameter is required
    # a, b need parameter p, and we want sets a, b, c
    c = {"sets": ["a", "b", "c"], "p": "exists"}
    check_set_specific_parameter(c, set(["a", "b"]), "p")

    # Parameter isn't required based on the sets we want
    # z needs parameter p, but we only want sets a, b, c
    c = {"sets": ["a", "b", "c"], "p": ""}
    check_set_specific_parameter(c, set(["z"]), "p")

    # Parameter is required
    # a, b need parameter p, and we want sets a, b, c
    c = {"sets": ["a", "b", "c"], "p": ""}
    with pytest.raises(ParameterNotProvidedError):
        check_set_specific_parameter(c, set(["a", "b"]), "p")


def test_check_parameters_for_bash():
    # diurnal_cycle
    c = {"sets": ["diurnal_cycle"], "climo_diurnal_frequency": "diurnal_8xdaily"}
    check_parameters_for_bash(c)
    c = {"sets": ["diurnal_cycle"], "climo_diurnal_frequency": ""}
    with pytest.raises(ParameterNotProvidedError):
        check_parameters_for_bash(c)

    # enso_diags
    c = {"sets": ["enso_diags"], "ref_start_yr": "1990"}
    check_parameters_for_bash(c)
    c = {"sets": ["enso_diags"], "ref_start_yr": ""}
    with pytest.raises(ParameterNotProvidedError):
        check_parameters_for_bash(c)

    # qbo
    c = {"sets": ["qbo"], "ref_final_yr": "2000", "ref_start_yr": "1990"}
    check_parameters_for_bash(c)
    c = {"sets": ["qbo"], "ref_final_yr": "", "ref_start_yr": "1990"}
    with pytest.raises(ParameterNotProvidedError):
        check_parameters_for_bash(c)
    c = {"sets": ["qbo"], "ref_final_yr": "2000", "ref_start_yr": ""}
    with pytest.raises(ParameterNotProvidedError):
        check_parameters_for_bash(c)


def test_check_mvm_only_parameters_for_bash():
    z0 = {"diff_title": "a", "ref_name": "b", "short_ref_name": "c"}
    z1 = {"diff_title": "", "ref_name": "b", "short_ref_name": "c"}
    z2 = {"diff_title": "a", "ref_name": "", "short_ref_name": "c"}
    z3 = {"diff_title": "a", "ref_name": "b", "short_ref_name": ""}
    c: Dict[str, Any] = {"sets": []}
    c.update(z0)
    check_mvm_only_parameters_for_bash(c)
    c.update(z1)
    with pytest.raises(ParameterNotProvidedError):
        check_mvm_only_parameters_for_bash(c)
    c.update(z2)
    with pytest.raises(ParameterNotProvidedError):
        check_mvm_only_parameters_for_bash(c)
    c.update(z3)
    with pytest.raises(ParameterNotProvidedError):
        check_mvm_only_parameters_for_bash(c)

    d0 = {
        "ref_final_yr": "2000",
        "ref_start_yr": "1990",
        "ts_num_years_ref": "2",
        "ts_subsection": "sub",
    }
    d1 = {
        "ref_final_yr": "",
        "ref_start_yr": "1990",
        "ts_num_years_ref": "2",
        "ts_subsection": "sub",
    }
    d2 = {
        "ref_final_yr": "2000",
        "ref_start_yr": "",
        "ts_num_years_ref": "2",
        "ts_subsection": "sub",
    }
    d3 = {
        "ref_final_yr": "2000",
        "ref_start_yr": "1990",
        "ts_num_years_ref": "",
        "ts_subsection": "sub",
    }
    d4 = {
        "ref_final_yr": "2000",
        "ref_start_yr": "1990",
        "ts_num_years_ref": "2",
        "ts_subsection": "",
    }

    # Load required parameters into all of the dicts above.
    d0.update(z0)
    d1.update(z0)
    d2.update(z0)
    d3.update(z0)
    d4.update(z0)

    # area_mean_time_series
    c = {"sets": ["area_mean_time_series"]}
    c.update(d0)
    check_mvm_only_parameters_for_bash(c)
    c.update(d1)
    check_mvm_only_parameters_for_bash(c)  # ref_final_yr not needed
    c.update(d2)
    check_mvm_only_parameters_for_bash(c)  # ref_start_yr not needed
    c.update(d3)
    with pytest.raises(ParameterNotProvidedError):
        check_mvm_only_parameters_for_bash(c)
    c.update(d4)
    with pytest.raises(ParameterNotProvidedError):
        check_mvm_only_parameters_for_bash(c)

    # enso_diags
    c = {"sets": ["enso_diags"]}
    c.update(d0)
    check_mvm_only_parameters_for_bash(c)
    c.update(d1)
    with pytest.raises(ParameterNotProvidedError):
        check_mvm_only_parameters_for_bash(c)
    c.update(d2)
    check_mvm_only_parameters_for_bash(c)  # ref_start_yr not needed
    c.update(d3)
    with pytest.raises(ParameterNotProvidedError):
        check_mvm_only_parameters_for_bash(c)
    c.update(d4)
    with pytest.raises(ParameterNotProvidedError):
        check_mvm_only_parameters_for_bash(c)

    # qbo
    c = {"sets": ["qbo"]}
    c.update(d0)
    check_mvm_only_parameters_for_bash(c)
    c.update(d1)
    check_mvm_only_parameters_for_bash(c)  # ref_final_yr not needed
    c.update(d2)
    check_mvm_only_parameters_for_bash(c)  # ref_start_yr not needed
    c.update(d3)
    with pytest.raises(ParameterNotProvidedError):
        check_mvm_only_parameters_for_bash(c)
    c.update(d4)
    with pytest.raises(ParameterNotProvidedError):
        check_mvm_only_parameters_for_bash(c)

    # streamflow
    c = {"sets": ["streamflow"]}
    c.update(d0)
    check_mvm_only_parameters_for_bash(c)
    c.update(d1)
    with pytest.raises(ParameterNotProvidedError):
        check_mvm_only_parameters_for_bash(c)
    c.update(d2)
    with pytest.raises(ParameterNotProvidedError):
        check_mvm_only_parameters_for_bash(c)
    c.update(d3)
    with pytest.raises(ParameterNotProvidedError):
        check_mvm_only_parameters_for_bash(c)
    c.update(d4)
    with pytest.raises(ParameterNotProvidedError):
        check_mvm_only_parameters_for_bash(c)

    # tc_analysis
    c = {"sets": ["tc_analysis"]}
    c.update(d0)
    check_mvm_only_parameters_for_bash(c)
    c.update(d1)
    with pytest.raises(ParameterNotProvidedError):
        check_mvm_only_parameters_for_bash(c)
    c.update(d2)
    with pytest.raises(ParameterNotProvidedError):
        check_mvm_only_parameters_for_bash(c)
    c.update(d3)
    check_mvm_only_parameters_for_bash(c)  # ts_num_years_ref not needed
    c.update(d4)
    check_mvm_only_parameters_for_bash(c)  # ts_subsection not needed

    # tropical_subseasonal
    c = {"sets": ["tropical_subseasonal"]}
    c.update(d0)
    check_mvm_only_parameters_for_bash(c)
    c.update(d1)
    with pytest.raises(ParameterNotProvidedError):
        check_mvm_only_parameters_for_bash(c)
    c.update(d2)
    with pytest.raises(ParameterNotProvidedError):
        check_mvm_only_parameters_for_bash(c)
    c.update(d3)
    with pytest.raises(ParameterNotProvidedError):
        check_mvm_only_parameters_for_bash(c)
    c.update(d4)
    with pytest.raises(ParameterNotProvidedError):
        check_mvm_only_parameters_for_bash(c)


def test_check_and_define_parameters():
    # test_zppy_utils.py tests the inference functionality turned off.
    # So, we'll only test it turned on here.
    inferences = {"infer_path_parameters": True, "infer_section_parameters": True}
    prefix_requirements = {
        "subsection": "sub",
        "tag": "tag",
        "year1": 1990,
        "year2": 2000,
        "ref_year1": 1980,
        "ref_year2": 1990,
    }
    base: Dict[str, Any] = {"diagnostics_base_path": "diags/post"}
    base.update(inferences)
    base.update(prefix_requirements)

    mvm_base = dict()
    mvm_base.update(base)
    required_for_mvm = {
        "diff_title": "diff_title",
        "ref_name": "ref_name",
        "short_ref_name": "short_ref_name",
    }
    mvm_base.update(required_for_mvm)

    # No sets, mvo
    c: Dict[str, Any] = {
        "sets": [],
        "run_type": "model_vs_obs",
        "reference_data_path": "a",
    }
    c.update(base)
    check_and_define_parameters(c)
    assert c["reference_data_path"] == "a"
    assert c["prefix"] == "e3sm_diags_sub_tag_1990-2000"

    # No sets, mvm
    c = {"sets": [], "run_type": "model_vs_model", "reference_data_path": ""}
    c.update(mvm_base)
    check_and_define_parameters(c)
    assert c["reference_data_path"] == "diags/post/observations/Atm/climatology/"
    assert c["prefix"] == "e3sm_diags_sub_tag_1990-2000_vs_1980-1990"

    # No sets, bad run_type
    c = {"sets": [], "run_type": "invalid", "reference_data_path": ""}
    c.update(base)
    with pytest.raises(ValueError):
        check_and_define_parameters(c)

    # ts_num_years => obs_ts, mvo
    c = {
        "sets": [],
        "run_type": "model_vs_obs",
        "reference_data_path": "",
        "ts_num_years": 3,
        "obs_ts": "a",
    }
    c.update(base)
    check_and_define_parameters(c)
    assert c["obs_ts"] == "a"

    c = {
        "sets": [],
        "run_type": "model_vs_obs",
        "reference_data_path": "",
        "ts_num_years": 3,
        "obs_ts": "",
    }
    c.update(base)
    check_and_define_parameters(c)
    assert c["obs_ts"] == "diags/post/observations/Atm/time-series/"

    # ts_num_years => obs_ts, mvm
    c = {
        "sets": [],
        "run_type": "model_vs_model",
        "reference_data_path": "",
        "ts_num_years": 3,
        "obs_ts": "a",
    }
    c.update(mvm_base)
    check_and_define_parameters(c)
    assert c["obs_ts"] == "a"

    c = {
        "sets": [],
        "run_type": "model_vs_model",
        "reference_data_path": "",
        "ts_num_years": 3,
        "obs_ts": "",
    }
    c.update(mvm_base)
    check_and_define_parameters(c)
    assert c["obs_ts"] == "diags/post/observations/Atm/time-series/"

    # area_mean_time_series/enso_diags/qbo, mvm
    for diags_set in ["area_mean_time_series", "enso_diags", "qbo"]:
        c = {
            "sets": [diags_set],
            "run_type": "model_vs_model",
            "reference_data_path": "",
            "reference_data_path_ts": "a",
            "grid": "grid",
        }
        c.update(mvm_base)
        check_and_define_parameters(c)
        assert c["reference_data_path_ts"] == "a"

        c = {
            "sets": [diags_set],
            "run_type": "model_vs_model",
            "reference_data_path": "",
            "reference_data_path_ts": "",
            "grid": "grid",
        }
        c.update(mvm_base)
        check_and_define_parameters(c)
        assert c["reference_data_path_ts"] == "diags/post/atm/grid/ts/monthly"

    # diurnal_cycle, mvo
    c = {
        "sets": ["diurnal_cycle"],
        "run_type": "model_vs_obs",
        "reference_data_path": "",
        "dc_obs_climo": "a",
    }
    c.update(base)
    check_and_define_parameters(c)
    assert c["dc_obs_climo"] == "a"

    c = {
        "sets": ["diurnal_cycle"],
        "run_type": "model_vs_obs",
        "reference_data_path": "",
        "dc_obs_climo": "",
    }
    c.update(base)
    check_and_define_parameters(c)
    assert c["dc_obs_climo"] == "diags/post/observations/Atm/climatology/"

    # diurnal_cycle, mvm
    c = {
        "sets": ["diurnal_cycle"],
        "run_type": "model_vs_model",
        "reference_data_path": "",
        "reference_data_path_climo_diurnal": "a",
        "grid": "grid",
    }
    c.update(mvm_base)
    check_and_define_parameters(c)
    assert c["reference_data_path_climo_diurnal"] == "a"

    c = {
        "sets": ["diurnal_cycle"],
        "run_type": "model_vs_model",
        "reference_data_path": "",
        "reference_data_path_climo_diurnal": "",
        "grid": "grid",
    }
    c.update(mvm_base)
    check_and_define_parameters(c)
    assert (
        c["reference_data_path_climo_diurnal"]
        == "diags/post/atm/grid/clim_diurnal_8xdaily"
    )

    # streamflow, mvo
    c = {
        "sets": ["streamflow"],
        "run_type": "model_vs_obs",
        "reference_data_path": "",
        "streamflow_obs_ts": "a",
        "ts_num_years": 3,
        "obs_ts": "",
    }
    c.update(base)
    check_and_define_parameters(c)
    assert c["streamflow_obs_ts"] == "a"

    c = {
        "sets": ["streamflow"],
        "run_type": "model_vs_obs",
        "reference_data_path": "",
        "streamflow_obs_ts": "",
        "ts_num_years": 3,
        "obs_ts": "",
    }
    c.update(base)
    check_and_define_parameters(c)
    assert c["streamflow_obs_ts"] == "diags/post/observations/Atm/time-series/"

    # streamflow, mvm
    c = {
        "sets": ["streamflow"],
        "run_type": "model_vs_model",
        "reference_data_path": "",
        "reference_data_path_ts_rof": "a",
        "gauges_path": "b",
    }
    c.update(mvm_base)
    check_and_define_parameters(c)
    assert c["reference_data_path_ts_rof"] == "a"
    assert c["gauges_path"] == "b"

    c = {
        "sets": ["streamflow"],
        "run_type": "model_vs_model",
        "reference_data_path": "",
        "reference_data_path_ts_rof": "",
        "gauges_path": "",
    }
    c.update(mvm_base)
    check_and_define_parameters(c)
    assert c["reference_data_path_ts_rof"] == "diags/post/rof/native/ts/monthly"
    assert (
        c["gauges_path"]
        == "diags/post/observations/Atm/time-series/GSIM/GSIM_catchment_characteristics_all_1km2.csv"
    )

    # tc_analysis, mvo
    c = {
        "sets": ["tc_analysis"],
        "run_type": "model_vs_obs",
        "reference_data_path": "",
        "tc_obs": "a",
    }
    c.update(base)
    check_and_define_parameters(c)
    assert c["tc_obs"] == "a"

    c = {
        "sets": ["tc_analysis"],
        "run_type": "model_vs_obs",
        "reference_data_path": "",
        "tc_obs": "",
    }
    c.update(base)
    check_and_define_parameters(c)
    assert c["tc_obs"] == "diags/post/observations/Atm/tc-analysis/"

    # tc_analysis, mvm
    c = {
        "sets": ["tc_analysis"],
        "run_type": "model_vs_model",
        "reference_data_path": "",
        "tc_obs": "a",
        "reference_data_path_tc": "b",
    }
    c.update(mvm_base)
    check_and_define_parameters(c)
    assert c["tc_obs"] == "a"
    assert c["reference_data_path_tc"] == "b"

    c = {
        "sets": ["tc_analysis"],
        "run_type": "model_vs_model",
        "reference_data_path": "",
        "tc_obs": "",
        "reference_data_path_tc": "",
    }
    c.update(mvm_base)
    check_and_define_parameters(c)
    assert c["tc_obs"] == "diags/post/observations/Atm/tc-analysis/"
    assert c["reference_data_path_tc"] == "diags/post/atm/tc-analysis_1980_1990"

    # tropical_subseasonal, mvm
    c = {
        "sets": ["tropical_subseasonal"],
        "run_type": "model_vs_model",
        "reference_data_path": "",
        "reference_data_path_ts_daily": "a",
        "grid": "grid",
    }
    c.update(mvm_base)
    check_and_define_parameters(c)
    assert c["reference_data_path_ts_daily"] == "a"

    c = {
        "sets": ["tropical_subseasonal"],
        "run_type": "model_vs_model",
        "reference_data_path": "",
        "reference_data_path_ts_daily": "",
        "grid": "grid",
    }
    c.update(mvm_base)
    check_and_define_parameters(c)
    assert c["reference_data_path_ts_daily"] == "diags/post/atm/grid/ts/daily"


def test_add_climo_dependencies():
    base: Dict[str, Any] = {"year1": 1980, "year2": 1990}
    sets = [
        "lat_lon",
        "lat_lon_land",
        "zonal_mean_xy",
        "zonal_mean_2d",
        "polar",
        "cosp_histogram",
        "meridional_mean_2d",
        "annual_cycle_zonal_mean",
        "zonal_mean_2d_stratosphere",
    ]
    for diags_set in sets:
        c: Dict[str, Any] = {"sets": [diags_set], "climo_subsection": "csub"}
        c.update(base)
        dependencies: List[str] = []
        add_climo_dependencies(c, dependencies, "script_dir")
        assert dependencies == ["script_dir/climo_csub_1980-1990.status"]

    c = {"sets": ["diurnal_cycle"], "climo_diurnal_subsection": "cdsub"}
    c.update(base)
    dependencies = []
    add_climo_dependencies(c, dependencies, "script_dir")
    assert dependencies == ["script_dir/climo_cdsub_1980-1990.status"]
    c = {"sets": ["diurnal_cycle"]}
    c.update(base)
    dependencies = []
    with pytest.raises(ParameterNotProvidedError):
        add_climo_dependencies(c, dependencies, "script_dir")

    c = {"sets": ["tc_analysis"]}
    c.update(base)
    dependencies = []
    add_climo_dependencies(c, dependencies, "script_dir")
    assert dependencies == ["script_dir/tc_analysis_1980-1990.status"]


def test_add_ts_dependencies():
    base: Dict[str, Any] = {
        "ts_num_years": 5,
        "ts_subsection": "sub",
        "ts_daily_subsection": "dsub",
    }
    sets = ["area_mean_time_series", "enso_diags", "qbo"]
    for diags_set in sets:
        c: Dict[str, Any] = {"sets": [diags_set]}
        c.update(base)
        dependencies: List[str] = []
        add_ts_dependencies(c, dependencies, "script_dir", 1980)
        assert dependencies == [
            "script_dir/ts_sub_1980-1984-0005.status",
        ]

    c = {"sets": ["streamflow"]}
    c.update(base)
    dependencies = []
    add_ts_dependencies(c, dependencies, "script_dir", 1980)
    assert dependencies == ["script_dir/ts_rof_monthly_1980-1984-0005.status"]

    c = {"sets": ["tropical_subseasonal"]}
    c.update(base)
    dependencies = []
    add_ts_dependencies(c, dependencies, "script_dir", 1980)
    assert dependencies == ["script_dir/ts_dsub_1980-1984-0005.status"]
