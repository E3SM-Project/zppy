"""Tests for the image diff viewer."""

import json
import os

from tests.complete_run import viewer
from tests.integration.image_severity import REVIEWABLE_SEVERITIES, SEVERITY_ORDER


def _score(name, severity, **extra):
    entry = {
        "name": name,
        "severity": severity,
        "content_fraction": 0.0,
        "raw_fraction": 0.0,
        "localized_pixels": 0,
        "cause": "some cause",
    }
    entry.update(extra)
    return entry


def test_only_reviewable_images_are_shown() -> None:
    scores = [
        _score("identical", "IDENTICAL"),
        _score("cosmetic", "NEGLIGIBLE"),
        _score("real", "MAJOR"),
    ]
    page = viewer.render_viewer(scores, "weekly_comprehensive_v3", "e3sm_diags")

    assert "data-name='real'" in page
    # Showing 900 identical plots would bury the three that changed.
    assert "data-name='identical'" not in page
    assert "data-name='cosmetic'" not in page
    # But they are still counted, so the reviewer knows the scale.
    assert "IDENTICAL (not a failure): <b>1</b>" in page


def test_images_are_ordered_worst_first() -> None:
    scores = [
        _score("minor", "MINOR"),
        _score("missing", "MISSING"),
        _score("major", "MAJOR"),
        _score("structural", "STRUCTURAL"),
        _score("moderate", "MODERATE"),
    ]
    page = viewer.render_viewer(scores, "cfg", "task")
    order = [
        line.split("'")[1]
        for line in page.split("data-name='")[1:]
        for line in [f"x'{line.split(chr(39))[0]}'"]
    ]
    assert order == ["missing", "structural", "major", "moderate", "minor"]


def test_equal_severities_are_ordered_by_how_much_changed() -> None:
    scores = [
        _score("small", "MAJOR", content_fraction=0.01),
        _score("large", "MAJOR", content_fraction=0.30),
    ]
    page = viewer.render_viewer(scores, "cfg", "task")
    assert page.index("data-name='large'") < page.index("data-name='small'")


def test_a_missing_image_says_so_instead_of_linking_nothing() -> None:
    page = viewer.render_viewer([_score("gone", "MISSING")], "cfg", "task")
    assert "This image was not produced." in page
    # There is no actual image to link to.
    assert "gone_actual.png" not in page
    assert "gone_expected.png" in page


def test_a_clean_comparison_says_so() -> None:
    page = viewer.render_viewer([_score("a", "IDENTICAL")], "cfg", "task")
    assert "No image needs review" in page
    assert "<figure" not in page


def test_page_is_self_contained() -> None:
    # The portal serves static files; an external stylesheet or script would
    # silently fail to load.
    page = viewer.render_viewer([_score("a", "MAJOR")], "cfg", "task")
    assert "http://" not in page
    assert "https://" not in page
    assert "<style>" in page


def test_names_are_escaped() -> None:
    page = viewer.render_viewer(
        [_score("<script>alert(1)</script>", "MAJOR")], "cfg", "task"
    )
    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;" in page


def test_every_severity_is_counted_even_at_zero() -> None:
    page = viewer.render_viewer([_score("a", "MAJOR")], "cfg", "task")
    for severity in SEVERITY_ORDER:
        assert f"{severity}" in page


def test_filters_offer_every_reviewable_severity() -> None:
    scores = [_score(name, name.upper()) for name in ("minor", "major")]
    page = viewer.render_viewer(scores, "cfg", "task")
    for severity in REVIEWABLE_SEVERITIES:
        assert f"<option value='{severity}'>" in page


def test_write_viewer_reads_the_scores_file(tmp_path) -> None:
    diff_dir = tmp_path / "e3sm_diags"
    diff_dir.mkdir()
    (diff_dir / "image_scores.json").write_text(json.dumps([_score("a", "MAJOR")]))

    path = viewer.write_viewer(str(diff_dir), "weekly_comprehensive_v3", "e3sm_diags")
    assert os.path.basename(path) == viewer.VIEWER_FILENAME
    assert "data-name='a'" in open(path).read()
    # Served by the web portal, so it must be readable by the web server.
    assert oct(os.stat(path).st_mode)[-3:] == "644"


def test_write_viewer_image_links_resolve(tmp_path) -> None:
    # The image checker writes <diff_dir>/<name>_{actual,expected,diff}.png,
    # with names that start with the task, while the page lives one level down
    # in <diff_dir>/<task>/. Linking the bare name doubled the task directory.
    diff_dir = tmp_path / "image_check_failures_comprehensive_v3"
    diff_subdir = diff_dir / "e3sm_diags"
    diff_subdir.mkdir(parents=True)
    name = "e3sm_diags/atm_monthly/lat_lon/PRECT.png"
    (diff_subdir / "image_scores.json").write_text(json.dumps([_score(name, "MAJOR")]))
    for kind in ("actual", "expected", "diff"):
        png = diff_dir / f"{name}_{kind}.png"
        png.parent.mkdir(parents=True, exist_ok=True)
        png.write_bytes(b"")

    path = viewer.write_viewer(
        str(diff_subdir), "weekly_comprehensive_v3", "e3sm_diags"
    )
    sources = [chunk.split("'")[0] for chunk in open(path).read().split("src='")[1:]]
    assert len(sources) == 3
    for source in sources:
        assert os.path.exists(os.path.join(os.path.dirname(path), source)), source


def test_write_viewer_writes_nothing_without_scores(tmp_path) -> None:
    # An empty page would look like a clean result rather than a missing one.
    assert viewer.write_viewer(str(tmp_path), "cfg", "task") == ""

    bad = tmp_path / "image_scores.json"
    bad.write_text("{ truncated")
    assert viewer.write_viewer(str(tmp_path), "cfg", "task") == ""


# Environment panel ###########################################################


def _env(repo="e3sm_diags", changes=(), available=True, detail=""):
    from tests.complete_run.envdiff import EnvironmentDiff

    return EnvironmentDiff(
        repo=repo, available=available, detail=detail, changes=list(changes)
    )


def _change(name, before, after):
    from tests.complete_run.envdiff import PackageChange

    return PackageChange(name, before, after)


def test_environment_panel_lists_what_changed() -> None:
    diffs = [_env(changes=[_change("numpy", "2.1.3", "2.2.0")])]
    page = viewer.render_viewer(
        [_score("a", "MAJOR")], "cfg", "task", environment_diffs=diffs
    )

    assert "Environment: 1 dependency change" in page
    assert "numpy" in page
    assert "2.1.3" in page and "2.2.0" in page


def test_environment_panel_states_when_nothing_changed() -> None:
    # "Nothing changed" is what makes an image difference attributable to code,
    # so its absence would leave a reviewer guessing.
    page = viewer.render_viewer(
        [_score("a", "MAJOR")], "cfg", "task", environment_diffs=[_env()]
    )
    assert "Environment: no dependency changed" in page


def test_a_failed_reproduction_is_opened_and_marked() -> None:
    from tests.complete_run.envdiff import interpretation

    diffs = [_env(changes=[_change("numpy", "1", "2")])]
    note = interpretation(diffs, {"e3sm_diags": "baseline"})
    page = viewer.render_viewer(
        [_score("a", "MAJOR")],
        "cfg",
        "task",
        environment_diffs=diffs,
        environment_note=note,
    )

    # A reviewer must not scroll past this one.
    assert "<details class='env warn' open>" in page
    assert "<strong>not</strong>" in page


def test_a_fresh_solve_difference_is_not_marked_as_a_warning() -> None:
    from tests.complete_run.envdiff import interpretation

    diffs = [_env(changes=[_change("numpy", "1", "2")])]
    note = interpretation(diffs, {"e3sm_diags": "dev"})
    page = viewer.render_viewer(
        [_score("a", "MAJOR")],
        "cfg",
        "task",
        environment_diffs=diffs,
        environment_note=note,
    )

    assert "env warn" not in page
    assert "may come from those changes" in page


def test_notable_packages_are_marked() -> None:
    diffs = [
        _env(changes=[_change("numpy", "1", "2"), _change("pip:obscure", "1", "2")])
    ]
    page = viewer.render_viewer(
        [_score("a", "MAJOR")], "cfg", "task", environment_diffs=diffs
    )

    assert "<tr class='notable'><td class='pkg'>numpy" in page
    assert "<tr class=''><td class='pkg'>pip:obscure" in page


def test_an_uncomparable_environment_says_so() -> None:
    diffs = [_env(available=False, detail="No environment export for the baseline")]
    page = viewer.render_viewer(
        [_score("a", "MAJOR")], "cfg", "task", environment_diffs=diffs
    )

    assert "Environment: not compared" in page
    assert "No environment export for the baseline" in page


def test_no_environment_panel_when_there_is_nothing_to_say() -> None:
    page = viewer.render_viewer([_score("a", "MAJOR")], "cfg", "task")
    assert "class='env" not in page


def test_environment_panel_appears_on_a_clean_image_page() -> None:
    # A run with no image differences still needs its environment reported.
    page = viewer.render_viewer(
        [_score("a", "IDENTICAL")],
        "cfg",
        "task",
        environment_diffs=[_env(changes=[_change("numpy", "1", "2")])],
    )
    assert "Environment: 1 dependency change" in page
    assert "No image needs review" in page


def test_write_viewer_passes_the_environment_through(tmp_path) -> None:
    diff_dir = tmp_path / "e3sm_diags"
    diff_dir.mkdir()
    (diff_dir / "image_scores.json").write_text(json.dumps([_score("a", "MAJOR")]))

    path = viewer.write_viewer(
        str(diff_dir),
        "weekly_comprehensive_v3",
        "e3sm_diags",
        environment_diffs=[_env(changes=[_change("numpy", "1", "2")])],
        environment_note="Dependencies changed in `e3sm_diags`.",
    )

    page = open(path).read()
    assert "numpy" in page
    assert "<code>e3sm_diags</code>" in page


def _row(package, task, cfg, counts, **extra):
    return viewer.SummaryRow(package, task, cfg, counts, **extra)


def test_summary_rolls_packages_up_across_cfgs() -> None:
    rows = [
        _row(
            "e3sm_diags", "e3sm_diags", "weekly_bundles", {"MAJOR": 2, "IDENTICAL": 8}
        ),
        _row("e3sm_diags", "e3sm_diags", "weekly_comprehensive_v3", {"IDENTICAL": 5}),
        _row("ILAMB", "ilamb", "weekly_bundles", {}),
    ]
    page = viewer.render_summary(rows, "20260918_run1")

    package_table = page[page.index("By package") : page.index("By check")]
    # e3sm_diags: 1 of 2 checks needs review, 2 of 15 images.
    assert (
        "<td class='num'>1</td><td class='num'>2</td><td class='num'>2</td><td class='num'>15</td>"
        in package_table
    )
    assert "sev-MAJOR" in package_table
    assert "not checked" in package_table
    assert "1 of 3 checks need review (2 images). 1 recorded no comparison." in page


def test_summary_totals_add_up() -> None:
    rows = [
        _row("a", "a", "c1", {"MISSING": 1, "IDENTICAL": 3}),
        _row("b", "b", "c1", {"MINOR": 2, "NEGLIGIBLE": 4}),
    ]
    page = viewer.render_summary(rows, "tag")
    footer = page[page.index("<tfoot>") : page.index("</tfoot>")]
    # Cosmetic 7, total 10.
    assert footer.endswith("<td class='num'>7</td><td class='num'>10</td></tr>")


def test_summary_links_packages_and_tasks_where_they_are_visible() -> None:
    rows = [
        _row(
            "MPAS-Analysis", "mpas_analysis", "c1", {"MINOR": 1}, viewer_href="a/i.html"
        ),
        _row(
            "MPAS-Analysis", "mpas_analysis", "c2", {"MINOR": 1}, viewer_href="b/i.html"
        ),
        _row("ILAMB", "ilamb", "c1", {}),
    ]
    page = viewer.render_summary(rows, "tag")
    package_table = page[page.index("By package") : page.index("By check")]
    check_table = page[page.index("By check") :]

    # A package name jumps to its first row among the checks.
    assert "<a href='#pkg-mpas-analysis'>MPAS-Analysis</a>" in package_table
    assert check_table.count("id='pkg-mpas-analysis'") == 1
    assert "id='pkg-ilamb'" in check_table
    # The review link is on the task, not in a trailing column that a wide
    # table scrolls out of view.
    assert "<td><a href='a/i.html'>mpas_analysis \u2192</a></td>" in check_table
    # A task with no review page is plain text.
    assert "<td>ilamb</td>" in check_table


def test_summary_escapes_and_stays_self_contained() -> None:
    rows = [_row("<pkg>", "<task>", "cfg", {"IDENTICAL": 1})]
    page = viewer.render_summary(rows, "<tag>")
    assert "<pkg>" not in page and "&lt;pkg&gt;" in page
    assert "http://" not in page and "https://" not in page
