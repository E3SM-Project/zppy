import os

import pytest

from tests.integration.utils import check_mismatched_images, get_expansions

V3_CASE_NAME = "v3.LR.historical_0051"
V2_CASE_NAME = "v2.LR.historical_0201"


def check_images(test_name, case_name):
    # See docs/source/dev_guide/testing.rst for steps to run before running this test.
    expansions = get_expansions()
    expected_dir = expansions["expected_dir"]
    user_www = expansions["user_www"]
    unique_id = expansions["unique_id"]
    actual_images_dir = (
        f"{user_www}zppy_weekly_{test_name}_www/{unique_id}/{case_name}/"
    )

    # The expected_images_file lists all images we expect to compare.
    expected_images_file = f"{expected_dir}image_list_expected_{test_name}.txt"
    expected_images_dir = f"{expected_dir}expected_{test_name}"

    # The directory to place differences in.
    diff_dir = f"{actual_images_dir}image_check_failures_{test_name}"

    # To run a subset of the image-check test:
    # 1) comment out sections you don't want to run in the `cfg`
    # 2) set `subdirs_to_check` to the subset of tasks you want to run
    # subdirs_to_check = ["mpas_analysis", "e3sm_diags", "global_time_series", "ilamb"]
    subdirs_to_check = ["ilamb"]

    check_mismatched_images(
        actual_images_dir,
        expected_images_file,
        expected_images_dir,
        diff_dir,
        subdirs_to_check,
    )


# Run with:
# pytest tests/integration/test_weekly.py
# Comment/uncomment `skip` declarations to run specific tests.


# @pytest.mark.skip(reason="Not testing")
def test_comprehensive_v2_images():
    check_images("comprehensive_v2", V2_CASE_NAME)


# @pytest.mark.skip(reason="Not testing")
def test_comprehensive_v3_images():
    check_images("comprehensive_v3", V3_CASE_NAME)


@pytest.mark.skip(reason="Not testing")
def test_bundles_images():
    check_images("bundles", V3_CASE_NAME)


@pytest.mark.skip(reason="Not testing")
def test_bundles_bash_file_list():
    # Check that the correct bash files are generated
    expansions = get_expansions()
    user_output = expansions["user_output"]
    unique_id = expansions["unique_id"]
    directory = f"{user_output}zppy_weekly_bundles_output/{unique_id}/{V3_CASE_NAME}/post/scripts"
    bash_file_list = f"{directory}/bash_file_list.txt"
    cmd = f"cd {directory} && find . -type f -name '*.bash' > {bash_file_list}"
    os.system(cmd)
    actual_bash_files = set()
    with open(bash_file_list, "r") as f:
        for line in f:
            actual_bash_files.add(line.lstrip("./").rstrip("\n"))
    expected_bash_files = set(
        [
            "bundle1.bash",
            "bundle2.bash",
            "bundle3.bash",
            "climo_atm_monthly_180x360_aave_1985-1986.bash",
            "climo_atm_monthly_180x360_aave_1987-1988.bash",
            "climo_atm_monthly_diurnal_8xdaily_180x360_aave_1985-1986.bash",
            "climo_atm_monthly_diurnal_8xdaily_180x360_aave_1987-1988.bash",
            "e3sm_diags_atm_monthly_180x360_aave_model_vs_obs_1985-1986.bash",
            "e3sm_diags_atm_monthly_180x360_aave_model_vs_obs_1987-1988.bash",
            "e3sm_diags_atm_monthly_180x360_aave_mvm_model_vs_model_1987-1988_vs_1985-1986.bash",
            "e3sm_to_cmip_atm_monthly_180x360_aave_1985-1986-0002.bash",
            "e3sm_to_cmip_atm_monthly_180x360_aave_1987-1988-0002.bash",
            "e3sm_to_cmip_land_monthly_1985-1986-0002.bash",
            "e3sm_to_cmip_land_monthly_1987-1988-0002.bash",
            "global_time_series_1985-1995.bash",
            "ilamb_1985-1986.bash",
            # "tc_analysis_1985-1986.bash",
            # "tc_analysis_1987-1988.bash",
            "ts_atm_monthly_180x360_aave_1985-1986-0002.bash",
            "ts_atm_monthly_180x360_aave_1987-1988-0002.bash",
            "ts_atm_monthly_glb_1985-1989-0005.bash",
            "ts_atm_monthly_glb_1990-1994-0005.bash",
            "ts_land_monthly_1985-1986-0002.bash",
            "ts_land_monthly_1987-1988-0002.bash",
            "ts_rof_monthly_1985-1986-0002.bash",
            "ts_rof_monthly_1987-1988-0002.bash",
        ]
    )
    assert actual_bash_files == expected_bash_files


@pytest.mark.skip(reason="Not testing")
def test_bundles_bash_file_content():
    expansions = get_expansions()
    user_output = expansions["user_output"]
    expected_dir = expansions["expected_dir"]
    unique_id = expansions["unique_id"]
    actual_directory = f"{user_output}zppy_weekly_bundles_output/{unique_id}/{V3_CASE_NAME}/post/scripts"
    expected_directory = f"{expected_dir}expected_bundles/bundle_files"
    # Check that bundle files are correct
    assert (
        os.system(
            f"diff -bu -I 'zppy_weekly_bundles_output/' {actual_directory}/bundle1.bash {expected_directory}/bundle1.bash"
        )
        == 0
    )
    assert (
        os.system(
            f"diff -bu -I 'zppy_weekly_bundles_output/' {actual_directory}/bundle2.bash {expected_directory}/bundle2.bash"
        )
        == 0
    )
    assert (
        os.system(
            f"diff -bu -I 'zppy_weekly_bundles_output/' {actual_directory}/bundle3.bash {expected_directory}/bundle3.bash"
        )
        == 0
    )
