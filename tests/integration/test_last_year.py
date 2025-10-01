import os


def test_last_year():
    # Note that this integration test does not have any expected files in `tests.integration.utils.get_expansions()["expected_dir"]`
    # cfg is not machine-specific
    # Start fresh:
    assert os.system("rm -rf test_last_year_output") == 0
    assert os.system("zppy -c tests/integration/test_last_year.cfg --last-year 12") == 0
    # Remove files that are not deterministic:
    assert os.system("rm test_last_year_output/post/scripts/*.settings") == 0
    assert os.system("rm -rf test_last_year_output/post/scripts/provenance*") == 0
    actual_files = sorted(os.listdir("test_last_year_output/post/scripts"))
    expected_files = [
        "climo_atm_monthly_180x360_aave_0001-0010.bash",
        "climo_atm_monthly_diurnal_8xdaily_180x360_aave_0001-0010.bash",
        "e3sm_diags_atm_monthly_180x360_aave_model_vs_obs_0001-0010.bash",
        "mpas_analysis_ts_0001-0010_climo_0001-0010.bash",
        "tc_analysis_0001-0010.bash",
        "ts_atm_daily_180x360_aave_0001-0010-0010.bash",
        "ts_atm_monthly_180x360_aave_0001-0010-0010.bash",
        "ts_atm_monthly_glb_0001-0010-0010.bash",
        "ts_land_monthly_0001-0010-0010.bash",
        "ts_rof_monthly_0001-0010-0010.bash",
    ]
    if actual_files != expected_files:
        print(actual_files)
        print(expected_files)
    assert actual_files == expected_files
    assert os.system("rm -r test_last_year_output") == 0
