import os
from typing import List, Optional

from mache import MachineInfo
from PIL import Image, ImageDraw

from tests.integration.image_checker import _compare_actual_and_expected


def _write_image(path: str) -> None:
    image = Image.new("RGB", (100, 100), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 20, 80, 80), fill="black")
    image.save(path)


# Run this test with:
# cd zppy
# pytest tests/images/test_image_checker.py
def test_compare() -> None:
    missing_images: List[str] = []
    mismatched_images: List[str] = []

    directory: str = "tests/images/"
    # Copied from /lcrc/group/e3sm/public_html/diagnostic_output/ac.forsyth2/zppy_weekly_comprehensive_v3_www/test_zppy_20250401/v3.LR.historical_0051/image_check_failures_comprehensive_v3/e3sm_diags/atm_monthly_180x360_aave/model_vs_obs_1987-1988/lat_lon/CRU_IPCC/CRU-TREFHT-ANN-land_60S90N.png_*
    image_name: str = "CRU-TREFHT-ANN-land_60S90N"
    path_to_actual_png: str = f"{directory}CRU-TREFHT-ANN-land_60S90N_input_actual.png"
    path_to_expected_png: str = (
        f"{directory}CRU-TREFHT-ANN-land_60S90N_input_expected.png"
    )

    machine_info = MachineInfo()
    web_portal_base_path: str = machine_info.config.get("web_portal", "base_path")
    web_portal_base_url: str = machine_info.config.get("web_portal", "base_url")
    print(f"web_portal_base_path: {web_portal_base_path}")
    print(f"web_portal_base_url: {web_portal_base_url}")
    user: Optional[str] = os.environ.get("USER")
    if not user:
        raise RuntimeError("USER could not be determined.")
    # Example diff dir URL: https://web.lcrc.anl.gov/public/e3sm/diagnostic_output/ac.forsyth2/test_image_checker_diffs/
    diff_dir: str = f"{web_portal_base_path}/{user}/test_image_checker_diffs"

    _compare_actual_and_expected(
        missing_images,
        mismatched_images,
        image_name,
        path_to_actual_png,
        path_to_expected_png,
        diff_dir,
    )
    assert missing_images == []
    assert mismatched_images == ["CRU-TREFHT-ANN-land_60S90N"]


def test_compare_ignores_small_pixel_shift(tmp_path) -> None:
    expected_path = tmp_path / "expected.png"
    actual_path = tmp_path / "actual.png"
    _write_image(str(expected_path))

    expected_image = Image.open(expected_path)
    actual_image = Image.new("RGB", expected_image.size, "white")
    actual_image.paste(expected_image, (1, -2))
    actual_image.save(actual_path)

    missing_images: List[str] = []
    mismatched_images: List[str] = []
    _compare_actual_and_expected(
        missing_images,
        mismatched_images,
        "shifted.png",
        str(actual_path),
        str(expected_path),
        str(tmp_path / "diffs"),
    )

    assert missing_images == []
    assert mismatched_images == []
