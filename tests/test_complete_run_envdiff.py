"""Tests for comparing the environments two runs were produced with.

The same set of dependency changes means opposite things depending on what the
run was holding fixed, so these tests pin the interpretation as much as the
parsing.
"""

from tests.complete_run import envdiff
from tests.complete_run.layout import run_layout

EXPORT = """name: test-e3sm_diags-main-20260901_run1
channels:
  - conda-forge
dependencies:
  - python=3.13.1=h1234_0
  - numpy=2.1.3=py313_0
  - xarray=2025.1.0=pyhd8ed1ab_0
  - pip:
    - e3sm-diags==3.0.0
    - some-tool==1.2.3
prefix: /home/me/envs/test-e3sm_diags-main-20260901_run1
"""


def test_identity_lines_are_ignored() -> None:
    # Every run builds its own environment, so name and prefix always differ
    # and would bury the changes worth seeing.
    packages = envdiff.parse_environment_export(EXPORT)
    assert "name" not in packages
    assert "prefix" not in packages
    assert packages["numpy"] == "2.1.3=py313_0"


def test_a_renamed_environment_is_not_a_difference() -> None:
    other = EXPORT.replace("20260901_run1", "20260918_run2")
    assert envdiff.diff_environments(EXPORT, other) == []


def test_pip_packages_are_namespaced() -> None:
    packages = envdiff.parse_environment_export(EXPORT)
    # A package installed by both conda and pip must not silently collide.
    assert packages["pip:e3sm-diags"] == "3.0.0"
    assert "e3sm-diags" not in packages


def test_changed_added_and_removed_are_classified() -> None:
    other = (
        EXPORT.replace("numpy=2.1.3=py313_0", "numpy=2.2.0=py313_0")
        .replace("  - xarray=2025.1.0=pyhd8ed1ab_0\n", "")
        .replace("    - some-tool==1.2.3", "    - some-tool==1.2.3\n    - added==0.1")
    )
    by_name = {
        change.name: change for change in envdiff.diff_environments(EXPORT, other)
    }

    assert by_name["numpy"].kind == "changed"
    assert by_name["xarray"].kind == "removed"
    assert by_name["pip:added"].kind == "added"


def test_notable_packages_sort_first() -> None:
    other = EXPORT.replace("some-tool==1.2.3", "some-tool==1.3.0").replace(
        "numpy=2.1.3=py313_0", "numpy=2.2.0=py313_0"
    )
    changes = envdiff.diff_environments(EXPORT, other)

    # numpy moves results far more often than an unrelated pip package.
    assert changes[0].name == "numpy"
    assert changes[0].notable
    assert not changes[-1].notable


def test_a_build_string_change_counts() -> None:
    # Same version, different build, is a recompiled dependency.
    other = EXPORT.replace("numpy=2.1.3=py313_0", "numpy=2.1.3=py313_1")
    changes = envdiff.diff_environments(EXPORT, other)
    assert [change.name for change in changes] == ["numpy"]


def test_empty_export_yields_nothing_rather_than_raising() -> None:
    assert envdiff.parse_environment_export("") == {}
    assert envdiff.diff_environments("", "") == []


def _write(layout, repo, text):
    import os

    os.makedirs(layout.environments, exist_ok=True)
    with open(layout.environment_file(repo), "w") as stream:
        stream.write(text)


def test_compare_runs_reports_per_repository(tmp_path) -> None:
    candidate = run_layout(str(tmp_path), "20260918_run1")
    baseline = run_layout(str(tmp_path), "20260901_run1")
    _write(baseline, "e3sm_diags", EXPORT)
    _write(candidate, "e3sm_diags", EXPORT.replace("2.1.3", "2.2.0"))
    _write(baseline, "zppy", EXPORT)
    _write(candidate, "zppy", EXPORT)

    diffs = envdiff.compare_run_environments(
        candidate, baseline, ["e3sm_diags", "zppy"]
    )
    by_repo = {diff.repo: diff for diff in diffs}

    assert by_repo["e3sm_diags"].differs
    assert not by_repo["zppy"].differs


def test_a_missing_export_is_reported_not_treated_as_no_change(tmp_path) -> None:
    candidate = run_layout(str(tmp_path), "20260918_run1")
    baseline = run_layout(str(tmp_path), "20260901_run1")
    _write(candidate, "e3sm_diags", EXPORT)

    diff = envdiff.compare_run_environments(candidate, baseline, ["e3sm_diags"])[0]

    # "We could not check" must never read as "nothing changed".
    assert not diff.available
    assert not diff.differs
    assert "baseline" in diff.detail


def test_interpretation_flags_a_failed_reproduction() -> None:
    diffs = [
        envdiff.EnvironmentDiff(
            "e3sm_diags", changes=[envdiff.PackageChange("numpy", "1", "2")]
        )
    ]
    note = envdiff.interpretation(diffs, {"e3sm_diags": "baseline"})

    # This is the case a reviewer must not miss: the run meant to hold
    # dependencies fixed and did not, so the image diffs prove nothing.
    assert "not" in note and "attributable" in note
    assert "e3sm_diags" in note


def test_interpretation_names_dependency_changes_in_a_fresh_solve() -> None:
    diffs = [
        envdiff.EnvironmentDiff(
            "e3sm_diags", changes=[envdiff.PackageChange("numpy", "1", "2")]
        )
    ]
    note = envdiff.interpretation(diffs, {"e3sm_diags": "dev"})

    assert "may come from those changes" in note
    assert "not** attributable" not in note


def test_interpretation_of_a_clean_comparison() -> None:
    diffs = [envdiff.EnvironmentDiff("e3sm_diags", changes=[])]
    note = envdiff.interpretation(diffs, {"e3sm_diags": "dev"})
    assert "No dependency changed" in note


def test_summary_counts(tmp_path) -> None:
    diffs = [
        envdiff.EnvironmentDiff(
            "e3sm_diags",
            changes=[
                envdiff.PackageChange("numpy", "1", "2"),
                envdiff.PackageChange("obscure", "1", "2"),
            ],
        ),
        envdiff.EnvironmentDiff("zppy", changes=[]),
        envdiff.EnvironmentDiff("mpas_analysis", available=False, detail="missing"),
    ]
    summary = envdiff.summarize(diffs)

    assert summary["compared"] == 2
    assert summary["repos_differing"] == ["e3sm_diags"]
    assert summary["change_count"] == 2
    assert summary["notable_change_count"] == 1
    assert summary["unavailable"] == ["mpas_analysis"]
