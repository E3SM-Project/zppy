from pathlib import Path
from typing import List

from tests.integration.image_summary_report import render_failing_image_summary


def test_render_failing_image_summary_uses_header_and_exact_task_tokens(
    tmp_path: Path,
) -> None:
    summary: Path = tmp_path / "test_images_summary.md"
    summary.write_text(
        "\n".join(
            [
                "# Summary of test results",
                "",
                "| Test name | Missing images | Total images | Needs review | Correct images | Identical | Cosmetic only | Severity |",
                "| --- | --- | --- | --- | --- | --- | --- | --- |",
                "| /plots/global_time_series/case_a | 1 | 10 | 0 | 9 | 9 | 0 | medium |",
                "| /plots/notglobal_time_seriesx/case_b | 0 | 10 | 1 | 9 | 9 | 0 | low |",
                "| /plots/e3sm_diags/case_c | 0 | 10 | 0 | 10 | 10 | 0 | none |",
            ]
        )
        + "\n"
    )

    tasks: List[str] = ["e3sm_diags", "global_time_series"]
    report: str = render_failing_image_summary(str(summary), tasks)

    assert "`global_time_series`" in report
    assert "`other`" in report
    assert "/plots/global_time_series/case_a" in report
    assert "/plots/notglobal_time_seriesx/case_b" in report
    assert "/plots/e3sm_diags/case_c" not in report
    assert report.index("`global_time_series`") < report.index("`other`")


def test_render_failing_image_summary_reports_missing_columns(
    tmp_path: Path,
) -> None:
    summary: Path = tmp_path / "test_images_summary.md"
    summary.write_text(
        "\n".join(
            [
                "# Summary of test results",
                "",
                "| Test name | Total images | Correct images | Severity |",
                "| --- | --- | --- | --- |",
                "| /plots/global_time_series/case_a | 10 | 9 | medium |",
            ]
        )
        + "\n"
    )

    report: str = render_failing_image_summary(
        str(summary), ["global_time_series"]
    )

    assert report == "Unable to identify failing image-check columns.\n"
