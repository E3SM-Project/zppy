"""Unit tests for the image severity scorer.

These use small synthetic images so they run anywhere, with no dependency on
the large expected-image trees on Chrysalis.
"""

import numpy as np
import pytest

from tests.integration.image_severity import (
    MAJOR,
    MINOR,
    NEGLIGIBLE,
    STRUCTURAL,
    Comparison,
    group_by_cause,
    localized_change_pixels,
    tolerant_difference,
    trim_background,
)

WHITE = 255


def blank(height=80, width=80):
    return np.full((height, width, 3), WHITE, np.uint8)


def fraction_different(actual, expected, radius=4, tolerance=32):
    return float((tolerant_difference(actual, expected, radius) > tolerance).mean())


class TestTolerantDifference:
    def test_identical_images_have_no_difference(self):
        image = blank()
        image[40, 10:70] = 0
        assert fraction_different(image, image) == 0.0

    def test_shifted_feature_is_forgiven(self):
        """A line that moved one pixel is the harmless matplotlib case."""
        expected = blank()
        expected[40, 10:70] = 0
        actual = blank()
        actual[41, 10:70] = 0
        assert fraction_different(actual, expected) == 0.0

    def test_shift_within_tolerance_is_forgiven(self):
        expected = blank()
        expected[40, 10:70] = 0
        actual = blank()
        actual[44, 10:70] = 0  # moved exactly `radius` pixels
        assert fraction_different(actual, expected, radius=4) == 0.0

    def test_shift_beyond_tolerance_is_reported(self):
        expected = blank()
        expected[20, 10:70] = 0
        actual = blank()
        actual[60, 10:70] = 0  # far too far to be reflow
        assert fraction_different(actual, expected, radius=4) > 0.0

    def test_deleted_feature_is_reported(self):
        """The case a one-directional check would miss.

        Blank pixels do appear near the line in the expected image, so looking
        only that way sees nothing wrong. The reverse check catches it.
        """
        expected = blank()
        expected[40, 10:70] = 0
        actual = blank()
        assert fraction_different(actual, expected) > 0.0

    def test_added_feature_is_reported(self):
        expected = blank()
        actual = blank()
        actual[40, 10:70] = 0
        assert fraction_different(actual, expected) > 0.0

    def test_recolored_feature_is_reported(self):
        """Same shape and position, different color: a real data change."""
        expected = blank()
        expected[30:50, 30:50] = (255, 0, 0)
        actual = blank()
        actual[30:50, 30:50] = (0, 0, 255)
        assert fraction_different(actual, expected) > 0.0

    def test_deletion_is_caught_at_every_tolerance(self):
        """Raising the tolerance must not blind us to removed content."""
        expected = blank()
        expected[40, 10:70] = 0
        actual = blank()
        for radius in (2, 3, 4, 5, 8):
            assert fraction_different(actual, expected, radius=radius) > 0.0


class TestTrimBackground:
    def test_border_is_removed(self):
        image = blank(100, 100)
        image[40:60, 30:70] = 0
        trimmed = trim_background(image)
        assert trimmed.shape[:2] == (20, 40)

    def test_one_pixel_of_border_does_not_change_content(self):
        """The bbox_inches='tight' case: same plot, one more pixel of margin."""
        narrow = blank(100, 100)
        narrow[40:60, 30:70] = 0
        wide = blank(100, 101)
        wide[40:60, 31:71] = 0
        assert trim_background(narrow).shape == trim_background(wide).shape

    def test_blank_image_is_left_alone(self):
        image = blank()
        assert trim_background(image).shape == image.shape


class TestGrouping:
    def test_failures_are_counted_by_severity_and_cause(self):
        comparisons = [
            Comparison(
                "a", MAJOR, 0.5, 0.2, (1, 1), (1, 1), "panel or labels added/removed"
            ),
            Comparison(
                "b", MAJOR, 0.4, 0.2, (1, 1), (1, 1), "panel or labels added/removed"
            ),
            Comparison("c", NEGLIGIBLE, 0.0, 0.0, (1, 1), (1, 1), "layout shifted"),
        ]
        counts = group_by_cause(comparisons)
        assert counts[(MAJOR, "panel or labels added/removed")] == 2
        assert counts[(NEGLIGIBLE, "layout shifted")] == 1

    def test_worst_sorts_first(self):
        negligible = Comparison("a", NEGLIGIBLE, 0.0, 0.0, (1, 1), (1, 1), "x")
        structural = Comparison("b", STRUCTURAL, 1.0, 0.5, (1, 1), (1, 1), "y")
        assert (
            sorted([negligible, structural], key=Comparison.sort_key)[0] is structural
        )

    @pytest.mark.parametrize(
        "severity,expected",
        [(NEGLIGIBLE, False), (MAJOR, True), (STRUCTURAL, True)],
    )
    def test_only_real_changes_need_review(self, severity, expected):
        comparison = Comparison("a", severity, 0.0, 0.0, (1, 1), (1, 1), "x")
        assert comparison.needs_review is expected


class TestLocalizedChanges:
    """A changed number is far too small to move an area-based score.

    These guard the case that area-based severity cannot see: the repository's
    own e3sm_diags fixture differs only by "Mean -0.18" becoming "Mean -0.17".
    """

    def test_unchanged_images_report_nothing(self):
        image = blank(200, 200)
        image[50:150, 50:150] = (200, 30, 30)
        assert localized_change_pixels(image, image) == 0

    def test_a_small_solid_change_is_found(self):
        """Stands in for a digit being redrawn."""
        expected = blank(200, 200)
        actual = blank(200, 200)
        actual[100:106, 100:110] = 0
        assert localized_change_pixels(actual, expected) > 0

    def test_a_change_too_small_to_matter_is_ignored(self):
        """A couple of stray pixels are noise, not a redrawn character."""
        expected = blank(200, 200)
        actual = blank(200, 200)
        actual[100, 100] = 0
        actual[120, 130] = 0
        assert localized_change_pixels(actual, expected) == 0

    def test_many_scattered_spots_are_ignored(self):
        """Every gridline shifting a pixel is anti-aliasing, not a value change."""
        expected = blank(400, 400)
        actual = blank(400, 400)
        for row in range(20, 380, 12):
            actual[row : row + 4, 20:26] = 0  # spots all over the figure
        assert localized_change_pixels(actual, expected) == 0

    def test_faint_differences_are_ignored(self):
        """Anti-aliasing changes intensity slightly; that is not a real change."""
        expected = blank(200, 200)
        actual = blank(200, 200)
        actual[50:150, 50:150] = 235  # well under the intensity tolerance
        assert localized_change_pixels(actual, expected) == 0


class TestResultsOrdering:
    """The ranked list feeds both severity_report.txt and the diff grid PDF."""

    def test_mismatched_list_is_worst_first(self):
        from tests.integration.image_checker import Results

        comparisons = [
            Comparison("minor.png", MINOR, 0.01, 0.0, (1, 1), (1, 1), "x"),
            Comparison("structural.png", STRUCTURAL, 1.0, 0.5, (1, 1), (1, 1), "y"),
            Comparison("major.png", MAJOR, 0.5, 0.0, (1, 1), (1, 1), "z"),
        ]
        results = Results(
            diff_dir="/tmp/diff",
            prefix="task",
            image_count_total=3,
            file_list_missing=[],
            file_list_mismatched=["minor.png", "structural.png", "major.png"],
            comparisons=comparisons,
        )
        assert results.file_list_mismatched == [
            "structural.png",
            "major.png",
            "minor.png",
        ]

    def test_cosmetic_images_are_counted_separately(self):
        from tests.integration.image_checker import Results

        comparisons = [
            Comparison("a.png", NEGLIGIBLE, 0.0, 0.0, (1, 1), (1, 1), "x"),
            Comparison("b.png", NEGLIGIBLE, 0.0, 0.0, (1, 1), (1, 1), "x"),
            Comparison("c.png", MAJOR, 0.5, 0.0, (1, 1), (1, 1), "y"),
        ]
        results = Results("/tmp/diff", "task", 3, [], ["c.png"], comparisons)
        assert results.image_count_cosmetic == 2
        assert results.image_count_mismatched == 1
