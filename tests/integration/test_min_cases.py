import os
from typing import Dict, List

from tests.integration.utils import TestResults, check_mismatched_images, get_expansions

V3_CASE_NAME = "v3.LR.historical_0051"
V2_CASE_NAME = "v2.LR.historical_0201"


def check_images(test_name: str, case_name: str, subdir: List[str]) -> TestResults:
    # See docs/source/dev_guide/testing.rst for steps to run before running this test.
    expansions = get_expansions()
    # TODO: Add expected results to expected_dir_min_case
    expected_dir = expansions["expected_dir_min_case"]
    user_www = expansions["user_www"]
    unique_id = expansions["unique_id"]
    # TODO: Create a script that will launch ALL the min case cfgs, similar to https://github.com/E3SM-Project/zppy/pull/520
    actual_images_dir = (
        f"{user_www}/zppy_test_results/{unique_id}/zppy_{test_name}_www/{case_name}/"
    )

    # The expected_images_file lists all images we expect to compare.
    expected_images_file = f"{expected_dir}image_list_expected_{test_name}.txt"
    expected_images_dir = f"{expected_dir}expected_{test_name}"

    # The directory to place differences in.
    diff_dir = f"{actual_images_dir}image_check_failures_{test_name}"

    test_results = check_mismatched_images(
        actual_images_dir,
        expected_images_file,
        expected_images_dir,
        diff_dir,
        subdir,
    )
    if os.path.exists(f"{diff_dir}/missing_images.txt"):
        os.remove(f"{diff_dir}/missing_images.txt")
    if os.path.exists(f"{diff_dir}/mismatched_images.txt"):
        os.remove(f"{diff_dir}/mismatched_images.txt")
    for missing_image in test_results.file_list_missing:
        with open(f"{diff_dir}/missing_images.txt", "a") as f:
            f.write(f"{missing_image}\n")
    for mismatched_image in test_results.file_list_mismatched:
        with open(f"{diff_dir}/mismatched_images.txt", "a") as f:
            f.write(f"{mismatched_image}\n")
    return test_results


def construct_markdown_summary_table(
    test_results_dict: Dict[str, TestResults], output_file_path: str
):
    with open(output_file_path, "w") as f:
        f.write("# Summary of test results\n\n")
        f.write(
            "| Test name | Total images | Missing images | Mismatched images | Correct images |\n"
        )
        f.write("| --- | --- | --- | --- | --- |\n")
        for test_name, test_results in test_results_dict.items():
            f.write(
                f"| {test_name} | {test_results.image_count_total} | {test_results.image_count_missing} | {test_results.image_count_mismatched} | {test_results.image_count_correct} |\n"
            )


# Run with:
# pytest tests/integration/test_min_cases.py
def test_all_min_cases():
    test_results_dict: Dict[str, TestResults] = dict()

    # TODO: add test lines for ALL min case cfgs
    test_results = check_images(
        "min_case_add_dependencies",
        V3_CASE_NAME,
        ["e3sm_diags", "global_time_series", "ilamb"],
    )
    test_results_dict["min_case_add_dependencies"] = test_results

    construct_markdown_summary_table(test_results_dict, "min_case_summary.md")
    print("Copy output of min_case_summary.md to a PR comment.")
    # TODO: create an image diff grid, as in https://github.com/E3SM-Project/zppy/pull/685, for each min case
    for tr in test_results_dict.values():
        assert tr.image_count_total == tr.image_count_correct
