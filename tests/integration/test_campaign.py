import os
import unittest


class TestCampaign(unittest.TestCase):
    def test_campaign_cryosphere(self):
        self.assertEqual(
            os.system("zppy -c tests/integration/test_campaign_cryosphere.cfg"), 0
        )
        self.assertEqual(
            os.system("rm test_campaign_cryosphere_output/post/scripts/*.bash"), 0
        )
        self.assertEqual(
            os.system(
                "diff -u -I 'templateDir' test_campaign_cryosphere_output/post/scripts /lcrc/group/e3sm/public_html/zppy_test_resources/test_campaign_cryosphere_expected_files"
            ),
            0,
        )
        self.assertEqual(os.system("rm -r test_campaign_cryosphere_output"), 0)

    def test_campaign_cryosphere_override(self):
        self.assertEqual(
            os.system(
                "zppy -c tests/integration/test_campaign_cryosphere_override.cfg"
            ),
            0,
        )
        self.assertEqual(
            os.system(
                "rm test_campaign_cryosphere_override_output/post/scripts/*.bash"
            ),
            0,
        )
        self.assertEqual(
            os.system(
                "diff -u -I 'templateDir' test_campaign_cryosphere_override_output/post/scripts /lcrc/group/e3sm/public_html/zppy_test_resources/test_campaign_cryosphere_override_expected_files"
            ),
            0,
        )
        self.assertEqual(os.system("rm -r test_campaign_cryosphere_override_output"), 0)

    def test_campaign_high_res_v1(self):
        self.assertEqual(
            os.system("zppy -c tests/integration/test_campaign_high_res_v1.cfg"), 0
        )
        self.assertEqual(
            os.system("rm test_campaign_high_res_v1_output/post/scripts/*.bash"), 0
        )
        self.assertEqual(
            os.system(
                "diff -u -I 'templateDir' test_campaign_high_res_v1_output/post/scripts /lcrc/group/e3sm/public_html/zppy_test_resources/test_campaign_high_res_v1_expected_files"
            ),
            0,
        )
        self.assertEqual(os.system("rm -r test_campaign_high_res_v1_output"), 0)

    def test_campaign_none(self):
        self.assertEqual(
            os.system("zppy -c tests/integration/test_campaign_none.cfg"), 0
        )
        self.assertEqual(
            os.system("rm test_campaign_none_output/post/scripts/*.bash"), 0
        )
        self.assertEqual(
            os.system(
                "diff -u -I 'templateDir' test_campaign_none_output/post/scripts /lcrc/group/e3sm/public_html/zppy_test_resources/test_campaign_none_expected_files"
            ),
            0,
        )
        self.assertEqual(os.system("rm -r test_campaign_none_output"), 0)

    def test_campaign_water_cycle(self):
        self.assertEqual(
            os.system("zppy -c tests/integration/test_campaign_water_cycle.cfg"), 0
        )
        self.assertEqual(
            os.system("rm test_campaign_water_cycle_output/post/scripts/*.bash"), 0
        )
        self.assertEqual(
            os.system(
                "diff -u -I 'templateDir' test_campaign_water_cycle_output/post/scripts /lcrc/group/e3sm/public_html/zppy_test_resources/test_campaign_water_cycle_expected_files"
            ),
            0,
        )
        self.assertEqual(os.system("rm -r test_campaign_water_cycle_output"), 0)

    def test_campaign_water_cycle_override(self):
        self.assertEqual(
            os.system(
                "zppy -c tests/integration/test_campaign_water_cycle_override.cfg"
            ),
            0,
        )
        self.assertEqual(
            os.system(
                "rm test_campaign_water_cycle_override_output/post/scripts/*.bash"
            ),
            0,
        )
        self.assertEqual(
            os.system(
                "diff -u -I 'templateDir' test_campaign_water_cycle_override_output/post/scripts /lcrc/group/e3sm/public_html/zppy_test_resources/test_campaign_water_cycle_override_expected_files"
            ),
            0,
        )
        self.assertEqual(
            os.system("rm -r test_campaign_water_cycle_override_output"), 0
        )

    # test_bash_generation.py covers the case of an unspecified campaign.


if __name__ == "__main__":
    # Run from top level of repo
    unittest.main()
