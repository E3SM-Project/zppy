import os
import shutil
from typing import List

from PIL import Image, ImageChops, ImageDraw


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
        print("\npath_to_actual_png={}".format(path_to_actual_png))
        print("path_to_expected_png={}".format(path_to_expected_png))
        print("diff has {} nonzero pixels.".format(num_nonzero_pixels))
        width, height = expected_png.size
        num_pixels = width * height
        print("total number of pixels={}".format(num_pixels))
        fraction = num_nonzero_pixels / num_pixels
        print("num_nonzero_pixels/num_pixels fraction={}".format(fraction))
        # Fraction of mismatched pixels should be less than 0.02%
        if fraction >= 0.0002:
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

    test.assertEqual(missing_images, [])
    test.assertEqual(mismatched_images, [])
