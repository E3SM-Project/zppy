# Script to generate global time series plots
import csv
import distutils.dir_util
import glob
import math
import os
import stat
import sys
import traceback
from enum import Enum
from typing import Any, Dict, List, Tuple

import cftime
import matplotlib as mpl
import matplotlib.backends.backend_pdf
import matplotlib.pyplot as plt
import numpy as np
import xarray
import xcdat
from bs4 import BeautifulSoup
from netCDF4 import Dataset
from output_viewer.build import build_page, build_viewer
from output_viewer.index import (
    OutputFile,
    OutputGroup,
    OutputIndex,
    OutputPage,
    OutputRow,
)
from output_viewer.utils import rechmod

mpl.use("Agg")


# Useful classes and their helper functions ###################################
def param_get_list(param_value: str) -> List[str]:
    if param_value == "None":
        return []
    else:
        return param_value.split(",")


def get_region(rgn: str) -> str:
    if rgn.lower() in ["glb", "global"]:
        rgn = "glb"
    elif rgn.lower() in ["n", "north", "northern"]:
        rgn = "n"
    elif rgn.lower() in ["s", "south", "southern"]:
        rgn = "s"
    else:
        raise ValueError(f"Invalid rgn={rgn}")
    return rgn


class Parameters(object):
    def __init__(self, parameters):
        self.case_dir: str = parameters[1]
        self.experiment_name: str = parameters[2]
        self.figstr: str = parameters[3]
        self.year1: int = int(parameters[4])
        self.year2: int = int(parameters[5])
        self.color: str = parameters[6]
        self.ts_num_years_str: str = parameters[7]
        self.plots_original: List[str] = param_get_list(parameters[8])
        self.atmosphere_only: bool = (
            False if (parameters[9].lower() == "false") else True
        )
        self.plots_atm: List[str] = param_get_list(parameters[10])
        self.plots_ice: List[str] = param_get_list(parameters[11])
        self.plots_lnd: List[str] = param_get_list(parameters[12])
        self.plots_ocn: List[str] = param_get_list(parameters[13])
        self.nrows: int = int(parameters[14])
        self.ncols: int = int(parameters[15])
        # These regions are used often as strings,
        # so making an Enum Region={GLOBAL, NORTH, SOUTH} would be limiting.
        self.regions: List[str] = list(
            map(lambda rgn: get_region(rgn), parameters[16].split(","))
        )


class Metric(Enum):
    AVERAGE = 1
    TOTAL = 2


class Variable(object):
    def __init__(
        self,
        variable_name,
        metric=Metric.AVERAGE,
        scale_factor=1.0,
        original_units="",
        final_units="",
        group="",
        long_name="",
    ):
        # The name of the EAM/ELM/etc. variable on the monthly h0 history file
        self.variable_name: str = variable_name

        # These fields are used for computation
        # Global average over land area or global total
        self.metric: Metric = metric
        # The factor that should convert from original_units to final_units, after standard processing with nco
        self.scale_factor: float = scale_factor
        # Test string for the units as given on the history file (included here for possible testing)
        self.original_units: str = original_units
        # The units that should be reported in time series plots, based on metric and scale_factor
        self.final_units: str = final_units

        # These fields are used for plotting
        # A name used to cluster variables together, to be separated in groups within the output web pages
        self.group: str = group
        # Descriptive text to add to the plot page to help users identify the variable
        self.long_name: str = long_name


def get_vars_original(plots_original: List[str]) -> List[Variable]:
    vars_original: List[Variable] = []
    if ("net_toa_flux_restom" in plots_original) or (
        "net_atm_energy_imbalance" in plots_original
    ):
        vars_original.append(Variable("RESTOM"))
    if "net_atm_energy_imbalance" in plots_original:
        vars_original.append(Variable("RESSURF"))
    if "global_surface_air_temperature" in plots_original:
        vars_original.append(Variable("TREFHT"))
    if "toa_radiation" in plots_original:
        vars_original.append(Variable("FSNTOA"))
        vars_original.append(Variable("FLUT"))
    if "net_atm_water_imbalance" in plots_original:
        vars_original.append(Variable("PRECC"))
        vars_original.append(Variable("PRECL"))
        vars_original.append(Variable("QFLX"))
    return vars_original


def land_csv_row_to_var(csv_row: List[str]) -> Variable:
    # “A” or “T” for global average over land area or global total, respectively
    metric: Metric
    if csv_row[1] == "A":
        metric = Metric.AVERAGE
    elif csv_row[1] == "T":
        metric = Metric.TOTAL
    else:
        raise ValueError(f"Invalid metric={csv_row[1]}")
    return Variable(
        variable_name=csv_row[0],
        metric=metric,
        scale_factor=float(csv_row[2]),
        original_units=csv_row[3],
        final_units=csv_row[4],
        group=csv_row[5],
        long_name=csv_row[6],
    )


def construct_land_variables(requested_vars: List[str]) -> List[Variable]:
    var_list: List[Variable] = []
    header = True
    # If this file is being run stand-alone, then
    # it will search the directory above the git directory
    with open("zppy_land_fields.csv", newline="") as csv_file:
        print("In File")
        var_reader = csv.reader(csv_file)
        for row in var_reader:
            print(f"row={row}")
            # Skip the header row
            if header:
                header = False
            else:
                # If set to "all" then we want all variables.
                # Design note: we can't simply run all variables if requested_vars is empty because
                # that would actually mean the user doesn't want to make *any* land plots.
                if (requested_vars == ["all"]) or (row[0] in requested_vars):
                    row_elements_strip_whitespace: List[str] = list(
                        map(lambda x: x.strip(), row)
                    )
                    var_list.append(land_csv_row_to_var(row_elements_strip_whitespace))
    return var_list


def construct_generic_variables(requested_vars: List[str]) -> List[Variable]:
    var_list: List[Variable] = []
    for var_name in requested_vars:
        var_list.append(Variable(var_name))
    return var_list


class RequestedVariables(object):
    def __init__(self, parameters: Parameters):
        self.vars_original: List[Variable] = get_vars_original(
            parameters.plots_original
        )
        self.vars_land: List[Variable] = construct_land_variables(parameters.plots_lnd)
        self.vars_atm: List[Variable] = construct_generic_variables(
            parameters.plots_atm
        )
        self.vars_ice: List[Variable] = construct_generic_variables(
            parameters.plots_ice
        )
        self.vars_ocn: List[Variable] = construct_generic_variables(
            parameters.plots_ocn
        )


class VariableGroup(object):
    def __init__(self, name: str, variables: List[Variable]):
        self.group_name = name
        self.variables = variables


class TS(object):
    def __init__(self, directory):

        self.directory: str = directory

        # `directory` will be of the form `{case_dir}/post/<component>/glb/ts/monthly/{ts_num_years_str}yr/`
        self.f: xarray.core.dataset.Dataset = xcdat.open_mfdataset(
            f"{directory}*.nc", center_times=True
        )

    def __del__(self):

        self.f.close()

    def globalAnnualHelper(
        self,
        var: str,
        metric: Metric,
        scale_factor: float,
        original_units: str,
        final_units: str,
    ) -> Tuple[xarray.core.dataarray.DataArray, str]:

        data_array: xarray.core.dataarray.DataArray
        units: str = ""

        # Constants, from AMWG diagnostics
        Lv = 2.501e6
        Lf = 3.337e5

        # Is this a derived variable?
        if var == "RESTOM":
            FSNT, _ = self.globalAnnualHelper(
                "FSNT", metric, scale_factor, original_units, final_units
            )
            FLNT, _ = self.globalAnnualHelper(
                "FLNT", metric, scale_factor, original_units, final_units
            )
            data_array = FSNT - FLNT
        elif var == "RESTOA":
            print("NOT READY")
            FSNTOA, _ = self.globalAnnualHelper(
                "FSNTOA", metric, scale_factor, original_units, final_units
            )
            FLUT, _ = self.globalAnnualHelper(
                "FLUT", metric, scale_factor, original_units, final_units
            )
            data_array = FSNTOA - FLUT
        elif var == "LHFLX":
            QFLX, _ = self.globalAnnualHelper(
                "QFLX", metric, scale_factor, original_units, final_units
            )
            PRECC, _ = self.globalAnnualHelper(
                "PRECC", metric, scale_factor, original_units, final_units
            )
            PRECL, _ = self.globalAnnualHelper(
                "PRECL", metric, scale_factor, original_units, final_units
            )
            PRECSC, _ = self.globalAnnualHelper(
                "PRECSC", metric, scale_factor, original_units, final_units
            )
            PRECSL, _ = self.globalAnnualHelper(
                "PRECSL", metric, scale_factor, original_units, final_units
            )
            data_array = (Lv + Lf) * QFLX - Lf * 1.0e3 * (
                PRECC + PRECL - PRECSC - PRECSL
            )
        elif var == "RESSURF":
            FSNS, _ = self.globalAnnualHelper(
                "FSNS", metric, scale_factor, original_units, final_units
            )
            FLNS, _ = self.globalAnnualHelper(
                "FLNS", metric, scale_factor, original_units, final_units
            )
            SHFLX, _ = self.globalAnnualHelper(
                "SHFLX", metric, scale_factor, original_units, final_units
            )
            LHFLX, _ = self.globalAnnualHelper(
                "LHFLX", metric, scale_factor, original_units, final_units
            )
            data_array = FSNS - FLNS - SHFLX - LHFLX
        elif var == "PREC":
            PRECC, _ = self.globalAnnualHelper(
                "PRECC", metric, scale_factor, original_units, final_units
            )
            PRECL, _ = self.globalAnnualHelper(
                "PRECL", metric, scale_factor, original_units, final_units
            )
            data_array = 1.0e3 * (PRECC + PRECL)
        else:
            # Non-derived variables
            if (metric == Metric.AVERAGE) or (metric == Metric.TOTAL):
                annual_average_dataset_for_var: xarray.core.dataset.Dataset = (
                    self.f.temporal.group_average(var, "year")
                )
                data_array = annual_average_dataset_for_var.data_vars[var]
            # elif metric == Metric.TOTAL:
            #     # TODO: Implement this!
            #     raise NotImplementedError()
            else:
                # This shouldn't be possible
                raise ValueError(f"Invalid Enum option for metric={metric}")
            units = data_array.units
            # `units` will be "1" if it's a dimensionless quantity
            if (units != "1") and (original_units != "") and original_units != units:
                raise ValueError(
                    f"Units don't match up: Have {units} but expected {original_units}. This renders the supplied scale_factor ({scale_factor}) unusable."
                )
            data_array *= scale_factor
            units = final_units
        return data_array, units

    def globalAnnual(
        self, var: Variable
    ) -> Tuple[xarray.core.dataarray.DataArray, str]:
        return self.globalAnnualHelper(
            var.variable_name,
            var.metric,
            var.scale_factor,
            var.original_units,
            var.final_units,
        )


# Copied from e3sm_diags
class OutputViewer(object):
    def __init__(self, path=".", index_name="Results"):
        self.path = os.path.abspath(path)
        self.index = OutputIndex(index_name)
        self.cache = {}  # dict of { OutputPage: { OutputGroup: [OutputRow] } }
        self.page = None
        self.group = None
        self.row = None

    def add_page(self, page_title, *args, **kwargs):
        """Add a page to the viewer's index"""
        self.page = OutputPage(page_title, *args, **kwargs)
        self.cache[self.page] = {}
        self.index.addPage(self.page)

    def set_page(self, page_title):
        """Sets the page with the title name as the current page"""
        for output_page in self.cache:
            if page_title == output_page.title:
                self.page = output_page
                return
        raise RuntimeError("There is no page titled: %s" % page_title)

    def add_group(self, group_name):
        """Add a group to the current page"""
        if self.page is None:
            raise RuntimeError("You must first insert a page with add_page()")
        self.group = OutputGroup(group_name)
        if self.group not in self.cache[self.page]:
            self.cache[self.page][self.group] = []  # group doesn't have any rows yet
        self.page.addGroup(self.group)

    def set_group(self, group_name):
        """Sets the group with the title name as the current group"""
        for output_group in self.cache[self.page]:
            if group_name == output_group.title:
                self.group = output_group
                return
        raise RuntimeError("There is no group titled: %s" % group_name)

    def add_row(self, row_name):
        """Add a row with the title name to the current group"""
        if self.group is None:
            raise RuntimeError("You must first insert a group with add_group()")
        self.row = OutputRow(row_name, [])
        if self.row not in self.cache[self.page][self.group]:
            self.cache[self.page][self.group].append(self.row)
        self.page.addRow(self.row, len(self.page.groups) - 1)  # type: ignore

    def set_row(self, row_name):
        """Sets the row with the title name as the current row"""
        for output_row in self.cache[self.page][self.group]:
            if row_name == output_row.title:
                self.row = output_row
                return
        raise RuntimeError("There is no row titled: %s" % row_name)

    def add_cols(self, cols):
        """Add multiple string cols to the current row"""
        self.row.columns.append(cols)  # type: ignore

    def add_col(self, col, is_file=False, **kwargs):
        """Add a single col to the current row. Set is_file to True if the col is a file path."""
        if is_file:
            self.row.columns.append(OutputFile(col, **kwargs))  # type: ignore
        else:
            self.row.columns.append(col)  # type: ignore

    def generate_page(self) -> str:
        """
        Generate and return the location of the current HTML page.
        """
        self.index.toJSON(os.path.join(self.path, "index.json"))

        default_mask = stat.S_IMODE(os.stat(self.path).st_mode)
        rechmod(self.path, default_mask)

        if os.access(self.path, os.W_OK):
            default_mask = stat.S_IMODE(
                os.stat(self.path).st_mode
            )  # mode of files to be included
            url = build_page(
                self.page,
                os.path.join(self.path, "index.json"),
                default_mask=default_mask,
            )
            return url

        raise RuntimeError("Error geneating the page.")

    def generate_viewer(self):
        """Generate the webpage"""
        self.index.toJSON(os.path.join(self.path, "index.json"))

        default_mask = stat.S_IMODE(os.stat(self.path).st_mode)
        rechmod(self.path, default_mask)

        if os.access(self.path, os.W_OK):
            default_mask = stat.S_IMODE(
                os.stat(self.path).st_mode
            )  # mode of files to be included
            build_viewer(
                os.path.join(self.path, "index.json"),
                diag_name="Global Time Series",
                default_mask=default_mask,
            )


# Setup #######################################################################


def get_data_dir(parameters: Parameters, component: str, conditional: bool) -> str:
    return (
        f"{parameters.case_dir}/post/{component}/glb/ts/monthly/{parameters.ts_num_years_str}yr/"
        if conditional
        else ""
    )


def get_exps(parameters: Parameters) -> List[Dict[str, Any]]:
    # Experiments
    use_atmos: bool = (parameters.plots_atm != []) or (parameters.plots_original != [])
    # Use set intersection: check if any of these 3 plots were requested
    set_intersection: set = set(["change_ohc", "max_moc", "change_sea_level"]) & set(
        parameters.plots_original
    )
    has_original_ocn_plots: bool = set_intersection != set()
    use_ocn: bool = (parameters.plots_ocn != []) or (
        (not parameters.atmosphere_only) and has_original_ocn_plots
    )
    ocean_dir = get_data_dir(parameters, "ocn", use_ocn)
    exps: List[Dict[str, Any]] = [
        {
            "atmos": get_data_dir(parameters, "atm", use_atmos),
            "ice": get_data_dir(parameters, "ice", parameters.plots_ice != []),
            "land": get_data_dir(parameters, "lnd", parameters.plots_lnd != []),
            "ocean": ocean_dir,
            "moc": ocean_dir,
            "vol": ocean_dir,
            "name": parameters.experiment_name,
            "yoffset": 0.0,
            "yr": ([parameters.year1, parameters.year2],),
            "color": f"{parameters.color}",
        }
    ]
    return exps


def set_var(
    exp: Dict[str, Any],
    exp_key: str,
    var_list: List[Variable],
    valid_vars: List[str],
    invalid_vars: List[str],
    rgn: str,
) -> None:
    if exp[exp_key] != "":
        ts: TS = TS(exp[exp_key])
        for var in var_list:
            var_str: str = var.variable_name
            try:
                data_array: xarray.core.dataarray.DataArray
                units: str
                data_array, units = ts.globalAnnual(var)
                valid_vars.append(str(var_str))
            except Exception as e:
                print(e)
                print(f"globalAnnual failed for {var_str}")
                invalid_vars.append(str(var_str))
                continue
            if data_array.sizes["rgn"] > 1:
                # number of years x 3 regions = data_array.shape
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
                data_array = data_array.isel(rgn=n)  # Just use nth region
            elif rgn != "glb":
                # data_array only has one dimension -- glb.
                # Therefore it is not possible to get n or s plots.
                raise RuntimeError(
                    f"var={var_str} only has global data. Cannot process rgn={rgn}"
                )
            exp["annual"][var_str] = (data_array, units)
            if "year" not in exp["annual"]:
                years: np.ndarray[cftime.DatetimeNoLeap] = data_array.coords[
                    "time"
                ].values
                exp["annual"]["year"] = [x.year for x in years]
        del ts


def process_data(
    parameters: Parameters, requested_variables: RequestedVariables, rgn: str
) -> List[Dict[str, Any]]:
    exps: List[Dict[str, Any]] = get_exps(parameters)
    valid_vars: List[str] = []
    invalid_vars: List[str] = []
    exp: Dict[str, Any]
    for exp in exps:
        exp["annual"] = {}

        set_var(
            exp,
            "atmos",
            requested_variables.vars_original,
            valid_vars,
            invalid_vars,
            rgn,
        )
        set_var(
            exp, "atmos", requested_variables.vars_atm, valid_vars, invalid_vars, rgn
        )
        set_var(exp, "ice", requested_variables.vars_ice, valid_vars, invalid_vars, rgn)
        set_var(
            exp, "land", requested_variables.vars_land, valid_vars, invalid_vars, rgn
        )
        set_var(
            exp, "ocean", requested_variables.vars_ocn, valid_vars, invalid_vars, rgn
        )

        # Optionally read ohc
        if exp["ocean"] != "":
            ts = TS(exp["ocean"])
            exp["annual"]["ohc"], _ = ts.globalAnnual(Variable("ohc"))
            # anomalies with respect to first year
            exp["annual"]["ohc"][:] = exp["annual"]["ohc"][:] - exp["annual"]["ohc"][0]

        if exp["vol"] != "":
            ts = TS(exp["vol"])
            exp["annual"]["volume"], _ = ts.globalAnnual(Variable("volume"))
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
    return exps


# Plotting ####################################################################


def get_variable_groups(variables: List[Variable]) -> List[VariableGroup]:
    group_names: List[str] = []
    groups: List[VariableGroup] = []
    for v in variables:
        g: str = v.group
        if g not in group_names:
            # A new group!
            group_names.append(g)
            groups.append(VariableGroup(g, [v]))
        else:
            # Add a new variable to this existing group
            for group in groups:
                if g == group.group_name:
                    group.variables.append(v)
    return groups


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
        if param_dict["check_exp_ocean"] and (exp["ocean"] == ""):
            continue
        # Relevant to "Plot 7: plot_change_sea_level"
        # This must be checked before plot 6,
        # otherwise, `param_dict["var"]` will be run,
        # but `exp["annual"]["volume"]` won't exist.
        if param_dict["check_exp_vol"] and (exp["vol"] == ""):
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


# FIXME: C901 'make_plot_pdfs' is too complex (20)
def make_plot_pdfs(  # noqa: C901
    parameters: Parameters,
    rgn,
    component,
    xlim,
    exps,
    plot_list,
    valid_plots,
    invalid_plots,
):
    num_plots = len(plot_list)
    if num_plots == 0:
        return
    plots_per_page = parameters.nrows * parameters.ncols
    num_pages = math.ceil(num_plots / plots_per_page)

    counter = 0
    # https://stackoverflow.com/questions/58738992/save-multiple-figures-with-subplots-into-a-pdf-with-multiple-pages
    pdf = matplotlib.backends.backend_pdf.PdfPages(
        f"{parameters.figstr}_{rgn}_{component}.pdf"
    )
    for page in range(num_pages):
        if plots_per_page == 1:
            fig = plt.figure(1, figsize=[13.5 / 2, 16.5 / 4])
        else:
            fig = plt.figure(1, figsize=[13.5, 16.5])
        fig.suptitle(f"{parameters.figstr}_{rgn}_{component}")
        for j in range(plots_per_page):
            # The final page doesn't need to be filled out with plots.
            if counter >= num_plots:
                break
            ax = plt.subplot(parameters.nrows, parameters.ncols, j + 1)
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
        if plots_per_page == 1:
            fig.savefig(
                f"{parameters.figstr}_{rgn}_{component}_{plot_name}.png", dpi=150
            )
        elif num_pages > 1:
            fig.savefig(f"{parameters.figstr}_{rgn}_{component}_{page}.png", dpi=150)
        else:
            fig.savefig(f"{parameters.figstr}_{rgn}_{component}.png", dpi=150)
        plt.clf()
    pdf.close()


# Run coupled_global ##########################################################
# -----------------------------------------------------------------------------
def run(parameters: Parameters, requested_variables: RequestedVariables, rgn: str):
    # Experiments
    exps: List[Dict[str, Any]] = process_data(parameters, requested_variables, rgn)

    xlim: List[float] = [float(parameters.year1), float(parameters.year2)]

    valid_plots: List[str] = []
    invalid_plots: List[str] = []

    # Use list of tuples rather than a dict, to keep order
    mapping: List[Tuple[str, List[str]]] = [
        ("original", parameters.plots_original),
        ("atm", parameters.plots_atm),
        ("ice", parameters.plots_ice),
        ("lnd", parameters.plots_lnd),
        ("ocn", parameters.plots_ocn),
    ]
    for component, plot_list in mapping:
        make_plot_pdfs(
            parameters,
            rgn,
            component,
            xlim,
            exps,
            plot_list,
            valid_plots,
            invalid_plots,
        )
    print(f"These {rgn} region plots generated successfully: {valid_plots}")
    print(
        f"These {rgn} regions plots could not be generated successfully: {invalid_plots}"
    )


def get_vars(requested_variables: RequestedVariables, component: str) -> List[Variable]:
    vars: List[Variable]
    if component == "original":
        vars = requested_variables.vars_original
    elif component == "atm":
        vars = requested_variables.vars_atm
    elif component == "ice":
        vars = requested_variables.vars_ice
    elif component == "lnd":
        vars = requested_variables.vars_land
    elif component == "ocn":
        vars = requested_variables.vars_ocn
    else:
        raise ValueError(f"Invalid component={component}")
    return vars


def create_viewer(parameters: Parameters, vars: List[Variable], component: str) -> str:
    viewer = OutputViewer(path=".")
    viewer.add_page("Table", parameters.regions)
    groups: List[VariableGroup] = get_variable_groups(vars)
    for group in groups:
        # Only groups that have at least one variable will be returned by `get_variable_groups`
        # So, we know this group will be non-empty and should therefore be added to the viewer.
        viewer.add_group(group.group_name)
        for var in group.variables:
            plot_name: str = var.variable_name
            row_title: str
            if var.long_name != "":
                row_title = f"{plot_name}: {var.long_name}"
            else:
                row_title = plot_name
            viewer.add_row(row_title)
            for rgn in parameters.regions:
                # v3.LR.historical_0051_glb_lnd_SOIL4C.png
                # viewer/c-state/glb_lnd_soil4c.html
                viewer.add_col(
                    f"{parameters.figstr}_{rgn}_{component}_{plot_name}.png",
                    is_file=True,
                    title=f"{rgn}_{component}_{plot_name}",
                )

    url = viewer.generate_page()
    viewer.generate_viewer()
    # Copy the contents of `table` into the `viewer` directory
    # (which initially only has `css` and `js` subdirectories)
    # Because `viewer` already exists,
    # `shutil.copytree` will not work.
    distutils.dir_util.copy_tree("table", "viewer")
    print(
        os.getcwd()
    )  # /lcrc/group/e3sm/ac.forsyth2/zppy_min_case_global_time_series_viewers_output/test-pr616-20241022v2/v3.LR.historical_0051/post/scripts/global_time_series_1985-1995_dir
    # shutil.rmtree("table")
    # new_url = f"viewer_{component}"
    # # shutil.move("viewer", new_url)
    # distutils.dir_util.copy_tree("viewer", new_url)
    return url


# Copied from E3SM Diags and modified
def create_viewer_index(
    root_dir: str, title_and_url_list: List[Tuple[str, str]]
) -> str:
    """
    Creates the index page in root_dir which
    joins the individual viewers.

    Each tuple is on its own row.
    """

    def insert_data_in_row(row_obj, name, url):
        """
        Given a row object, insert the name and url.
        """
        td = soup.new_tag("td")
        a = soup.new_tag("a")
        a["href"] = url
        a.string = name
        td.append(a)
        row_obj.append(td)

    install_path = ""  # TODO: figure this out
    path = os.path.join(install_path, "viewer", "index_template.html")
    output = os.path.join(root_dir, "index.html")

    soup = BeautifulSoup(open(path), "lxml")

    # If no one changes it, the template only has
    # one element in the find command below.
    table = soup.find_all("table", {"class": "table"})[0]

    # Adding the title.
    tr = soup.new_tag("tr")
    th = soup.new_tag("th")
    th.string = "Output Sets"
    tr.append(th)

    # Adding each of the rows.
    for row in title_and_url_list:
        tr = soup.new_tag("tr")

        if isinstance(row, list):
            for elt in row:
                name, url = elt
                insert_data_in_row(tr, name, url)
        else:
            name, url = row
            insert_data_in_row(tr, name, url)

        table.append(tr)

    html = soup.prettify("utf-8")

    with open(output, "wb") as f:
        f.write(html)

    return output


def run_by_region(command_line_arguments):
    parameters: Parameters = Parameters(command_line_arguments)
    requested_variables = RequestedVariables(parameters)
    for rgn in parameters.regions:
        run(parameters, requested_variables, rgn)
    plots_per_page = parameters.nrows * parameters.ncols
    # TODO: Is this how we want to determine when to make a viewer or should we have a `make_viewer` parameter in the cfg?
    if plots_per_page == 1:
        # In this case, we don't want the summary PDF.
        # Rather, we want to construct a viewer similar to E3SM Diags.
        # TODO: determine directory paths for each viewer
        # TODO: include "original"?
        # for component in ["original", "atm", "ice", "lnd", "ocn"]:
        title_and_url_list: List[Tuple[str, str]] = []
        for component in ["lnd"]:
            vars = get_vars(requested_variables, component)
            url = create_viewer(parameters, vars, component)
            print(url)
            title_and_url_list.append((component, url))
        # index_url: str = create_viewer_index(parameters.case_dir, title_and_url_list)
        # print(f"Viewer index URL: {index_url}")


if __name__ == "__main__":
    run_by_region(sys.argv)
