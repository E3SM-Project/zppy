from typing import List

from tests.integration.image_checker import _compare_actual_and_expected


# Run this test with:
# cd zppy
# pytest tests/images/test_image_checker.py
def test_compare(tmp_path):
    missing_images: List[str] = []
    mismatched_images: List[str] = []

    directory: str = "tests/images/"
    # Copied from /lcrc/group/e3sm/public_html/diagnostic_output/ac.forsyth2/zppy_weekly_comprehensive_v3_www/test_zppy_20250401/v3.LR.historical_0051/image_check_failures_comprehensive_v3/e3sm_diags/atm_monthly_180x360_aave/model_vs_obs_1987-1988/lat_lon/CRU_IPCC/CRU-TREFHT-ANN-land_60S90N.png_*
    image_name: str = "CRU-TREFHT-ANN-land_60S90N"
    path_to_actual_png: str = f"{directory}CRU-TREFHT-ANN-land_60S90N_input_actual.png"
    path_to_expected_png: str = (
        f"{directory}CRU-TREFHT-ANN-land_60S90N_input_expected.png"
    )

    # The diff images are an artifact of the comparison, not what is under
    # test, so they go to a temporary directory. Deriving a real web portal
    # path would tie this test to an E3SM machine, where `mache` can discover
    # one, and leave the diffs behind on the shared filesystem.
    diff_dir: str = str(tmp_path / "test_image_checker_diffs")

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
