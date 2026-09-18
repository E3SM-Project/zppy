.. _automated-testing-zppy:

*************************
Automated testing of zppy
*************************

The complete run test builds development environments for ``zppy`` and the four
packages whose tasks it launches, submits the weekly test configurations,
validates the results, and writes a report.

One command runs all of it:

.. code-block:: bash

    python -m tests.complete_run.automation --machine chrysalis --account e3sm

The rest of this page covers what that command does, how to configure it, how to
read its report, and how to run it on a schedule.

What it does
============

The run moves through six stages. Each writes ``status.json`` under the run
directory, so an interrupted run can be resumed and a crashed one still produces
a report.

Everything that exercises zppy -- cfg generation, ``zppy -c``, and every test --
runs inside the environment built from the commit under test (via ``conda run``),
never in whatever environment launched the run. The environment you start the
run from only needs Python and ``mache``.

``prepare``
    Resolves each repository's branch to an immutable commit, checks that commit
    out into a detached worktree, builds a conda environment from it, and runs
    the unit tests that gate the run (``zppy``, ``zppy-interfaces``, and the
    tests covering the image checker itself). Records which baseline the run
    compares against, and writes one ``env_description.txt`` per task and a
    ``manifest.json`` for the run.

``generate``
    Generates the machine-specific cfgs from their templates.

``submit``
    Submits every selected cfg with ``zppy -c`` and waits for the queue to drain.

``bundles``
    Resubmits the bundles cfgs, which need a second pass, and waits again.

``validate``
    Sweeps every job's status files for entries that are not ``OK``, runs the
    integration tests, and submits the image checker as its own batch job.

``report``
    Writes ``complete-run-report.json`` and ``complete-run-report.md``.

Where a run lives
-----------------

Runs are not written to a personal directory. Each one gets an immutable
directory under a shared, group-writable root that the web portal serves:

.. code-block:: text

    /lcrc/group/e3sm/public_html/zppy_complete_run/
      runs/<tag>/
        manifest.json  status.json
        complete-run-report.{json,md}
        env_descriptions/          one per task
        www/                       zppy plots -- also the image baseline
        image_lists/               image_list_<cfg>.txt
        settings/                  small bash and settings baselines
        image_check/               diffs and their viewers
      baselines/
        latest-main -> ../runs/<tag>

Any maintainer can read, compare against, or promote any run. Nothing encodes
whose account produced it.

Intermediate data stays out of this tree. zppy's post-processing output
(climatologies, time series, job scripts and logs) and the worktrees are large,
and are worthless once a run is validated, so they go to your scratch space:

.. code-block:: text

    /lcrc/globalscratch/$USER/zppy_complete_run/<tag>/
      output/                      zppy post/scripts output
      worktrees/<repo>/            detached checkouts

Validation copies out everything a baseline needs from it (the bash and
settings baselines, the bundle scripts), so scratch purges never damage a
baseline. On Perlmutter this is ``/pscratch/sd/<u>/$USER/zppy_complete_run``.
Pass ``--scratch-root`` to put it somewhere else. Conda environments live
wherever conda keeps them.

On Perlmutter the root is ``/global/cfs/cdirs/e3sm/www/zppy_complete_run``.
Compy grants no write access to ``/compyfs/www``, so it has no default: pass
``--shared-root`` with a directory a maintainer has provisioned.

Your checkouts are never modified
---------------------------------

Every repository is used through a **detached worktree of one resolved commit**,
created under ``<scratch>/zppy_complete_run/<tag>/worktrees/`` and removed
when the run passes. Nothing is
committed, no branch is switched, and no clone is left on a different revision
than you left it on. You do not need a separate set of clones for testing, and
you do not need to copy anything out of the repository before starting.

Resolving a commit up front also means a branch that moves mid-run -- someone
merging to ``main`` while your jobs are queued -- cannot change what is under
test.

Because the run works from a throwaway worktree, anything ``zppy`` writes inside
its own repository (``test_images_summary.md``, ``images_logs/``, the generated
cfgs) is copied into ``runs/<tag>/artifacts/`` before cleanup. Worktrees are
**kept** when a run does not pass, so there is always something to inspect, and
when it was stopped early with ``--stop-after``, so it can be resumed.

Before you start
================

Step 1: Determine what the current baseline is
----------------------------------------------

.. code-block:: bash

    python -m tests.complete_run.promote --machine chrysalis show

That prints the run ``latest-main`` points at, the machine it ran on, when it
was produced, and the commit each repository was at. Because the baseline is a
run rather than a copy of one, this is exact -- there is no promotion date to
confuse with a production date.

For a per-task view, read the ``Generated:`` line of the baseline's environment
descriptions:

.. code-block:: bash

    baseline=$(python -m tests.complete_run.promote --machine chrysalis show \
        | python -c 'import json,sys; print(json.load(sys.stdin)["run"])')
    head -2 ${baseline}/env_descriptions/e3sm_diags.txt

Step 2: Review changes since expected results were updated
-----------------------------------------------------------

Review each commit log and note commits made since that date:

* For the ``e3sm_to_cmip`` task: `e3sm_to_cmip <https://github.com/E3SM-Project/e3sm_to_cmip/commits/master>`_
* For the ``e3sm_diags`` task: `e3sm_diags <https://github.com/E3SM-Project/e3sm_diags/commits/main>`_
* For the ``mpas_analysis`` task: `MPAS-Analysis <https://github.com/MPAS-Dev/MPAS-Analysis/commits/develop/>`_
* For the ``global_time_series`` and ``pcmdi_diags`` tasks: `zppy-interfaces <https://github.com/E3SM-Project/zppy-interfaces/commits/main>`_
* For ``zppy`` itself: `zppy <https://github.com/E3SM-Project/zppy/commits/main>`_

For the remaining tasks (``climo``, ``ts``, ``tc_analysis``, ``ilamb``,
``livvkit``), we typically use the associated package's latest release rather
than making dev environments, so their latest development has no impact unless
we have started using a newer release.

This step is human judgement; the report records what was tested, but deciding
which changes matter is yours.

Running the test
================

The run expects the five repositories cloned under one directory
(``--repo-root``, ``~/ez`` by default):

.. code-block:: text

    ~/ez/zppy
    ~/ez/e3sm_diags
    ~/ez/e3sm_to_cmip
    ~/ez/MPAS-Analysis
    ~/ez/zppy-interfaces

Then, from the ``zppy`` repository:

.. code-block:: bash

    screen  # So the run survives a dropped connection.
    ulimit -s unlimited  # Required for MPAS-Analysis to work inside `screen`.

    python -m tests.complete_run.automation \
        --machine chrysalis \
        --account e3sm \
        2>&1 | tee complete_run.log
    # Ctrl-A D to detach from screen.

Which cfgs run
--------------

By default the run submits five weekly cfgs: ``weekly_bundles``,
``weekly_comprehensive_v2``, ``weekly_comprehensive_v3``,
``weekly_legacy_3.1.0_comprehensive_v3`` and
``weekly_legacy_3.0.0_comprehensive_v3``. They are defined, together with the
case each runs against and the tasks whose plots are image-checked, in
``tests/integration/weekly_cfgs.py``.

.. note::

   **For the team: four legacy cfgs were removed.**
   ``weekly_legacy_3.0.0_bundles``, ``weekly_legacy_3.1.0_bundles``,
   ``weekly_legacy_3.0.0_comprehensive_v2`` and
   ``weekly_legacy_3.1.0_comprehensive_v2`` had been brought up to current
   syntax over time. They ended up identical to ``weekly_bundles`` and
   ``weekly_comprehensive_v2`` except for their output paths, so they reran
   the same jobs on the same data and doubled the image checks for those cases
   without testing any older syntax. The two legacy ``comprehensive_v3`` cfgs
   do still differ, in both syntax and tasks, and are kept.

   If a legacy bundles or v2 cfg is wanted again, restore it from git history
   and make it differ from the current cfg in the syntax it is meant to cover.
   Then add it to ``WEEKLY_CFGS``. ``tests/test_weekly_cfgs.py`` fails until
   the table and the templates agree.

   Two image-check gaps were closed at the same time. ``livvkit`` plots from
   ``weekly_comprehensive_v3`` and ``pcmdi_diags`` plots from
   ``weekly_legacy_3.1.0_comprehensive_v3`` were produced but never compared.
   The existing expected results already include those plots, so they are
   compared from the next run. A difference there is new coverage, not a new
   regression.

Choosing what to hold fixed
---------------------------

A comparison cannot attribute a difference to code *and* to dependencies at the
same time. Decide which of the two you are holding fixed before you run.

**Test a branch (hold dependencies fixed).** Rebuild the environment the
baseline was produced with, so any difference is attributable to the code under
review:

.. code-block:: bash

    python -m tests.complete_run.automation --machine chrysalis \
        --branch e3sm_diags=my-feature-branch \
        --env-type e3sm_diags=baseline

Each run exports every environment it built to ``environments/<repo>.yml``, so
the baseline's are reconstructible. A baseline produced before those exports
existed cannot be reproduced, and the run says so rather than quietly solving a
fresh environment instead.

**Test dependencies (hold code fixed).** Solve every environment afresh from
each repository's ``dev.yml``, from the default branches. This is the default,
and it is what the weekly scheduled run does:

.. code-block:: bash

    python -m tests.complete_run.automation --machine chrysalis

``dev.yml`` carries floating constraints that only a fresh solve exercises, so
this is the mode that catches a dependency regression.

**Use E3SM-Unified.** For a package you are not testing, skip building a dev
environment and use the released one:

.. code-block:: bash

    python -m tests.complete_run.automation --machine chrysalis \
        --env-type mpas_analysis=unified --env-type e3sm_to_cmip=unified

This is much faster when you only care about one package. ``livvkit`` always
runs from E3SM-Unified, as do ``climo``, ``ts``, ``tc_analysis``, and ``ilamb``.
``zppy`` itself cannot: the run installs the revision under test and runs pytest
from its worktree.

The three modes mix per repository, so testing an ``e3sm_diags`` branch against
baseline dependencies while everything else comes from E3SM-Unified is one
command:

.. code-block:: bash

    python -m tests.complete_run.automation --machine chrysalis \
        --branch e3sm_diags=my-feature-branch \
        --env-type e3sm_diags=baseline \
        --env-type mpas_analysis=unified \
        --env-type e3sm_to_cmip=unified \
        --env-type zppy_interfaces=unified \
        --cfg weekly_comprehensive_v3 --task e3sm_diags

The report records which mode each repository used, under ``environment_type``
and ``environment_source``, so a reader can tell what was held fixed.

.. note::

   Reproducing a baseline's environment is not the same as pinning
   dependencies. zppy deliberately does not test against frozen environments
   (see the `testing strategy discussion
   <https://github.com/E3SM-Project/zppy/discussions/856>`_); the exports exist
   so that a *branch* can be evaluated against a known-good environment, not so
   that the weekly run stops seeing dependency changes.

Common options
--------------

Run a subset of cfgs or tasks:

.. code-block:: bash

    python -m tests.complete_run.automation --machine chrysalis \
        --cfg weekly_comprehensive_v3 --cfg weekly_bundles \
        --task e3sm_diags --task global_time_series

Reuse environments from an earlier run today:

.. code-block:: bash

    python -m tests.complete_run.automation --machine chrysalis \
        --existing-env zppy=test-zppy-main-20260918_run1

Resume an interrupted run. Pass the same ``--tag``, so it finds the worktrees
and environments the first attempt created. The cfgs, tasks, environments, and
baseline recorded in its ``status.json`` carry over; pass ``--cfg`` or ``--task``
only to change them:

.. code-block:: bash

    python -m tests.complete_run.automation --machine chrysalis \
        --tag 20260918_run1 --start-stage validate

Stop early, to check the setup before committing to a full run:

.. code-block:: bash

    python -m tests.complete_run.automation --machine chrysalis \
        --stop-after prepare

Build the environments concurrently, which shortens ``prepare`` considerably.
It is off by default because parallel solves load a shared login node:

.. code-block:: bash

    python -m tests.complete_run.automation --machine chrysalis --parallel-envs 5

``--help`` lists every option, including the polling intervals and timeouts.

Reading the report
==================

Both reports land in the run directory under the shared root:

.. code-block:: text

    <shared root>/runs/<tag>/
        complete-run-report.json   Machine-readable.
        complete-run-report.md     For the weekly testing log.
        manifest.json              Commits, environments, and selections.
        status.json                Stage-by-stage state.
        env_descriptions/          One per task.
        artifacts/                 Copied out of the worktree.
        image_checker_<tag>.o<id>  Image checker output.

The Markdown report opens with the overall status and the baseline it was
compared against (with the date that baseline was produced), then covers what was tested
(each repository's commit and environment), the job status-file sweep, the
integration test results, and the image checker's severity breakdown. Paste it
into the `weekly testing log <https://github.com/E3SM-Project/zppy/discussions/845>`_.

The severity table separates images that need review from ones that do not.
``IDENTICAL`` and ``NEGLIGIBLE`` do not fail the test; ``MINOR`` through
``MISSING`` do. See :ref:`image_checking` for how to read them.

Reviewing image differences
---------------------------

Start from the run's summary page, ``runs/<tag>/index.html``. It has two
tables. **By package** gives each package (``e3sm_diags``, ``MPAS-Analysis``,
``zppy-interfaces``, ``ILAMB``, ``LIVVkit``), the commit or environment it was
tested at, its worst result, and how many checks and images need review.
**By check** has one row per cfg and task with the full severity breakdown and
a link to that task's page. A task that should have been image-checked but
recorded no comparison is listed as *not checked*, rather than being left out.


Each task's diff directory gets an ``index.html`` listing every image that needs
review, with the plot beside its baseline and their difference, ranked worst
first. It filters by severity, by likely cause, and by name, and reports how
many images were identical or looked cosmetic without listing them.

Above the images, each page reports **how this run's dependencies differed from
the baseline's**, because that decides how to read everything below it:

* **No dependency changed** -- an image difference is attributable to the code
  under test.
* **Dependencies changed** (a fresh solve) -- the listed packages moved, and an
  image difference may come from them rather than from zppy. Here the
  dependency list *is* the finding.
* **A reproduction that did not take** -- the run asked for
  ``--env-type <repo>=baseline`` but the environment still differs. The panel
  opens by default and is marked, because the image differences prove nothing
  about the code until it is resolved.

Packages that most often move results (``numpy``, ``matplotlib``, ``xarray``,
``nco``, ``esmf``, the analysis packages themselves) are listed first and
marked. The comparison ignores the environment's name and prefix, which differ
on every run by design and would otherwise bury the real changes.

The same comparison appears in the report's ``## Environment`` section, ahead of
the results.

Because the run directory is served by the portal, that page has a URL. The
report links to one per task, so reviewing a run means opening a page rather
than browsing thousands of files over SSH.

Failures are for human review. **A complete run never promotes a baseline on its
own**; promotion is always a separate, explicit command.

If a run does not pass
----------------------

The report names what failed. To dig further:

.. code-block:: bash

    # Job output is on scratch; the report prints the exact path.
    cd /lcrc/globalscratch/$USER/zppy_complete_run/<tag>/output/zppy_<cfg>_output/run/<case>/post/scripts
    grep -v "OK" *status                       # Which jobs failed.
    tail ${job_that_failed}.o${job_id}         # Why.
    grep -i error ${job_that_failed}.o${job_id}

Errors in the integration tests may be expected if the expected results have not
been updated to reflect a recently merged pull request, or if you ran only a
subset of the cfgs.

Worktrees and environments are retained after a failure. Once you have finished
with them:

.. code-block:: bash

    git worktree list          # In each repository.
    conda env list | grep test-

Running it on a schedule
========================

``tests/complete_run/`` carries a controller and a crontab template. The
controller holds a lock (``LOCK_FILE``, ``~/.zppy_complete_run.lock`` by
default) for the length of a run, so a second firing while one is still going
exits immediately rather than overlapping. Leave ``SHARED_ROOT`` empty to use the
machine's default shared root.

Chrysalis has no ``scrontab`` -- that is NERSC-specific -- so this is an
ordinary login-node crontab.

1. Copy the configuration template somewhere outside the repository and fill it
   in. It names accounts and paths specific to you:

   .. code-block:: bash

       cp tests/complete_run/complete-run.config.env.template ~/.zppy-complete-run.env
       $EDITOR ~/.zppy-complete-run.env

2. Fill in the crontab template's placeholders and install it:

   .. code-block:: bash

       $EDITOR tests/complete_run/complete-run.crontab.template
       crontab tests/complete_run/complete-run.crontab.template
       crontab -l

3. Check on it:

   .. code-block:: bash

       tail -f <LOG_DIR>/complete-run-controller.log

.. warning::

   Login-node crontabs are **per node**. An entry installed on ``chrlogin1``
   does not exist on ``chrlogin2``. Install it on one node, record which one,
   and check there when a run does not appear.

Set ``WEEK_PARITY`` to ``even`` or ``odd`` in the configuration file to gate the
weekly schedule down to biweekly; standard cron cannot express "every second
Monday" across month boundaries on its own.

Promoting a baseline
====================

A run *is* the baseline material -- its ``www`` tree holds the plots, and its
``image_lists`` and ``settings`` directories describe what it produced. Nothing
is copied at promotion time; ``baselines/latest-main`` is pointed at the run:

.. code-block:: bash

    python -m tests.complete_run.promote --machine chrysalis run 20260918_run1

That is atomic, takes no time regardless of how many images the run produced,
and leaves the previous baseline exactly where it was. Rolling back is promoting
the old run again:

.. code-block:: bash

    python -m tests.complete_run.promote --machine chrysalis show
    python -m tests.complete_run.promote --machine chrysalis run 20260911_run1

Promotion reads the run's own report and manifest, and refuses a run that did
not pass or that was built from a feature branch:

.. code-block:: bash

    # After reviewing the differences and deciding the new results are correct:
    python -m tests.complete_run.promote --machine chrysalis run 20260918_run1 \
        --allow-failed

Expected results legitimately change when a dependency improves a plot, so
``--allow-failed`` is a normal part of the workflow -- but it should follow
reviewing the diff viewer, not replace it.

Release snapshots are another channel rather than another copy:

.. code-block:: bash

    python -m tests.complete_run.promote --machine chrysalis run 20260918_run1 \
        --channel unified_1.13.0

Comparing against a specific baseline
-------------------------------------

``--baseline-dir`` on cfg generation, or ``ZPPY_COMPLETE_RUN_BASELINE`` when
running the image checker directly, compares against a run other than
``latest-main``.

Deleting old runs
-----------------

Runs a channel points at are kept forever. The rest are pruned:

.. code-block:: bash

    python -m tests.complete_run.promote --machine chrysalis prune --keep 8
    # Reports what it would delete; add --delete to do it.

Generating cfgs by hand
=======================

The complete run generates cfgs through a command-line interface, so it never
edits ``tests/integration/utils.py``. The same interface is available directly:

.. code-block:: bash

    python -m tests.integration.utils \
        --unique-id my_test_id \
        --cfg weekly_comprehensive_v3 \
        --task e3sm_diags \
        --env-cmd "e3sm_diags=source ~/miniforge3/etc/profile.d/conda.sh; conda activate my_diags_env"

Anything not passed keeps its value from ``TEST_SPECIFICS``, so editing that
dict by hand and running ``python tests/integration/utils.py`` still works for a
one-off run.

Running the steps by hand
=========================

See :ref:`manually-testing-zppy` for the underlying manual procedure. It remains
the reference for what each stage does, and is worth following when debugging a
stage that keeps failing.
