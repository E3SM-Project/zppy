.. _image_checking:

**********************
Reviewing image checks
**********************

The integration tests compare every image a run produces against a saved
expected image. This page explains how to review what comes back.

Why images differ
=================

Two images can differ for very different reasons:

* **Cosmetic.** Upgrading matplotlib changes text metrics slightly. Figures are
  saved with ``bbox_inches="tight"``, so a plot can come out a pixel wider and
  every anti-aliased edge lands a fraction of a pixel away. Nothing about the
  science changed.
* **Real.** A panel is missing, a title was dropped, a contour moved, or a
  printed statistic changed. These need a person to look at them.

A plain pixel-by-pixel comparison cannot tell these apart. Visually identical
plots routinely differ in 2-20% of their pixels after a matplotlib upgrade, so
comparing raw pixels reports essentially every image as a failure. In the
2026-08-04 weekly test that meant 1274 of 1280 MPAS-Analysis images were listed
as failures with nothing to distinguish them.

Severity
========

Each image pair is therefore given a severity, and failures are sorted worst
first. Work down the list and stop when the differences stop mattering.

.. list-table::
   :header-rows: 1
   :widths: 15 60 25

   * - Severity
     - Meaning
     - What to do
   * - ``STRUCTURAL``
     - The figure changed size enough that a panel came or went.
     - Always investigate.
   * - ``MAJOR``
     - A large part of the plot looks different.
     - Always investigate.
   * - ``MODERATE``
     - A visible part of the plot looks different.
     - Investigate.
   * - ``MINOR``
     - Slightly different, or a small isolated change such as a printed number.
     - Skim.
   * - ``NEGLIGIBLE``
     - Cosmetic only.
     - Nothing. Counted in the summary, not reported as a failure.
   * - ``MISSING``
     - The image was never created.
     - Always investigate.

``NEGLIGIBLE`` images do not fail the test and no diff images are written for
them. They are still counted, so the summary table always adds up.

What gets written
=================

Alongside the existing outputs, each task's diff directory gets:

``severity_report.txt``
    The ranked list. Start here. It opens with counts, then a grouping by
    likely cause, then every image needing review, worst first.

``image_scores.json``
    The same information as raw numbers, one entry per image. Useful for
    re-examining thresholds without re-running the comparison.

Reviewing efficiently
=====================

Most failures share a handful of root causes -- a single upstream change can
alter hundreds of images identically. ``severity_report.txt`` therefore groups
failures by cause before listing them:

.. code-block:: none

    Grouped by cause (check one example from each):
         381  STRUCTURAL   panel added/removed
         302  MAJOR        title or label line added/removed
          53  MAJOR        layout shifted
          28  MODERATE     plotted content changed
           9  MINOR        small isolated change (possible value change)

Check one example from each group rather than every image. If the example is a
genuine regression, the whole group almost certainly is too.

A note on small changes
=======================

Severity is based on how much of the picture looks different, and that is not
the same as how much it matters. A single wrong digit in a ``Mean -0.18`` label
is about 13 pixels, far too small to affect an area-based score, but it means
the data changed.

Those are found by a separate check that looks for small, sharply-defined
differences, and reported as ``MINOR`` with the cause "small isolated change
(possible value change)". Do not skip that group just because it ranks low --
it is the one place where a low rank does not mean a small problem.
