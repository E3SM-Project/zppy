import pytest

from zppy.e3sm_to_cmip import check_and_define_parameters, check_parameters_for_bash
from zppy.utils import ParameterNotProvidedError


def test_check_parameters_for_bash():
    c = {"ts_grid": "grid"}
    check_parameters_for_bash(c)

    c = {"ts_grid": ""}
    with pytest.raises(ParameterNotProvidedError):
        check_parameters_for_bash(c)

    c = {"component": "atm", "ts_atm_grid": "atm_grid"}
    check_parameters_for_bash(c)
    c = {"component": "lnd", "ts_land_grid": "land_grid"}
    check_parameters_for_bash(c)

    c = {"component": "atm", "ts_land_grid": "land_grid"}
    with pytest.raises(ParameterNotProvidedError):
        check_parameters_for_bash(c)
    c = {"component": "lnd", "ts_atm_grid": "atm_grid"}
    with pytest.raises(ParameterNotProvidedError):
        check_parameters_for_bash(c)

    c = {"ts_atm_grid": "atm_grid"}
    with pytest.raises(ParameterNotProvidedError):
        check_parameters_for_bash(c)
    c = {"ts_land_grid": "land_grid"}
    with pytest.raises(ParameterNotProvidedError):
        check_parameters_for_bash(c)


def test_check_and_define_parameters():
    sub = "name_of_this_subsection"

    # Guess the subsection
    c = {"ts_subsection": "subsection", "guess_section_parameters": True}
    check_and_define_parameters(c, sub)
    assert c["ts_subsection"] == "subsection"

    c = {"ts_subsection": "", "guess_section_parameters": True}
    check_and_define_parameters(c, sub)
    assert c["ts_subsection"] == "name_of_this_subsection"

    c = {
        "component": "atm",
        "ts_atm_subsection": "atm_subsection",
        "guess_section_parameters": True,
    }
    check_and_define_parameters(c, sub)
    assert c["ts_subsection"] == "atm_subsection"
    c = {
        "component": "lnd",
        "ts_land_subsection": "land_subsection",
        "guess_section_parameters": True,
    }
    check_and_define_parameters(c, sub)
    assert c["ts_subsection"] == "land_subsection"

    c = {
        "component": "atm",
        "ts_land_subsection": "land_subsection",
        "guess_section_parameters": True,
    }
    check_and_define_parameters(c, sub)
    assert c["ts_subsection"] == "name_of_this_subsection"
    c = {
        "component": "lnd",
        "ts_atm_subsection": "atm_subsection",
        "guess_section_parameters": True,
    }
    check_and_define_parameters(c, sub)
    assert c["ts_subsection"] == "name_of_this_subsection"

    c = {"ts_atm_subsection": "atm_subsection", "guess_section_parameters": True}
    check_and_define_parameters(c, sub)
    assert c["ts_subsection"] == "name_of_this_subsection"
    c = {"ts_land_subsection": "land_subsection", "guess_section_parameters": True}
    check_and_define_parameters(c, sub)
    assert c["ts_subsection"] == "name_of_this_subsection"

    c = {"guess_section_parameters": True}
    check_and_define_parameters(c, sub)
    assert c["ts_subsection"] == "name_of_this_subsection"

    c = {"ts_atm_subsection": "", "guess_section_parameters": True}
    check_and_define_parameters(c, sub)
    assert c["ts_subsection"] == "name_of_this_subsection"

    c = {"ts_land_subsection": "", "guess_section_parameters": True}
    check_and_define_parameters(c, sub)
    assert c["ts_subsection"] == "name_of_this_subsection"

    # Don't guess the subsection
    c = {"ts_subsection": "subsection", "guess_section_parameters": False}
    check_and_define_parameters(c, sub)
    assert c["ts_subsection"] == "subsection"

    c = {"ts_subsection": "", "guess_section_parameters": False}
    with pytest.raises(ParameterNotProvidedError):
        check_and_define_parameters(c, sub)

    c = {
        "component": "atm",
        "ts_atm_subsection": "atm_subsection",
        "guess_section_parameters": False,
    }
    with pytest.raises(ParameterNotProvidedError):
        check_and_define_parameters(c, sub)
    c = {
        "component": "lnd",
        "ts_land_subsection": "land_subsection",
        "guess_section_parameters": False,
    }
    with pytest.raises(ParameterNotProvidedError):
        check_and_define_parameters(c, sub)

    c = {
        "component": "atm",
        "ts_land_subsection": "land_subsection",
        "guess_section_parameters": False,
    }
    with pytest.raises(ParameterNotProvidedError):
        check_and_define_parameters(c, sub)
    c = {
        "component": "lnd",
        "ts_atm_subsection": "atm_subsection",
        "guess_section_parameters": False,
    }
    with pytest.raises(ParameterNotProvidedError):
        check_and_define_parameters(c, sub)

    c = {"ts_atm_subsection": "atm_subsection", "guess_section_parameters": False}
    with pytest.raises(ParameterNotProvidedError):
        check_and_define_parameters(c, sub)
    c = {"ts_land_subsection": "land_subsection", "guess_section_parameters": False}
    with pytest.raises(ParameterNotProvidedError):
        check_and_define_parameters(c, sub)

    c = {"guess_section_parameters": False}
    with pytest.raises(ParameterNotProvidedError):
        check_and_define_parameters(c, sub)

    c = {"ts_atm_subsection": "", "guess_section_parameters": False}
    with pytest.raises(ParameterNotProvidedError):
        check_and_define_parameters(c, sub)

    c = {"ts_land_subsection": "", "guess_section_parameters": False}
    with pytest.raises(ParameterNotProvidedError):
        check_and_define_parameters(c, sub)
