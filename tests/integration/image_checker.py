import os
import shutil
from math import ceil
from typing import Dict, List, Tuple

import cv2
import matplotlib.backends.backend_pdf
import matplotlib.image as mpimg
import numpy as np
from mache import MachineInfo
from matplotlib import pyplot as plt
from PIL import Image, ImageChops, ImageDraw


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

                USE_CV = True
                if USE_CV:
                    _cv_compare_actual_and_expected(
                        missing_images,
                        mismatched_images,
                        image_name,
                        path_to_actual_png,
                        path_to_expected_png,
                        parameters.diff_dir,
                    )
                else:
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
"""
cd /home/ac.forsyth2/ez/zppy
lcrc_conda # alias to set up conda
pre-commit run --all-files
git add -A
conda clean --all --y
conda env create -f conda/dev.yml -n zppy-hackathon-20250707-with-cv
conda activate zppy-hackathon-20250707-with-cv
pip install .

# Update try_num
pre-commit run --all-files
git add -A
python tests/integration/image_checker.py
diff /lcrc/group/e3sm/public_html/diagnostic_output/ac.forsyth2/cv_prototype/diff_try9/e3sm_diags/missing_images.txt /lcrc/group/e3sm/public_html/diagnostic_output/ac.forsyth2/cv_prototype/diff_try1/e3sm_diags/missing_images.txt
diff /lcrc/group/e3sm/public_html/diagnostic_output/ac.forsyth2/cv_prototype/diff_try9/e3sm_diags/mismatched_images.txt /lcrc/group/e3sm/public_html/diagnostic_output/ac.forsyth2/cv_prototype/diff_try1/e3sm_diags/mismatched_images.txt
"""


def cv_prototype(try_num: int):
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
    test_results: Results = check_images(parameters, "e3sm_diags")
    # test_results_dict: Dict[str, Results] = {"e3sm_diags": test_results}
    # construct_markdown_summary_table(test_results_dict, "cv_prototype_summary.md")
    # | e3sm_diags | 1713 | 1644 | 12 | 57 | /lcrc/group/e3sm/public_html/diagnostic_output/ac.forsyth2/cv_prototype/diff_try{try_num}/e3sm_diags |

    # Try           | Total | Correct | Missing | Mismatched | Notes
    # 1,2: original | 1713 | 1644    | 12       | 57         |
    # 7,9: Step 1   | 1713 | 1632    | 12       | 69         | +12 mismatched
    assert test_results.image_count_total == 1713
    assert test_results.image_count_missing == 12
    assert test_results.image_count_mismatched == 57
    assert test_results.image_count_correct == 1644


# Modified from LivChat code ###


def _cv_compare_actual_and_expected(
    missing_images,
    mismatched_images,
    image_name,
    path_to_actual_png,
    path_to_expected_png,
    diff_dir,
):
    if not os.path.exists(path_to_actual_png):
        missing_images.append(image_name)
        return
    actual_image: np.ndarray = cv2.imread(str(path_to_actual_png))
    if actual_image is None:
        raise ValueError(f"cv2.imread failed to read {path_to_actual_png}")
    expected_image = cv2.imread(str(path_to_expected_png))
    # diff: np.ndarray
    mask: np.ndarray
    _, mask = compute_diff_image(expected_image, actual_image)
    if not mask.any():
        # Images are close enough, call it a match
        return
    # # diff != 0 => boolean array where True indicates diff[i,j] is not 0
    # # count_nonzero counts all the Trues
    # num_nonzero_pixels = np.count_nonzero(diff != 0)
    # width, height = diff.shape
    # num_pixels = width * height
    # threshold = num_nonzero_pixels / num_pixels
    # # Threshold of mismatched pixels should be less than 0.02%
    # if threshold >= 0.0002:
    #     mismatched_images.append(image_name)
    mismatched_images.append(image_name)
    diff_dir_actual_png = os.path.join(diff_dir, f"{image_name}_actual.png")
    # image_name could contain a number of subdirectories.
    # So, let's make them.
    os.makedirs(os.path.dirname(diff_dir_actual_png), exist_ok=True)
    shutil.copy(
        path_to_actual_png,
        diff_dir_actual_png,
    )
    diff_dir_expected_png = os.path.join(diff_dir, f"{image_name}_expected.png")
    # image_name could contain a number of subdirectories.
    # So, let's make them.
    os.makedirs(os.path.dirname(diff_dir_expected_png), exist_ok=True)
    shutil.copy(
        path_to_expected_png,
        diff_dir_expected_png,
    )
    # Draw red box around diff-area on each of: diff, actual, expected
    # _draw_box(diff, diff, os.path.join(diff_dir, f"{image_name}_diff.png"))
    # _draw_box(actual_image, diff, os.path.join(diff_dir, f"{image_name}_actual.png"))
    # _draw_box(
    #     expected_image, diff, os.path.join(diff_dir, f"{image_name}_expected.png")
    # )

    # keypoints, _ = detect_features(expected_image)
    # clusters = cluster_diff_regions(mask)
    # groupings = assign_clusters_to_features(clusters, keypoints)
    # # Save diff image
    # diff_name = output_dir / f"diff_{Path(path_to_expected_png).stem}.png"
    # cv2.imwrite(str(diff_name), diff)
    # print(f"Processed {image_name}: {path_to_expected_png} vs {path_to_actual_png}: {len(clusters)} diff regions grouped by features.")


# Step 1: Compute Diff Images
def compute_diff_image(
    expected_image: np.ndarray, actual_image: np.ndarray
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
    # If it's > 30, we add it to the mask.
    _, mask = cv2.threshold(gray_diff, 30, 255, cv2.THRESH_BINARY)
    if len(mask.shape) != 2:
        raise ValueError(f"mask.shape={mask.shape} should have 2 dimensions")
    return diff, mask


# # Step 2: Feature Detection/Segmentation
# # NOTE: I imagine this will take quite a bit of troubleshooting to actually get working! There are many many plot types, each with different features. Will this detect them accurately?
# def detect_features(img):
#     sift = cv2.SIFT_create()
#     keypoints, descriptors = sift.detectAndCompute(img, None)
#     return keypoints, descriptors

# # Step 3: Cluster Diff Pixels
# # NOTE: how would we ever know what `n_clusters` should be? Without that would we need to resort to classification rather than clustering (i.e., needing to hand-label a training set)?
# def cluster_diff_regions(mask, n_clusters=3):
#     # Find nonzero (diff) pixels
#     ys, xs = np.nonzero(mask)
#     coords = np.column_stack((xs, ys))
#     if len(coords) == 0:
#         return []
#     kmeans = KMeans(n_clusters=min(n_clusters, len(coords)), random_state=42)
#     labels = kmeans.fit_predict(coords)
#     clusters = [coords[labels == i] for i in range(n_clusters)]
#     return clusters

# # Step 4: Group Diffs by Feature
# def assign_clusters_to_features(clusters, keypoints):
#     feature_coords = np.array([kp.pt for kp in keypoints])
#     groupings = {}
#     for i, cluster in enumerate(clusters):
#         if len(feature_coords) == 0 or len(cluster) == 0:
#             groupings[i] = None
#             continue
#         # Find the closest feature for each cluster centroid
#         centroid = np.mean(cluster, axis=0)
#         distances = np.linalg.norm(feature_coords - centroid, axis=1)
#         closest_feature_idx = np.argmin(distances)
#         groupings[i] = keypoints[closest_feature_idx]
#     return groupings


if __name__ == "__main__":
    # Tries 1-2: with current image checker functions
    # Try 3-: first attempt using cv2, Step 1: Compute Diff Images
    cv_prototype(9)
