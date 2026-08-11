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

In your Markdown report, note the date the expected results were last updated, and whether they were generated using the E3SM-Unified environment or a dev environment (check the run's cfg/logs for the relevant ``_ENV_TYPE`` settings, or ask if it's unclear). This matters for Step 2.5 below.

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

Step 2.5: Refresh frozen dependency lock files (if needed)
============================================================

The test script freezes dependencies for ``e3sm_to_cmip``, ``e3sm_diags``, ``mpas_analysis``, ``zppy-interfaces``, and ``zppy`` so that ``test_images.py`` diffs can be attributed to the package under test rather than to an unrelated dependency (e.g. ``matplotlib``) that happened to move between runs. Each of these five gets its own dedicated, fully-resolved conda env (a "frozen base"); the test env for a given run is created by *cloning* that frozen base and ``pip install``-ing the branch under test on top, so nothing else in the environment can drift.

This means each of the five needs a lock file -- an exact-version ``conda list --explicit`` snapshot, not a ``dev.yml`` (a ``dev.yml`` re-solves and can drift between runs even unmodified). You only need to regenerate a component's lock file when:

* You don't have one yet (first-time setup), or
* That component's ``dev.yml`` changed in a way that should be picked up (a new or updated dependency), or
* The test script warned that ``pip install .`` pulled in something beyond the frozen base for that component (see Step C below) and you've decided to bake that change in.

Reviewing dependency-setup changes since expected results were updated
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The expected results may have been generated using either the E3SM-Unified environment or a dev environment -- see the note you made in Step 1. In practice, the first test run(s) after a new Unified release are likely to use Unified-produced results as the baseline "expected results," since a Unified release is usually the occasion for refreshing them; at other times, a dev environment may have been used instead.

Regardless of which one produced the *current* expected results, the goal for the frozen base (below) is to track Unified's dependency versions as closely as possible -- Unified is the stable common target, independent of which source happens to be backing the expected results at any given moment. What's useful to check here, before getting to that, is narrower: whether each component's *own* dependency-setup file has changed since the expected results were updated. If it has, any image-check diffs in that component's task carry extra ambiguity (dependency version change vs. a code change in the branch under test) until dependencies have been reconciled with Unified as described in the next subsection.

Review each of the following, comparing from the commit that was current on the date the expected results were last updated (Step 1) to the current commit on the relevant base branch:

* ``e3sm_to_cmip``: `conda-env/dev.yml <https://github.com/E3SM-Project/e3sm_to_cmip/commits/master/conda-env/dev.yml>`__
* ``e3sm_diags``: `conda-env/dev.yml <https://github.com/E3SM-Project/e3sm_diags/commits/main/conda-env/dev.yml>`__
* ``MPAS-Analysis``: `dev-spec.txt <https://github.com/MPAS-Dev/MPAS-Analysis/commits/develop/dev-spec.txt>`__
* ``zppy-interfaces``: `conda/dev.yml <https://github.com/E3SM-Project/zppy-interfaces/commits/main/conda/dev.yml>`__
* ``zppy``: `conda/dev.yml <https://github.com/E3SM-Project/zppy/commits/main/conda/dev.yml>`__

In your Markdown report, make a table like:

.. code-block::

    | Package | Dev setup changes since expected results were updated? |
    | --- | --- |
    | [package name](compare link, e.g. .../compare/<old-sha>...<new-sha>/<dev-file-path>) | "No changes" or a description of what changed |
    ...

Pinning dev-env dependencies to match the Unified environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The frozen base for each component should default to matching Unified's resolved dependency versions as closely as possible -- treat Unified as the target state regardless of whether the *current* expected results happen to have come from Unified or from a dev environment. Only deviate from Unified's version for a given package when the dev environment genuinely requires it: for example, a new feature merged into one of our packages needs a dependency newer than what Unified currently ships. In that case, keep the ``dev.yml``'s own (newer) constraint for that package instead of overriding it with Unified's older version, and note the deviation explicitly in your report so it isn't mistaken for accidental drift later.

This does not make the dev env identical to Unified -- the two cover different package sets, and conda's solver can still pick different transitive dependencies than Unified's solver did for the same top-level pin -- but it removes version drift in whatever packages they *do* share as an avoidable source of ambiguity in later image-check diffs.

Two scripts automate the matching part (both are standard-library-only, so no ``pip install`` is needed to run them):

* ``get_unified_versions.sh`` -- sources the Unified load script for the target machine and captures the resolved package versions of the resulting environment (via ``pip list --format=json``, with an ``importlib.metadata`` fallback, plus the interpreter's own version, since ``pip list`` doesn't report Python itself).
* ``pin_dev_env_to_unified.py`` -- cross-references those versions against a component's ``dev.yml``, sorting every dependency into one of four buckets:

  * **Pinned to Unified** -- no conflict (either the dep was unconstrained in dev.yml, or dev.yml's own constraint is satisfied by Unified's version).
  * **Forced deviation** -- dev.yml has an explicit range constraint (e.g. ``>=0.23``) that Unified's version fails to satisfy. This is detected automatically and mechanically: the constraint is parsed and checked against Unified's version, so it isn't a guess -- dev.yml's own requirement rules Unified out.
  * **Flagged for manual review** -- either an *exact* pin (e.g. ``numpy=1.24.3``) that differs from Unified's version, or a range constraint where the versions involved aren't plain dotted-numeric (e.g. a pre-release like ``1.11.0rc1``) and so can't be compared with confidence by a stdlib-only comparator. Both cases are genuinely ambiguous or unresolvable without more context, and the script deliberately doesn't guess -- it keeps dev.yml's version and leaves the decision to a human.
  * **No Unified match** -- the package isn't in Unified at all; left as-is.

.. code-block:: bash

    # 1. Capture Unified's resolved versions (once; reused for all five components).
    #    On Chrysalis, the Unified load script is:
    #    /lcrc/soft/climate/e3sm-unified/load_latest_e3sm_unified_chrysalis.sh
    ./get_unified_versions.sh <path-to-unified-load-script> unified_versions.json

    # 2. For each of the five components, cross-reference and resolve:
    python pin_dev_env_to_unified.py \
        --unified unified_versions.json \
        --devyml <path-to-component's-dev.yml-or-dev-spec.txt> \
        --out-devyml pinned-dev-<component>.yml \
        --out-report pin-report-<component>.md \
        --component <component>

Use the resulting ``pinned-dev-<component>.yml`` in place of the stock ``dev.yml`` in the "To (re)generate a lock file for a component" steps below.

.. note::

    Only the "flagged for manual review" bucket needs a human -- check ``pin-report-<component>.md`` for those packages and decide by hand whether to accept Unified's version or keep the dev.yml pin, editing the pinned file directly if you keep it. "Forced deviation" packages need no action; the script already kept dev.yml's constraint because Unified's version provably fails it.

.. important::

    Confirm the Unified load script you point at is the exact release that generated the expected results (if they came from Unified) before trusting the pin. ``load_latest_...`` tracks whichever release is currently newest -- if Unified has moved on since the expected-results date, source an archived/dated load script for that specific release instead, if your site keeps one, or you'll be comparing against a newer Unified than the one that actually produced the expected-results images.

In your Markdown report, include (or summarize) each component's ``pin-report-<component>.md``, calling out any forced deviations and any packages still flagged for manual review -- both are relevant context for interpreting later image-check diffs for that component's task.

If ``FREEZE_DEPENDENCIES=false`` in your config, you can skip this step (and the pinning step above) entirely -- every component will solve its own ``dev.yml`` fresh, as before.

To (re)generate a lock file for a component:

.. code-block:: bash

    cd ${repo_parent_dir}/<component>          # e.g. e3sm_diags, MPAS-Analysis, zppy-interfaces, zppy, e3sm_to_cmip
    conda env create -f <conda_dir>/dev.yml -n tmp-lock-gen   # or --file dev-spec.txt for mpas_analysis
    # If you pinned dependencies to Unified above, use that file instead:
    #   conda env create -f pinned-dev-<component>.yml -n tmp-lock-gen
    conda activate tmp-lock-gen
    conda list --explicit > ${EZ_DIR}/frozen-base-<component>.txt
    conda deactivate
    conda remove --yes --all --name tmp-lock-gen

Repeat for each of the five components, using the exact filenames referenced by ``BASE_ENV_LOCK_FILE_<COMPONENT>`` in your ``zppy_test.cfg`` (see Section B below). If ``FREEZE_DEPENDENCIES=false`` in your config, you can skip this step entirely -- every component will solve its own ``dev.yml`` fresh, as before.

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

These parameters control the frozen dependency base discussed in Step 2.5 above. In most runs you won't need to touch these beyond making sure ``FREEZE_DEPENDENCIES=true`` and that a lock file exists for each component in ``FROZEN_BASE_COMPONENTS``.

.. code-block::

    # Master switch. false = every component solves its own dev.yml fresh,
    # as before this feature existed.
    FREEZE_DEPENDENCIES=true

    # Which components get their own dedicated frozen base. Defaults to all
    # five dev-env components, since image-check diffs can come from any of
    # them, not just e3sm_diags/pcmdi_diags.
    FROZEN_BASE_COMPONENTS="e3sm_to_cmip,e3sm_diags,mpas_analysis,zppy_interfaces,zppy"

Further down, after ``EZ_DIR`` is defined (see below), each frozen component's lock file path is set:

.. code-block::

    BASE_ENV_LOCK_FILE_E3SM_TO_CMIP="$EZ_DIR/frozen-base-e3sm_to_cmip.txt"
    BASE_ENV_LOCK_FILE_E3SM_DIAGS="$EZ_DIR/frozen-base-e3sm_diags.txt"
    BASE_ENV_LOCK_FILE_MPAS_ANALYSIS="$EZ_DIR/frozen-base-mpas_analysis.txt"
    BASE_ENV_LOCK_FILE_ZPPY_INTERFACES="$EZ_DIR/frozen-base-zppy_interfaces.txt"
    BASE_ENV_LOCK_FILE_ZPPY="$EZ_DIR/frozen-base-zppy.txt"

If ``FREEZE_DEPENDENCIES=false``, or a component is removed from ``FROZEN_BASE_COMPONENTS``, its corresponding ``BASE_ENV_LOCK_FILE_*`` value is simply ignored.

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

If ``FREEZE_DEPENDENCIES=true``, watch for warnings like the following while Phase 1 sets up environments:

.. code-block::

    ⚠ 'test-diags-main-yyyymmdd_runN': package set changed beyond the frozen base after 'pip install .'.
    ⚠ This is expected ONLY if 'e3sm_diags' itself added or bumped a dependency:
    < some diff lines >

This means the branch under test needed something beyond what's pinned in that component's lock file. It's not necessarily a problem -- just confirm the added/bumped package is one you'd expect that branch to need, and consider regenerating that component's lock file (Step 2.5) so future runs pick it up without the warning. The full diff is also saved as ``pre_install_<env>_<TAG>.txt`` / ``post_install_<env>_<TAG>.txt`` in your run directory.

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

    Running zppy-interfaces unit tests...

and

.. code-block::

    Running zppy unit tests...

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

If ``FREEZE_DEPENDENCIES=true`` was used for this run, any diffs reported here should trace back to the branches under test in ``FROZEN_BASE_COMPONENTS`` rather than to incidental dependency movement -- that's the isolation this feature is for. If a diff still looks like it could be dependency-related, double check the ``pre_install_*``/``post_install_*`` files and any warnings from Step C for that component.

In your Markdown report:

* From the ``pytest tests/integration/test_images.py `` command-line output, copy everything after ``Captured stdout call`` to a code block labeled "Output"
* Copy the results of ``cat test_images_summary.md`` to a section labeled "Complete summary table"
* Make a new section named "Summary table -- only failing image-check tests, sorted by task". For each task that has missing and/or mismatched images, copy the relevant rows from the summary table. Skip this section if there were no failing image-check tests.
* Note any test failures from the other Python tests.
* If there were no failures at all, print "All tests pass"
