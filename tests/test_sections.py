import os
import pprint
import unittest

from configobj import ConfigObj, Section
from validate import Validator

from zppy.utils import getTasks


def compare(tester, actual, expected):
    if actual != expected:
        actual_keys = set(actual.keys())
        expected_keys = set(expected.keys())
        if actual_keys != expected_keys:
            only_in_actual = actual_keys - expected_keys
            print("only_in_actual={}".format(only_in_actual))
            tester.assertEqual(only_in_actual, set())
            only_in_expected = expected_keys - actual_keys
            print("only_in_expected={}".format(only_in_expected))
            tester.assertEqual(only_in_expected, set())
        incorrect_values = []
        for key in actual_keys:
            if type(actual[key]) == Section:
                print("Calling `compare` again on {}".format(key))
                compare(tester, actual[key], expected[key])
            elif actual[key] != expected[key]:
                incorrect_values.append((key, actual[key], expected[key]))
        print("incorrect_values=")
        for v in incorrect_values:
            print(v)
        tester.assertEqual(incorrect_values, [])


def get_config(test_case, config_file):
    # Subdirectory where templates are located
    templateDir = os.path.join("zppy", "templates")

    # Read configuration file and validate it
    config = ConfigObj(config_file, configspec=os.path.join(templateDir, "default.ini"))
    validator = Validator()

    test_case.assertTrue(config.validate(validator))

    # Add templateDir to config
    config["default"]["templateDir"] = templateDir

    # For debugging
    DISPLAY_CONFIG = False
    if DISPLAY_CONFIG:
        with open("{}.txt".format(config_file), "w") as output:
            p = pprint.PrettyPrinter(indent=2, stream=output)
            p.pprint(config)
        test_case.maxDiff = None

    return config


class TestAllSets(unittest.TestCase):
    def test_sections(self):
        config = get_config(self, "tests/test_sections.cfg")

        # default
        actual_default = config["default"]
        expected_default = {
            "active": False,
            "account": "",
            "bundle": "",
            "campaign": "none",
            "case": "CASE",
            "constraint": "",
            "debug": False,
            "dry_run": False,
            "environment_commands": "",
            "frequency": "monthly",
            "grid": "",
            "input": "INPUT",
            "input_files": "eam.h0",
            "input_subdir": "INPUT_SUBDIR",
            "mapping_file": "",
            "output": "OUTPUT",
            "nodes": 1,
            "partition": "SHORT",
            "plugins": [],
            "qos": "regular",
            "templateDir": "zppy/templates",
            "vars": "FSNTOA,FLUT,FSNT,FLNT,FSNS,FLNS,SHFLX,QFLX,TAUX,TAUY,PRECC,PRECL,PRECSC,PRECSL,TS,TREFHT,CLDTOT,CLDHGH,CLDMED,CLDLOW,U",
            "walltime": "02:00:00",
            "www": "WWWW",
            "years": [""],
        }
        compare(self, actual_default, expected_default)

        # ts
        section_name = "ts"
        actual_section = config[section_name]
        expected_section = {
            "active": "True",
            "area_nm": "area",
            "cmip_metadata": "e3sm_to_cmip/default_metadata.json",
            "dpf": 30,
            "extra_vars": "",
            "mapping_file": "MAPPING_FILE_TS",
            "tpd": 1,
            "ts_fmt": "ts_only",
            "vars": "FSNTOA,FLUT,FSNT,FLNT,FSNS,FLNS,SHFLX,QFLX,PRECC,PRECL,PRECSC,PRECSL,TS,TREFHT",
            "years": ["0001:0020:5"],
        }
        compare(self, actual_section, expected_section)
        actual_tasks = getTasks(config, section_name)
        self.assertEqual(len(actual_tasks), 1)
        actual_task = actual_tasks[0]
        expected_task = {
            "active": "True",
            "account": "",
            "bundle": "",
            "area_nm": "area",
            "campaign": "none",
            "case": "CASE",
            "cmip_metadata": "e3sm_to_cmip/default_metadata.json",
            "constraint": "",
            "debug": False,
            "dpf": 30,
            "dry_run": False,
            "environment_commands": "",
            "extra_vars": "",
            "frequency": "monthly",
            "grid": "",
            "input": "INPUT",
            "input_files": "eam.h0",
            "input_subdir": "INPUT_SUBDIR",
            "mapping_file": "MAPPING_FILE_TS",
            "nodes": 1,
            "output": "OUTPUT",
            "partition": "SHORT",
            "plugins": [],
            "qos": "regular",
            "subsection": None,
            "templateDir": "zppy/templates",
            "tpd": 1,
            "ts_fmt": "ts_only",
            "vars": "FSNTOA,FLUT,FSNT,FLNT,FSNS,FLNS,SHFLX,QFLX,PRECC,PRECL,PRECSC,PRECSL,TS,TREFHT",
            "walltime": "02:00:00",
            "www": "WWWW",
            "years": ["0001:0020:5"],
        }
        compare(self, actual_task, expected_task)

        # climo
        section_name = "climo"
        actual_section = config[section_name]
        expected_section = {
            "active": "True",
            "exclude": False,
            "mapping_file": "MAPPING_FILE_CLIMO",
            "nodes": 4,
            "vars": "",
            "years": ["0001:0050:50"],
        }
        compare(self, actual_section, expected_section)
        actual_tasks = getTasks(config, section_name)
        compare(self, len(actual_tasks), 1)
        actual_task = actual_tasks[0]
        expected_task = {
            "active": "True",
            "account": "",
            "bundle": "",
            "campaign": "none",
            "case": "CASE",
            "constraint": "",
            "debug": False,
            "dry_run": False,
            "environment_commands": "",
            "exclude": False,
            "frequency": "monthly",
            "grid": "",
            "input": "INPUT",
            "input_files": "eam.h0",
            "input_subdir": "INPUT_SUBDIR",
            "mapping_file": "MAPPING_FILE_CLIMO",
            "nodes": 4,
            "output": "OUTPUT",
            "partition": "SHORT",
            "plugins": [],
            "qos": "regular",
            "subsection": None,
            "templateDir": "zppy/templates",
            "vars": "",
            "walltime": "02:00:00",
            "www": "WWWW",
            "years": ["0001:0050:50"],
        }
        compare(self, actual_task, expected_task)

        # tc_analysis: test an inactive task
        section_name = "tc_analysis"
        actual_section = config[section_name]
        self.assertTrue(actual_section["active"] == "False")
        actual_tasks = getTasks(config, section_name)
        self.assertEqual(len(actual_tasks), 0)

        # e3sm_diags: test an excluded task
        section_name = "e3sm_diags"
        actual_section = config[section_name]
        self.assertTrue("active" not in actual_section.keys())
        actual_tasks = getTasks(config, section_name)
        self.assertEqual(len(actual_tasks), 0)

    def test_subsections(self):
        config = get_config(self, "tests/test_subsections.cfg")

        # default
        actual_default = config["default"]
        expected_default = {
            "active": False,
            "account": "",
            "bundle": "",
            "campaign": "none",
            "case": "CASE",
            "constraint": "",
            "debug": False,
            "dry_run": False,
            "environment_commands": "",
            "frequency": "monthly",
            "grid": "",
            "input": "INPUT",
            "input_files": "eam.h0",
            "input_subdir": "INPUT_SUBDIR",
            "mapping_file": "",
            "nodes": 1,
            "output": "OUTPUT",
            "partition": "SHORT",
            "plugins": [],
            "qos": "regular",
            "templateDir": "zppy/templates",
            "vars": "FSNTOA,FLUT,FSNT,FLNT,FSNS,FLNS,SHFLX,QFLX,TAUX,TAUY,PRECC,PRECL,PRECSC,PRECSL,TS,TREFHT,CLDTOT,CLDHGH,CLDMED,CLDLOW,U",
            "walltime": "02:00:00",
            "www": "WWWW",
            "years": [""],
        }
        compare(self, actual_default, expected_default)

        # ts
        section_name = "ts"
        actual_section = config[section_name]
        expected_section = {
            "active": "True",
            "area_nm": "area",
            "cmip_metadata": "e3sm_to_cmip/default_metadata.json",
            "dpf": 30,
            "extra_vars": "",
            "tpd": 1,
            "ts_fmt": "ts_only",
            "ts_grid1": {
                "area_nm": None,
                "cmip_metadata": None,
                "dpf": None,
                "extra_vars": None,
                "mapping_file": "MAPPING_FILE_TS_GRID1",
                "tpd": None,
                "ts_fmt": None,
                "years": ["0001:0020:5"],
            },
            "ts_grid2": {
                "area_nm": None,
                "cmip_metadata": None,
                "dpf": None,
                "extra_vars": None,
                "mapping_file": "MAPPING_FILE_TS_GRID2",
                "tpd": None,
                "ts_fmt": None,
                "years": ["0001:0020:10"],
            },
            "vars": "FSNTOA,FLUT,FSNT,FLNT,FSNS,FLNS,SHFLX,QFLX,PRECC,PRECL,PRECSC,PRECSL,TS,TREFHT",
        }
        compare(self, actual_section, expected_section)
        actual_tasks = getTasks(config, section_name)
        self.assertEqual(len(actual_tasks), 2)
        actual_task = actual_tasks[0]
        expected_task = {
            "active": "True",
            "account": "",
            "area_nm": "area",
            "bundle": "",
            "campaign": "none",
            "case": "CASE",
            "cmip_metadata": "e3sm_to_cmip/default_metadata.json",
            "constraint": "",
            "debug": False,
            "dpf": 30,
            "dry_run": False,
            "environment_commands": "",
            "extra_vars": "",
            "frequency": "monthly",
            "grid": "",
            "input": "INPUT",
            "input_files": "eam.h0",
            "input_subdir": "INPUT_SUBDIR",
            "mapping_file": "MAPPING_FILE_TS_GRID1",
            "nodes": 1,
            "output": "OUTPUT",
            "partition": "SHORT",
            "plugins": [],
            "qos": "regular",
            "subsection": "ts_grid1",
            "templateDir": "zppy/templates",
            "tpd": 1,
            "ts_fmt": "ts_only",
            "vars": "FSNTOA,FLUT,FSNT,FLNT,FSNS,FLNS,SHFLX,QFLX,PRECC,PRECL,PRECSC,PRECSL,TS,TREFHT",
            "walltime": "02:00:00",
            "www": "WWWW",
            "years": ["0001:0020:5"],
        }
        compare(self, actual_task, expected_task)
        actual_task = actual_tasks[1]
        expected_task = {
            "active": "True",
            "account": "",
            "area_nm": "area",
            "bundle": "",
            "campaign": "none",
            "case": "CASE",
            "cmip_metadata": "e3sm_to_cmip/default_metadata.json",
            "constraint": "",
            "debug": False,
            "dpf": 30,
            "dry_run": False,
            "environment_commands": "",
            "extra_vars": "",
            "frequency": "monthly",
            "grid": "",
            "input": "INPUT",
            "input_files": "eam.h0",
            "input_subdir": "INPUT_SUBDIR",
            "mapping_file": "MAPPING_FILE_TS_GRID2",
            "nodes": 1,
            "output": "OUTPUT",
            "partition": "SHORT",
            "plugins": [],
            "qos": "regular",
            "subsection": "ts_grid2",
            "templateDir": "zppy/templates",
            "tpd": 1,
            "ts_fmt": "ts_only",
            "vars": "FSNTOA,FLUT,FSNT,FLNT,FSNS,FLNS,SHFLX,QFLX,PRECC,PRECL,PRECSC,PRECSL,TS,TREFHT",
            "walltime": "02:00:00",
            "www": "WWWW",
            "years": ["0001:0020:10"],
        }
        compare(self, actual_task, expected_task)

        # climo
        section_name = "climo"
        actual_section = config[section_name]
        expected_section = {
            "active": "True",
            "climo_grid1": {
                "mapping_file": "MAPPING_FILE_CLIMO_GRID1",
                "nodes": None,
                "exclude": None,
                "vars": None,
            },
            "climo_grid2": {
                "mapping_file": "MAPPING_FILE_CLIMO_GRID2",
                "years": ["0001:0100:50"],
                "partition": "LONG",
                "nodes": None,
                "exclude": None,
                "vars": None,
            },
            "exclude": False,
            "mapping_file": "MAPPING_FILE_CLIMO",
            "nodes": 4,
            "vars": "",
            "years": ["0001:0050:50"],
        }
        compare(self, actual_section, expected_section)
        actual_tasks = getTasks(config, section_name)
        self.assertEqual(len(actual_tasks), 2)
        actual_task = actual_tasks[0]
        expected_task = {
            "active": "True",
            "account": "",
            "bundle": "",
            "campaign": "none",
            "case": "CASE",
            "constraint": "",
            "debug": False,
            "dry_run": False,
            "environment_commands": "",
            "exclude": False,
            "frequency": "monthly",
            "grid": "",
            "input": "INPUT",
            "input_files": "eam.h0",
            "input_subdir": "INPUT_SUBDIR",
            "mapping_file": "MAPPING_FILE_CLIMO_GRID1",
            "nodes": 4,
            "output": "OUTPUT",
            "partition": "SHORT",
            "plugins": [],
            "qos": "regular",
            "subsection": "climo_grid1",
            "templateDir": "zppy/templates",
            "vars": "",
            "walltime": "02:00:00",
            "www": "WWWW",
            "years": ["0001:0050:50"],
        }
        compare(self, actual_task, expected_task)
        actual_task = actual_tasks[1]
        expected_task = {
            "active": "True",
            "account": "",
            "bundle": "",
            "campaign": "none",
            "case": "CASE",
            "constraint": "",
            "debug": False,
            "dry_run": False,
            "environment_commands": "",
            "exclude": False,
            "frequency": "monthly",
            "grid": "",
            "input": "INPUT",
            "input_files": "eam.h0",
            "input_subdir": "INPUT_SUBDIR",
            "mapping_file": "MAPPING_FILE_CLIMO_GRID2",
            "nodes": 4,
            "output": "OUTPUT",
            "partition": "LONG",
            "plugins": [],
            "qos": "regular",
            "subsection": "climo_grid2",
            "templateDir": "zppy/templates",
            "vars": "",
            "walltime": "02:00:00",
            "www": "WWWW",
            "years": ["0001:0100:50"],
        }
        compare(self, actual_task, expected_task)


if __name__ == "__main__":
    unittest.main()
