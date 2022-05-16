import argparse
import errno
import os
from typing import List

from configobj import ConfigObj
from mache import MachineInfo
from validate import Validator

from zppy.amwg import amwg
from zppy.bundle import Bundle, predefined_bundles
from zppy.climo import climo
from zppy.e3sm_diags import e3sm_diags
from zppy.global_time_series import global_time_series
from zppy.ilamb_run import ilamb_run
from zppy.mpas_analysis import mpas_analysis
from zppy.tc_analysis import tc_analysis
from zppy.ts import ts
from zppy.utils import checkStatus, submitScript


# FIXME: C901 'main' is too complex (19)
def main():  # noqa: C901

    # Command line parser
    parser = argparse.ArgumentParser(
        description="Launch E3SM post-processing tasks", usage="zppy -c <config>"
    )
    parser.add_argument(
        "-c", "--config", type=str, help="configuration file", required=True
    )
    parser.add_argument(
        "-l", "--last-year", type=int, help="last year to process", required=False
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
    username = os.environ.get("USER")
    output = output.replace("$USER", username)
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
        machine_info = MachineInfo()
        unified_base = machine_info.config.get("e3sm_unified", "base_path")
        if tmp.startswith("compy"):
            machine = "compy"
            environment_commands = (
                f"source {unified_base}/load_latest_e3sm_unified_compy.sh"
            )
            account = "e3sm"
        elif tmp.startswith("cori"):
            machine = "cori"
            partition = config["default"]["partition"]
            if partition not in ["haswell", "knl"]:
                raise ValueError(
                    f'Expected Cori parition to be "haswell" or '
                    f'"knl" but got: {partition}'
                )
            environment_commands = (
                f"source {unified_base}/load_latest_e3sm_unified_cori-{partition}.sh"
            )
            account = "e3sm"
        elif tmp.startswith("blues"):
            machine = "anvil"
            environment_commands = (
                f"source {unified_base}/load_latest_e3sm_unified_anvil.sh"
            )
            account = "condo"
        elif tmp.startswith("chr"):
            machine = "chrysalis"
            environment_commands = (
                f"source {unified_base}/load_latest_e3sm_unified_chrysalis.sh"
            )
            account = "e3sm"
    config["default"]["machine"] = machine
    if config["default"]["environment_commands"] == "":
        config["default"]["environment_commands"] = environment_commands
    if config["default"]["account"] == "":
        config["default"]["account"] = account

    if args.last_year:
        config["default"]["last_year"] = args.last_year

    existing_bundles: List[Bundle] = []

    # predefined bundles
    existing_bundles = predefined_bundles(config, scriptDir, existing_bundles)

    # climo tasks
    existing_bundles = climo(config, scriptDir, existing_bundles)

    # time series tasks
    existing_bundles = ts(config, scriptDir, existing_bundles)

    # tc_analysis tasks
    existing_bundles = tc_analysis(config, scriptDir, existing_bundles)

    # e3sm_diags tasks
    existing_bundles = e3sm_diags(config, scriptDir, existing_bundles)

    # amwg tasks
    existing_bundles = amwg(config, scriptDir, existing_bundles)

    # mpas_analysis tasks
    existing_bundles = mpas_analysis(config, scriptDir, existing_bundles)

    # global time series tasks
    existing_bundles = global_time_series(config, scriptDir, existing_bundles)

    # ilamb_run tasks
    existing_bundles = ilamb_run(config, scriptDir, existing_bundles)

    # Submit bundle jobs
    for b in existing_bundles:
        skip = checkStatus(b.bundle_status)
        if skip:
            continue
        b.display_dependencies()
        b.render(config)
        if not b.dry_run:
            submitScript(
                b.bundle_file,
                b.bundle_status,
                b.export,
                dependFiles=b.dependencies_external,
            )


def _validate_config(config):
    validator = Validator()

    result = config.validate(validator)
    if result is not True:
        print("Validation results={}".format(result))
        raise Exception("Configuration file validation failed")
    else:
        print("Configuration file validation passed")
