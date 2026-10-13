from pathlib import Path
from typing import Any, List

from tests.cfg_suite import viewer
from tests.integration import image_checker
from tests.integration.image_checker import Results, _compare_actual_and_expected
from tests.integration.image_severity import MISSING, MINOR, Comparison


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


def test_new_cfg_without_baseline_is_not_image_compared(
    tmp_path: Path, monkeypatch: Any
) -> None:
    def fail_comparison(*args: object, **kwargs: object) -> None:
        raise AssertionError("unexpected image comparison")

    monkeypatch.setattr(
        image_checker,
        "check_images",
        fail_comparison,
    )
    results = {}

    image_checker.set_up_and_run_image_checker(
        "legacy_3.2.0_comprehensive_v3",
        "v3.LR.historical_0051",
        {
            "user_www": f"{tmp_path}/",
            "unique_id": "run",
            "baseline_by_cfg_task": {
                "weekly_legacy_3.2.0_comprehensive_v3:e3sm_diags": {
                    "state": "not-compared",
                    "reason": "new cfg",
                }
            },
        },
        "",
        ["e3sm_diags"],
        results,
    )

    assert results == {}


def test_markdown_and_html_attention_counts_match(
    tmp_path: Path, monkeypatch: Any
) -> None:
    class Config:
        def get(self, section: str, key: str) -> str:
            return (
                "/unrelated"
                if key == "base_path"
                else "https://example.invalid"
            )

    class FakeMachineInfo:
        config = Config()

    monkeypatch.setattr(image_checker, "MachineInfo", FakeMachineInfo)
    comparisons = [
        Comparison("missing.png", MISSING, 1.0, 1.0, None, None, "missing"),
        Comparison("changed.png", MINOR, 0.01, 0.0, (1, 1), (1, 1), "changed"),
    ]
    result = Results(
        str(tmp_path / "diff"),
        "task",
        2,
        ["missing.png"],
        ["changed.png"],
        comparisons,
    )
    summary_path = tmp_path / "summary.md"

    image_checker.construct_markdown_summary_table(
        {"cfg": result}, str(summary_path)
    )
    markdown = summary_path.read_text()
    markdown_row = next(
        line for line in markdown.splitlines() if line.startswith("| cfg |")
    )
    markdown_cells = [cell.strip() for cell in markdown_row.strip("|").split("|")]
    html_page = viewer.render_summary(
        [
            viewer.SummaryRow(
                "package",
                "task",
                "cfg",
                {"MISSING": 1, "MINOR": 1},
            )
        ],
        "tag",
    )
    check_table = html_page[html_page.index("By check") :]

    expected_headers = (
        "Missing",
        "Needs review (excluding missing)",
        "Total needing attention",
    )
    assert all(
        header in markdown and header in html_page for header in expected_headers
    )
    assert markdown_cells[5:8] == ["1", "1", "2"]
    assert (
        "<td class='num'>1</td><td class='num'>1</td><td class='num'>2</td>"
        in check_table
    )
