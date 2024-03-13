# Script to plot some global atmosphere and ocean time series
import glob
import math
import sys
import traceback
from typing import Any, List, Tuple

import matplotlib as mpl
import matplotlib.backends.backend_pdf
import matplotlib.pyplot as plt
import numpy as np
from netCDF4 import Dataset
from readTS import TS

mpl.use("Agg")


# ---additional function to get moc time series
def getmoc(dir_in):
    files = sorted(glob.glob(dir_in + "mocTimeSeries*.nc"))
    nfiles = len(files)
    print(dir_in, nfiles, "moc files in total")
    var = np.array([])
    time = np.array([])
    for i in range(nfiles):
        # Open input file
        fin = Dataset(files[i], "r")
        time0 = fin["year"][:]
        var0 = fin["mocAtlantic26"][:]
        for iyear in range(int(time0[0]), int(time0[-1]) + 1):
            if i > 0 and iyear <= time[-1]:
                print(
                    "the amoc value for year",
                    iyear,
                    "has been included in the moc time series from another moc file",
                    files[i - 1],
                    time[-1],
                    "Skipping...",
                )
            else:
                imon = np.where(time0 == iyear)[0]
                if len(imon) == 12:
                    var = np.append(var, np.mean(var0[imon]))
                    time = np.append(time, iyear)
                else:
                    print("error in input file :", files[i])

    return time, var


# -----------------------------------------------------------------------------
# Function to add horizontal line showing average value over a specified period
def add_line(year, var, year1, year2, ax, format="%4.2f", lw=1, color="b"):

    i1 = (np.abs(year - year1)).argmin()
    i2 = (np.abs(year - year2)).argmin()

    tmp = np.average(var[i1 : i2 + 1])
    ax.plot((year[i1], year[i2]), (tmp, tmp), lw=lw, color=color)
    ax.text(ax.get_xlim()[1] + 1, tmp, format % tmp, va="center", color=color)

    return


# -----------------------------------------------------------------------------
# Function to add line showing linear trend over a specified period
def add_trend(
    year,
    var,
    year1,
    year2,
    ax,
    format="%4.2f",
    lw=1,
    color="b",
    verbose=False,
    ohc=False,
    vol=False,
):

    i1 = (np.abs(year - year1)).argmin()
    i2 = (np.abs(year - year2)).argmin()
    x = year[i1 : i2 + 1]
    y = var[i1 : i2 + 1]

    fit = np.polyfit(x, y, 1)
    if verbose:
        print(fit)
    fit_fn = np.poly1d(fit)
    ax.plot(x, fit_fn(x), lw=lw, ls="--", c=color)
    if ohc:
        # Earth radius 6371229. from MPAS-O output files
        heat_uptake = fit[0] / (4.0 * math.pi * (6371229.0) ** 2 * 365.0 * 86400.0)
        ax.text(
            ax.get_xlim()[1] + 1,
            fit_fn(x[-1]),
            "%+4.2f W m$^{-2}$" % (heat_uptake),
            color=color,
        )
    if vol:
        # Earth radius 6371229. from MPAS-O output files
        # sea_lvl = fit[0] / ( 4.0*math.pi*(6371229.)**2*0.7)      #for oceanic portion of the Earth surface
        ax.text(
            ax.get_xlim()[1] + 1,
            fit_fn(x[-1]),
            "%+5.4f mm yr$^{-1}$" % (fit[0]),
            color=color,
        )

    return


# -----------------------------------------------------------------------------
# Function to get ylim
def get_ylim(standard_range, extreme_values):
    standard_min = standard_range[0]
    standard_max = standard_range[1]
    if extreme_values == []:
        return [standard_min, standard_max]
    extreme_min = np.amin(extreme_values)
    extreme_max = np.amax(extreme_values)
    if standard_min <= extreme_min:
        ylim_min = standard_min
    else:
        ylim_min = extreme_min
    if standard_max >= extreme_max:
        ylim_max = standard_max
    else:
        ylim_max = extreme_max
    return [ylim_min, ylim_max]


# -----------------------------------------------------------------------------
# Plotting functions

# Generic plot function
def plot_generic(ax, xlim, exps, var_name, rgn):
    print("plot_generic")
    print(exps)
    param_dict = {
        "2nd_var": False,
        "axhline_y": 0,
        "check_exp_ocean": False,
        "check_exp_vol": False,
        "check_exp_year": True,
        "default_ylim": [-1, 1],
        "do_add_line": True,
        "do_add_trend": True,
        "format": "%4.2f",
        "glb_only": False,
        "lw": 1.0,
        "ohc": False,
        "set_axhline": False,
        "set_legend": True,
        "shorten_year": False,
        "title": var_name,
        "use_getmoc": False,
        "var": lambda exp: np.array(exp["annual"][var_name][0]),
        "verbose": False,
        "vol": False,
        "ylabel": lambda exp: np.array(exp["annual"][var_name][1]),
    }
    plot(ax, xlim, exps, param_dict, rgn)


# 1
def plot_net_toa_flux_restom(ax, xlim, exps, rgn):
    print("Plot 1: plot_net_toa_flux_restom")
    param_dict = {
        "2nd_var": False,
        "axhline_y": 0,
        "check_exp_ocean": False,
        "check_exp_vol": False,
        "check_exp_year": True,
        "default_ylim": [-1.5, 1.5],
        "do_add_line": True,
        "do_add_trend": True,
        "format": "%4.2f",
        "glb_only": False,
        "lw": 1.0,
        "ohc": False,
        "set_axhline": True,
        "set_legend": True,
        "shorten_year": False,
        "title": "Net TOA flux (restom)",
        "use_getmoc": False,
        "var": lambda exp: np.array(exp["annual"]["RESTOM"][0]),
        "verbose": False,
        "vol": False,
        "ylabel": "W m-2",
    }
    plot(ax, xlim, exps, param_dict, rgn)


# 2
def plot_global_surface_air_temperature(ax, xlim, exps, rgn):
    print("Plot 2: plot_global_surface_air_temperature")
    if rgn == "glb":
        region_title = "Global"
    elif rgn == "n":
        region_title = "Northern Hemisphere"
    elif rgn == "s":
        region_title = "Southern Hemisphere"
    else:
        raise RuntimeError(f"Invalid rgn={rgn}")
    param_dict = {
        "2nd_var": False,
        "axhline_y": None,
        "check_exp_ocean": False,
        "check_exp_vol": False,
        "check_exp_year": True,
        "default_ylim": [13, 15.5],
        "do_add_line": True,
        "do_add_trend": True,
        "format": "%4.2f",
        "glb_only": False,
        "lw": 1.0,
        "ohc": False,
        "set_axhline": False,
        "set_legend": False,
        "shorten_year": False,
        "title": f"{region_title} surface air temperature",
        "use_getmoc": False,
        "var": lambda exp: np.array(exp["annual"]["TREFHT"][0]) - 273.15,
        "verbose": False,
        "vol": False,
        "ylabel": "degC",
    }
    plot(ax, xlim, exps, param_dict, rgn)


# 3
def plot_toa_radiation(ax, xlim, exps, rgn):
    print("Plot 3: plot_toa_radiation")
    param_dict = {
        "2nd_var": True,
        "axhline_y": None,
        "check_exp_ocean": False,
        "check_exp_vol": False,
        "check_exp_year": False,
        "default_ylim": [235, 245],
        "do_add_line": False,
        "do_add_trend": False,
        "format": None,
        "glb_only": False,
        "lw": 1.0,
        "ohc": False,
        "set_axhline": False,
        "set_legend": False,
        "shorten_year": False,
        "title": "TOA radiation: SW (solid), LW (dashed)",
        "use_getmoc": False,
        "var": lambda exp: np.array(exp["annual"]["FSNTOA"][0]),
        "verbose": None,
        "vol": None,
        "ylabel": "W m-2",
    }
    plot(ax, xlim, exps, param_dict, rgn)


# 4
def plot_net_atm_energy_imbalance(ax, xlim, exps, rgn):
    print("Plot 4: plot_net_atm_energy_imbalance")
    param_dict = {
        "2nd_var": False,
        "axhline_y": None,
        "check_exp_ocean": False,
        "check_exp_vol": False,
        "check_exp_year": True,
        "default_ylim": [-0.3, 0.3],
        "do_add_line": True,
        "do_add_trend": False,
        "format": "%4.2f",
        "glb_only": False,
        "lw": 1.0,
        "ohc": False,
        "set_axhline": False,
        "set_legend": False,
        "shorten_year": False,
        "title": "Net atm energy imbalance (restom-ressurf)",
        "use_getmoc": False,
        "var": lambda exp: np.array(exp["annual"]["RESTOM"][0])
        - np.array(exp["annual"]["RESSURF"][0]),
        "verbose": False,
        "vol": False,
        "ylabel": "W m-2",
    }
    plot(ax, xlim, exps, param_dict, rgn)


# 5
def plot_change_ohc(ax, xlim, exps, rgn):
    print("Plot 5: plot_change_ohc")
    param_dict = {
        "2nd_var": False,
        "axhline_y": 0,
        "check_exp_ocean": True,
        "check_exp_vol": False,
        "check_exp_year": False,
        "default_ylim": [-0.3e24, 0.9e24],
        "do_add_line": False,
        "do_add_trend": True,
        "format": "%4.2f",
        "glb_only": True,
        "lw": 1.5,
        "ohc": True,
        "set_axhline": True,
        "set_legend": True,
        "shorten_year": True,
        "title": "Change in ocean heat content",
        "use_getmoc": False,
        "var": lambda exp: np.array(exp["annual"]["ohc"]),
        "verbose": False,
        "vol": False,
        "ylabel": "J",
    }
    plot(ax, xlim, exps, param_dict, rgn)


# 6
def plot_max_moc(ax, xlim, exps, rgn):
    print("Plot 6: plot_max_moc")
    param_dict = {
        "2nd_var": False,
        "axhline_y": 10,
        "check_exp_ocean": False,
        "check_exp_vol": False,
        "check_exp_year": False,
        "default_ylim": [4, 22],
        "do_add_line": False,
        "do_add_trend": True,
        "format": "%4.2f",
        "glb_only": True,
        "lw": 1.5,
        "ohc": False,
        "set_axhline": True,
        "set_legend": True,
        "shorten_year": False,
        "title": "Max MOC Atlantic streamfunction at 26.5N",
        "use_getmoc": True,
        "var": None,
        "verbose": True,
        "vol": None,
        "ylabel": "Sv",
    }
    plot(ax, xlim, exps, param_dict, rgn)


# 7
def plot_change_sea_level(ax, xlim, exps, rgn):
    print("Plot 7: plot_change_sea_level")
    param_dict = {
        "2nd_var": False,
        "axhline_y": None,
        "check_exp_ocean": False,
        "check_exp_vol": True,
        "check_exp_year": True,
        "default_ylim": [4, 22],
        "do_add_line": False,
        "do_add_trend": True,
        "format": "%5.3f",
        "glb_only": True,
        "lw": 1.5,
        "ohc": False,
        "set_axhline": False,
        "set_legend": True,
        "shorten_year": True,
        "title": "Change in sea level",
        "use_getmoc": False,
        "var": lambda exp: (
            1e3
            * np.array(exp["annual"]["volume"])
            / (4.0 * math.pi * (6371229.0) ** 2 * 0.7)
        ),
        "verbose": True,
        "vol": True,
        "ylabel": "mm",
    }
    plot(ax, xlim, exps, param_dict, rgn)


# 8
def plot_net_atm_water_imbalance(ax, xlim, exps, rgn):
    print("Plot 8: plot_net_atm_water_imbalance")
    param_dict = {
        "2nd_var": False,
        "axhline_y": None,
        "check_exp_ocean": False,
        "check_exp_vol": False,
        "check_exp_year": False,
        "default_ylim": [-1, 1],
        "do_add_line": True,
        "do_add_trend": False,
        "format": "%5.4f",
        "glb_only": False,
        "lw": 1.0,
        "ohc": False,
        "set_axhline": False,
        "set_legend": False,
        "shorten_year": False,
        "title": "Net atm water imbalance (evap-prec)",
        "use_getmoc": False,
        "var": lambda exp: (
            365
            * 86400
            * (
                np.array(exp["annual"]["QFLX"][0])
                - 1e3
                * (
                    np.array(exp["annual"]["PRECC"][0])
                    + np.array(exp["annual"]["PRECL"][0])
                )
            )
        ),
        "verbose": False,
        "vol": False,
        "ylabel": "mm yr-1",
    }
    plot(ax, xlim, exps, param_dict, rgn)


# FIXME: C901 'plot' is too complex (19)
def plot(ax, xlim, exps, param_dict, rgn):  # noqa: C901
    if param_dict["glb_only"] and (rgn != "glb"):
        return
    ax.set_xlim(xlim)
    extreme_values = []
    for exp in exps:
        print("exp[annual]=")
        print(exp["annual"].keys())
        # dict_keys(['TREFHT', 'year', 'FSNTOA', 'FLUT', 'PRECC', 'PRECL', 'QFLX', 'TS', 'FSNT', 'FLNT', 'ohc', 'volume'])
        if param_dict["check_exp_ocean"] and (exp["ocean"] is None):
            continue
        if param_dict["check_exp_vol"] and (exp["vol"] is None):
            continue
        if param_dict["use_getmoc"]:
            if exp["moc"]:
                [year, var] = getmoc(exp["moc"])
            else:
                continue
        else:
            year = np.array(exp["annual"]["year"]) + exp["yoffset"]
            var = param_dict["var"](exp)
        extreme_values.append(np.amax(var))
        extreme_values.append(np.amin(var))
        if param_dict["shorten_year"]:
            year = year[: len(var)]
        ax.plot(
            year,
            var,
            lw=param_dict["lw"],
            marker=None,
            c=exp["color"],
            label=exp["name"],
        )
        if param_dict["2nd_var"]:
            # Specifically for plot_toa_radiation
            # TODO: if more plots require a 2nd variable, we can change `var` to be a list,
            # but that will be a more significant refactoring.
            var = np.array(exp["annual"]["FLUT"][0])
            ax.plot(year, var, lw=1.0, marker=None, ls=":", c=exp["color"])
            continue
        if param_dict["check_exp_year"] and exp["yr"] is None:
            continue
        elif param_dict["do_add_line"] or param_dict["do_add_trend"]:
            print(f"exp['name']={exp['name']}")
            for yrs in exp["yr"]:
                if param_dict["do_add_line"]:
                    add_line(
                        year,
                        var,
                        yrs[0],
                        yrs[1],
                        format=param_dict["format"],
                        ax=ax,
                        lw=2 * param_dict["lw"],
                        color=exp["color"],
                    )
                if param_dict["do_add_trend"]:
                    add_trend(
                        year,
                        var,
                        yrs[0],
                        yrs[1],
                        format=param_dict["format"],
                        ax=ax,
                        lw=2 * param_dict["lw"],
                        color=exp["color"],
                        ohc=param_dict["ohc"],
                        verbose=param_dict["verbose"],
                        vol=param_dict["vol"],
                    )
    ax.set_ylim(get_ylim(param_dict["default_ylim"], extreme_values))
    if param_dict["set_axhline"]:
        ax.axhline(y=param_dict["axhline_y"], lw=1, c="0.5")
    ax.set_title(param_dict["title"])
    ax.set_xlabel("Year")
    units = param_dict["ylabel"]
    print(units)
    try:
        c = callable(units)
    except Exception as e:
        print(e)
        raise e
    if c:
        print(exps[1])
        units = units(exps[1])  # How do we know which var's units to put as the ylabel?
        print(units)
    print("EEE")
    ax.set_ylabel(units)
    if param_dict["set_legend"]:
        ax.legend(loc="best")


PLOT_DICT = {
    "net_toa_flux_restom": plot_net_toa_flux_restom,
    "global_surface_air_temperature": plot_global_surface_air_temperature,
    "toa_radiation": plot_toa_radiation,
    "net_atm_energy_imbalance": plot_net_atm_energy_imbalance,
    "change_ohc": plot_change_ohc,  # only glb
    "max_moc": plot_max_moc,  # only glb
    "change_sea_level": plot_change_sea_level,  # only glb
    "net_atm_water_imbalance": plot_net_atm_water_imbalance,
}


def param_get_list(param_value):
    if param_value == "None":
        return []
    else:
        return param_value.split(",")


def set_var(exp, exp_key, var_list, valid_vars, invalid_vars, rgn):
    if exp[exp_key] is not None:
        print(f"exp['{exp_key}']={exp[exp_key]}")
        ts = TS(exp[exp_key])
        for var in var_list:
            try:
                v, units = ts.globalAnnual(var)
                valid_vars.append(str(var))
            except Exception as e:
                print(e)
                print(f"globalAnnual failed. Invalid var = {var}")
                invalid_vars.append(str(var))
                continue
            if len(v.shape) > 1:
                # number of years x 3 regions = v.shape
                # 3 regions = global, northern hemisphere, southern hemisphere
                # We get here if we used the updated `ts` task
                # (using `rgn_avg` rather than `glb_avg`).
                if rgn == "glb":
                    n = 0
                elif rgn == "n":
                    n = 1
                elif rgn == "s":
                    n = 2
                else:
                    raise RuntimeError(f"Invalid rgn={rgn}")
                v = v[:, n]  # Just use nth column
            elif rgn != "glb":
                # v only has one dimension -- glb.
                # Therefore it is not possible to get n or s plots.
                raise RuntimeError(
                    f"var={var} only has global data. Cannot process rgn={rgn}"
                )
            exp["annual"][var] = v
            print(f"var={var} units={units}")
            exp["annual"][var] = (v, units)
            if "year" not in exp["annual"]:
                time = v.getTime()
                exp["annual"]["year"] = [x.year for x in time.asComponentTime()]
        del ts


# -----------------------------------------------------------------------------
# FIXME: C901 'run' is too complex (19)
def run(parameters, rgn):  # noqa: C901
    # These are the "Tableau 20" colors as RGB.
    t20: List[Tuple[float, float, float]] = [
        (31, 119, 180),
        (174, 199, 232),
        (255, 127, 14),
        (255, 187, 120),
        (44, 160, 44),
        (152, 223, 138),
        (214, 39, 40),
        (255, 152, 150),
        (148, 103, 189),
        (197, 176, 213),
        (140, 86, 75),
        (196, 156, 148),
        (227, 119, 194),
        (247, 182, 210),
        (127, 127, 127),
        (199, 199, 199),
        (188, 189, 34),
        (219, 219, 141),
        (23, 190, 207),
        (158, 218, 229),
    ]
    # Scale the RGB values to the [0, 1] range, which is the format matplotlib accepts.
    for i in range(len(t20)):
        r, g, b = t20[i]
        t20[i] = (r / 255.0, g / 255.0, b / 255.0)

    # "Tableau 10" uses every other color
    t10 = []
    for i in range(0, len(t20), 2):
        t10.append(t20[i])

    # -----------------------------------------------------------------------------
    # --- Atmos data ---

    # Experiments
    case_dir = parameters[1]
    experiment_name = parameters[2]
    figstr = parameters[3]
    year1 = int(parameters[4])
    year2 = int(parameters[5])
    color = parameters[6]
    ts_num_years = parameters[7]
    plot_list = param_get_list(parameters[8])
    plots_atm = param_get_list(parameters[9])
    plots_lnd = param_get_list(parameters[10])
    plots_ocn = param_get_list(parameters[11])
    exps = [
        {
            "atmos": None
            if not plots_atm
            else "{}/post/atm/glb/ts/monthly/{}yr/glb.xml".format(
                case_dir, ts_num_years
            ),
            "land": None
            if not plots_lnd
            else "{}/post/lnd/glb/ts/monthly/{}yr/glb.xml".format(
                case_dir, ts_num_years
            ),
            "ocean": None
            if not plots_ocn
            else "{}/post/ocn/glb/ts/monthly/{}yr/glb.xml".format(
                case_dir, ts_num_years
            ),
            "moc": None
            if not plots_ocn
            else "{}/post/ocn/glb/ts/monthly/{}yr/".format(case_dir, ts_num_years),
            "vol": None
            if not plots_ocn
            else "{}/post/ocn/glb/ts/monthly/{}yr/glb.xml".format(
                case_dir, ts_num_years
            ),
            "name": experiment_name,
            "yoffset": 0.0,
            "yr": ([year1, year2],),
            "color": f"{color}",
        }
    ]

    atm_vars = [
        "RESTOM",
        "RESSURF",
        "TREFHT",
        "FSNTOA",
        "FLUT",
        "PRECC",
        "PRECL",
        "QFLX",
    ] + plots_atm
    lnd_vars = plots_lnd
    ocn_vars = plots_ocn
    valid_vars: List[str] = []
    invalid_vars: List[str] = []

    # Read data
    exp: Any
    for exp in exps:
        exp["annual"] = {}
        set_var(exp, "atmos", atm_vars, valid_vars, invalid_vars, rgn)
        set_var(exp, "land", lnd_vars, valid_vars, invalid_vars, rgn)
        set_var(exp, "ocean", ocn_vars, valid_vars, invalid_vars, rgn)

        # Optionally read ohc
        if exp["ocean"] is not None:
            ts = TS(exp["ocean"])
            exp["annual"]["ohc"], _ = ts.globalAnnual("ohc")
            # annomalies with respect to first year
            exp["annual"]["ohc"][:] = exp["annual"]["ohc"][:] - exp["annual"]["ohc"][0]

        if exp["vol"] is not None:
            ts = TS(exp["vol"])
            exp["annual"]["volume"], _ = ts.globalAnnual("volume")
            # annomalies with respect to first year
            exp["annual"]["volume"][:] = (
                exp["annual"]["volume"][:] - exp["annual"]["volume"][0]
            )

    print(f"globalAnnual was computed successfully for these variables: {valid_vars}")
    if invalid_vars:
        raise Exception(
            f"globalAnnual could not be computed for these variables: {invalid_vars}"
        )

    # -----------------------------------------------------------------------------
    # --- Generate plots ---

    xlim = [float(year1), float(year2)]

    extra_plots = plots_atm + plots_lnd + plots_ocn

    num_initial_plots = len(plot_list)
    num_extra_plots = len(extra_plots)
    num_total_plots = num_initial_plots + num_extra_plots
    nrows = 4
    ncols = 2
    plots_per_page = nrows * ncols
    num_pages = math.ceil(num_total_plots / plots_per_page)

    counter_initial_plots = 0
    counter_extra_plots = 0
    valid_plots = []
    invalid_plots = []
    # https://stackoverflow.com/questions/58738992/save-multiple-figures-with-subplots-into-a-pdf-with-multiple-pages
    pdf = matplotlib.backends.backend_pdf.PdfPages(f"{figstr}_{rgn}.pdf")
    for page in range(num_pages):
        fig = plt.figure(1, figsize=[13.5, 16.5])
        fig.suptitle(f"{figstr}_{rgn}")
        for j in range(plots_per_page):
            if counter_initial_plots < num_initial_plots:
                ax = plt.subplot(nrows, ncols, j + 1)
                try:
                    PLOT_DICT[plot_list[counter_initial_plots]](ax, xlim, exps, rgn)
                except KeyError:
                    raise KeyError(
                        f"Invalid plot name: {plot_list[counter_initial_plots]}"
                    )
                counter_initial_plots += 1
            elif counter_extra_plots < num_extra_plots:
                ax = plt.subplot(nrows, ncols, j + 1)
                try:
                    plot = extra_plots[counter_extra_plots]
                    plot_generic(ax, xlim, exps, plot, rgn)
                    valid_plots.append(plot)
                except Exception:
                    traceback.print_exc()
                    invalid_plot = extra_plots[counter_extra_plots]
                    print(f"plot_generic failed. Invalid plot={invalid_plot}")
                    invalid_plots.append(invalid_plot)
                counter_extra_plots += 1

        fig.tight_layout()
        pdf.savefig(1)
        if num_pages > 1:
            fig.savefig(f"{figstr}_{rgn}_{page}.png", dpi=150)
        else:
            fig.savefig(f"{figstr}_{rgn}.png", dpi=150)
        plt.clf()
    pdf.close()
    print(f"These plots generated successfully: {valid_plots}")
    if invalid_plots:
        raise Exception(f"These plots could not be generated: {invalid_plots}")


def run_by_region(parameters):
    print(parameters)
    regions = parameters[12].split(",")
    for rgn in regions:
        if rgn.lower() in ["glb", "global"]:
            rgn = "glb"
        elif rgn.lower() in ["n", "north", "northern"]:
            rgn = "n"
        elif rgn.lower() in ["s", "south", "southern"]:
            rgn = "s"
        else:
            raise RuntimeError(f"Invalid rgn={rgn}")
        run(parameters, rgn)


if __name__ == "__main__":
    run_by_region(sys.argv)
