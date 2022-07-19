import os
import unittest

from tests.integration.utils import check_mismatched_images, get_expansions


class TestBundles(unittest.TestCase):
    def test_bundles_bash_file_list(self):
        # Check that the correct bash files are generated
        user_output = get_expansions()["user_output"]
        directory = (
            f"{user_output}zppy_test_bundles_output/v2.LR.historical_0201/post/scripts"
        )
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
                "climo_atm_monthly_180x360_aave_1850-1851.bash",
                "climo_atm_monthly_180x360_aave_1852-1853.bash",
                "climo_atm_monthly_diurnal_8xdaily_180x360_aave_1850-1851.bash",
                "climo_atm_monthly_180x360_aave_1850-1853.bash",
                "climo_atm_monthly_diurnal_8xdaily_180x360_aave_1852-1853.bash",
                "climo_atm_monthly_diurnal_8xdaily_180x360_aave_1850-1853.bash",
                "e3sm_diags_atm_monthly_180x360_aave_model_vs_obs_1850-1851.bash",
                "e3sm_diags_atm_monthly_180x360_aave_model_vs_obs_1850-1853.bash",
                "e3sm_diags_atm_monthly_180x360_aave_model_vs_obs_1852-1853.bash",
                "e3sm_diags_atm_monthly_180x360_aave_mvm_model_vs_model_1850-1851_vs_1850-1851.bash",
                "global_time_series_1850-1860.bash",
                "ilamb_1850-1851.bash",
                "tc_analysis_1850-1851.bash",
                "ts_atm_daily_180x360_aave_1850-1851-0002.bash",
                "ts_atm_daily_180x360_aave_1852-1853-0002.bash",
                "ts_atm_monthly_180x360_aave_1850-1851-0002.bash",
                "ts_atm_monthly_180x360_aave_1852-1853-0002.bash",
                "ts_atm_monthly_glb_1850-1854-0005.bash",
                "ts_atm_monthly_glb_1855-1859-0005.bash",
                "ts_land_monthly_1850-1851-0002.bash",
                "ts_land_monthly_1852-1853-0002.bash",
                "ts_rof_monthly_1850-1851-0002.bash",
                "ts_rof_monthly_1852-1853-0002.bash",
            ]
        )
        self.assertEqual(actual_bash_files, expected_bash_files)

    def test_bundles_bash_file_content(self):
        expansions = get_expansions()
        user_output = expansions["user_output"]
        expected_dir = expansions["expected_dir"]
        actual_directory = (
            f"{user_output}zppy_test_bundles_output/v2.LR.historical_0201/post/scripts"
        )
        expected_directory = f"{expected_dir}expected_bundles/bundle_files"
        # Check that bundle files are correct
        self.assertEqual(
            os.system(
                f"diff -bu {actual_directory}/bundle1.bash {expected_directory}/bundle1.bash"
            ),
            0,
        )
        self.assertEqual(
            os.system(
                f"diff -bu {actual_directory}/bundle2.bash {expected_directory}/bundle2.bash"
            ),
            0,
        )
        self.assertEqual(
            os.system(
                f"diff -bu {actual_directory}/bundle3.bash {expected_directory}/bundle3.bash"
            ),
            0,
        )

    def test_bundles_images(self):
        # Check that correct images were generated
        # See docs/source/dev_guide/testing.rst for steps to run before running this test.
        expansions = get_expansions()
        expected_dir = expansions["expected_dir"]
        user_www = expansions["user_www"]
        actual_images_dir = f"{user_www}zppy_test_bundles_www/v2.LR.historical_0201"

        # The expected_images_file lists all images we expect to compare.
        expected_images_file = f"{expected_dir}image_list_expected_bundles.txt"
        expected_images_dir = f"{expected_dir}expected_bundles"

        # The directory to place differences in.
        diff_dir = "tests/integration/image_check_failures_bundles"

        check_mismatched_images(
            self, actual_images_dir, expected_images_file, expected_images_dir, diff_dir
        )


if __name__ == "__main__":
    unittest.main()
