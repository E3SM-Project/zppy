# Script to plot some global atmosphere and ocean time series
import glob
import math
import sys
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
        for iyear in range(np.int(time0[0]), np.int(time0[-1]) + 1):
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

# Net TOA flux (restom)
def plot_net_toa_flux_restom(ax, xlim, exps):
    ax.set_xlim(xlim)
    extreme_values = []
    for exp in exps:
        year = np.array(exp["annual"]["year"]) + exp["yoffset"]
        var = np.array(exp["annual"]["RESTOM"])
        extreme_values.append(np.amax(var))
        extreme_values.append(np.amin(var))
        ax.plot(year, var, lw=1.0, marker=None, c=exp["color"], label=exp["name"])
        if exp["yr"] is not None:
            print(exp["name"])
            for yrs in exp["yr"]:
                add_line(
                    year,
                    var,
                    yrs[0],
                    yrs[1],
                    format="%4.2f",
                    ax=ax,
                    lw=2,
                    color=exp["color"],
                )
                add_trend(
                    year,
                    var,
                    yrs[0],
                    yrs[1],
                    format="%4.2f",
                    ax=ax,
                    lw=2,
                    color=exp["color"],
                )

    ax.set_ylim(get_ylim([-1.5, 1.5], extreme_values))
    ax.axhline(y=0, lw=1, c="0.5")
    ax.set_title("Net TOA flux (restom)")
    ax.set_xlabel("Year")
    ax.set_ylabel("W m-2")
    ax.legend(loc="best")


def plot_global_surface_air_temperature(ax, xlim, exps):
    ax.set_xlim(xlim)

    extreme_values = []
    for exp in exps:
        year = np.array(exp["annual"]["year"]) + exp["yoffset"]
        var = np.array(exp["annual"]["TREFHT"]) - 273.15
        extreme_values.append(np.amax(var))
        extreme_values.append(np.amin(var))
        ax.plot(year, var, lw=1.0, marker=None, c=exp["color"], label=exp["name"])
        if exp["yr"] is not None:
            print(exp["name"])
            for yrs in exp["yr"]:
                add_line(
                    year,
                    var,
                    yrs[0],
                    yrs[1],
                    format="%4.2f",
                    ax=ax,
                    lw=2,
                    color=exp["color"],
                )
                add_trend(
                    year,
                    var,
                    yrs[0],
                    yrs[1],
                    format="%4.2f",
                    ax=ax,
                    lw=2,
                    color=exp["color"],
                )

    ax.set_ylim(get_ylim([13, 15.5], extreme_values))
    ax.set_title("Global surface air temperature")
    ax.set_xlabel("Year")
    ax.set_ylabel("degC")


def plot_toa_radiation(ax, xlim, exps):
    ax.set_xlim(xlim)

    extreme_values = []
    for exp in exps:
        year = np.array(exp["annual"]["year"]) + exp["yoffset"]
        var = np.array(exp["annual"]["FSNTOA"])
        extreme_values.append(np.amax(var))
        extreme_values.append(np.amin(var))
        ax.plot(year, var, lw=1.0, marker=None, c=exp["color"], label=exp["name"])
        var = np.array(exp["annual"]["FLUT"])
        ax.plot(year, var, lw=1.0, marker=None, ls=":", c=exp["color"])

    ax.set_ylim(get_ylim([235, 245], extreme_values))
    ax.set_title("TOA radiation: SW (solid), LW (dashed)")
    ax.set_xlabel("Year")
    ax.set_ylabel("W m-2")


def plot_net_atm_energy_imbalance(ax, xlim, exps):
    ax.set_xlim(xlim)

    extreme_values = []
    for exp in exps:
        year = np.array(exp["annual"]["year"]) + exp["yoffset"]
        var = np.array(exp["annual"]["RESTOM"]) - np.array(exp["annual"]["RESSURF"])
        extreme_values.append(np.amax(var))
        extreme_values.append(np.amin(var))
        ax.plot(year, var, lw=1.0, marker=None, c=exp["color"], label=exp["name"])
        if exp["yr"] is not None:
            print(exp["name"])
            for yrs in exp["yr"]:
                add_line(
                    year,
                    var,
                    yrs[0],
                    yrs[1],
                    format="%4.2f",
                    ax=ax,
                    lw=2,
                    color=exp["color"],
                )

    ax.set_ylim(get_ylim([-0.3, 0.3], extreme_values))
    ax.set_title("Net atm energy imbalance (restom-ressurf)")
    ax.set_xlabel("Year")
    ax.set_ylabel("W m-2")


def plot_change_ohc(ax, xlim, exps):
    ax.set_xlim(xlim)

    extreme_values = []
    for exp in exps:
        if exp["ocean"] is not None:
            year = np.array(exp["annual"]["year"]) + exp["yoffset"]
            var = np.array(exp["annual"]["ohc"])
            extreme_values.append(np.amax(var))
            extreme_values.append(np.amin(var))
            ax.plot(year, var, lw=1.5, marker=None, c=exp["color"], label=exp["name"])
            for yrs in exp["yr"]:
                add_trend(
                    year,
                    var,
                    yrs[0],
                    yrs[1],
                    format="%4.2f",
                    ax=ax,
                    lw=3,
                    color=exp["color"],
                    ohc=True,
                )

    ax.set_ylim(get_ylim([-0.3e24, 0.9e24], extreme_values))
    ax.axhline(y=0, lw=1, c="0.5")
    ax.set_title("Change in ocean heat content")
    ax.set_xlabel("Year")
    ax.set_ylabel("J")
    ax.legend(loc="best")


def plot_max_moc(ax, xlim, exps):
    ax.set_xlim(xlim)

    extreme_values = []
    for exp in exps:
        if exp["moc"] is not None:
            [year_moc, var] = getmoc(exp["moc"])
            ax.plot(
                year_moc, var, lw=1.5, marker=None, c=exp["color"], label=exp["name"]
            )
            extreme_values.append(np.amax(var))
            extreme_values.append(np.amin(var))
            for yrs in exp["yr"]:
                add_trend(
                    year_moc,
                    var,
                    yrs[0],
                    yrs[1],
                    format="%4.2f",
                    ax=ax,
                    lw=3,
                    color=exp["color"],
                    verbose=True,
                )

    ax.set_ylim(get_ylim([4, 22], extreme_values))
    ax.axhline(y=10, lw=1, c="0.5")
    ax.set_title("Max MOC Atlantic streamfunction at 26.5N")
    ax.set_xlabel("Year")
    ax.set_ylabel("Sv")
    ax.legend(loc="best")


def plot_change_sea_level(ax, xlim, exps):
    ax.set_xlim(xlim)

    extreme_values = []
    for exp in exps:
        if exp["vol"] is not None:
            year_vol = np.array(exp["annual"]["year"]) + exp["yoffset"]
            var = (
                1e3
                * np.array(exp["annual"]["volume"])
                / (4.0 * math.pi * (6371229.0) ** 2 * 0.7)
            )
            extreme_values.append(np.amax(var))
            extreme_values.append(np.amin(var))
            ax.plot(
                year_vol, var, lw=1.5, marker=None, c=exp["color"], label=exp["name"]
            )
            for yrs in exp["yr"]:
                add_trend(
                    year_vol,
                    var,
                    yrs[0],
                    yrs[1],
                    format="%5.3f",
                    ax=ax,
                    lw=3,
                    color=exp["color"],
                    verbose=True,
                    vol=True,
                )

    ax.set_ylim(get_ylim([4, 22], extreme_values))
    ax.set_title("Change in sea level")
    ax.set_xlabel("Year")
    ax.set_ylabel("mm")
    ax.legend(loc="best")


def plot_net_atm_water_imbalance(ax, xlim, exps):
    ax.set_xlim(xlim)

    extreme_values = []
    for exp in exps:
        year = np.array(exp["annual"]["year"]) + exp["yoffset"]
        var = (
            365
            * 86400
            * (
                np.array(exp["annual"]["QFLX"])
                - 1e3
                * (np.array(exp["annual"]["PRECC"]) + np.array(exp["annual"]["PRECL"]))
            )
        )
        extreme_values.append(np.amax(var))
        extreme_values.append(np.amin(var))
        ax.plot(year, var, lw=1.0, marker=None, c=exp["color"], label=exp["name"])
        if exp["yr"] is not None:
            print(exp["name"])
            for yrs in exp["yr"]:
                add_line(
                    year,
                    var,
                    yrs[0],
                    yrs[1],
                    format="%5.4f",
                    ax=ax,
                    lw=2,
                    color=exp["color"],
                )

    ax.set_ylim(get_ylim([-1, 1], extreme_values))
    ax.set_title("Net atm water imbalance (evap-prec)")
    ax.set_xlabel("Year")
    ax.set_ylabel("mm yr-1")


PLOT_DICT = {
    "net_toa_flux_restom": plot_net_toa_flux_restom,
    "global_surface_air_temperature": plot_global_surface_air_temperature,
    "toa_radiation": plot_toa_radiation,
    "net_atm_energy_imbalance": plot_net_atm_energy_imbalance,
    "change_ohc": plot_change_ohc,
    "max_moc": plot_max_moc,
    "change_sea_level": plot_change_sea_level,
    "net_atm_water_imbalance": plot_net_atm_water_imbalance,
}


# -----------------------------------------------------------------------------
def run(parameters):
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
    if parameters[8].lower() == "false":
        atmosphere_only = False
    else:
        atmosphere_only = True
    plot_list = parameters[9].split(",")
    exps = [
        {
            "atmos": "{}/post/atm/glb/ts/monthly/{}yr/glb.xml".format(
                case_dir, ts_num_years
            ),
            "ocean": None
            if atmosphere_only
            else "{}/post/ocn/glb/ts/monthly/{}yr/glb.xml".format(
                case_dir, ts_num_years
            ),
            "moc": None
            if atmosphere_only
            else "{}/post/ocn/glb/ts/monthly/{}yr/".format(case_dir, ts_num_years),
            "vol": None
            if atmosphere_only
            else "{}/post/ocn/glb/ts/monthly/{}yr/glb.xml".format(
                case_dir, ts_num_years
            ),
            "name": experiment_name,
            "yoffset": 0.0,
            "yr": ([year1, year2],),
            "color": f"{color}",
        }
    ]

    # Variables to extract
    vars = ["RESTOM", "RESSURF", "TREFHT", "FSNTOA", "FLUT", "PRECC", "PRECL", "QFLX"]

    # Read data
    exp: Any
    for exp in exps:
        print(exp["atmos"])
        ts = TS(exp["atmos"])
        exp["annual"] = {}
        for var in vars:
            print(var)
            v = ts.globalAnnual(var)
            exp["annual"][var] = v
            if "year" not in exp["annual"]:
                time = v.getTime()
                exp["annual"]["year"] = [x.year for x in time.asComponentTime()]
        del ts

        # Optionally read ohc
        if exp["ocean"] is not None:
            ts = TS(exp["ocean"])
            exp["annual"]["ohc"] = ts.globalAnnual("ohc")
            # annomalies with respect to first year
            exp["annual"]["ohc"][:] = exp["annual"]["ohc"][:] - exp["annual"]["ohc"][0]

        if exp["vol"] is not None:
            ts = TS(exp["vol"])
            exp["annual"]["volume"] = ts.globalAnnual("volume")
            # annomalies with respect to first year
            exp["annual"]["volume"][:] = (
                exp["annual"]["volume"][:] - exp["annual"]["volume"][0]
            )

    # -----------------------------------------------------------------------------
    # --- Generate plots ---

    xlim = [float(year1), float(year2)]

    num_plots = len(plot_list)
    nrows = 4
    ncols = 2
    plots_per_page = nrows * ncols
    num_pages = math.ceil(num_plots / plots_per_page)

    i = 0
    # https://stackoverflow.com/questions/58738992/save-multiple-figures-with-subplots-into-a-pdf-with-multiple-pages
    pdf = matplotlib.backends.backend_pdf.PdfPages(f"{figstr}.pdf")
    for page in range(num_pages):
        fig = plt.figure(1, figsize=[13.5, 16.5])
        for j in range(plots_per_page):
            if i < num_plots:
                ax = plt.subplot(nrows, ncols, j + 1)
                try:
                    PLOT_DICT[plot_list[i]](ax, xlim, exps)
                except KeyError:
                    raise KeyError(f"Invalid plot name: {plot_list[i]}")
                i += 1

        fig.tight_layout()
        pdf.savefig(1)
        if num_pages > 1:
            fig.savefig(figstr + f"_{page}.png", dpi=150)
        else:
            fig.savefig(figstr + ".png", dpi=150)
        plt.clf()
    pdf.close()


if __name__ == "__main__":
    run(sys.argv)
