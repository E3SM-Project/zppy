***************************************
Testing directions for making a release
***************************************

1. Have three shells open: one on Chrysalis, one on Compy, and one on Perlmutter. Do the following steps on each machine.

2. ``cd`` to the ``zppy`` directory.
   
3. Check out a branch to test on.

    a. test dev (run before making a new zppy RC) ::

        git fetch upstream main
        git checkout -b test_zppy_pre_#.#.#rc#_<machine_name> upstream/main
        git log # check the commits match https://github.com/E3SM-Project/zppy/commits/main
   
    b. test new Unified RC ::

        git fetch upstream main
        git checkout -b test_unified_#.#.#rc#_<machine_name> upstream/main
        git log # check the commits match https://github.com/E3SM-Project/zppy/commits/main

    c. test final Unified ::

        git fetch upstream main
        git checkout -b test_unified_#.#.#rc#_<machine_name> upstream/main
        git log # check the commits match https://github.com/E3SM-Project/zppy/commits/main

4. Set up a dev environment for E3SM Diags. This is used for the ``diags_environment_commands`` parameter. Normally, this is only used for checking ``environment_commands`` works properly. However, by modifying the test templates, it's possible to run other E3SM Diags subtasks in a different environment. This can be useful if a bug fix in E3SM Diags hasn't been incorporated into the latest Unified RC yet. ::

     # `cd` to e3sm_diags directory
     $ git checkout main
     $ git fetch upstream
     $ git reset --hard upstream/main
     $ git log # Should match https://github.com/E3SM-Project/e3sm_diags/commits/main
     $ mamba clean --all
     $ mamba env create -f conda-env/dev.yml -n e3sm_diags_<date>
     $ conda activate e3sm_diags_<date>
     $ pip install .
     $ `cd` back to zppy directory

5. Make sure you're using the latest packages. In ``tests/integration/utils.py``, do the following:

    a. test dev (run before making a new zppy RC):

        * If it's the first zppy RC (i.e., a Unified RC hasn't been made yet): Change the last line ``generate_cfgs()`` to ``generate_cfgs(unified_testing=False)``. We want to use the latest officially released E3SM Unified environment.
	* Otherwise: follow the (b: test new Unified RC) directions for this step.


    b. test new Unified RC

        * Change the last line ``generate_cfgs()`` to ``generate_cfgs(unified_testing=True)``. We **don't** want to use the latest officially released E3SM Unified environment.
	* Update ``environment_commands_test`` for the machine you're currently working on. If this is not done, then ``zppy`` will use the existing value, which is likely an old E3SM Unified RC launch script that doesn't even exist anymore. This parameter should be set to source the latest E3SM Unified RC launch script, since E3SM Unified is the only environment that all ``zppy`` tasks can run from. For instance, ``ncclimo`` isn't in the ``zppy`` dev environment.


    c. test final Unified

        * Change the last line ``generate_cfgs()`` to ``generate_cfgs(unified_testing=False)``. We want to use the latest officially released E3SM Unified environment.

    For a, b, and c, always:

    * Update ``diags_environment_commands`` for the machine you're currently working on to use the environment created in the above step. If this is not done, the ``atm_monthly_180x360_aave_environment_commands`` subtask will use an older dev environment for E3SM Diags than we want.
    * Update ``UNIQUE_ID`` to be a short description of what you're testing.

6. Set up your environment.

    a. test dev (run before making a new zppy RC): Set up a new development environment. This ensures that testing will use the latest conda changes. Note that you will need to run ``conda remove -n zppy_dev_pre_zppy_#.#.#rc# --all`` first if you have previously done this step. ::

        mamba clean --all
        mamba env create -f conda/dev.yml -n zppy_dev_pre_#.#.#rc#
        conda activate zppy_dev_pre_#.#.#rc#
        pip install .

    b. test new Unified RC: Launch the E3SM Unified environment for the machine you're on. Change out the version numbers below.

        * Chrysalis: ``source /lcrc/soft/climate/e3sm-unified/test_e3sm_unified_#.#.#rc#_chrysalis.sh``
        * Compy: ``source /share/apps/E3SM/conda_envs/test_e3sm_unified_#.#.#rc#_compy.sh``
        * Perlmutter: ``source /global/common/software/e3sm/anaconda_envs/test_e3sm_unified_#.#.#rc#_pm-cpu.sh``

    c. test final Unified: Launch the latest E3SM Unified environment for the machine you're on.

        * Chrysalis: ``source /lcrc/soft/climate/e3sm-unified/load_latest_e3sm_unified_chrysalis.sh``
        * Compy: ``source /share/apps/E3SM/conda_envs/load_latest_e3sm_unified_compy.sh``
        * Perlmutter: ``source /global/common/software/e3sm/anaconda_envs/load_latest_e3sm_unified_pm-cpu.sh``

7. Run the unit tests with ``pytest tests/test_*.py``.

    a. test dev (run before making a new zppy RC):

        * If there are any failures, fix the code (or tests). If you make any conda changes, go back to step 6a. If you otherwise change zppy source code, run ``pip install .`` and then redo step 7. If you only make changes to tests, you can immediately redo step 7.

    b. test new Unified RC:

        * If there are any failures, fix the code and go back to step 1, following the (a: test dev (run before making a new zppy RC)) directions. 

    c. test final Unified:

        * There should be no failures. If there are, a patch release of E3SM Unified may be required.

    For a, b, and c:

        * If there are no failures, proceed to the next step.
     
8. Run the "Commands to run before running integration tests" for the current machine. To ensure you don't encounter issues from running ``zppy`` commands simultaneously, wait for all the automatically launched jobs from one run to finish before running ``zppy`` again.

    * `Chrysalis <https://github.com/E3SM-Project/zppy/blob/main/tests/integration/generated/directions_chrysalis.md>`_
    * `Compy <https://github.com/E3SM-Project/zppy/blob/main/tests/integration/generated/directions_compy.md>`_
    * `Perlmutter <https://github.com/E3SM-Project/zppy/blob/main/tests/integration/generated/directions_pm-cpu.md>`_

9. Run the integration tests with ``pytest tests/integration/test_*.py``. Note that ``test_complete_run.py`` takes approximately 75 minutes to run on Compy.

    a. test dev (run before making a new zppy RC):

        * If there are any unexpected failures, fix the code (or tests). If you make any conda changes, go back to step 6a. If you otherwise change zppy source code, run ``pip install .`` and then go back to step 7. If you only make changes to tests, you can immediately redo step 9.

    b. test new Unified RC:

        * If there are any unexpected failures, fix the code and go back to step 1, following the (a: test dev (run before making a new zppy RC)) directions.

    c. test final Unified:

        * There should be no unexpected failures. If there are, a patch release of E3SM Unified may be required.
   
    For a, b, and c:

    * If there are only expected failures, then update the expected files. Use the "Commands to run to replace outdated expected files" from the links on step 8. Then repeat step 9.
    * If there are no failures at all, proceed to the next step.

10. Run ``git diff``. All of your changes should be from editing ``tests/integration/utils.py`` in step 5, and running it in step 8.

    * If this is the case, you can delete this testing branch.
    * If not, you have probably made code changes to get the tests to pass. Make a pull request to merge the changes. Add the "semver: bug" label.

11. Wrap up release testing:

    a. test dev (run before making a new zppy RC): Create the next zppy RC by following the "release candidates" directions at https://e3sm-project.github.io/zppy/_build/html/main/dev_guide/release.html.

    b. test new Unified RC: Create the next zppy release following the "production releases" directions at https://e3sm-project.github.io/zppy/_build/html/main/dev_guide/release.html.

    c. test final Unified: Run the "Commands to generate official expected results for a release" from step 8. This will create a baseline of expected files for the release. You can now safely remove old branches and environments. At https://github.com/E3SM-Project/zppy/branches, delete any branches that are no longer needed. Also, run: ::

        # Branches
        $ cd <zppy directory>
        $ git branch # Look at all branch names
        $ git branch -D <list branches you want to delete>

        # Environments
        $ conda env list
        # For each environment you want to delete, run:
        $ conda remove -n <environment_name> --all
