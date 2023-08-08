import os
import re
import shutil
import subprocess
from typing import List

from mache import MachineInfo
from PIL import Image, ImageChops, ImageDraw

# Image checking ##########################################################


# Copied from E3SM Diags
def compare_images(
    test,
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
        test.assertIsNone(diff.getbbox())
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
            print("\npath_to_actual_png={}".format(path_to_actual_png))
            print("path_to_expected_png={}".format(path_to_expected_png))
            print("diff has {} nonzero pixels.".format(num_nonzero_pixels))
            print("total number of pixels={}".format(num_pixels))
            print("num_nonzero_pixels/num_pixels fraction={}".format(fraction))

            mismatched_images.append(image_name)

            simple_image_name = image_name.split("/")[-1].split(".")[0]
            shutil.copy(
                path_to_actual_png,
                os.path.join(diff_dir, "{}_actual.png".format(simple_image_name)),
            )
            shutil.copy(
                path_to_expected_png,
                os.path.join(diff_dir, "{}_expected.png".format(simple_image_name)),
            )
            # https://stackoverflow.com/questions/41405632/draw-a-rectangle-and-a-text-in-it-using-pil
            draw = ImageDraw.Draw(diff)
            (left, upper, right, lower) = diff.getbbox()
            draw.rectangle(((left, upper), (right, lower)), outline="red")
            diff.save(
                os.path.join(diff_dir, "{}_diff.png".format(simple_image_name)),
                "PNG",
            )


def check_mismatched_images(
    test, actual_images_dir, expected_images_file, expected_images_dir, diff_dir
):
    missing_images: List[str] = []
    mismatched_images: List[str] = []

    counter = 0
    with open(expected_images_file) as f:
        for line in f:
            counter += 1
            if counter % 250 == 0:
                print("On line #", counter)
            image_name = line.strip("./").strip("\n")
            path_to_actual_png = os.path.join(actual_images_dir, image_name)
            path_to_expected_png = os.path.join(expected_images_dir, image_name)

            compare_images(
                test,
                missing_images,
                mismatched_images,
                image_name,
                path_to_actual_png,
                path_to_expected_png,
                diff_dir,
            )

    if missing_images:
        print("Missing images:")
        for i in missing_images:
            print(i)
    if mismatched_images:
        print("Mismatched images:")
        for i in mismatched_images:
            print(i)

    # Make diff_dir readable
    os.system(f"chmod -R 755 {diff_dir}")

    test.assertEqual(missing_images, [])
    test.assertEqual(mismatched_images, [])


# Multi-machine testing ##########################################################

# Inspired by https://github.com/E3SM-Project/e3sm_diags/blob/master/docs/source/quickguides/generate_quick_guides.py


def get_chyrsalis_expansions(config):
    # Note: `os.environ.get("USER")` also works. Here we're already using mache but not os, so using mache.
    username = config.get("web_portal", "username")
    web_base_path = config.get("web_portal", "base_path")
    d = {
        "bundles_walltime": "02:00:00",
        "constraint": "",
        # To run this test, replace conda environment with your e3sm_diags dev environment
        "diags_environment_commands": "source /home/ac.forsyth2/miniconda3/etc/profile.d/conda.sh; conda activate e3sm_diags_20230807",
        "diags_walltime": "2:00:00",
        "environment_commands_test": "source /lcrc/soft/climate/e3sm-unified/test_e3sm_unified_1.9.0rc10_chrysalis.sh",
        "expected_dir": "/lcrc/group/e3sm/public_html/zppy_test_resources/",
        "partition_long": "compute",
        "partition_short": "debug",
        "qos_long": "regular",
        "qos_short": "regular",
        "scratch": f"/lcrc/globalscratch/{username}/",
        "user_input": "/lcrc/group/e3sm/ac.forsyth2/",
        "user_output": f"/lcrc/group/e3sm/{username}/",
        "user_www": f"{web_base_path}/{username}/",
    }
    return d


def get_compy_expansions(config):
    # Note: `os.environ.get("USER")` also works. Here we're already using mache but not os, so using mache.
    username = config.get("web_portal", "username")
    web_base_path = config.get("web_portal", "base_path")
    d = {
        "bundles_walltime": "02:00:00",
        "constraint": "",
        # To run this test, replace conda environment with your e3sm_diags dev environment
        "diags_environment_commands": "source /qfs/people/fors729/miniconda3/etc/profile.d/conda.sh; conda activate e3sm_diags_dev_20220722",
        "diags_walltime": "03:00:00",
        "environment_commands_test": "source /share/apps/E3SM/conda_envs/test_e3sm_unified_1.8.0rc6_compy.sh",
        "expected_dir": "/compyfs/www/zppy_test_resources/",
        "partition_long": "slurm",
        "partition_short": "short",
        "qos_long": "regular",
        "qos_short": "regular",
        "scratch": f"/qfs/people/{username}/",
        "user_input": "/compyfs/fors729/",
        "user_output": f"/compyfs/{username}/",
        "user_www": f"{web_base_path}/{username}/",
    }
    return d


def get_perlmutter_expansions(config):
    # Note: `os.environ.get("USER")` also works. Here we're already using mache but not os, so using mache.
    username = config.get("web_portal", "username")
    web_base_path = config.get("web_portal", "base_path")
    d = {
        "bundles_walltime": "6:00:00",
        "constraint": "cpu",
        # To run this test, replace conda environment with your e3sm_diags dev environment
        "diags_environment_commands": "source /global/homes/f/forsyth/miniconda3/etc/profile.d/conda.sh; conda activate e3sm_diags_20230728",
        "diags_walltime": "6:00:00",
        "environment_commands_test": "source /global/common/software/e3sm/anaconda_envs/test_e3sm_unified_1.9.0rc9_pm-cpu.sh",
        "expected_dir": "/global/cfs/cdirs/e3sm/www/zppy_test_resources/",
        "partition_long": "",
        "partition_short": "",
        "qos_long": "regular",
        "qos_short": "regular",  # debug walltime too short?
        "scratch": f"/pscratch/sd/{username[0]}/{username}/",
        # Use CFS for large datasets
        "user_input": "/global/cfs/cdirs/e3sm/forsyth/",
        "user_output": f"/global/cfs/cdirs/e3sm/{username}/",
        "user_www": f"{web_base_path}/{username}/",
    }
    return d


def get_expansions():
    machine_info = MachineInfo()
    config = machine_info.config
    machine = machine_info.machine
    if machine == "chrysalis":
        expansions = get_chyrsalis_expansions(config)
    elif machine == "compy":
        expansions = get_compy_expansions(config)
    elif machine == "pm-cpu":
        expansions = get_perlmutter_expansions(config)
    else:
        raise ValueError(f"Unsupported machine={machine}")
    expansions["machine"] = machine
    return expansions


def substitute_expansions(expansions, file_in, file_out):
    with open(file_in, "r") as file_read:
        with open(file_out, "w") as file_write:
            # For line in file, if line matches #expand <expansion_name>#, then replace text with <expansion>.
            # Send output to the corresponding specific cfg file.
            for line in file_read:
                match_object = re.search("#expand ([^#]*)#", line)
                while match_object is not None:
                    expansion_indicator = match_object.group(0)
                    expansion_name = match_object.group(1)
                    expansion = expansions[expansion_name]
                    line = line.replace(expansion_indicator, expansion)
                    match_object = re.search("#expand ([^#]*)#", line)
                file_write.write(line)


def generate_cfgs(unified_testing=False, dry_run=False):
    git_top_level = (
        subprocess.check_output("git rev-parse --show-toplevel".split())
        .strip()
        .decode("utf-8")
    )
    expansions = get_expansions()
    if unified_testing:
        expansions["environment_commands"] = expansions["environment_commands_test"]
    else:
        # The cfg doesn't need this line,
        # but it would be difficult to only write environment_commands in the unified_testing case.
        expansions["environment_commands"] = ""
    machine = expansions["machine"]

    if dry_run:
        expansions["dry_run"] = "True"
    else:
        expansions["dry_run"] = "False"

    cfg_names = ["bundles", "complete_run"]
    for cfg_name in cfg_names:
        cfg_template = f"{git_top_level}/tests/integration/template_{cfg_name}.cfg"
        cfg_generated = (
            f"{git_top_level}/tests/integration/generated/test_{cfg_name}_{machine}.cfg"
        )
        substitute_expansions(expansions, cfg_template, cfg_generated)

    directions_template = f"{git_top_level}/tests/integration/template_directions.md"
    directions_generated = (
        f"{git_top_level}/tests/integration/generated/directions_{machine}.md"
    )
    substitute_expansions(expansions, directions_template, directions_generated)

    script_template = (
        f"{git_top_level}/tests/integration/template_update_campaign_expected_files.sh"
    )
    script_generated = f"{git_top_level}/tests/integration/generated/update_campaign_expected_files_{machine}.sh"
    substitute_expansions(expansions, script_template, script_generated)


if __name__ == "__main__":
    generate_cfgs(unified_testing=True)
