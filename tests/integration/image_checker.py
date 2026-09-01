import os
import shutil
from math import ceil
from typing import Dict, List, Tuple

import matplotlib.backends.backend_pdf
import matplotlib.image as mpimg
import numpy as np
from mache import MachineInfo
from matplotlib import pyplot as plt
from PIL import Image, ImageChops, ImageDraw, ImageFilter

# The FFT-based shift estimate in `_estimate_shift` can in principle return
# any shift up to half the image's width/height, but shifts larger than this
# are treated as genuine mismatches rather than harmless translations.
MAXIMUM_PIXEL_SHIFT = 10
MAXIMUM_MISMATCH_FRACTION = 0.0002

# `actual` and `expected` images are allowed to differ in size by up to this
# many pixels (in either dimension) before being treated as a guaranteed
# mismatch. Small differences like this are typically caused by
# DPI/layout-rounding changes between matplotlib/font versions rather than
# an actual change to the figure's content, and are corrected for by
# resizing `actual` to `expected`'s exact size before comparing.
MAXIMUM_SIZE_DIFFERENCE = 20

# `_get_zoned_mismatch_fractions` classifies every pixel as either "edge
# zone" (within EDGE_TOLERANCE_RADIUS pixels of a line, contour boundary,
# axis, or piece of text in the EXPECTED image) or "interior" (everything
# else: flat fills and backgrounds). Differences of up to
# DIFF_MAGNITUDE_THRESHOLD (out of 255) are ignored everywhere, since even
# genuinely identical images can differ by a few intensity levels once
# either has been resized (see MAXIMUM_SIZE_DIFFERENCE above) due to
# interpolation rounding. Beyond that:
#   - the interior must match almost exactly (MAXIMUM_INTERIOR_MISMATCH_FRACTION
#     of interior pixels), since a real data/content change is expected to
#     show up away from existing edges;
#   - the edge zone is allowed much more slop
#     (MAXIMUM_EDGE_ZONE_MISMATCH_FRACTION of edge-zone pixels), since
#     anti-aliasing and font-hinting differences between rendering
#     environments concentrate there, and how much of that noise appears
#     scales with how much line/contour/text content an image has - which
#     varies a lot from one plot to another. This mainly guards against
#     wholesale loss of edge-dense content (e.g. an entire legend or
#     contour set disappearing).
# These only classify pixels using the (pristine, never-resized) expected
# image, so resizing `actual` to correct a size difference never distorts
# the zone boundaries themselves - only the pixel values being compared.
#
# Note: a real content difference that is both small (roughly under 1-2% of
# the image) AND located inside an already edge-dense region (e.g. a subtle
# error tucked among existing contour lines) may not be caught by this
# check, since that is exactly the kind of location where rendering noise
# is expected and tolerated. There is no way to fully close this gap using
# only the rendered images; the mismatched-image diff grid remains useful
# for catching this narrow class of change by eye.
EDGE_GRADIENT_THRESHOLD = 20
EDGE_TOLERANCE_RADIUS = 3
DIFF_MAGNITUDE_THRESHOLD = 30
MAXIMUM_INTERIOR_MISMATCH_FRACTION = 0.005
MAXIMUM_EDGE_ZONE_MISMATCH_FRACTION = 0.5


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
        self.file_list_mismatched = sorted(file_list_mismatched)


# Specialized setup ###########################################################


def _get_unused_diff_dir(base_diff_dir: str) -> str:
    """Return a diff_dir path that does not already exist.

    If base_diff_dir does not exist, it is returned unchanged. Otherwise,
    a "_tryN" suffix (starting at N=2) is appended until an unused
    directory name is found. This prevents reruns of the image checker
    from overwriting the results of previous runs.
    """
    if not os.path.exists(base_diff_dir):
        return base_diff_dir
    try_number = 2
    while os.path.exists(f"{base_diff_dir}_try{try_number}"):
        try_number += 1
    return f"{base_diff_dir}_try{try_number}"


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
    base_diff_dir = (
        f"{actual_images_dir}image_check_failures_{cfg_specifier}{diff_dir_suffix}"
    )
    d: Dict[str, str] = {
        "actual_images_dir": actual_images_dir,
        "expected_images_dir": f"{expansions['expected_dir']}expected_{cfg_specifier}",
        "diff_dir": _get_unused_diff_dir(base_diff_dir),
        "expected_images_list": f"{expansions['expected_dir']}image_list_expected_{cfg_specifier}.txt",
    }
    if d["diff_dir"] != base_diff_dir:
        print(
            f"diff_dir={base_diff_dir} already exists; using {d['diff_dir']} instead to avoid overwriting previous results"
        )
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
    # Create image diff grid
    _make_image_diff_grid(diff_subdir)
    return test_results


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
            "| Test name | Total images | Correct images | Missing images | Mismatched images | \n"
        )
        f.write("| --- | --- | --- | --- | --- | \n")
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

            f.write(
                f"| {test_name} | {test_results.image_count_total} | {test_results.image_count_correct} | {missing_str} | {mismatched_str} | \n"
            )
    print(f"Copy the output of {output_file_path} to a Pull Request comment")


# Helper functions ############################################################


def _check_mismatched_images(
    parameters: Parameters,
    prefix: str,
) -> Results:
    missing_images: List[str] = []
    mismatched_images: List[str] = []

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
    print(f"Number of mismatched images: {len(mismatched_images)}")
    print(
        f"Number of correct images: {counter - len(missing_images) - len(mismatched_images)}"
    )
    test_results = Results(
        parameters.diff_dir, prefix, counter, missing_images, mismatched_images
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
):
    # https://stackoverflow.com/questions/35176639/compare-images-python-pil
    try:
        actual_png = Image.open(path_to_actual_png).convert("RGB")
    except FileNotFoundError:
        missing_images.append(image_name)
        return
    except Exception as e:
        print(f"Warning: could not open actual image {path_to_actual_png}: {e}")
        missing_images.append(image_name)
        return
    expected_png = Image.open(path_to_expected_png).convert("RGB")
    diff = ImageChops.difference(actual_png, expected_png)

    if not os.path.isdir(diff_dir):
        os.mkdir(diff_dir)

    bbox = diff.getbbox()
    if not bbox:
        # If `diff.getbbox()` is None, then the images are in theory equal
        assert diff.getbbox() is None
    else:
        fraction = _get_mismatched_fraction(diff, expected_png.size)
        # Fraction of mismatched pixels should be less than 0.02%
        if fraction >= MAXIMUM_MISMATCH_FRACTION and not _images_match_after_shift(
            actual_png, expected_png
        ):
            verbose = False
            if verbose:
                print("\npath_to_actual_png={}".format(path_to_actual_png))
                print("path_to_expected_png={}".format(path_to_expected_png))
                print("num_nonzero_pixels/num_pixels fraction={}".format(fraction))

            mismatched_images.append(image_name)

            diff_dir_actual_png = os.path.join(
                diff_dir, "{}_actual.png".format(image_name)
            )
            # image_name could contain a number of subdirectories.
            os.makedirs(os.path.dirname(diff_dir_actual_png), exist_ok=True)
            shutil.copy(
                path_to_actual_png,
                diff_dir_actual_png,
            )
            diff_dir_expected_png = os.path.join(
                diff_dir, "{}_expected.png".format(image_name)
            )
            # image_name could contain a number of subdirectories.
            os.makedirs(os.path.dirname(diff_dir_expected_png), exist_ok=True)
            shutil.copy(
                path_to_expected_png,
                diff_dir_expected_png,
            )
            # Draw red box around diff-area on each of: diff, actual, expected
            _draw_box(diff, diff, os.path.join(diff_dir, f"{image_name}_diff.png"))
            _draw_box(
                actual_png, diff, os.path.join(diff_dir, f"{image_name}_actual.png")
            )
            _draw_box(
                expected_png, diff, os.path.join(diff_dir, f"{image_name}_expected.png")
            )


def _get_mismatched_fraction(diff: Image.Image, size: Tuple[int, int]) -> float:
    # Sometimes, a few pixels will differ, but the two images appear identical.
    # https://codereview.stackexchange.com/questions/55902/fastest-way-to-count-non-zero-pixels-using-python-and-pillow
    bbox = diff.getbbox()
    if bbox is None:
        return 0.0
    nonzero_pixels = (
        diff.crop(bbox)
        .point(lambda x: 255 if x else 0)
        .convert("L")
        .point(bool)
        .getdata()
    )
    return sum(nonzero_pixels) / (size[0] * size[1])


def _images_match_after_shift(
    actual_png: Image.Image, expected_png: Image.Image
) -> bool:
    if actual_png.size != expected_png.size:
        width_difference = abs(actual_png.size[0] - expected_png.size[0])
        height_difference = abs(actual_png.size[1] - expected_png.size[1])
        if (
            width_difference > MAXIMUM_SIZE_DIFFERENCE
            or height_difference > MAXIMUM_SIZE_DIFFERENCE
        ):
            return False
        # A small size difference is typically caused by a DPI/layout
        # rounding change between rendering environments rather than an
        # actual change to the figure's content. Resizing introduces its
        # own interpolation noise, but `_get_zoned_mismatch_fractions`
        # (below) is specifically designed to tolerate that.
        actual_png = actual_png.resize(expected_png.size, Image.LANCZOS)

    # Rather than exhaustively trying every candidate shift (which costs up
    # to (2 * MAXIMUM_PIXEL_SHIFT + 1)^2 image diffs), use phase correlation
    # (an FFT-based technique) to find the single best-aligning shift in one
    # pass. See: https://en.wikipedia.org/wiki/Phase_correlation
    horizontal_shift, vertical_shift = _estimate_shift(actual_png, expected_png)
    if (
        abs(horizontal_shift) > MAXIMUM_PIXEL_SHIFT
        or abs(vertical_shift) > MAXIMUM_PIXEL_SHIFT
    ):
        return False

    if horizontal_shift == 0 and vertical_shift == 0:
        # No translation was found. This is not automatically a failure:
        # differences in anti-aliasing or font hinting between rendering
        # environments can leave a thin halo of mismatched pixels hugging
        # every line, contour boundary, and piece of text even when nothing
        # has actually moved. `_get_zoned_mismatch_fractions` (below) is
        # what determines whether that halo is small enough to ignore.
        actual_overlap, expected_overlap = actual_png, expected_png
    else:
        actual_overlap, expected_overlap = _get_overlapping_images(
            actual_png, expected_png, horizontal_shift, vertical_shift
        )

    interior_mismatch, edge_zone_mismatch = _get_zoned_mismatch_fractions(
        actual_overlap, expected_overlap
    )
    return (
        interior_mismatch < MAXIMUM_INTERIOR_MISMATCH_FRACTION
        and edge_zone_mismatch < MAXIMUM_EDGE_ZONE_MISMATCH_FRACTION
    )


def _get_edge_zone_mask(expected_png: Image.Image) -> np.ndarray:
    """Return a boolean array marking pixels on or near an edge in `expected_png`.

    `FIND_EDGES` is a Laplacian-style kernel that highlights lines, contour
    boundaries, axes, and text; thresholding its output identifies pixels
    that are part of some drawn feature rather than a flat fill or
    background. The result is dilated by EDGE_TOLERANCE_RADIUS so that
    pixels close to (not just exactly on) an edge are also marked. Using
    only the expected image (rather than, say, requiring an edge in both
    images) means this mask is unaffected by any blurring introduced by
    resizing `actual` to correct a size difference.
    """
    edges = expected_png.convert("L").filter(ImageFilter.FIND_EDGES)
    edge_array = np.asarray(edges, dtype=np.uint8)
    is_edge = edge_array > EDGE_GRADIENT_THRESHOLD
    mask_image = Image.fromarray((is_edge * 255).astype(np.uint8))
    dilated = mask_image.filter(ImageFilter.MaxFilter(2 * EDGE_TOLERANCE_RADIUS + 1))
    return np.asarray(dilated, dtype=bool)


def _get_zoned_mismatch_fractions(
    actual_png: Image.Image, expected_png: Image.Image
) -> Tuple[float, float]:
    """Return (interior_mismatch_fraction, edge_zone_mismatch_fraction).

    Every pixel is classified as "edge zone" or "interior" using
    `_get_edge_zone_mask`, and each fraction is computed relative to the
    size of its own zone (not the whole image), since how much of an image
    is edge/text content - and therefore how much rendering-noise halo it
    can accumulate - varies a lot between plot types. A per-pixel
    difference only counts as a mismatch if it exceeds
    DIFF_MAGNITUDE_THRESHOLD, since resizing alone introduces a few
    intensity levels of interpolation rounding even where content is
    genuinely identical.
    """
    diff_array = np.asarray(
        ImageChops.difference(actual_png, expected_png).convert("L"),
        dtype=np.float64,
    )
    edge_zone_mask = _get_edge_zone_mask(expected_png)
    interior_mask = ~edge_zone_mask
    exceeds_threshold = diff_array > DIFF_MAGNITUDE_THRESHOLD

    interior_pixel_count = max(int(np.sum(interior_mask)), 1)
    edge_zone_pixel_count = max(int(np.sum(edge_zone_mask)), 1)
    interior_mismatch_fraction = (
        float(np.sum(exceeds_threshold & interior_mask)) / interior_pixel_count
    )
    edge_zone_mismatch_fraction = (
        float(np.sum(exceeds_threshold & edge_zone_mask)) / edge_zone_pixel_count
    )
    return interior_mismatch_fraction, edge_zone_mismatch_fraction


def _estimate_shift(
    actual_png: Image.Image, expected_png: Image.Image
) -> Tuple[int, int]:
    # Use phase correlation to estimate the (horizontal, vertical) pixel
    # shift that best aligns `actual_png` with `expected_png`. This finds the
    # shift in a single FFT-based operation, regardless of how large the
    # shift is, rather than searching over every candidate shift.
    actual_array = np.asarray(actual_png.convert("L"), dtype=np.float64)
    expected_array = np.asarray(expected_png.convert("L"), dtype=np.float64)

    actual_fft = np.fft.fft2(actual_array)
    expected_fft = np.fft.fft2(expected_array)
    # The order here matters: this yields a peak at (horizontal_shift,
    # vertical_shift) such that actual(x, y) == expected(x + horizontal_shift,
    # y + vertical_shift), matching the convention used by
    # `_get_overlapping_images`.
    cross_power = expected_fft * np.conj(actual_fft)
    magnitude = np.abs(cross_power)
    # Avoid division by zero where the cross power is (near) zero.
    magnitude[magnitude < 1e-10] = 1e-10
    correlation = np.abs(np.fft.ifft2(cross_power / magnitude))

    height, width = correlation.shape
    peak_row, peak_col = np.unravel_index(np.argmax(correlation), correlation.shape)

    # The correlation surface wraps around at the image boundaries, so a peak
    # in the second half of the axis corresponds to a negative shift.
    horizontal_shift = int(peak_col)
    if horizontal_shift > width // 2:
        horizontal_shift -= width
    vertical_shift = int(peak_row)
    if vertical_shift > height // 2:
        vertical_shift -= height

    return horizontal_shift, vertical_shift


def _get_overlapping_images(
    actual_png: Image.Image,
    expected_png: Image.Image,
    horizontal_shift: int,
    vertical_shift: int,
) -> Tuple[Image.Image, Image.Image]:
    width, height = actual_png.size
    actual_left = max(0, -horizontal_shift)
    actual_upper = max(0, -vertical_shift)
    expected_left = max(0, horizontal_shift)
    expected_upper = max(0, vertical_shift)
    overlap_width = width - abs(horizontal_shift)
    overlap_height = height - abs(vertical_shift)
    actual_overlap = actual_png.crop(
        (
            actual_left,
            actual_upper,
            actual_left + overlap_width,
            actual_upper + overlap_height,
        )
    )
    expected_overlap = expected_png.crop(
        (
            expected_left,
            expected_upper,
            expected_left + overlap_width,
            expected_upper + overlap_height,
        )
    )
    return actual_overlap, expected_overlap


def _draw_box(image, diff, output_path: str):
    # https://stackoverflow.com/questions/41405632/draw-a-rectangle-and-a-text-in-it-using-pil
    draw = ImageDraw.Draw(image)
    left, upper, right, lower = (
        diff.getbbox()
    )  # We specifically want the diff's bounding box
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


def _make_image_diff_grid(diff_subdir, pdf_name="image_diff_grid.pdf", rows_per_page=2):
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
            count = page * rows_per_page + i
            if count > len(prefixes) - 1:
                break
            # We already know all the files are in `diff_subdir`; no need to repeat it.
            # short_title starts with a slash.
            short_title = prefixes[count].removeprefix(diff_subdir)
            print(f"short_title {i}: {short_title}")

            # Recall:
            # web_subdir does not start with a slash.
            # short_title starts with a slash.
            diff_url = f"{web_portal_base_url}/{web_subdir}{short_title}_diff.png"

            # Set title with hyperlink
            title = ax_row[1].set_title(short_title, fontsize=6, color="blue")
            title.set_url(diff_url)

            # Load and display images
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
