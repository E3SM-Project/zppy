import unittest
from typing import List

from zppy.ilamb import determine_and_add_dependencies


class TestZppyILAMB(unittest.TestCase):
    def test_determine_and_add_dependencies(self):
        c = {
            "land_only": True,
            "ts_land_subsection": "land_monthly",
            "year1": 1980,
            "year2": 1990,
            "ts_num_years": 5,
        }
        dependencies: List[str] = []
        determine_and_add_dependencies(c, dependencies, "script_dir")
        expected = [
            "script_dir/ts_land_monthly_1980-1984-0005.status",
            "script_dir/ts_land_monthly_1985-1989-0005.status",
        ]
        self.assertEqual(dependencies, expected)

        # Have zppy guess the subsection names
        c = {
            "land_only": False,
            "ts_land_subsection": "",
            "ts_atm_subsection": "",
            "year1": 1980,
            "year2": 1990,
            "ts_num_years": 5,
            "guess_path_parameters": True,
            "guess_section_parameters": True,
        }
        dependencies = []
        determine_and_add_dependencies(c, dependencies, "script_dir")
        expected = [
            "script_dir/ts_land_monthly_1980-1984-0005.status",
            "script_dir/ts_land_monthly_1985-1989-0005.status",
            "script_dir/ts_atm_monthly_180x360_aave_1980-1984-0005.status",
            "script_dir/ts_atm_monthly_180x360_aave_1985-1989-0005.status",
        ]
        self.assertEqual(dependencies, expected)


if __name__ == "__main__":
    unittest.main()
