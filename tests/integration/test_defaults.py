import os
import unittest


class TestDefaults(unittest.TestCase):
    def test_defaults(self):
        self.assertEqual(os.system("zppy -c tests/integration/test_defaults.cfg"), 0)
        self.assertEqual(os.system("rm test_defaults_output/post/scripts/*.bash"), 0)
        self.assertEqual(
            os.system(
                "rm -rf test_defaults_output/post/scripts/global_time_series_0001-0020_dir"
            ),
            0,
        )
        self.assertEqual(
            os.system(
                "diff -bur -I 'templateDir' test_defaults_output/post/scripts /lcrc/group/e3sm/public_html/zppy_test_resources/test_defaults_expected_files"
            ),
            0,
        )
        self.assertEqual(os.system("rm -r test_defaults_output"), 0)


if __name__ == "__main__":
    # Run from top level of repo
    unittest.main()
