.. _testing_e3sm_unified:

*************************************
Testing zppy for E3SM Unified release
*************************************

This tutorial covers testing ``zppy`` for an E3SM Unified release.
Examples are from testing for E3SM Unified v1.5.0.

Parameters
==========

Only a few parameters in the configuration file need to change for different machines.
Be sure to change the file paths to fit your own workspaces.

.. warning::

    Also consider the space quotas or purge policies for the file paths you use.
    You'll be storing about 2 TB of data.

Chrysalis:

- <INPUT>: /lcrc/group/e3sm/ac.forsyth2/E3SM_simulations/e3sm_unified_test_simulation/20210528.v2rc3e.piControl.ne30pg2_EC30to60E2r2.chrysalis
- <OUTPUT>: /lcrc/group/e3sm/ac.forsyth2/E3SM_simulations/e3sm_unified_test_simulation/
- <WWW>: /lcrc/group/e3sm/public_html/diagnostic_output/ac.forsyth2/E3SM/e3sm_unified_test_simulation/
- <PARTITION>: compute
- <ENVIRONMENT_COMMANDS>: source /lcrc/soft/climate/e3sm-unified/test_e3sm_unified_1.5.0rc8_chrysalis.sh
- <MAPPING_FILE>: /home/ac.zender/data/maps/map_ne30pg2_to_cmip6_180x360_aave.20200201.nc
- <REFERENCE_DATA_PATH>: /lcrc/soft/climate/e3sm_diags_data/obs_for_e3sm_diags/climatology
- <OBS_TS>: /lcrc/soft/climate/e3sm_diags_data/obs_for_e3sm_diags/time-series
- <DC_OBS_CLIMO>: /lcrc/group/e3sm/public_html/e3sm_diags_test_data/unit_test_complete_run/obs/climatology

Compy:

- <INPUT>: /compyfs/fors729/e3sm_unified_test_zppy/20210528.v2rc3e.piControl.ne30pg2_EC30to60E2r2.chrysalis
- <OUTPUT>: /compyfs/fors729/e3sm_unified_test_zppy/
- <WWW>: /compyfs/www/fors729/E3SM/e3sm_unified_test_simulation/
- <PARTITION>: slurm
- <ENVIRONMENT_COMMANDS>: source /share/apps/E3SM/conda_envs/test_e3sm_unified_1.5.0rc8_compy.sh
- <MAPPING_FILE>: /compyfs/zender/maps/map_ne30pg2_to_cmip6_180x360_aave.20200201.nc
- <REFERENCE_DATA_PATH>: /compyfs/e3sm_diags_data/obs_for_e3sm_diags/climatology
- <OBS_TS>: /compyfs/e3sm_diags_data/obs_for_e3sm_diags/time-series
- <DC_OBS_CLIMO>: /compyfs/e3sm_diags_data/obs_for_e3sm_diags/climatology

Cori:

- <INPUT>: /global/cscratch1/sd/forsyth/e3sm_unified_test_zppy/20210528.v2rc3e.piControl.ne30pg2_EC30to60E2r2.chrysalis
- <OUTPUT>: /global/cscratch1/sd/forsyth/e3sm_unified_test_zppy/
- <WWW>: /global/cfs/cdirs/e3sm/www/forsyth/E3SM/e3sm_unified_test_simulation/
- <PARTITION>: haswell
- <ENVIRONMENT_COMMANDS>: source /global/common/software/e3sm/anaconda_envs/test_e3sm_unified_1.5.0rc8_cori-haswell.sh
- <MAPPING_FILE>: /global/homes/z/zender/data/maps/map_ne30pg2_to_cmip6_180x360_aave.20200201.nc
- <REFERENCE_DATA_PATH>: /global/cfs/cdirs/e3sm/acme_diags/obs_for_e3sm_diags/climatology
- <OBS_TS>: /global/cfs/cdirs/e3sm/acme_diags/obs_for_e3sm_diags/time-series
- <DC_OBS_CLIMO>: /global/cfs/cdirs/e3sm/acme_diags/obs_for_e3sm_diags/climatology

These values don't appear in the configuration file but are still useful to specify
here:

Chrysalis:

- <HTML>: https://web.lcrc.anl.gov/public/e3sm/diagnostic_output/ac.forsyth2/E3SM/e3sm_unified_test_simulation/20210528.v2rc3e.piControl.ne30pg2_EC30to60E2r2.chrysalis/
- <ZSTASH_OUTPUT_DIR>: /lcrc/group/e3sm/ac.forsyth2/zstash_dir
- <ZSTASH_CACHE_DIR>: /lcrc/group/e3sm/ac.forsyth2/e3sm_unified_test_zstash/unified_test_cache

Compy:

- <HTML>: https://compy-dtn.pnl.gov/fors729/E3SM/e3sm_unified_test_simulation/20210528.v2rc3e.piControl.ne30pg2_EC30to60E2r2.chrysalis/
- <ZSTASH_OUTPUT_DIR>: /compyfs/fors729/e3sm_unified_test_zstash
- <ZSTASH_CACHE_DIR>: /compyfs/fors729/e3sm_unified_test_zstash/unified_test_cache

Cori:

- <HTML>: http://portal.nersc.gov/cfs/e3sm/forsyth/E3SM/e3sm_unified_test_simulation/20210528.v2rc3e.piControl.ne30pg2_EC30to60E2r2.chrysalis/
- <ZSTASH_OUTPUT_DIR>: /global/cscratch1/sd/forsyth/e3sm_unified_test_zstash
- <ZSTASH_CACHE_DIR>: /global/cscratch1/sd/forsyth/e3sm_unified_test_zstash/unified_test_cache

Testing zppy on a small simulation
==================================

1. Find a simulation to test on. In this example, we'll use a simulation on Chrysalis:
``/lcrc/group/e3sm/ac.golaz/E3SM_simulations/20210528.v2rc3e.piControl.ne30pg2_EC30to60E2r2.chrysalis/``.

2. The simulation might be too large to reasonably test on. We can copy over a
subsection to a testing directory with a script like the following. In this example,
the simulation data starts at year 51. We want to have at least 20 years, so we'll
copy over years 51-79 using the pattern ``*.00[5-7]*``. This subsection turns out to be
about 2 terabytes in size.

    ::

        #!/bin/bash

        input=/lcrc/group/e3sm/ac.golaz/E3SM_simulations/20210528.v2rc3e.piControl.ne30pg2_EC30to60E2r2.chrysalis/
        output=e3sm_unified_test_simulation/20210528.v2rc3e.piControl.ne30pg2_EC30to60E2r2.chrysalis/

        # For E3SM Diags: About 40 minutes to run
        # Copy over years xx5x - xx7x
        cp ${input}archive/atm/hist/*.00[5-7]* ${output}archive/atm/hist
        cp ${input}archive/cpl/hist/*.00[5-7]* ${output}archive/cpl/hist
        cp ${input}archive/ice/hist/*.00[5-7]* ${output}archive/ice/hist
        cp ${input}archive/lnd/hist/*.00[5-7]* ${output}archive/lnd/hist
        cp ${input}archive/ocn/hist/*.00[5-7]* ${output}archive/ocn/hist
        cp ${input}archive/rof/hist/*.00[5-7]* ${output}archive/rof/hist

        # For MPAS-Analysis: Less than a minute to run
        cp ${input}run/mpaso_in ${output}run/mpaso_in
        cp ${input}run/mpassi_in ${output}run/mpassi_in
        cp ${input}run/streams.ocean ${output}run/streams.ocean
        cp ${input}run/streams.seaice ${output}run/streams.seaice
        cp ${input}run/*rst* ${output}run/


3. Now we need to load ``zppy``. We first want to test out ``zppy`` from
the new unified environment release candidate.
We can do this by running ``<ENVIRONMENT_COMMANDS>``.
See 3a-c below if errors are encountered in later steps.

3a. If ``zppy`` has problems in later steps,
we'll have to make changes in the ``zppy`` code and
create a new release candidate; until the new ``zppy`` release candidate is included in the
new unified environment release candidate,
we'll have to just use the ``zppy`` development environment.
This will require running ``pip install .`` in that environment from the top level of
the repo.

3b. It may be the case that the configuration file had an error and thus neither
``zppy`` nor any package that ``zppy`` runs actually failed. In that case, fix the
configuration file.

3c. Keep in mind if you run ``zppy -c`` multiple times, it will only rerun tasks that
have failed. This may or may not be what we want. For example, if we change the
environment we're using, we probably want to rerun everything using the new environment.

4. Create a configuration file ``e3sm_unified_test_simulation.cfg``.

.. literalinclude:: testing_e3sm_unified.cfg
   :language: cfg
   :linenos:

5. We can now test out ``zppy`` by running ``zppy -c e3sm_unified_test_simulation.cfg``.
If that command fails, return to step 3.

6. If the above command completes successfully, run:
    ::

        # cd into output directory
        cd <OUTPUT>/post/scripts
        # Check status of files that either failed or are still running.
        grep -v "OK" *status
        # If there is an error, return to step 3.
        # If you want to remove all output run the following two steps:
        rm -rf <OUTPUT>/post
        rm -rf <WWW>/20210528.v2rc3e.piControl.ne30pg2_EC30to60E2r2.chrysalis

7. Output can be viewed at the web link corresponding to ``<WWW>`` in the configuration
file (i.e., ``<HTML>`` defined in "Parameters" above).

Archive simulation using zstash
===============================

1. Create a batch script ``zstash_create.bash`` to run ``zstash``.
    ::

        #!/bin/bash

        #SBATCH  --job-name=zstash_create
        #SBATCH  --nodes=1
        #SBATCH  --output=<ZSTASH_OUTPUT_DIR>/zstash_create.o%j
        #SBATCH  --exclusive
        #SBATCH  --time=04:00:00

        <ENVIRONMENT_COMMANDS>
        zstash create --hpss=none --cache=<ZSTASH_CACHE_DIR> <OUTPUT>/20210528.v2rc3e.piControl.ne30pg2_EC30to60E2r2.chrysalis

2. Run with ``sbatch zstash_create.bash``. This example takes about 2.5 hours to run.

Transfer simulation to other machines
=====================================
We can follow an adapted version of the steps at
https://e3sm-project.github.io/zstash/_build/html/master/best_practices.html#transfer-to-nersc-hpss
to transfer the data.

Login to Globus: https://www.globus.org/ (using NERSC credentials)

Transfer to Cori
----------------

1. On the left sidebar, choose "ENDPOINTS".

2. Search for "NERSC DTN". Click on Green power button to activate endpoint.

3. On the left sidebar, choose "ENDPOINTS".

4. Search for "lcrc#dtn_bebop". Click on Green power button to activate endpoint.
Log in using LCRC credentials.

5. Paste the path to the ``zstash`` archive (``<ZSTASH_CACHE_DIR>`` for Chrysalis)
in the "Path" box.

6. Click "Transfer or Sync to..." on the right side. The screen will now be split.

7. On the left side, choose "Select all"

8. On the right side, put "NERSC DTN" for collection.

9. Paste the NERSC path you want the archive copied to
(``<ZSTASH_CACHE_DIR>`` for Cori). This path needs to already exist.

10. Click "Transfer & Sync Options" in the center.

11. Choose "sync - only transfer new or changed files"
(choose "modification time is newer" in the dropdown box),
"preserve source file modification times", and "verify file integrity after transfer".

12. For "Label This Transfer", put something like "zstash archive LCRC to NERSC".

13. On the left side, click "Start >". This will start the transfer from LCRC to NERSC.

Transfer to Compy
-----------------

1. On the left sidebar, choose "ENDPOINTS".

2. Search for "pic#compy-dtn". Click on Green power button to activate endpoint.
Log in using Compy credentials.

3. On the left sidebar, choose "File Manager." The screen will now be split.

4. On the left side, put "lcrc#dtn_bebop" for "Collection".

5. On the left side, paste the path to the ``zstash`` archive
(``<ZSTASH_CACHE_DIR>`` for Chrysalis) in the "Path" box.

6. On the left side, choose "Select all".

7. On the right side, put "pic#compy-dtn" for "Collection".

8. Paste the Compy path you want the archive copied to
(``<ZSTASH_CACHE_DIR>`` for Compy).
This path needs to already exist.

9. Click "Transfer & Sync Options" in the center.

10. Choose "sync - only transfer new or changed files"
(choose "modification time is newer" in the dropdown box),
"preserve source file modification times", and "verify file integrity after transfer".

11. For "Label This Transfer", put something like "zstash archive LCRC to Compy".

12. On the left side, click "Start >". This will start the transfer from LCRC to Compy.

Check transfers were successful
===============================

Cori
----
1. Create a batch script ``zstash_check.bash``: ::

    #!/bin/bash
    #SBATCH  --job-name=zstash_check
    #SBATCH  --nodes=1
    #SBATCH  --output=<ZSTASH_OUTPUT_DIR>/zstash_check.o%j
    #SBATCH  --exclusive
    #SBATCH  --time=3:00:00
    #SBATCH  -q regular
    #SBATCH  --constraint=haswell

    <ENVIRONMENT_COMMANDS>
    zstash check --hpss=none --cache=<ZSTASH_CACHE_DIR>

2. Run ``sbatch zstash_check.bash``. This takes about an hour to run.

Compy
-----

1. Create a batch script ``zstash_check.bash``: ::

    #!/bin/bash
    #SBATCH  --job-name=zstash_check
    #SBATCH  --nodes=1
    #SBATCH  --output=<ZSTASH_OUTPUT_DIR>/zstash_check.o%j
    #SBATCH  --exclusive
    #SBATCH  --time=3:00:00

    <ENVIRONMENT_COMMANDS>
    zstash check --hpss=none --cache=<ZSTASH_CACHE_DIR>

2. Run ``sbatch zstash_check.bash``. This takes over 3 hours to run.

Extract the data from the archives
==================================

Use ``zstash extract``.

Cori
----

1. ``mkdir unified_test_extraction``.

2. Create a batch script ``zstash_extract.bash``: ::

    #!/bin/bash
    #SBATCH  --job-name=zstash_extract
    #SBATCH  --nodes=1
    #SBATCH  --output=<ZSTASH_OUTPUT_DIR>/zstash_extract.o%j
    #SBATCH  --exclusive
    #SBATCH  --time=4:00:00
    #SBATCH  -q regular
    #SBATCH  --constraint=haswell

    <ENVIRONMENT_COMMANDS>
    cd unified_test_extraction
    zstash extract --hpss=none --cache=<ZSTASH_CACHE_DIR>

3. Run ``sbatch zstash_extract.bash``.

Compy
-----

1. ``mkdir unified_test_extraction``.

2. Create a batch script ``zstash_extract.bash``: ::

    #!/bin/bash
    #SBATCH  --job-name=zstash_extract
    #SBATCH  --nodes=1
    #SBATCH  --output=<ZSTASH_OUTPUT_DIR>/zstash_extract.o%j
    #SBATCH  --exclusive
    #SBATCH  --time=6:00:00

    <ENVIRONMENT_COMMANDS>
    cd unified_test_extraction
    zstash extract --hpss=none --cache=<ZSTASH_CACHE_DIR>

3. Run ``sbatch zstash_extract.bash``.


Testing zppy on other machines
==============================

``mv e3sm_unified_test_zstash/unified_test_extraction e3sm_unified_test_zppy/20210528.v2rc3e.piControl.ne30pg2_EC30to60E2r2.chrysalis``.

Go through steps 3-7 of "Testing zppy on a small simulation" but for
Cori (haswell) and Compy.

Sample configuration files for Compy and Cori
---------------------------------------------

``<OUTPUT>/e3sm_unified_test_simulation.cfg``:
Use the configuration file from "Testing zppy on a small simulation" step 4, updating
the appropriate parameters for Compy or Cori.

Run unit tests and integration tests
====================================

Run the unit tests and integration tests on Chrysalis:

``cd`` into your clone of the ``zppy`` repo. Then: ::

    git checkout main # if not already on the `main` branch
    git fetch upstream
    git rebase upstream/main
    <ENVIRONMENT_COMMANDS> # Load the appropriate environment
    python -u -m unittest tests/test_*.py # Run unit tests
    python -u -m unittest tests/integration/test_*.py # Run integration tests
