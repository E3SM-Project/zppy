import unittest
from typing import List

from zppy.utils import (
    ParameterGuessType,
    ParameterNotProvidedError,
    add_dependencies,
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


class TestZppyUtils(unittest.TestCase):
    def test_get_active_status(self):
        # Test bool input
        task = {"active": True}
        self.assertTrue(get_active_status(task))
        task = {"active": False}
        self.assertFalse(get_active_status(task))

        # Test str input
        task = {"active": "True"}  # type: ignore
        self.assertTrue(get_active_status(task))
        task = {"active": "False"}  # type: ignore
        self.assertFalse(get_active_status(task))

        # Test bad value
        task = {"active": "bad input"}  # type: ignore
        self.assertRaises(ValueError, get_active_status, task)

        # Test bad type
        task = {"active": 5}  # type: ignore
        self.assertRaises(TypeError, get_active_status, task)

    def test_get_guess_type_parameter(self):
        actual = get_guess_type_parameter(ParameterGuessType.SECTION_GUESS)
        self.assertEqual(actual, "guess_section_parameters")

        actual = get_guess_type_parameter(ParameterGuessType.PATH_GUESS)
        self.assertEqual(actual, "guess_path_parameters")

    def test_get_url_message(self):
        c = {
            "web_portal_base_path": "a",
            "web_portal_base_url": "b",
            "www": "a/c",
            "case": "d",
        }
        actual = get_url_message(c, "task_name")
        self.assertEqual(actual, "URL: b/c/d/task_name")

        c = {
            "web_portal_base_path": "a",
            "web_portal_base_url": "b",
            "www": "c",
            "case": "d",
        }
        actual = get_url_message(c, "task_name")
        self.assertEqual(actual, "Could not determine URL from www=c")

    # def test_initialize_template

    # def test_get_tasks

    def test_set_mapping_file(self):
        # Test no-change cases
        c = {"mapping_file": ""}
        set_mapping_file(c)
        self.assertEqual(c["mapping_file"], "")

        c = {"mapping_file": "glb"}
        set_mapping_file(c)
        self.assertEqual(c["mapping_file"], "glb")

        c = {"mapping_file": "dir/file"}
        set_mapping_file(c)
        self.assertEqual(c["mapping_file"], "dir/file")

        #  Now, the function should do something
        c = {"mapping_file": "file", "diagnostics_base_path": "base"}
        set_mapping_file(c)
        self.assertEqual(c["mapping_file"], "base/maps/file")

    def test_set_grid(self):
        c = {"grid": "grid"}
        set_grid(c)
        self.assertEqual(c["grid"], "grid")

        c = {"grid": "", "mapping_file": ""}
        set_grid(c)
        self.assertEqual(c["grid"], "native")

        c = {"grid": "", "mapping_file": "glb"}
        set_grid(c)
        self.assertEqual(c["grid"], "glb")

        # TODO: test a realistic mapping file

    def test_set_component_and_prc_typ(self):
        # Test without input_files
        c = {"input_component": "cam"}
        set_component_and_prc_typ(c)
        self.assertEqual(c["component"], "atm")
        self.assertEqual(c["prc_typ"], "cam")

        c = {"input_component": "eam"}
        set_component_and_prc_typ(c)
        self.assertEqual(c["component"], "atm")
        self.assertEqual(c["prc_typ"], "eam")

        c = {"input_component": "eamxx"}
        set_component_and_prc_typ(c)
        self.assertEqual(c["component"], "atm")
        self.assertEqual(c["prc_typ"], "eamxx")

        c = {"input_component": "cpl"}
        set_component_and_prc_typ(c)
        self.assertEqual(c["component"], "cpl")
        self.assertEqual(c["prc_typ"], "sgs")

        c = {"input_component": "clm2"}
        set_component_and_prc_typ(c)
        self.assertEqual(c["component"], "lnd")
        self.assertEqual(c["prc_typ"], "clm")

        c = {"input_component": "elm"}
        set_component_and_prc_typ(c)
        self.assertEqual(c["component"], "lnd")
        self.assertEqual(c["prc_typ"], "elm")

        c = {"input_component": "mosart"}
        set_component_and_prc_typ(c)
        self.assertEqual(c["component"], "rof")
        self.assertEqual(c["prc_typ"], "sgs")

        # Test with input_files
        c = {"input_component": "", "input_files": "cam.extension"}
        set_component_and_prc_typ(c)
        self.assertEqual(c["component"], "atm")
        self.assertEqual(c["prc_typ"], "cam")

        c = {"input_component": "", "input_files": "eam.extension"}
        set_component_and_prc_typ(c)
        self.assertEqual(c["component"], "atm")
        self.assertEqual(c["prc_typ"], "eam")

        c = {"input_component": "", "input_files": "eamxx.extension"}
        set_component_and_prc_typ(c)
        self.assertEqual(c["component"], "atm")
        self.assertEqual(c["prc_typ"], "eamxx")

        c = {"input_component": "", "input_files": "cpl.extension"}
        set_component_and_prc_typ(c)
        self.assertEqual(c["component"], "cpl")
        self.assertEqual(c["prc_typ"], "sgs")

        c = {"input_component": "", "input_files": "clm2.extension"}
        set_component_and_prc_typ(c)
        self.assertEqual(c["component"], "lnd")
        self.assertEqual(c["prc_typ"], "clm")

        c = {"input_component": "", "input_files": "elm.extension"}
        set_component_and_prc_typ(c)
        self.assertEqual(c["component"], "lnd")
        self.assertEqual(c["prc_typ"], "elm")

        c = {"input_component": "", "input_files": "mosart.extension"}
        set_component_and_prc_typ(c)
        self.assertEqual(c["component"], "rof")
        self.assertEqual(c["prc_typ"], "sgs")

        # Test error case
        c = {"input_component": "", "input_files": ""}
        self.assertRaises(ValueError, set_component_and_prc_typ, c)

    def test_check_required_parameters(self):
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
        self.assertRaises(
            ParameterNotProvidedError,
            check_required_parameters,
            c,
            set(["a", "b"]),
            "p",
        )

    def test_get_years(self):
        self.assertEqual(get_years("1980:1990:05"), [(1980, 1984), (1985, 1989)])
        self.assertEqual(get_years("1980-1990"), [(1980, 1990)])

        self.assertEqual(get_years(["1980:1990:05"]), [(1980, 1984), (1985, 1989)])
        self.assertEqual(get_years(["1980-1990"]), [(1980, 1990)])

        self.assertEqual(
            get_years(["1980:1990:05", "2000:2010:05"]),
            [(1980, 1984), (1985, 1989), (2000, 2004), (2005, 2009)],
        )
        self.assertEqual(
            get_years(["1980-1990", "2000-2005"]), [(1980, 1990), (2000, 2005)]
        )

        self.assertRaises(ValueError, get_years, "1980")
        self.assertRaises(ValueError, get_years, "1980:1990")
        self.assertRaises(ValueError, get_years, "1980:1990:05:03")
        self.assertRaises(ValueError, get_years, "1980-1990-05")

        self.assertRaises(
            ValueError, get_years, ["1983-1993", "1980"]
        )  # one year set works
        self.assertRaises(ValueError, get_years, ["1980:1990"])
        self.assertRaises(ValueError, get_years, ["1980:1990:05:03"])
        self.assertRaises(ValueError, get_years, ["1980-1990-05"])

        # This one is in fact a value error, but not one we raised directly
        self.assertRaises(ValueError, get_years, "1980-1990:05:03")

    def test_define_or_guess(self):
        # First choice is defined
        c = {
            "first_choice": "a",
            "second_choice": "b",
            "guess_path_parameters": True,
            "guess_section_parameters": True,
        }
        actual = define_or_guess(
            c, "first_choice", "second_choice", ParameterGuessType.PATH_GUESS
        )
        self.assertEqual(actual, "a")
        actual = define_or_guess(
            c, "first_choice", "second_choice", ParameterGuessType.SECTION_GUESS
        )
        self.assertEqual(actual, "a")

        c = {
            "first_choice": "a",
            "second_choice": "b",
            "guess_path_parameters": True,
            "guess_section_parameters": False,
        }
        actual = define_or_guess(
            c, "first_choice", "second_choice", ParameterGuessType.PATH_GUESS
        )
        self.assertEqual(actual, "a")
        actual = define_or_guess(
            c, "first_choice", "second_choice", ParameterGuessType.SECTION_GUESS
        )
        self.assertEqual(actual, "a")

        c = {
            "first_choice": "a",
            "second_choice": "b",
            "guess_path_parameters": False,
            "guess_section_parameters": True,
        }
        actual = define_or_guess(
            c, "first_choice", "second_choice", ParameterGuessType.PATH_GUESS
        )
        self.assertEqual(actual, "a")
        actual = define_or_guess(
            c, "first_choice", "second_choice", ParameterGuessType.SECTION_GUESS
        )
        self.assertEqual(actual, "a")

        # First choice is undefined
        c = {
            "first_choice": "",
            "second_choice": "b",
            "guess_path_parameters": True,
            "guess_section_parameters": True,
        }
        actual = define_or_guess(
            c, "first_choice", "second_choice", ParameterGuessType.PATH_GUESS
        )
        self.assertEqual(actual, "b")
        actual = define_or_guess(
            c, "first_choice", "second_choice", ParameterGuessType.SECTION_GUESS
        )
        self.assertEqual(actual, "b")

        c = {
            "first_choice": "",
            "second_choice": "b",
            "guess_path_parameters": True,
            "guess_section_parameters": False,
        }
        actual = define_or_guess(
            c, "first_choice", "second_choice", ParameterGuessType.PATH_GUESS
        )
        self.assertEqual(actual, "b")
        self.assertRaises(
            ParameterNotProvidedError,
            define_or_guess,
            c,
            "first_choice",
            "second_choice",
            ParameterGuessType.SECTION_GUESS,
        )

        c = {
            "first_choice": "",
            "second_choice": "b",
            "guess_path_parameters": False,
            "guess_section_parameters": True,
        }
        self.assertRaises(
            ParameterNotProvidedError,
            define_or_guess,
            c,
            "first_choice",
            "second_choice",
            ParameterGuessType.PATH_GUESS,
        )
        actual = define_or_guess(
            c, "first_choice", "second_choice", ParameterGuessType.SECTION_GUESS
        )
        self.assertEqual(actual, "b")

    def test_define_or_guess2(self):
        # The required parameter has a value
        c = {
            "required_parameter": "a",
            "guess_path_parameters": True,
            "guess_section_parameters": True,
        }
        define_or_guess2(
            c, "required_parameter", "backup_option", ParameterGuessType.PATH_GUESS
        )
        self.assertEqual(c["required_parameter"], "a")
        c = {
            "required_parameter": "a",
            "guess_path_parameters": True,
            "guess_section_parameters": True,
        }
        define_or_guess2(
            c, "required_parameter", "backup_option", ParameterGuessType.SECTION_GUESS
        )
        self.assertEqual(c["required_parameter"], "a")

        c = {
            "required_parameter": "a",
            "guess_path_parameters": True,
            "guess_section_parameters": False,
        }
        define_or_guess2(
            c, "required_parameter", "backup_option", ParameterGuessType.PATH_GUESS
        )
        self.assertEqual(c["required_parameter"], "a")
        c = {
            "required_parameter": "a",
            "guess_path_parameters": True,
            "guess_section_parameters": False,
        }
        define_or_guess2(
            c, "required_parameter", "backup_option", ParameterGuessType.SECTION_GUESS
        )
        self.assertEqual(c["required_parameter"], "a")

        c = {
            "required_parameter": "a",
            "guess_path_parameters": False,
            "guess_section_parameters": True,
        }
        define_or_guess2(
            c, "required_parameter", "backup_option", ParameterGuessType.PATH_GUESS
        )
        self.assertEqual(c["required_parameter"], "a")
        c = {
            "required_parameter": "a",
            "guess_path_parameters": False,
            "guess_section_parameters": True,
        }
        define_or_guess2(
            c, "required_parameter", "backup_option", ParameterGuessType.SECTION_GUESS
        )
        self.assertEqual(c["required_parameter"], "a")

        # The required parameter is undefined
        c = {
            "required_parameter": "",
            "guess_path_parameters": True,
            "guess_section_parameters": True,
        }
        define_or_guess2(
            c, "required_parameter", "backup_option", ParameterGuessType.PATH_GUESS
        )
        self.assertEqual(c["required_parameter"], "backup_option")
        c = {
            "required_parameter": "",
            "guess_path_parameters": True,
            "guess_section_parameters": True,
        }
        define_or_guess2(
            c, "required_parameter", "backup_option", ParameterGuessType.SECTION_GUESS
        )
        self.assertEqual(c["required_parameter"], "backup_option")

        c = {
            "required_parameter": "",
            "guess_path_parameters": True,
            "guess_section_parameters": False,
        }
        define_or_guess2(
            c, "required_parameter", "backup_option", ParameterGuessType.PATH_GUESS
        )
        self.assertEqual(c["required_parameter"], "backup_option")
        c = {
            "required_parameter": "",
            "guess_path_parameters": True,
            "guess_section_parameters": False,
        }
        self.assertRaises(
            ParameterNotProvidedError,
            define_or_guess2,
            c,
            "required_parameter",
            "backup_option",
            ParameterGuessType.SECTION_GUESS,
        )

        c = {
            "required_parameter": "",
            "guess_path_parameters": False,
            "guess_section_parameters": True,
        }
        self.assertRaises(
            ParameterNotProvidedError,
            define_or_guess2,
            c,
            "required_parameter",
            "backup_option",
            ParameterGuessType.PATH_GUESS,
        )
        c = {
            "required_parameter": "",
            "guess_path_parameters": False,
            "guess_section_parameters": True,
        }
        define_or_guess2(
            c, "required_parameter", "backup_option", ParameterGuessType.SECTION_GUESS
        )
        self.assertEqual(c["required_parameter"], "backup_option")

    def test_get_file_names(self):
        bash, settings, status = get_file_names("script_dir", "prefix")
        self.assertEqual(bash, "script_dir/prefix.bash")
        self.assertEqual(settings, "script_dir/prefix.settings")
        self.assertEqual(status, "script_dir/prefix.status")

    # def test_check_status

    # def test_make_executable

    def test_add_dependencies(self):
        dependencies: List[str] = []
        add_dependencies(dependencies, "script_dir", "prefix", "sub", 1980, 1990, 10)
        self.assertEqual(dependencies, ["script_dir/prefix_sub_1980-1989-0010.status"])

        dependencies = []
        add_dependencies(dependencies, "script_dir", "prefix", "sub", 1980, 1990, 2)
        expected = [
            "script_dir/prefix_sub_1980-1981-0002.status",
            "script_dir/prefix_sub_1982-1983-0002.status",
            "script_dir/prefix_sub_1984-1985-0002.status",
            "script_dir/prefix_sub_1986-1987-0002.status",
            "script_dir/prefix_sub_1988-1989-0002.status",
        ]
        self.assertEqual(dependencies, expected)

    # def test_write_settings_file

    # def test_submit_script

    # def test_print_url


if __name__ == "__main__":
    unittest.main()
