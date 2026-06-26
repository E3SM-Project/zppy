.. _testing-zppy:

*************
Testing zppy
*************

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

Step 3: Set up environments for called packages
===============================================

Machine-specific setup
~~~~~~~~~~~~~~~~~~~~~~

Chrysalis:

.. code-block:: bash

    repo_parent_dir=~/ez/ # Or wherever you keep your repos
    
    start_bash_subshell()
    {
        bash
        source ~/.bashrc # Or wherever you have your aliases, etc. defined
    }

    activate_dev_env()
    {
        env_name=$1

        lcrc_conda # Or however you activate conda
        rm -rf build
        conda clean --all --y
        conda env create -f conda/dev.yml -n ${env_name}
        conda activate ${env_name}
        pre-commit run --all-files # Confirm this passes
        python -m pip install .
    }

    activate_unified_env()
    {
        source /lcrc/soft/climate/e3sm-unified/load_latest_e3sm_unified_chrysalis.sh
    }

Compy:

.. code-block:: bash

    repo_parent_dir=~/ez/ # Or wherever you keep your repos

    start_bash_subshell()
    {
        bash
        source ~/.bash_profile # Or wherever you have your aliases, etc. defined
    }
    
    activate_dev_env()
    {
        env_name=$1

        compy_conda # Or however you activate conda
        rm -rf build
        conda clean --all --y
        conda env create -f conda/dev.yml -n ${env_name}
        conda activate ${env_name}
        pre-commit run --all-files # Confirm this passes
        python -m pip install .
    }

    activate_unified_env()
    {
        source /share/apps/E3SM/conda_envs/load_latest_e3sm_unified_compy.sh
    }

Perlmutter:

.. code-block:: bash

    repo_parent_dir=~/ez/ # Or wherever you keep your repos

    start_bash_subshell()
    {
        bash
        source ~/.bash_profile.ext # Or wherever you have your aliases, etc. defined
    }

    activate_dev_env()
    {
        env_name=$1

        nersc_conda # Or however you activate conda
        rm -rf build
        conda clean --all --y
        conda env create -f conda/dev.yml -n ${env_name}
        conda activate ${env_name}
        pre-commit run --all-files # Confirm this passes
        python -m pip install .
    }

    activate_unified_env()
    {
        source /global/common/software/e3sm/anaconda_envs/load_latest_e3sm_unified_pm-cpu.sh
    }

Process
~~~~~~~

.. code-block:: bash

    set_up_repo()
    {
        repo_name=$1
        main_branch_name=$2

        cd ${repo_parent_dir}/${repo_name}
        git status # Check for uncommitted changes

        # If there are uncommitted changes, 
        # commit them so we can move cleanly to a new branch:
        git add -A
        git commit -m "Checkpoint"

        git fetch upstream ${main_branch_name} # This assumes you've named your remote for the main repo as "upstream"
        git checkout ${main_branch_name}
        git reset --hard upstream/${main_branch_name}
        git log --oneline | head -n 1
        # Check that this matches the corresponding commit log:
        # https://github.com/E3SM-Project/e3sm_to_cmip/commits/master
        # https://github.com/E3SM-Project/e3sm_diags/commits/main
        # https://github.com/MPAS-Dev/MPAS-Analysis/commits/develop/
        # https://github.com/E3SM-Project/zppy-interfaces/commits/main

        # Activate EITHER a dev environment or the Unified env:
        # Dev environment -- test latest development
        # Unified environment -- test latest Unified environment
        activate_dev_env ${repo_name}-yyyymmdd # Use today's date
        # OR: activate_unified_env ${repo_name}-yyyymmdd # Use today's date
    }


.. code-block:: bash

    start_bash_subshell
    set_up_repo e3sm_to_cmip master
    exit # Exit bash subshell

    start_bash_subshell
    set_up_repo e3sm_diags main
    exit # Exit bash subshell

    start_bash_subshell
    set_up_repo MPAS-Analysis develop
    exit # Exit bash subshell

    start_bash_subshell
    set_up_repo zppy-interfaces main
    # Since zppy-interfaces is so integrated into `zppy`,
    # run its unit tests as well:
    pytest tests/unit/global_time_series/test_*.py
    pytest tests/unit/pcmdi_diags/test_*.py
    exit # Exit bash subshell

Step 4: Set up zppy environment
===============================

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

    start_bash_subshell
    # Activate EITHER a dev environment or the Unified env:
    # Dev environment -- test latest development
    # Unified environment -- test latest Unified environment
    activate_dev_env zppy-yyyymmdd # Use today's date
    # OR: activate_unified_env zppy-yyyymmdd # Use today's date

    # Note the Python version being used
    # If you activated dev env:
    conda list python 
    # If you activated unified env:
    pixi list python

    # Run zppy unit tests
    pytest tests/test_*.py # 44 passed in 0.87s

Step 5: Launch zppy jobs
========================

Machine-specific setup
~~~~~~~~~~~~~~~~~~~~~~

Chrysalis:

.. code-block:: bash

    conda_setup_cmd=source /gpfs/fs1/home/ac.forsyth2/miniforge3/etc/profile.d/conda.sh
    output_dir=/lcrc/group/e3sm/ac.forsyth2

Compy:

.. code-block:: bash

    conda_setup_cmd=source /qfs/people/fors729/miniforge3/etc/profile.d/conda.sh
    output_dir=/compyfs/fors729

Perlmutter:

.. code-block:: bash

    conda_setup_cmd=source /global/homes/f/forsyth/miniforge3/etc/profile.d/conda.sh
    output_dir=/global/cfs/cdirs/e3sm/forsyth

Process
~~~~~~~

First, let's edit ``tests/integration/utils.py``. 

In place of each ``{env_cmd}`` put either ``${conda_setup_cmd}; conda activate ${repo_name}-yyyymmdd`` or the command from ``activate_unified_env``. You may want to use dev environments for some tasks and the Unified environment for others.

You can comment out ``cfg``s from ``cfgs_to_run`` to run fewer configuration files. Likewise, you can comment out tasks from ``tasks_to_run`` to run fewer tasks.

Be sure to set the ``unique_id``; this allows us to avoid path name collisions.

.. code-block:: python

    TEST_SPECIFICS: Dict[str, Any] = {
        # This is the NCO path.
        # Keep as "" to use the production-version NCO commands.
        # Set to a specific path to use development-version NCO commands.
        "nco_path": "",
        # These are custom environment_commands for specific tasks.
        # Never set these to "", because they will print the line
        # `environment_commands = ""` for the corresponding task,
        # thus overriding the value set higher up in the cfg.
        # That is, there will be no environment set.
        # (`environment_commands = ""` only redirects to Unified
        # if specified under the [default] task)
        "e3sm_to_cmip_environment_commands": "{env_cmd}",
        "diags_environment_commands": "{env_cmd}",
        "mpas_analysis_environment_commands": "{env_cmd}",
        "global_time_series_environment_commands": "{env_cmd}",
        "livvkit_environment_commands": "{env_cmd}",
        "pcmdi_diags_environment_commands": "{env_cmd}",
        # This is the environment setup for other tasks.
        # Leave as "" to use the latest Unified environment.
        "environment_commands": "{env_cmd}",
        # For a complete test, run the set of latest cfgs and at least one set of legacy cfgs
        "cfgs_to_run": [
            "weekly_bundles", # Typically, we run on Chrysalis, Compy
            "weekly_comprehensive_v2", # Typically, we run on Chrysalis, Compy
            "weekly_comprehensive_v3", # Typically, we run on all 3 machines
            "weekly_legacy_3.1.0_bundles", # Typically, we run on Chrysalis
            "weekly_legacy_3.1.0_comprehensive_v2", # Typically, we run on Chrysalis
            "weekly_legacy_3.1.0_comprehensive_v3", # Typically, we run on Chrysalis
            "weekly_legacy_3.0.0_bundles", # Typically, we run on Chrysalis
            "weekly_legacy_3.0.0_comprehensive_v2", # Typically, we run on Chrysalis
            "weekly_legacy_3.0.0_comprehensive_v3", # Typically, we run on Chrysalis
        ],
        "tasks_to_run": [
            "e3sm_diags",
            "mpas_analysis",
            "global_time_series",
            "ilamb",
            "livvkit",
            "pcmdi_diags",
        ],
        "unique_id": "test_zppy_yyyymmdd", # Use today's date
    }

.. code-block:: bash

    git diff # Check that the diff looks as you expect
    python tests/integration/utils.py
    # This will generate the actual test cfgs based off the templates.

    # Set up an alias for checking jobs:
    alias sqa='squeue -o "%8u %.7a %.4D %.9P %7i %.2t %.10r %.10M %.10l %.8Q %j" --sort=P,-t,-p'
    alias sq='sqa -u $USER'

    sq
    # Check that you have no jobs currently queued.
    # It's ok if you do, but it makes counting remaining zppy jobs easier if you don't have any existing jobs.

    # Typically run on Chrysalis, Compy, Perlmutter:
    zppy -c tests/integration/generated/test_weekly_comprehensive_v3_chrysalis.cfg

    # Typically run on Chrysalis, Compy:
    zppy -c tests/integration/generated/test_weekly_bundles_chrysalis.cfg
    zppy -c tests/integration/generated/test_weekly_comprehensive_v2_chrysalis.cfg

    # Typically run on Chrysalis:
    zppy -c tests/integration/generated/test_weekly_legacy_3.1.0_bundles_chrysalis.cfg
    zppy -c tests/integration/generated/test_weekly_legacy_3.1.0_comprehensive_v2_chrysalis.cfg
    zppy -c tests/integration/generated/test_weekly_legacy_3.1.0_comprehensive_v3_chrysalis.cfg
    zppy -c tests/integration/generated/test_weekly_legacy_3.0.0_bundles_chrysalis.cfg
    zppy -c tests/integration/generated/test_weekly_legacy_3.0.0_comprehensive_v2_chrysalis.cfg
    zppy -c tests/integration/generated/test_weekly_legacy_3.0.0_comprehensive_v3_chrysalis.cfg


    sq | wc -l # This includes the header row, so subtract 1 to get the number of jobs you have running
    # WAIT until that returns 1 (i.e., 0 jobs running)


Step 6: Launch zppy jobs -- bundles part 2
==========================================

This section is only relevant only if you're running the ``_bundles_`` jobs. Only run the lines relevant to the jobs you launched in step 5.

.. code-block:: bash

    # Check on bundles status
    cd ${output_dir}/zppy_weekly_bundles_output/${unique_id}/v3.LR.historical_0051/post/scripts
    grep -v "OK" *status # Confirm no non-OK statuses appear

    cd ${output_dir}/zppy_weekly_legacy_3.1.0_bundles_output/${unique_id}/v3.LR.historical_0051/post/scripts
    grep -v "OK" *status # Confirm no non-OK statuses appear

    cd ${output_dir}/zppy_weekly_legacy_3.0.0_bundles_output/${unique_id}/v3.LR.historical_0051/post/scripts
    grep -v "OK" *status # Confirm no non-OK statuses appear

    # Now, run bundles part 2
    cd ${repo_parent_dir}/zppy
    git status
    # You might have changed branches while you were waiting for jobs to finish.
    # Make sure you're now back on the correct branch: test-zppy-yyyymmdd
    # Also confirm you're back in the correct env: zppy-yyyymmdd or the Unified env


    zppy -c tests/integration/generated/test_weekly_bundles_chrysalis.cfg
    zppy -c tests/integration/generated/test_weekly_legacy_3.1.0_bundles_chrysalis.cfg
    zppy -c tests/integration/generated/test_weekly_legacy_3.0.0_bundles_chrysalis.cfg
    sq | wc -l
    # WAIT until that returns 1 (i.e., 0 jobs running)

Step 7: Review finished returns
===============================

Only run the lines relevant to the jobs you launched in steps 5/6.

.. code-block:: bash

    ### v2  ###
    cd ${output_dir}/zppy_weekly_comprehensive_v2_output/${unique_id}/v2.LR.historical_0201/post/scripts
    grep -v "OK" *status # Confirm no non-OK statuses appear

    cd ${output_dir}/zppy_weekly_legacy_3.0.0_comprehensive_v2_output/${unique_id}/v2.LR.historical_0201/post/scripts
    grep -v "OK" *status # Confirm no non-OK statuses appear

    cd ${output_dir}/zppy_weekly_legacy_3.1.0_comprehensive_v2_output/${unique_id}/v2.LR.historical_0201/post/scripts
    grep -v "OK" *status # Confirm no non-OK statuses appear

    ### v3 ###
    cd ${output_dir}/zppy_weekly_comprehensive_v3_output/${unique_id}/v3.LR.historical_0051/post/scripts
    grep -v "OK" *status # Confirm no non-OK statuses appear

    cd ${output_dir}/zppy_weekly_legacy_3.0.0_comprehensive_v3_output/${unique_id}/v3.LR.historical_0051/post/scripts
    grep -v "OK" *status # Confirm no non-OK statuses appear

    cd ${output_dir}/zppy_weekly_legacy_3.1.0_comprehensive_v3_output/${unique_id}/v3.LR.historical_0051/post/scripts
    grep -v "OK" *status # Confirm no non-OK statuses appear

    ### bundles ###
    cd ${output_dir}/zppy_weekly_bundles_output/${unique_id}/v3.LR.historical_0051/post/scripts
    grep -v "OK" *status # Confirm no non-OK statuses appear

    cd ${output_dir}/zppy_weekly_legacy_3.0.0_bundles_output/${unique_id}/v3.LR.historical_0051/post/scripts
    grep -v "OK" *status # Confirm no non-OK statuses appear

    cd ${output_dir}/zppy_weekly_legacy_3.1.0_bundles_output/${unique_id}/v3.LR.historical_0051/post/scripts
    grep -v "OK" *status # Confirm no non-OK statuses appear

In your Markdown report, any of the output subdirectories that had non-OK statuses.

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

    # This test doesn't make use of an expected results directory.
    pytest tests/integration/test_last_year.py

    # These tests do make use of an expected results directory.
    # That is, the expected results may need to be updated if expected behavior has changed.
    pytest tests/integration/test_bash_generation.py
    pytest tests/integration/test_campaign.py
    pytest tests/integration/test_defaults.py

    # These tests make use of an expected results directory
    # AND rely on the jobs we just ran:
    # 1. The bundles test:
    pytest tests/integration/test_bundles.py
    # 2. The image checker test, which we'll run from a compute node:
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
