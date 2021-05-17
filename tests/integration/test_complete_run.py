import os
import shutil
import subprocess
import unittest

from PIL import Image, ImageChops, ImageDraw


# Copied from E3SM Diags
def compare_images(
    test,
    mismatched_images,
    image_name,
    path_to_actual_png,
    path_to_expected_png,
):
    # https://stackoverflow.com/questions/35176639/compare-images-python-pil
    actual_png = Image.open(path_to_actual_png).convert("RGB")
    expected_png = Image.open(path_to_expected_png).convert("RGB")
    diff = ImageChops.difference(actual_png, expected_png)

    diff_dir = "tests/image_check_failures"
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


class TestCompleteRun(unittest.TestCase):
    def test_complete_run(self):
        # Run `zppy -c test_complete_run.cfg` prior to running this test!!!
        actual_images_dir = '/lcrc/group/e3sm/public_html/diagnostic_output/ac.forsyth2/zppy_test_www/20210122.v2_test01.piControl.ne30pg2_EC30to60E2r2-1900_ICG.chrysalis'

        # The expected_images_file lists all images we expect to compare.
        expected_images_file = "/lcrc/group/e3sm/public_html/zppy_test_resources/image_list_expected_complete_run.txt"
        expected_images_dir = "/lcrc/group/e3sm/public_html/zppy_test_resources/expected_complete_run"

        mismatched_images = []

        counter = 0
        with open(expected_images_file) as f:
            for line in f:
                counter += 1
                if counter % 250 == 0:
                    print('On line #', counter)
                image_name = line.strip("./").strip("\n")
                path_to_actual_png = os.path.join(actual_images_dir, image_name)
                path_to_expected_png = os.path.join(expected_images_dir, image_name)

                compare_images(
                    self,
                    mismatched_images,
                    image_name,
                    path_to_actual_png,
                    path_to_expected_png,
                )

        self.assertEqual(mismatched_images, [])


if __name__ == "__main__":
    unittest.main()
