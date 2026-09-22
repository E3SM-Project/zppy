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


# E3SM-Unified baselines #####################################################

# What an env_description.txt carries for a task backed by E3SM-Unified: its own
# header, then `conda list`.
UNIFIED_DESCRIPTION = """Task: e3sm_diags
Generated: 2026-09-18 12:50:18

Repository: N/A (uses a released package via the unified environment)

Conda environment: E3SM-Unified

Package versions:
-----------------
# packages in environment at /lcrc/soft/climate/e3sm-unified/default:
#
# Name                    Version                   Build  Channel
python                    3.13.1               h1234_0    conda-forge
numpy                     2.4.4           py313hf6604e3_0    conda-forge
xarray                    2025.1.0          pyhd8ed1ab_0    conda-forge
e3sm-diags                3.2.0                    pypi_0    pypi
some-tool                 1.2.3                    pypi_0    pypi
"""


def _write_description(layout, task, text):
    import os

    os.makedirs(layout.env_descriptions, exist_ok=True)
    with open(os.path.join(layout.env_descriptions, f"{task}.txt"), "w") as stream:
        stream.write(text)


def test_package_list_is_parsed_below_the_description_header() -> None:
    packages = envdiff.parse_package_list(UNIFIED_DESCRIPTION)
    assert packages["numpy"] == "2.4.4"
    assert packages["pip:e3sm-diags"] == "3.2.0"
    # The description's own lines are not packages.
    assert "Task:" not in packages and "Generated:" not in packages
    assert len(packages) == 5


def test_a_unified_baseline_is_compared_through_its_package_list(tmp_path) -> None:
    # The baseline ran e3sm_diags from E3SM-Unified, so it exported no
    # environment for it; this run solved a dev environment.
    candidate = run_layout(str(tmp_path), "20260918_main_run1")
    baseline = run_layout(str(tmp_path), "20260918_unified113")
    _write(candidate, "e3sm_diags", EXPORT)
    _write_description(baseline, "e3sm_diags", UNIFIED_DESCRIPTION)

    diff = envdiff.compare_run_environments(candidate, baseline, ["e3sm_diags"])[0]

    assert diff.available
    changes = {change.name: change for change in diff.changes}
    # Only versions are compared: conda list and an export write builds
    # differently, so python and xarray match.
    assert set(changes) == {"numpy", "e3sm-diags"}
    assert (changes["numpy"].baseline, changes["numpy"].candidate) == (
        "2.4.4",
        "2.1.3",
    )
    assert "env_descriptions/e3sm_diags.txt" in diff.detail


def test_a_pip_installed_package_matches_its_conda_counterpart(tmp_path) -> None:
    # The dev environment pip-installs the package under test; E3SM-Unified has
    # it from conda-forge. Same package, same version: not a change.
    candidate = run_layout(str(tmp_path), "20260918_main_run1")
    baseline = run_layout(str(tmp_path), "20260918_unified113")
    _write(
        candidate,
        "e3sm_diags",
        EXPORT.replace("e3sm-diags==3.0.0", "e3sm-diags==3.2.0"),
    )
    _write_description(
        baseline,
        "e3sm_diags",
        UNIFIED_DESCRIPTION.replace(
            "e3sm-diags                3.2.0                    pypi_0    pypi",
            "e3sm_diags                3.2.0              pyhc364b38_0    conda-forge",
        ),
    )

    diff = envdiff.compare_run_environments(candidate, baseline, ["e3sm_diags"])[0]
    assert "e3sm-diags" not in {change.name for change in diff.changes}
    assert "pip:e3sm-diags" not in {change.name for change in diff.changes}


def test_any_of_a_repositorys_tasks_supplies_the_package_list(tmp_path) -> None:
    candidate = run_layout(str(tmp_path), "20260918_main_run1")
    baseline = run_layout(str(tmp_path), "20260918_unified113")
    _write(candidate, "zppy_interfaces", EXPORT)
    _write_description(baseline, "pcmdi_diags", UNIFIED_DESCRIPTION)

    diff = envdiff.compare_run_environments(candidate, baseline, ["zppy_interfaces"])[0]
    assert diff.available and diff.differs
    assert "pcmdi_diags.txt" in diff.detail


def test_interpretation_does_not_call_an_uncompared_run_clean() -> None:
    # Only zppy could be compared. Saying "no dependency changed" would credit
    # every image difference to the code under test when e3sm_diags may have
    # moved underneath it.
    diffs = [
        envdiff.EnvironmentDiff("zppy", changes=[]),
        envdiff.EnvironmentDiff("e3sm_diags", available=False, detail="missing"),
    ]
    note = envdiff.interpretation(diffs, {"zppy": "dev", "e3sm_diags": "dev"})
    assert "`e3sm_diags` could not be compared" in note
    assert "not necessarily attributable" in note
