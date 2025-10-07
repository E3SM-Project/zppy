import re
import subprocess
from typing import Any, Dict

from mache import MachineInfo

# To run:
# `python -m pip install .` latest code into conda env
# Update TEST_SPECIFICS below
# python tests/integration/utils.py
# zppy -c <generated cfg>
# pytest tests/integration/test_*.py

TEST_SPECIFICS: Dict[str, Any] = {
    "diags_environment_commands": "source /lcrc/soft/climate/e3sm-unified/load_latest_e3sm_unified_chrysalis.sh",
    "global_time_series_environment_commands": "source /gpfs/fs1/home/ac.forsyth2/miniforge3/etc/profile.d/conda.sh; conda activate zi-pcmdi-diags-20251007-test1",
    "pcmdi_diags_environment_commands": "source /gpfs/fs1/home/ac.forsyth2/miniforge3/etc/profile.d/conda.sh; conda activate zi-pcmdi-diags-20251007-test1",
    "cfgs_to_run": [
        "weekly_comprehensive_v3",
    ],
    "tasks_to_run": [
        "pcmdi_diags",
    ],
    "unique_id": "unique_id_test_20251007_3",
}

# Multi-machine testing #########################################################
# Inspired by https://github.com/E3SM-Project/e3sm_diags/blob/master/docs/source/quickguides/generate_quick_guides.py


def get_chyrsalis_expansions(config):
    # Note: `os.environ.get("USER")` also works. Here we're already using mache but not os, so using mache.
    username = config.get("web_portal", "username")
    web_base_path = config.get("web_portal", "base_path")
    d = {
        "bundles_walltime": "07:00:00",
        "case_name": "v3.LR.historical_0051",
        "case_name_v2": "v2.LR.historical_0201",
        "constraint": "",
        "diags_walltime": "5:00:00",
        "environment_commands_test": "",
        "expected_dir": "/lcrc/group/e3sm/public_html/zppy_test_resources/",
        "mpas_analysis_walltime": "00:30:00",
        "partition_long": "compute",
        "partition_short": "debug",
        "qos_long": "regular",
        "qos_short": "regular",
        "user_input_v2": "/lcrc/group/e3sm/ac.forsyth2/",
        "user_input_v3": "/lcrc/group/e3sm2/ac.wlin/",
        "user_output": f"/lcrc/group/e3sm/{username}/",
        "user_www": f"{web_base_path}/{username}/",
    }
    return d


def get_compy_expansions(config):
    username = config.get("web_portal", "username")
    web_base_path = config.get("web_portal", "base_path")
    d = {
        "bundles_walltime": "02:00:00",
        "case_name": "v3.LR.historical_0051",
        "case_name_v2": "v2.LR.historical_0201",
        "constraint": "",
        "diags_walltime": "03:00:00",
        "environment_commands_test": "",
        "expected_dir": "/compyfs/www/zppy_test_resources/",
        "mpas_analysis_walltime": "02:00:00",
        "partition_long": "slurm",
        "partition_short": "short",
        "qos_long": "regular",
        "qos_short": "regular",
        "user_input_v2": "/compyfs/fors729/",
        "user_input_v3": "/compyfs/fors729/",
        "user_output": f"/compyfs/{username}/",
        "user_www": f"{web_base_path}/{username}/",
    }
    return d


def get_perlmutter_expansions(config):
    username = config.get("web_portal", "username")
    web_base_path = config.get("web_portal", "base_path")
    d = {
        "bundles_walltime": "6:00:00",
        "case_name": "v3.LR.historical_0051",
        "case_name_v2": "v2.LR.historical_0201",
        "constraint": "cpu",
        "diags_walltime": "6:00:00",
        "environment_commands_test": "",
        "expected_dir": "/global/cfs/cdirs/e3sm/www/zppy_test_resources/",
        "mpas_analysis_walltime": "03:00:00",
        "partition_long": "",
        "partition_short": "",
        "qos_long": "regular",
        "qos_short": "regular",  # debug walltime too short?
        # Use CFS for large datasets
        "user_input_v2": "/global/cfs/cdirs/e3sm/forsyth/",
        "user_input_v3": "/global/cfs/cdirs/e3sm/forsyth/",
        "user_output": f"/global/cfs/cdirs/e3sm/{username}/",
        "user_www": f"{web_base_path}/{username}/",
    }
    return d


def get_expansions():
    machine_info = MachineInfo()
    config = machine_info.config
    machine = machine_info.machine
    if machine == "chrysalis":
        expansions = get_chyrsalis_expansions(config)
    elif machine == "compy":
        expansions = get_compy_expansions(config)
    elif machine == "pm-cpu":
        expansions = get_perlmutter_expansions(config)
    else:
        raise ValueError(f"Unsupported machine={machine}")

    # Set up environments
    # To run this test, replace conda environment with your e3sm_diags dev environment
    # Or the Unified environment
    # (The same for `global_time_series_environment_commands`)
    # Never set this to "" because it will print the line
    # `environment_commands = ""` for the [e3sm_diags] task, overriding zppy's
    # default of using Unified. That is, there will be no environment set.
    # `environment_commands = ""` only redirects to Unified if specified under the
    # [default] task
    expansions["diags_environment_commands"] = TEST_SPECIFICS[
        "diags_environment_commands"
    ]
    expansions["global_time_series_environment_commands"] = TEST_SPECIFICS[
        "global_time_series_environment_commands"
    ]
    expansions["pcmdi_diags_environment_commands"] = TEST_SPECIFICS[
        "pcmdi_diags_environment_commands"
    ]

    # Activate requested tests
    expansions["active_e3sm_to_cmip"] = "False"
    expansions["active_e3sm_diags"] = "False"
    expansions["active_mpas_analysis"] = "False"
    expansions["active_global_time_series"] = "False"
    expansions["active_ilamb"] = "False"
    expansions["active_pcmdi_diags"] = "False"
    if "e3sm_diags" in TEST_SPECIFICS["tasks_to_run"]:
        expansions["active_e3sm_diags"] = "True"
    if "mpas_analysis" in TEST_SPECIFICS["tasks_to_run"]:
        expansions["active_mpas_analysis"] = "True"
    if "global_time_series" in TEST_SPECIFICS["tasks_to_run"]:
        expansions["active_global_time_series"] = "True"
        expansions["active_mpas_analysis"] = "True"  # For ocn plots
        expansions["active_e3sm_to_cmip"] = "True"  # For lnd plots
    if "ilamb" in TEST_SPECIFICS["tasks_to_run"]:
        expansions["active_ilamb"] = "True"
        expansions["active_e3sm_to_cmip"] = "True"
    if "pcmdi_diags" in TEST_SPECIFICS["tasks_to_run"]:
        expansions["active_pcmdi_diags"] = "True"
        expansions["active_e3sm_to_cmip"] = "True"
    expansions["cfgs_to_run"] = TEST_SPECIFICS["cfgs_to_run"]
    expansions["tasks_to_run"] = TEST_SPECIFICS["tasks_to_run"]

    expansions["diagnostics_base_path"] = config.get("diagnostics", "base_path")
    expansions["machine"] = machine
    expansions["unique_id"] = TEST_SPECIFICS["unique_id"]
    return expansions


def substitute_expansions(expansions, file_in, file_out):
    with open(file_in, "r") as file_read:
        with open(file_out, "w") as file_write:
            # For line in file, if line matches #expand <expansion_name>#, then replace text with <expansion>.
            # Send output to the corresponding specific cfg file.
            for line in file_read:
                match_object = re.search("#expand ([^#]*)#", line)
                while match_object is not None:
                    expansion_indicator = match_object.group(0)
                    expansion_name = match_object.group(1)
                    expansion = expansions[expansion_name]
                    try:
                        line = line.replace(expansion_indicator, expansion)
                    except TypeError as e:
                        raise TypeError(
                            f"Error replacing {expansion_indicator} with {expansion} of type {type(expansion)}"
                        ) from e
                    match_object = re.search("#expand ([^#]*)#", line)
                file_write.write(line)


def generate_cfgs(unified_testing=False, dry_run=False):
    git_top_level = (
        subprocess.check_output("git rev-parse --show-toplevel".split())
        .strip()
        .decode("utf-8")
    )
    expansions = get_expansions()
    if unified_testing:
        expansions["environment_commands"] = expansions["environment_commands_test"]
        # Use Unified for e3sm_diags and global_time_series unless we specify otherwise
        if expansions["diags_environment_commands"] == "":
            expansions["diags_environment_commands"] = expansions[
                "environment_commands_test"
            ]
        if expansions["global_time_series_environment_commands"] == "":
            expansions["global_time_series_environment_commands"] = expansions[
                "environment_commands_test"
            ]
    else:
        # The cfg doesn't need this line,
        # but it would be difficult to only write environment_commands in the unified_testing case.
        expansions["environment_commands"] = ""
    machine = expansions["machine"]

    if dry_run:
        expansions["dry_run"] = "True"
    else:
        expansions["dry_run"] = "False"

    full_list_cfg_names = [
        "min_case_add_dependencies",
        "min_case_carryover_dependencies",
        "min_case_deprecated_parameters",
        "min_case_tc_analysis_only",
        "min_case_tc_analysis_res",
        "min_case_tc_analysis_simultaneous_1",
        "min_case_tc_analysis_simultaneous_2",
        "min_case_tc_analysis_v2_simultaneous_1",
        "min_case_tc_analysis_v2_simultaneous_2",
        "min_case_e3sm_diags_depend_on_climo_mvm_1",
        "min_case_e3sm_diags_depend_on_climo_mvm_2",
        "min_case_e3sm_diags_depend_on_climo",
        "min_case_e3sm_diags_depend_on_ts_mvm_1",
        "min_case_e3sm_diags_depend_on_ts_mvm_2",
        "min_case_e3sm_diags_depend_on_ts",
        "min_case_e3sm_diags_diurnal_cycle_mvm_1",
        "min_case_e3sm_diags_diurnal_cycle_mvm_2",
        "min_case_e3sm_diags_diurnal_cycle",
        "min_case_e3sm_diags_lat_lon_land_mvm_1",
        "min_case_e3sm_diags_lat_lon_land_mvm_2",
        # "min_case_e3sm_diags_lat_lon_land",
        "min_case_e3sm_diags_streamflow_mvm_1",
        "min_case_e3sm_diags_streamflow_mvm_2",
        "min_case_e3sm_diags_streamflow",
        "min_case_e3sm_diags_tc_analysis_mvm_1",
        "min_case_e3sm_diags_tc_analysis_mvm_2",
        "min_case_e3sm_diags_tc_analysis_parallel",
        "min_case_e3sm_diags_tc_analysis_v2_mvm_1",
        "min_case_e3sm_diags_tc_analysis_v2_mvm_2",
        "min_case_e3sm_diags_tc_analysis_v2_parallel",
        "min_case_e3sm_diags_tc_analysis_v2",
        "min_case_e3sm_diags_tc_analysis",
        "min_case_e3sm_diags_tropical_subseasonal_mvm_1",
        "min_case_e3sm_diags_tropical_subseasonal_mvm_2",
        "min_case_e3sm_diags_tropical_subseasonal",
        "min_case_global_time_series_comprehensive_v3_setup_only",
        "min_case_global_time_series_custom",
        "min_case_global_time_series_original_8_missing_ocn",
        "min_case_global_time_series_original_8_no_ocn",
        "min_case_global_time_series_original_8",
        "min_case_global_time_series_viewers",
        "min_case_global_time_series_viewers_all_land_variables",
        "min_case_global_time_series_viewers_original_8",
        "min_case_global_time_series_viewers_original_atm_plus_land",
        "min_case_global_time_series_viewers_undefined_variables",
        "min_case_ilamb_diff_years",
        "min_case_ilamb_land_only",
        "min_case_ilamb",
        "min_case_mpas_analysis",
        "min_case_nco",
        "weekly_bundles",
        "weekly_comprehensive_v2",
        "weekly_comprehensive_v3",
        "weekly_legacy_3.0.0_bundles",
        "weekly_legacy_3.0.0_comprehensive_v2",
        "weekly_legacy_3.0.0_comprehensive_v3",
    ]
    if TEST_SPECIFICS["cfgs_to_run"] == []:
        cfg_names = full_list_cfg_names
    else:
        cfg_names = TEST_SPECIFICS["cfgs_to_run"]
    for cfg_name in cfg_names:
        cfg_template = f"{git_top_level}/tests/integration/template_{cfg_name}.cfg"
        cfg_generated = (
            f"{git_top_level}/tests/integration/generated/test_{cfg_name}_{machine}.cfg"
        )
        substitute_expansions(expansions, cfg_template, cfg_generated)

    directions_template = f"{git_top_level}/tests/integration/template_directions.md"
    directions_generated = (
        f"{git_top_level}/tests/integration/generated/directions_{machine}.md"
    )
    substitute_expansions(expansions, directions_template, directions_generated)

    script_names = [
        "archive",
        "bash_generation",
        "campaign",
        "defaults",
        "weekly",  # for both test_bundles and test_images
    ]
    for script_name in script_names:
        script_template = f"{git_top_level}/tests/integration/template_update_{script_name}_expected_files.sh"
        script_generated = f"{git_top_level}/tests/integration/generated/update_{script_name}_expected_files_{machine}.sh"
        substitute_expansions(expansions, script_template, script_generated)
    print("CFG FILES HAVE BEEN GENERATED FROM TEMPLATES WITH THESE SETTINGS:")
    print(f"UNIQUE_ID={TEST_SPECIFICS['unique_id']}")
    print(f"unified_testing={unified_testing}")
    print(f"diags_environment_commands={expansions['diags_environment_commands']}")
    print(
        f"global_time_series_environment_commands={expansions['global_time_series_environment_commands']}"
    )
    print(
        f"pcmdi_diags_environment_commands={expansions['pcmdi_diags_environment_commands']}"
    )
    print(f"environment_commands={expansions['environment_commands']}")
    print(
        "Reminder: `environment_commands=''` => the latest E3SM Unified environment will be used"
    )


if __name__ == "__main__":
    generate_cfgs(unified_testing=False, dry_run=False)
