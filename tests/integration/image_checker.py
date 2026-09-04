import json
import os
import shutil
import textwrap
from math import ceil
from typing import Dict, List, Optional

import matplotlib.backends.backend_pdf
import matplotlib.image as mpimg
from mache import MachineInfo
from matplotlib import pyplot as plt
from PIL import Image, ImageChops, ImageDraw

from tests.integration import image_severity
from tests.integration.image_severity import Comparison


# Classes #####################################################################
class Parameters(object):
    def __init__(self, args: Dict[str, str]):
        self.actual_images_dir = args["actual_images_dir"]
        self.expected_images_dir = args["expected_images_dir"]
        self.diff_dir = args["diff_dir"]
        self.expected_images_list = args["expected_images_list"]


class Results(object):
    def __init__(
        self,
        diff_dir: str,
        prefix: str,
        image_count_total: int,
        file_list_missing: List[str],
        file_list_mismatched: List[str],
        comparisons: Optional[List[Comparison]] = None,
    ):
        if image_count_total == 0:
            raise ValueError(f"No images found for task {prefix} in {diff_dir}")
        self.diff_dir = diff_dir
        self.prefix = prefix
        self.image_count_total = image_count_total
        self.image_count_missing = len(file_list_missing)
        self.image_count_mismatched = len(file_list_mismatched)
        self.image_count_correct = (
            image_count_total - len(file_list_missing) - len(file_list_mismatched)
        )
        self.file_list_missing = sorted(file_list_missing)
        # Worst first, so a reviewer can work down the list and stop once the
        # remaining differences are clearly cosmetic.
        self.comparisons: List[Comparison] = comparisons or []
        by_severity = {c.image_name: c for c in self.comparisons}
        self.file_list_mismatched = sorted(
            file_list_mismatched,
            key=lambda name: (
                by_severity[name].sort_key() if name in by_severity else (0, 0.0)
            ),
        )
        self.severity_counts: Dict[str, int] = {}
        for comparison in self.comparisons:
            self.severity_counts[comparison.severity] = (
                self.severity_counts.get(comparison.severity, 0) + 1
            )
        # Cosmetic differences are reported but do not require review.
        self.image_count_cosmetic = self.severity_counts.get(
            image_severity.NEGLIGIBLE, 0
        )

    def severity_summary(self) -> str:
        """e.g. "2 structural, 15 major, 40 minor"."""
        parts = [
            f"{self.severity_counts[level]} {level.lower()}"
            for level in reversed(image_severity.SEVERITY_ORDER)
            if self.severity_counts.get(level)
        ]
        return ", ".join(parts) if parts else "none"


# Specialized setup ###########################################################


def set_up_and_run_image_checker(
    cfg_specifier: str,
    case_name: str,
    expansions: Dict,
    diff_dir_suffix: str,
    task_list: List[str],
    test_results_dict: Dict[str, Results],
):
    print(f"Image checking {cfg_specifier}")
    actual_images_dir = f"{expansions['user_www']}zppy_weekly_{cfg_specifier}_www/{expansions['unique_id']}/{case_name}/"
    d: Dict[str, str] = {
        "actual_images_dir": actual_images_dir,
        "expected_images_dir": f"{expansions['expected_dir']}expected_{cfg_specifier}",
        "diff_dir": f"{actual_images_dir}image_check_failures_{cfg_specifier}{diff_dir_suffix}",
        "expected_images_list": f"{expansions['expected_dir']}image_list_expected_{cfg_specifier}.txt",
    }
    print(f"Removing diff_dir={d['diff_dir']} to produce new results")
    if os.path.exists(d["diff_dir"]):
        try:
            shutil.rmtree(d["diff_dir"])
        except PermissionError:
            print(
                f"{d['diff_dir']} cannot be removed. Execute permissions are needed to remove files. Adding execute permission and trying again."
            )
            _chmod_recursive(d["diff_dir"], 0o744)
            shutil.rmtree(d["diff_dir"])
    print("Image checking dict:")
    for key in d:
        print(f"{key}: {d[key]}")
    parameters: Parameters = Parameters(d)
    for task in task_list:
        test_results = check_images(parameters, task)
        test_results_dict[f"{cfg_specifier}_{task}"] = test_results


# Everything below here could, in theory, be pulled out into an Image Checker package
# (or more likely, a zppy-interfaces entry point)
# Generalized image checking ##################################################


def check_images(parameters: Parameters, prefix: str):
    test_results = _check_mismatched_images(parameters, prefix)
    diff_subdir = f"{parameters.diff_dir}/{prefix}"
    if not os.path.exists(diff_subdir):
        os.makedirs(diff_subdir, exist_ok=True)
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
    # Rank and group the failures so a reviewer knows where to start
    _write_severity_report(diff_subdir, test_results)
    # Create image diff grid, worst failures first
    _make_image_diff_grid(
        diff_subdir,
        ordered_names=test_results.file_list_mismatched,
        labels={
            c.image_name: f"[{c.severity}] {c.cause}" for c in test_results.comparisons
        },
    )
    return test_results


def _write_severity_report(diff_subdir: str, test_results: Results) -> None:
    """Write a ranked, grouped summary plus the raw scores.

    The point of both files is to answer "where do I start?". The old flat
    list of every differing image could not.
    """
    comparisons = sorted(test_results.comparisons, key=Comparison.sort_key)
    needing_review = [c for c in comparisons if c.needs_review]

    with open(f"{diff_subdir}/severity_report.txt", "w") as f:
        f.write(f"Image check for {test_results.prefix}\n")
        f.write(f"{test_results.image_count_total} images compared\n")
        f.write(
            f"{test_results.image_count_cosmetic} cosmetic "
            f"(reported only, no review needed)\n"
        )
        f.write(f"{len(needing_review)} need review\n\n")

        # Most failures share a handful of root causes. Showing the groups
        # first means a reviewer can check one example instead of hundreds.
        f.write("Grouped by cause (check one example from each):\n")
        groups = image_severity.group_by_cause(needing_review)
        for (severity, cause), count in sorted(
            groups.items(), key=lambda item: -item[1]
        ):
            f.write(f"  {count:6d}  {severity:11s}  {cause}\n")

        f.write("\nWorst first:\n")
        for c in needing_review:
            f.write(f"  {c.severity:11s} {c.content_fraction:8.4f}  {c.image_name}\n")

    with open(f"{diff_subdir}/image_scores.json", "w") as f:
        json.dump(
            [
                {
                    "name": c.image_name,
                    "severity": c.severity,
                    "content_fraction": round(c.content_fraction, 6),
                    "geometry_change": round(c.geometry_change, 6),
                    "localized_pixels": c.localized_pixels,
                    "cause": c.cause,
                }
                for c in comparisons
            ],
            f,
            indent=1,
        )


def construct_markdown_summary_table(
    test_results_dict: Dict[str, Results], output_file_path: str
):
    machine_info = MachineInfo()
    config = machine_info.config
    web_portal_base_path = config.get(
        "web_portal", "base_path"
    )  # Does NOT include trailing "/"
    web_portal_base_url = config.get(
        "web_portal", "base_url"
    )  # Does NOT include trailing "/"
    with open(output_file_path, "w") as f:
        f.write("# Summary of test results\n\n")
        f.write(
            "| Test name | Total images | Correct images | Cosmetic only |"
            " Missing images | Needs review | Severity | \n"
        )
        f.write("| --- | --- | --- | --- | --- | --- | --- | \n")
        for test_name, test_results in test_results_dict.items():
            missing_str = f"{test_results.image_count_missing}"
            mismatched_str = f"{test_results.image_count_mismatched}"

            # test_results.diff_dir starts with the file path that is displayed on the web server.
            # That is, it starts with the web_portal_base_path

            web_link = ""
            diff_subdir = f"{test_results.diff_dir}/{test_results.prefix}"
            if test_results.diff_dir.startswith(web_portal_base_path):
                web_subdir = test_results.diff_dir.removeprefix(web_portal_base_path)
                web_link = f"{web_portal_base_url}/{web_subdir}/{test_results.prefix}"
            if web_link:
                has_missing: bool = test_results.image_count_missing > 0
                if has_missing:
                    if os.path.exists(f"{diff_subdir}/missing_images.txt"):
                        missing_str = f"{test_results.image_count_missing} ([list]({web_link}/missing_images.txt))"
                    else:
                        missing_str = (
                            f"{test_results.image_count_missing} (no list created)"
                        )
                has_mismatched: bool = test_results.image_count_mismatched > 0
                if has_mismatched:
                    mismatched_list_exists = os.path.exists(
                        f"{diff_subdir}/mismatched_images.txt"
                    )
                    image_diff_grid_exists = os.path.exists(
                        f"{diff_subdir}/image_diff_grid.pdf"
                    )
                    if mismatched_list_exists and image_diff_grid_exists:
                        mismatched_str = f"{test_results.image_count_mismatched} ([list]({web_link}/mismatched_images.txt), [grid]({web_link}/image_diff_grid.pdf))"
                    elif mismatched_list_exists:
                        mismatched_str = f"{test_results.image_count_mismatched} ([list]({web_link}/mismatched_images.txt), no grid created)"
                    elif image_diff_grid_exists:
                        mismatched_str = f"{test_results.image_count_mismatched} (no list created, [grid]({web_link}/image_diff_grid.pdf))"
                    else:
                        mismatched_str = f"{test_results.image_count_mismatched} (no list/grid created)"
                    if os.path.exists(f"{diff_subdir}/severity_report.txt"):
                        mismatched_str += f", [ranked]({web_link}/severity_report.txt)"

            f.write(
                f"| {test_name} | {test_results.image_count_total}"
                f" | {test_results.image_count_correct}"
                f" | {test_results.image_count_cosmetic}"
                f" | {missing_str} | {mismatched_str}"
                f" | {test_results.severity_summary()} | \n"
            )
    print(f"Copy the output of {output_file_path} to a Pull Request comment")


# Helper functions ############################################################


def _check_mismatched_images(
    parameters: Parameters,
    prefix: str,
) -> Results:
    missing_images: List[str] = []
    mismatched_images: List[str] = []
    comparisons: List[Comparison] = []

    counter = 0
    print(f"Opening expected images file {parameters.expected_images_list}")
    with open(parameters.expected_images_list) as f:
        print(f"Reading expected images file {parameters.expected_images_list}")
        for line in f:
            image_name = line.strip("./").strip("\n")
            if image_name.startswith(f"{prefix}/"):
                counter += 1
                if counter % 250 == 0:
                    print("On line #", counter)
                path_to_actual_png = os.path.join(
                    parameters.actual_images_dir, image_name
                )
                path_to_expected_png = os.path.join(
                    parameters.expected_images_dir, image_name
                )

                _compare_actual_and_expected(
                    missing_images,
                    mismatched_images,
                    image_name,
                    path_to_actual_png,
                    path_to_expected_png,
                    parameters.diff_dir,
                    comparisons,
                )

    verbose: bool = False
    if verbose:
        if missing_images:
            print("Missing images:")
            for i in missing_images:
                print(i)
        if mismatched_images:
            print("Mismatched images:")
            for i in mismatched_images:
                print(i)

    # Count summary
    print(f"Total: {counter}")
    print(f"Number of missing images: {len(missing_images)}")
    print(f"Number of images needing review: {len(mismatched_images)}")
    print(
        f"Number of correct images: {counter - len(missing_images) - len(mismatched_images)}"
    )
    test_results = Results(
        parameters.diff_dir,
        prefix,
        counter,
        missing_images,
        mismatched_images,
        comparisons,
    )

    # Make diff_dir readable
    if os.path.exists(parameters.diff_dir):
        # Execute permission for user is needed to remove diff_dir if we're re-running the image checks.
        # Execute permission for others is needed to make diff_dir visible on the web server.
        # 7 - rwx for user
        # 5 - r-x for group, others
        _chmod_recursive(parameters.diff_dir, 0o755)
    else:
        # diff_dir won't exist if all the expected images are missing
        # That is, if we're in this case, we expect the following:
        assert len(missing_images) == counter

    return test_results


def _compare_actual_and_expected(
    missing_images,
    mismatched_images,
    image_name,
    path_to_actual_png,
    path_to_expected_png,
    diff_dir,
    comparisons: Optional[List[Comparison]] = None,
):
    """Score one image pair and record it if a human needs to look at it."""
    comparison = image_severity.compare(
        image_name, path_to_actual_png, path_to_expected_png
    )
    if comparisons is not None:
        comparisons.append(comparison)

    if comparison.severity == image_severity.MISSING:
        missing_images.append(image_name)
        return

    if not comparison.needs_review:
        # Cosmetic only -- typically anti-aliasing that moved a fraction of a
        # pixel when matplotlib was upgraded. Counted in the summary, but not
        # worth a reviewer's time.
        return

    mismatched_images.append(image_name)
    _save_comparison_images(
        image_name, path_to_actual_png, path_to_expected_png, diff_dir
    )


def _save_comparison_images(
    image_name, path_to_actual_png, path_to_expected_png, diff_dir
):
    """Write actual, expected and diff images for one failure, boxed."""
    if not os.path.isdir(diff_dir):
        os.makedirs(diff_dir, exist_ok=True)

    actual_png = Image.open(path_to_actual_png).convert("RGB")
    expected_png = Image.open(path_to_expected_png).convert("RGB")
    diff = ImageChops.difference(actual_png, expected_png)

    diff_dir_actual_png = os.path.join(diff_dir, "{}_actual.png".format(image_name))
    # image_name could contain a number of subdirectories.
    os.makedirs(os.path.dirname(diff_dir_actual_png), exist_ok=True)
    shutil.copy(path_to_actual_png, diff_dir_actual_png)

    diff_dir_expected_png = os.path.join(diff_dir, "{}_expected.png".format(image_name))
    os.makedirs(os.path.dirname(diff_dir_expected_png), exist_ok=True)
    shutil.copy(path_to_expected_png, diff_dir_expected_png)

    # Draw red box around diff-area on each of: diff, actual, expected
    _draw_box(diff, diff, os.path.join(diff_dir, f"{image_name}_diff.png"))
    _draw_box(actual_png, diff, os.path.join(diff_dir, f"{image_name}_actual.png"))
    _draw_box(expected_png, diff, os.path.join(diff_dir, f"{image_name}_expected.png"))


def _draw_box(image, diff, output_path: str):
    # https://stackoverflow.com/questions/41405632/draw-a-rectangle-and-a-text-in-it-using-pil
    draw = ImageDraw.Draw(image)
    # We specifically want the diff's bounding box.
    bbox = diff.getbbox()
    if bbox is not None:
        left, upper, right, lower = bbox
        draw.rectangle(((left, upper), (right, lower)), outline="red")
    image.save(output_path, "PNG")


def _chmod_recursive(path: str, mode):
    root: str
    dirs: List[str]
    files: List[str]
    for root, dirs, files in os.walk(path):
        for name in dirs:
            dir_path: str = os.path.join(root, name)
            os.chmod(dir_path, mode)
        for name in files:
            file_path: str = os.path.join(root, name)
            os.chmod(file_path, mode)
    # Also chmod the root directory itself
    os.chmod(path, mode)


def _make_image_diff_grid(
    diff_subdir,
    pdf_name="image_diff_grid.pdf",
    rows_per_page=2,
    ordered_names: Optional[List[str]] = None,
    labels: Optional[Dict[str, str]] = None,
):
    """
    Path definitions:
    z = x.removeprefix(y) => x = y + z

    diff_subdir     = web_portal_base_path + web_subdir
    pdf_path        = diff_subdir + "/" + pdf_name
    prefixes[count] = diff_subdir + short_title

    pdf_url  = web_portal_base_url + "/" + web_subdir + "/" + pdf_name
    diff_url = web_portal_base_url + "/" + web_subdir + short_title + "_diff.png"

    Example:

    Given:
    short_title = /lnd_monthly_mvm_lnd/model_vs_model_1982-1983/lat_lon_land/Physical State/v2.LR.historical_0201-SNOINTABS-DJF-global.png

    pdf_url = https://web.lcrc.anl.gov/public/e3sm/diagnostic_output//ac.forsyth2/zppy_weekly_comprehensive_v2_www/test-zppy-diags-1019-xc-break/v2.LR.historical_0201/image_check_failures_comprehensive_v2/e3sm_diags/image_diff_grid.pdf

    Then:
    web_portal_base_url + "/" + web_subdir = https://web.lcrc.anl.gov/public/e3sm/diagnostic_output//ac.forsyth2/zppy_weekly_comprehensive_v2_www/test-zppy-diags-1019-xc-break/v2.LR.historical_0201/image_check_failures_comprehensive_v2/e3sm_diags/

    diff_url = web_portal_base_url + "/" + web_subdir + short_title  + "_diff.png" = https://web.lcrc.anl.gov/public/e3sm/diagnostic_output//ac.forsyth2/zppy_weekly_comprehensive_v2_www/test-zppy-diags-1019-xc-break/v2.LR.historical_0201/image_check_failures_comprehensive_v2/e3sm_diags/lnd_monthly_mvm_lnd/model_vs_model_1982-1983/lat_lon_land/Physical State/v2.LR.historical_0201-SNOINTABS-DJF-global.png_diff.png
    """
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
    # web_subdir does NOT start with a slash.
    web_subdir = diff_subdir.removeprefix(web_portal_base_path)
    print(f"Web page will be at:\n{web_portal_base_url}/{web_subdir}/{pdf_name}")

    prefixes = []
    label_by_prefix: Dict[str, str] = {}
    if ordered_names:
        # Keep the caller's order, which is worst failure first.
        diff_dir = diff_subdir.removesuffix("/" + os.path.basename(diff_subdir))
        for name in ordered_names:
            candidate = f"{diff_dir}/{name}"
            if os.path.exists(f"{candidate}_diff.png"):
                prefixes.append(candidate)
                if labels and name in labels:
                    label_by_prefix[candidate] = labels[name]
    if not prefixes:
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
        # squeeze=False keeps `axes` two-dimensional even when rows_per_page
        # is 1, so the row loop below works for any page size.
        fig, axes = plt.subplots(rows_per_page, cols, squeeze=False)
        print(f"Page {page}")
        for i, ax_row in enumerate(axes):
            count = page * rows_per_page + i
            if count > len(prefixes) - 1:
                # The last page is usually not full. Hide the leftover axes,
                # or they are drawn as confusing empty boxes.
                for unused_row in axes[i:]:
                    for unused_ax in unused_row:
                        unused_ax.set_visible(False)
                break
            # We already know all the files are in `diff_subdir`; no need to repeat it.
            # short_title starts with a slash.
            short_title = prefixes[count].removeprefix(diff_subdir)
            print(f"short_title {i}: {short_title}")

            # Recall:
            # web_subdir does not start with a slash.
            # short_title starts with a slash.
            diff_url = f"{web_portal_base_url}/{web_subdir}{short_title}_diff.png"

            # Lead with the severity and likely cause so the reader can see
            # how far down the ranking they are and which group this belongs
            # to. Wrap the path, or it runs off both edges of the page.
            prefix_label = label_by_prefix.get(prefixes[count])
            wrapped = "\n".join(textwrap.wrap(short_title, width=95))
            heading = f"{prefix_label}\n{wrapped}" if prefix_label else wrapped
            title = ax_row[1].set_title(heading, fontsize=5, color="blue")
            title.set_url(diff_url)

            # Load and display images, naming each column so the reader does
            # not have to remember which is which.
            for ax, kind in zip(ax_row, ("actual", "expected", "diff")):
                ax.imshow(mpimg.imread(f"{prefixes[count]}_{kind}.png"))
                ax.set_xticks([])
                ax.set_yticks([])
                ax.set_xlabel(kind, fontsize=5)
        fig.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)
    pdf.close()
    plt.close("all")
    print(f"Reminder:\n{web_portal_base_url}/{web_subdir}/{pdf_name}")
