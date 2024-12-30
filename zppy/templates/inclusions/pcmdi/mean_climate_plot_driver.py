#!/bin/env python
##############################################################################
# This model is used to generate mean climate diagnostic figures
# Author: Shixuan Zhang (shixuan.zhang@pnnl.gov)
#############################################################################
import os
import shutil

import numpy as np
import pandas as pd
from mean_climate_plot_parser import (
    fill_plot_var_and_units,
    find_metrics_data,
    metrics_inquire,
    shift_row_to_bottom,
)
from pcmdi_metrics.graphics import (
    Metrics,
    normalize_by_median,
    parallel_coordinate_plot,
    portrait_plot,
)


def load_test_model_data(test_file, refr_file, mip, run_type):
    # load the data and reorganize if needed
    pd.set_option("future.no_silent_downcasting", True)
    test_lib = Metrics(test_file)

    # model_vs_model, merge the reference model data into test model
    if run_type == "model_vs_model":
        refr_lib = Metrics(refr_file)
        test_lib = test_lib.merge(refr_lib)
        del refr_lib

    # collect and reorgnize test model data for plotting:
    test_models = []
    for stat in test_lib.df_dict:
        for season in test_lib.df_dict[stat]:
            for region in test_lib.df_dict[stat][season]:
                df = pd.DataFrame(test_lib.df_dict[stat][season][region])
                for i, model in enumerate(df["model"].tolist()):
                    model_run = df["model_run"].tolist()[i]
                    new_name = "{}-{}".format(mip.upper(), model_run.upper())
                    idxs = df[df.iloc[:, 2] == model_run].index
                    df.loc[idxs, "model"] = list(
                        map(
                            lambda x: x.replace(model, new_name),
                            df.loc[idxs, "model"],
                        )
                    )
                    if new_name not in test_models:
                        test_models.append(new_name)
                test_lib.df_dict[stat][season][region] = df
                del df
    return test_models, test_lib


def load_cmip_metrics_data(cmip_file):
    # collect cmip multi-model ensemble data for comparison
    pd.set_option("future.no_silent_downcasting", True)
    cmip_lib = Metrics(cmip_file)
    cmip_models = []
    highlight_models = []
    for stat in cmip_lib.df_dict:
        for season in cmip_lib.df_dict[stat]:
            for region in cmip_lib.df_dict[stat][season]:
                # now find all E3SM models in cmip6
                df = pd.DataFrame(cmip_lib.df_dict[stat][season][region])
                for model in df["model"].tolist():
                    if model not in cmip_models:
                        cmip_models.append(model)
                    if ("e3sm" in model.lower()) and (model not in highlight_models):
                        highlight_models.append(model)
                # move highlight_models to the end
                for model in highlight_models:
                    idxs = df[df.iloc[:, 0] == model].index
                    cmip_models.remove(model)
                    cmip_models.append(model)
                    for idx in idxs:
                        df = shift_row_to_bottom(df, idx)
                cmip_lib.df_dict[stat][season][region] = df
                del df
    return cmip_models, highlight_models, cmip_lib


def save_figure_data(
    stat, region, season, var_names, var_units, data_dict, template, outdir
):
    # construct output file name
    fname = (
        template.replace("%(metric)", stat)
        .replace("%(region)", region)
        .replace("%(season)", season)
    )
    outfile = os.path.join(outdir, fname)
    outdic = pd.DataFrame(data_dict)
    outdic = outdic.drop(columns=["model_run"])
    for var in list(outdic.columns.values[3:]):
        if var not in var_names:
            print("{} is excluded from the {}".format(var, fname))
            outdic = outdic.drop(columns=[var])
        else:
            # replace the variable with the name + units
            outdic.columns.values[outdic.columns.values.tolist().index(var)] = (
                var_units[var_names.index(var)]
            )

    # save data to .csv file
    outdic.to_csv(outfile)
    del (fname, outfile, outdic)
    return


def construct_port4sea_axis_lables(
    var_names, cmip_models, test_models, highlight_models
):
    model_list = cmip_models + test_models
    # assign colors for labels of models
    lable_colors = []
    for model in model_list:
        if model in highlight_models:
            lable_colors.append("#5170d7")
        elif model in test_models:
            lable_colors.append("#FC5A50")
        else:
            lable_colors.append("#000000")

    if len(model_list) > len(var_names):
        xlabels = model_list
        ylabels = var_names
        landscape = True
    else:
        xlabels = var_names
        ylabels = model_list
        landscape = False
    del model_list
    return xlabels, ylabels, lable_colors, landscape


def construct_port4sea_data(
    stat,
    seasons,
    region,
    data_dict,
    var_names,
    var_units,
    file_template,
    outdir,
    landscape,
):
    # work array
    data_all = dict()
    # loop 4 seasons and collect data
    for season in seasons:
        # save raw metric results as a .csv file for each season
        save_figure_data(
            stat,
            region,
            season,
            var_names,
            var_units,
            data_dict[stat][season][region],
            file_template,
            outdir,
        )
        if stat == "cor_xy":
            data_nor = data_dict[stat][season][region][var_names].to_numpy()
            if landscape:
                data_all[season] = data_nor.T
            else:
                data_all[season] = data_nor
            del data_nor
        elif stat == "bias_xy":
            # calculate the relative bias
            data_sea = data_dict[stat][season][region][var_names].to_numpy()
            data_rfm = data_dict["mean-obs_xy"][season][region][var_names].to_numpy()
            data_msk = np.where(np.abs(data_rfm) == 0.0, np.nan, data_rfm)
            data_nor = data_sea * 100.0 / data_msk
            if landscape:
                data_all[season] = data_nor.T
            else:
                data_all[season] = data_nor
            del (data_sea, data_rfm, data_msk, data_nor)
        else:
            data_sea = data_dict[stat][season][region][var_names].to_numpy()
            if landscape:
                data_sea = data_sea.T
                data_all[season] = normalize_by_median(data_sea, axis=1)
            else:
                data_all[season] = normalize_by_median(data_sea, axis=0)
            del data_sea

    # data for final plot
    data_all_nor = np.stack(
        [data_all["djf"], data_all["mam"], data_all["jja"], data_all["son"]]
    )
    del data_all
    return data_all_nor


def port4sea_plot(
    stat,
    region,
    seasons,
    data_dict,
    var_names,
    var_units,
    cmip_models,
    test_models,
    highlight_models,
    file_template,
    figure_template,
    outdir,
    add_vertical_line,
    data_version=None,
    watermark=False,
):

    # process figure
    fontsize = 20
    var_names = sorted(var_names)
    var_units = sorted(var_units)

    # construct the axis labels and colors
    (
        xaxis_labels,
        yaxis_labels,
        lable_colors,
        landscape,
    ) = construct_port4sea_axis_lables(
        var_names, cmip_models, test_models, highlight_models
    )

    # construct data for plotting
    data_all_nor = construct_port4sea_data(
        stat,
        seasons,
        region,
        data_dict,
        var_names,
        var_units,
        file_template,
        outdir,
        landscape,
    )

    if stat == "cor_xy":
        cbar_label = "Pattern Corr."
        var_range = (-1.0, 1.0)
        cmap_bounds = [0.1, 0.2, 0.4, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0]
    elif stat == "bias_xy":
        cbar_label = "{}, relative (%)".format(stat.upper())
        var_range = (-30.0, 30.0)
        cmap_bounds = [-30.0, -20.0, -10.0, -5.0, -1, 0.0, 1.0, 5.0, 10.0, 20.0, 30.0]
    else:
        cbar_label = "{}, normalized by median".format(stat.upper())
        var_range = (-0.5, 0.5)
        cmap_bounds = [-0.5, -0.4, -0.3, -0.2, -0.1, 0, 0.1, 0.2, 0.3, 0.4, 0.5]

    if landscape:
        figsize = (40, 18)
        legend_box_xy = (1.08, 1.18)
        legend_box_size = 4
        legend_lw = 1.5
        shrink = 0.8
        legend_fontsize = fontsize * 0.8
    else:
        figsize = (18, 25)
        legend_box_xy = (1.25, 1)
        legend_box_size = 3
        legend_lw = 1.5
        shrink = 1.0
        legend_fontsize = fontsize * 0.8

    # Add Watermark/Logo
    if watermark:
        logo_rect = [0.85, 0.15, 0.07, 0.07]
        logo_off = False
    else:
        logo_rect = [0, 0, 0, 0]
        logo_off = True

    # Using Matplotlib-based PMP Visualization Function to Generate Portrait Plot
    fig, ax, cbar = portrait_plot(
        data_all_nor,
        xaxis_labels=xaxis_labels,
        yaxis_labels=yaxis_labels,
        cbar_label=cbar_label,
        cbar_label_fontsize=fontsize * 1.2,
        box_as_square=True,
        vrange=var_range,
        figsize=figsize,
        cmap="RdYlBu_r",
        cmap_bounds=cmap_bounds,
        cbar_kw={"extend": "both", "shrink": shrink},
        missing_color="white",
        legend_on=True,
        legend_labels=["DJF", "MAM", "JJA", "SON"],
        legend_box_xy=legend_box_xy,
        legend_box_size=legend_box_size,
        legend_lw=legend_lw,
        legend_fontsize=legend_fontsize,
        logo_rect=logo_rect,
        logo_off=logo_off,
    )

    if add_vertical_line:
        ax.axvline(
            x=len(xaxis_labels) - len(highlight_models) - len(test_models),
            color="k",
            linewidth=3,
        )

    if landscape:
        ax.set_xticklabels(xaxis_labels, rotation=45, va="bottom", ha="left")
        ax.set_yticklabels(yaxis_labels, rotation=0, va="center", ha="right")
        for xtick, color in zip(ax.get_xticklabels(), lable_colors):
            xtick.set_color(color)
        ax.yaxis.label.set_color(lable_colors[0])
    else:
        ax.set_xticklabels(xaxis_labels, rotation=45, va="bottom", ha="left")
        ax.set_yticklabels(yaxis_labels, rotation=0, va="center", ha="right")
        ax.xaxis.label.set_color(lable_colors[0])
        for ytick, color in zip(ax.get_yticklabels(), lable_colors):
            ytick.set_color(color)

    ax.tick_params(axis="x", labelsize=fontsize)
    ax.tick_params(axis="y", labelsize=fontsize)

    cbar.ax.tick_params(labelsize=fontsize)

    # Add title
    ax.set_title(
        "Model Performance of Seasonal Climatology ({}, {})".format(
            stat.upper(), region.upper()
        ),
        fontsize=fontsize * 1.5,
        pad=30,
    )

    # Add Watermark
    if watermark:
        ax.text(
            0.5,
            0.5,
            "E3SM-PCMDI",
            transform=ax.transAxes,
            fontsize=100,
            color="black",
            alpha=0.5,
            ha="center",
            va="center",
            rotation=25,
        )
        # Add data info
        fig.text(
            1.25,
            0.9,
            "Data version\n" + data_version,
            transform=ax.transAxes,
            fontsize=12,
            color="black",
            alpha=0.6,
            ha="left",
            va="top",
        )

    # Save figure as an image file
    figname = (
        figure_template.replace("%(metric)", stat)
        .replace("%(region)", region)
        .replace("%(season)", "4season")
    )
    figfile = os.path.join(outdir, figname)
    fig.savefig(figfile, facecolor="w", bbox_inches="tight")
    del (
        data_all_nor,
        xaxis_labels,
        yaxis_labels,
        lable_colors,
    )

    return


def paracord_plot(
    stat,
    region,
    season,
    data_dict,
    var_names,
    var_units,
    cmip_models,
    test_models,
    highlight_models,
    file_template,
    figure_template,
    outdir,
    identify_all_models,
    data_version=None,
    watermark=False,
):

    # construct plotting data
    var_names = sorted(var_names)
    var_units = sorted(var_units)

    # write out the results as a table
    save_figure_data(
        stat, region, season, var_names, var_units, data_dict, file_template, outdir
    )

    # add ensemble mean
    model_data = data_dict[var_names].to_numpy()

    # construct the string for plot
    model_list = data_dict[
        "model"
    ].to_list()  # cmip_models + test_models + ["CMIP6 MME"]
    model_list_group2 = highlight_models + test_models
    models_to_highlight = test_models + [
        data_dict["model"].to_list()[-1]
    ]  # ["CMIP6 MME"]
    figsize = (40, 12)
    fontsize = 20
    legend_ncol = int(7 * figsize[0] / 40.0)
    legend_posistion = (0.50, -0.14)
    # color map for markers
    colormap = "tab20_r"
    # color map for highlight lines
    xcolors = [
        "#000000",
        "#e41a1c",
        "#ff7f00",
        "#4daf4a",
        "#f781bf",
        "#a65628",
        "#984ea3",
        "#999999",
        "#377eb8",
        "#dede00",
    ]
    lncolors = xcolors[1 : len(test_models) + 1] + [xcolors[0]]
    # Add Watermark/Logo
    if watermark:
        logo_rect = [0.85, 0.15, 0.07, 0.07]
        logo_off = False
    else:
        logo_rect = [0, 0, 0, 0]
        logo_off = True

    xlabel = "Metric"
    if "rms" in stat:
        ylabel = "RMS Error (" + stat.upper() + ")"
    elif "std" in stat:
        ylabel = "Standard Deviation (" + stat.upper() + ")"
    else:
        ylabel = "value (" + stat.upper() + ")"

    if not np.isnan(model_data).all():
        print(model_data.min(), model_data.max())
        title = "Model Performance of {} Climatology ({}, {})".format(
            season.upper(), stat.upper(), region.upper()
        )
        fig, ax = parallel_coordinate_plot(
            model_data,
            var_units,
            model_list,
            model_names2=model_list_group2,
            group1_name="CMIP6",
            group2_name="E3SM",
            models_to_highlight=models_to_highlight,
            models_to_highlight_colors=lncolors,
            models_to_highlight_labels=models_to_highlight,
            identify_all_models=identify_all_models,  # hide indiviaul model markers for CMIP6 models
            vertical_center="median",
            vertical_center_line=True,
            title=title,
            figsize=figsize,
            axes_labelsize=fontsize * 1.1,
            title_fontsize=fontsize * 1.1,
            yaxes_label=ylabel,
            xaxes_label=xlabel,
            colormap=colormap,
            show_boxplot=False,
            show_violin=True,
            violin_colors=("lightgrey", "pink"),
            legend_ncol=legend_ncol,
            legend_bbox_to_anchor=legend_posistion,
            legend_fontsize=fontsize * 0.85,
            xtick_labelsize=fontsize * 0.95,
            ytick_labelsize=fontsize * 0.95,
            logo_rect=logo_rect,
            logo_off=logo_off,
        )

        # Add Watermark
        if watermark:
            ax.text(
                0.5,
                0.5,
                "E3SM-PCMDI",
                transform=ax.transAxes,
                fontsize=100,
                color="black",
                alpha=0.5,
                ha="center",
                va="center",
                rotation=25,
            )
            # Add data info
            fig.text(
                1.25,
                0.9,
                "Data version\n" + data_version,
                transform=ax.transAxes,
                fontsize=12,
                color="black",
                alpha=0.6,
                ha="left",
                va="top",
            )

        # Save figure as an image file
        figname = (
            figure_template.replace("%(metric)", stat)
            .replace("%(region)", region)
            .replace("%(season)", season)
        )
        figfile = os.path.join(outdir, figname)
        fig.savefig(figfile, facecolor="w", bbox_inches="tight")

    del (model_data, model_list, model_list_group2, models_to_highlight)

    return


def mean_climate_metrics_plot(parameter):
    # info for test simulation
    test_mip = parameter.test_data_set.split(".")[0]
    test_exp = parameter.test_data_set.split(".")[1]
    test_product = parameter.test_data_set.split(".")[2]
    test_case_id = parameter.test_data_set.split(".")[-1]
    # output directory
    outdir = os.path.join(parameter.output_path, test_mip, test_exp, test_case_id)

    # construct file template to save the figure data in .csv file
    file_template = "%(metric)_%(region)_{}_{}_{}_{}_mean_climate_%(season)_{}.csv"
    file_template = file_template.format(
        parameter.run_type.upper(),
        test_mip.upper(),
        test_exp.upper(),
        test_product.upper(),
        parameter.period,
    )
    # construct figure template
    figure_template = file_template.replace("csv", parameter.ftype)

    # find the metrics data
    test_file, refr_file, cmip_file = find_metrics_data(parameter)

    # load cmip metrics data
    cmip_models, highlight_models, cmip_lib = load_cmip_metrics_data(cmip_file)

    # load test model metrics data
    test_models, test_lib = load_test_model_data(
        test_file, refr_file, test_mip, parameter.run_type
    )
    # collect overlap sets of variables for plotting:
    test_lib, cmip_lib, var_list, var_unit_list = fill_plot_var_and_units(
        test_lib, cmip_lib
    )
    # search overlap of regions in test and reference
    regions = []
    for reg in parameter.regions:
        if (reg in test_lib.regions) and (reg in cmip_lib.regions):
            regions.append(reg)

    # merge the cmip and model data
    merged_lib = cmip_lib.merge(test_lib)

    ###################################
    # generate parallel coordinate plot
    ###################################
    parall_fig_dir = os.path.join(outdir, "paracord_annual")
    if os.path.exists(parall_fig_dir):
        shutil.rmtree(parall_fig_dir)
    os.makedirs(parall_fig_dir)
    print("Parallel Coordinate  Plots (4 seasons), loop each region and metric....")
    # add ensemble mean
    for metric in [
        "rms_xyt",
        "std-obs_xyt",
        "std_xyt",
        "rms_y",
        "rms_devzm",
        "std_xy_devzm",
        "std-obs_xy_devzm",
    ]:
        for region in regions:
            for season in ["ann"]:
                data_dict = merged_lib.df_dict[metric][season][region]
                data_dict.loc["CMIP MMM"] = cmip_lib.df_dict[metric][season][
                    region
                ].mean(numeric_only=True, skipna=True)
                data_dict.at["CMIP MMM", "model"] = "CMIP MMM"
                if parameter.parcord_show_markers is not None:
                    identify_all_models = parameter.parcord_show_markers
                else:
                    identify_all_models = True
                paracord_plot(
                    metric,
                    region,
                    season,
                    data_dict,
                    var_list,
                    var_unit_list,
                    cmip_models,
                    test_models,
                    highlight_models,
                    file_template,
                    figure_template,
                    parall_fig_dir,
                    identify_all_models,
                    data_version=None,
                    watermark=False,
                )
                del data_dict

    ###################################
    # generate portrait plot
    ###################################
    ptrait_fig_dir = os.path.join(outdir, "portrait_4seasons")
    if os.path.exists(ptrait_fig_dir):
        shutil.rmtree(ptrait_fig_dir)
    os.makedirs(ptrait_fig_dir)
    print("Portrait  Plots (4 seasons),loop each region and metric....")
    #########################################################################
    seasons = ["djf", "mam", "jja", "son"]
    data_dict = merged_lib.df_dict
    for metric in ["rms_xy", "cor_xy", "bias_xy"]:
        for region in regions:
            print("working on {} in {} region".format(metrics_inquire(metric), region))
            if parameter.add_vertical_line is not None:
                add_vertical_line = parameter.add_vertical_line
            else:
                add_vertical_line = False
            port4sea_plot(
                metric,
                region,
                seasons,
                data_dict,
                var_list,
                var_unit_list,
                cmip_models,
                test_models,
                highlight_models,
                file_template,
                figure_template,
                ptrait_fig_dir,
                add_vertical_line,
                data_version=None,
                watermark=False,
            )

    # release the data space
    del (merged_lib, cmip_lib, test_lib, var_unit_list, var_list, regions)

    return
