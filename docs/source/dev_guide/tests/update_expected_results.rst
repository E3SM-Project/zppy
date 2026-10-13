.. _updating-expected-results:

*************************
Updating expected results
*************************

Expected results are not a copy of a run. They *are* a run: the complete run
test writes each run into its own immutable directory, and promotion points
``baselines/latest-main`` at one of them.

That has three consequences worth knowing before you promote anything:

* Promotion is instant and atomic, however many images the run produced.
* The previous baseline is not destroyed. It is still a run directory sitting
  beside the new one, so rolling back is promoting it again.
* There is nothing to archive by hand beforehand.

Choosing a run to promote
=========================

List what is promoted now, and what the run you are considering contains:

.. code-block:: bash

    python -m tests.complete_run.promote --machine chrysalis show
    ls /lcrc/group/e3sm/public_html/zppy_complete_run/runs

Read the run's report before promoting it. If images changed, open the diff
viewer the run produced and confirm each change is one you meant to accept --
see :ref:`image_checking` for how to read severities.

Promoting
=========

.. code-block:: bash

    python -m tests.complete_run.promote --machine chrysalis run 20260918_run1

Promotion reads the run's own report and manifest rather than trusting the
command line, and refuses a run that did not pass or that was built from a
feature branch.

When a dependency legitimately changes a plot, the run will not have passed --
that is the normal case for updating expected results. Promote it deliberately:

.. code-block:: bash

    python -m tests.complete_run.promote --machine chrysalis run 20260918_run1 \
        --allow-failed

Use ``--allow-failed`` after reviewing the differences, not instead of it.

Rolling back
============

.. code-block:: bash

    python -m tests.complete_run.promote --machine chrysalis run 20260911_run1

Release snapshots
=================

A release snapshot is another channel pointing at the same kind of run, not
another copy of the images:

.. code-block:: bash

    python -m tests.complete_run.promote --machine chrysalis run 20260918_run1 \
        --channel unified_1.13.0

Partial updates
===============

A channel's baseline is its default run plus optional per-cfg/task overrides.
Overrides point at whole immutable runs; no images or other results are copied.
This lets a reviewed task be updated without changing the baseline used by
other tasks:

.. code-block:: bash

    python -m tests.complete_run.promote --machine chrysalis run 20260918_run1 \
        --cfg weekly_comprehensive_v3 --task pcmdi_diags
    python -m tests.complete_run.promote --machine chrysalis show

The selected entries must have passed their job-status checks and, for plotting
tasks, have a clean image comparison. A failure elsewhere in the run does not
prevent promoting a passing entry. ``--allow-failed`` and ``--allow-non-main``
remain available after review. To roll an entry back, promote its previous run
for the same ``--cfg``/``--task`` selection. Promoting a whole run without
selectors updates the channel default and clears its overrides.

To compare against a different run without changing channel defaults, select it
when launching automation. Repeat ``--baseline`` to select task-wide or
cfg/task-specific runs; exact cfg/task selections take precedence:

.. code-block:: bash

    python -m tests.complete_run.automation --machine chrysalis \
        --baseline pcmdi_diags=20260911_run1 \
        --baseline weekly_comprehensive_v3:pcmdi_diags=20260918_run1

For ``--env-type <repo>=baseline``, all selected tasks using the same repository
environment must resolve to one baseline run. Automation stops with an error if
they resolve to different runs.

Deleting old runs
=================

Runs referenced by any channel's default or overrides are kept indefinitely.
Other runs are subject to pruning:

.. code-block:: bash

    # Reports what it would delete.
    python -m tests.complete_run.promote --machine chrysalis prune --keep 8
    # Also restrict candidates to runs older than 60 days.
    python -m tests.complete_run.promote --machine chrysalis prune --keep 8 \
        --older-than 60
    # Actually delete.
    python -m tests.complete_run.promote --machine chrysalis prune --keep 8 --delete

Comparing against something other than latest-main
==================================================

.. code-block:: bash

    python -m tests.complete_run.automation --machine chrysalis \
        --baseline pcmdi_diags=20260901_run1

For cfg generation, ``--baseline-dir`` still selects a run directory directly.
When running the image checker directly, set ``ZPPY_COMPLETE_RUN_BASELINE``.
Both mechanisms use that run for every task unless a more specific cfg/task
selection is provided.
