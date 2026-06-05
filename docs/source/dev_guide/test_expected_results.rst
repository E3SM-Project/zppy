.. _updating-expected-results:

***************************************
Updating expected results for the tests
***************************************


Machine-specific setup
~~~~~~~~~~~~~~~~~~~~~~

Chrysalis:

.. code-block:: bash

    machine_name=chrysalis
    repo_parent_dir=~/ez/ # Or wherever you keep your repos
    expected_results_dir=/lcrc/group/e3sm/public_html/zppy_test_resources
    expected_results_records_dir=/lcrc/group/e3sm/public_html/zppy_test_resources_previous

    launch_compute_node()    
    {
        salloc --nodes=1 --partition=debug --time=02:00:00 --account=e3sm
    }

Compy:

.. code-block:: bash

    machine_name=compy
    repo_parent_dir=~/ez/ # Or wherever you keep your repos
    expected_results_dir=/compyfs/www/zppy_test_resources
    expected_results_records_dir=/compyfs/fors729/zppy_test_resources_previous

    launch_compute_node()    
    {
        salloc --nodes=1 --partition=short --time=01:00:00 --account=e3sm
    }

Note that Compy doesn't give write access to ``/compyfs/www/``, so we can't add a new directory there. That's why ``zppy_test_resources_previous`` is in a separate path.

Perlmutter:

.. code-block:: bash

    machine_name=pm-cpu
    repo_parent_dir=~/ez/ # Or wherever you keep your repos
    expected_results_dir=/global/cfs/cdirs/e3sm/www/zppy_test_resources
    expected_results_records_dir=/global/cfs/cdirs/e3sm/www/zppy_test_resources_previous

    launch_compute_node()    
    {
        salloc --nodes=1 --qos=interactive --time=01:00:00 --constraint=cpu --account=e3sm
    }


Process
~~~~~~~

.. code-block:: bash

    # First, let's copy over the old expected results #############################
    cp -r ${expected_results_dir} ${expected_results_records_dir}/expected_results_until_yyyymmdd 
    # Use today's date
    # Chrysalis -- takes between 20 and 60 minutes

    # Second, update the expected results #########################################
    # Let's update the simpler tests' results first:
    cd ${repo_parent_dir}/zppy
    git status
    # You might have changed branches since you ran the tests.
    # Make sure you're now back on the correct branch: test-zppy-yyyymmdd
    # Also confirm you're back in the correct env: zppy-yyyymmdd or the Unified env

    # Make sure the update script permissions are set up
    chmod 755 tests/integration/generated/update_bash_generation_expected_files_${machine_name}.sh
    chmod 755 tests/integration/generated/update_campaign_expected_files_${machine_name}.sh
    chmod 755 tests/integration/generated/update_defaults_expected_files_${machine_name}.sh
    chmod 755 tests/integration/generated/update_weekly_expected_files_${machine_name}.sh

    # These scripts update the expected results and re-run the tests:
    ./tests/integration/generated/update_bash_generation_expected_files_${machine_name}.sh
    ./tests/integration/generated/update_campaign_expected_files_${machine_name}.sh
    ./tests/integration/generated/update_defaults_expected_files_${machine_name}.sh

    # Theis script only updates the expected results
    ./tests/integration/generated/update_weekly_expected_files_${machine_name}.sh
    # Chrysalis -- takes about 40 minutes
    # Perlmutter -- takes about 25 minutes
    ls ${expected_results_dir}
    # Confirm there are expected results subdirs and image lists for each cfg

    cd ${repo_parent_dir}/zppy
    pytest tests/integration/test_bundles.py
    launch_compute_node

    start_bash_subshell
    # EITHER:
    # Activate EITHER a dev environment or the Unified env:
    conda activate zppy-yyyymmdd
    # OR: the command from `activate_unified_env`

    pytest tests/integration/test_images.py
    exit # Exit bash shell
    exit # Exit compute note

Only do this part if you're updating the Official Results (i.e., the results we'd expect from a specific ``zppy`` version):

.. code-block:: bash

    alias this_release=unified_1.13.0 # Or whatever the release is

    # Third, let's copy the expected results into a special official results dir ##
    cp -r ${expected_results_dir} ${expected_results_records_dir}/expected_results_for_${this_release}
    # Compy -- takes about 1h20m
    ls ${expected_results_records_dir}/expected_results_for_${this_release}
    # Confirm there are expected results subdirs and image lists for each cfg
