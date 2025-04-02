import os
from math import ceil
from typing import Dict

import matplotlib.backends.backend_pdf
import matplotlib.image as mpimg
from mache import MachineInfo
from matplotlib import pyplot as plt

from tests.integration.utils import Results, check_mismatched_images, get_expansions

V3_CASE_NAME = "v3.LR.historical_0051"
V2_CASE_NAME = "v2.LR.historical_0201"


# TODO: fix issue where blank plots generate after so many pages in the PDF
def make_image_diff_grid(diff_subdir, pdf_name="image_diff_grid.pdf", rows_per_page=2):
    machine_info = MachineInfo()
    web_portal_base_path = machine_info.config.get("web_portal", "base_path")
    web_portal_base_url = machine_info.config.get("web_portal", "base_url")
    print(f"web_portal_base_path: {web_portal_base_path}")
    print(f"web_portal_base_url: {web_portal_base_url}")
    print(f"Making image diff grid for {diff_subdir}")

    if not diff_subdir.startswith(web_portal_base_path):
        print(
            f"diff_subdir {diff_subdir} is not a subdir of web_portal_base_path: {web_portal_base_path}"
        )
        return
    pdf_path = f"{diff_subdir}/{pdf_name}"
    pdf = matplotlib.backends.backend_pdf.PdfPages(pdf_path)
    print(f"Saving to:\n{pdf_path}")
    web_subdir = diff_subdir.removeprefix(web_portal_base_path)
    print(f"Web page will be at:\n{web_portal_base_url}/{web_subdir}/{pdf_name}")

    prefixes = []
    # print(f"Walking diff_subdir: {diff_subdir}")
    for root, _, files in os.walk(diff_subdir):
        # print(f"root: {root}")
        for file_name in files:
            # print(f"file_name: {file_name}")
            if file_name.endswith("_diff.png"):
                prefixes.append(f"{root}/{file_name.split('_diff.png')[0]}")
    rows = len(prefixes)
    if rows == 0:
        # No diffs to collect into a PDF
        return
    cols = 3  # actual, expected, diff
    print(f"Constructing a {rows}x{cols} grid of image diffs")

    num_pages = ceil(rows / rows_per_page)
    for page in range(num_pages):
        fig, axes = plt.subplots(rows_per_page, cols)
        print(f"Page {page}")
        for i, ax_row in enumerate(axes):
            count = page * 3 + i
            if count > len(prefixes) - 1:
                break
            # We already know all the files are in `diff_subdir`; no need to repeat it.
            short_title = prefixes[count].removeprefix(diff_subdir)
            print(f"short_title {i}: {short_title}")
            ax_row[1].set_title(short_title, fontsize=6)
            img = mpimg.imread(f"{prefixes[count]}_actual.png")
            ax_row[0].imshow(img)
            ax_row[0].set_xticks([])
            ax_row[0].set_yticks([])
            img = mpimg.imread(f"{prefixes[count]}_expected.png")
            ax_row[1].imshow(img)
            ax_row[1].set_xticks([])
            ax_row[1].set_yticks([])
            img = mpimg.imread(f"{prefixes[count]}_diff.png")
            ax_row[2].imshow(img)
            ax_row[2].set_xticks([])
            ax_row[2].set_yticks([])
        fig.tight_layout()
        pdf.savefig(1)
        plt.close(fig)
    pdf.close()
    plt.close("all")
    print(f"Reminder:\n{web_portal_base_url}/{web_subdir}/{pdf_name}")


def check_images(expansions, cfg_specifier, case_name, task, diff_dir_suffix=""):
    expected_dir = expansions["expected_dir"]
    user_www = expansions["user_www"]
    unique_id = expansions["unique_id"]
    actual_images_dir = (
        f"{user_www}zppy_weekly_{cfg_specifier}_www/{unique_id}/{case_name}/"
    )

    # The expected_images_file lists all images we expect to compare.
    expected_images_file = f"{expected_dir}image_list_expected_{cfg_specifier}.txt"
    expected_images_dir = f"{expected_dir}expected_{cfg_specifier}"

    # The directory to place differences in.
    diff_dir = (
        f"{actual_images_dir}image_check_failures_{cfg_specifier}{diff_dir_suffix}"
    )

    test_results = check_mismatched_images(
        actual_images_dir,
        expected_images_file,
        expected_images_dir,
        diff_dir,
        task,
    )
    diff_subdir = f"{diff_dir}/{task}"
    if os.path.exists(diff_subdir):
        # Write missing and mismatched images to files
        missing_images_file = f"{diff_subdir}/missing_images.txt"
        if os.path.exists(missing_images_file):
            os.remove(missing_images_file)
        for missing_image in test_results.file_list_missing:
            with open(missing_images_file, "a") as f:
                f.write(f"{missing_image}\n")
        mismatched_images_file = f"{diff_subdir}/mismatched_images.txt"
        if os.path.exists(mismatched_images_file):
            os.remove(mismatched_images_file)
        for mismatched_image in test_results.file_list_mismatched:
            with open(mismatched_images_file, "a") as f:
                f.write(f"{mismatched_image}\n")
        # Create image diff grid
        # make_image_diff_grid(diff_subdir)
    else:
        print(f"Diff subdir {diff_subdir} does not exist.")
    return test_results


def construct_markdown_summary_table(
    test_results_dict: Dict[str, Results], output_file_path: str
):
    with open(output_file_path, "w") as f:
        f.write("# Summary of test results\n\n")
        f.write(
            "Diff subdir is where to find the lists of missing/mismatched images, the image diff grid, and the individual diffs.\n"
        )
        f.write("Note image diff grids can not yet be constructed automatically.\n")
        f.write(
            "| Test name | Total images | Correct images | Missing images | Mismatched images | Diff subdir | \n"
        )
        f.write("| --- | --- | --- | --- | --- | --- | \n")
        for test_name, test_results in test_results_dict.items():
            f.write(
                f"| {test_name} | {test_results.image_count_total} | {test_results.image_count_correct} | {test_results.image_count_missing} | {test_results.image_count_mismatched} | {test_results.diff_dir}/{test_results.task} | \n"
            )


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
        print("Image checking comprehensive_v2")
        for task in ["e3sm_diags", "mpas_analysis", "global_time_series", "ilamb"]:
            test_results = check_images(
                expansions,
                "comprehensive_v2",
                V2_CASE_NAME,
                task,
                diff_dir_suffix=diff_dir_suffix,
            )
            test_results_dict[f"comprehensive_v2_{task}"] = test_results
        print("Image checking comprehensive_v3")
        for task in ["e3sm_diags", "mpas_analysis", "global_time_series", "ilamb"]:
            test_results = check_images(
                expansions,
                "comprehensive_v3",
                V3_CASE_NAME,
                task,
                diff_dir_suffix=diff_dir_suffix,
            )
            test_results_dict[f"comprehensive_v3_{task}"] = test_results
        print("Image checking bundles")
        for task in ["e3sm_diags", "global_time_series", "ilamb"]:  # No mpas_analysis
            test_results = check_images(
                expansions,
                "bundles",
                V3_CASE_NAME,
                task,
                diff_dir_suffix=diff_dir_suffix,
            )
            test_results_dict[f"bundles_{task}"] = test_results
    except Exception as e:
        construct_markdown_summary_table(
            test_results_dict, "early_test_images_summary.md"
        )
        raise e
    md_path = "test_images_summary.md"
    construct_markdown_summary_table(test_results_dict, md_path)
    print(f"Copy output of {md_path} to a PR comment.")
    for tr in test_results_dict.values():
        assert tr.image_count_total == tr.image_count_correct
