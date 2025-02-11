import pytest

from zppy.e3sm_to_cmip import check_and_define_parameters, check_parameters_for_bash
from zppy.utils import ParameterNotProvidedError


def test_check_parameters_for_bash():

    # 1. ts_grid is set explictily
    c = {"ts_grid": "grid"}
    check_parameters_for_bash(c)

    # 2. ts_grid can't be set because an empty string is provided
    c = {"ts_grid": ""}
    with pytest.raises(ParameterNotProvidedError):
        check_parameters_for_bash(c)

    # 3. ts_grid is set via ts_atm_grid
    c = {"component": "atm", "ts_atm_grid": "atm_grid"}
    check_parameters_for_bash(c)
    # 4. ts_grid is set via ts_land_grid
    c = {"component": "lnd", "ts_land_grid": "land_grid"}
    check_parameters_for_bash(c)

    # 5. ts_grid can't be set via ts_land_grid since component is atm
    c = {"component": "atm", "ts_land_grid": "land_grid"}
    with pytest.raises(ParameterNotProvidedError):
        check_parameters_for_bash(c)
    # 6. ts_grid can't be set via ts_atm_grid since component is lnd
    c = {"component": "lnd", "ts_atm_grid": "atm_grid"}
    with pytest.raises(ParameterNotProvidedError):
        check_parameters_for_bash(c)

    # 7. ts_grid can't be set via ts_atm_grid since component isn't specified
    c = {"ts_atm_grid": "atm_grid"}
    with pytest.raises(ParameterNotProvidedError):
        check_parameters_for_bash(c)
    # 8. ts_grid can't be set via ts_land_grid since component isn't specified
    c = {"ts_land_grid": "land_grid"}
    with pytest.raises(ParameterNotProvidedError):
        check_parameters_for_bash(c)

    # 9. ts_grid can't be set because ts_atm_grid is set to the empty string
    c = {"component": "atm", "ts_atm_grid": ""}
    with pytest.raises(ParameterNotProvidedError):
        check_parameters_for_bash(c)
    # 10. ts_grid can't be set because ts_land_grid is set to the empty string
    c = {"component": "lnd", "ts_land_grid": ""}
    with pytest.raises(ParameterNotProvidedError):
        check_parameters_for_bash(c)


def test_check_and_define_parameters():
    sub = "name_of_this_subsection"

    # Infer the subsection ####################################################
    # 1. ts_subsection is set explictily
    c = {"ts_subsection": "subsection", "infer_section_parameters": True}
    check_and_define_parameters(c, sub)
    assert c["ts_subsection"] == "subsection"

    # 2. ts_subsection is set via sub because it is initially set to the empty string
    c = {"ts_subsection": "", "infer_section_parameters": True}
    check_and_define_parameters(c, sub)
    assert c["ts_subsection"] == "name_of_this_subsection"

    # 3. ts_subsection is set via ts_atm_subsection
    c = {
        "component": "atm",
        "ts_atm_subsection": "atm_subsection",
        "infer_section_parameters": True,
    }
    check_and_define_parameters(c, sub)
    assert c["ts_subsection"] == "atm_subsection"
    # 4. ts_subsection is set via ts_land_subsection
    c = {
        "component": "lnd",
        "ts_land_subsection": "land_subsection",
        "infer_section_parameters": True,
    }
    check_and_define_parameters(c, sub)
    assert c["ts_subsection"] == "land_subsection"

    # 5. ts_subsection can't be set via ts_land_subsection since component is atm
    c = {
        "component": "atm",
        "ts_land_subsection": "land_subsection",
        "infer_section_parameters": True,
    }
    check_and_define_parameters(c, sub)
    assert c["ts_subsection"] == "name_of_this_subsection"
    # 6. ts_subsection can't be set via ts_atm_subsection since component is lnd
    c = {
        "component": "lnd",
        "ts_atm_subsection": "atm_subsection",
        "infer_section_parameters": True,
    }
    check_and_define_parameters(c, sub)
    assert c["ts_subsection"] == "name_of_this_subsection"

    # 7. ts_subsection can't be set via ts_atm_subsection since component isn't specified
    c = {"ts_atm_subsection": "atm_subsection", "infer_section_parameters": True}
    check_and_define_parameters(c, sub)
    assert c["ts_subsection"] == "name_of_this_subsection"
    # 8. ts_subsection can't be set via ts_atm_subsection since component isn't specified
    c = {"ts_land_subsection": "land_subsection", "infer_section_parameters": True}
    check_and_define_parameters(c, sub)
    assert c["ts_subsection"] == "name_of_this_subsection"

    # 9. ts_subsection is set via sub because it is initially not provided
    c = {"infer_section_parameters": True}
    check_and_define_parameters(c, sub)
    assert c["ts_subsection"] == "name_of_this_subsection"

    # 10. ts_subsection is set via sub because it is initially not provided and component isn't specified (required to use ts_atm_subsection)
    c = {"ts_atm_subsection": "", "infer_section_parameters": True}
    check_and_define_parameters(c, sub)
    assert c["ts_subsection"] == "name_of_this_subsection"

    # 11. ts_subsection is set via sub because it is initially not provided and component isn't specified (required to use ts_land_subsection)
    c = {"ts_land_subsection": "", "infer_section_parameters": True}
    check_and_define_parameters(c, sub)
    assert c["ts_subsection"] == "name_of_this_subsection"

    # Don't infer the subsection ##############################################
    # Repeat above cases, but with infer_section_parameters set to False

    # 1
    c = {"ts_subsection": "subsection", "infer_section_parameters": False}
    check_and_define_parameters(c, sub)
    assert c["ts_subsection"] == "subsection"

    # 2
    c = {"ts_subsection": "", "infer_section_parameters": False}
    with pytest.raises(ParameterNotProvidedError):
        check_and_define_parameters(c, sub)

    # 3
    c = {
        "component": "atm",
        "ts_atm_subsection": "atm_subsection",
        "infer_section_parameters": False,
    }
    with pytest.raises(ParameterNotProvidedError):
        check_and_define_parameters(c, sub)
    # 4
    c = {
        "component": "lnd",
        "ts_land_subsection": "land_subsection",
        "infer_section_parameters": False,
    }
    with pytest.raises(ParameterNotProvidedError):
        check_and_define_parameters(c, sub)

    # 5
    c = {
        "component": "atm",
        "ts_land_subsection": "land_subsection",
        "infer_section_parameters": False,
    }
    with pytest.raises(ParameterNotProvidedError):
        check_and_define_parameters(c, sub)
    # 6
    c = {
        "component": "lnd",
        "ts_atm_subsection": "atm_subsection",
        "infer_section_parameters": False,
    }
    with pytest.raises(ParameterNotProvidedError):
        check_and_define_parameters(c, sub)

    # 7
    c = {"ts_atm_subsection": "atm_subsection", "infer_section_parameters": False}
    with pytest.raises(ParameterNotProvidedError):
        check_and_define_parameters(c, sub)
    # 8
    c = {"ts_land_subsection": "land_subsection", "infer_section_parameters": False}
    with pytest.raises(ParameterNotProvidedError):
        check_and_define_parameters(c, sub)

    # 9
    c = {"infer_section_parameters": False}
    with pytest.raises(ParameterNotProvidedError):
        check_and_define_parameters(c, sub)

    # 10
    c = {"ts_atm_subsection": "", "infer_section_parameters": False}
    with pytest.raises(ParameterNotProvidedError):
        check_and_define_parameters(c, sub)

    # 11
    c = {"ts_land_subsection": "", "infer_section_parameters": False}
    with pytest.raises(ParameterNotProvidedError):
        check_and_define_parameters(c, sub)
