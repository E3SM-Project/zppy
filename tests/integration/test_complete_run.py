import unittest

from tests.integration.utils import check_mismatched_images, get_expansions


class TestCompleteRun(unittest.TestCase):
    def test_complete_run(self):
        # See docs/source/dev_guide/testing.rst for steps to run before running this test.
        expansions = get_expansions()
        expected_dir = expansions["expected_dir"]
        user_www = expansions["user_www"]
        actual_images_dir = (
            f"{user_www}zppy_test_complete_run_www/v2.LR.historical_0201"
        )

        # The expected_images_file lists all images we expect to compare.
        expected_images_file = f"{expected_dir}image_list_expected_complete_run.txt"
        expected_images_dir = f"{expected_dir}expected_complete_run"

        # The directory to place differences in.
        diff_dir = "tests/integration/image_check_failures_complete_run"

        check_mismatched_images(
            self, actual_images_dir, expected_images_file, expected_images_dir, diff_dir
        )


if __name__ == "__main__":
    unittest.main()
