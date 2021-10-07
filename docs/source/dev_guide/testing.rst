************
Testing zppy
************

Unit tests
==========

Run all unit tests by doing the following:

    .. code::

        pip install . # Install your changes (`python -m pip install .` also works)
        python -m unittest tests/test_*.py # Run all unit tests

Integration tests
=================

Integration tests must be run on an LCRC machine. Run all integration tests by doing the following:

    .. code::

        pip install . # Install your changes (`python -m pip install .` also works)
        python -m unittest tests/integration/test_*.py # Run all integration tests

Commands to run before running integration tests
------------------------------------------------

Before running ``tests/integration/test_complete_run.py`` run the following:

    .. code::

       # You'll need to set some paths to your own directories:
       # 1) Edit the paths below
       # 2) Edit `output` and `www` parameters in `tests/integration/test_complete_run.cfg`
       # 3) Edit `actual_images_dir` in `tests/integration/test_complete_run.py`
       rm -rf /lcrc/group/e3sm/public_html/diagnostic_output/ac.forsyth2/zppy_test_complete_run_www/20210122.v2_test01.piControl.ne30pg2_EC30to60E2r2-1900_ICG.chrysalis
       rm -rf /lcrc/group/e3sm/ac.forsyth2/zppy_test_complete_run_output/20210122.v2_test01.piControl.ne30pg2_EC30to60E2r2-1900_ICG.chrysalis/post
       zppy -c tests/integration/test_complete_run.cfg

Before running ``tests/integration/test_environment_commands.py`` run the following:

    .. code::

       # You'll need to set some paths to your own directories:
       # 1) Edit the paths below
       # 2) Edit `output`, `www`, and `environment_commands` parameters in `tests/integration/test_environment_commands.cfg`
       # 3) Edit `actual_images_dir` in `tests/integration/test_environment_commands.py`
       rm -rf /lcrc/group/e3sm/public_html/diagnostic_output/ac.forsyth2/zppy_test_environment_commands_www/20210122.v2_test01.piControl.ne30pg2_EC30to60E2r2-1900_ICG.chrysalis
       rm -rf /lcrc/group/e3sm/ac.forsyth2/zppy_test_environment_commands_output/20210122.v2_test01.piControl.ne30pg2_EC30to60E2r2-1900_ICG.chrysalis/post
       zppy -c tests/integration/test_environment_commands.cfg

Commands to run to replace outdated expected files
--------------------------------------------------
       
To replace the expected bash files for ``test_bash_generation.py`` run the following:

    .. code::

       rm -rf /lcrc/group/e3sm/public_html/zppy_test_resources/expected_bash_files
       cd <top level of zppy repo>
       # Your output will now become the new expectation.
       # You can just move (i.e., not copy) the output since re-running this test will re-generate the output.
       mv test_bash_generation_output/post/scripts /lcrc/group/e3sm/public_html/zppy_test_resources/expected_bash_files
       # Rerun test
       python -m unittest tests/integration/test_bash_generation.py       

To replace the expected files for ``test_campaign.py`` run the following:

    .. code::

       rm -rf /lcrc/group/e3sm/public_html/zppy_test_resources/test_campaign_none_expected_files 
       rm -rf /lcrc/group/e3sm/public_html/zppy_test_resources/test_campaign_water_cycle_expected_files
       rm -rf /lcrc/group/e3sm/public_html/zppy_test_resources/test_campaign_water_cycle_override_expected_files
       mkdir -p /lcrc/group/e3sm/public_html/zppy_test_resources/test_campaign_none_expected_files
       mkdir -p /lcrc/group/e3sm/public_html/zppy_test_resources/test_campaign_water_cycle_expected_files
       mkdir -p /lcrc/group/e3sm/public_html/zppy_test_resources/test_campaign_water_cycle_override_expected_files
       cd <top level of zppy repo>
       # Your output will now become the new expectation.
       # You can just move (i.e., not copy) the output since re-running this test will re-generate the output.
       mv test_campaign_none_output/post/scripts /lcrc/group/e3sm/public_html/zppy_test_resources/test_campaign_none_expected_files 
       mv test_campaign_water_cycle_output/post/scripts /lcrc/group/e3sm/public_html/zppy_test_resources/test_campaign_water_cycle_expected_files
       mv test_campaign_water_cycle_override_output/post/scripts /lcrc/group/e3sm/public_html/zppy_test_resources/test_campaign_water_cycle_override_expected_files
       # Rerun test
       python -m unittest tests/integration/test_campaign.py       

       
To replace the expected images for ``test_complete_run.py`` run the following:

    .. code::

       rm -rf /lcrc/group/e3sm/public_html/zppy_test_resources/expected_complete_run
       # Your output will now become the new expectation.
       # Copy output so you don't have to rerun zppy to generate the output.
       cp -r /lcrc/group/e3sm/public_html/diagnostic_output/ac.forsyth2/zppy_test_complete_run_www/20210122.v2_test01.piControl.ne30pg2_EC30to60E2r2-1900_ICG.chrysalis /lcrc/group/e3sm/public_html/zppy_test_resources/expected_complete_run
       cd /lcrc/group/e3sm/public_html/zppy_test_resources/expected_complete_run
       # This file will list all the expected images.
       find . -type f -name '*.png' > ../image_list_expected_complete_run.txt
       cd <top level of zppy repo>
       # Rerun test
       python -m unittest tests/integration/test_complete_run.py

To replace the expected images for ``test_environment_commands.py`` run the following:

    .. code::

       rm -rf /lcrc/group/e3sm/public_html/zppy_test_resources/expected_environment_commands
       # Your output will now become the new expectation.
       # Copy output so you don't have to rerun zppy to generate the output.
       cp -r /lcrc/group/e3sm/public_html/diagnostic_output/ac.forsyth2/zppy_test_environment_commands_www/20210122.v2_test01.piControl.ne30pg2_EC30to60E2r2-1900_ICG.chrysalis /lcrc/group/e3sm/public_html/zppy_test_resources/expected_environment_commands
       cd /lcrc/group/e3sm/public_html/zppy_test_resources/expected_environment_commands
       # This file will list all the expected images.
       find . -type f -name '*.png' > ../image_list_expected_environment_commands.txt
       cd <top level of zppy repo>
       # Rerun test
       python -m unittest tests/integration/test_environment_commands.py
       
Automated tests
===============

We have a :ref:`GitHub Actions <ci-cd>` Continuous Integration / Continuous Delivery (CI/CD) workflow.

The unit tests are run automatically as part of this. As mentioned earlier,
integration tests must be run on an LCRC machine.

