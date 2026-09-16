.. _automated-testing-zppy:

*************************
Automated testing of zppy
*************************

Follow the steps below to test ``zppy``. A Markdown report summarizing your
results is generated automatically at the end of the run (see
``test_report_<TAG>.md`` in the directory you ran the script from).

Step 1: Determine what the current expected results are
=======================================================

Machine-specific setup
~~~~~~~~~~~~~~~~~~~~~~

Chrysalis:

.. code-block:: bash

    expected_results_dir=/lcrc/group/e3sm/public_html/zppy_test_resources
    expected_results_records_dir=/lcrc/group/e3sm/public_html/zppy_test_resources_previous

Compy:

.. code-block:: bash

    expected_results_dir=/compyfs/www/zppy_test_resources
    expected_results_records_dir=/compyfs/fors729/zppy_test_resources_previous

Note that Compy doesn't give write access to ``/compyfs/www/``, so we can't add a new directory there. That's why ``zppy_test_resources_previous`` is in a separate path.

Perlmutter:

.. code-block:: bash

    expected_results_dir=/global/cfs/cdirs/e3sm/www/zppy_test_resources
    expected_results_records_dir=/global/cfs/cdirs/e3sm/www/zppy_test_resources_previous

Process
~~~~~~~

.. code-block:: bash

    ls -lt ${expected_results_dir}

Set ``EXPECTED_RESULTS_DIR`` in your test cfg to this path. The automated
report no longer dumps the full ``ls -lt`` listing here -- it instead shows,
for each cfg/task under this directory, the date its expected-results files
were last **promoted** (copied into place).

Note that "promoted" is not the same thing as "produced," and in practice
the two are usually *further apart than you'd expect*, not closer: a run's
results normally sit under review while a task developer confirms the
diffs look acceptable, and only get promoted later -- often right before
the *next* test run needs a fresh baseline, not right after the run that
produced them. (E.g. expected results promoted on 9/4 that were actually
produced by an 8/28 run, confirmed acceptable only after the fact.) So
this promotion date is informational only -- it tells you when the files
were last touched, not what commits they reflect. Step 2 below uses a
different, more reliable date for that.

Step 2: Review changes since expected results were updated
==========================================================

Now that Step 1 above has confirmed the expected-results directory is
correctly configured, we can review what changes we'll be testing.

Each dependency's expected results can have been produced on a different
date (and a promotion's date, per Step 1, isn't reliable for this anyway),
so the report determines a *production* date separately per dependency: it
reads the ``Generated:`` line written by the test script into the
promoted ``env_description.txt`` for the corresponding task(s), taking the
earliest one found across every cfg in ``CFGS_TO_RUN`` (deliberately
conservative -- better to surface a few extra candidate commits than miss
the actual cause of a diff). If you've determined through other means
(e.g. a discussion thread) that this auto-detected date is wrong -- for
instance, the promoted results were confirmed to actually come from an
earlier run -- set the matching ``*_EXPECTED_RESULTS_DATE`` (or
``*_LAST_TESTED_DATE``, see below) in your cfg to override it.

``zppy-interfaces`` bundles two tasks, ``global_time_series`` and
``pcmdi_diags``, that get refreshed independently of each other -- one can
be updated well before the other. So rather than one ``ZI_*`` date, it gets
two: ``ZI_GLOBAL_TIME_SERIES_EXPECTED_RESULTS_DATE`` and
``ZI_PCMDI_DIAGS_EXPECTED_RESULTS_DATE``, each auto-detected (or
overridable) independently, and each shown as its own row in the report.

``e3sm_to_cmip`` and ``zppy`` have no dedicated task subdirectory of their
own at all, so there's no per-task "expected results" file to read a
production date from -- the only meaningful question for them is whether
anything has changed since the last time this dependency was tested, full
stop. So instead of ``*_EXPECTED_RESULTS_DATE`` they use
``E3SM_TO_CMIP_LAST_TESTED_DATE`` and ``ZPPY_LAST_TESTED_DATE``, which are
detected the same way but fall back to the earliest production date found
across *all* tasks, since there's no task of their own to read.

The automated report will list, for each dependency below, the commits/PRs
merged on its *expected-results baseline branch* since that date -- i.e.
the branch the expected results were actually generated from, which is not
always the same branch this run checked out to test:

* For the ``e3sm_to_cmip`` task: `e3sm_to_cmip <https://github.com/E3SM-Project/e3sm_to_cmip/commits/master>`_
* For the ``e3sm_diags`` task: `e3sm_diags <https://github.com/E3SM-Project/e3sm_diags/commits/main>`_
* For the ``mpas_analysis`` task: `MPAS-Analysis <https://github.com/MPAS-Dev/MPAS-Analysis/commits/develop/>`_
* For the ``global_time_series`` task and the ``pcmdi_diags`` task (reported as separate rows, though both point at the same repo): `zppy-interfaces <https://github.com/E3SM-Project/zppy-interfaces/commits/main>`_
* For ``zppy`` itself: `zppy <https://github.com/E3SM-Project/zppy/commits/main>`_

Each of these links is your dependency's ``*_EXPECTED_RESULTS_BRANCH``,
which defaults to the matching ``*_BASE_BRANCH`` in your cfg -- so if
you're testing straight off a project's default branch, there's nothing
extra to configure here. If instead ``*_BASE_BRANCH`` points at a
variant/feature branch (e.g. rebased onto ``main``) whose expected results
were still generated from a different branch, set that dependency's
``*_EXPECTED_RESULTS_BRANCH`` explicitly to the branch the expected results
actually came from. Otherwise the report would conflate genuine upstream
drift on the expected-results baseline with commits that only exist on the
branch under test. When the two differ, the report's table adds a "Branch
tested" column so that's visible at a glance.

For the remaining tasks (``climo``, ``ts``, ``tc_analysis``, ``ilamb``, ``livvkit``), we typically just use the associated package's latest release rather than making dev environments. As such, their latest development will have no impact on our tests unless we have started using one of their newer releases.

The report's table looks like:

.. code-block::

    | Package | Branch tested | Since | Changes since expected results were produced |
    | --- | --- | --- | --- |
    | [package name](link to expected-results baseline branch's commit log) | Branch this run tested, if different | Production date used for this dependency | Links to all PRs merged since that date |
    ...

Because this is generated from each repo's local git history, make sure each
``*_DIR`` repo has a working default remote (the script fetches the
configured ``*_EXPECTED_RESULTS_BRANCH`` non-interactively from ``upstream``
when available, otherwise ``origin``).

The automated test script
=========================

The automated test script handles the following steps from the manual testing process:

* Step 3: Set up environments for called packages
* Step 4: Set up zppy environment
* Step 5: Launch zppy jobs
* Step 6: Launch zppy jobs – bundles part 2
* Step 7: Review finished returns
* Step 8: Run all Python tests, including the image checker (``pytest tests/integration/test_images.py``), which is now launched automatically on a compute node -- no manual step required.

It additionally:

* Runs the "tests of the tests" (``tests/images/test_image_checker.py``, ``tests/images/test_image_severity.py``, and ``tests/images/test_image_summary_report.py``), which validate the image-checking logic itself, independent of any particular run's output.
* Writes an ``env_description.txt`` for each task (e.g. ``global_time_series/env_description.txt``), recording the commit hash of the relevant dev repo (or noting that a released package was used) plus the full ``conda list`` package versions for that task's environment.
* Writes a Markdown report (``test_report_<TAG>.md``) summarizing all of the above, including the complete and failing-only image-check summary tables.

A. Set up the test script
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    cd ${repo_parent_dir}/zppy
    git status # Check for uncommitted changes

    # If there are uncommitted changes,
    # commit them so we can move cleanly to a new branch:
    git add -A
    git commit -m "Checkpoint"

    git fetch upstream main # This assumes you've named your remote for the main repo as "upstream"
    git checkout -b test-zppy-yyyymmdd upstream/main # Use today's date
    git log --oneline | head -n 1
    # Check that this matches the corresponding commit log:
    # https://github.com/E3SM-Project/zppy/commits/main

    # Now, copy the test script and cfg from the zppy repo into the directory
    # that you'll be running the test script from.
    mkdir -p ${test_script_dir}/test_yyyymmdd_runN
    cd ${test_script_dir}/test_yyyymmdd_runN
    cp ${repo_parent_dir}/zppy/tests/main_branch_testing/run_integration_test.bash .
    cp ${repo_parent_dir}/zppy/tests/main_branch_testing/zppy_test.cfg .

    # Now, edit the test cfg as needed
    emacs zppy_test.cfg

B. Set up the test cfg
~~~~~~~~~~~~~~~~~~~~~~

Let's examine the parts of the test cfg.

You'll likely just need to update the ``MACHINE`` name if you're not running on Chrysalis.

.. code-block::

    # For these,

    MACHINE=chrysalis       # chrysalis | compy | perlmutter
    START_PHASE=1           # 1 | 2 | 3
    AUTO_MODE=true          # true = skip all interactive checkpoints
    EXPLICIT_TAG=""         # Leave empty to auto-generate; set to resume a prior run

Update the ``RUN_NUMBER`` if you've already done a test run today.

.. code-block::

    RUN_NUMBER=1

Update the ``_BASE_BRANCH`` parameters if you plan to test new features or bug fixes that aren't yet included on whatever the repo calls its "official" branch.

.. code-block::

    DIAGS_BASE_BRANCH="main"
    E3SM_TO_CMIP_BASE_BRANCH="master"
    MPAS_BASE_BRANCH="develop"
    ZI_BASE_BRANCH="main"
    ZPPY_BASE_BRANCH="main"

Leave the ``_EXPECTED_RESULTS_BRANCH`` parameters empty in the common case
where you're testing straight off the branch above -- each defaults to its
matching ``_BASE_BRANCH``. Only set one explicitly when its ``_BASE_BRANCH``
is a variant/feature branch but the expected results you're comparing
against were generated from a different branch (see Step 2 above).

.. code-block::

    DIAGS_EXPECTED_RESULTS_BRANCH=""
    E3SM_TO_CMIP_EXPECTED_RESULTS_BRANCH=""
    MPAS_EXPECTED_RESULTS_BRANCH=""
    ZI_EXPECTED_RESULTS_BRANCH=""
    ZPPY_EXPECTED_RESULTS_BRANCH=""

Update the ``_ENV_TYPE`` parameters if you want to use E3SM-Unified rather than a dev environment. If you plan to only run a subset of tasks, you can set the ones you aren't running to use E3SM-Unified, so that the script doesn't spend time building a dev environment that won't be used.

.. code-block::

    # "dev"     = build a dedicated conda env from the repo's dev.yml
    # "unified" = use the machine's e3sm-unified env (UNIFIED_ENV_CMD)
    DIAGS_ENV_TYPE="dev"
    E3SM_TO_CMIP_ENV_TYPE="dev"
    MPAS_ENV_TYPE="dev"
    ZI_ENV_TYPE="dev"

Update the ``_EXISTING_ENV`` parameters if you already have an environment from a previous test run to use.

.. code-block::

    # Optional: reuse an existing named conda env instead of creating a new one.
    # When non-empty AND the corresponding ENV_TYPE is "dev", the script skips
    # conda env creation and activates this env directly.
    # Leave empty to let the script auto-name and create the env as usual.
    DIAGS_EXISTING_ENV=""
    E3SM_TO_CMIP_EXISTING_ENV=""
    MPAS_EXISTING_ENV=""
    ZI_EXISTING_ENV=""
    ZPPY_EXISTING_ENV=""

Update these two parameters to configure which jobs run.

.. code-block::

    # Comma-separated list of zppy cfg names to generate and submit.
    # These correspond to generated filenames: test_weekly_<name>_<machine>.cfg
    # Any name containing "bundle" is treated as a bundle cfg and re-submitted in Phase 2.
    CFGS_TO_RUN="weekly_bundles,weekly_comprehensive_v2,weekly_comprehensive_v3,weekly_legacy_3.1.0_bundles,weekly_legacy_3.1.0_comprehensive_v2,weekly_legacy_3.1.0_comprehensive_v3,weekly_legacy_3.0.0_bundles,weekly_legacy_3.0.0_comprehensive_v2,weekly_legacy_3.0.0_comprehensive_v3"

    # Comma-separated list of tasks to enable in utils.py.
    TASKS_TO_RUN="e3sm_diags,mpas_analysis,global_time_series,ilamb,livvkit,pcmdi_diags"

Optionally, set ``EXPECTED_RESULTS_DIR`` to auto-populate Steps 1 and 2 of
the Markdown report. The per-dependency ``*_EXPECTED_RESULTS_DATE`` /
``*_LAST_TESTED_DATE`` parameters are normally left empty -- each is
auto-detected from ``env_description.txt`` under that directory (see Step 2
above) -- and only need to be set to override a specific dependency's
auto-detected date.

.. code-block::

    # Machine-specific expected-results directory (see Step 1 above).
    EXPECTED_RESULTS_DIR=""

    # Date each dependency's expected results were actually produced (see
    # Step 2 above). Normally left empty and auto-detected per dependency
    # from EXPECTED_RESULTS_DIR; set one explicitly only to override its
    # auto-detected date.
    DIAGS_EXPECTED_RESULTS_DATE=""
    MPAS_EXPECTED_RESULTS_DATE=""

    # zppy-interfaces bundles two independently-refreshed tasks, so it gets
    # two dates instead of one.
    ZI_GLOBAL_TIME_SERIES_EXPECTED_RESULTS_DATE=""
    ZI_PCMDI_DIAGS_EXPECTED_RESULTS_DATE=""

    # e3sm_to_cmip and zppy have no task subdir of their own, so there's no
    # "expected results" date to read -- these track when the dependency
    # was last tested at all, auto-detected the same way.
    E3SM_TO_CMIP_LAST_TESTED_DATE=""
    ZPPY_LAST_TESTED_DATE=""

These parameters are unlikely to change between runs. They just let the test script know where to find files in your particular workspace. It is recommended to clone a new copy of the repos and use that for each ``_DIR`` parameter listed below. The script will change branches, so using a distinct copy means you won't get your work overwritten.

.. code-block::

    HOME_DIR="$HOME"
    EZ_DIR="$HOME_DIR/ez"

    E3SM_DIAGS_DIR="$EZ_DIR/e3sm_diags"
    E3SM_TO_CMIP_DIR="$EZ_DIR/e3sm_to_cmip"
    MPAS_ANALYSIS_DIR="$EZ_DIR/MPAS-Analysis"
    ZPPY_INTERFACES_DIR="$EZ_DIR/zppy-interfaces"
    ZPPY_DIR="$EZ_DIR/zppy"

    CONDA_PROFILE="$HOME_DIR/miniforge3/etc/profile.d/conda.sh"
    TAG_CACHE_FILE="$HOME_DIR/.zppy_test_tag"


C. Run the test script
~~~~~~~~~~~~~~~~~~~~~~

Now that we have the test cfg set up, we can run it.

.. code-block:: bash

    screen # Use `screen`` so that even if the terminal connection is interrupted, the script will keep running.
    ulimit -s unlimited # This is necessary for MPAS-Analysis to work inside `screen`
    cd ${test_script_dir}/test_yyyymmdd_runN
    cat zppy_test.cfg # Make sure changes are there
    time ./run_integration_test.bash --config zppy_test.cfg 2>&1 | tee integration_test_runN.log
    # Ctrl-A D to detach from screen
    screen -ls # See what screen sessions you have
    tail -f integration_test_runN.log

Follow the ``tail`` output until you get to:

.. code-block::

    ✓ Phase 3 automated tests complete!
    ✓ Markdown report: .../test_report_yyyymmdd_runN.md
    ✓ Integration test automation complete!

The image checker now runs automatically as part of Phase 3 (submitted as
its own SLURM batch job and waited on, the same way the earlier zppy jobs
are), so there is no separate manual compute-node step to run it.

D. Review the output
~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # CTRL C # Exit tail
    screen -R # The script should have finished and there should be ``time`` output: real, user, sys
    exit # Exit screen
    cd ${test_script_dir}/test_yyyymmdd_runN
    cat integration_test_runN.log
    cat test_report_yyyymmdd_runN.md # The auto-generated Markdown report

Let's review the test script's output log.

First, the unit tests. Early in setup, you should see:

.. code-block::

    Running zppy-interfaces unit tests...

.. code-block::

    Running zppy unit tests...

Later in setup, before the image-helper test files run, you should also see:

.. code-block::

    Running tests of the image checker itself...

Second, the output directories status. It should look like the following:

.. code-block::

    Checking all status files...
    ...
    ✓ All status files clean!

If some status files were unsuccessful, you'll want to run the following to review the errors:

.. code-block:: bash

    cd ${dir_with_failures}
    grep -v "OK" * status # See what jobs failed
    # Review errors:
    tail ${job_that_failed}.o${id_of_job_that_failed}
    grep -i error ${job_that_failed}.o${id_of_job_that_failed}

Third, the integration tests.

.. code-block::

    test_last_year.py
    test_bash_generation.py
    test_campaign.py
    test_defaults.py
    test_bundles.py

Errors here may actually be expected if the expected results haven't been updated yet to reflect a recently merged pull request. Another reason for errors on ``test_bundles.py`` in particular is if you didn't run all the jobs necessary (i.e., if you're running a partial test).

Finally, the script auto-launches the image checker (``tests/integration/test_images.py``) as a SLURM job, waits for it, and folds its results straight into ``test_report_yyyymmdd_runN.md``: a "Complete summary table" section (the full contents of ``test_images_summary.md``) and, if any tests failed, a "Summary table -- only failing image-check tests, sorted by task" section. The report links directly to the SLURM job's ``.o``/``.e`` output files rather than embedding their contents (which duplicated the log and could render as an empty code block); open those files if you need the raw pytest output. Review the summary tables (and, if needed, the linked output files) to decide whether the diffs are expected.

In the Markdown report, fill in the ``Results analysis`` section at the bottom with your conclusions (e.g. whether any diffs are expected, whether expected results should be updated).

Scheduling this as a weekly cron job
=====================================

Because the image checker now launches itself and the report is generated
automatically, ``run_integration_test.bash`` no longer requires any
interactive/manual steps as long as ``AUTO_MODE=true`` in your cfg. This
makes it straightforward to run on a weekly cron schedule.

1. Set up your test cfg once, with ``AUTO_MODE=true`` and ``EXPLICIT_TAG=""``
   (so a new ``TAG`` is generated every run based on the current date).

2. Wrap the invocation in a small driver script so each week's run gets its
   own directory and log file, e.g. ``~/ez/run_zppy_weekly_test.sh``:

   .. code-block:: bash

       #!/bin/bash
       set -e
       WEEK_DIR="$HOME/ez/zppy_main_branch_tests/test_$(date +%Y%m%d)_run1"
       ZPPY_SCRIPT_SOURCE="$HOME/ez/zppy_cron_source"
       git -C "$ZPPY_SCRIPT_SOURCE" fetch upstream main
       git -C "$ZPPY_SCRIPT_SOURCE" checkout main
       git -C "$ZPPY_SCRIPT_SOURCE" reset --hard upstream/main
       mkdir -p "$WEEK_DIR"
       cd "$WEEK_DIR"
       cp "$ZPPY_SCRIPT_SOURCE/tests/main_branch_testing/run_integration_test.bash" .
       cp "$HOME/ez/zppy_weekly_test.cfg" ./zppy_test.cfg
       ulimit -s unlimited
       ./run_integration_test.bash --config zppy_test.cfg \
           > "integration_test_run1.log" 2>&1

   Keep your reusable, edited cfg at a stable path (e.g.
   ``~/ez/zppy_weekly_test.cfg``) outside of any per-run directory, since the
   driver script copies it in fresh each week. Keep the copied
   ``run_integration_test.bash`` source in a separate checkout (here
   ``~/ez/zppy_cron_source``) that the driver updates to ``main`` before each
   run, rather than reusing the per-run test checkout that Phase 1 switches to
   ``test_zppy_<TAG>``.

3. Add a weekly ``cron`` entry (edit with ``crontab -e``). For example, to
   run every Monday at 06:00 local time:

   .. code-block:: cron

       0 6 * * 1 /bin/bash -lc '$HOME/ez/run_zppy_weekly_test.sh' >> $HOME/ez/zppy_weekly_test_cron.log 2>&1

   Using ``bash -lc`` ensures your login shell environment (e.g. module
   commands, ``PATH`` for ``sbatch``/``squeue``, SSH agent for ``git fetch``)
   is loaded, since cron jobs otherwise run with a minimal environment.

4. Because ``wait_for_slurm_jobs`` and ``wait_for_slurm_job`` poll rather than
   blocking indefinitely,
   make sure the cron job's machine allows a long-running background process
   (several hours) -- e.g. run it from a persistent login node rather than a
   machine that may reboot, or launch it inside ``screen``/``tmux`` from the
   cron entry if your site's policy discourages long-lived cron processes
   directly.

5. After each run, check ``$WEEK_DIR/test_report_<TAG>.md`` for the
   "Results analysis" TODO and the failing-tests summary table; consider
   having the cron wrapper ``mail`` or post that file's contents somewhere
   visible (e.g. a Slack webhook or a PR comment) so failures don't go
   unnoticed.
