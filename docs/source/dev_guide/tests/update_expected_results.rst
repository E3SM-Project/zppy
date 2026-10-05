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

A baseline is one whole run, so a promotion updates every cfg and task at once.
This is deliberate: a baseline assembled from several runs is hard to reason
about when a difference later appears, because the results were produced by
different code and different dependencies.

There is no way to accept a change in one task only. Do not promote a run made
with a reduced ``--cfg`` or ``--task`` selection: a run's expected image lists
are built by walking its own ``www`` tree, so such a run becomes a baseline
that holds only the tasks it ran, and every other task then records no
comparison against it. Promote a run that covered everything.

Deleting old runs
=================

Runs that a channel points at are kept indefinitely. Everything else is subject
to pruning:

.. code-block:: bash

    # Reports what it would delete.
    python -m tests.complete_run.promote --machine chrysalis prune --keep 8
    # Actually delete.
    python -m tests.complete_run.promote --machine chrysalis prune --keep 8 --delete

Comparing against something other than latest-main
==================================================

.. code-block:: bash

    python -m tests.complete_run.automation --machine chrysalis \
        --baseline-dir /lcrc/group/e3sm/public_html/zppy_complete_run/runs/20260901_run1

When running the image checker directly, set ``ZPPY_COMPLETE_RUN_BASELINE``
instead.
