import pytest

from zppy.pcmdi_diags import (
    check_parameters_for_bash,
    check_parameters_for_pcmdi,
    define_current_set,
)
from zppy.utils import ParameterNotProvidedError


def test_define_current_set():
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


def test_check_parameters_for_bash():
    c = {"current_set": "mean_climate", "ref_final_yr": "2000", "ref_start_yr": "1850"}
    check_parameters_for_bash(c)

    c = {"current_set": "mean_climate", "ref_final_yr": "", "ref_start_yr": "1850"}
    with pytest.raises(ParameterNotProvidedError):
        check_parameters_for_bash(c)

    c = {"current_set": "mean_climate", "ref_final_yr": "2000", "ref_start_yr": ""}
    with pytest.raises(ParameterNotProvidedError):
        check_parameters_for_bash(c)

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
        "diagnostics_base_path": "diags/post",
        "infer_path_parameters": True,
    }
    check_parameters_for_pcmdi(c)
    assert c["cmip_clim_dir"] == "diags/post/pcmdi_data/metrics_data/mean_climate"
    assert c["cmip_movs_dir"] == "diags/post/pcmdi_data/metrics_data/variability_modes"
    assert c["cmip_enso_dir"] == ""

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
