import os
import unittest

from tests.integration.utils import get_expansions


class TestBashGeneration(unittest.TestCase):
    def test_bash_generation(self):
        # cfg is not machine-specific
        self.assertEqual(
            os.system("zppy -c tests/integration/test_bash_generation.cfg"), 0
        )
        expected_dir = get_expansions()["expected_dir"]
        self.assertEqual(
            os.system(
                f"diff -bur -I 'templateDir' test_bash_generation_output/post/scripts {expected_dir}expected_bash_files"
            ),
            0,
        )
        self.assertEqual(os.system("rm -r test_bash_generation_output"), 0)


if __name__ == "__main__":
    # Run from top level of repo
    unittest.main()
