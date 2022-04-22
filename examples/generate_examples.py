import re
import subprocess

# Script to generate standard example configurations for different machines.
# Inspired by https://github.com/E3SM-Project/e3sm_diags/blob/master/docs/source/quickguides/generate_quick_guides.py

EXPANSIONS = {
    "compy": {
        # [default]
        "environment_commands": "source /share/apps/E3SM/conda_envs/load_latest_e3sm_unified_compy.sh",
        "input": "/compyfs/fors729/e3sm_unified_test_zppy/20210528.v2rc3e.piControl.ne30pg2_EC30to60E2r2.chrysalis",
        "mapping_file": "/compyfs/zender/maps/map_ne30pg2_to_cmip6_180x360_aave.20200201.nc",
        "output": "/qfs/people/fors729/zppy_complete_run_compy_output/20210528.v2rc3e.piControl.ne30pg2_EC30to60E2r2.chrysalis",
        "partition": "short",
        "www": "/compyfs/www/fors729/zppy_complete_run_compy_output",
        # [tc_analysis]
        "scratch": "/qfs/people/fors729",
        # [e3sm_diags]
        "obs_ts": "/compyfs/e3sm_diags_data/obs_for_e3sm_diags/time-series",
        "reference_data_path": "/compyfs/e3sm_diags_data/obs_for_e3sm_diags/climatology",
        # [e3sm_diags] > [[ atm_monthly_180x360_aave ]]
        "dc_obs_climo": "/compyfs/e3sm_diags_data/obs_for_e3sm_diags/climatology",
        "streamflow_obs_ts": "/compyfs/e3sm_diags_data/obs_for_e3sm_diags/time-series",
        # [e3sm_diags] > [[ atm_monthly_180x360_aave_tc_analysis ]]
        "tc_obs": "/compyfs/e3sm_diags_data/obs_for_e3sm_diags/tc-analysis",
        # [e3sm_diags] > [[ atm_monthly_180x360_aave_mvm ]]
        "gauges_path": "/compyfs/e3sm_diags_data/obs_for_e3sm_diags/time-series/GSIM/GSIM_catchment_characteristics_all_1km2.csv",
        "ref_name": "20210528.v2rc3e.piControl.ne30pg2_EC30to60E2r2.chrysalis",
        "reference_data_path_mvm": "/qfs/people/fors729/zppy_complete_run_compy_output/20210528.v2rc3e.piControl.ne30pg2_EC30to60E2r2.chrysalis/post/atm/180x360_aave/clim",
        "reference_data_path_climo_diurnal": "/qfs/people/fors729/zppy_complete_run_compy_output/20210528.v2rc3e.piControl.ne30pg2_EC30to60E2r2.chrysalis/post/atm/180x360_aave/clim_diurnal_8xdaily",
        "reference_data_path_tc": "/qfs/people/fors729/zppy_complete_run_compy_output/20210528.v2rc3e.piControl.ne30pg2_EC30to60E2r2.chrysalis/post/atm/tc-analysis_51_52",
        "reference_data_path_ts": "/qfs/people/fors729/zppy_complete_run_compy_output/20210528.v2rc3e.piControl.ne30pg2_EC30to60E2r2.chrysalis/post/atm/180x360_aave/ts/monthly",
        "reference_data_path_ts_rof": "/qfs/people/fors729/zppy_complete_run_compy_output/20210528.v2rc3e.piControl.ne30pg2_EC30to60E2r2.chrysalis/post/rof/native/ts/monthly",
        # [mpas_analysis]
        "partition_mpas": "slurm",
    }
}


# Important: Do not have more than one `#expand` operation per line. The code will only expand the first one.
def generate_cfgs():
    machine_names = EXPANSIONS.keys()
    git_top_level = (
        subprocess.check_output("git rev-parse --show-toplevel".split())
        .strip()
        .decode("utf-8")
    )
    cfg_dir = f"{git_top_level}/examples/"
    generic_cfg = f"{cfg_dir}example_generic.cfg"
    specific_cfgs = {}
    specific_cfg_files = {}
    for machine_name in machine_names:
        cfg_name = f"{cfg_dir}example_{machine_name}.cfg"
        specific_cfgs[machine_name] = cfg_name
        specific_cfg_files[machine_name] = open(cfg_name, "w")
    with open(generic_cfg, "r") as file_read:
        # For line in file, if line matches #expand <expansion_name>#, then replace text with <expansion>.
        # Send output to the corresponding specific cfg file.
        for line in file_read:
            match_object = re.search("#expand ([^#]*)#", line)
            for machine_name in machine_names:
                if match_object is None:
                    new_line = line
                else:
                    expansion_indicator = match_object.group(0)
                    expansion_name = match_object.group(1)
                    expansion = EXPANSIONS[machine_name][expansion_name]
                    new_line = line.replace(expansion_indicator, expansion)
                specific_cfg_files[machine_name].write(new_line)
    for machine_name in machine_names:
        specific_cfg_files[machine_name].close()


if __name__ == "__main__":
    generate_cfgs()
