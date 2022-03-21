import unittest

from tests.integration.utils import check_mismatched_images


class TestCompleteRun(unittest.TestCase):
    def test_complete_run(self):
        # See docs/source/dev_guide/testing.rst for steps to run before running this test.
        actual_images_dir = "/lcrc/group/e3sm/public_html/diagnostic_output/ac.forsyth2/zppy_test_complete_run_www/v2.LR.historical_0201"

        # The expected_images_file lists all images we expect to compare.
        expected_images_file = "/lcrc/group/e3sm/public_html/zppy_test_resources/image_list_expected_complete_run.txt"
        expected_images_dir = (
            "/lcrc/group/e3sm/public_html/zppy_test_resources/expected_complete_run"
        )

        # The directory to place differences in.
        diff_dir = "tests/integration/image_check_failures_complete_run"

        check_mismatched_images(
            self, actual_images_dir, expected_images_file, expected_images_dir, diff_dir
        )


if __name__ == "__main__":
    unittest.main()
