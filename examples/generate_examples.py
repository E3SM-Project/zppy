import re
import subprocess

from mache import MachineInfo

# Script to generate standard example configurations for different machines.
# Inspired by https://github.com/E3SM-Project/e3sm_diags/blob/master/docs/source/quickguides/generate_quick_guides.py


def get_expansions():
    machine_info = MachineInfo()
    config = machine_info.config
    machine = machine_info.machine
    if machine == "compy":
        expansions = get_compy_expansions(config)
    else:
        raise ValueError(f"Unsupported machine={machine}")
    return expansions


def get_compy_expansions(config):
    diags_base_path = config.get("diagnostics", "base_path")
    web_base_path = config.get("web_portal", "base_path")
    # Note: `os.environ.get("USER")` also works. Here we're already using mache but not os, so using mache.
    username = config.get("web_portal", "username")
    d = {
        # [default]
        "environment_commands": "source /share/apps/E3SM/conda_envs/load_latest_e3sm_unified_compy.sh",
        # `input` data is only in this directory, so not using `username`
        "input": "/compyfs/fors729/e3sm_unified_test_zppy/20210528.v2rc3e.piControl.ne30pg2_EC30to60E2r2.chrysalis",
        "mapping_file": "/compyfs/zender/maps/map_ne30pg2_to_cmip6_180x360_aave.20200201.nc",
        "output": f"/qfs/people/{username}/zppy_complete_run_compy_output/20210528.v2rc3e.piControl.ne30pg2_EC30to60E2r2.chrysalis",
        "partition": "short",
        "www": f"{web_base_path}/{username}/zppy_complete_run_compy_output",
        # [tc_analysis]
        "scratch": f"/qfs/people/{username}",
        # [e3sm_diags]
        "obs_ts": f"{diags_base_path}/observations/Atm/time-series",
        "reference_data_path": f"{diags_base_path}/observations/Atm/climatology",
        # [e3sm_diags] > [[ atm_monthly_180x360_aave_tc_analysis ]]
        "tc_obs": "/compyfs/e3sm_diags_data/obs_for_e3sm_diags/tc-analysis",
        # [e3sm_diags] > [[ atm_monthly_180x360_aave_mvm ]]
        "ref_name": "20210528.v2rc3e.piControl.ne30pg2_EC30to60E2r2.chrysalis",
        "reference_data_path_mvm": "/qfs/people/fors729/zppy_complete_run_compy_output/20210528.v2rc3e.piControl.ne30pg2_EC30to60E2r2.chrysalis/post/atm/180x360_aave/clim",
        # [mpas_analysis]
        "partition_mpas": "slurm",
    }
    return d


# Important: Do not have more than one `#expand` operation per line. The code will only expand the first one.
def generate_cfg():
    git_top_level = (
        subprocess.check_output("git rev-parse --show-toplevel".split())
        .strip()
        .decode("utf-8")
    )
    cfg_dir = f"{git_top_level}/examples/"
    generic_cfg = f"{cfg_dir}example_generic.cfg"
    machine = MachineInfo().machine
    cfg_name = f"{cfg_dir}example_{machine}.cfg"
    expansions = get_expansions()
    with open(generic_cfg, "r") as file_read:
        with open(cfg_name, "w") as file_write:
            # For line in file, if line matches #expand <expansion_name>#, then replace text with <expansion>.
            # Send output to the corresponding specific cfg file.
            for line in file_read:
                match_object = re.search("#expand ([^#]*)#", line)
                if match_object is None:
                    new_line = line
                else:
                    expansion_indicator = match_object.group(0)
                    expansion_name = match_object.group(1)
                    expansion = expansions[expansion_name]
                    new_line = line.replace(expansion_indicator, expansion)
                file_write.write(new_line)


if __name__ == "__main__":
    generate_cfg()
