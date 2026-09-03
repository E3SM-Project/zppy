import os
import random
from pathlib import Path
from typing import List, Optional, Tuple

from mache import MachineInfo
from PIL import Image, ImageDraw

from tests.integration.image_checker import _compare_actual_and_expected


def _write_image(path: str) -> None:
    image = Image.new("RGB", (100, 100), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 20, 80, 80), fill="black")
    image.save(path)


def _write_edge_dense_image(
    path: str,
    patch: Optional[Tuple[int, int, int, int]] = None,
    patch_fill: str = "gray",
) -> None:
    """Write a 100x100 image covered in many short line segments, meant to
    stand in for a contour-dense scientific plot where most of the image
    ends up classified as "edge zone" (see EDGE_TOLERANCE_RADIUS in
    image_checker.py). `patch`, if given, is a solid rectangle drawn on
    top representing a real, localized content change.

    A fixed random seed keeps this deterministic across runs. With this
    seed and segment count, essentially all of the canvas (and in
    particular the (0, 0, 16, 16) corner used by
    test_compare_flags_real_change_in_edge_dense_region below) falls
    inside the edge zone - if you change either, re-derive a patch
    location that lands entirely within the edge zone, since that's what
    isolates the edge-zone threshold from the (already-strict) interior
    threshold.
    """
    image = Image.new("RGB", (100, 100), "white")
    draw = ImageDraw.Draw(image)
    rng = random.Random(0)
    for _ in range(250):
        x1, y1 = rng.randint(0, 99), rng.randint(0, 99)
        x2 = x1 + rng.randint(-10, 10)
        y2 = y1 + rng.randint(-10, 10)
        draw.line((x1, y1, x2, y2), fill="black", width=1)
    if patch is not None:
        draw.rectangle(patch, fill=patch_fill)
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


def test_compare_ignores_small_pixel_shift(tmp_path: Path) -> None:
    expected_path = tmp_path / "expected.png"
    actual_path = tmp_path / "actual.png"
    _write_image(str(expected_path))

    with Image.open(expected_path) as expected_image:
        expected_image = expected_image.convert("RGB")
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


def test_compare_flags_real_change_in_edge_dense_region(tmp_path: Path) -> None:
    """A real content change located inside an edge-dense region (e.g. a
    contour-heavy plot) must still be flagged as a mismatch, even though
    the edge zone is given a much larger tolerance than the interior.

    This guards against the edge-zone tolerance being set so loose that it
    swallows genuine changes - which is exactly what happened before: with
    a single ~50% tolerance applied everywhere, deleting every contour
    line on a contour-dense plot still passed. Here, ~98% of the canvas
    is classified as edge zone, and a small (16x16, ~3% of the edge zone)
    patch that lands entirely inside it is a real, unambiguous content
    change - not shift noise or anti-aliasing halo (the shift estimate
    confidently reports no shift for this pair). If the edge-zone
    tolerance regresses back to a single loose threshold, this change
    would silently pass again.
    """
    expected_path = tmp_path / "expected.png"
    actual_path = tmp_path / "actual.png"
    _write_edge_dense_image(str(expected_path))
    _write_edge_dense_image(str(actual_path), patch=(0, 0, 16, 16))

    missing_images: List[str] = []
    mismatched_images: List[str] = []
    _compare_actual_and_expected(
        missing_images,
        mismatched_images,
        "edge_dense_change.png",
        str(actual_path),
        str(expected_path),
        str(tmp_path / "diffs"),
    )

    assert missing_images == []
    assert mismatched_images == ["edge_dense_change.png"]
