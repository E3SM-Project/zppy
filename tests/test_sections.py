import os
import unittest

from configobj import ConfigObj
from validate import Validator

from zppy.utils import getTasks


def get_config(test_case, config_file):
    # Subdirectory where templates are located
    templateDir = os.path.join("zppy", "templates")

    # Read configuration file and validate it
    config = ConfigObj(config_file, configspec=os.path.join(templateDir, "default.ini"))
    validator = Validator()

    test_case.assertTrue(config.validate(validator))

    # Add templateDir to config
    config["default"]["templateDir"] = templateDir

    return config


class TestAllSets(unittest.TestCase):
    def test_sections(self):
        config = get_config(self, "tests/test_sections.cfg")

        # default
        actual_default = config["default"]
        expected_default = {
            "input": "INPUT",
            "input_subdir": "INPUT_SUBDIR",
            "output": "OUTPUT",
            "case": "CASE",
            "www": "WWWW",
            "partition": "SHORT",
            "debug": False,
            "e3sm_unified": "latest",
            "dry_run": False,
            "templateDir": "zppy/templates",
        }
        self.assertEqual(actual_default, expected_default)

        # ts
        section_name = "ts"
        actual_section = config[section_name]
        expected_section = {
            "active": True,
            "vars": "FSNTOA,FLUT,FSNT,FLNT,FSNS,FLNS,SHFLX,QFLX,PRECC,PRECL,PRECSC,PRECSL,TS,TREFHT",
            "mapping_file": "MAPPING_FILE_TS",
            "years": ["0001:0020:5"],
            "qos": "regular",
            "nodes": 1,
            "walltime": "02:00:00",
            "input_files": "eam.h0",
            "frequency": "monthly",
            "grid": "",
            "area_nm": "area",
            "dpf": 30,
            "tpd": 1,
        }
        self.assertEqual(actual_section, expected_section)
        actual_tasks = getTasks(config, section_name)
        self.assertEqual(len(actual_tasks), 1)
        actual_task = actual_tasks[0]
        expected_task = {
            "active": True,
            "area_nm": "area",
            "case": "CASE",
            "debug": False,
            "dpf": 30,
            "dry_run": False,
            "e3sm_unified": "latest",
            "frequency": "monthly",
            "grid": "",
            "input": "INPUT",
            "input_files": "eam.h0",
            "input_subdir": "INPUT_SUBDIR",
            "mapping_file": "MAPPING_FILE_TS",
            "nodes": 1,
            "output": "OUTPUT",
            "partition": "SHORT",
            "qos": "regular",
            "subsection": None,
            "templateDir": "zppy/templates",
            "tpd": 1,
            "vars": "FSNTOA,FLUT,FSNT,FLNT,FSNS,FLNS,SHFLX,QFLX,PRECC,PRECL,PRECSC,PRECSL,TS,TREFHT",
            "walltime": "02:00:00",
            "www": "WWWW",
            "years": ["0001:0020:5"],
        }
        self.assertEqual(actual_task, expected_task)

        # climo
        section_name = "climo"
        actual_section = config[section_name]
        expected_section = {
            "active": True,
            "years": ["0001:0050:50"],
            "mapping_file": "MAPPING_FILE_CLIMO",
            "qos": "regular",
            "nodes": 4,
            "walltime": "02:00:00",
            "input_files": "eam.h0",
            "frequency": "monthly",
            "grid": "",
            "exclude": False,
            "vars": "",
        }
        self.assertEqual(actual_section, expected_section)
        actual_tasks = getTasks(config, section_name)
        self.assertEqual(len(actual_tasks), 1)
        actual_task = actual_tasks[0]
        expected_task = {
            "active": True,
            "case": "CASE",
            "debug": False,
            "dry_run": False,
            "e3sm_unified": "latest",
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
            "qos": "regular",
            "subsection": None,
            "templateDir": "zppy/templates",
            "vars": "",
            "walltime": "02:00:00",
            "www": "WWWW",
            "years": ["0001:0050:50"],
        }
        self.assertEqual(actual_task, expected_task)

    def test_subsections(self):
        config = get_config(self, "tests/test_subsections.cfg")

        # default
        actual_default = config["default"]
        expected_default = {
            "input": "INPUT",
            "input_subdir": "INPUT_SUBDIR",
            "output": "OUTPUT",
            "case": "CASE",
            "www": "WWWW",
            "partition": "SHORT",
            "debug": False,
            "e3sm_unified": "latest",
            "dry_run": False,
            "templateDir": "zppy/templates",
        }
        self.assertEqual(actual_default, expected_default)

        # ts
        section_name = "ts"
        actual_section = config[section_name]
        expected_section = {
            "active": True,
            "vars": "FSNTOA,FLUT,FSNT,FLNT,FSNS,FLNS,SHFLX,QFLX,PRECC,PRECL,PRECSC,PRECSL,TS,TREFHT",
            "qos": "regular",
            "nodes": 1,
            "walltime": "02:00:00",
            "input_files": "eam.h0",
            "frequency": "monthly",
            "mapping_file": "",
            "grid": "",
            "area_nm": "area",
            "years": [""],
            "dpf": 30,
            "tpd": 1,
            "ts_grid1": {
                "mapping_file": "MAPPING_FILE_TS_GRID1",
                "years": ["0001:0020:5"],
                "active": None,
                "qos": None,
                "nodes": None,
                "walltime": None,
                "input_files": None,
                "frequency": None,
                "grid": None,
                "area_nm": None,
                "vars": None,
                "dpf": None,
                "tpd": None,
            },
            "ts_grid2": {
                "mapping_file": "MAPPING_FILE_TS_GRID2",
                "years": ["0001:0020:10"],
                "active": None,
                "qos": None,
                "nodes": None,
                "walltime": None,
                "input_files": None,
                "frequency": None,
                "grid": None,
                "area_nm": None,
                "vars": None,
                "dpf": None,
                "tpd": None,
            },
        }
        self.assertEqual(actual_section, expected_section)
        actual_tasks = getTasks(config, section_name)
        self.assertEqual(len(actual_tasks), 2)
        actual_task = actual_tasks[0]
        expected_task = {
            "active": True,
            "area_nm": "area",
            "case": "CASE",
            "debug": False,
            "dpf": 30,
            "dry_run": False,
            "e3sm_unified": "latest",
            "frequency": "monthly",
            "grid": "",
            "input": "INPUT",
            "input_files": "eam.h0",
            "input_subdir": "INPUT_SUBDIR",
            "mapping_file": "MAPPING_FILE_TS_GRID1",
            "nodes": 1,
            "output": "OUTPUT",
            "partition": "SHORT",
            "qos": "regular",
            "subsection": "ts_grid1",
            "templateDir": "zppy/templates",
            "tpd": 1,
            "vars": "FSNTOA,FLUT,FSNT,FLNT,FSNS,FLNS,SHFLX,QFLX,PRECC,PRECL,PRECSC,PRECSL,TS,TREFHT",
            "walltime": "02:00:00",
            "www": "WWWW",
            "years": ["0001:0020:5"],
        }
        self.assertEqual(actual_task, expected_task)
        actual_task = actual_tasks[1]
        expected_task = {
            "active": True,
            "area_nm": "area",
            "case": "CASE",
            "debug": False,
            "dpf": 30,
            "dry_run": False,
            "e3sm_unified": "latest",
            "frequency": "monthly",
            "grid": "",
            "input": "INPUT",
            "input_files": "eam.h0",
            "input_subdir": "INPUT_SUBDIR",
            "mapping_file": "MAPPING_FILE_TS_GRID2",
            "nodes": 1,
            "output": "OUTPUT",
            "partition": "SHORT",
            "qos": "regular",
            "subsection": "ts_grid2",
            "templateDir": "zppy/templates",
            "tpd": 1,
            "vars": "FSNTOA,FLUT,FSNT,FLNT,FSNS,FLNS,SHFLX,QFLX,PRECC,PRECL,PRECSC,PRECSL,TS,TREFHT",
            "walltime": "02:00:00",
            "www": "WWWW",
            "years": ["0001:0020:10"],
        }
        self.assertEqual(actual_task, expected_task)

        # climo
        section_name = "climo"
        actual_section = config[section_name]
        expected_section = {
            "active": True,
            "years": ["0001:0050:50"],
            "mapping_file": "MAPPING_FILE_CLIMO",
            "qos": "regular",
            "nodes": 4,
            "walltime": "02:00:00",
            "input_files": "eam.h0",
            "frequency": "monthly",
            "grid": "",
            "exclude": False,
            "vars": "",
            "climo_grid1": {
                "mapping_file": "MAPPING_FILE_CLIMO_GRID1",
                "active": None,
                "qos": None,
                "nodes": None,
                "walltime": None,
                "input_files": None,
                "frequency": None,
                "grid": None,
                "years": None,
                "exclude": None,
                "vars": None,
            },
            "climo_grid2": {
                "mapping_file": "MAPPING_FILE_CLIMO_GRID2",
                "years": ["0001:0100:50"],
                "partition": "LONG",
                "active": None,
                "qos": None,
                "nodes": None,
                "walltime": None,
                "input_files": None,
                "frequency": None,
                "grid": None,
                "exclude": None,
                "vars": None,
            },
        }
        self.assertEqual(actual_section, expected_section)
        actual_tasks = getTasks(config, section_name)
        self.assertEqual(len(actual_tasks), 2)
        actual_task = actual_tasks[0]
        expected_task = {
            "active": True,
            "case": "CASE",
            "debug": False,
            "dry_run": False,
            "e3sm_unified": "latest",
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
            "qos": "regular",
            "subsection": "climo_grid1",
            "templateDir": "zppy/templates",
            "vars": "",
            "walltime": "02:00:00",
            "www": "WWWW",
            "years": ["0001:0050:50"],
        }
        self.assertEqual(actual_task, expected_task)
        actual_task = actual_tasks[1]
        expected_task = {
            "active": True,
            "case": "CASE",
            "debug": False,
            "dry_run": False,
            "e3sm_unified": "latest",
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
            "qos": "regular",
            "subsection": "climo_grid2",
            "templateDir": "zppy/templates",
            "vars": "",
            "walltime": "02:00:00",
            "www": "WWWW",
            "years": ["0001:0100:50"],
        }
        self.assertEqual(actual_task, expected_task)


if __name__ == "__main__":
    unittest.main()
