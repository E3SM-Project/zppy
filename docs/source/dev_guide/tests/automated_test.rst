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

Set ``EXPECTED_RESULTS_DIR`` in your test cfg to this path, and the
automated report will include this ``ls -lt`` output (and the date the
expected results were last updated) for you automatically.

Step 2: Review changes since expected results were updated
==========================================================

Now that we know the date the expected results are from, we can review what changes we'll be testing.

Set ``EXPECTED_RESULTS_UPDATED_DATE`` in your test cfg to that date (e.g.
``"2026-08-12"``), and the automated report will list, for each dependency
below, the commits/PRs merged on its default branch since that date:

* For the ``e3sm_to_cmip`` task: `e3sm_to_cmip <https://github.com/E3SM-Project/e3sm_to_cmip/commits/master>`_
* For the ``e3sm_diags`` task: `e3sm_diags <https://github.com/E3SM-Project/e3sm_diags/commits/main>`_
* For the ``mpas_analysis`` task: `MPAS-Analysis <https://github.com/MPAS-Dev/MPAS-Analysis/commits/develop/>`_
* For the ``global_time_series`` and ``pcmdi_diags`` tasks: `zppy-interfaces <https://github.com/E3SM-Project/zppy-interfaces/commits/main>`_
* For ``zppy`` itself: `zppy <https://github.com/E3SM-Project/zppy/commits/main>`_

For the remaining tasks (``climo``, ``ts``, ``tc_analysis``, ``ilamb``, ``livvkit``), we typically just use the associated package's latest release rather than making dev environments. As such, their latest development will have no impact on our tests unless we have started using one of their newer releases.

The report's table looks like:

.. code-block::

    | Package | Changes since expected results were updated |
    | --- | --- |
    | [package name](link to package's commit log) | Links to all PRs merged since the expected results were updated |
    ...

Because this is generated from each repo's local git history, make sure each
``*_DIR`` repo has fetched ``upstream`` recently (the script does this
itself for the branch it tests, via ``git fetch upstream``).

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

* Runs the "tests of the tests" (``tests/images/test_image_checker.py`` and ``tests/images/test_image_severity.py``), which validate the image-checking logic itself, independent of any particular run's output.
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

Optionally, set these two parameters to auto-populate Steps 1 and 2 of the Markdown report.

.. code-block::

    # Machine-specific expected-results directory (see Step 1 above).
    EXPECTED_RESULTS_DIR=""

    # Date the expected results were last updated (see Step 2 above).
    EXPECTED_RESULTS_UPDATED_DATE=""

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

First, the unit tests. There are three blocks, starting with:

.. code-block::

    Running zppy-interfaces unit tests...

.. code-block::

    Running zppy unit tests...

and

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

Finally, the script auto-launches the image checker (``tests/integration/test_images.py``) as a SLURM job, waits for it, and folds its results straight into ``test_report_yyyymmdd_runN.md``: a "Complete summary table" section (the full contents of ``test_images_summary.md``) and, if any tests failed, a "Summary table -- only failing image-check tests, sorted by task" section. Review these tables (and the raw ``Captured stdout call`` output also embedded in the report) to decide whether the diffs are expected.

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

4. Because ``wait_for_slurm_jobs`` polls rather than blocking indefinitely,
   make sure the cron job's machine allows a long-running background
   process (several hours) -- e.g. run it from a persistent login node
   rather than a machine that may reboot, or launch it inside ``screen``/
   ``tmux`` from the cron entry if your site's policy discourages long-lived
   cron processes directly.

5. After each run, check ``$WEEK_DIR/test_report_<TAG>.md`` for the
   "Results analysis" TODO and the failing-tests summary table; consider
   having the cron wrapper ``mail`` or post that file's contents somewhere
   visible (e.g. a Slack webhook or a PR comment) so failures don't go
   unnoticed.
