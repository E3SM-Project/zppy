"""Tests for baseline promotion.

Promotion points a link at a run directory. It must be atomic, must not copy or
destroy anything, and must refuse a run that does not vouch for itself.
"""

import json
import os

import pytest

from tests.complete_run import promote
from tests.complete_run.layout import baseline_run_for, run_layout


def _make_run(root, tag, *, status="passed", branches=("main",), images=1):
    layout = run_layout(str(root), tag)
    os.makedirs(layout.root, exist_ok=True)
    os.makedirs(layout.www, exist_ok=True)
    with open(os.path.join(layout.root, "complete-run-report.json"), "w") as stream:
        json.dump({"status": status}, stream)
    with open(layout.manifest, "w") as stream:
        json.dump(
            {
                "tag": tag,
                "machine": "chrysalis",
                "generated": "2026-09-18T00:00:00+00:00",
                "cfgs": ["weekly_comprehensive_v3"],
                "tasks": ["climo"],
                "repos": {
                    f"repo{index}": {
                        "branch": branch,
                        "sha": "a" * 40,
                        "sha_date": "2026-09-17T12:00:00+00:00",
                    }
                    for index, branch in enumerate(branches)
                },
            },
            stream,
        )
    with open(layout.status, "w") as stream:
        json.dump(
            {"task_status_by_cfg": {"weekly_comprehensive_v3": {"climo": "OK"}}},
            stream,
        )
    for index in range(images):
        with open(os.path.join(layout.www, f"plot{index}.png"), "w") as stream:
            stream.write("x")
    return layout


def test_promote_points_the_link_at_the_run(tmp_path) -> None:
    _make_run(tmp_path, "20260901_run1")
    link = promote.promote(str(tmp_path), "20260901_run1")

    assert os.path.islink(link)
    assert os.path.basename(os.path.realpath(link)) == "20260901_run1"


def test_promote_copies_nothing(tmp_path) -> None:
    layout = _make_run(tmp_path, "20260901_run1", images=5)
    promote.promote(str(tmp_path), "20260901_run1")

    # The baseline is the run, not a copy of it: exactly one set of images.
    all_pngs = [
        os.path.join(directory, name)
        for directory, _, names in os.walk(tmp_path)
        for name in names
        if name.endswith(".png") and not os.path.islink(directory)
    ]
    assert len(all_pngs) == 5
    assert all(path.startswith(layout.root) for path in all_pngs)


def test_promoting_again_leaves_the_previous_baseline_intact(tmp_path) -> None:
    first = _make_run(tmp_path, "20260901_run1")
    _make_run(tmp_path, "20260908_run1")

    promote.promote(str(tmp_path), "20260901_run1")
    promote.promote(str(tmp_path), "20260908_run1")

    # Rolling back is promoting the old one again -- it was never destroyed.
    assert os.path.isdir(first.root)
    promote.promote(str(tmp_path), "20260901_run1")
    assert promote.show(str(tmp_path))["tag"] == "20260901_run1"


def test_link_is_relative_so_the_root_can_move(tmp_path) -> None:
    _make_run(tmp_path, "20260901_run1")
    link = promote.promote(str(tmp_path), "20260901_run1")
    assert not os.readlink(link).startswith("/")


def test_refuses_a_run_that_did_not_pass(tmp_path) -> None:
    _make_run(tmp_path, "20260901_run1", status="images_failed")
    with pytest.raises(promote.PromotionError, match="images_failed"):
        promote.promote(str(tmp_path), "20260901_run1")


def test_a_failed_run_can_be_promoted_deliberately(tmp_path) -> None:
    _make_run(tmp_path, "20260901_run1", status="images_failed")
    # Expected results legitimately change; this is the reviewed override.
    promote.promote(str(tmp_path), "20260901_run1", allow_failed=True)
    assert promote.show(str(tmp_path))["tag"] == "20260901_run1"


def test_refuses_a_feature_branch(tmp_path) -> None:
    _make_run(tmp_path, "20260901_run1", branches=("main", "my-feature"))
    with pytest.raises(promote.PromotionError, match="my-feature"):
        promote.promote(str(tmp_path), "20260901_run1")


def test_allows_the_upstream_branch_names(tmp_path) -> None:
    # The five repos do not agree on what to call their default branch.
    _make_run(tmp_path, "20260901_run1", branches=("main", "master", "develop"))
    promote.promote(str(tmp_path), "20260901_run1")


def test_refuses_a_run_with_no_report(tmp_path) -> None:
    layout = run_layout(str(tmp_path), "20260901_run1")
    os.makedirs(layout.root)
    with pytest.raises(promote.PromotionError, match="Only a finished run"):
        promote.promote(str(tmp_path), "20260901_run1")


def test_refuses_a_run_that_does_not_exist(tmp_path) -> None:
    with pytest.raises(promote.PromotionError, match="No such run"):
        promote.promote(str(tmp_path), "nope")


def test_channels_are_independent(tmp_path) -> None:
    _make_run(tmp_path, "20260901_run1")
    _make_run(tmp_path, "20260908_run1")
    promote.promote(str(tmp_path), "20260901_run1", channel="unified_1.13.0")
    promote.promote(str(tmp_path), "20260908_run1")

    assert promote.show(str(tmp_path))["tag"] == "20260908_run1"
    assert promote.show(str(tmp_path), "unified_1.13.0")["tag"] == "20260901_run1"


def test_show_reports_what_is_promoted(tmp_path) -> None:
    _make_run(tmp_path, "20260901_run1")
    promote.promote(str(tmp_path), "20260901_run1")
    described = promote.show(str(tmp_path))

    assert described["machine"] == "chrysalis"
    assert described["exists"] is True
    assert "repo0" in described["repos"]
    assert described["default_run"]["repos"]["repo0"]["sha_date"]
    assert described["default_run"]["repos"]["repo0"]["age_days"] >= 0


def test_show_raises_when_nothing_is_promoted(tmp_path) -> None:
    with pytest.raises(promote.PromotionError, match="No baseline"):
        promote.show(str(tmp_path))


def test_prune_never_deletes_a_promoted_run(tmp_path) -> None:
    for day in range(1, 13):
        _make_run(tmp_path, f"202609{day:02d}_run1")
    promote.promote(str(tmp_path), "20260901_run1")

    doomed = promote.prune(str(tmp_path), keep=2, dry_run=False)

    assert "20260901_run1" not in doomed
    assert os.path.isdir(run_layout(str(tmp_path), "20260901_run1").root)
    # Newest two unpromoted runs survive.
    assert os.path.isdir(run_layout(str(tmp_path), "20260912_run1").root)
    assert os.path.isdir(run_layout(str(tmp_path), "20260911_run1").root)


def test_prune_is_a_dry_run_by_default(tmp_path) -> None:
    for day in range(1, 13):
        _make_run(tmp_path, f"202609{day:02d}_run1")

    doomed = promote.prune(str(tmp_path), keep=2)

    # A run directory holds tens of thousands of images; deleting by default
    # would be the wrong way round.
    assert doomed
    assert all(os.path.isdir(run_layout(str(tmp_path), tag).root) for tag in doomed)


def test_prune_keeps_everything_when_there_is_little(tmp_path) -> None:
    _make_run(tmp_path, "20260901_run1")
    assert promote.prune(str(tmp_path), keep=8) == []


def test_promoted_tags_lists_every_channel(tmp_path) -> None:
    _make_run(tmp_path, "20260901_run1")
    _make_run(tmp_path, "20260908_run1")
    promote.promote(str(tmp_path), "20260901_run1", channel="unified_1.13.0")
    promote.promote(str(tmp_path), "20260908_run1")

    assert sorted(promote.promoted_tags(str(tmp_path))) == [
        "20260901_run1",
        "20260908_run1",
    ]


def test_partial_promotion_adds_an_override_without_moving_default(tmp_path) -> None:
    _make_run(tmp_path, "20260901_run1")
    _make_run(tmp_path, "20260908_run1", status="jobs_failed")
    promote.promote(str(tmp_path), "20260901_run1")

    promote.promote(str(tmp_path), "20260908_run1", tasks=("climo",))

    assert promote.show(str(tmp_path))["tag"] == "20260901_run1"
    assert baseline_run_for(
        str(tmp_path), "weekly_comprehensive_v3", "climo"
    ).root.endswith("20260908_run1")
    assert "20260908_run1" in promote.promoted_tags(str(tmp_path))
    assert os.path.isfile(tmp_path / "baselines" / "main.overrides.json")


def test_partial_promotion_can_roll_back_an_entry_to_the_default(tmp_path) -> None:
    _make_run(tmp_path, "20260901_run1")
    _make_run(tmp_path, "20260908_run1")
    promote.promote(str(tmp_path), "20260901_run1")
    promote.promote(str(tmp_path), "20260908_run1", tasks=("climo",))

    promote.promote(str(tmp_path), "20260901_run1", tasks=("climo",))

    assert baseline_run_for(
        str(tmp_path), "weekly_comprehensive_v3", "climo"
    ).root.endswith("20260901_run1")
    assert promote.promoted_tags(str(tmp_path)) == ["20260901_run1"]
    assert json.loads(
        (tmp_path / "baselines" / "main.overrides.json").read_text()
    ) == {}


def test_partial_promotion_checks_only_the_selected_entry(tmp_path) -> None:
    layout = _make_run(tmp_path, "20260908_run1", status="jobs_failed")
    with open(layout.status, "w") as stream:
        json.dump(
            {
                "task_status_by_cfg": {
                    "weekly_comprehensive_v3": {
                        "climo": "OK",
                        "e3sm_to_cmip": "1 failed jobs",
                    }
                }
            },
            stream,
        )
    manifest = json.loads(open(layout.manifest).read())
    manifest["tasks"] = ["climo", "e3sm_to_cmip"]
    with open(layout.manifest, "w") as stream:
        json.dump(manifest, stream)

    promote.promote(str(tmp_path), "20260908_run1", tasks=("climo",))

    with pytest.raises(promote.PromotionError, match="e3sm_to_cmip"):
        promote.promote(str(tmp_path), "20260908_run1", tasks=("e3sm_to_cmip",))


def test_partial_promotion_does_not_require_images_for_unchecked_plot_tasks(
    tmp_path,
) -> None:
    layout = _make_run(tmp_path, "20260908_run1")
    manifest = json.loads(open(layout.manifest).read())
    manifest["cfgs"] = ["weekly_legacy_3.0.0_comprehensive_v3"]
    manifest["tasks"] = ["global_time_series"]
    with open(layout.manifest, "w") as stream:
        json.dump(manifest, stream)
    with open(layout.status, "w") as stream:
        json.dump(
            {
                "task_status_by_cfg": {
                    "weekly_legacy_3.0.0_comprehensive_v3": {
                        "global_time_series": "OK"
                    }
                }
            },
            stream,
        )

    promote.promote(
        str(tmp_path),
        "20260908_run1",
        cfgs=("weekly_legacy_3.0.0_comprehensive_v3",),
        tasks=("global_time_series",),
    )

    assert "20260908_run1" in promote.promoted_tags(str(tmp_path))


def test_prune_protects_runs_referenced_only_by_overrides(tmp_path) -> None:
    _make_run(tmp_path, "20260901_run1")
    _make_run(tmp_path, "20260908_run1")
    promote.promote(str(tmp_path), "20260901_run1")
    promote.promote(str(tmp_path), "20260908_run1", tasks=("climo",))

    doomed = promote.prune(str(tmp_path), keep=0, dry_run=False)

    assert "20260908_run1" not in doomed
    assert os.path.isdir(run_layout(str(tmp_path), "20260908_run1").root)
