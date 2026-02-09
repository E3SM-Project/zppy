from typing import List

from zppy.livvkit import add_climo_dependency, determine_and_add_dependencies


def test_add_climo_dependency():
    dependencies: List[str] = []
    script_dir = "script_dir"
    prefix = "climo_pfx"
    subset = "land_monthly_racmo_gis"
    start_year = 2020
    end_year = 2059
    num_years = 15
    add_climo_dependency(
        dependencies, script_dir, prefix, subset, start_year, end_year, num_years
    )
    expected_dependencies = [
        "script_dir/climo_pfx_land_monthly_racmo_gis_2020-2034.status",
        "script_dir/climo_pfx_land_monthly_racmo_gis_2035-2049.status",
    ]
    assert dependencies == expected_dependencies


def test_determine_and_add_dependencies():
    c = {
        "e3sm_to_cmip_land_subsection": "land_monthly",
        "land_only": True,
        "ts_land_subsection": "land_monthly",
        "year1": 1980,
        "year2": 1990,
        "ts_num_years": 5,
        "sets": "cmb,smb,energy_era5",
        "icesheets": "gis",
    }
    dependencies: List[str] = []
    determine_and_add_dependencies(c, dependencies, "script_dir")

    expected = [
        "script_dir/ts_land_monthly_1980-1984-0005.status",
        "script_dir/ts_land_monthly_1985-1989-0005.status",
        "script_dir/climo_land_monthly_climo_native_1980-1984.status",
        "script_dir/climo_land_monthly_climo_native_1985-1989.status",
        "script_dir/climo_land_monthly_climo_era5_1980-1984.status",
        "script_dir/climo_land_monthly_climo_era5_1985-1989.status",
        "script_dir/climo_land_monthly_climo_racmo_gis_1980-1984.status",
        "script_dir/climo_land_monthly_climo_racmo_gis_1985-1989.status",
    ]
    assert sorted(dependencies) == sorted(expected)
