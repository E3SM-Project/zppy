# Script to plot some global atmosphere and ocean time series
import glob
import math
import sys
import traceback
from typing import Any, Dict, List, Optional, Tuple

import cftime
import matplotlib as mpl
import matplotlib.backends.backend_pdf
import matplotlib.pyplot as plt
import numpy as np
import xarray
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
    ax.plot((year[i1], year[i2]), (tmp, tmp), lw=lw, color=color, label="average")
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
    ax.plot(x, fit_fn(x), lw=lw, ls="--", c=color, label="trend")
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
    if len(extreme_values) > 0:
        has_extreme_values = True
        extreme_min = np.amin(extreme_values)
        extreme_max = np.amax(extreme_values)
    else:
        has_extreme_values = False
        extreme_min = None
        extreme_max = None
    if len(standard_range) == 2:
        has_standard_range = True
        standard_min = standard_range[0]
        standard_max = standard_range[1]
    else:
        has_standard_range = False
        standard_min = None
        standard_max = None
    if has_extreme_values and has_standard_range:
        # Use at least the standard range,
        # perhaps a wider window to include extremes
        if standard_min <= extreme_min:
            ylim_min = standard_min
        else:
            ylim_min = extreme_min
        if standard_max >= extreme_max:
            ylim_max = standard_max
        else:
            ylim_max = extreme_max
    elif has_extreme_values and not has_standard_range:
        ylim_min = extreme_min
        ylim_max = extreme_max
    elif has_standard_range and not has_extreme_values:
        ylim_min = standard_min
        ylim_max = standard_max
    else:
        raise ValueError("Not enough range information supplied")
    return [ylim_min, ylim_max]


# -----------------------------------------------------------------------------
# Plotting functions


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
        "set_legend": True,
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
        "set_legend": True,
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
        "set_legend": True,
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


# Generic plot function
def plot_generic(ax, xlim, exps, var_name, rgn):
    print(f"plot_generic for {var_name}")
    param_dict = {
        "2nd_var": False,
        "axhline_y": 0,
        "check_exp_ocean": False,
        "check_exp_vol": False,
        "check_exp_year": True,
        "default_ylim": [],
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


# FIXME: C901 'plot' is too complex (19)
def plot(ax, xlim, exps, param_dict, rgn):  # noqa: C901
    if param_dict["glb_only"] and (rgn != "glb"):
        return
    ax.set_xlim(xlim)
    extreme_values = []
    for exp in exps:
        # Relevant to "Plot 5: plot_change_ohc"
        if param_dict["check_exp_ocean"] and (exp["ocean"] is None):
            continue
        # Relevant to "Plot 7: plot_change_sea_level"
        # This must be checked before plot 6,
        # otherwise, `param_dict["var"]` will be run,
        # but `exp["annual"]["volume"]` won't exist.
        if param_dict["check_exp_vol"] and (exp["vol"] is None):
            continue
        # Relevant to "Plot 6: plot_max_moc"
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
        try:
            ax.plot(
                year,
                var,
                lw=param_dict["lw"],
                marker=None,
                c=exp["color"],
                label=exp["name"],
            )
        except Exception:
            raise RuntimeError(f"{param_dict['title']} could not be plotted.")
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
    ylim = get_ylim(param_dict["default_ylim"], extreme_values)
    ax.set_ylim(ylim)
    if param_dict["set_axhline"]:
        ax.axhline(y=param_dict["axhline_y"], lw=1, c="0.5")
    ax.set_title(param_dict["title"])
    ax.set_xlabel("Year")
    units = param_dict["ylabel"]
    c = callable(units)
    if c:
        units = units(exps[0])
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


def set_var(
    exp: Dict[str, Any],
    exp_key: str,
    var_list: List[str],
    valid_vars: List[str],
    invalid_vars: List[str],
    rgn: str,
) -> None:
    if exp[exp_key] is not None:
        ts = TS(exp[exp_key])
        for var in var_list:
            try:
                v: xarray.core.dataarray.DataArray
                units: Optional[str]
                v, units = ts.globalAnnual(var)
                valid_vars.append(str(var))
            except Exception as e:
                print(e)
                print(f"globalAnnual failed. Invalid var = {var}")
                invalid_vars.append(str(var))
                continue
            if v.sizes["rgn"] > 1:
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
                v = v.isel(rgn=n)  # Just use nth region
            elif rgn != "glb":
                # v only has one dimension -- glb.
                # Therefore it is not possible to get n or s plots.
                raise RuntimeError(
                    f"var={var} only has global data. Cannot process rgn={rgn}"
                )
            exp["annual"][var] = (v, units)
            if "year" not in exp["annual"]:
                years: np.ndarray[cftime.DatetimeNoLeap] = v.coords["time"].values
                exp["annual"]["year"] = [x.year for x in years]
        del ts


def make_plot_pdfs(
    figstr, rgn, component, xlim, exps, plot_list, valid_plots, invalid_plots
):
    num_plots = len(plot_list)
    if num_plots == 0:
        return
    nrows = 4
    ncols = 2
    plots_per_page = nrows * ncols
    num_pages = math.ceil(num_plots / plots_per_page)

    counter = 0
    # https://stackoverflow.com/questions/58738992/save-multiple-figures-with-subplots-into-a-pdf-with-multiple-pages
    pdf = matplotlib.backends.backend_pdf.PdfPages(f"{figstr}_{rgn}_{component}.pdf")
    for page in range(num_pages):
        fig = plt.figure(1, figsize=[13.5, 16.5])
        fig.suptitle(f"{figstr}_{rgn}_{component}")
        for j in range(plots_per_page):
            # The final page doesn't need to be filled out with plots.
            if counter >= num_plots:
                break
            ax = plt.subplot(nrows, ncols, j + 1)
            if component == "original":
                try:
                    plot_function = PLOT_DICT[plot_list[counter]]
                except KeyError:
                    raise KeyError(f"Invalid plot name: {plot_list[counter]}")
                try:
                    plot_function(ax, xlim, exps, rgn)
                    valid_plots.append(plot_list[counter])
                except Exception:
                    traceback.print_exc()
                    plot_name = plot_list[counter]
                    required_vars = []
                    if plot_name == "net_toa_flux_restom":
                        required_vars = ["RESTOM"]
                    elif plot_name == "net_atm_energy_imbalance":
                        required_vars = ["RESTOM", "RESSURF"]
                    elif plot_name == "global_surface_air_temperature":
                        required_vars = ["TREFHT"]
                    elif plot_name == "toa_radiation":
                        required_vars = ["FSNTOA", "FLUT"]
                    elif plot_name == "net_atm_water_imbalance":
                        required_vars = ["PRECC", "PRECL", "QFLX"]
                    print(
                        f"Failed plot_function for {plot_name}. Check that {required_vars} are available."
                    )
                    invalid_plots.append(plot_name)
                counter += 1
            else:
                try:
                    plot_name = plot_list[counter]
                    plot_generic(ax, xlim, exps, plot_name, rgn)
                    valid_plots.append(plot_name)
                except Exception:
                    traceback.print_exc()
                    print(f"plot_generic failed. Invalid plot={plot_name}")
                    invalid_plots.append(plot_name)
                counter += 1

        fig.tight_layout()
        pdf.savefig(1)
        if num_pages > 1:
            fig.savefig(f"{figstr}_{rgn}_{component}_{page}.png", dpi=150)
        else:
            fig.savefig(f"{figstr}_{rgn}_{component}.png", dpi=150)
        plt.clf()
    pdf.close()


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
    plots_original = param_get_list(parameters[8])
    if parameters[9].lower() == "false":
        atmosphere_only = False
    else:
        atmosphere_only = True
    plots_atm = param_get_list(parameters[10])
    plots_ice = param_get_list(parameters[11])
    plots_lnd = param_get_list(parameters[12])
    plots_ocn = param_get_list(parameters[13])
    vars_original = []
    if "net_toa_flux_restom" or "net_atm_energy_imbalance" in plots_original:
        vars_original.append("RESTOM")
    if "net_atm_energy_imbalance" in plots_original:
        vars_original.append("RESSURF")
    if "global_surface_air_temperature" in plots_original:
        vars_original.append("TREFHT")
    if "toa_radiation" in plots_original:
        vars_original.append("FSNTOA")
        vars_original.append("FLUT")
    if "net_atm_water_imbalance" in plots_original:
        vars_original.append("PRECC")
        vars_original.append("PRECL")
        vars_original.append("QFLX")
    use_atmos = plots_atm or plots_original
    has_original_ocn_plots = (
        ("change_ohc" in plots_original)
        or ("max_moc" in plots_original)
        or ("change_sea_level" in plots_original)
    )
    use_ocn = plots_ocn or (not atmosphere_only and has_original_ocn_plots)
    exps: List[Dict[str, Any]] = [
        {
            "atmos": (
                f"{case_dir}/post/atm/glb/ts/monthly/{ts_num_years}yr/"
                if use_atmos
                else None
            ),
            "ice": (
                f"{case_dir}/post/ice/glb/ts/monthly/{ts_num_years}yr/"
                if plots_ice
                else None
            ),
            "land": (
                f"{case_dir}/post/lnd/glb/ts/monthly/{ts_num_years}yr/"
                if plots_lnd
                else None
            ),
            "ocean": (
                f"{case_dir}/post/ocn/glb/ts/monthly/{ts_num_years}yr/"
                if use_ocn
                else None
            ),
            "moc": (
                f"{case_dir}/post/ocn/glb/ts/monthly/{ts_num_years}yr/"
                if use_ocn
                else None
            ),
            "vol": (
                f"{case_dir}/post/ocn/glb/ts/monthly/{ts_num_years}yr/"
                if use_ocn
                else None
            ),
            "name": experiment_name,
            "yoffset": 0.0,
            "yr": ([year1, year2],),
            "color": f"{color}",
        }
    ]

    valid_vars: List[str] = []
    invalid_vars: List[str] = []

    # Read data
    exp: Dict[str, Any]
    for exp in exps:
        exp["annual"] = {}

        # Use vars_original rather than plots_original,
        # since the plots have different names than the variables
        set_var(exp, "atmos", vars_original, valid_vars, invalid_vars, rgn)
        set_var(exp, "atmos", plots_atm, valid_vars, invalid_vars, rgn)
        set_var(exp, "ice", plots_ice, valid_vars, invalid_vars, rgn)
        set_var(exp, "land", plots_lnd, valid_vars, invalid_vars, rgn)
        set_var(exp, "ocean", plots_ocn, valid_vars, invalid_vars, rgn)

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

    print(
        f"{rgn} region globalAnnual was computed successfully for these variables: {valid_vars}"
    )
    print(
        f"{rgn} region globalAnnual could not be computed for these variables: {invalid_vars}"
    )

    # -----------------------------------------------------------------------------
    # --- Generate plots ---

    xlim = [float(year1), float(year2)]

    valid_plots: List[str] = []
    invalid_plots: List[str] = []

    make_plot_pdfs(
        figstr, rgn, "original", xlim, exps, plots_original, valid_plots, invalid_plots
    )
    make_plot_pdfs(
        figstr, rgn, "atm", xlim, exps, plots_atm, valid_plots, invalid_plots
    )
    make_plot_pdfs(
        figstr, rgn, "ice", xlim, exps, plots_ice, valid_plots, invalid_plots
    )
    make_plot_pdfs(
        figstr, rgn, "lnd", xlim, exps, plots_lnd, valid_plots, invalid_plots
    )
    make_plot_pdfs(
        figstr, rgn, "ocn", xlim, exps, plots_ocn, valid_plots, invalid_plots
    )

    print(f"These {rgn} region plots generated successfully: {valid_plots}")
    print(
        f"These {rgn} region plots could not be generated successfully: {invalid_plots}"
    )


def run_by_region(parameters):
    regions = parameters[14].split(",")
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
