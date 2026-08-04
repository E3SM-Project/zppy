.. _automated-testing-zppy:

*************************
Automated testing of zppy
*************************

Follow the steps below to test ``zppy``. As you do so, please produce a Markdown report summarizing your results.

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

In your Markdown report, note the date the expected results were last updated.

Step 2: Review changes since expected results were updated
==========================================================

Now that we know the date the expected results are from, we can review what changes we'll be testing.

Review each of the following commit logs and note commits made since the date the expected results were updated:

* For the ``e3sm_to_cmip`` task: `e3sm_to_cmip <https://github.com/E3SM-Project/e3sm_to_cmip/commits/master>`_
* For the ``e3sm_diags`` task: `e3sm_diags <https://github.com/E3SM-Project/e3sm_diags/commits/main>`_
* For the ``mpas_analysis`` task: `MPAS-Analysis <https://github.com/MPAS-Dev/MPAS-Analysis/commits/develop/>`_
* For the ``global_time_series`` and ``pcmdi_diags`` tasks: `zppy-interfaces <https://github.com/E3SM-Project/zppy-interfaces/commits/main>`_
* For ``zppy`` itself: `zppy <https://github.com/E3SM-Project/zppy/commits/main>`_

For the remaining tasks (``climo``, ``ts``, ``tc_analysis``, ``ilamb``, ``livvkit``), we typically just use the associated package's latest release rather than making dev environments. As such, their latest development will have no impact on our tests unless we have started using one of their newer releases.

In your Markdown report, make a table like:

.. code-block::

    | Package | Changes since expected results were updated |
    | --- | --- |
    | [package name](link to package's commit log) | Links to all PRs merged since the expected results were updated |
    ...

The automated test script
=========================

The automated test script handles the following steps from the manual testing process:

* Step 3: Set up environments for called packages
* Step 4: Set up zppy environment
* Step 5: Launch zppy jobs
* Step 6: Launch zppy jobs – bundles part 2
* Step 7: Review finished returns
* Step 8: Run Python tests (excluding the final ``pytest tests/integration/test_images.py`` call from a compute node)

A. Set up the test script
~~~~~~~~~~~~~~~~~~~~~~

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
~~~~~~~~~~~~~~~~~~~

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
    ✓ Remember to run test_images.py manually from a compute node.
    ✓ Integration test automation complete!

D. Review the output
~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # CTRL C # Exit tail
    screen -R # The script should have finished and there should be ``time`` output: real, user, sys
    exit # Exit screen
    cd ${test_script_dir}/test_yyyymmdd_runN
    cat integration_test_runN.log

Let's review the test script's output log.

First, the unit tests. There are two blocks, starting with:

.. code-block::

    Running zppy unit tests...

and

.. code-block::

    Running zppy-interfaces unit tests...

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

If all 3 pieces look good, you can proceed with the final integration test, the image checker.

Step 8: Run Python tests
========================

Machine-specific setup
~~~~~~~~~~~~~~~~~~~~~~

Chrysalis:

.. code-block:: bash

    launch_compute_node()
    {
        salloc --nodes=1 --partition=debug --time=02:00:00 --account=e3sm
    }

Compy:

.. code-block:: bash

    launch_compute_node()
    {
        salloc --nodes=1 --partition=short --time=01:00:00 --account=e3sm
    }

Perlmutter:

.. code-block:: bash

    launch_compute_node()
    {
        salloc --nodes=1 --qos=interactive --time=01:00:00 --constraint=cpu --account=e3sm
    }

Process
~~~~~~~

.. code-block:: bash

    cd ${repo_parent_dir}/zppy
    git status
    # You might have changed branches while you were waiting for jobs to finish.
    # Make sure you're now back on the correct branch: test-zppy-yyyymmdd
    # Also confirm you're back in the correct env: zppy-yyyymmdd or the Unified env

    # The image checker test, which we'll run from a compute node:
    launch_compute_node

    start_bash_subshell
    # EITHER:
    # Activate EITHER a dev environment or the Unified env:
    conda activate zppy-yyyymmdd
    # OR: the command from `activate_unified_env`

    pytest tests/integration/test_images.py
    # Typically takes between 10 and 20 minutes on Chrysalis and Perlmutter.
    # Typically takes closer to 50 minutes on Compy.
    cat test_images_summary.md
    exit # Exit bash shell
    exit # Exit compute note

In your Markdown report:

* From the ``pytest tests/integration/test_images.py `` command-line output, copy everything after ``Captured stdout call`` to a code block labeled "Output"
* Copy the results of ``cat test_images_summary.md`` to a section labeled "Complete summary table"
* Make a new section named "Summary table -- only failing image-check tests, sorted by task". For each task that has missing and/or mismatched images, copy the relevant rows from the summary table. Skip this section if there were no failing image-check tests.
* Note any test failures from the other Python tests.
* If there were no failures at all, print "All tests pass"
