from typing import Dict

from tests.integration.image_checker import (
    Results,
    construct_markdown_summary_table,
    set_up_and_run_image_checker,
)
from tests.integration.utils import get_expansions

V3_CASE_NAME = "v3.LR.historical_0051"
V2_CASE_NAME = "v2.LR.historical_0201"


def test_images():
    # To test a different branch, set this to True, and manually set the expansions.
    TEST_DIFFERENT_EXPANSIONS = False
    if TEST_DIFFERENT_EXPANSIONS:
        expansions = dict()
        # Example settings:
        expansions["expected_dir"] = "/lcrc/group/e3sm/public_html/zppy_test_resources/"
        expansions["user_www"] = (
            "/lcrc/group/e3sm/public_html/diagnostic_output/ac.forsyth2/"
        )
        expansions["unique_id"] = "test_zppy_20250401"
        diff_dir_suffix = "_test_pr699_try6"
    else:
        expansions = get_expansions()
        diff_dir_suffix = ""
    test_results_dict: Dict[str, Results] = dict()
    try:
        set_up_and_run_image_checker(
            "comprehensive_v2",
            V2_CASE_NAME,
            expansions,
            diff_dir_suffix,
            ["e3sm_diags", "mpas_analysis", "global_time_series", "ilamb"],
            test_results_dict,
        )
        set_up_and_run_image_checker(
            "comprehensive_v3",
            V3_CASE_NAME,
            expansions,
            diff_dir_suffix,
            ["e3sm_diags", "mpas_analysis", "global_time_series", "ilamb"],
            test_results_dict,
        )
        set_up_and_run_image_checker(
            "bundles",
            V3_CASE_NAME,
            expansions,
            diff_dir_suffix,
            ["e3sm_diags", "global_time_series", "ilamb"],  # No mpas_analysis
            test_results_dict,
        )
    except Exception as e:
        construct_markdown_summary_table(
            test_results_dict, "early_test_images_summary.md"
        )
        raise e
    construct_markdown_summary_table(test_results_dict, "test_images_summary.md")
    for tr in test_results_dict.values():
        assert tr.image_count_total == tr.image_count_correct
