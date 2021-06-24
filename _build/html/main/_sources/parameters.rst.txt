.. _parameters:

***************
Parameters
***************

Parameters make use of inheritance. Parameters set in ``[default]`` can
be overridden by parameters set in a ``[section]``, which can themselves
be overridden by parameters set in a ``[[subsection]``.



.. warning::
    The following code block lists the types and default values for parameters.
    It is not the correct syntax for a configuration file.
    Copying and pasting the code block into a configuration file will not work!

.. warning::
    The ``amwg`` section is user-contributed and is not officially supported/documented!

The following is adapted from ``zppy/zppy/templates/default.ini`` and explains the
types and default values for the parameters. ::

        [default]
        # The directory to be post-processed
        input = string
        # The specific subdirectory with the atmospheric data
        input_subdir = string(default="archive/atm/hist")
        # Where the post-processing results (`post` directory) should go
        output = string
        # The case name of the simulation
        case = string
        # Where the post-processing visuals should go (to be viewed online)
        www = string
        # Set to True to keep temporary directories/files after zppy completes
        debug = boolean(default=False)
        # The partition of the machine to run on
        partition = string(default="")
        # The version of E3SM Unified to use
        e3sm_unified = option('latest', 'test', default='latest')
        # This should be set to True if you don't want the batch jobs to be submitted
        dry_run = boolean(default=False)

        [climo]
        # Set to True to run this section
        active = boolean(default=True)
        # Quality of service
        qos = string(default="regular")
        # The number of nodes to use
        nodes = integer(default=4)
        # The maximum time to run
        walltime = string(default="02:00:00")
        # Which files to use as input
        input_files = string(default="eam.h0")
        # The frequency of the data. Options include "monthly", "monthly_diurnal_8xdaily"
        frequency = string(default="monthly")
        # The mapping file to use
        mapping_file = string(default="")
        # The grid to use
        grid = string(default="")
        # The years to run; "1:100:20" would mean process years 1-100 in 20-year increments
        years = string_list(default=list(""))
        exclude = boolean(default=False)
        # The variables to process
        vars = string(default="")

        [ts]
        # Set to True to run this section
        active = boolean(default=True)
        # Quality of service
        qos = string(default="regular")
        # The number of nodes to use
        nodes = integer(default=1)
        # The maximum time to run
        walltime = string(default="02:00:00")
        # Which files to use as input
        input_files = string(default="eam.h0")
        # The frequency of the data. Options include "monthly", "monthly_diurnal_8xdaily"
        frequency = string(default="monthly")
        # The mapping file to use
        mapping_file = string(default="")
        # The grid to use
        grid = string(default="")
        area_nm = string(default="area")
        # The variables to process
        vars = string(default="FSNTOA,FLUT,FSNT,FLNT,FSNS,FLNS,SHFLX,QFLX,TAUX,TAUY,PRECC,PRECL,PRECSC,PRECSL,TS,TREFHT,CLDTOT,CLDHGH,CLDMED,CLDLOW,U")
        # The years to run; "1:100:10" would mean process years 1-100 in 10-year increments
        years = string_list(default=list(""))
        # Days per file
        dpf = integer(default=30)
        # Time-steps per day
        tpd = integer(default=1)

        [e3sm_diags]
        # Set to True to run this section
        active = boolean(default=True)
        # The grid to use
        grid = string(default="")
        # Quality of service
        qos = string(default="regular")
        # The number of nodes to use
        nodes = integer(default=1)
        # The maximum time to run
        walltime = string(default="02:00:00")
        # See https://e3sm-project.github.io/e3sm_diags/_build/html/master/available-parameters.html
        reference_data_path = string(default="")
        # Used for `test_name` and `short_test_name` in https://e3sm-project.github.io/e3sm_diags/_build/html/master/available-parameters.html
        short_name = string(default="")
        cfg = string(default="")
        # The sets to run
        # Note that "enso_diags","qbo","area_mean_time_series" require time-series data.
        # They also require `obs_ts` and `ref_start_yr` to be set.
        # "qbo" requires `ref_final_yr` to be set as well.
        # "diurnal_cycle" requires `climo_diurnal_subsection` and `ds_obs_climo` to be set.
        sets = string_list(default=list("lat_lon","zonal_mean_xy","zonal_mean_2d","polar","cosp_histogram","meridional_mean_2d","enso_diags","qbo","area_mean_time_series","diurnal_cycle"))
        # See https://e3sm-project.github.io/e3sm_diags/_build/html/master/available-parameters.html
        backend = string(default="mpl")
        # See https://e3sm-project.github.io/e3sm_diags/_build/html/master/available-parameters.html
        diff_title = string(default="Model - Observations")
        # See https://e3sm-project.github.io/e3sm_diags/_build/html/master/available-parameters.html
        run_type = string(default="model_vs_obs")
        # Used to label the results directory
        tag = string(default="model_vs_obs")
        # See https://e3sm-project.github.io/e3sm_diags/_build/html/master/available-parameters.html
        output_format = string_list(default=list("png"))
        # See https://e3sm-project.github.io/e3sm_diags/_build/html/master/available-parameters.html
        output_format_subplot = string_list(default=list())
        # See https://e3sm-project.github.io/e3sm_diags/_build/html/master/available-parameters.html
        multiprocessing = boolean(default=True)
        # See https://e3sm-project.github.io/e3sm_diags/_build/html/master/available-parameters.html
        num_workers = integer(default=24)
        # Variables to process
        vars = string(default="FSNTOA,FLUT,FSNT,FLNT,FSNS,FLNS,SHFLX,QFLX,TAUX,TAUY,PRECC,PRECL,PRECSC,PRECSL,TS,TREFHT,CLDTOT,CLDHGH,CLDMED,CLDLOW,U")
        # Name of the subsection of `[climo]` to use for "diurnal_cycle" runs
        climo_diurnal_subsection = string(default="")
        # The following parameters aren't defined in `default.ini`
        # Path to observation data for diurnal cycle runs
        dc_obs_climo = string
        # Path to observation data for time-series-required ("enso_diags","qbo","area_mean_time_series") runs
        obs_ts = string
        # Start year for the reference data
        ref_start_yr = string
        # End year (i.e., the last year to use) for the reference data
        ref_end_yr = string
        # Final year (i.e., the last available year) for the reference data
        ref_final_yr = string

        [e3sm_diags_vs_model]
        # Set to True to run this section
        active = boolean(default=True)
        grid = string(default="")
        # Quality of service
        qos = string(default="regular")
        nodes = integer(default=1)
        walltime = string(default="02:00:00")
        reference_data_path = string(default="")
        ref_name = string(default="")
        short_ref_name = string(default="")
        short_name = string(default="")
        swap_test_ref = boolean(default=False)
        sets = string_list(default=list("lat_lon","zonal_mean_xy","zonal_mean_2d","polar","cosp_histogram","meridional_mean_2d"))
        backend = string(default="mpl")
        diff_title = string(default="Difference")
        run_type = string(default="model_vs_model")
        tag = string(default="model_vs_model")
        output_format = string_list(default=list("png"))
        output_format_subplot = string_list(default=list(""))
        multiprocessing = boolean(default=True)
        num_workers = integer(default=24)

        years = string_list(default=list(""))
        ref_years = string_list(default=list(""))

        [amwg]
        # Set to True to run this section
        active = boolean(default=True)

        [mpas_analysis]
        # Set to True to run this section
        active = boolean(default=True)
        shortTermArchive = boolean(default=True)
        # Quality of service
        qos = string(default="regular")
        # The number of nodes to use
        nodes = integer(default=1)
        # The maximum time to run
        walltime = string(default="06:00:00")
        parallelTaskCount = integer(default=12)
        ncclimoParallelMode = string(default="bck")
        ncclimoThreads = integer(default=12)
        mapMpiTasks = integer(default=6)
        cache = boolean(default=True)
        purge = boolean(default=False)
        PostMOC = boolean(default=False)
        mpaso_nml = string(default="mpaso_in")
        mpassi_nml = string(default="mpassi_in")
        stream_ocn = string(default="streams.ocean")
        stream_ice = string(default="streams.seaice")
        generate = string_list(default=list('all', 'no_landIceCavities', 'no_BGC', 'no_icebergs', 'no_min', 'no_max', 'no_sose', 'no_climatologyMapAntarcticMelt', 'no_regionalTSDiagrams', 'no_timeSeriesAntarcticMelt', 'no_timeSeriesOceanRegions', 'no_climatologyMapSose', 'no_woceTransects', 'no_soseTransects', 'no_geojsonTransects', 'no_oceanRegionalProfiles', 'no_hovmollerOceanRegions'))

        [global_time_series]
        # Set to True to run this section
        active = boolean(default=True)
        # The number of nodes to use
        nodes = integer(default=1)
        # The maximum time to run
        walltime = string(default="02:00:00")
        # The color to be used for the graphs.
        color = string(default="Blue")
        # "1-100" would plot years 1 to 100 on the graphs.
        years = string_list(default=list(""))
        # The number of years in a time-series file.
        ts_num_years = integer(default=10)
        # What the plot files should be named
        figstr = string(default="")
        moc_file = string(default="")
        experiment_name = string(default="")
        ts_years = string_list(default=list(""))
        climo_years = string_list(default=list(""))
