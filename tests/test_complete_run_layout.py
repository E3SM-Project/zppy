"""Tests for the shared run and baseline layout."""

import os

import pytest

from tests.complete_run import layout


def test_shared_roots_are_group_locations_not_personal_ones() -> None:
    # The whole point of the layout is that anyone can promote any run.
    for machine in ("chrysalis", "pm-cpu", "perlmutter"):
        root = layout.shared_root(machine)
        assert root.startswith("/")
        assert "$USER" not in root
        assert "{username}" not in root


def test_compy_has_no_default_and_says_why() -> None:
    # Compy grants no write access to /compyfs/www, so there is no shared
    # web-served location to fall back to. Silently using a personal directory
    # would recreate the problem this layout exists to solve.
    with pytest.raises(ValueError, match="No shared complete-run root"):
        layout.shared_root("compy")

    assert layout.shared_root("compy", "/compyfs/shared/zppy") == "/compyfs/shared/zppy"


def test_environment_variable_overrides_the_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(layout.SHARED_ROOT_ENV_VAR, "/scratch/fake/")
    assert layout.shared_root("chrysalis") == "/scratch/fake"


def test_explicit_override_beats_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(layout.SHARED_ROOT_ENV_VAR, "/scratch/fake")
    assert layout.shared_root("chrysalis", "/explicit") == "/explicit"


def test_run_layout_paths() -> None:
    run = layout.run_layout("/shared", "20260918_run1")
    assert run.root == "/shared/runs/20260918_run1"
    assert run.output == "/shared/runs/20260918_run1/output"
    assert run.www == "/shared/runs/20260918_run1/www"
    assert run.manifest.endswith("manifest.json")
    assert run.image_list("weekly_bundles").endswith("image_list_weekly_bundles.txt")
    assert run.settings_baseline("expected_bundles").endswith(
        "settings/expected_bundles"
    )


def test_www_case_dir_matches_what_zppy_writes() -> None:
    # zppy writes <www>/zppy_weekly_<cfg>_www/<unique_id>/<case>; the run uses a
    # fixed segment for unique_id because the run directory already has the tag.
    run = layout.run_layout("/shared", "20260918_run1")
    # The cfg name already begins with "weekly_", so the directory is
    # zppy_<cfg>_www -- doubling the prefix is an easy mistake to make here.
    assert run.www_case_dir("weekly_comprehensive_v3", "v3.LR.historical_0051") == (
        "/shared/runs/20260918_run1/www/zppy_weekly_comprehensive_v3_www/run/"
        "v3.LR.historical_0051"
    )
    assert "weekly_weekly" not in run.www_case_dir("weekly_bundles", "case")


def test_www_case_dir_agrees_with_the_status_directory() -> None:
    # Both derive from the same zppy_<cfg>_* convention; if they drift, the run
    # checks images in one place and job status in another.
    run = layout.run_layout("/shared", "tag")
    www = run.www_case_dir("weekly_bundles", "v3.LR.historical_0051")
    status = run.status_dir("weekly_bundles")
    assert status == (
        "/shared/runs/tag/output/zppy_weekly_bundles_output/run/"
        "v3.LR.historical_0051/post/scripts"
    )
    assert "zppy_weekly_bundles_www" in www


def test_output_can_live_outside_the_run_directory() -> None:
    run = layout.run_layout("/shared", "tag", "/scratch/me/tag/output")
    assert run.output == "/scratch/me/tag/output"
    assert run.status_dir("weekly_bundles").startswith("/scratch/me/tag/output/")
    # Everything a baseline keeps stays under the shared root.
    assert run.www == "/shared/runs/tag/www"
    assert layout.run_layout("/shared", "tag").output == "/shared/runs/tag/output"


def test_json_helpers_round_trip_and_tolerate_damage(tmp_path) -> None:
    path = str(tmp_path / "nested" / "status.json")
    layout.write_json(path, {"b": 1, "a": [1, 2]})
    assert layout.read_json_object(path) == {"a": [1, 2], "b": 1}

    (tmp_path / "corrupt.json").write_text("{not json")
    assert layout.read_json_object(str(tmp_path / "corrupt.json")) == {}
    (tmp_path / "list.json").write_text("[1, 2]")
    assert layout.read_json_object(str(tmp_path / "list.json")) == {}
    assert layout.read_json_object(str(tmp_path / "absent.json")) == {}


def test_resolve_baseline_follows_the_link(tmp_path) -> None:
    root = str(tmp_path)
    target = tmp_path / "runs" / "20260901_run1"
    target.mkdir(parents=True)
    (tmp_path / "baselines").mkdir()
    os.symlink("../runs/20260901_run1", layout.baseline_link(root))

    assert layout.resolve_baseline(root).root == os.path.realpath(str(target))
    assert layout.baseline_tag(root) == "20260901_run1"


def test_resolve_baseline_raises_when_nothing_is_promoted(tmp_path) -> None:
    # Thousands of "missing image" failures would be a terrible way to discover
    # there is no baseline.
    with pytest.raises(FileNotFoundError, match="No baseline is promoted"):
        layout.resolve_baseline(str(tmp_path))


def test_resolve_baseline_raises_on_a_dangling_link(tmp_path) -> None:
    root = str(tmp_path)
    (tmp_path / "baselines").mkdir()
    os.symlink("../runs/deleted", layout.baseline_link(root))
    with pytest.raises(FileNotFoundError, match="broken"):
        layout.resolve_baseline(root)
