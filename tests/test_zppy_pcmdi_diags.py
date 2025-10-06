from typing import List, Tuple
from unittest.mock import patch

import pytest

from zppy.pcmdi_diags import (
    add_pcmdi_dependencies,
    add_ts_dependencies,
    check_and_define_parameters,
    check_mvm_only_parameters_for_bash,
    check_parameters_for_bash,
    check_parameters_for_pcmdi,
    define_current_set,
    define_relevant_years,
    define_relevant_years_for_synthetic_plots,
    define_year_sets,
)
from zppy.utils import ParameterNotProvidedError


def test_define_current_set():
    # Set current_set directly
    c = {"current_set": "mean_climate", "infer_path_parameters": False}
    define_current_set(c)
    assert c["current_set"] == "mean_climate"

    c = {"current_set": "variability_modes_cpl", "infer_path_parameters": False}
    define_current_set(c)
    assert c["current_set"] == "variability_modes_cpl"

    c = {"current_set": "variability_modes_atm", "infer_path_parameters": False}
    define_current_set(c)
    assert c["current_set"] == "variability_modes_atm"

    c = {"current_set": "enso", "infer_path_parameters": False}
    define_current_set(c)
    assert c["current_set"] == "enso"

    c = {"current_set": "synthetic_plots", "infer_path_parameters": False}
    define_current_set(c)
    assert c["current_set"] == "synthetic_plots"

    c = {"current_set": "invalid_set", "infer_path_parameters": False}
    with pytest.raises(ValueError):
        define_current_set(c)

    # Infer current_set from subsection
    c = {"current_set": "", "subsection": "mean_climate", "infer_path_parameters": True}
    define_current_set(c)
    assert c["current_set"] == "mean_climate"

    c = {
        "current_set": "",
        "subsection": "variability_modes_cpl",
        "infer_path_parameters": True,
    }
    define_current_set(c)
    assert c["current_set"] == "variability_modes_cpl"

    c = {
        "current_set": "",
        "subsection": "variability_modes_atm",
        "infer_path_parameters": True,
    }
    define_current_set(c)
    assert c["current_set"] == "variability_modes_atm"

    c = {"current_set": "", "subsection": "enso", "infer_path_parameters": True}
    define_current_set(c)
    assert c["current_set"] == "enso"

    c = {
        "current_set": "",
        "subsection": "synthetic_plots",
        "infer_path_parameters": True,
    }
    define_current_set(c)
    assert c["current_set"] == "synthetic_plots"

    c = {"current_set": "", "subsection": "invalid_set", "infer_path_parameters": True}
    with pytest.raises(ValueError):
        define_current_set(c)

    c = {
        "current_set": "",
        "subsection": "mean_climate",
        "infer_path_parameters": False,
    }
    with pytest.raises(ParameterNotProvidedError):
        define_current_set(c)

    # Test case where subsection is missing with infer_path_parameters=True
    c = {"current_set": "", "infer_path_parameters": True}
    with pytest.raises(ParameterNotProvidedError):
        define_current_set(c)


def test_check_parameters_for_bash():
    # Test synthetic_plots (should not require ref_start_yr and ref_end_yr)
    c = {
        "current_set": "synthetic_plots",
        "ref_final_yr": "2000",
        "ref_start_yr": "1850",
    }
    check_parameters_for_bash(c)

    c = {"current_set": "synthetic_plots", "ref_final_yr": "", "ref_start_yr": "1850"}
    check_parameters_for_bash(c)

    c = {"current_set": "synthetic_plots", "ref_final_yr": "2000", "ref_start_yr": ""}
    check_parameters_for_bash(c)

    # Test BASE_PCMDI_SETS
    c = {"current_set": "mean_climate", "ref_final_yr": "2000", "ref_start_yr": "1850"}
    check_parameters_for_bash(c)

    c = {"current_set": "mean_climate", "ref_final_yr": "", "ref_start_yr": "1850"}
    with pytest.raises(ParameterNotProvidedError):
        check_parameters_for_bash(c)

    c = {"current_set": "mean_climate", "ref_final_yr": "2000", "ref_start_yr": ""}
    with pytest.raises(ParameterNotProvidedError):
        check_parameters_for_bash(c)

    c = {
        "current_set": "variability_modes_atm",
        "ref_final_yr": "2000",
        "ref_start_yr": "1850",
    }
    check_parameters_for_bash(c)

    c = {
        "current_set": "variability_modes_atm",
        "ref_final_yr": "",
        "ref_start_yr": "1850",
    }
    with pytest.raises(ParameterNotProvidedError):
        check_parameters_for_bash(c)

    c = {
        "current_set": "variability_modes_cpl",
        "ref_final_yr": "2000",
        "ref_start_yr": "1850",
    }
    check_parameters_for_bash(c)

    c = {
        "current_set": "variability_modes_cpl",
        "ref_final_yr": "2000",
        "ref_start_yr": "",
    }
    with pytest.raises(ParameterNotProvidedError):
        check_parameters_for_bash(c)

    c = {"current_set": "enso", "ref_final_yr": "2000", "ref_start_yr": "1850"}
    check_parameters_for_bash(c)


def test_check_parameters_for_pcmdi():
    c = {
        "current_set": "synthetic_plots",
        "figure_sets": [
            "mean_climate",
            "variability_modes",
        ],
        "cmip_enso_dir": "",
        "cmip_clim_dir": "",
        "cmip_movs_dir": "",
        "enso_viewer": False,
        "clim_viewer": True,
        "mova_viewer": True,
        "diagnostics_base_path": "diags/post",
        "infer_path_parameters": True,
    }
    check_parameters_for_pcmdi(c)
    assert c["cmip_clim_dir"] == "diags/post/pcmdi_data/metrics_data/mean_climate"
    assert c["cmip_movs_dir"] == "diags/post/pcmdi_data/metrics_data/variability_modes"
    assert c["cmip_enso_dir"] == "placeholder_dir"

    c = {
        "current_set": "mean_climate",
        "figure_sets": [
            "mean_climate",
            "variability_modes",
        ],
        "cmip_enso_dir": "",
        "cmip_clim_dir": "",
        "cmip_movs_dir": "",
        "diagnostics_base_path": "diags/post",
        "infer_path_parameters": True,
    }
    check_parameters_for_pcmdi(c)
    assert c["cmip_clim_dir"] == ""
    assert c["cmip_movs_dir"] == ""
    assert c["cmip_enso_dir"] == ""

    c = {
        "current_set": "synthetic_plots",
        "figure_sets": [
            "mean_climate",
            "variability_modes",
        ],
        "cmip_enso_dir": "",
        "cmip_clim_dir": "",
        "cmip_movs_dir": "",
        "enso_viewer": False,
        "clim_viewer": True,
        "diagnostics_base_path": "diags/post",
        "infer_path_parameters": False,
    }
    with pytest.raises(ParameterNotProvidedError):
        check_parameters_for_pcmdi(c)

    c = {
        "current_set": "mean_climate",
        "figure_sets": [
            "mean_climate",
            "variability_modes",
        ],
        "cmip_enso_dir": "",
        "cmip_clim_dir": "",
        "cmip_movs_dir": "",
        "diagnostics_base_path": "diags/post",
        "infer_path_parameters": False,
    }
    check_parameters_for_pcmdi(c)
    assert c["cmip_clim_dir"] == ""
    assert c["cmip_movs_dir"] == ""
    assert c["cmip_enso_dir"] == ""

    # Test enso_metric figure set
    c = {
        "current_set": "synthetic_plots",
        "figure_sets": ["enso_metric"],
        "cmip_enso_dir": "",
        "cmip_clim_dir": "",
        "cmip_movs_dir": "",
        "enso_viewer": False,
        "clim_viewer": True,
        "mova_viewer": True,
        "diagnostics_base_path": "diags/post",
        "infer_path_parameters": True,
    }
    check_parameters_for_pcmdi(c)
    assert c["cmip_enso_dir"] == "placeholder_dir"

    # Test when parameters are already defined
    c = {
        "current_set": "synthetic_plots",
        "figure_sets": ["mean_climate"],
        "cmip_enso_dir": "/custom/enso",
        "cmip_clim_dir": "/custom/clim",
        "cmip_movs_dir": "/custom/movs",
        "enso_viewer": False,
        "clim_viewer": True,
        "mova_viewer": True,
        "diagnostics_base_path": "diags/post",
        "infer_path_parameters": True,
    }
    check_parameters_for_pcmdi(c)
    assert c["cmip_clim_dir"] == "/custom/clim"  # Should not change


def test_define_year_sets():
    # Should use ts_years
    c = {
        "current_set": "mean_climate",
        "ts_years": "2000:2010:5",
    }
    actual: List[Tuple[int, int]] = define_year_sets(c)
    expected = [(2000, 2004), (2005, 2009)]
    assert actual == expected

    # Should use available year set
    c = {
        "current_set": "synthetic_plots",
        "ts_years": "2000:2010:5",
        "enso_years": "2001-2004",
    }
    actual = define_year_sets(c)
    expected = [(2001, 2004)]
    assert actual == expected

    # Should use the first available year set
    c = {
        "current_set": "synthetic_plots",
        "ts_years": "2000:2010:5",
        "clim_years": "2001-2004",
        "mova_years": "2002-2003",
        "movc_years": "2003-2004",
        "enso_years": "2004-2005",
    }
    actual = define_year_sets(c)
    expected = [(2001, 2004)]
    assert actual == expected

    # Should default to ts_years
    c = {
        "current_set": "synthetic_plots",
        "ts_years": "2000:2010:5",
    }
    actual = define_year_sets(c)
    expected = [(2000, 2004), (2005, 2009)]
    assert actual == expected


def test_check_mvm_only_parameters_for_bash():
    # Test with all required parameters present
    c = {
        "current_set": "mean_climate",
        "reference_data_path_ts": "/path/to/ref/ts",
        "model_name_ref": "CESM2",
        "model_tableID_ref": "Amon",
        "ref_start_yr": "1850",
        "ts_subsection": "atm_monthly_180x360_aave",
    }
    check_mvm_only_parameters_for_bash(c)

    # Test missing reference_data_path_ts
    c = {
        "current_set": "mean_climate",
        "model_name_ref": "CESM2",
        "model_tableID_ref": "Amon",
        "ref_start_yr": "1850",
        "ts_subsection": "atm_monthly_180x360_aave",
    }
    with pytest.raises(ParameterNotProvidedError):
        check_mvm_only_parameters_for_bash(c)

    # Test missing model_name_ref
    c = {
        "current_set": "mean_climate",
        "reference_data_path_ts": "/path/to/ref/ts",
        "model_tableID_ref": "Amon",
        "ref_start_yr": "1850",
        "ts_subsection": "atm_monthly_180x360_aave",
    }
    with pytest.raises(ParameterNotProvidedError):
        check_mvm_only_parameters_for_bash(c)

    # Test missing model_tableID_ref
    c = {
        "current_set": "mean_climate",
        "reference_data_path_ts": "/path/to/ref/ts",
        "model_name_ref": "CESM2",
        "ref_start_yr": "1850",
        "ts_subsection": "atm_monthly_180x360_aave",
    }
    with pytest.raises(ParameterNotProvidedError):
        check_mvm_only_parameters_for_bash(c)

    # Test missing ref_start_yr for BASE_PCMDI_SETS
    c = {
        "current_set": "mean_climate",
        "reference_data_path_ts": "/path/to/ref/ts",
        "model_name_ref": "CESM2",
        "model_tableID_ref": "Amon",
        "ref_start_yr": "",
        "ts_subsection": "atm_monthly_180x360_aave",
    }
    with pytest.raises(ParameterNotProvidedError):
        check_mvm_only_parameters_for_bash(c)

    # Test missing ts_subsection for BASE_PCMDI_SETS
    c = {
        "current_set": "mean_climate",
        "reference_data_path_ts": "/path/to/ref/ts",
        "model_name_ref": "CESM2",
        "model_tableID_ref": "Amon",
        "ref_start_yr": "1850",
        "ts_subsection": "",
    }
    with pytest.raises(ParameterNotProvidedError):
        check_mvm_only_parameters_for_bash(c)

    # Test synthetic_plots (should not require ref_start_yr and ts_subsection)
    c = {
        "current_set": "synthetic_plots",
        "reference_data_path_ts": "/path/to/ref/ts",
        "model_name_ref": "CESM2",
        "model_tableID_ref": "Amon",
    }
    check_mvm_only_parameters_for_bash(c)


def test_check_and_define_parameters():
    # Test model_vs_obs run_type
    c = {
        "run_type": "model_vs_obs",
        "sub": "mean_climate",
        "year1": 2000,
        "year2": 2010,
        "ts_num_years": 1,
        "obs_ts": "",
        "diagnostics_base_path": "/diags",
        "infer_path_parameters": True,
    }
    check_and_define_parameters(c)
    assert c["prefix"] == "pcmdi_diags_mean_climate_model_vs_obs_2000-2010"
    assert c["obs_ts"] == "/diags/observations/Atm/time-series/"

    # Test model_vs_model run_type
    c = {
        "run_type": "model_vs_model",
        "sub": "variability_modes_atm",
        "year1": 2000,
        "year2": 2010,
        "ref_year1": 1850,
        "ref_year2": 1900,
        "current_set": "variability_modes_atm",
        "reference_data_path_ts": "/ref/path/ts",
        "model_name_ref": "CESM2",
        "model_tableID_ref": "Amon",
        "ref_start_yr": "1850",
        "ts_subsection": "atm_monthly_180x360_aave",
        "reference_data_path": "/ref/path/post/analysis",
        "grid": "180x360_aave",
        "infer_path_parameters": True,
        "clim_viewer": True,
    }
    check_and_define_parameters(c)
    assert (
        c["prefix"]
        == "pcmdi_diags_variability_modes_atm_model_vs_model_2000-2010_vs_1850-1900"
    )
    assert (
        c["reference_data_path_ts"]
        == "/ref/path/ts"  # Value is set, so won't be changed
    )

    # Test invalid run_type
    c = {
        "run_type": "invalid_type",
        "sub": "mean_climate",
        "year1": 2000,
        "year2": 2010,
    }
    with pytest.raises(ValueError):
        check_and_define_parameters(c)

    # Test model_vs_obs without ts_num_years (should not set obs_ts)
    c = {
        "run_type": "model_vs_obs",
        "sub": "mean_climate",
        "year1": 2000,
        "year2": 2010,
        "obs_ts": "",
    }
    check_and_define_parameters(c)
    assert c["prefix"] == "pcmdi_diags_mean_climate_model_vs_obs_2000-2010"
    assert c["obs_ts"] == ""


def test_define_relevant_years():
    c = {
        "current_set": "mean_climate",
        "year1": 2000,
        "year2": 2010,
    }
    define_relevant_years(c)
    assert c["clim_years"] == "2000-2010"

    c = {
        "current_set": "variability_modes_cpl",
        "year1": 1990,
        "year2": 2000,
    }
    define_relevant_years(c)
    assert c["movc_years"] == "1990-2000"

    c = {
        "current_set": "variability_modes_atm",
        "year1": 1980,
        "year2": 1990,
    }
    define_relevant_years(c)
    assert c["mova_years"] == "1980-1990"

    c = {
        "current_set": "enso",
        "year1": 1970,
        "year2": 1980,
    }
    define_relevant_years(c)
    assert c["enso_years"] == "1970-1980"

    # Test synthetic_plots (should not set any years)
    c = {
        "current_set": "synthetic_plots",
        "year1": 2000,
        "year2": 2010,
    }
    with pytest.raises(ValueError):
        define_relevant_years(c)


def test_define_relevant_years_for_synthetic_plots():
    c = {
        "current_set": "synthetic_plots",
        "year1": 2000,
        "year2": 2010,
        "clim_years": "",
        "mova_years": "",
        "movc_years": "",
        "enso_years": "",
    }
    define_relevant_years_for_synthetic_plots(c)
    assert c["clim_years"] == "2000-2010"
    assert c["mova_years"] == "2000-2010"
    assert c["movc_years"] == "2000-2010"
    assert c["enso_years"] == "2000-2010"

    c = {
        "current_set": "synthetic_plots",
        "year1": 1990,
        "year2": 2000,
        "clim_years": "1991-1995",
        "mova_years": "",
        "movc_years": "",
        "enso_years": "",
    }
    define_relevant_years_for_synthetic_plots(c)
    assert c["clim_years"] == "1991-1995"  # Should not change
    assert c["mova_years"] == "1990-2000"
    assert c["movc_years"] == "1990-2000"
    assert c["enso_years"] == "1990-2000"

    c = {
        "current_set": "mean_climate",
        "year1": 2000,
        "year2": 2010,
        "clim_years": "",
        "mova_years": "",
        "movc_years": "",
        "enso_years": "",
    }
    with pytest.raises(ValueError):
        define_relevant_years_for_synthetic_plots(c)


def test_add_ts_dependencies():
    dependencies: List[str] = []
    c = {
        "current_set": "mean_climate",
        "ts_num_years": 5,
    }
    script_dir = "/scripts"
    yr = 2000

    with patch("zppy.pcmdi_diags.add_dependencies") as mock_add_dependencies:
        add_ts_dependencies(c, dependencies, script_dir, yr)
        mock_add_dependencies.assert_called_once_with(
            dependencies,
            script_dir,
            "ts",
            "atm_monthly_180x360_aave",
            2000,
            2004,
            5,
        )

    # Test with non-BASE_PCMDI_SETS (should not call add_dependencies)
    dependencies = []
    c = {
        "current_set": "synthetic_plots",
        "ts_num_years": 5,
    }

    with patch("zppy.pcmdi_diags.add_dependencies") as mock_add_dependencies:
        add_ts_dependencies(c, dependencies, script_dir, yr)
        mock_add_dependencies.assert_not_called()


@patch("os.path.exists")
def test_add_pcmdi_dependencies(mock_exists):
    dependencies: List[str] = []
    c = {
        "run_type": "model_vs_obs",
        "year1": 2000,
        "year2": 2010,
        "figure_sets": ["mean_climate", "variability_modes", "enso_metric"],
        "clim_viewer": True,
        "mova_viewer": True,
        "movc_viewer": True,
        "enso_viewer": False,
    }
    script_dir = "/scripts"

    # Mock all status files as existing
    mock_exists.return_value = True

    add_pcmdi_dependencies(c, dependencies, script_dir)

    expected_dependencies = [
        "/scripts/pcmdi_diags_mean_climate_model_vs_obs_2000-2010.status",
        "/scripts/pcmdi_diags_variability_modes_cpl_model_vs_obs_2000-2010.status",
        "/scripts/pcmdi_diags_variability_modes_atm_model_vs_obs_2000-2010.status",
    ]
    assert set(dependencies) == set(expected_dependencies)

    # Test model_vs_model run_type
    dependencies = []
    c = {
        "run_type": "model_vs_model",
        "year1": 2000,
        "year2": 2010,
        "ref_year1": 1850,
        "ref_year2": 1900,
        "figure_sets": ["mean_climate"],
        "clim_viewer": True,
        "enso_viewer": False,
        "mova_viewer": False,
        "movc_viewer": False,
    }

    add_pcmdi_dependencies(c, dependencies, script_dir)
    expected_dependencies = [
        "/scripts/pcmdi_diags_mean_climate_model_vs_model_2000-2010_vs_1850-1900.status",
    ]
    assert dependencies == expected_dependencies

    # Test with non-existing status files
    dependencies = []
    c = {
        "run_type": "model_vs_obs",
        "year1": 2000,
        "year2": 2010,
        "figure_sets": ["mean_climate"],
        "clim_viewer": True,
        "enso_viewer": False,
        "mova_viewer": False,
        "movc_viewer": False,
    }
    mock_exists.return_value = False

    add_pcmdi_dependencies(c, dependencies, script_dir)
    assert dependencies == []

    # Test missing run_type
    c = {
        "year1": 2000,
        "year2": 2010,
        "figure_sets": ["mean_climate"],
    }
    with pytest.raises(ParameterNotProvidedError):
        add_pcmdi_dependencies(c, dependencies, script_dir)

    # Test duplicate dependencies are not added
    dependencies = ["/scripts/pcmdi_diags_mean_climate_model_vs_obs_2000-2010.status"]
    c = {
        "run_type": "model_vs_obs",
        "year1": 2000,
        "year2": 2010,
        "figure_sets": ["mean_climate"],
        "clim_viewer": True,
        "enso_viewer": False,
        "mova_viewer": False,
        "movc_viewer": False,
    }
    mock_exists.return_value = True

    add_pcmdi_dependencies(c, dependencies, script_dir)
    # Should still only have one instance
    assert len(dependencies) == 1
    assert (
        dependencies[0]
        == "/scripts/pcmdi_diags_mean_climate_model_vs_obs_2000-2010.status"
    )
