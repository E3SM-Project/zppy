import os
import pprint

import pytest
from configobj import ConfigObj, Section
from validate import Validator

from zppy.utils import get_tasks


def compare(actual, expected):
    if actual != expected:
        actual_keys = set(actual.keys())
        expected_keys = set(expected.keys())
        if actual_keys != expected_keys:
            only_in_actual = actual_keys - expected_keys
            print("only_in_actual={}".format(only_in_actual))
            assert only_in_actual == set()
            only_in_expected = expected_keys - actual_keys
            print("only_in_expected={}".format(only_in_expected))
            assert only_in_expected == set()
        incorrect_values = []
        for key in actual_keys:
            if isinstance(actual[key], Section):
                print("Calling `compare` again on {}".format(key))
                compare(actual[key], expected[key])
            elif actual[key] != expected[key]:
                incorrect_values.append((key, actual[key], expected[key]))
        print("incorrect_values=")
        for v in incorrect_values:
            print(v)
        assert incorrect_values == []


def get_config(config_file):
    # Subdirectory where templates are located
    defaults_dir = os.path.join("zppy", "defaults")

    # Read configuration file and validate it
    config = ConfigObj(
        config_file, configspec=os.path.join(defaults_dir, "default.ini")
    )
    validator = Validator()

    assert config.validate(validator)

    # Add templateDir to config
    config["default"]["templateDir"] = os.path.join("zppy", "templates")

    # For debugging
    DISPLAY_CONFIG = False
    if DISPLAY_CONFIG:
        with open("{}.txt".format(config_file), "w") as output:
            p = pprint.PrettyPrinter(indent=2, stream=output)
            p.pprint(config)
        pytest.maxdiff = None

    return config


def test_sections():
    config = get_config("tests/test_sections.cfg")

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
        "fail_on_dependency_skip": False,
        "frequency": "monthly",
        "grid": "",
        "infer_section_parameters": True,
        "infer_path_parameters": True,
        "input": "INPUT",
        "input_files": "eam.h0",
        "input_subdir": "INPUT_SUBDIR",
        "mapping_file": "",
        "output": "OUTPUT",
        "nodes": 1,
        "parallel": "",
        "partition": "SHORT",
        "plugins": [],
        "reservation": "",
        "qos": "regular",
        "templateDir": "zppy/templates",
        "ts_atm_grid": "180x360_aave",
        "ts_atm_subsection": "",
        "ts_grid": "180x360_aave",
        "ts_land_grid": "180x360_aave",
        "ts_land_subsection": "",
        "ts_num_years": 5,
        "ts_subsection": "",
        "vars": "FSNTOA,FLUT,FSNT,FLNT,FSNS,FLNS,SHFLX,QFLX,TAUX,TAUY,PRECC,PRECL,PRECSC,PRECSL,TS,TREFHT,CLDTOT,CLDHGH,CLDMED,CLDLOW,U",
        "vars_exclude": "H2OSOI,LAKEICEFRAC,O_SCALAR,PCT_LANDUNIT,PCT_NAT_PFT,SOILICE,SOILICE_ICE,SOILLIQ,SOILLIQ_ICE,SOILPSI,T_SCALAR,TLAKE,TSOI,TSOI_ICE,W_SCALAR",
        "walltime": "02:00:00",
        "www": "WWWW",
        "years": [""],
    }
    compare(actual_default, expected_default)

    # ts
    section_name = "ts"
    actual_section = config[section_name]
    expected_section = {
        "active": "True",
        "area_nm": "area",
        "dpf": 30,
        "extra_vars": "",
        "input_component": "",
        "mapping_file": "MAPPING_FILE_TS",
        "tpd": 1,
        "vars": "FSNTOA,FLUT,FSNT,FLNT,FSNS,FLNS,SHFLX,QFLX,PRECC,PRECL,PRECSC,PRECSL,TS,TREFHT",
        "years": ["0001:0020:5"],
    }
    compare(actual_section, expected_section)
    actual_tasks = get_tasks(config, section_name)
    assert len(actual_tasks) == 1
    actual_task = actual_tasks[0]
    expected_task = {
        "active": "True",
        "account": "",
        "bundle": "",
        "area_nm": "area",
        "campaign": "none",
        "case": "CASE",
        "constraint": "",
        "debug": False,
        "dpf": 30,
        "dry_run": False,
        "environment_commands": "",
        "extra_vars": "",
        "fail_on_dependency_skip": False,
        "frequency": "monthly",
        "grid": "",
        "infer_section_parameters": True,
        "infer_path_parameters": True,
        "input": "INPUT",
        "input_component": "",
        "input_files": "eam.h0",
        "input_subdir": "INPUT_SUBDIR",
        "mapping_file": "MAPPING_FILE_TS",
        "nodes": 1,
        "output": "OUTPUT",
        "parallel": "",
        "partition": "SHORT",
        "plugins": [],
        "qos": "regular",
        "reservation": "",
        "subsection": None,
        "templateDir": "zppy/templates",
        "tpd": 1,
        "ts_atm_grid": "180x360_aave",
        "ts_atm_subsection": "",
        "ts_grid": "180x360_aave",
        "ts_land_grid": "180x360_aave",
        "ts_land_subsection": "",
        "ts_num_years": 5,
        "ts_subsection": "",
        "vars": "FSNTOA,FLUT,FSNT,FLNT,FSNS,FLNS,SHFLX,QFLX,PRECC,PRECL,PRECSC,PRECSL,TS,TREFHT",
        "vars_exclude": "H2OSOI,LAKEICEFRAC,O_SCALAR,PCT_LANDUNIT,PCT_NAT_PFT,SOILICE,SOILICE_ICE,SOILLIQ,SOILLIQ_ICE,SOILPSI,T_SCALAR,TLAKE,TSOI,TSOI_ICE,W_SCALAR",
        "walltime": "02:00:00",
        "www": "WWWW",
        "years": ["0001:0020:5"],
    }
    compare(actual_task, expected_task)

    # climo
    section_name = "climo"
    actual_section = config[section_name]
    expected_section = {
        "active": "True",
        "exclude": False,
        "input_component": "",
        "mapping_file": "MAPPING_FILE_CLIMO",
        "nodes": 4,
        "parallel": "mpi",
        "vars": "",
        "years": ["0001:0050:50"],
    }
    compare(actual_section, expected_section)
    actual_tasks = get_tasks(config, section_name)
    compare(len(actual_tasks), 1)
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
        "fail_on_dependency_skip": False,
        "frequency": "monthly",
        "grid": "",
        "infer_section_parameters": True,
        "infer_path_parameters": True,
        "input": "INPUT",
        "input_component": "",
        "input_files": "eam.h0",
        "input_subdir": "INPUT_SUBDIR",
        "mapping_file": "MAPPING_FILE_CLIMO",
        "nodes": 4,
        "output": "OUTPUT",
        "parallel": "mpi",
        "partition": "SHORT",
        "plugins": [],
        "qos": "regular",
        "reservation": "",
        "subsection": None,
        "templateDir": "zppy/templates",
        "ts_atm_grid": "180x360_aave",
        "ts_atm_subsection": "",
        "ts_grid": "180x360_aave",
        "ts_land_grid": "180x360_aave",
        "ts_land_subsection": "",
        "ts_num_years": 5,
        "ts_subsection": "",
        "vars": "",
        "vars_exclude": "H2OSOI,LAKEICEFRAC,O_SCALAR,PCT_LANDUNIT,PCT_NAT_PFT,SOILICE,SOILICE_ICE,SOILLIQ,SOILLIQ_ICE,SOILPSI,T_SCALAR,TLAKE,TSOI,TSOI_ICE,W_SCALAR",
        "walltime": "02:00:00",
        "www": "WWWW",
        "years": ["0001:0050:50"],
    }
    compare(actual_task, expected_task)

    # tc_analysis: test an inactive task
    section_name = "tc_analysis"
    actual_section = config[section_name]
    assert actual_section["active"] == "False"
    actual_tasks = get_tasks(config, section_name)
    assert len(actual_tasks) == 0

    # e3sm_diags: test an excluded task
    section_name = "e3sm_diags"
    actual_section = config[section_name]
    assert "active" not in actual_section.keys()
    actual_tasks = get_tasks(config, section_name)
    assert len(actual_tasks) == 0


def test_subsections():
    config = get_config("tests/test_subsections.cfg")

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
        "fail_on_dependency_skip": False,
        "frequency": "monthly",
        "grid": "",
        "infer_section_parameters": True,
        "infer_path_parameters": True,
        "input": "INPUT",
        "input_files": "eam.h0",
        "input_subdir": "INPUT_SUBDIR",
        "mapping_file": "",
        "nodes": 1,
        "output": "OUTPUT",
        "parallel": "",
        "partition": "SHORT",
        "plugins": [],
        "qos": "regular",
        "reservation": "",
        "templateDir": "zppy/templates",
        "ts_atm_grid": "180x360_aave",
        "ts_atm_subsection": "",
        "ts_grid": "180x360_aave",
        "ts_land_grid": "180x360_aave",
        "ts_land_subsection": "",
        "ts_num_years": 5,
        "ts_subsection": "",
        "vars": "FSNTOA,FLUT,FSNT,FLNT,FSNS,FLNS,SHFLX,QFLX,TAUX,TAUY,PRECC,PRECL,PRECSC,PRECSL,TS,TREFHT,CLDTOT,CLDHGH,CLDMED,CLDLOW,U",
        "vars_exclude": "H2OSOI,LAKEICEFRAC,O_SCALAR,PCT_LANDUNIT,PCT_NAT_PFT,SOILICE,SOILICE_ICE,SOILLIQ,SOILLIQ_ICE,SOILPSI,T_SCALAR,TLAKE,TSOI,TSOI_ICE,W_SCALAR",
        "walltime": "02:00:00",
        "www": "WWWW",
        "years": [""],
    }
    compare(actual_default, expected_default)

    # ts
    section_name = "ts"
    actual_section = config[section_name]
    expected_section = {
        "active": "True",
        "area_nm": "area",
        "dpf": 30,
        "extra_vars": "",
        "input_component": "",
        "tpd": 1,
        "ts_grid1": {
            "area_nm": None,
            "dpf": None,
            "extra_vars": None,
            "input_component": None,
            "mapping_file": "MAPPING_FILE_TS_GRID1",
            "tpd": None,
            "years": ["0001:0020:5"],
        },
        "ts_grid2": {
            "area_nm": None,
            "dpf": None,
            "extra_vars": None,
            "input_component": None,
            "mapping_file": "MAPPING_FILE_TS_GRID2",
            "tpd": None,
            "years": ["0001:0020:10"],
        },
        "vars": "FSNTOA,FLUT,FSNT,FLNT,FSNS,FLNS,SHFLX,QFLX,PRECC,PRECL,PRECSC,PRECSL,TS,TREFHT",
    }
    compare(actual_section, expected_section)
    actual_tasks = get_tasks(config, section_name)
    assert len(actual_tasks) == 2
    actual_task = actual_tasks[0]
    expected_task = {
        "active": "True",
        "account": "",
        "area_nm": "area",
        "bundle": "",
        "campaign": "none",
        "case": "CASE",
        "constraint": "",
        "debug": False,
        "dpf": 30,
        "dry_run": False,
        "environment_commands": "",
        "extra_vars": "",
        "fail_on_dependency_skip": False,
        "frequency": "monthly",
        "grid": "",
        "infer_section_parameters": True,
        "infer_path_parameters": True,
        "input": "INPUT",
        "input_component": "",
        "input_files": "eam.h0",
        "input_subdir": "INPUT_SUBDIR",
        "mapping_file": "MAPPING_FILE_TS_GRID1",
        "nodes": 1,
        "output": "OUTPUT",
        "parallel": "",
        "partition": "SHORT",
        "plugins": [],
        "qos": "regular",
        "reservation": "",
        "subsection": "ts_grid1",
        "templateDir": "zppy/templates",
        "tpd": 1,
        "ts_atm_grid": "180x360_aave",
        "ts_atm_subsection": "",
        "ts_grid": "180x360_aave",
        "ts_land_grid": "180x360_aave",
        "ts_land_subsection": "",
        "ts_num_years": 5,
        "ts_subsection": "",
        "vars": "FSNTOA,FLUT,FSNT,FLNT,FSNS,FLNS,SHFLX,QFLX,PRECC,PRECL,PRECSC,PRECSL,TS,TREFHT",
        "vars_exclude": "H2OSOI,LAKEICEFRAC,O_SCALAR,PCT_LANDUNIT,PCT_NAT_PFT,SOILICE,SOILICE_ICE,SOILLIQ,SOILLIQ_ICE,SOILPSI,T_SCALAR,TLAKE,TSOI,TSOI_ICE,W_SCALAR",
        "walltime": "02:00:00",
        "www": "WWWW",
        "years": ["0001:0020:5"],
    }
    compare(actual_task, expected_task)
    actual_task = actual_tasks[1]
    expected_task = {
        "active": "True",
        "account": "",
        "area_nm": "area",
        "bundle": "",
        "campaign": "none",
        "case": "CASE",
        "constraint": "",
        "debug": False,
        "dpf": 30,
        "dry_run": False,
        "environment_commands": "",
        "extra_vars": "",
        "fail_on_dependency_skip": False,
        "frequency": "monthly",
        "grid": "",
        "infer_section_parameters": True,
        "infer_path_parameters": True,
        "input": "INPUT",
        "input_component": "",
        "input_files": "eam.h0",
        "input_subdir": "INPUT_SUBDIR",
        "mapping_file": "MAPPING_FILE_TS_GRID2",
        "nodes": 1,
        "output": "OUTPUT",
        "parallel": "",
        "partition": "SHORT",
        "plugins": [],
        "qos": "regular",
        "reservation": "",
        "subsection": "ts_grid2",
        "templateDir": "zppy/templates",
        "tpd": 1,
        "ts_atm_grid": "180x360_aave",
        "ts_atm_subsection": "",
        "ts_grid": "180x360_aave",
        "ts_land_grid": "180x360_aave",
        "ts_land_subsection": "",
        "ts_num_years": 5,
        "ts_subsection": "",
        "vars": "FSNTOA,FLUT,FSNT,FLNT,FSNS,FLNS,SHFLX,QFLX,PRECC,PRECL,PRECSC,PRECSL,TS,TREFHT",
        "vars_exclude": "H2OSOI,LAKEICEFRAC,O_SCALAR,PCT_LANDUNIT,PCT_NAT_PFT,SOILICE,SOILICE_ICE,SOILLIQ,SOILLIQ_ICE,SOILPSI,T_SCALAR,TLAKE,TSOI,TSOI_ICE,W_SCALAR",
        "walltime": "02:00:00",
        "www": "WWWW",
        "years": ["0001:0020:10"],
    }
    compare(actual_task, expected_task)

    # climo
    section_name = "climo"
    actual_section = config[section_name]
    expected_section = {
        "active": "True",
        "climo_grid1": {
            "input_component": None,
            "mapping_file": "MAPPING_FILE_CLIMO_GRID1",
            "nodes": None,
            "exclude": None,
            "vars": None,
        },
        "climo_grid2": {
            "input_component": None,
            "mapping_file": "MAPPING_FILE_CLIMO_GRID2",
            "years": ["0001:0100:50"],
            "partition": "LONG",
            "nodes": None,
            "exclude": None,
            "vars": None,
        },
        "exclude": False,
        "input_component": "",
        "mapping_file": "MAPPING_FILE_CLIMO",
        "nodes": 4,
        "parallel": "mpi",
        "vars": "",
        "years": ["0001:0050:50"],
    }
    compare(actual_section, expected_section)
    actual_tasks = get_tasks(config, section_name)
    assert len(actual_tasks) == 2
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
        "fail_on_dependency_skip": False,
        "frequency": "monthly",
        "grid": "",
        "infer_section_parameters": True,
        "infer_path_parameters": True,
        "input": "INPUT",
        "input_component": "",
        "input_files": "eam.h0",
        "input_subdir": "INPUT_SUBDIR",
        "mapping_file": "MAPPING_FILE_CLIMO_GRID1",
        "nodes": 4,
        "output": "OUTPUT",
        "parallel": "mpi",
        "partition": "SHORT",
        "plugins": [],
        "qos": "regular",
        "reservation": "",
        "subsection": "climo_grid1",
        "templateDir": "zppy/templates",
        "ts_atm_grid": "180x360_aave",
        "ts_atm_subsection": "",
        "ts_grid": "180x360_aave",
        "ts_land_grid": "180x360_aave",
        "ts_land_subsection": "",
        "ts_num_years": 5,
        "ts_subsection": "",
        "vars": "",
        "vars_exclude": "H2OSOI,LAKEICEFRAC,O_SCALAR,PCT_LANDUNIT,PCT_NAT_PFT,SOILICE,SOILICE_ICE,SOILLIQ,SOILLIQ_ICE,SOILPSI,T_SCALAR,TLAKE,TSOI,TSOI_ICE,W_SCALAR",
        "walltime": "02:00:00",
        "www": "WWWW",
        "years": ["0001:0050:50"],
    }
    compare(actual_task, expected_task)
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
        "fail_on_dependency_skip": False,
        "frequency": "monthly",
        "grid": "",
        "infer_section_parameters": True,
        "infer_path_parameters": True,
        "input": "INPUT",
        "input_component": "",
        "input_files": "eam.h0",
        "input_subdir": "INPUT_SUBDIR",
        "mapping_file": "MAPPING_FILE_CLIMO_GRID2",
        "nodes": 4,
        "output": "OUTPUT",
        "parallel": "mpi",
        "partition": "LONG",
        "plugins": [],
        "reservation": "",
        "qos": "regular",
        "subsection": "climo_grid2",
        "templateDir": "zppy/templates",
        "ts_atm_grid": "180x360_aave",
        "ts_atm_subsection": "",
        "ts_grid": "180x360_aave",
        "ts_land_grid": "180x360_aave",
        "ts_land_subsection": "",
        "ts_num_years": 5,
        "ts_subsection": "",
        "vars": "",
        "vars_exclude": "H2OSOI,LAKEICEFRAC,O_SCALAR,PCT_LANDUNIT,PCT_NAT_PFT,SOILICE,SOILICE_ICE,SOILLIQ,SOILLIQ_ICE,SOILPSI,T_SCALAR,TLAKE,TSOI,TSOI_ICE,W_SCALAR",
        "walltime": "02:00:00",
        "www": "WWWW",
        "years": ["0001:0100:50"],
    }
    compare(actual_task, expected_task)
