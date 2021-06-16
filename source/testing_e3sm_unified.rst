.. _testing_e3sm_unified:

*************************************
Testing zppy for E3SM Unified release
*************************************

This tutorial covers testing ``zppy`` for an E3SM Unified release.
Examples are from testing for E3SM Unified v1.5.0.

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
the new unified environment. On Chrysalis, we can load that environment using
``source /lcrc/soft/climate/e3sm-unified/test_e3sm_unified_1.5.0rc5_chrysalis.sh``.
For Cori this is
``source /global/common/software/e3sm/anaconda_envs/test_e3sm_unified_1.5.0rc5_cori-haswell.sh``
or
``source /global/common/software/e3sm/anaconda_envs/test_e3sm_unified_1.5.0rc5_cori-knl.sh``.
For Compy this is
``source /share/apps/E3SM/conda_envs/test_e3sm_unified_1.5.0rc5_compy.sh``.
See 3a-d below if errors are encountered in later steps.

3a. If ``zppy`` has problems in later steps,
we'll have to make changes in the ``zppy`` code and
create a new release candidate; until the new release candidate is included in the
new unified environment, we'll have to just use the ``zppy`` development environment.

3b. We may need to set ``environment_commands`` to source the no-mpi version of the
E3SM Unified environment if we encounter MPI failures in later steps.

3c. It may be the case that the configuration file had an error and thus neither
``zppy`` nor any package that ``zppy`` runs actually failed.

3d. Keep in mind if you run ``zppy -c`` multiple times, it will only rerun tasks that
have failed. This may or may not be what we want. For example, if we change the
environment we're using, we probably want to rerun everything using the new one.

4. Create a configuration file ``e3sm_unified_test_simulation.cfg``.
    ::

        [default]
        # Subsection of a larger simulation
        input = /lcrc/group/e3sm/ac.forsyth2/E3SM_simulations/e3sm_unified_test_simulation/20210528.v2rc3e.piControl.ne30pg2_EC30to60E2r2.chrysalis
        input_subdir = archive/atm/hist
        # Placing output (`post` directory) one level above, so it's not included when running `zstash` on `input`
        output = /lcrc/group/e3sm/ac.forsyth2/E3SM_simulations/e3sm_unified_test_simulation/
        case = 20210528.v2rc3e.piControl.ne30pg2_EC30to60E2r2.chrysalis
        www = /lcrc/group/e3sm/public_html/diagnostic_output/ac.forsyth2/E3SM/e3sm_unified_test_simulation/
        e3sm_unified = latest
        partition = compute
        environment_commands = "source /lcrc/soft/climate/e3sm-unified/test_e3sm_unified_1.5.0rc5_chrysalis.sh"

        [climo]
        active = True
        years = "51:70:20",
        # Use default vars

          [[ atm_monthly_180x360_aave ]]
          mapping_file = /home/ac.zender/data/maps/map_ne30pg2_to_cmip6_180x360_aave.20200201.nc
          frequency = "monthly"

          [[ atm_monthly_diurnal_8xdaily_180x360_aave ]]
          input_subdir = "archive/atm/hist"
          input_files = "eam.h4"
          mapping_file = /home/ac.zender/data/maps/map_ne30pg2_to_cmip6_180x360_aave.20200201.nc
          vars = "PRECT"
          frequency = "monthly_diurnal_8xdaily"

        [ts]
        active = True
        years = "51:70:10",

          [[ atm_monthly_180x360_aave ]]
          input_subdir = "archive/atm/hist"
          input_files = "eam.h0"
          frequency = "monthly"
          mapping_file = /home/ac.zender/data/maps/map_ne30pg2_to_cmip6_180x360_aave.20200201.nc
          # Use default vars

          [[ atm_daily_180x360_aave ]]
          input_subdir = "archive/atm/hist"
          input_files = "eam.h1"
          frequency = "daily"
          mapping_file = /home/ac.zender/data/maps/map_ne30pg2_to_cmip6_180x360_aave.20200201.nc
          vars = "PRECT"

          [[ atm_monthly_glb ]]
          input_subdir = "archive/atm/hist"
          input_files = "eam.h0"
          frequency = "monthly"
          mapping_file = "glb"
          # Use default vars

          [[ land_monthly ]]
          input_subdir = "archive/lnd/hist"
          input_files = "elm.h0"
          frequency = "monthly"
          mapping_file = /home/ac.zender/data/maps/map_ne30pg2_to_cmip6_180x360_aave.20200201.nc
          vars = "FSH,RH2M"

        [e3sm_diags]
        active = True
        years = "51:70:20",
        ts_num_years = 10
        ref_start_yr = 1979
        ref_final_yr = 2016
        environment_commands = "source /lcrc/soft/climate/e3sm-unified/test_e3sm_unified_1.5.0rc5_nompi.sh"

          [[ atm_monthly_180x360_aave ]]
          short_name = '20210528.v2rc3e.piControl.ne30pg2_EC30to60E2r2.chrysalis'
          grid = '180x360_aave'
          reference_data_path = '/lcrc/soft/climate/e3sm_diags_data/obs_for_e3sm_diags/climatology'
          obs_ts = '/lcrc/soft/climate/e3sm_diags_data/obs_for_e3sm_diags/time-series'
          dc_obs_climo = '/lcrc/group/e3sm/public_html/e3sm_diags_test_data/unit_test_complete_run/obs/climatology'
          climo_diurnal_subsection = "atm_monthly_diurnal_8xdaily_180x360_aave"

        [e3sm_diags_vs_model]
        active = False

        [amwg]
        active = False

        [mpas_analysis]
        active = True
        walltime = "24:00:00"
        parallelTaskCount = 6
        ts_years = "51-70",
        enso_years = "51-70",
        climo_years ="51-70",
        mesh = "EC30to60E2r2"
        anomalyRefYear = 51

        [global_time_series]
        active = True
        years = "51-70",
        ts_num_years = 10
        figstr=coupled_v2rc3e
        moc_file=mocTimeSeries_0101-0200.nc
        experiment_name=20210528.v2rc3e.piControl.ne30pg2_EC30to60E2r2.chrysalis
        ts_years = "51-70",
        climo_years ="51-70",
        environment_commands = "source /lcrc/soft/climate/e3sm-unified/test_e3sm_unified_1.5.0rc5_nompi.sh"

5. We can now test out ``zppy`` by running ``zppy -c e3sm_unified_test_simulation.cfg``.
If that command fails, return to step 3.

6. If the above command completes successfully, run:
    ::

        # cd into output directory
        cd /lcrc/group/e3sm/ac.forsyth2/E3SM_simulations/e3sm_unified_test_simulation/post/scripts
        # Check status of files that either failed or are still running.
        grep -v "OK" *status
        # If there is an error, return to step 3.

7. Output can be viewed at the web link corresponding to ``www`` in the configuration
file. In this case, that would be:
https://web.lcrc.anl.gov/public/e3sm/diagnostic_output/ac.forsyth2/E3SM/e3sm_unified_test_simulation/20210528.v2rc3e.piControl.ne30pg2_EC30to60E2r2.chrysalis/

Archive simulation using zstash
===============================

1. Create a batch script ``zstash_create.bash`` to run ``zstash``.
    ::

        #!/bin/bash

        #SBATCH  --job-name=zstash_create
        #SBATCH  --nodes=1
        #SBATCH  --output=/lcrc/group/e3sm/ac.forsyth2/zstash_dir/zstash_create.o%j
        #SBATCH  --exclusive
        #SBATCH  --time=04:00:00

        source /lcrc/soft/climate/e3sm-unified/test_e3sm_unified_1.5.0rc5_chrysalis.sh
        zstash create --hpss=none --cache=/lcrc/group/e3sm/ac.forsyth2/e3sm_unified_test_zstash/unified_test_cache /lcrc/group/e3sm/ac.forsyth2/E3SM_simulations/e3sm_unified_test_simulation/20210528.v2rc3e.piControl.ne30pg2_EC30to60E2r2.chrysalis

2. Run with ``sbatch zstash_create.bash``. This example takes about 2.5 hours to run.

Transfer simulation to other machines
=====================================
We can follow an adapted version of the steps at
https://e3sm-project.github.io/zstash/_build/html/master/best_practices.html#transfer-to-nersc-hpss
to transfer the data.

1. Login to Globus: https://www.globus.org/ (use NERSC credentials)

2. On the left sidebar, choose "ENDPOINTS".

3. Search for "NERSC DTN". Click on Green power button to activate endpoint.

4. On the left sidebar, choose "ENDPOINTS".

5. Search for "lcrc#dtn_bebop". Click on Green power button to activate endpoint.
Log in using LCRC credentials.

6. Paste the path to the ``zstash`` archive
(``/lcrc/group/e3sm/ac.forsyth2/e3sm_unified_test_zstash/unified_test_cache``)
in the "Path" box.

7. Click "Transfer or Sync to..." on the right side. The screen will now be split.

8. On the left side, choose "Select all"

9. On the right side, put "NERSC DTN" for collection.

10. Paste the NERSC path you want the archive copied to
(``/global/cscratch1/sd/forsyth/e3sm_unified_test_zstash/unified_test_cache``).
This path needs to already exist.

11. Click "Transfer & Sync Options" in the center.

12. Choose "sync - only transfer new or changed files"
(choose "modification time is newer" in the dropdown box),
"preserve source file modification times", and "verify file integrity after transfer".

13. For "Label This Transfer", put something like "zstash archive LCRC to NERSC".

14. On the left side, click "Start >". This will start the transfer from LCRC to NERSC.

15. On the left sidebar, choose "ENDPOINTS".

16. Search for "pic#compy-dtn". Click on Green power button to activate endpoint.
Log in using Compy credentials.

17. On the left sidebar, choose "File Manager." The screen will now be split.

18. On the left side, put "lcrc#dtn_bebop" for "Collection".

19. On the left side, paste the path to the ``zstash`` archive
(``/lcrc/group/e3sm/ac.forsyth2/e3sm_unified_test_zstash/unified_test_cache``)
in the "Path" box.

20. On the left side, choose "Select all"

21. On the right side, put "pic#compy-dtn" for "Collection".

22. Paste the NERSC path you want the archive copied to
(``/compyfs/fors729/e3sm_unified_test_zstash/unified_test_cache``).
This path needs to already exist.

23. Click "Transfer & Sync Options" in the center.

24. Choose "sync - only transfer new or changed files"
(choose "modification time is newer" in the dropdown box),
"preserve source file modification times", and "verify file integrity after transfer".

25. For "Label This Transfer", put something like "zstash archive LCRC to Compy".

26. On the left side, click "Start >". This will start the transfer from LCRC to Compy.

Check transfers were successful
===============================

Cori
----
1. Create a batch script ``zstash_check.bash``: ::

    #!/bin/bash
    #SBATCH  --job-name=zstash_check
    #SBATCH  --nodes=1
    #SBATCH  --output=/global/cscratch1/sd/forsyth/e3sm_unified_test_zstash/zstash_check.o%j
    #SBATCH  --exclusive
    #SBATCH  --time=3:00:00
    #SBATCH  -q regular
    #SBATCH  --constraint=haswell

source /global/common/software/e3sm/anaconda_envs/test_e3sm_unified_1.5.0rc5_cori-haswell.sh
zstash check --hpss=none --cache=/global/cscratch1/sd/forsyth/e3sm_unified_test_zstash/unified_test_cache

2. Run ``sbatch zstash_check.bash``. This takes about an hour to run.

Compy
-----

1. Create a batch script ``zstash_check.bash``: ::

    #!/bin/bash
    #SBATCH  --job-name=zstash_check
    #SBATCH  --nodes=1
    #SBATCH  --output=/compyfs/fors729/e3sm_unified_test_zstash/zstash_check.o%j
    #SBATCH  --exclusive
    #SBATCH  --time=3:00:00

    source /share/apps/E3SM/conda_envs/test_e3sm_unified_1.5.0rc5_compy.sh
    zstash check --hpss=none --cache=/compyfs/fors729/e3sm_unified_test_zstash/unified_test_cache

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
    #SBATCH  --output=/global/cscratch1/sd/forsyth/e3sm_unified_test_zstash/zstash_extract.o%j
    #SBATCH  --exclusive
    #SBATCH  --time=4:00:00
    #SBATCH  -q regular
    #SBATCH  --constraint=haswell

    source /global/common/software/e3sm/anaconda_envs/test_e3sm_unified_1.5.0rc5_cori-haswell.sh
    cd unified_test_extraction
    zstash extract --hpss=none --cache=/global/cscratch1/sd/forsyth/e3sm_unified_test_zstash/unified_test_cache

3. Run ``sbatch zstash_extract.bash``.


Compy
-----

1. ``mkdir unified_test_extraction``.

2. Create a batch script ``zstash_extract.bash``: ::

    #!/bin/bash
    #SBATCH  --job-name=zstash_extract
    #SBATCH  --nodes=1
    #SBATCH  --output=/compyfs/fors729/e3sm_unified_test_zstash/zstash_extract.o%j
    #SBATCH  --exclusive
    #SBATCH  --time=6:00:00

    source /share/apps/E3SM/conda_envs/test_e3sm_unified_1.5.0rc5_compy.sh
    cd unified_test_extraction
    zstash extract --hpss=none --cache=/compyfs/fors729/e3sm_unified_test_zstash/unified_test_cache

3. Run ``sbatch zstash_extract.bash``.


Testing zppy on other machines
==============================

``mv e3sm_unified_test_zstash/unified_test_extraction e3sm_unified_test_zppy/<case-name>``.

Go through steps 3-7 of "Testing zppy on a small simulation" but for
Cori (haswell and KNL) and Compy.

<Remember to replace these config files with the latest versions before merging!>

Sample configuration file for Cori
----------------------------------

``/global/cscratch1/sd/forsyth/e3sm_unified_test_zppy/e3sm_unified_test_simulation.cfg`` ::

    [default]
    # Subsection of a larger simulation
    input = /global/cscratch1/sd/forsyth/e3sm_unified_test_zppy/20210528.v2rc3e.piControl.ne30pg2_EC30to60E2r2.chrysalis
    input_subdir = archive/atm/hist
    # Placing output (`post` directory) one level above, so it's not included when running `zstash` on `input`
    output = /global/cscratch1/sd/forsyth/e3sm_unified_test_zppy/
    case = 20210528.v2rc3e.piControl.ne30pg2_EC30to60E2r2.chrysalis
    www = /global/cfs/cdirs/e3sm/www/forsyth/E3SM/e3sm_unified_test_simulation/
    e3sm_unified = latest
    partition = haswell
    environment_commands = "source /global/common/software/e3sm/anaconda_envs/test_e3sm_unified_1.5.0rc5_cori-haswell.sh"

    [climo]
    active = True
    years = "51:70:20",
    # Use default vars

      [[ atm_monthly_180x360_aave ]]
      mapping_file = /global/homes/z/zender/data/maps/map_ne30pg2_to_cmip6_180x360_aave.20200201.nc
      frequency = "monthly"

      [[ atm_monthly_diurnal_8xdaily_180x360_aave ]]
      input_subdir = "archive/atm/hist"
      input_files = "eam.h4"
      mapping_file = /global/homes/z/zender/data/maps/map_ne30pg2_to_cmip6_180x360_aave.20200201.nc
      vars = "PRECT"
      frequency = "monthly_diurnal_8xdaily"

    [ts]
    active = True
    years = "51:70:10",

      [[ atm_monthly_180x360_aave ]]
      input_subdir = "archive/atm/hist"
      input_files = "eam.h0"
      frequency = "monthly"
      mapping_file = /global/homes/z/zender/data/maps/map_ne30pg2_to_cmip6_180x360_aave.20200201.nc
      # Use default vars

      [[ atm_daily_180x360_aave ]]
      input_subdir = "archive/atm/hist"
      input_files = "eam.h1"
      frequency = "daily"
      mapping_file = /global/homes/z/zender/data/maps/map_ne30pg2_to_cmip6_180x360_aave.20200201.nc
      vars = "PRECT"

      [[ atm_monthly_glb ]]
      input_subdir = "archive/atm/hist"
      input_files = "eam.h0"
      frequency = "monthly"
      mapping_file = "glb"
      # Use default vars

      [[ land_monthly ]]
      input_subdir = "archive/lnd/hist"
      input_files = "elm.h0"
      frequency = "monthly"
      mapping_file = /global/homes/z/zender/data/maps/map_ne30pg2_to_cmip6_180x360_aave.20200201.nc
      vars = "FSH,RH2M"

    [e3sm_diags]
    active = True
    years = "51:70:20",
    ts_num_years = 10
    ref_start_yr = 1979
    ref_final_yr = 2016

      [[ atm_monthly_180x360_aave ]]
      short_name = '20210528.v2rc3e.piControl.ne30pg2_EC30to60E2r2.chrysalis'
      grid = '180x360_aave'
      reference_data_path = '/global/cfs/cdirs/e3sm/acme_diags/obs_for_e3sm_diags/climatology'
      obs_ts = '/global/cfs/cdirs/e3sm/acme_diags/obs_for_e3sm_diags/time-series'
      dc_obs_climo = '/global/cfs/cdirs/e3sm/acme_diags/obs_for_e3sm_diags/climatology'
      climo_diurnal_subsection = "atm_monthly_diurnal_8xdaily_180x360_aave"

    [e3sm_diags_vs_model]
    active = False

    [amwg]
    active = False

    [mpas_analysis]
    active = True
    walltime = "24:00:00"
    parallelTaskCount = 6
    ts_years = "51-70",
    enso_years = "51-70",
    climo_years ="51-70",
    mesh = "EC30to60E2r2"
    anomalyRefYear = 51

    [global_time_series]
    active = True
    years = "51-70",
    ts_num_years = 10
    figstr=coupled_v2rc3e
    moc_file=mocTimeSeries_0051-0070.nc
    experiment_name=20210528.v2rc3e.piControl.ne30pg2_EC30to60E2r2.chrysalis
    ts_years = "51-70",
    climo_years ="51-70",
    qos = "regular"


Sample configuration file for Compy
-----------------------------------

``/compyfs/fors729/e3sm_unified_test_zppy/e3sm_unified_test_simulation.cfg`` ::

    [default]
    # Subsection of a larger simulation
    input = /compyfs/fors729/e3sm_unified_test_zppy/20210528.v2rc3e.piControl.ne30pg2_EC30to60E2r2.chrysalis
    input_subdir = archive/atm/hist
    # Placing output (`post` directory) one level above, so it's not included when running `zstash` on `input`
    output = /compyfs/fors729/e3sm_unified_test_zppy/
    case = 20210528.v2rc3e.piControl.ne30pg2_EC30to60E2r2.chrysalis
    www = /compyfs/www/fors729/E3SM/e3sm_unified_test_simulation/
    e3sm_unified = latest
    partition = slurm
    environment_commands = "source /share/apps/E3SM/conda_envs/test_e3sm_unified_1.5.0rc5_compy.sh"

    [climo]
    active = True
    years = "51:70:20",
    # Use default vars

      [[ atm_monthly_180x360_aave ]]
      mapping_file = /compyfs/zender/maps/map_ne30pg2_to_cmip6_180x360_aave.20200201.nc
      frequency = "monthly"

      [[ atm_monthly_diurnal_8xdaily_180x360_aave ]]
      input_subdir = "archive/atm/hist"
      input_files = "eam.h4"
      mapping_file = /compyfs/zender/maps/map_ne30pg2_to_cmip6_180x360_aave.20200201.nc
      vars = "PRECT"
      frequency = "monthly_diurnal_8xdaily"

    [ts]
    active = True
    years = "51:70:10",

      [[ atm_monthly_180x360_aave ]]
      input_subdir = "archive/atm/hist"
      input_files = "eam.h0"
      frequency = "monthly"
      mapping_file = /compyfs/zender/maps/map_ne30pg2_to_cmip6_180x360_aave.20200201.nc
      # Use default vars

      [[ atm_daily_180x360_aave ]]
      input_subdir = "archive/atm/hist"
      input_files = "eam.h1"
      frequency = "daily"
      mapping_file = /compyfs/zender/maps/map_ne30pg2_to_cmip6_180x360_aave.20200201.nc
      vars = "PRECT"

      [[ atm_monthly_glb ]]
      input_subdir = "archive/atm/hist"
      input_files = "eam.h0"
      frequency = "monthly"
      mapping_file = "glb"
      # Use default vars

      [[ land_monthly ]]
      input_subdir = "archive/lnd/hist"
      input_files = "elm.h0"
      frequency = "monthly"
      mapping_file = /compyfs/zender/maps/map_ne30pg2_to_cmip6_180x360_aave.20200201.nc
      vars = "FSH,RH2M"

    [e3sm_diags]
    active = True
    years = "51:70:20",
    ts_num_years = 10
    ref_start_yr = 1979
    ref_final_yr = 2016

      [[ atm_monthly_180x360_aave ]]
      short_name = '20210528.v2rc3e.piControl.ne30pg2_EC30to60E2r2.chrysalis'
      grid = '180x360_aave'
      reference_data_path = '/compyfs/e3sm_diags_data/obs_for_e3sm_diags/climatology'
      obs_ts = '/compyfs/e3sm_diags_data/obs_for_e3sm_diags/time-series'
      dc_obs_climo = '/compyfs/e3sm_diags_data/obs_for_e3sm_diags/climatology'
      climo_diurnal_subsection = "atm_monthly_diurnal_8xdaily_180x360_aave"

    [e3sm_diags_vs_model]
    active = False

    [amwg]
    active = False

    [mpas_analysis]
    active = True
    walltime = "24:00:00"
    parallelTaskCount = 6
    ts_years = "51-70",
    enso_years = "51-70",
    climo_years ="51-70",
    mesh = "EC30to60E2r2"
    anomalyRefYear = 51

    [global_time_series]
    active = True
    years = "51-70",
    ts_num_years = 10
    figstr=coupled_v2rc3e
    moc_file=mocTimeSeries_0051-0070.nc
    experiment_name=20210528.v2rc3e.piControl.ne30pg2_EC30to60E2r2.chrysalis
    ts_years = "51-70",
    climo_years ="51-70",
    qos = "regular"

