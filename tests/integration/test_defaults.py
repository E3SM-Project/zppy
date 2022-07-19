import os
import unittest

from tests.integration.utils import get_expansions


class TestDefaults(unittest.TestCase):
    def test_defaults(self):
        # cfg is not machine-specific
        self.assertEqual(os.system("zppy -c tests/integration/test_defaults.cfg"), 0)
        self.assertEqual(os.system("rm test_defaults_output/post/scripts/*.bash"), 0)
        self.assertEqual(
            os.system(
                "rm -rf test_defaults_output/post/scripts/global_time_series_0001-0020_dir"
            ),
            0,
        )
        expected_dir = get_expansions()["expected_dir"]
        self.assertEqual(
            os.system(
                f"diff -bur -I 'templateDir' test_defaults_output/post/scripts {expected_dir}test_defaults_expected_files"
            ),
            0,
        )
        self.assertEqual(os.system("rm -r test_defaults_output"), 0)


if __name__ == "__main__":
    # Run from top level of repo
    unittest.main()
