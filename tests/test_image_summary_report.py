from pathlib import Path
import runpy
import subprocess
import sys
from typing import List

import pytest

from tests.integration.image_summary_report import (
    main,
    render_failing_image_summary,
)


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


def test_main_writes_report_to_stdout(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    summary: Path = tmp_path / "test_images_summary.md"
    summary.write_text(
        "\n".join(
            [
                "# Summary of test results",
                "",
                "| Test name | Total images | Correct images | Identical | Cosmetic only | Missing images | Needs review | Severity |",
                "| --- | --- | --- | --- | --- | --- | --- | --- |",
                "| /plots/global_time_series/case_a | 10 | 9 | 9 | 0 | 1 | 0 | medium |",
            ]
        )
        + "\n"
    )

    exit_code: int = main([str(summary), "global_time_series"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out == (
        "`global_time_series`\n\n"
        "| Test name | Total images | Correct images | Identical |"
        " Cosmetic only | Missing images | Needs review | Severity |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
        "| /plots/global_time_series/case_a | 10 | 9 | 9 | 0 | 1 | 0 |"
        " medium |\n"
    )


def test_module_entry_point_writes_report_to_stdout(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    summary: Path = tmp_path / "test_images_summary.md"
    summary.write_text(
        "\n".join(
            [
                "# Summary of test results",
                "",
                "| Test name | Total images | Correct images | Identical | Cosmetic only | Missing images | Needs review | Severity |",
                "| --- | --- | --- | --- | --- | --- | --- | --- |",
                "| /plots/global_time_series/case_a | 10 | 9 | 9 | 0 | 1 | 0 | medium |",
            ]
        )
        + "\n"
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "python",
            str(summary),
            "global_time_series",
        ],
    )

    with pytest.raises(SystemExit) as excinfo:
        runpy.run_module("tests.integration.image_summary_report", run_name="__main__")

    captured = capsys.readouterr()
    assert excinfo.value.code == 0
    assert captured.out == (
        "`global_time_series`\n\n"
        "| Test name | Total images | Correct images | Identical |"
        " Cosmetic only | Missing images | Needs review | Severity |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
        "| /plots/global_time_series/case_a | 10 | 9 | 9 | 0 | 1 | 0 |"
        " medium |\n"
    )


def test_shell_invocation_appends_failing_summary_to_report(tmp_path: Path) -> None:
    summary: Path = tmp_path / "test_images_summary.md"
    report_file: Path = tmp_path / "report.md"
    repo_root: Path = Path(__file__).resolve().parent.parent
    summary.write_text(
        "\n".join(
            [
                "# Summary of test results",
                "",
                "| Test name | Total images | Correct images | Identical | Cosmetic only | Missing images | Needs review | Severity |",
                "| --- | --- | --- | --- | --- | --- | --- | --- |",
                "| /plots/global_time_series/case_a | 10 | 9 | 9 | 0 | 1 | 0 | medium |",
            ]
        )
        + "\n"
    )

    subprocess.run(
        [
            "bash",
            "-lc",
            (
                f'"{sys.executable}" -m tests.integration.image_summary_report '
                f'"{summary}" global_time_series >> "{report_file}"'
            ),
        ],
        check=True,
        cwd=repo_root,
    )

    assert report_file.read_text() == (
        "`global_time_series`\n\n"
        "| Test name | Total images | Correct images | Identical |"
        " Cosmetic only | Missing images | Needs review | Severity |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
        "| /plots/global_time_series/case_a | 10 | 9 | 9 | 0 | 1 | 0 |"
        " medium |\n"
    )
