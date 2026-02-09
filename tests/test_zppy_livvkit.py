from typing import List

from zppy.livvkit import add_climo_dependency, determine_and_add_dependencies

# def add_climo_dependency(
#     dependencies: List[str],
#     scriptDir: str,
#     prefix: str,
#     sub: str,
#     start_yr: int,
#     end_yr: int,
#     num_years: int,
# ) -> None:
#     y1: int = start_yr
#     y2: int = start_yr + num_years - 1
#     while y2 <= end_yr:
#         dependencies.append(
#             os.path.join(scriptDir, f"{prefix}_{sub}_{y1:04d}-{y2:04d}.status")
#         )
#         y1 += num_years
#         y2 += num_years

def test_add_climo_dependency():
    dependencies: List[str] = []
    script_dir = "script_dir"
    prefix = "climo_pfx"
    subset = "land_monthly_racmo_gis"
    start_year = 2020
    end_year = 2059
    num_years = 15
    add_climo_dependency(dependencies, script_dir, prefix, subset, start_year, end_year, num_years)
    breakpoint()
    expected_dependencies = ['script_dir/climo_pfx_land_monthly_racmo_gis_2020-2034.status', 'script_dir/climo_pfx_land_monthly_racmo_gis_2035-2049.status']
    assert all(dependencies == expected_dependencies)

# def test_determine_and_add_dependencies():
#     c = {
#         "e3sm_to_cmip_land_subsection": "land_monthly",
#         "land_only": True,
#         "ts_land_subsection": "land_monthly",
#         "year1": 1980,
#         "year2": 1990,
#         "ts_num_years": 5,
#     }
#     dependencies: List[str] = []
#     determine_and_add_dependencies(c, dependencies, "script_dir")
#     expected = [
#         "script_dir/ts_land_monthly_1980-1984-0005.status",
#         "script_dir/ts_land_monthly_1985-1989-0005.status",
#         "script_dir/e3sm_to_cmip_land_monthly_1980-1984-0005.status",
#         "script_dir/e3sm_to_cmip_land_monthly_1985-1989-0005.status",
#     ]
#     assert dependencies == expected
# 
#     # Have zppy infer the subsection names
#     c = {
#         "e3sm_to_cmip_atm_subsection": "",
#         "e3sm_to_cmip_land_subsection": "",
#         "land_only": False,
#         "ts_land_subsection": "",
#         "ts_atm_subsection": "",
#         "year1": 1980,
#         "year2": 1990,
#         "ts_num_years": 5,
#         "infer_path_parameters": True,
#         "infer_section_parameters": True,
#     }
#     dependencies = []
#     determine_and_add_dependencies(c, dependencies, "script_dir")
#     expected = [
#         "script_dir/ts_land_monthly_1980-1984-0005.status",
#         "script_dir/ts_land_monthly_1985-1989-0005.status",
#         "script_dir/e3sm_to_cmip_land_monthly_1980-1984-0005.status",
#         "script_dir/e3sm_to_cmip_land_monthly_1985-1989-0005.status",
#         "script_dir/ts_atm_monthly_180x360_aave_1980-1984-0005.status",
#         "script_dir/ts_atm_monthly_180x360_aave_1985-1989-0005.status",
#         "script_dir/e3sm_to_cmip_atm_monthly_180x360_aave_1980-1984-0005.status",
#         "script_dir/e3sm_to_cmip_atm_monthly_180x360_aave_1985-1989-0005.status",
#     ]
#     assert dependencies == expected
