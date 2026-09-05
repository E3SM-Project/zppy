"""Severity scoring for image regression checking.

The old check asked one question -- "what fraction of pixels differ at all?" --
and failed on anything above 0.02%. That question has no useful answer for
scientific plots: when matplotlib changes its text metrics, every anti-aliased
edge moves a fraction of a pixel and *visually identical* images score 2-20%.
In the 2026-08-04 weekly test that meant 1274 of 1280 MPAS-Analysis images were
reported as failures, unsorted, for a human to review by hand.

This module answers a more useful question: *how badly* do two images differ?
It returns a severity band so the reviewer can work from worst to least bad and
stop once the remaining differences are clearly cosmetic.

Two independent things are measured:

1. ``geometry_change`` -- how much the plot's overall size changed. A missing
   panel or a dropped subtitle shows up here, because the figure is saved with
   ``bbox_inches="tight"`` and so shrinks when content disappears.

2. ``content_fraction`` -- how much of the picture actually looks different,
   ignoring small movements. See ``tolerant_difference`` below.

See IMAGE_DIFF_DESIGN.md for the analysis these thresholds come from.
"""

import os
from typing import Dict, List, NamedTuple, Optional, Tuple

import numpy as np
from PIL import Image
from scipy import ndimage

# --- Tuning -----------------------------------------------------------------
#
# How far (in pixels) a feature may move before we stop calling it a change.
# Larger values ignore more of the harmless reflow caused by a matplotlib
# upgrade, but also blind us to genuine movement of that size. 4 was chosen by
# sweeping r=2..5 against hand-labeled images; see IMAGE_DIFF_DESIGN.md 5.2.
SHIFT_TOLERANCE_PIXELS = 4

# How different two pixels must be (0-255) before the difference counts at all.
# Below this is anti-aliasing noise.
INTENSITY_TOLERANCE = 32

# Fraction of the image that must look different to reach each band.
NEGLIGIBLE_MAX = 0.005
MINOR_MAX = 0.02
MODERATE_MAX = 0.08

# Relative change in figure size. Above STRUCTURAL_GEOMETRY_CHANGE something
# large is gone (typically a whole panel). Above NOTABLE_GEOMETRY_CHANGE the
# layout definitely moved, which bumps the severity up one band.
STRUCTURAL_GEOMETRY_CHANGE = 0.10
NOTABLE_GEOMETRY_CHANGE = 0.006

# Pixels within this of the corner color count as blank border.
BACKGROUND_TOLERANCE = 6

# A changed number in a statistics box is only a few dozen pixels -- far too
# small to move `content_fraction`, which is why it needs its own check. These
# settings look for compact spots of strong difference, using a much smaller
# movement tolerance because at 4 pixels one digit simply looks like another.
LOCALIZED_SHIFT_TOLERANCE_PIXELS = 1
LOCALIZED_INTENSITY_TOLERANCE = 80
LOCALIZED_MIN_SPOT_PIXELS = 8
LOCALIZED_MIN_TOTAL_PIXELS = 20
# A changed number is a few spots in one place. A plot whose gridlines and
# coastlines all shifted by a pixel produces spots scattered over the whole
# figure -- that is anti-aliasing, not a changed value, so ignore it.
LOCALIZED_MAX_SPOTS = 20

# Ordered least to most severe.
NEGLIGIBLE = "NEGLIGIBLE"
MINOR = "MINOR"
MODERATE = "MODERATE"
MAJOR = "MAJOR"
STRUCTURAL = "STRUCTURAL"
MISSING = "MISSING"

SEVERITY_ORDER: List[str] = [NEGLIGIBLE, MINOR, MODERATE, MAJOR, STRUCTURAL, MISSING]

# Bands at or below NEGLIGIBLE are reported but do not fail the test.
REVIEWABLE_SEVERITIES: List[str] = [MINOR, MODERATE, MAJOR, STRUCTURAL, MISSING]


class Comparison(NamedTuple):
    """The result of comparing one actual image against its expected image."""

    image_name: str
    severity: str
    content_fraction: float  # fraction of the image that looks different
    geometry_change: float  # relative change in figure size
    actual_size: Optional[Tuple[int, int]]
    expected_size: Optional[Tuple[int, int]]
    cause: str  # short human-readable guess at the root cause
    localized_pixels: int = 0  # size of small isolated changes, e.g. a changed number

    @property
    def needs_review(self) -> bool:
        return self.severity in REVIEWABLE_SEVERITIES

    def sort_key(self) -> Tuple[int, float]:
        """Worst first."""
        return (-SEVERITY_ORDER.index(self.severity), -self.content_fraction)


def trim_background(image: np.ndarray) -> np.ndarray:
    """Crop the uniform border off an image.

    Figures are saved with ``bbox_inches="tight"``, so a change in text metrics
    can add or remove a pixel of whitespace around the whole plot. Cropping the
    border first means that jitter never reaches the comparison. In the
    2026-08-04 corpus, 464 images differed by exactly one pixel of width.
    """
    background = image[0, 0].astype(np.int16)
    is_content = (
        np.abs(image.astype(np.int16) - background).max(axis=2) > BACKGROUND_TOLERANCE
    )
    if not is_content.any():
        return image
    rows = np.where(is_content.any(axis=1))[0]
    cols = np.where(is_content.any(axis=0))[0]
    return image[rows[0] : rows[-1] + 1, cols[0] : cols[-1] + 1]


def tolerant_difference(
    actual: np.ndarray, expected: np.ndarray, radius: int = SHIFT_TOLERANCE_PIXELS
) -> np.ndarray:
    """Per-pixel difference that forgives movement of up to ``radius`` pixels.

    For each pixel we ask: does this pixel's color appear *anywhere nearby* in
    the other image? If it does, the feature merely moved and we report no
    difference. If it does not, the feature genuinely changed or disappeared.

    "Anywhere nearby" is cheap to compute: the largest and smallest values in a
    neighborhood are a grayscale dilation and erosion, so a pixel matches when
    it falls between them.

    Both directions are needed, and we take the *larger* of the two. Checking
    only one direction misses thin features. Consider a contour line that was
    deleted: at that spot the actual image is blank, and blank pixels certainly
    do appear near the line in the expected image, so looking that way sees
    nothing wrong. Only the reverse check -- asking whether the line's dark
    pixels appear anywhere in the actual image -- notices that it is gone.
    """
    size = 2 * radius + 1
    worst = np.zeros(actual.shape[:2], dtype=np.float32)
    for channel in range(3):
        a = actual[..., channel].astype(np.float32)
        b = expected[..., channel].astype(np.float32)
        # How far `a` falls outside the range of `b`'s neighborhood, and vice versa.
        a_vs_b = np.maximum(
            a - ndimage.grey_dilation(b, size=size),
            ndimage.grey_erosion(b, size=size) - a,
        )
        b_vs_a = np.maximum(
            b - ndimage.grey_dilation(a, size=size),
            ndimage.grey_erosion(a, size=size) - b,
        )
        both = np.maximum(a_vs_b, b_vs_a).clip(min=0)
        worst = np.maximum(worst, both)
    return worst


def localized_change_pixels(actual: np.ndarray, expected: np.ndarray) -> int:
    """Total size of small, isolated, high-contrast differences.

    ``content_fraction`` measures area, and area is not the same as importance.
    A single wrong digit in a "Mean -0.18" label is about 13 pixels -- roughly
    240 times smaller than the noise floor -- so it can never move an
    area-based score. But it means the underlying data changed, which is
    exactly what we must not miss.

    This looks for it directly: spots where the two images differ strongly and
    which are compact rather than spread out. Anti-aliasing noise is diffuse
    and disappears here; a changed character does not. Measured on 5375
    unchanged e3sm_diags images, 5357 return zero.

    Only meaningful when the two images have the same shape, so that no
    resampling has been applied to either one.
    """
    difference = tolerant_difference(actual, expected, LOCALIZED_SHIFT_TOLERANCE_PIXELS)
    strong = difference > LOCALIZED_INTENSITY_TOLERANCE
    if not strong.any():
        return 0
    labels, count = ndimage.label(strong)
    if count == 0:
        return 0
    sizes = ndimage.sum(strong, labels, range(1, count + 1))
    spots = sizes[sizes >= LOCALIZED_MIN_SPOT_PIXELS]
    if len(spots) > LOCALIZED_MAX_SPOTS:
        return 0
    return int(spots.sum())


def _relative_size_change(actual: Tuple[int, int], expected: Tuple[int, int]) -> float:
    """Largest relative difference between two (height, width) pairs."""
    return max(
        abs(actual[0] - expected[0]) / max(actual[0], expected[0], 1),
        abs(actual[1] - expected[1]) / max(actual[1], expected[1], 1),
    )


def _describe_cause(
    geometry_change: float,
    actual_size: Tuple[int, int],
    expected_size: Tuple[int, int],
) -> str:
    """A short guess at the root cause, used to group similar failures."""
    width_lost = expected_size[1] - actual_size[1]
    height_lost = expected_size[0] - actual_size[0]
    if geometry_change >= STRUCTURAL_GEOMETRY_CHANGE:
        # The figure changed size substantially. Usually a panel came or went,
        # but axis labels or an extra statistic can do it too, so do not claim
        # more than the size actually tells us.
        return "panel or labels added/removed"
    if abs(height_lost) >= 20:
        return "title or label line added/removed"
    if geometry_change >= NOTABLE_GEOMETRY_CHANGE or abs(width_lost) > 3:
        return "layout shifted"
    return "plotted content changed"


def _files_are_identical(path_a: str, path_b: str) -> bool:
    """Compare two files byte by byte, without decoding them.

    Most images in a passing test run are untouched, and reading bytes is far
    cheaper than decoding two PNGs and comparing them pixel by pixel. Files
    that differ here may still decode to identical images; that costs nothing,
    because such a pair simply falls through to the full comparison.
    """
    if os.path.getsize(path_a) != os.path.getsize(path_b):
        return False
    chunk = 1 << 16
    with open(path_a, "rb") as file_a, open(path_b, "rb") as file_b:
        while True:
            block_a = file_a.read(chunk)
            if block_a != file_b.read(chunk):
                return False
            if not block_a:
                return True


def compare(image_name: str, actual_path: str, expected_path: str) -> Comparison:
    """Compare one image pair and return its severity."""
    if not os.path.exists(actual_path):
        return Comparison(
            image_name, MISSING, 1.0, 1.0, None, None, "image not created"
        )

    # The overwhelming majority of images do not change from one run to the
    # next -- 98.5% of the 2026-09-04 weekly test, for instance. Settling
    # those from the file bytes alone keeps the check faster than comparing
    # every pixel, which is what it replaces.
    if _files_are_identical(actual_path, expected_path):
        with Image.open(expected_path) as image:
            size = (image.height, image.width)
        return Comparison(image_name, NEGLIGIBLE, 0.0, 0.0, size, size, "identical")

    actual = np.asarray(Image.open(actual_path).convert("RGB"))
    expected = np.asarray(Image.open(expected_path).convert("RGB"))
    actual_size = actual.shape[:2]
    expected_size = expected.shape[:2]

    actual = trim_background(actual)
    expected = trim_background(expected)
    geometry_change = _relative_size_change(actual.shape[:2], expected.shape[:2])
    cause = _describe_cause(geometry_change, actual_size, expected_size)

    # A large size change means content is gone. Say so without the expensive
    # pixel comparison, which is meaningless once the layouts disagree.
    if geometry_change >= STRUCTURAL_GEOMETRY_CHANGE:
        return Comparison(
            image_name,
            STRUCTURAL,
            1.0,
            geometry_change,
            actual_size,
            expected_size,
            cause,
        )

    # Look for a changed number or label. This must happen before any
    # resampling below, which would smear the very thing it looks for.
    localized_pixels = 0
    if actual.shape == expected.shape:
        localized_pixels = localized_change_pixels(actual, expected)

    # Put both on the same grid so they can be compared pixel by pixel.
    if actual.shape != expected.shape:
        height, width = expected.shape[:2]
        actual = np.asarray(
            Image.fromarray(actual).resize((width, height), Image.Resampling.BILINEAR)
        )

    difference = tolerant_difference(actual, expected)
    content_fraction = float((difference > INTENSITY_TOLERANCE).mean())

    severity = _band(content_fraction)
    # The layout moved measurably, so treat the change as one band worse.
    if geometry_change >= NOTABLE_GEOMETRY_CHANGE:
        severity = _promote(severity)
    # Something small but possibly meaningful changed, such as a printed
    # statistic. Too small to rank highly, but it must not be filtered out.
    if localized_pixels >= LOCALIZED_MIN_TOTAL_PIXELS and severity == NEGLIGIBLE:
        severity = MINOR
        cause = "small isolated change (possible value change)"

    return Comparison(
        image_name,
        severity,
        content_fraction,
        geometry_change,
        actual_size,
        expected_size,
        cause,
        localized_pixels,
    )


def _band(content_fraction: float) -> str:
    if content_fraction <= NEGLIGIBLE_MAX:
        return NEGLIGIBLE
    if content_fraction <= MINOR_MAX:
        return MINOR
    if content_fraction <= MODERATE_MAX:
        return MODERATE
    return MAJOR


def _promote(severity: str) -> str:
    """Bump one band, but never into STRUCTURAL.

    STRUCTURAL means the figure's layout itself changed -- a panel came or
    went -- which is decided by size alone. A change that is merely large and
    slightly shifted is MAJOR, not structural.
    """
    index = SEVERITY_ORDER.index(severity)
    return SEVERITY_ORDER[min(index + 1, SEVERITY_ORDER.index(MAJOR))]


def group_by_cause(comparisons: List[Comparison]) -> Dict[Tuple[str, str], int]:
    """Count failures by (severity, cause).

    1274 failures in the 2026-08-04 run came from only a handful of root causes.
    Grouping lets a reviewer look at one example per group instead of every image.
    """
    counts: Dict[Tuple[str, str], int] = {}
    for comparison in comparisons:
        key = (comparison.severity, comparison.cause)
        counts[key] = counts.get(key, 0) + 1
    return counts
