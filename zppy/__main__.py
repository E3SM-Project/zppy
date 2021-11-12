import argparse
import errno
import os

from configobj import ConfigObj
from validate import Validator

from zppy.amwg import amwg
from zppy.climo import climo
from zppy.e3sm_diags import e3sm_diags
from zppy.e3sm_diags_vs_model import e3sm_diags_vs_model
from zppy.global_time_series import global_time_series
from zppy.mpas_analysis import mpas_analysis
from zppy.postprocess_tc import postprocess_tc
from zppy.ts import ts


def main():

    # Command line parser
    parser = argparse.ArgumentParser(
        description="Launch E3SM post-processing tasks", usage="zppy -c <config>"
    )
    parser.add_argument(
        "-c", "--config", type=str, help="configuration file", required=True
    )
    args = parser.parse_args()

    # Subdirectory where templates are located
    templateDir = os.path.join(os.path.dirname(__file__), "templates")

    # Read configuration file and validate it
    default_config = os.path.join(templateDir, "default.ini")
    user_config = ConfigObj(args.config, configspec=default_config)
    if "campaign" in user_config["default"]:
        campaign = user_config["default"]["campaign"]
    else:
        campaign = "none"
    if campaign != "none":
        campaign_file = os.path.join(templateDir, "{}.cfg".format(campaign))
        if not os.path.exists(campaign_file):
            raise ValueError(
                "{} does not appear to be a known campaign".format(campaign)
            )
        campaign_config = ConfigObj(campaign_file, configspec=default_config)
        # merge such that user_config takes priority over campaign_config
        campaign_config.merge(user_config)
        config = campaign_config
    else:
        config = user_config
    _validate_config(config)

    # Add templateDir to config
    config["default"]["templateDir"] = templateDir

    # Output script directory
    output = config["default"]["output"]
    scriptDir = os.path.join(output, "post/scripts")
    try:
        os.makedirs(scriptDir)
    except OSError as exc:
        if exc.errno != errno.EEXIST:
            print("Cannot create script directory")
            raise Exception
        pass

    # Determine machine to decide which header files to use
    tmp = os.getenv("HOSTNAME")
    if tmp:
        if tmp.startswith("compy"):
            machine = "compy"
            environment_commands = "source /share/apps/E3SM/conda_envs/load_{}_e3sm_unified_compy.sh".format(
                config["default"]["e3sm_unified"]
            )
        elif tmp.startswith("cori"):
            machine = "cori"
            environment_commands = "source /global/cfs/cdirs/e3sm/software/anaconda_envs/load_{}_e3sm_unified_cori-haswell.sh".format(
                config["default"]["e3sm_unified"]
            )
        elif tmp.startswith("blues"):
            machine = "anvil"
            environment_commands = "source /lcrc/soft/climate/e3sm-unified/load_{}_e3sm_unified_anvil.sh".format(
                config["default"]["e3sm_unified"]
            )
        elif tmp.startswith("chr"):
            machine = "chrysalis"
            environment_commands = "source /lcrc/soft/climate/e3sm-unified/load_{}_e3sm_unified_chrysalis.sh".format(
                config["default"]["e3sm_unified"]
            )
    config["default"]["machine"] = machine
    if "environment_commands" not in config["default"].keys():
        config["default"]["environment_commands"] = environment_commands

    # climo tasks
    climo(config, scriptDir)

    # time series tasks
    ts(config, scriptDir)

    # postprocess_tc tasks
    postprocess_tc(config, scriptDir)

    # e3sm_diags tasks
    e3sm_diags(config, scriptDir)

    # e3sm_diags_vs_model tasks
    e3sm_diags_vs_model(config, scriptDir)

    # amwg tasks
    amwg(config, scriptDir)

    # mpas_analysis tasks
    mpas_analysis(config, scriptDir)

    # global time series tasks
    global_time_series(config, scriptDir)


def _validate_config(config):
    validator = Validator()

    result = config.validate(validator)
    if result is not True:
        print("Validation results={}".format(result))
        raise Exception("Configuration file validation failed")
    else:
        print("Configuration file validation passed")
