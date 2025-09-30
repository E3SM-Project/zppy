from typing import Dict, List

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
    tasks_to_run: List[str] = list(expansions["tasks_to_run"])
    try:
        # TODO: these could be run in parallel, if easy to implement

        # Weekly comprehensive tests
        print("Checking weekly cfg output")
        if "weekly_comprehensive_v2" in expansions["cfgs_to_run"]:
            set_up_and_run_image_checker(
                "comprehensive_v2",
                V2_CASE_NAME,
                expansions,
                diff_dir_suffix,
                tasks_to_run,
                test_results_dict,
            )
        if "weekly_comprehensive_v3" in expansions["cfgs_to_run"]:
            set_up_and_run_image_checker(
                "comprehensive_v3",
                V3_CASE_NAME,
                expansions,
                diff_dir_suffix,
                tasks_to_run,
                test_results_dict,
            )
        if "weekly_bundles" in expansions["cfgs_to_run"]:
            # No mpas_analysis
            if "mpas_analysis" in expansions["tasks_to_run"]:
                tasks_to_run_modified = tasks_to_run.copy()
                tasks_to_run_modified.remove("mpas_analysis")
            else:
                tasks_to_run_modified = tasks_to_run
            set_up_and_run_image_checker(
                "bundles",
                V3_CASE_NAME,
                expansions,
                diff_dir_suffix,
                tasks_to_run_modified,
                test_results_dict,
            )

        # Legacy comprehensive tests
        # These cfgs remain unchanged, but we test the latest zppy code on them
        # to check for backwards-compatiblity issues.
        print("Checking legacy cfg output")
        if "weekly_legacy_3.0.0_comprehensive_v2" in expansions["cfgs_to_run"]:
            set_up_and_run_image_checker(
                "legacy_3.0.0_comprehensive_v2",
                V2_CASE_NAME,
                expansions,
                diff_dir_suffix,
                tasks_to_run,
                test_results_dict,
            )
        if "weekly_legacy_3.0.0_comprehensive_v3" in expansions["cfgs_to_run"]:
            set_up_and_run_image_checker(
                "legacy_3.0.0_comprehensive_v3",
                V3_CASE_NAME,
                expansions,
                diff_dir_suffix,
                tasks_to_run,
                test_results_dict,
            )
        if "weekly_legacy_3.0.0_bundles" in expansions["cfgs_to_run"]:
            # No mpas_analysis
            if "mpas_analysis" in expansions["tasks_to_run"]:
                tasks_to_run_modified = tasks_to_run.copy()
                tasks_to_run_modified.remove("mpas_analysis")
            else:
                tasks_to_run_modified = tasks_to_run
            set_up_and_run_image_checker(
                "legacy_3.0.0_bundles",
                V3_CASE_NAME,
                expansions,
                diff_dir_suffix,
                tasks_to_run_modified,
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
