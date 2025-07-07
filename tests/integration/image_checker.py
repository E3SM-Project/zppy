import os
import shutil
from math import ceil
from typing import Any, Dict, List, Tuple

import cv2
import matplotlib.backends.backend_pdf
import matplotlib.image as mpimg
import numpy as np
from mache import MachineInfo
from matplotlib import pyplot as plt
from PIL import Image, ImageChops, ImageDraw
from sklearn.cluster import DBSCAN, AgglomerativeClustering, KMeans
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.preprocessing import StandardScaler


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


def check_images(parameters: Parameters, prefix: str, cv_dict: Dict[str, Any] = {}):
    if cv_dict:
        test_results = _cv_check_mismatched_images(parameters, prefix, cv_dict)
    else:
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
    # _make_image_diff_grid(diff_subdir)
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
                f"| {test_name} | {test_results.image_count_total} | {test_results.image_count_correct} | {test_results.image_count_missing} | {test_results.image_count_mismatched} | {test_results.diff_dir}/{test_results.prefix} | \n"
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
            proceed = False
            if image_name.startswith(prefix):
                proceed = True
            if proceed:
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
    expected_png = Image.open(path_to_expected_png).convert("RGB")
    diff = ImageChops.difference(actual_png, expected_png)

    if not os.path.isdir(diff_dir):
        os.mkdir(diff_dir)

    bbox = diff.getbbox()
    if not bbox:
        # If `diff.getbbox()` is None, then the images are in theory equal
        assert diff.getbbox() is None
    else:
        # Sometimes, a few pixels will differ, but the two images appear identical.
        # https://codereview.stackexchange.com/questions/55902/fastest-way-to-count-non-zero-pixels-using-python-and-pillow
        nonzero_pixels = (
            diff.crop(bbox)
            .point(lambda x: 255 if x else 0)
            .convert("L")
            .point(bool)
            .getdata()
        )
        num_nonzero_pixels = sum(nonzero_pixels)
        width, height = expected_png.size
        num_pixels = width * height
        fraction = num_nonzero_pixels / num_pixels
        # Fraction of mismatched pixels should be less than 0.02%
        if fraction >= 0.0002:
            verbose = False
            if verbose:
                print("\npath_to_actual_png={}".format(path_to_actual_png))
                print("path_to_expected_png={}".format(path_to_expected_png))
                print("diff has {} nonzero pixels.".format(num_nonzero_pixels))
                print("total number of pixels={}".format(num_pixels))
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


def _draw_box(image, diff, output_path: str):
    # https://stackoverflow.com/questions/41405632/draw-a-rectangle-and-a-text-in-it-using-pil
    draw = ImageDraw.Draw(image)
    (left, upper, right, lower) = (
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


# TODO: fix issue where blank plots generate after so many pages in the PDF
def _make_image_diff_grid(diff_subdir, pdf_name="image_diff_grid.pdf", rows_per_page=2):
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


# CV proof-of-concept #########################################################


def cv_prototype(try_num: int, cv_dict: Dict[str, Any]):
    print("Computer Vision Prototype for image checker")
    """
    cd /lcrc/group/e3sm/public_html/diagnostic_output/ac.forsyth2
    mkdir -p cv_prototype/actual_from_20250613/e3sm_diags/
    cp -r zppy_weekly_comprehensive_v3_www/test_weekly_20250613/v3.LR.historical_0051/e3sm_diags/atm_monthly_180x360_aave cv_prototype/actual_from_20250613/e3sm_diags/
    ls cv_prototype/actual_from_20250613/e3sm_diags/atm_monthly_180x360_aave/model_vs_obs_1987-1988/
    # Contains the different sets, good
    """
    actual_images_dir: str = (
        "/lcrc/group/e3sm/public_html/diagnostic_output/ac.forsyth2/cv_prototype/actual_from_20250613"
    )
    """
    cd /lcrc/group/e3sm/public_html/diagnostic_output/ac.forsyth2
    mkdir -p cv_prototype/expected_from_unified/e3sm_diags/
    cp -r /lcrc/group/e3sm/public_html/zppy_test_resources_previous/expected_results_for_unified_1.11.1/expected_comprehensive_v3/e3sm_diags/atm_monthly_180x360_aave cv_prototype/expected_from_unified/e3sm_diags/
    ls cv_prototype/expected_from_unified/e3sm_diags/atm_monthly_180x360_aave/model_vs_obs_1987-1988/
    # Contains the different sets, good
    """
    expected_images_dir: str = (
        "/lcrc/group/e3sm/public_html/diagnostic_output/ac.forsyth2/cv_prototype/expected_from_unified"
    )
    diff_dir: str = (
        f"/lcrc/group/e3sm/public_html/diagnostic_output/ac.forsyth2/cv_prototype/diff_try{try_num}"
    )
    """
    cd cv_prototype/expected_from_unified/
    find . -type f -name '*.png' > ../image_list_expected.txt
    cd ..
    ls
    # actual_from_20250613  expected_from_unified  image_list_expected.txt
    """
    expected_images_list: str = (
        "/lcrc/group/e3sm/public_html/diagnostic_output/ac.forsyth2/cv_prototype/image_list_expected.txt"
    )
    d: Dict[str, str] = {
        "actual_images_dir": actual_images_dir,
        "expected_images_dir": expected_images_dir,
        "diff_dir": diff_dir,
        "expected_images_list": expected_images_list,
    }
    print(f"Removing diff_dir={d['diff_dir']} to produce new results")
    if os.path.exists(d["diff_dir"]):
        print(f"{d['diff_dir']} exists, increment try_num={try_num+1}")
    print("Image checking dict:")
    for key in d:
        print(f"{key}: {d[key]}")
    parameters: Parameters = Parameters(d)
    # TODO: if/when merging, do the following:
    # To use the CV-version of the image checker for actual integration testing,
    # we'd simply need to update `set_up_and_run_image_checker` from
    # `check_images(parameters, task)` to `check_images(parameters, task, use_cv=cv_dict)`
    test_results: Results = check_images(parameters, "e3sm_diags", cv_dict=cv_dict)
    # Try                       | Total | Correct | Missing | Mismatched | Notes
    # 1,2: original             | 1713 | 1644    | 12       | 57         |
    # 7,9: compute_diff_image   | 1713 | 1632    | 12       | 69         | +12 mismatched
    # 29,30,31,32: clustering   | 1713 | 1632    | 12       | 69         |
    print(f"Done with try {try_num}")
    assert test_results.image_count_total == 1713
    assert test_results.image_count_missing == 12
    assert test_results.image_count_mismatched == 69
    assert test_results.image_count_correct == 1632


def _cv_check_mismatched_images(
    parameters: Parameters, prefix: str, cv_dict: Dict[str, Any]
) -> Results:
    missing_images: List[str] = []
    mismatched_images: List[str] = []
    features: List[np.ndarray] = []
    diff_image_paths: List[str] = []

    counter = 0
    print(f"Opening expected images file {parameters.expected_images_list}")
    with open(parameters.expected_images_list) as f:
        print(f"Reading expected images file {parameters.expected_images_list}")
        # Step 1: Process all pairs and collect diff regions
        for line in f:
            image_name = line.strip("./").strip("\n")
            if image_name.startswith(prefix):
                counter += 1
                if counter % 250 == 0:
                    print("On line #", counter)
                path_to_actual_png = os.path.join(
                    parameters.actual_images_dir, image_name
                )
                path_to_expected_png = os.path.join(
                    parameters.expected_images_dir, image_name
                )

                # Compare a single image's actual & expected, compute diffs
                _cv_compare_actual_and_expected(
                    missing_images,
                    mismatched_images,
                    image_name,
                    path_to_actual_png,
                    path_to_expected_png,
                    parameters.diff_dir,
                    features,
                    diff_image_paths,
                    cv_dict,
                )

    # Compare all the diffs we found
    # Pass in parallel lists: features & diff_image_paths
    group_diffs(features, diff_image_paths, parameters.diff_dir, cv_dict)

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


def _cv_compare_actual_and_expected(
    missing_images: List[str],
    mismatched_images: List[str],
    image_name: str,
    path_to_actual_png: str,
    path_to_expected_png: str,
    diff_dir: str,
    features: List[np.ndarray],
    diff_image_paths: List[str],
    cv_dict: Dict[str, Any],
):
    if not os.path.exists(path_to_actual_png):
        missing_images.append(image_name)
        return

    # The image is present in actual; let's see if it matches expected
    actual_image: np.ndarray
    expected_image: np.ndarray
    actual_image, expected_image = get_images(path_to_actual_png, path_to_expected_png)
    diff: np.ndarray
    mask: np.ndarray
    diff, mask = compute_diff_image(actual_image, expected_image, cv_dict)
    if not mask.any():
        # Images are close enough, call it a match
        return

    # The image does NOT match expected; let's compute the diff
    mismatched_images.append(image_name)
    diff_dir_paths: Dict[str, str] = write_images(
        diff_dir, image_name, path_to_actual_png, path_to_expected_png, diff
    )
    # Update the parallel lists diff_image_paths & features
    diff_image_paths.append(diff_dir_paths["diff"])
    update_features(actual_image, diff, features, cv_dict)


def get_images(
    path_to_actual_png: str, path_to_expected_png: str
) -> Tuple[np.ndarray, np.ndarray]:
    actual_image: np.ndarray = cv2.imread(str(path_to_actual_png))
    if actual_image is None:
        raise ValueError(f"cv2.imread failed to read {path_to_actual_png}")
    expected_image: np.ndarray = cv2.imread(str(path_to_expected_png))
    return actual_image, expected_image


def compute_diff_image(
    actual_image: np.ndarray, expected_image: np.ndarray, cv_dict: Dict[str, Any]
) -> Tuple[np.ndarray, np.ndarray]:
    # Ensure both images are the same size
    if expected_image.shape != actual_image.shape:
        raise ValueError(
            f"Images must be the same size. Expected shape={expected_image.shape}, actual shape={actual_image.shape}"
        )
    diff: np.ndarray = cv2.absdiff(expected_image, actual_image)
    if len(diff.shape) != 3:
        raise ValueError(f"diff.shape={diff.shape} should have 3 dimensions")
    gray_diff: np.ndarray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    if len(gray_diff.shape) != 2:
        raise ValueError(f"gray_diff.shape={gray_diff.shape} should have 2 dimensions")
    mask: np.ndarray
    # Before, we filtered based on `if fraction >= 0.0002`
    # That is, the fraction of mismatched pixels should be less than 0.02%
    # This is a little different.
    # Here, we're seeing how high the grayscale value is for each pixel in the diff.
    # If it's > gray_diff_threshold, we add it to the mask.
    _, mask = cv2.threshold(
        gray_diff, cv_dict["gray_diff_threshold"], 255, cv2.THRESH_BINARY
    )
    if len(mask.shape) != 2:
        raise ValueError(f"mask.shape={mask.shape} should have 2 dimensions")
    return diff, mask


def write_images(
    diff_dir: str,
    image_name: str,
    path_to_actual_png: str,
    path_to_expected_png: str,
    diff: np.ndarray,
) -> Dict[str, str]:
    diff_dir_paths: Dict[str, str] = {
        "actual": os.path.join(diff_dir, f"{image_name}_actual.png"),
        "expected": os.path.join(diff_dir, f"{image_name}_expected.png"),
        "diff": os.path.join(diff_dir, f"{image_name}_diff.png"),
    }

    # image_name could contain a number of subdirectories under diff_dir
    # So, let's be sure to make them.
    os.makedirs(os.path.dirname(diff_dir_paths["actual"]), exist_ok=True)

    shutil.copy(path_to_actual_png, diff_dir_paths["actual"])
    shutil.copy(
        path_to_expected_png,
        diff_dir_paths["expected"],
    )
    cv2.imwrite(diff_dir_paths["diff"], diff)

    return diff_dir_paths


def update_features(
    actual_image: np.ndarray,
    diff: np.ndarray,
    features: List[np.ndarray],
    cv_dict: Dict[str, Any],
):
    diff_feat: np.ndarray = extract_features(diff, cv_dict)
    if cv_dict["extract_diff_features_only"]:
        features.append(diff_feat)
    else:
        actual_feat: np.ndarray = extract_features(actual_image, cv_dict)
        combined_feat: np.ndarray = np.concatenate([actual_feat, diff_feat])
        features.append(combined_feat)


def extract_features(img: np.ndarray, cv_dict: Dict[str, Any]) -> np.ndarray:
    bins: int
    if cv_dict["feature_extraction_algorithm"] == "simple_hist":
        # Extract a normalized color histogram from an image.
        bins = cv_dict["simple_hist_bins"]
        hist = cv2.calcHist(
            [img], [0, 1, 2], None, [bins, bins, bins], [0, 180, 0, 256, 0, 256]
        )
        hist = cv2.normalize(hist, hist).flatten()
        return hist
    elif cv_dict["feature_extraction_algorithm"] == "combined_features":
        """
        Color histograms: Capture the “what” (which colors are present).
        Spatial features: Capture the “where” (location of non-zero/colorful regions).
        Combined features: Enable the clustering algorithm to group images based on both criteria.
        """
        bins = cv_dict["combined_features_bins"]
        thirds: int = 3
        split_imgs = np.array_split(img, thirds, axis=0)
        features = []
        nonzero_counts = []
        for part in split_imgs:
            hist = cv2.calcHist(
                [part], [0, 1, 2], None, [bins, bins, bins], [0, 180, 0, 256, 0, 256]
            )
            hist = cv2.normalize(hist, hist).flatten()
            features.append(hist)
            # Grayscale for non-zero detection
            gray = cv2.cvtColor(part, cv2.COLOR_BGR2GRAY) if part.ndim == 3 else part
            nonzero_counts.append(np.count_nonzero(gray))
        return np.concatenate(features + [np.array(nonzero_counts, dtype=np.float32)])
    elif cv_dict["feature_extraction_algorithm"] == "sector_slice":
        if img.ndim == 3:  # Convert to grayscale if needed
            img = img.max(axis=2)
            H, W = img.shape
            sector_slices = get_sector_slices(H, W)
            features = []
            for s in sector_slices:
                sector = img[s[0], s[1]]
                features.append(int(np.any(sector > 0)))
            return np.array(features, dtype=np.uint8)  # shape: (15,)
    else:
        raise ValueError(
            f"Invalid feature_extraction_algorithm={cv_dict['feature_extraction_algorithm']}"
        )


def get_sector_slices(img_h, img_w):
    # Example: hardcoded values, adjust to your layout!
    thirds = np.linspace(0, img_h, 4, dtype=int)
    segment_h = img_h // 8
    segment_w = img_w // 8
    top_bound = segment_h
    bottom_bound = img_h - segment_h
    left_bound = segment_w
    right_bound = img_w - segment_w
    # IMPORTANT!
    # These sector definitions are extremely rough and do not translate well amongst plot types
    sector_defs = [
        # (y_start, y_end, x_start, x_end)
        ("title", 0, top_bound, 0, img_w),
        ("plot", top_bound, bottom_bound, left_bound, right_bound),
        ("y_axis", top_bound, bottom_bound, 0, left_bound),
        ("x_axis", bottom_bound, img_h, left_bound, right_bound),
        ("colorbar", 0, img_h, right_bound, img_w),
    ]
    slices = []
    for i in range(3):  # For each plot
        y0, _ = thirds[i], thirds[i + 1]
        for _, rel_y0, rel_y1, x0, x1 in sector_defs:
            sector_slice = (slice(y0 + rel_y0, y0 + rel_y1), slice(x0, x1))
            slices.append(sector_slice)
    return slices


def group_diffs(
    features: List[np.ndarray],
    diff_image_paths: List[str],
    diff_dir: str,
    cv_dict: Dict[str, Any],
):
    clusters_subdir: str = os.path.join(diff_dir, "clusters")
    os.makedirs(clusters_subdir)
    features = preprocess_diffs(clusters_subdir, features, cv_dict)
    labels: np.ndarray = run_cluster_algorithm(features, cv_dict)

    # Group diff_image_paths by cluster label
    clusters: Dict[str, List[str]] = {}
    idx: int
    cluster_name: str
    for idx, cluster_name in enumerate(labels):
        if cluster_name == -1:
            # -1 is noise in DBSCAN; treat as its own group
            cluster_name = "noise"
        clusters.setdefault(cluster_name, []).append(diff_image_paths[idx])
    if not clusters:
        raise ValueError("Likely, no labels were produced by fit_predict")
    for cluster_name in clusters:
        cluster_file_path: str = os.path.join(
            clusters_subdir, f"cluster_{cluster_name}.txt"
        )
        this_cluster_subdir: str = os.path.join(
            clusters_subdir, f"dir_cluster_{cluster_name}"
        )
        os.makedirs(this_cluster_subdir)
        with open(cluster_file_path, "w") as cluster_file:
            # Write all the diffs that are part of this cluster.
            for diff_image_path in clusters[cluster_name]:
                diff_image_path_suffix = copy_to_cluster_subdir(
                    diff_image_path, diff_dir, this_cluster_subdir
                )
                cluster_file.write(f"{diff_image_path_suffix}\n")

                computed_actual_path = diff_image_path.replace(
                    "_diff.png", "_actual.png"
                )
                copy_to_cluster_subdir(
                    computed_actual_path, diff_dir, this_cluster_subdir
                )

                computed_expected_path = diff_image_path.replace(
                    "_diff.png", "_expected.png"
                )
                copy_to_cluster_subdir(
                    computed_expected_path, diff_dir, this_cluster_subdir
                )


def preprocess_diffs(
    clusters_subdir: str, features: List[np.ndarray], cv_dict: Dict[str, Any]
) -> List[np.ndarray]:
    if cv_dict["scale_features"]:
        scaler = StandardScaler()
        features = scaler.fit_transform(features)
    if cv_dict["reduce_dimensions"]:
        pca = PCA(n_components=10)
        features = pca.fit_transform(features)
    if cv_dict["plot_features"]:
        tsne = TSNE(n_components=2, random_state=42)
        features_2d = tsne.fit_transform(features)
        plt.figure(figsize=(8, 6))
        plt.scatter(features_2d[:, 0], features_2d[:, 1], s=10)
        plt.title("t-SNE projection of features")
        plt.xlabel("Component 1")
        plt.ylabel("Component 2")
        plt.tight_layout()
        file_path: str = os.path.join(clusters_subdir, "feature_space_tsne.png")
        plt.savefig(file_path, dpi=150)  # Save to file
        plt.close()  # Close the figure to free memory
    return features


def run_cluster_algorithm(
    features: List[np.ndarray], cv_dict: Dict[str, Any]
) -> np.ndarray:
    labels: np.ndarray
    n_clusters: int = cv_dict["n_clusters"]
    if cv_dict["cluster_algorithm"] == "DBSCAN":
        # features & diff_image_paths are parallel lists
        feature_array = np.array(features)
        # OpenBLAS Warning : Detect OpenMP Loop and this application may hang. Please rebuild the library with USE_OPENMP=1 option.
        clustering = DBSCAN(
            eps=cv_dict["eps"], min_samples=cv_dict["min_samples"], metric="euclidean"
        )
        labels = clustering.fit_predict(feature_array)
    elif cv_dict["cluster_algorithm"] == "KMeans":
        clustering = KMeans(n_clusters=min(n_clusters, len(features)), random_state=42)
        labels = clustering.fit_predict(features)
    elif cv_dict["cluster_algorithm"] == "AgglomerativeClustering":
        clustering = AgglomerativeClustering(n_clusters=n_clusters)
        labels = clustering.fit_predict(features)
    else:
        raise ValueError(f"Invalid cluster_algorithm={cv_dict['cluster_algorithm']}")
    return labels


def copy_to_cluster_subdir(full_path: str, diff_dir: str, clusters_subdir: str) -> str:
    relevant_suffix: str = full_path.removeprefix(diff_dir)
    # Flatten the path so that all images appear at the same level
    flat_suffix: str = relevant_suffix.replace("/", ".")
    if flat_suffix.startswith("."):
        # If we don't do this, the file name will start with "." and won't show up with `ls`
        flat_suffix = flat_suffix.removeprefix(".")
    new_path: str = os.path.join(clusters_subdir, flat_suffix)
    # print(f"Copying {full_path} to {new_path}")
    shutil.copy(full_path, new_path)
    return relevant_suffix


if __name__ == "__main__":
    # Tries 1-2: with current image checker functions
    # Tries 3-9: first attempt using cv2, compute_diff_image
    # Tries 10-13: detect_features
    # Tries 14-24: reworking code to group multiple diff images together
    # Tries 25-28: working on clusters
    # Tries 29-32: 4 combinations of DBSCAN/KMeans & extract features on diff/diff+actual
    # Try 33: cleaned up code, DBSCAN & diff-only
    # Try 34: cleaned up code, DBSCAN & diff+actual
    # Tries 35-38: new feature detection, clustering algorithms
    """
    ###########################################################################
    To run:
    ```bash
    # Initial setup
    cd /home/ac.forsyth2/ez/zppy
    lcrc_conda # alias to set up conda
    pre-commit run --all-files
    git add -A
    conda clean --all --y
    conda env create -f conda/dev.yml -n zppy-hackathon-20250707-with-cv
    conda activate zppy-hackathon-20250707-with-cv
    pip install .

    # Each run
    # Update `try_num` below (the argument to `cv_prototype`)
    pre-commit run --all-files
    git add -A
    python tests/integration/image_checker.py
    # Compare missing/mismatched images with the original image checker's results
    # Change the number below to the `try_num`
    ${num} = 0
    diff /lcrc/group/e3sm/public_html/diagnostic_output/ac.forsyth2/cv_prototype/diff_try${num}/e3sm_diags/missing_images.txt /lcrc/group/e3sm/public_html/diagnostic_output/ac.forsyth2/cv_prototype/diff_try1/e3sm_diags/missing_images.txt
    diff /lcrc/group/e3sm/public_html/diagnostic_output/ac.forsyth2/cv_prototype/diff_try${num}/e3sm_diags/mismatched_images.txt /lcrc/group/e3sm/public_html/diagnostic_output/ac.forsyth2/cv_prototype/diff_try1/e3sm_diags/mismatched_images.txt
    ```

    ###########################################################################
    Try 29: feature detection -- actual + diffs, clustering algorithm -- DBSCAN
    Total of 69 mismatched images. That's 12 more than the original image checker found,
    because we're using a new mask-and-threshold method. Those new diffs are:
    < lat_lon/Cloud SSM/I/SSMI-TGCLDLWP_OCN-ANN-global.png
    < lat_lon/Cloud SSM/I/SSMI-TGCLDLWP_OCN-DJF-global.png
    < lat_lon/Cloud SSM/I/SSMI-TGCLDLWP_OCN-JJA-global.png
    < lat_lon/OMI-MLS/OMI-MLS-TCO-JJA-60S60N.png
    < lat_lon/SST_CL_HadISST/HadISST_CL-SST-ANN-global.png
    < lat_lon/SST_CL_HadISST/HadISST_CL-SST-DJF-global.png
    < at_lon/SST_CL_HadISST/HadISST_CL-SST-JJA-global.png
    < lat_lon/SST_CL_HadISST/HadISST_CL-SST-MAM-global.png
    < lat_lon/SST_PD_HadISST/HadISST_PD-SST-ANN-global.png
    < lat_lon/SST_PD_HadISST/HadISST_PD-SST-DJF-global.png
    < lat_lon/SST_PD_HadISST/HadISST_PD-SST-MAM-global.png
    < lat_lon/SST_PI_HadISST/HadISST_PI-SST-ANN-global.png

    These 27 diffs all involve the bottom plot AND the metrics
    0: 5 polar MERRA2 > MERRA2-U-850-{season}-polar_S, diffs in bottom plot/metrics
    1: 7 polar MERRA2 > MERRA2-T-850-{season}-polar_{hemisphere}, diffs in bottom plot/metrics
    2: 5 polar MERRA2 > MERRA2-U-850-{season}_polar_{hemisphere}, diffs in bottom plot/metrics
    6: 5 lat_lon Cloud_Calpiso > CALIPSOCOSP-CLDLOW_CAL-{season}-global, diffs in bottom plot/metrics
    11: 5 lat_lon MERRA2 > MERRA2-OMEGA-850-{season}-global, diffs in bottom plot/metrics

    These 7 diffs all involve all 3 plots
    3: 3 tropical_subseasonal wavernumber-frequency > PRECT_{}_15N-15S, diffs in all 3 plots
    4: 4 tropical_subseasonal wavernumber-frequency > PRECT_norm_{}_15N-15S, diffs in all 3 plots

    These 5 diffs all involve the bottom plot only
    9: 5 lat_lon MERRA2 > MERRA2-U-850-{season}-global, all barely noticeable diffs in bottom plot

    These 25 diffs all involve the bottom plots and/or metrics, but with less similarity
    5: 15 lat_lon SST_{}_HadISST > HadISST_{}-SST-{season}-global diff always in bottom plot, sometimes on bottom metrics; some diffs are barely visible, but some are noticeable
    7: 3 lat_lon OMI-MLS > OMI-MLS-TCO-{season}-60S60N, 1 barely noticeable diff in bottom plot, 1 diff in bottom plot/metrics, 1 diff in bottom plot only
    8: 3 lat_lon Cloud_SSM.I > SSMI-TGCLDLWP_OCN-{season}-global, 2 nearly invisible diffs in bottom plot, 1 nearly invisible diff in bottom metrics
    10: 4 lat_lon MERRA2 > MERRA2-T-850-{season}-global, 2 diffs in bottom plot/metrics and 2 just in bottom plot

    noise: 5 remaining diffs. 1 lat_lon, 3 polar, 1 qbo

    CONCLUSIONS
    - Diffs of plots in the same family almost always have the same things wrong with them.
    - Our combination of feature detection + clustering algorithm (DBSCAN) is actually able to tell which plot types are which, so that is interesting/good. HOWEVER, we're really more interested in grouping together similar diffs. E.g., clusters 0,1,2,6,11 above all involve diffs in the bottom plot AND metrics. Is there *anything* we can do to get the feature detection/clustering algorithm to merge clusters 0,1,2,6,11 into one cluster?
    - The ultimate goal here is to be able to look at just a few representative diffs rather than needing to sort through many many diffs manually (69 diffs is already a lot, but there can be even more).

    ###########################################################################
    Try 30: feature detection -- diffs only, clustering algorithm -- DBSCAN

    cluster_0 has all 69 diffs in it.

    CONCLUSIONS
    - Looking at only the diffs, it doesn't seem "smart" enough to distinguish that the 3-plot square diffs of tropical_subseasonal clearly belong in a different cluster than the small world map diffs of the other plots.

    ###########################################################################
    Try 31: feature detection -- diffs only, clustering algorithm -- KMeans

    Trying with n_clusters = 3. Can we get it to make the following 3 clusters: the world map plots, the tropical_subseasonal plots, and the qbo plots?

    Clusters:
    0: 2 tropical_subseasonal diffs
    2: 2 tropical_subseasonal diffs
    1: the remaining 65 diffs, including 3 tropical_subseasonal diffs

    CONCLUSIONS
    - Not good at all. The tropical subeasonal plots are spread out into 3 clusters and everything else is in one of those.

    ###########################################################################
    Try 32: feature detection -- actual + diffs, clustering algorithm -- KMeans

    Clusters:
    0: 39 diffs in lat_lon, polar, tropical_subseasonal
    1: 21 diffs in lat_lon, polar
    2: 9 diffs in polar

    ###########################################################################
    Try 38: feature detection -- diffs, clustering algorithm -- AC
    4 clusters -- 2 for tropical_subseasonal, 1 for qbo, and 1 for lat_lon/polar
    Pretty decent!

    ###########################################################################
    Try 40: feature detection -- sector slice on diffs, clustering algorithm -- AC
    3 clusters -- 2 for tropical_subseasonal/qbo, 1 for lat_lon, 1 for lat_lon/polar/tropical_subseasonal
    So, not that great

    diff_try# subdirectories to keep: 1, 2, 7, 9, 29, 30, 31, 32, 38
    TODO: delete remaining try# subdirectories
    """
    cv_dict: Dict[str, Any] = {
        # Image diff
        "gray_diff_threshold": 30,  # Out of 255
        # Feature extraction
        "extract_diff_features_only": True,
        "feature_extraction_algorithm": "sector_slice",
        "simple_hist_bins": 32,
        "combined_features_bins": 8,
        # Preprocessing
        "scale_features": True,
        "reduce_dimensions": True,
        "plot_features": True,
        # Clustering
        "cluster_algorithm": "AgglomerativeClustering",
        # Clustering > DBSCAN
        "eps": 0.5,
        "min_samples": 2,
        # Clustering > KMeans, AgglomerativeClustering
        "n_clusters": 3,
    }
    cv_prototype(41, cv_dict)
