import os

from tests.integration.utils import get_expansions


# cfgs are not machine-specific
def test_campaign_cryosphere():
    assert os.system("zppy -c tests/integration/test_campaign_cryosphere.cfg") == 0
    assert os.system("rm test_campaign_cryosphere_output/post/scripts/*.bash") == 0
    assert (
        os.system("rm -rf test_campaign_cryosphere_output/post/scripts/provenance*")
        == 0
    )
    expected_dir = get_expansions()["expected_dir"]
    assert (
        os.system(
            f"diff -u -I 'templateDir' test_campaign_cryosphere_output/post/scripts {expected_dir}test_campaign_cryosphere_expected_files"
        )
        == 0
    )
    assert os.system("rm -r test_campaign_cryosphere_output") == 0


def test_campaign_cryosphere_override():
    assert (
        os.system("zppy -c tests/integration/test_campaign_cryosphere_override.cfg")
        == 0
    )
    assert (
        os.system("rm test_campaign_cryosphere_override_output/post/scripts/*.bash")
        == 0
    )
    assert (
        os.system(
            "rm -rf test_campaign_cryosphere_override_output/post/scripts/provenance*"
        )
        == 0
    )
    expected_dir = get_expansions()["expected_dir"]
    assert (
        os.system(
            f"diff -u -I 'templateDir' test_campaign_cryosphere_override_output/post/scripts {expected_dir}test_campaign_cryosphere_override_expected_files"
        )
        == 0
    )
    assert os.system("rm -r test_campaign_cryosphere_override_output") == 0


def test_campaign_high_res_v1():
    assert os.system("zppy -c tests/integration/test_campaign_high_res_v1.cfg") == 0
    assert os.system("rm test_campaign_high_res_v1_output/post/scripts/*.bash") == 0
    assert (
        os.system("rm -rf test_campaign_high_res_v1_output/post/scripts/provenance*")
        == 0
    )
    expected_dir = get_expansions()["expected_dir"]
    assert (
        os.system(
            f"diff -u -I 'templateDir' test_campaign_high_res_v1_output/post/scripts {expected_dir}test_campaign_high_res_v1_expected_files"
        )
        == 0
    )
    assert os.system("rm -r test_campaign_high_res_v1_output") == 0


def test_campaign_none():
    assert os.system("zppy -c tests/integration/test_campaign_none.cfg") == 0
    assert os.system("rm test_campaign_none_output/post/scripts/*.bash") == 0
    assert os.system("rm -rf test_campaign_none_output/post/scripts/provenance*") == 0
    expected_dir = get_expansions()["expected_dir"]
    assert (
        os.system(
            f"diff -u -I 'templateDir' test_campaign_none_output/post/scripts {expected_dir}test_campaign_none_expected_files"
        )
        == 0
    )
    assert os.system("rm -r test_campaign_none_output") == 0


def test_campaign_water_cycle():
    assert os.system("zppy -c tests/integration/test_campaign_water_cycle.cfg") == 0
    assert os.system("rm test_campaign_water_cycle_output/post/scripts/*.bash") == 0
    assert (
        os.system("rm -rf test_campaign_water_cycle_output/post/scripts/provenance*")
        == 0
    )
    expected_dir = get_expansions()["expected_dir"]
    assert (
        os.system(
            f"diff -u -I 'templateDir' test_campaign_water_cycle_output/post/scripts {expected_dir}test_campaign_water_cycle_expected_files"
        )
        == 0
    )
    assert os.system("rm -r test_campaign_water_cycle_output") == 0


def test_campaign_water_cycle_override():
    assert (
        os.system("zppy -c tests/integration/test_campaign_water_cycle_override.cfg")
        == 0
    )
    assert (
        os.system("rm test_campaign_water_cycle_override_output/post/scripts/*.bash")
        == 0
    )
    assert (
        os.system(
            "rm -rf test_campaign_water_cycle_override_output/post/scripts/provenance*"
        )
        == 0
    )
    expected_dir = get_expansions()["expected_dir"]
    assert (
        os.system(
            f"diff -u -I 'templateDir' test_campaign_water_cycle_override_output/post/scripts {expected_dir}test_campaign_water_cycle_override_expected_files"
        )
        == 0
    )
    assert os.system("rm -r test_campaign_water_cycle_override_output") == 0


# test_bash_generation.py covers the case of an unspecified campaign.
