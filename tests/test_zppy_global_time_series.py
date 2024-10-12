import unittest
from typing import Any, Dict, List

from zppy.global_time_series import determine_and_add_dependencies, determine_components


class TestZppyGlobalTimeSeries(unittest.TestCase):
    def test_determine_components(self):
        # Test non-legacy
        c: Dict[str, Any] = {
            "plot_names": "",
            "plots_original": "",
            "plots_atm": ["a"],
            "plots_ice": "",
            "plots_lnd": "",
            "plots_ocn": "",
        }
        determine_components(c)
        self.assertEqual(c["use_atm"], True)
        self.assertEqual(c["use_ice"], False)
        self.assertEqual(c["use_lnd"], False)
        self.assertEqual(c["use_ocn"], False)
        self.assertEqual(c["plots_atm"], ["a"])
        self.assertEqual(c["plots_ice"], "None")
        self.assertEqual(c["plots_lnd"], "None")
        self.assertEqual(c["plots_ocn"], "None")

        c = {
            "plot_names": "",
            "plots_original": "",
            "plots_atm": "",
            "plots_ice": ["a"],
            "plots_lnd": "",
            "plots_ocn": "",
        }
        determine_components(c)
        self.assertEqual(c["use_atm"], False)
        self.assertEqual(c["use_ice"], True)
        self.assertEqual(c["use_lnd"], False)
        self.assertEqual(c["use_ocn"], False)
        self.assertEqual(c["plots_atm"], "None")
        self.assertEqual(c["plots_ice"], ["a"])
        self.assertEqual(c["plots_lnd"], "None")
        self.assertEqual(c["plots_ocn"], "None")

        c = {
            "plot_names": "",
            "plots_original": "",
            "plots_atm": "",
            "plots_ice": "",
            "plots_lnd": ["a"],
            "plots_ocn": "",
        }
        determine_components(c)
        self.assertEqual(c["use_atm"], False)
        self.assertEqual(c["use_ice"], False)
        self.assertEqual(c["use_lnd"], True)
        self.assertEqual(c["use_ocn"], False)
        self.assertEqual(c["plots_atm"], "None")
        self.assertEqual(c["plots_ice"], "None")
        self.assertEqual(c["plots_lnd"], ["a"])
        self.assertEqual(c["plots_ocn"], "None")

        c = {
            "plot_names": "",
            "plots_original": "",
            "plots_atm": "",
            "plots_ice": "",
            "plots_lnd": "",
            "plots_ocn": ["a"],
        }
        determine_components(c)
        self.assertEqual(c["use_atm"], False)
        self.assertEqual(c["use_ice"], False)
        self.assertEqual(c["use_lnd"], False)
        self.assertEqual(c["use_ocn"], True)
        self.assertEqual(c["plots_atm"], "None")
        self.assertEqual(c["plots_ice"], "None")
        self.assertEqual(c["plots_lnd"], "None")
        self.assertEqual(c["plots_ocn"], ["a"])

        # Test legacy
        base = {"plots_atm": "", "plots_ice": "", "plots_lnd": "", "plots_ocn": ""}

        c = {
            "plot_names": ["a"],
            "plots_original": "gets_overwritten",
            "atmosphere_only": False,
        }
        c.update(base)
        determine_components(c)
        self.assertEqual(c["plots_original"], ["a"])
        self.assertEqual(c["use_atm"], True)
        self.assertEqual(c["use_ice"], False)
        self.assertEqual(c["use_lnd"], False)
        self.assertEqual(c["use_ocn"], False)
        self.assertEqual(c["plots_atm"], "None")
        self.assertEqual(c["plots_ice"], "None")
        self.assertEqual(c["plots_lnd"], "None")
        self.assertEqual(c["plots_ocn"], "None")

        for ocn_set in ["change_ohc", "max_moc", "change_sea_level"]:
            c = {
                "plot_names": "",
                "plots_original": [ocn_set],
                "atmosphere_only": False,
            }
            c.update(base)
            determine_components(c)
            self.assertEqual(c["plots_original"], [ocn_set])
            self.assertEqual(c["use_atm"], True)
            self.assertEqual(c["use_ice"], False)
            self.assertEqual(c["use_lnd"], False)
            self.assertEqual(c["use_ocn"], True)
            self.assertEqual(c["plots_atm"], "None")
            self.assertEqual(c["plots_ice"], "None")
            self.assertEqual(c["plots_lnd"], "None")
            self.assertEqual(c["plots_ocn"], "None")

        c = {"plot_names": "", "plots_original": ["a"], "atmosphere_only": True}
        c.update(base)
        determine_components(c)
        self.assertEqual(c["plots_original"], ["a"])
        self.assertEqual(c["use_atm"], True)
        self.assertEqual(c["use_ice"], False)
        self.assertEqual(c["use_lnd"], False)
        self.assertEqual(c["use_ocn"], False)
        self.assertEqual(c["plots_atm"], "None")
        self.assertEqual(c["plots_ice"], "None")
        self.assertEqual(c["plots_lnd"], "None")
        self.assertEqual(c["plots_ocn"], "None")

    def test_determine_and_add_dependencies(self):
        c: Dict[str, Any] = {
            "use_atm": True,
            "use_lnd": False,
            "use_ocn": False,
            "year1": 1980,
            "year2": 1990,
            "ts_num_years": 5,
        }
        dependencies: List[str] = []
        determine_and_add_dependencies(c, dependencies, "script_dir")
        expected = [
            "script_dir/ts_atm_monthly_glb_1980-1984-0005.status",
            "script_dir/ts_atm_monthly_glb_1985-1989-0005.status",
        ]
        self.assertEqual(dependencies, expected)

        c = {
            "use_atm": False,
            "use_lnd": True,
            "use_ocn": False,
            "year1": 1980,
            "year2": 1990,
            "ts_num_years": 5,
        }
        dependencies = []
        determine_and_add_dependencies(c, dependencies, "script_dir")
        expected = [
            "script_dir/ts_lnd_monthly_glb_1980-1984-0005.status",
            "script_dir/ts_lnd_monthly_glb_1985-1989-0005.status",
        ]
        self.assertEqual(dependencies, expected)

        c = {
            "use_atm": False,
            "use_lnd": False,
            "use_ocn": True,
            "ts_years": "1980:1990:10",
            "climo_years": "1980:1990:10",
        }
        dependencies = []
        determine_and_add_dependencies(c, dependencies, "script_dir")
        expected = ["script_dir/mpas_analysis_ts_1980-1989_climo_1980-1989.status"]
        self.assertEqual(dependencies, expected)

        c = {
            "use_atm": False,
            "use_lnd": False,
            "use_ocn": True,
            "ts_years": "",
            "climo_years": "1980:1990:10",
        }
        dependencies = []
        self.assertRaises(
            Exception, determine_and_add_dependencies, c, dependencies, "script_dir"
        )
        c = {
            "use_atm": False,
            "use_lnd": False,
            "use_ocn": True,
            "ts_years": "1980:1990:10",
            "climo_years": "",
        }
        dependencies = []
        self.assertRaises(
            Exception, determine_and_add_dependencies, c, dependencies, "script_dir"
        )


if __name__ == "__main__":
    unittest.main()
