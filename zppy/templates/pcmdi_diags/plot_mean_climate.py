#!/bin/env python
##############################################################################
# This model is used to generate mean climate diagnostic figures
# Author: Shixuan Zhang (shixuan.zhang@pnnl.gov)
#############################################################################
import os

from mean_climate_plot_driver import mean_climate_metrics_plot
from mean_climate_plot_parser import create_mean_climate_plot_parser


def main(
    run_type,
    test_data_set,
    test_data_dir,
    test_period,
    refr_data_set,
    refr_data_dir,
    refr_period,
    cmip_data_set,
    pcmdi_data_dir,
    results_dir,
):
    parser = create_mean_climate_plot_parser()
    parameter = parser.get_parameter(argparse_vals_only=False)

    parameter.pcmdi_data_set = cmip_data_set
    parameter.pcmdi_data_path = pcmdi_data_dir

    parameter.period = test_period
    parameter.test_product = test_data_set.split(".")[2]
    parameter.test_data_set = test_data_set
    parameter.test_data_path = os.path.join(test_data_dir, "mean_climate")
    parameter.run_type = run_type

    if parameter.run_type == "model_vs_model":
        parameter.refr_data_set = refr_data_set
        parameter.refr_period = refr_period
        parameter.refr_data_path = os.path.join(refr_data_dir, "mean_climate")

    parameter.output_path = os.path.join(results_dir, "graphics", "mean_climate")
    parameter.ftype = "png"
    parameter.debug = False
    parameter.regions = ["global", "NHEX", "SHEX", "TROPICS"]
    parameter.parcord_show_markers = False
    parameter.add_vertical_line = True

    mean_climate_metrics_plot(parameter)


if __name__ == "__main__":
    cmip_data_set = "cmip6.amip.v20241029"
    pcmdi_data_dir = (
        "/lcrc/soft/climate/e3sm_diags_data/obs_for_e3sm_diags/pcmdi_data/mean_climate"
    )
    results_dir = "/lcrc/group/e3sm/public_html/diagnostic_output/ac.szhang/e3sm-pcmdi/merged_data/model_vs_obs_1985-2014"
    run_type = "model_vs_obs"

    test_data_set = "e3sm.amip.v3-LR.all.v20241030"
    test_data_dir = "/lcrc/group/e3sm/public_html/diagnostic_output/ac.szhang/e3sm-pcmdi/merged_data/model_vs_obs_1985-2014"
    test_period = "1985-2014"

    if run_type == "model_vs_obs":
        refr_data_set = ""
        refr_data_dir = ""
        refr_period = ""
    else:
        print("need to provide reference data information ...")
        refr_data_set = "e3sm.historical.v3-LR.all.v20241030"
        refr_data_dir = "/lcrc/group/e3sm/public_html/diagnostic_output/ac.szhang/e3sm-pcmdi/merged_data/model_vs_obs_1985-2014"
        refr_period = "1985-2014"

    main(
        run_type,
        test_data_set,
        test_data_dir,
        test_period,
        refr_data_set,
        refr_data_dir,
        refr_period,
        cmip_data_set,
        pcmdi_data_dir,
        results_dir,
    )
