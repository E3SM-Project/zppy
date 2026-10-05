import argparse
import json
import os
import re
import subprocess
from typing import Any, Dict, List, Optional, Sequence

from mache import MachineInfo

from tests.integration.weekly_cfgs import WEEKLY_CFGS

# To run:
# `python -m pip install .` latest code into conda env
# Then either edit TEST_SPECIFICS below and run:
#     python tests/integration/utils.py
# or pass the settings explicitly, leaving this file untouched:
#     python -m tests.integration.utils --unique-id my_id --cfg weekly_comprehensive_v3
# Then:
# zppy -c <generated cfg>
# pytest tests/integration/test_*.py

TEST_SPECIFICS: Dict[str, Any] = {
    # This is the NCO path.
    # Keep as "" to use the production-version NCO commands.
    # Set to a specific path to use development-version NCO commands.
    "nco_path": "",
    # These are custom environment_commands for specific tasks.
    # Never set these to "", because they will print the line
    # `environment_commands = ""` for the corresponding task,
    # thus overriding the value set higher up in the cfg.
    # That is, there will be no environment set.
    # (`environment_commands = ""` only redirects to Unified
    # if specified under the [default] task)
    "e3sm_to_cmip_environment_commands": "source <INSERT PATH TO CONDA>/conda.sh; conda activate <INSERT ENV NAME>",
    "diags_environment_commands": "source <INSERT PATH TO CONDA>/conda.sh; conda activate <INSERT ENV NAME>",
    "mpas_analysis_environment_commands": "source <INSERT PATH TO CONDA>/conda.sh; conda activate <INSERT ENV NAME>",
    "global_time_series_environment_commands": "source <INSERT PATH TO CONDA>/conda.sh; conda activate <INSERT ENV NAME>",
    "livvkit_environment_commands": "source <INSERT PATH TO CONDA>/conda.sh; conda activate <INSERT ENV NAME>",
    "pcmdi_diags_environment_commands": "source <INSERT PATH TO CONDA>/conda.sh; conda activate <INSERT ENV NAME>",
    # This is the environment setup for other tasks.
    # Leave as "" to use the latest Unified environment.
    "environment_commands": "",
    # For a complete test, run the latest cfgs and at least one legacy cfg.
    # tests/integration/weekly_cfgs.py lists every weekly cfg.
    "cfgs_to_run": [
        "weekly_bundles",
        "weekly_comprehensive_v2",
        "weekly_comprehensive_v3",
        "weekly_legacy_3.1.0_comprehensive_v3",
        # "weekly_legacy_3.0.0_comprehensive_v3",
    ],
    "tasks_to_run": [
        "e3sm_diags",
        "mpas_analysis",
        "global_time_series",
        "ilamb",
        "livvkit",
        "pcmdi_diags",
    ],
    "unique_id": "unique_id",
}

# Multi-machine testing #########################################################
# Inspired by https://github.com/E3SM-Project/e3sm_diags/blob/master/docs/source/quickguides/generate_quick_guides.py


def get_chyrsalis_expansions(config):
    # Note: `os.environ.get("USER")` also works. Here we're already using mache but not os, so using mache.
    username = config.get("web_portal", "username")
    web_base_path = config.get("web_portal", "base_path")
    diagnostics_base_path = config.get("diagnostics", "base_path")
    d = {
        "bundles_walltime": "07:00:00",
        "case_name": "v3.LR.historical_0051",
        "case_name_v2": "v2.LR.historical_0201",
        "constraint": "",
        "diags_walltime": "5:00:00",
        # Fallback for a machine with no promoted baseline yet. Once one
        # is promoted, _apply_run_locations replaces this with the
        # promoted run's settings directory.
        "expected_dir": "/lcrc/group/e3sm/public_html/zppy_test_resources/",
        "livvkit_mapping_file_path": f"{diagnostics_base_path}/maps",
        "mpas_analysis_walltime": "00:30:00",
        "partition_long": "compute",
        "partition_short": "debug",
        # This differs from the default path /lcrc/group/e3sm/diagnostics/observations/Atm/climatology
        "path_dc_obs_climo": "/lcrc/group/e3sm/public_html/e3sm_diags_test_data/unit_test_complete_run/obs/climatology",
        # This differs from the default path /lcrc/group/e3sm/diagnostics/observations/Atm/time-series
        "path_pcmdi_diags_obs_ts": "/lcrc/soft/climate/e3sm_diags_data/obs_for_e3sm_diags/time-series",
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
    diagnostics_base_path = config.get("diagnostics", "base_path")
    d = {
        "bundles_walltime": "02:00:00",
        "case_name": "v3.LR.historical_0051",
        "case_name_v2": "v2.LR.historical_0201",
        "constraint": "",
        "diags_walltime": "06:00:00",
        # Fallback for a machine with no promoted baseline yet. Once one
        # is promoted, _apply_run_locations replaces this with the
        # promoted run's settings directory.
        "expected_dir": "/compyfs/www/zppy_test_resources/",
        "livvkit_mapping_file_path": f"{diagnostics_base_path}/maps",
        "mpas_analysis_walltime": "02:00:00",
        "partition_long": "slurm",
        "partition_short": "short",
        "path_dc_obs_climo": f"{diagnostics_base_path}/observations/Atm/climatology/",
        "path_pcmdi_diags_obs_ts": f"{diagnostics_base_path}/observations/Atm/time-series/",
        "qos_long": "regular",
        "qos_short": "regular",
        "user_input_v2": "/compyfs/fors729/",
        "user_input_v3": "/compyfs/fors729/zppy_test_data",
        "user_output": f"/compyfs/{username}/",
        "user_www": f"{web_base_path}/{username}/",
    }
    return d


def get_perlmutter_expansions(config):
    username = config.get("web_portal", "username")
    web_base_path = config.get("web_portal", "base_path")
    diagnostics_base_path = config.get("diagnostics", "base_path")
    d = {
        "bundles_walltime": "6:00:00",
        "case_name": "v3.LR.historical_0051",
        "case_name_v2": "v2.LR.historical_0201",
        "constraint": "cpu",
        "diags_walltime": "6:00:00",
        # Fallback for a machine with no promoted baseline yet. Once one
        # is promoted, _apply_run_locations replaces this with the
        # promoted run's settings directory.
        "expected_dir": "/global/cfs/cdirs/e3sm/www/zppy_test_resources/",
        "livvkit_mapping_file_path": f"{diagnostics_base_path}/maps",
        "mpas_analysis_walltime": "03:00:00",
        "partition_long": "",
        "partition_short": "",
        "path_dc_obs_climo": f"{diagnostics_base_path}/observations/Atm/climatology/",
        "path_pcmdi_diags_obs_ts": f"{diagnostics_base_path}/observations/Atm/time-series/",
        "qos_long": "regular",
        "qos_short": "regular",  # debug walltime too short?
        # Use CFS for large datasets
        "user_input_v2": "/global/cfs/cdirs/e3sm/forsyth/",
        "user_input_v3": "/global/cfs/cdirs/e3sm/forsyth/",
        "user_output": f"/global/cfs/cdirs/e3sm/{username}/",
        "user_www": f"{web_base_path}/{username}/",
    }
    return d


# Written by generate_cfgs when it targets a complete-run directory, so the
# integration tests -- which call get_expansions() with no arguments -- check the
# run that was generated rather than TEST_SPECIFICS' defaults. It lives beside
# the generated cfgs, in the run's own throwaway worktree.
RUN_SETTINGS_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "generated",
    "complete_run_settings.json",
)


def _load_run_settings(path: str = RUN_SETTINGS_PATH) -> Dict[str, Any]:
    try:
        with open(path) as stream:
            loaded = json.load(stream)
    except (OSError, json.JSONDecodeError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _resolve_settings(
    specifics: Optional[Dict[str, Any]],
    run_dir: Optional[str],
    baseline_dir: Optional[str],
    output_dir: Optional[str],
    saved: Dict[str, Any],
):
    """Fill every argument left as None from the saved run settings."""
    if specifics is None:
        specifics = saved.get("specifics") or TEST_SPECIFICS
    if run_dir is None:
        run_dir = saved.get("run_dir")
    if baseline_dir is None:
        baseline_dir = saved.get("baseline_dir")
    if output_dir is None:
        output_dir = saved.get("output_dir")
    return specifics, run_dir, baseline_dir, output_dir


def get_expansions(
    specifics: Optional[Dict[str, Any]] = None,
    run_dir: Optional[str] = None,
    baseline_dir: Optional[str] = None,
    output_dir: Optional[str] = None,
):
    """Build the template expansions for this machine.

    Parameters
    ----------
    specifics : Optional[Dict[str, Any]]
        Test-run settings. Defaults to the module-level ``TEST_SPECIFICS``, so
        editing that dict by hand still works for one-off developer runs; the
        complete run test passes its own instead of rewriting this file.
    run_dir : Optional[str]
        The run directory this run writes into. When given, `user_output` and
        `user_www` point inside it rather than at a personal directory, so any
        maintainer can inspect and promote the result.
    baseline_dir : Optional[str]
        The promoted run to compare against. When given, the expected-results
        paths resolve inside it. Defaults to whatever `latest-main` points at.
    output_dir : Optional[str]
        Where `user_output` points, overriding the run directory's own
        ``output/``. The complete run test puts this intermediate data on
        scratch.

    Any argument left as None comes from the settings a complete run saved
    beside its generated cfgs, if there are any; otherwise from the defaults.
    """
    specifics, run_dir, baseline_dir, output_dir = _resolve_settings(
        specifics, run_dir, baseline_dir, output_dir, _load_run_settings()
    )
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

    _apply_run_locations(expansions, machine, run_dir, baseline_dir, output_dir)

    # Set up environments
    expansions["nco_path"] = specifics["nco_path"]
    expansions["e3sm_to_cmip_environment_commands"] = specifics[
        "e3sm_to_cmip_environment_commands"
    ]
    expansions["diags_environment_commands"] = specifics["diags_environment_commands"]
    expansions["mpas_analysis_environment_commands"] = specifics[
        "mpas_analysis_environment_commands"
    ]
    expansions["global_time_series_environment_commands"] = specifics[
        "global_time_series_environment_commands"
    ]
    expansions["livvkit_environment_commands"] = specifics[
        "livvkit_environment_commands"
    ]
    expansions["pcmdi_diags_environment_commands"] = specifics[
        "pcmdi_diags_environment_commands"
    ]
    expansions["environment_commands"] = specifics["environment_commands"]

    # Activate requested tests

    # Dependencies
    expansions["active_climo_month_atm"] = "False"  # For e3sm_diags
    expansions["active_climo_month_lnd"] = "False"  # For e3sm_diags
    expansions["active_climo_month_lnd_for_livvkit"] = "False"  # For livvkit
    expansions["active_climo_diurnal_atm"] = "False"  # For e3sm_diags

    expansions["active_ts_daily_atm"] = "False"  # For e3sm_diags
    expansions["active_ts_month_atm"] = "False"  # For e3sm_diags, ilamb, pcmdi_diags
    expansions["active_ts_month_atm_glb"] = "False"  # For global_time_series
    expansions["active_ts_month_lnd"] = "False"  # For ilamb
    expansions["active_ts_month_lnd_for_livvkit"] = "False"  # For livvkit
    expansions["active_ts_month_lnd_glb"] = "False"  # For global_time_series
    expansions["active_ts_month_rof"] = "False"  # For e3sm_diags

    expansions["active_e3sm_to_cmip_month_atm"] = "False"  # For ilamb, pcmdi_diags
    expansions["active_e3sm_to_cmip_month_lnd"] = "False"  # For ilamb

    expansions["active_tc_analysis"] = "False"  # For e3sm_diags

    # Plotting packages
    expansions["active_e3sm_diags"] = "False"
    expansions["active_mpas_analysis"] = "False"  # Also used for global_time_series
    expansions["active_global_time_series"] = "False"
    expansions["active_ilamb"] = "False"
    expansions["active_livvkit"] = "False"
    expansions["active_pcmdi_diags"] = "False"

    if "e3sm_diags" in specifics["tasks_to_run"]:
        expansions["active_e3sm_diags"] = "True"

        expansions["active_climo_month_atm"] = "True"
        expansions["active_climo_month_lnd"] = "True"
        expansions["active_climo_diurnal_atm"] = "True"

        expansions["active_ts_month_atm"] = "True"
        expansions["active_ts_month_rof"] = "True"
        expansions["active_ts_daily_atm"] = "True"

        expansions["active_tc_analysis"] = "True"

    if "mpas_analysis" in specifics["tasks_to_run"]:
        expansions["active_mpas_analysis"] = "True"

    if "global_time_series" in specifics["tasks_to_run"]:
        expansions["active_global_time_series"] = "True"

        expansions["active_ts_month_atm_glb"] = "True"
        expansions["active_ts_month_lnd_glb"] = "True"

        expansions["active_mpas_analysis"] = "True"

    if "ilamb" in specifics["tasks_to_run"]:
        expansions["active_ilamb"] = "True"

        expansions["active_ts_month_atm"] = "True"
        expansions["active_ts_month_lnd"] = "True"

        expansions["active_e3sm_to_cmip_month_atm"] = "True"
        expansions["active_e3sm_to_cmip_month_lnd"] = "True"

    if "livvkit" in specifics["tasks_to_run"]:
        expansions["active_livvkit"] = "True"

        expansions["active_climo_month_lnd_for_livvkit"] = "True"

        expansions["active_ts_month_lnd_for_livvkit"] = "True"

    if "pcmdi_diags" in specifics["tasks_to_run"]:
        expansions["active_pcmdi_diags"] = "True"

        expansions["active_ts_month_atm"] = "True"

        expansions["active_e3sm_to_cmip_month_atm"] = "True"

    expansions["cfgs_to_run"] = specifics["cfgs_to_run"]
    expansions["tasks_to_run"] = specifics["tasks_to_run"]

    expansions["diagnostics_base_path"] = config.get("diagnostics", "base_path")
    expansions["machine"] = machine
    expansions["unique_id"] = specifics["unique_id"]
    return expansions


def _apply_run_locations(
    expansions, machine, run_dir=None, baseline_dir=None, output_dir=None
):
    """Point the run and baseline paths at shared run directories.

    A complete run writes into its own directory under a shared root, and
    compares against whichever run is currently promoted. Both are resolved
    lazily so that importing this module never requires the shared root to
    exist -- a developer generating one cfg by hand does not need it.
    """
    from tests.complete_run import layout

    if run_dir:
        expansions["run_dir"] = run_dir
        expansions["user_output"] = f"{layout.RunLayout(run_dir).output}/"
        expansions["user_www"] = f"{layout.RunLayout(run_dir).www}/"
    if output_dir:
        expansions["user_output"] = f"{output_dir.rstrip('/')}/"

    resolved_baseline = baseline_dir
    if resolved_baseline is None:
        try:
            resolved_baseline = layout.resolve_baseline(
                layout.shared_root(machine)
            ).root
        except (FileNotFoundError, ValueError):
            # No baseline promoted yet, or no shared root on this machine. The
            # legacy expected_dir stays in place so existing tests still run.
            resolved_baseline = ""

    if resolved_baseline:
        baseline = layout.RunLayout(resolved_baseline)
        expansions["baseline_dir"] = resolved_baseline
        expansions["baseline_www"] = f"{baseline.www}/"
        expansions["baseline_image_lists"] = f"{baseline.image_lists}/"
        # `expected_dir` keeps its meaning -- the directory holding the small
        # settings and bash baselines -- so its consumers need no changes.
        expansions["expected_dir"] = f"{baseline.settings}/"
    else:
        expansions["baseline_dir"] = ""
        expansions["baseline_www"] = ""
        expansions["baseline_image_lists"] = ""


def _save_run_settings(path: str, settings: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as stream:
        json.dump(settings, stream, indent=2, sort_keys=True)
        stream.write("\n")


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


def generate_cfgs(
    dry_run=False,
    specifics: Optional[Dict[str, Any]] = None,
    run_dir: Optional[str] = None,
    baseline_dir: Optional[str] = None,
    output_dir: Optional[str] = None,
):
    if specifics is None:
        specifics = TEST_SPECIFICS
    git_top_level = (
        subprocess.check_output("git rev-parse --show-toplevel".split())
        .strip()
        .decode("utf-8")
    )
    expansions = get_expansions(
        specifics, run_dir=run_dir, baseline_dir=baseline_dir, output_dir=output_dir
    )
    machine = expansions["machine"]
    if run_dir:
        _save_run_settings(
            f"{git_top_level}/tests/integration/generated/complete_run_settings.json",
            {
                "specifics": specifics,
                "run_dir": run_dir,
                # "" (no baseline) must survive the round trip; None would
                # mean "resolve latest-main" when the tests run.
                "baseline_dir": expansions["baseline_dir"],
                "output_dir": output_dir or "",
            },
        )

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
        *(cfg.name for cfg in WEEKLY_CFGS),
    ]
    if specifics["cfgs_to_run"] == []:
        cfg_names = full_list_cfg_names
    else:
        cfg_names = specifics["cfgs_to_run"]
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

    # The update_*_expected_files scripts are gone: baselines are no longer
    # produced by copying a run's output over the previous baseline. A run is
    # its own baseline material, and `python -m tests.complete_run.promote`
    # points latest-main at it.
    print("CFG FILES HAVE BEEN GENERATED FROM TEMPLATES WITH THESE SETTINGS:")
    print(f"UNIQUE_ID={specifics['unique_id']}")
    print(f"nco_path={expansions['nco_path']}")
    print("Reminder: `nco_path=''` => the production-version NCO commands will be used")
    print(
        f"e3sm_to_cmip_environment_commands={expansions['e3sm_to_cmip_environment_commands']}"
    )
    print(f"diags_environment_commands={expansions['diags_environment_commands']}")
    print(
        f"mpas_analysis_environment_commands={expansions['mpas_analysis_environment_commands']}"
    )
    print(
        f"global_time_series_environment_commands={expansions['global_time_series_environment_commands']}"
    )
    print(f"livvkit_environment_commands={expansions['livvkit_environment_commands']}")
    print(
        f"pcmdi_diags_environment_commands={expansions['pcmdi_diags_environment_commands']}"
    )
    print(f"environment_commands={expansions['environment_commands']}")
    print(
        "Reminder: `environment_commands=''` => the latest E3SM Unified environment will be used"
    )


# Command-line interface ######################################################
# The complete run test drives cfg generation through these flags rather than
# rewriting TEST_SPECIFICS in place, so this file is never modified by a run.

# zppy task name -> the TEST_SPECIFICS key holding its environment_commands.
TASK_ENV_KEYS: Dict[str, str] = {
    "e3sm_to_cmip": "e3sm_to_cmip_environment_commands",
    "e3sm_diags": "diags_environment_commands",
    "mpas_analysis": "mpas_analysis_environment_commands",
    "global_time_series": "global_time_series_environment_commands",
    "livvkit": "livvkit_environment_commands",
    "pcmdi_diags": "pcmdi_diags_environment_commands",
}


def build_specifics(
    unique_id: Optional[str] = None,
    cfgs_to_run: Optional[List[str]] = None,
    tasks_to_run: Optional[List[str]] = None,
    env_commands: Optional[Dict[str, str]] = None,
    nco_path: Optional[str] = None,
    environment_commands: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a TEST_SPECIFICS mapping from explicit values.

    Anything left as None keeps the module-level default, so a caller can
    override one field without restating the rest.
    """
    specifics: Dict[str, Any] = dict(TEST_SPECIFICS)
    if unique_id is not None:
        specifics["unique_id"] = unique_id
    if cfgs_to_run is not None:
        specifics["cfgs_to_run"] = list(cfgs_to_run)
    if tasks_to_run is not None:
        specifics["tasks_to_run"] = list(tasks_to_run)
    if nco_path is not None:
        specifics["nco_path"] = nco_path
    if environment_commands is not None:
        specifics["environment_commands"] = environment_commands

    for task, command in (env_commands or {}).items():
        try:
            key = TASK_ENV_KEYS[task]
        except KeyError:
            raise ValueError(
                f"Unknown task {task!r}; expected one of "
                f"{', '.join(sorted(TASK_ENV_KEYS))}"
            ) from None
        if not command:
            # An empty string would print `environment_commands = ""` into the
            # cfg, overriding the value set higher up and leaving the task with
            # no environment at all.
            raise ValueError(
                f"Environment commands for {task!r} may not be empty; pass the "
                "activation command, or omit the task to keep the default."
            )
        specifics[key] = command

    return specifics


def _parse_key_value(text: str) -> tuple:
    name, separator, value = text.partition("=")
    if not separator:
        raise argparse.ArgumentTypeError(f"Expected task=command, got {text!r}")
    return name.strip(), value.strip()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Generate machine-specific zppy test cfgs from templates.",
    )
    parser.add_argument("--unique-id", default=None, help="Keeps runs from colliding.")
    parser.add_argument(
        "--cfg",
        dest="cfgs",
        action="append",
        help="A cfg to generate; repeatable. Omit for the TEST_SPECIFICS list.",
    )
    parser.add_argument(
        "--task", dest="tasks", action="append", help="A task to enable; repeatable."
    )
    parser.add_argument(
        "--env-cmd",
        dest="env_cmds",
        action="append",
        type=_parse_key_value,
        metavar="TASK=COMMAND",
        help="environment_commands for one task; repeatable.",
    )
    parser.add_argument("--nco-path", default=None)
    parser.add_argument(
        "--run-dir",
        default=None,
        help="Run directory to write output into, instead of a personal one.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Where zppy's post-processing output goes; overrides --run-dir's.",
    )
    parser.add_argument(
        "--baseline-dir",
        default=None,
        help="Promoted run to compare against. Defaults to latest-main.",
    )
    parser.add_argument(
        "--environment-commands",
        default=None,
        help="Default environment for tasks without one of their own.",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Generate cfgs from command-line settings."""
    args = _build_parser().parse_args(argv)
    specifics = build_specifics(
        unique_id=args.unique_id,
        cfgs_to_run=args.cfgs,
        tasks_to_run=args.tasks,
        env_commands=dict(args.env_cmds or []),
        nco_path=args.nco_path,
        environment_commands=args.environment_commands,
    )
    generate_cfgs(
        dry_run=args.dry_run,
        specifics=specifics,
        run_dir=args.run_dir,
        baseline_dir=args.baseline_dir,
        output_dir=args.output_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
