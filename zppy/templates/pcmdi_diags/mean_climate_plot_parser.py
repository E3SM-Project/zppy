#!/usr/bin/env python
import ast
import glob
import os

import numpy as np
import pandas as pd
from pcmdi_metrics.mean_climate.lib import pmp_parser


def create_mean_climate_plot_parser():
    parser = pmp_parser.PMPMetricsParser()
    parser.add_argument(
        "--test_model",
        dest="test_model",
        help="Defines target model for the metrics plots",
        required=False,
    )

    parser.add_argument(
        "--test_data_set",
        type=str,
        nargs="+",
        dest="test_data_set",
        help="List of observations or models to test "
        + "against the reference_data_set",
        required=False,
    )

    parser.add_argument(
        "--test_data_path",
        dest="test_data_path",
        help="Path for the test climitologies",
        required=False,
    )

    parser.add_argument(
        "--period", dest="period", help="A simulation parameter", required=False
    )

    parser.add_argument(
        "--run_type", dest="run_type", help="A post-process parameter", required=False
    )

    parser.add_argument(
        "--regions",
        type=ast.literal_eval,
        dest="regions",
        help="Regions on which to run the metrics",
        required=False,
    )

    parser.add_argument(
        "--pcmdi_data_set",
        type=str,
        nargs="+",
        dest="pcmdi_data_set",
        help="PCMDI CMIP dataset that is used as a "
        + "CMIP multi-model ensembles against the test_data_set",
        required=False,
    )

    parser.add_argument(
        "--pcmdi_data_path",
        dest="pcmdi_data_path",
        help="Path for the PCMDI CMIP mean climate metrics data",
        required=False,
    )

    parser.add_argument(
        "--refr_model",
        dest="refr_model",
        help="A simulation parameter",
        required=False,
    )

    parser.add_argument(
        "--refr_data_set",
        type=str,
        nargs="+",
        dest="refr_data_set",
        help="List of reference models to test " + "against the reference_data_set",
        required=False,
    )

    parser.add_argument(
        "--refr_data_path",
        dest="refr_data_path",
        help="Path for the reference model climitologies",
        required=False,
    )

    parser.add_argument(
        "--output_path",
        dest="output_path",
        help="Path for the metrics plots",
        required=False,
    )

    parser.add_argument(
        "--parcord_show_markers",
        dest="parcord_show_markers",
        help="show markers for individual model in parallel coordinate plots",
        required=False,
    )
    parser.add_argument(
        "--add_vertical_line",
        dest="add_vertical_line",
        help="draw a vertical line to separate test and reference models for portrait plots",
        required=False,
    )
    return parser


def metrics_inquire(name):
    # list of metrics name and long-name
    metrics = {
        "std-obs_xy": "Spatial Standard Deviation (Reference)",
        "std_xy": "Spatial Standard Deviation (Model)",
        "std-obs_xyt": "Spatial-temporal Standard Deviation (Reference)",
        "std_xyt": "Spatial-temporal Standard Deviation (Model)",
        "std-obs_xy_devzm": "Standard Deviation of Deviation from Zonal Mean (Reference)",
        "mean_xy": "Area Weighted Spatial Mean (Model)",
        "mean-obs_xy": "Area Weighted Spatial Mean (Reference)",
        "std_xy_devzm": "Standard Deviation of Deviation from Zonal Mean (Model)",
        "rms_xyt": "Spatio-Temporal Root Mean Square Error",
        "rms_xy": "Spatial Root Mean Square Error",
        "rmsc_xy": "Centered Spatial Root Mean Square Error",
        "cor_xy": "Spatial Pattern Correlation Coefficient",
        "bias_xy": "Mean Bias (Model - Reference)",
        "mae_xy": "Mean Absolute Difference (Model - Reference)",
        "rms_y": "Root Mean Square Error of Zonal Mean",
        "rms_devzm": "Root Mean Square Error of Deviation From Zonal Mean",
    }
    if name in metrics.keys():
        long_name = metrics[name]

    return long_name


def find_latest(pmprdir, mip, exp):
    versions = sorted(
        [
            r.split("/")[-1]
            for r in glob.glob(os.path.join(pmprdir, mip, exp, "v????????"))
        ]
    )
    latest_version = versions[-1]
    return latest_version


def shift_row_to_bottom(df, index_to_shift):
    idx = [i for i in df.index if i != index_to_shift]
    return df.loc[idx + [index_to_shift]]


def find_cmip_metric_data(pmprdir, data_set, var):
    # cmip data for comparison
    mip = data_set.split(".")[0]
    exp = data_set.split(".")[1]
    case_id = data_set.split(".")[2]
    if case_id == "":
        case_id = find_latest(pmprdir, mip, exp)
    fpath = glob.glob(os.path.join(pmprdir, mip, exp, case_id, "{}.*.json".format(var)))
    if len(fpath) < 1 and var == "rtmt":
        fpath = glob.glob(
            os.path.join(pmprdir, mip, exp, case_id, "{}.*.json".format("rt"))
        )
    if len(fpath) > 0 and os.path.exists(fpath[0]):
        cmip_list = fpath[0]
        return_code = 0
    else:
        print("Warning: cmip metrics data not found for {}....".format(var))
        print("Warning: remove {} from the metric list....".format(var))
        cmip_list = None
        return_code = -99
    return cmip_list, return_code


def select_models(df, selected_models):
    # Selected models only
    model_names = df["model"].tolist()
    for model_name in model_names:
        drop_model = True
        for keyword in selected_models:
            if keyword in model_name:
                drop_model = False
                break
        if drop_model:
            df.drop(df.loc[df["model"] == model_name].index, inplace=True)
        df.reset_index(drop=True, inplace=True)

    return df


def exclude_models(df, excluded_models):
    # eclude models
    model_names = df["model"].tolist()
    for model_name in model_names:
        drop_model = False
        for keyword in excluded_models:
            if keyword in model_name:
                drop_model = True
                break
        if drop_model:
            df.drop(df.loc[df["model"] == model_name].index, inplace=True)
        df.reset_index(drop=True, inplace=True)
    return df


def fill_plot_var_and_units(model_lib, cmip_lib):
    # we define fixed sets of variables used for final plotting.
    units_all = {
        "prw": "[kg m$^{-2}$]",
        "pr": "[mm d$^{-1}$]",
        "prsn": "[mm d$^{-1}$]",
        "prc": "[mm d$^{-1}$]",
        "hfls": "[W m$^{-2}$]",
        "hfss": "[W m$^{-2}$]",
        "clivi": "[kg $m^{-2}$]",
        "clwvi": "[kg $m^{-2}$]",
        "psl": "[Pa]",
        "evspsbl": "[kg m$^{-2} s^{-1}$]",
        "rlds": "[W m$^{-2}$]",
        "rldscs": "[W $m^{-2}$]",
        "rtmt": "[W m$^{-2}$]",
        "rsdt": "[W m$^{-2}$]",
        "rlus": "[W m$^{-2}$]",
        "rluscs": "[W m$^{-2}$]",
        "rlut": "[W m$^{-2}$]",
        "rlutcs": "[W m$^{-2}$]",
        "rsds": "[W m$^{-2}$]",
        "rsdscs": "[W m$^{-2}$]",
        "rstcre": "[W m$^{-2}$]",
        "rltcre": "[W m$^{-2}$]",
        "rsus": "[W m$^{-2}$]",
        "rsuscs": "[W m$^{-2}$]",
        "rsut": "[W m$^{-2}$]",
        "rsutcs": "[W m$^{-2}$]",
        "ts": "[K]",
        "tas": "[K]",
        "tauu": "[Pa]",
        "tauv": "[Pa]",
        "sfcWind": "[m s$^{-1}$]",
        "zg-500": "[m]",
        "ta-200": "[K]",
        "ta-850": "[K]",
        "ua-200": "[m s$^{-1}$]",
        "ua-850": "[m s$^{-1}$]",
        "va-200": "[m s$^{-1}$]",
        "va-850": "[m s$^{-1}$]",
        "uas": "[m s$^{-1}$]",
        "vas": "[m s$^{-1}$]",
        "tasmin": "[K]",
        "tasmax": "[K]",
        "clt": "[%]",
    }

    # loop variable list and find them in cmip and target models
    variable_units = []
    variable_names = []
    for var in units_all.keys():
        # reorgnize cmip data
        if var == "rtmt":
            if ("rt" in cmip_lib.var_list) and ("rtmt" in model_lib.var_list):
                # special case (rt is used in pcmdi datasets, but rtmt is for cmip)
                cmip_lib.var_list = list(
                    map(lambda x: x.replace("rt", "rtmt"), cmip_lib.var_list)
                )
                for stat in cmip_lib.df_dict:
                    for season in cmip_lib.df_dict[stat]:
                        for region in cmip_lib.df_dict[stat][season]:
                            cmip_lib.df_dict[stat][season][region]["rtmt"] = (
                                cmip_lib.df_dict[stat][season][region].pop("rt")
                            )

        if var in model_lib.var_list and var in cmip_lib.var_list:
            varunt = var + "\n" + str(units_all[var])
            indv1 = cmip_lib.var_list.index(var)
            indv2 = model_lib.var_list.index(var)
            cmip_lib.var_unit_list[indv1] = varunt
            model_lib.var_unit_list[indv2] = varunt
            variable_units.append(varunt)
            variable_names.append(var)
            del (indv1, indv2, varunt)
        else:
            print("Warning: {} is not found in metrics data".format(var))
            print(
                "Warning: {} is possibly not included as default in fill_plot_var_and_units()".format(
                    var
                )
            )

    # sanity check for cmip data
    for stat in cmip_lib.df_dict:
        for season in cmip_lib.df_dict[stat]:
            for region in cmip_lib.df_dict[stat][season]:
                df = pd.DataFrame(cmip_lib.df_dict[stat][season][region])
                for i, model in enumerate(df["model"].tolist()):
                    if model in ["E3SM-1-0", "E3SM-1-1-ECA"]:
                        idxs = df[df.iloc[:, 0] == model].index
                        df.loc[idxs, "ta-850"] = np.nan
                        del idxs
                    if model in ["CIESM"]:
                        idxs = df[df.iloc[:, 0] == model].index
                        df.loc[idxs, "pr"] = np.nan
                        del idxs
                cmip_lib.df_dict[stat][season][region] = df
                del df

    return model_lib, cmip_lib, variable_names, variable_units


def find_metrics_data(parameter):
    pmp_set = parameter.pcmdi_data_set
    pmp_path = parameter.pcmdi_data_path
    test_set = parameter.test_data_set
    test_path = parameter.test_data_path
    refr_set = parameter.refr_data_set
    refr_path = parameter.refr_data_path
    run_type = parameter.run_type
    debug = parameter.debug

    test_mip = test_set.split(".")[0]
    test_exp = test_set.split(".")[1]
    test_case_id = test_set.split(".")[-1]
    test_dir = os.path.join(test_path, test_mip, test_exp, test_case_id)
    if run_type == "model_vs_model":
        refr_mip = refr_set.split(".")[0]
        refr_exp = refr_set.split(".")[1]
        refr_case_id = refr_set.split(".")[-1]
        refr_dir = os.path.join(refr_path, refr_mip, refr_exp, refr_case_id)

    variables = [
        s.split("/")[-1].split("_")[0]
        for s in glob.glob(os.path.join(test_dir, "*{}.json".format(test_case_id)))
        if os.path.exists(s)
    ]
    variables = list(set(variables))

    # find list of metrics data files
    test_list = []
    refr_list = []
    cmip_list = []

    for vv in variables:
        ftest = glob.glob(
            os.path.join(test_dir, "{}_*_{}.json".format(vv, test_case_id))
        )
        fcmip, rcode = find_cmip_metric_data(pmp_path, pmp_set, vv)
        if rcode == 0:
            if len(ftest) > 0 and len(fcmip) > 0:
                for fx in ftest:
                    test_list.append(fx)
                cmip_list.append(fcmip)
                if debug:
                    print(ftest[0].split("/")[-1], fcmip.split("/")[-1])
            if run_type == "model_vs_model":
                frefr = glob.glob(
                    os.path.join(refr_dir, "{}_*_{}.json".format(vv, refr_case_id))
                )
                if len(frefr) > 0:
                    for fr in frefr:
                        refr_list.append(fr)
                    if debug:
                        print(
                            ftest[0].split("/")[-1],
                            frefr[0].split("/")[-1],
                            fcmip.split("/")[-1],
                        )
                del frefr
        del (ftest, fcmip)
    return test_list, refr_list, cmip_list
