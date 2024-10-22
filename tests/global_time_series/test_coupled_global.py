import unittest
from typing import Any, Dict, List

from zppy.templates.coupled_global import (
    Metric,
    Parameters,
    Variable,
    VariableGroup,
    construct_generic_variables,
    get_data_dir,
    get_exps,
    get_region,
    get_variable_groups,
    get_vars_original,
    get_ylim,
    land_csv_row_to_var,
    param_get_list,
)


# Helper function
def get_var_names(vars: List[Variable]):
    return list(map(lambda v: v.variable_name, vars))


# Run this test suite in the environment the global_time_series task runs in.
# I.e., whatever `environment_commands` is set to for `[global_time_series]`
# NOT the zppy dev environment.
# Run: python -u -m unittest tests/global_time_series/test_coupled_global.py
class TestCoupledGlobal(unittest.TestCase):

    # Useful classes and their helper functions ###############################
    def test_param_get_list(self):
        self.assertEqual(param_get_list("None"), [])

        self.assertEqual(param_get_list("a"), ["a"])
        self.assertEqual(param_get_list("a,b,c"), ["a", "b", "c"])

        self.assertEqual(param_get_list(""), [""])
        self.assertEqual(param_get_list("a,"), ["a", ""])
        self.assertEqual(param_get_list("a,b,c,"), ["a", "b", "c", ""])

    def test_get_region(self):
        self.assertEqual(get_region("glb"), "glb")
        self.assertEqual(get_region("global"), "glb")
        self.assertEqual(get_region("GLB"), "glb")
        self.assertEqual(get_region("Global"), "glb")

        self.assertEqual(get_region("n"), "n")
        self.assertEqual(get_region("north"), "n")
        self.assertEqual(get_region("northern"), "n")
        self.assertEqual(get_region("N"), "n")
        self.assertEqual(get_region("North"), "n")
        self.assertEqual(get_region("Northern"), "n")

        self.assertEqual(get_region("s"), "s")
        self.assertEqual(get_region("south"), "s")
        self.assertEqual(get_region("southern"), "s")
        self.assertEqual(get_region("S"), "s")
        self.assertEqual(get_region("South"), "s")
        self.assertEqual(get_region("Southern"), "s")

        self.assertRaises(ValueError, get_region, "not-a-region")

    def test_Parameters_and_related_functions(self):
        # Consider the following parameters given by a user.
        args = [
            "coupled_global.py",
            "/lcrc/group/e3sm/ac.forsyth2/zppy_min_case_global_time_series_single_plots_output/test-616-20240930/v3.LR.historical_0051",
            "v3.LR.historical_0051",
            "v3.LR.historical_0051",
            "1985",
            "1989",
            "Blue",
            "5",
            "None",
            "false",
            "TREFHT",
            "None",
            "FSH,RH2M,LAISHA,LAISUN,QINTR,QOVER,QRUNOFF,QSOIL,QVEGE,QVEGT,SOILWATER_10CM,TSA,H2OSNO,TOTLITC,CWDC,SOIL1C,SOIL2C,SOIL3C,SOIL4C,WOOD_HARVESTC,TOTVEGC,NBP,GPP,AR,HR",
            "None",
            "1",
            "1",
            "glb,n,s",
        ]
        # Then:
        parameters: Parameters = Parameters(args)
        self.assertEqual(
            parameters.case_dir,
            "/lcrc/group/e3sm/ac.forsyth2/zppy_min_case_global_time_series_single_plots_output/test-616-20240930/v3.LR.historical_0051",
        )
        self.assertEqual(parameters.experiment_name, "v3.LR.historical_0051")
        self.assertEqual(parameters.figstr, "v3.LR.historical_0051")
        self.assertEqual(parameters.year1, 1985)
        self.assertEqual(parameters.year2, 1989)
        self.assertEqual(parameters.color, "Blue")
        self.assertEqual(parameters.ts_num_years_str, "5")
        self.assertEqual(parameters.plots_original, [])
        self.assertEqual(parameters.atmosphere_only, False)
        self.assertEqual(parameters.plots_atm, ["TREFHT"])
        self.assertEqual(parameters.plots_ice, [])
        self.assertEqual(
            parameters.plots_lnd,
            [
                "FSH",
                "RH2M",
                "LAISHA",
                "LAISUN",
                "QINTR",
                "QOVER",
                "QRUNOFF",
                "QSOIL",
                "QVEGE",
                "QVEGT",
                "SOILWATER_10CM",
                "TSA",
                "H2OSNO",
                "TOTLITC",
                "CWDC",
                "SOIL1C",
                "SOIL2C",
                "SOIL3C",
                "SOIL4C",
                "WOOD_HARVESTC",
                "TOTVEGC",
                "NBP",
                "GPP",
                "AR",
                "HR",
            ],
        )
        self.assertEqual(parameters.plots_ocn, [])
        self.assertEqual(parameters.nrows, 1)
        self.assertEqual(parameters.ncols, 1)
        self.assertEqual(parameters.regions, ["glb", "n", "s"])

        # test_get_data_dir
        self.assertEqual(
            get_data_dir(parameters, "atm", True),
            "/lcrc/group/e3sm/ac.forsyth2/zppy_min_case_global_time_series_single_plots_output/test-616-20240930/v3.LR.historical_0051/post/atm/glb/ts/monthly/5yr/",
        )
        self.assertEqual(get_data_dir(parameters, "atm", False), "")
        self.assertEqual(
            get_data_dir(parameters, "ice", True),
            "/lcrc/group/e3sm/ac.forsyth2/zppy_min_case_global_time_series_single_plots_output/test-616-20240930/v3.LR.historical_0051/post/ice/glb/ts/monthly/5yr/",
        )
        self.assertEqual(get_data_dir(parameters, "ice", False), "")
        self.assertEqual(
            get_data_dir(parameters, "lnd", True),
            "/lcrc/group/e3sm/ac.forsyth2/zppy_min_case_global_time_series_single_plots_output/test-616-20240930/v3.LR.historical_0051/post/lnd/glb/ts/monthly/5yr/",
        )
        self.assertEqual(get_data_dir(parameters, "lnd", False), "")
        self.assertEqual(
            get_data_dir(parameters, "ocn", True),
            "/lcrc/group/e3sm/ac.forsyth2/zppy_min_case_global_time_series_single_plots_output/test-616-20240930/v3.LR.historical_0051/post/ocn/glb/ts/monthly/5yr/",
        )
        self.assertEqual(get_data_dir(parameters, "ocn", False), "")

        # test_get_exps
        self.maxDiff = None
        exps: List[Dict[str, Any]] = get_exps(parameters)
        self.assertEqual(len(exps), 1)
        expected = {
            "atmos": "/lcrc/group/e3sm/ac.forsyth2/zppy_min_case_global_time_series_single_plots_output/test-616-20240930/v3.LR.historical_0051/post/atm/glb/ts/monthly/5yr/",
            "ice": "",
            "land": "/lcrc/group/e3sm/ac.forsyth2/zppy_min_case_global_time_series_single_plots_output/test-616-20240930/v3.LR.historical_0051/post/lnd/glb/ts/monthly/5yr/",
            "ocean": "",
            "moc": "",
            "vol": "",
            "name": "v3.LR.historical_0051",
            "yoffset": 0.0,
            "yr": ([1985, 1989],),
            "color": "Blue",
        }
        self.assertEqual(exps[0], expected)
        # Change up parameters
        parameters.plots_original = "net_toa_flux_restom,global_surface_air_temperature,toa_radiation,net_atm_energy_imbalance,change_ohc,max_moc,change_sea_level,net_atm_water_imbalance".split(
            ","
        )
        parameters.plots_atm = []
        parameters.plots_lnd = []
        exps = get_exps(parameters)
        self.assertEqual(len(exps), 1)
        expected = {
            "atmos": "/lcrc/group/e3sm/ac.forsyth2/zppy_min_case_global_time_series_single_plots_output/test-616-20240930/v3.LR.historical_0051/post/atm/glb/ts/monthly/5yr/",
            "ice": "",
            "land": "",
            "ocean": "/lcrc/group/e3sm/ac.forsyth2/zppy_min_case_global_time_series_single_plots_output/test-616-20240930/v3.LR.historical_0051/post/ocn/glb/ts/monthly/5yr/",
            "moc": "/lcrc/group/e3sm/ac.forsyth2/zppy_min_case_global_time_series_single_plots_output/test-616-20240930/v3.LR.historical_0051/post/ocn/glb/ts/monthly/5yr/",
            "vol": "/lcrc/group/e3sm/ac.forsyth2/zppy_min_case_global_time_series_single_plots_output/test-616-20240930/v3.LR.historical_0051/post/ocn/glb/ts/monthly/5yr/",
            "name": "v3.LR.historical_0051",
            "yoffset": 0.0,
            "yr": ([1985, 1989],),
            "color": "Blue",
        }
        self.assertEqual(exps[0], expected)
        # Change up parameters
        parameters.atmosphere_only = True
        exps = get_exps(parameters)
        self.assertEqual(len(exps), 1)
        expected = {
            "atmos": "/lcrc/group/e3sm/ac.forsyth2/zppy_min_case_global_time_series_single_plots_output/test-616-20240930/v3.LR.historical_0051/post/atm/glb/ts/monthly/5yr/",
            "ice": "",
            "land": "",
            "ocean": "",
            "moc": "",
            "vol": "",
            "name": "v3.LR.historical_0051",
            "yoffset": 0.0,
            "yr": ([1985, 1989],),
            "color": "Blue",
        }
        self.assertEqual(exps[0], expected)

    # Metric

    def test_Variable(self):
        v = Variable(
            "var_name",
            original_units="units1",
            final_units="units2",
            group="group_name",
            long_name="long name",
        )
        self.assertEqual(v.variable_name, "var_name")
        self.assertEqual(v.metric, Metric.AVERAGE)
        self.assertEqual(v.scale_factor, 1.0)
        self.assertEqual(v.original_units, "units1")
        self.assertEqual(v.final_units, "units2")
        self.assertEqual(v.group, "group_name")
        self.assertEqual(v.long_name, "long name")

    def test_get_vars_original(self):
        self.assertEqual(
            get_var_names(get_vars_original(["net_toa_flux_restom"])), ["RESTOM"]
        )
        self.assertEqual(
            get_var_names(get_vars_original(["net_atm_energy_imbalance"])),
            ["RESTOM", "RESSURF"],
        )
        self.assertEqual(
            get_var_names(get_vars_original(["global_surface_air_temperature"])),
            ["TREFHT"],
        )
        self.assertEqual(
            get_var_names(get_vars_original(["toa_radiation"])), ["FSNTOA", "FLUT"]
        )
        self.assertEqual(
            get_var_names(get_vars_original(["net_atm_water_imbalance"])),
            ["PRECC", "PRECL", "QFLX"],
        )
        self.assertEqual(
            get_var_names(
                get_vars_original(
                    [
                        "net_toa_flux_restom",
                        "net_atm_energy_imbalance",
                        "global_surface_air_temperature",
                        "toa_radiation",
                        "net_atm_water_imbalance",
                    ]
                )
            ),
            ["RESTOM", "RESSURF", "TREFHT", "FSNTOA", "FLUT", "PRECC", "PRECL", "QFLX"],
        )
        self.assertEqual(get_var_names(get_vars_original(["invalid_plot"])), [])

    def test_land_csv_row_to_var(self):
        # Test with first row of land csv, whitespace stripped
        csv_row = "BCDEP,A,1.00000E+00,kg/m^2/s,kg/m^2/s,Aerosol Flux,total black carbon deposition (dry+wet) from atmosphere".split(
            ","
        )
        v: Variable = land_csv_row_to_var(csv_row)
        self.assertEqual(v.variable_name, "BCDEP")
        self.assertEqual(v.metric, Metric.AVERAGE)
        self.assertEqual(v.scale_factor, 1.0)
        self.assertEqual(v.original_units, "kg/m^2/s")
        self.assertEqual(v.final_units, "kg/m^2/s")
        self.assertEqual(v.group, "Aerosol Flux")
        self.assertEqual(
            v.long_name, "total black carbon deposition (dry+wet) from atmosphere"
        )

    # construct_land_variables -- requires IO

    def test_construct_generic_variables(self):
        vars: List[str] = ["a", "b", "c"]
        self.assertEqual(get_var_names(construct_generic_variables(vars)), vars)

    # RequestedVariables -- requires IO

    def test_VariableGroup(self):
        var_str_list: List[str] = ["a", "b", "c"]
        vars: List[Variable] = construct_generic_variables(var_str_list)
        g: VariableGroup = VariableGroup("MyGroup", vars)
        self.assertEqual(g.group_name, "MyGroup")
        self.assertEqual(get_var_names(g.variables), var_str_list)

    # TS -- requires IO
    # OutputViewer -- requires IO

    # Setup ###################################################################

    # set_var -- requires IO
    # process_data -- requires IO

    # Plotting ####################################################################

    def test_get_variable_groups(self):
        a: Variable = Variable(variable_name="a", group="GroupA")
        b: Variable = Variable(variable_name="b", group="GroupA")
        x: Variable = Variable(variable_name="x", group="GroupX")
        y: Variable = Variable(variable_name="y", group="GroupX")

        def get_group_names(groups: List[VariableGroup]) -> List[str]:
            return list(map(lambda g: g.group_name, groups))

        self.assertEqual(
            get_group_names(get_variable_groups([a, b, x, y])), ["GroupA", "GroupX"]
        )

    # getmoc -- requires IO
    # add_line -- requires IO
    # add_trend -- requires IO

    def test_get_ylim(self):
        # Min is equal, max is equal
        self.assertEqual(get_ylim([-1, 1], [-1, 1]), [-1, 1])
        # Min is lower, max is equal
        self.assertEqual(get_ylim([-1, 1], [-2, 1]), [-2, 1])
        # Min is equal, max is higher
        self.assertEqual(get_ylim([-1, 1], [-1, 2]), [-1, 2])
        # Min is lower, max is higher
        self.assertEqual(get_ylim([-1, 1], [-2, 2]), [-2, 2])
        # Min is lower, max is higher, multiple extreme_values
        self.assertEqual(get_ylim([-1, 1], [-2, -0.5, 0.5, 2]), [-2, 2])
        # No standard range
        self.assertEqual(get_ylim([], [-2, 2]), [-2, 2])
        # No extreme range
        self.assertEqual(get_ylim([-1, 1], []), [-1, 1])

    # Plotting functions -- require IO
    # make_plot_pdfs -- requires IO

    # Run coupled_global ######################################################

    # run -- requires IO
    # get_vars -- requires IO
    # create_viewer -- requires IO
    # create_viewer_index -- requires IO
    # run_by_region -- requires IO


if __name__ == "__main__":
    unittest.main()
