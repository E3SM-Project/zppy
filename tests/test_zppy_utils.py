from typing import List

import pytest

from zppy.utils import (
    DeprecatedParameterError,
    ParameterGuessType,
    ParameterNotProvidedError,
    add_dependencies,
    check_for_deprecated_parameters,
    check_parameter_defined,
    check_required_parameters,
    define_or_guess,
    define_or_guess2,
    get_active_status,
    get_file_names,
    get_guess_type_parameter,
    get_url_message,
    get_years,
    set_component_and_prc_typ,
    set_grid,
    set_mapping_file,
)


def test_get_active_status():
    # Test bool input
    task = {"active": True}
    assert get_active_status(task) is True
    task = {"active": False}
    assert get_active_status(task) is False

    # Test str input
    task = {"active": "True"}  # type: ignore
    assert get_active_status(task) is True
    task = {"active": "False"}  # type: ignore
    assert get_active_status(task) is False

    # Test bad value
    task = {"active": "bad input"}  # type: ignore
    with pytest.raises(ValueError):
        get_active_status(task)

    # Test bad type
    task = {"active": 5}  # type: ignore
    with pytest.raises(TypeError):
        get_active_status(task)


def test_get_guess_type_parameter():
    assert (
        get_guess_type_parameter(ParameterGuessType.SECTION_GUESS)
        == "guess_section_parameters"
    )
    assert (
        get_guess_type_parameter(ParameterGuessType.PATH_GUESS)
        == "guess_path_parameters"
    )


def test_get_url_message():
    c = {
        "web_portal_base_path": "a",
        "web_portal_base_url": "b",
        "www": "a/c",
        "case": "d",
    }
    assert get_url_message(c, "task_name") == "URL: b/c/d/task_name"

    c = {
        "web_portal_base_path": "a",
        "web_portal_base_url": "b",
        "www": "c",
        "case": "d",
    }
    assert get_url_message(c, "task_name") == "Could not determine URL from www=c"


def test_set_mapping_file():
    # Test no-change cases
    c = {"mapping_file": ""}
    set_mapping_file(c)
    assert c["mapping_file"] == ""

    c = {"mapping_file": "glb"}
    set_mapping_file(c)
    assert c["mapping_file"] == "glb"

    c = {"mapping_file": "dir/file"}
    set_mapping_file(c)
    assert c["mapping_file"] == "dir/file"

    # Now, the function should do something
    c = {"mapping_file": "file", "diagnostics_base_path": "base"}
    set_mapping_file(c)
    assert c["mapping_file"] == "base/maps/file"


def test_set_grid():
    c = {"grid": "grid"}
    set_grid(c)
    assert c["grid"] == "grid"

    c = {"grid": "", "mapping_file": ""}
    set_grid(c)
    assert c["grid"] == "native"

    c = {"grid": "", "mapping_file": "glb"}
    set_grid(c)
    assert c["grid"] == "glb"

    # TODO: test a realistic mapping file


def test_set_component_and_prc_typ():
    # Test without input_files
    c = {"input_component": "cam"}
    set_component_and_prc_typ(c)
    assert c["component"] == "atm"
    assert c["prc_typ"] == "cam"

    c = {"input_component": "eam"}
    set_component_and_prc_typ(c)
    assert c["component"] == "atm"
    assert c["prc_typ"] == "eam"

    c = {"input_component": "eamxx"}
    set_component_and_prc_typ(c)
    assert c["component"] == "atm"
    assert c["prc_typ"] == "eamxx"

    c = {"input_component": "cpl"}
    set_component_and_prc_typ(c)
    assert c["component"] == "cpl"
    assert c["prc_typ"] == "sgs"

    c = {"input_component": "clm2"}
    set_component_and_prc_typ(c)
    assert c["component"] == "lnd"
    assert c["prc_typ"] == "clm"

    c = {"input_component": "elm"}
    set_component_and_prc_typ(c)
    assert c["component"] == "lnd"
    assert c["prc_typ"] == "elm"

    c = {"input_component": "mosart"}
    set_component_and_prc_typ(c)
    assert c["component"] == "rof"
    assert c["prc_typ"] == "sgs"

    # Test with input_files
    c = {"input_component": "", "input_files": "cam.extension"}
    set_component_and_prc_typ(c)
    assert c["component"] == "atm"
    assert c["prc_typ"] == "cam"

    c = {"input_component": "", "input_files": "eam.extension"}
    set_component_and_prc_typ(c)
    assert c["component"] == "atm"
    assert c["prc_typ"] == "eam"

    c = {"input_component": "", "input_files": "eamxx.extension"}
    set_component_and_prc_typ(c)
    assert c["component"] == "atm"
    assert c["prc_typ"] == "eamxx"

    c = {"input_component": "", "input_files": "cpl.extension"}
    set_component_and_prc_typ(c)
    assert c["component"] == "cpl"
    assert c["prc_typ"] == "sgs"

    c = {"input_component": "", "input_files": "clm2.extension"}
    set_component_and_prc_typ(c)
    assert c["component"] == "lnd"
    assert c["prc_typ"] == "clm"

    c = {"input_component": "", "input_files": "elm.extension"}
    set_component_and_prc_typ(c)
    assert c["component"] == "lnd"
    assert c["prc_typ"] == "elm"

    c = {"input_component": "", "input_files": "mosart.extension"}
    set_component_and_prc_typ(c)
    assert c["component"] == "rof"
    assert c["prc_typ"] == "sgs"

    # Test error case
    c = {"input_component": "", "input_files": ""}
    with pytest.raises(ValueError):
        set_component_and_prc_typ(c)


def test_check_required_parameters():
    # Parameter is required
    # a, b need parameter p, and we want sets a, b, c
    c = {"sets": ["a", "b", "c"], "p": "exists"}
    check_required_parameters(c, set(["a", "b"]), "p")

    # Parameter isn't required based on the sets we want
    # z needs parameter p, but we only want sets a, b, c
    c = {"sets": ["a", "b", "c"], "p": ""}
    check_required_parameters(c, set(["z"]), "p")

    # Parameter is required
    # a, b need parameter p, and we want sets a, b, c
    c = {"sets": ["a", "b", "c"], "p": ""}
    with pytest.raises(ParameterNotProvidedError):
        check_required_parameters(c, set(["a", "b"]), "p")


def test_get_years():
    assert get_years("1980:1990:05") == [(1980, 1984), (1985, 1989)]
    assert get_years("1980-1990") == [(1980, 1990)]

    assert get_years(["1980:1990:05"]) == [(1980, 1984), (1985, 1989)]
    assert get_years(["1980-1990"]) == [(1980, 1990)]

    assert get_years(["1980:1990:05", "2000:2010:05"]) == [
        (1980, 1984),
        (1985, 1989),
        (2000, 2004),
        (2005, 2009),
    ]
    assert get_years(["1980-1990", "2000-2005"]) == [(1980, 1990), (2000, 2005)]

    with pytest.raises(ValueError):
        get_years("1980")
    with pytest.raises(ValueError):
        get_years("1980:1990")
    with pytest.raises(ValueError):
        get_years("1980:1990:05:03")
    with pytest.raises(ValueError):
        get_years("1980-1990-05")

    with pytest.raises(ValueError):
        get_years(["1983-1993", "1980"])  # one year set works
    with pytest.raises(ValueError):
        get_years(["1980:1990"])
    with pytest.raises(ValueError):
        get_years(["1980:1990:05:03"])
    with pytest.raises(ValueError):
        get_years(["1980-1990-05"])

    # This one is in fact a value error, but not one we raised directly
    with pytest.raises(ValueError):
        get_years("1980-1990:05:03")


def test_define_or_guess():
    # First choice is defined
    c = {
        "first_choice": "a",
        "second_choice": "b",
        "guess_path_parameters": True,
        "guess_section_parameters": True,
    }
    assert (
        define_or_guess(
            c, "first_choice", "second_choice", ParameterGuessType.PATH_GUESS
        )
        == "a"
    )
    assert (
        define_or_guess(
            c, "first_choice", "second_choice", ParameterGuessType.SECTION_GUESS
        )
        == "a"
    )

    c = {
        "first_choice": "a",
        "second_choice": "b",
        "guess_path_parameters": True,
        "guess_section_parameters": False,
    }
    assert (
        define_or_guess(
            c, "first_choice", "second_choice", ParameterGuessType.PATH_GUESS
        )
        == "a"
    )
    assert (
        define_or_guess(
            c, "first_choice", "second_choice", ParameterGuessType.SECTION_GUESS
        )
        == "a"
    )

    c = {
        "first_choice": "a",
        "second_choice": "b",
        "guess_path_parameters": False,
        "guess_section_parameters": True,
    }
    assert (
        define_or_guess(
            c, "first_choice", "second_choice", ParameterGuessType.PATH_GUESS
        )
        == "a"
    )
    assert (
        define_or_guess(
            c, "first_choice", "second_choice", ParameterGuessType.SECTION_GUESS
        )
        == "a"
    )

    # First choice is undefined
    c = {
        "first_choice": "",
        "second_choice": "b",
        "guess_path_parameters": True,
        "guess_section_parameters": True,
    }
    assert (
        define_or_guess(
            c, "first_choice", "second_choice", ParameterGuessType.PATH_GUESS
        )
        == "b"
    )
    assert (
        define_or_guess(
            c, "first_choice", "second_choice", ParameterGuessType.SECTION_GUESS
        )
        == "b"
    )

    c = {
        "first_choice": "",
        "second_choice": "b",
        "guess_path_parameters": True,
        "guess_section_parameters": False,
    }
    assert (
        define_or_guess(
            c, "first_choice", "second_choice", ParameterGuessType.PATH_GUESS
        )
        == "b"
    )
    with pytest.raises(ParameterNotProvidedError):
        define_or_guess(
            c, "first_choice", "second_choice", ParameterGuessType.SECTION_GUESS
        )

    c = {
        "first_choice": "",
        "second_choice": "b",
        "guess_path_parameters": False,
        "guess_section_parameters": True,
    }
    with pytest.raises(ParameterNotProvidedError):
        define_or_guess(
            c, "first_choice", "second_choice", ParameterGuessType.PATH_GUESS
        )
    assert (
        define_or_guess(
            c, "first_choice", "second_choice", ParameterGuessType.SECTION_GUESS
        )
        == "b"
    )


def test_define_or_guess2():
    # The required parameter has a value
    c = {
        "required_parameter": "a",
        "guess_path_parameters": True,
        "guess_section_parameters": True,
    }
    define_or_guess2(
        c, "required_parameter", "backup_option", ParameterGuessType.PATH_GUESS
    )
    assert c["required_parameter"] == "a"
    c = {
        "required_parameter": "a",
        "guess_path_parameters": True,
        "guess_section_parameters": True,
    }
    define_or_guess2(
        c, "required_parameter", "backup_option", ParameterGuessType.SECTION_GUESS
    )
    assert c["required_parameter"] == "a"

    c = {
        "required_parameter": "a",
        "guess_path_parameters": True,
        "guess_section_parameters": False,
    }
    define_or_guess2(
        c, "required_parameter", "backup_option", ParameterGuessType.PATH_GUESS
    )
    assert c["required_parameter"] == "a"
    c = {
        "required_parameter": "a",
        "guess_path_parameters": True,
        "guess_section_parameters": False,
    }
    define_or_guess2(
        c, "required_parameter", "backup_option", ParameterGuessType.SECTION_GUESS
    )
    assert c["required_parameter"] == "a"

    c = {
        "required_parameter": "a",
        "guess_path_parameters": False,
        "guess_section_parameters": True,
    }
    define_or_guess2(
        c, "required_parameter", "backup_option", ParameterGuessType.PATH_GUESS
    )
    assert c["required_parameter"] == "a"
    c = {
        "required_parameter": "a",
        "guess_path_parameters": False,
        "guess_section_parameters": True,
    }
    define_or_guess2(
        c, "required_parameter", "backup_option", ParameterGuessType.SECTION_GUESS
    )
    assert c["required_parameter"] == "a"

    # The required parameter is undefined
    c = {
        "required_parameter": "",
        "guess_path_parameters": True,
        "guess_section_parameters": True,
    }
    define_or_guess2(
        c, "required_parameter", "backup_option", ParameterGuessType.PATH_GUESS
    )
    assert c["required_parameter"] == "backup_option"
    c = {
        "required_parameter": "",
        "guess_path_parameters": True,
        "guess_section_parameters": True,
    }
    define_or_guess2(
        c, "required_parameter", "backup_option", ParameterGuessType.SECTION_GUESS
    )
    assert c["required_parameter"] == "backup_option"

    c = {
        "required_parameter": "",
        "guess_path_parameters": True,
        "guess_section_parameters": False,
    }
    define_or_guess2(
        c, "required_parameter", "backup_option", ParameterGuessType.PATH_GUESS
    )
    assert c["required_parameter"] == "backup_option"
    c = {
        "required_parameter": "",
        "guess_path_parameters": True,
        "guess_section_parameters": False,
    }
    with pytest.raises(ParameterNotProvidedError):
        define_or_guess2(
            c, "required_parameter", "backup_option", ParameterGuessType.SECTION_GUESS
        )

    c = {
        "required_parameter": "",
        "guess_path_parameters": False,
        "guess_section_parameters": True,
    }
    with pytest.raises(ParameterNotProvidedError):
        define_or_guess2(
            c, "required_parameter", "backup_option", ParameterGuessType.PATH_GUESS
        )
    c = {
        "required_parameter": "",
        "guess_path_parameters": False,
        "guess_section_parameters": True,
    }
    define_or_guess2(
        c, "required_parameter", "backup_option", ParameterGuessType.SECTION_GUESS
    )
    assert c["required_parameter"] == "backup_option"


def test_check_parameter_defined():
    c = {"a": 1, "b": 2, "c": ""}
    check_parameter_defined(c, "a")
    with pytest.raises(ParameterNotProvidedError):
        check_parameter_defined(c, "c")
    with pytest.raises(ParameterNotProvidedError):
        check_parameter_defined(c, "d")


def test_check_for_deprecated_parameters():
    deprecated_parameters = [
        # Removed in https://github.com/E3SM-Project/zppy/pull/650
        "e3sm_to_cmip_environment_commands",
        "ts_fmt",
        # Removed in https://github.com/E3SM-Project/zppy/pull/654
        "scratch",
        "atmosphere_only",
        "plot_names",
    ]
    c = {"scratch": "xyz", "plot_names": "a,b,c"}
    with pytest.raises(DeprecatedParameterError):
        check_for_deprecated_parameters(c, deprecated_parameters)


def test_get_file_names():
    bash, settings, status = get_file_names("script_dir", "prefix")
    assert bash == "script_dir/prefix.bash"
    assert settings == "script_dir/prefix.settings"
    assert status == "script_dir/prefix.status"


def test_add_dependencies():
    dependencies: List[str] = []
    add_dependencies(dependencies, "script_dir", "prefix", "sub", 1980, 1990, 10)
    assert dependencies == ["script_dir/prefix_sub_1980-1989-0010.status"]

    dependencies = []
    add_dependencies(dependencies, "script_dir", "prefix", "sub", 1980, 1990, 2)
    expected = [
        "script_dir/prefix_sub_1980-1981-0002.status",
        "script_dir/prefix_sub_1982-1983-0002.status",
        "script_dir/prefix_sub_1984-1985-0002.status",
        "script_dir/prefix_sub_1986-1987-0002.status",
        "script_dir/prefix_sub_1988-1989-0002.status",
    ]
    assert dependencies == expected
