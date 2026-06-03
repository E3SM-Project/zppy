.. _testing-zppy:

*************
Testing zppy
*************

Unit tests
==========

Unit tests live in ``tests/test_*.py``. Run them with:

.. code-block:: bash

   pip install .  # or: python -m pip install .
   pytest tests/test_*.py

Integration tests
=================

Integration tests can be run on Chrysalis, Compy, or Perlmutter. They
require an active E3SM Unified environment and access to simulation data.

Machine-specific directions (generated setup commands, expected output files,
etc.) live in:
`tests/integration/generated/ <https://github.com/E3SM-Project/zppy/tree/main/tests/integration/generated>`_

Run all integration tests:

.. code-block:: bash

   pip install .
   pytest tests/integration/test_*.py

.. note::
   Image comparison tests require a compute node:

   .. code-block:: bash

      salloc --nodes=1 --partition=debug --time=02:00:00 --account=e3sm
      pytest tests/integration/test_images.py
      cat test_images_summary.md

Automated tests (CI)
====================

Unit tests run automatically via :ref:`GitHub Actions <ci-cd>` on every
pull request and push to ``main``. Integration tests must be run manually
on a supported machine.

.. _release-testing:

Full release testing directions
================================

This section describes the complete process for testing ``zppy`` before
making a release. See also :doc:`tutorial_testing_e3sm_unified` for a legacy
tutorial.

Overview
--------

Three testing scenarios exist:

a. **test dev** — run before making a new zppy RC (no new Unified RC yet)
b. **test new Unified RC** — run when a new E3SM Unified RC has been made
c. **test final Unified** — run after E3SM Unified is finalized

Tests should be run on **three machines**: Chrysalis, Compy, and Perlmutter.

Step 1: Set up zppy-interfaces (if needed)
-------------------------------------------

Update ``zppy-interfaces`` to the latest main branch:

.. code-block:: bash

   cd ~/ez/zppy-interfaces
   git status         # should be clean
   git fetch upstream main
   git checkout main
   git reset --hard upstream/main
   git log --oneline | head -n 1
   # Verify matches https://github.com/E3SM-Project/zppy-interfaces/commits/main

   bash  # isolated subshell
   source ~/.bashrc
   source /lcrc/soft/climate/e3sm-unified/test_e3sm_unified_<VERSION>_chrysalis.sh  # e.g., 1.13.0rc10

   # Verify zppy-interfaces tests
   pytest tests/unit/global_time_series/test_*.py
   pytest tests/unit/pcmdi_diags/test_*.py

Step 2: Check out the zppy branch
-----------------------------------

.. code-block:: bash

   cd ~/ez/zppy
   git status  # ensure clean workspace

   git fetch upstream main
   git checkout -b test-zppy-<description>-<machine> upstream/main
   git log --oneline | head -n 3
   # Verify matches https://github.com/E3SM-Project/zppy/commits/main

Step 3: Set up the environment
-------------------------------

a. **test dev**: create a new dev environment

   .. code-block:: bash

      mamba clean --all
      mamba env create -f conda/dev.yml -n zppy_dev_pre_<version>rc<N>
      conda activate zppy_dev_pre_<version>rc<N>
      pip install .

b. **test new Unified RC**: activate the Unified RC

   - Chrysalis: ``source /lcrc/soft/climate/e3sm-unified/test_e3sm_unified_<VERSION>rc<N>_chrysalis.sh``
   - Compy: ``source /share/apps/E3SM/conda_envs/test_e3sm_unified_<VERSION>rc<N>_compy.sh``
   - Perlmutter: ``source /global/common/software/e3sm/anaconda_envs/test_e3sm_unified_<VERSION>rc<N>_pm-cpu.sh``

c. **test final Unified**: activate the latest released Unified

   - Chrysalis: ``source /lcrc/soft/climate/e3sm-unified/load_latest_e3sm_unified_chrysalis.sh``
   - Compy: ``source /share/apps/E3SM/conda_envs/load_latest_e3sm_unified_compy.sh``
   - Perlmutter: ``source /global/common/software/e3sm/anaconda_envs/load_latest_e3sm_unified_pm-cpu.sh``

Step 4: Configure ``tests/integration/utils.py``
--------------------------------------------------

Edit ``tests/integration/utils.py`` to set the correct environment
and unique ID. Example ``TEST_SPECIFICS`` dictionary:

.. code-block:: python

   TEST_SPECIFICS: Dict[str, Any] = {
       # NCO path: "" uses production-version NCO commands
       # Set to a specific path to use development-version NCO commands
       "nco_path": "",
       # Environment commands for specific tasks.
       # Never set these to ""; that would override the task's environment
       # with a blank string (no environment).
       "e3sm_to_cmip_environment_commands": "source /lcrc/soft/climate/e3sm-unified/test_e3sm_unified_<VERSION>rc<N>_chrysalis.sh",
       "diags_environment_commands":         "source /lcrc/soft/climate/e3sm-unified/test_e3sm_unified_<VERSION>rc<N>_chrysalis.sh",
       "mpas_analysis_environment_commands": "source /lcrc/soft/climate/e3sm-unified/test_e3sm_unified_<VERSION>rc<N>_chrysalis.sh",
       "global_time_series_environment_commands": "source /lcrc/soft/climate/e3sm-unified/test_e3sm_unified_<VERSION>rc<N>_chrysalis.sh",
       "livvkit_environment_commands":       "source /lcrc/soft/climate/e3sm-unified/test_e3sm_unified_<VERSION>rc<N>_chrysalis.sh",
       "pcmdi_diags_environment_commands":   "source /lcrc/soft/climate/e3sm-unified/test_e3sm_unified_<VERSION>rc<N>_chrysalis.sh",
       # General environment for other tasks.
       # Leave as "" to use the latest Unified environment.
       "environment_commands": "source /lcrc/soft/climate/e3sm-unified/test_e3sm_unified_<VERSION>rc<N>_chrysalis.sh",
       # For a complete test, run the set of latest cfgs AND at least one set of legacy cfgs
       "cfgs_to_run": [
           "weekly_bundles",
           "weekly_comprehensive_v2",
           "weekly_comprehensive_v3",
           "weekly_legacy_3.1.0_bundles",
           "weekly_legacy_3.1.0_comprehensive_v2",
           "weekly_legacy_3.1.0_comprehensive_v3",
           "weekly_legacy_3.0.0_bundles",
           "weekly_legacy_3.0.0_comprehensive_v2",
           "weekly_legacy_3.0.0_comprehensive_v3",
       ],
       "tasks_to_run": [
           "e3sm_diags",
           "mpas_analysis",
           "global_time_series",
           "ilamb",
           "livvkit",
           "pcmdi_diags",
       ],
       "unique_id": "zppy_<branch>_<version>rc<N>_<description>",
   }

Step 5: Run unit tests
-----------------------

.. code-block:: bash

   pytest tests/test_*.py

All tests should pass. Failures in scenario (a) require code fixes.
Failures in scenario (c) may indicate a patch release of E3SM Unified is
needed.

Step 6: Generate cfg files and check quota
-------------------------------------------

.. code-block:: bash

   python tests/integration/utils.py
   # Review output to confirm settings

   # Check quota before launching
   mmlsquota -u <username> --block-size T fs2
   lcrc-quota

   ls tests/integration/generated/test_weekly_*_chrysalis.cfg

Step 7: Launch integration jobs
--------------------------------

To ensure no conflicts, wait for all jobs from one ``zppy`` run to finish
before launching another. Start with the most important:

.. code-block:: bash

   # Launch all cfg files
   zppy -c tests/integration/generated/test_weekly_comprehensive_v3_chrysalis.cfg
   zppy -c tests/integration/generated/test_weekly_bundles_chrysalis.cfg
   zppy -c tests/integration/generated/test_weekly_comprehensive_v2_chrysalis.cfg

   zppy -c tests/integration/generated/test_weekly_legacy_3.1.0_bundles_chrysalis.cfg
   zppy -c tests/integration/generated/test_weekly_legacy_3.1.0_comprehensive_v2_chrysalis.cfg
   zppy -c tests/integration/generated/test_weekly_legacy_3.1.0_comprehensive_v3_chrysalis.cfg

   zppy -c tests/integration/generated/test_weekly_legacy_3.0.0_bundles_chrysalis.cfg
   zppy -c tests/integration/generated/test_weekly_legacy_3.0.0_comprehensive_v2_chrysalis.cfg
   zppy -c tests/integration/generated/test_weekly_legacy_3.0.0_comprehensive_v3_chrysalis.cfg

   # Monitor job queue
   sq | wc -l  # subtract 1 for the header row

Step 8: Run bundles a second time
----------------------------------

After all initial jobs complete, check for errors and run the bundles a
second time to complete remaining work:

.. code-block:: bash

   # Check for errors first
   cd /path/to/output/.../post/scripts
   grep -v "OK" *status   # Good if no output

   # Re-run bundles
   zppy -c tests/integration/generated/test_weekly_bundles_chrysalis.cfg
   zppy -c tests/integration/generated/test_weekly_legacy_3.1.0_bundles_chrysalis.cfg
   zppy -c tests/integration/generated/test_weekly_legacy_3.0.0_bundles_chrysalis.cfg

Step 9: Review all finished runs
----------------------------------

For each output directory, check for failures:

.. code-block:: bash

   cd /path/to/zppy_weekly_comprehensive_v2_output/.../post/scripts
   grep -v "OK" *status

   cd /path/to/zppy_weekly_comprehensive_v3_output/.../post/scripts
   grep -v "OK" *status

   cd /path/to/zppy_weekly_bundles_output/.../post/scripts
   grep -v "OK" *status

   # Repeat for all legacy output directories

Step 10: Run Python integration tests
---------------------------------------

.. code-block:: bash

   pytest tests/integration/test_bash_generation.py
   pytest tests/integration/test_campaign.py
   pytest tests/integration/test_defaults.py
   pytest tests/integration/test_bundles.py
   pytest tests/integration/test_last_year.py

For image comparison tests (requires a compute node):

.. code-block:: bash

   salloc --nodes=1 --partition=debug --time=02:00:00 --account=e3sm
   bash
   source ~/.bashrc
   source /lcrc/soft/climate/e3sm-unified/test_e3sm_unified_<VERSION>_chrysalis.sh
   pytest tests/integration/test_images.py
   cat test_images_summary.md

Step 11: Wrap up
-----------------

After successful testing:

a. **test dev**: proceed to :ref:`create the zppy RC <release-candidates>`.

b. **test new Unified RC**: proceed to create the zppy production release.

c. **test final Unified**: run the "Commands to generate official expected
   results for a release" from the machine-specific directions. Then clean
   up branches and environments:

   .. code-block:: bash

      git branch
      git branch -D <branch-to-delete>

      conda env list
      conda remove -n <env-name> --all

   Update expected test result files if there are known/expected differences:
   use the "Commands to run to replace outdated expected files" from the
   machine-specific directions, then re-run the tests.

Step 12: Record test results
------------------------------

Document test results in the `zppy testing discussion
<https://github.com/E3SM-Project/zppy/discussions>`_ for the relevant
E3SM Unified release. Include:

- Machine name and date
- E3SM Unified version tested
- zppy version/branch tested
- Results summary (pass/fail per cfg)
- Any known issues or caveats
