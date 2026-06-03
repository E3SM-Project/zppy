.. _task-global-time-series:

global_time_series — Global Time Series Plots
=============================================

The ``global_time_series`` task generates global time series plots of
key climate metrics. It can optionally produce a Viewer page. It depends on
the :doc:`ts` task (for atmospheric, land, and ocean global-mean time series)
and optionally on :doc:`mpas_analysis` (for ocean and sea-ice plots).

Parameters
----------

.. list-table::
   :header-rows: 1
   :widths: 28 10 18 44

   * - Parameter
     - Required
     - Default
     - Description
   * - ``active``
     - No
     - ``False``
     - Set to ``True`` to enable this task.
   * - ``ts_years``
     - No
     - ``[""]``
     - Year ranges for the time-series sub-runs to depend on.
   * - ``climo_years``
     - No
     - ``[""]``
     - Year ranges for climatology data (if needed).
   * - ``color``
     - No
     - ``"Blue"``
     - Color used for the plots.
   * - ``experiment_name``
     - No
     - ``""``
     - Label displayed on the plots.
   * - ``figstr``
     - No
     - ``""``
     - Prefix for output figure file names.
   * - ``make_viewer``
     - No
     - ``False``
     - Set to ``True`` to construct a Viewer page with extended plots.
   * - ``regions``
     - No
     - ``"glb,n,s"``
     - Regions to plot: ``glb`` (global), ``n`` (northern hemisphere),
       ``s`` (southern hemisphere).
   * - ``input_subdir``
     - No
     - ``"archive/ocn/hist"``
     - Subdirectory with ocean data. Overrides the ``[default]`` value.
   * - ``moc_file``
     - No
     - ``""``
     - Path to the MOC file (for the ``max_moc`` plot). Only needed when
       ``make_viewer = False``.
   * - ``mpas_analysis_subsections``
     - No
     - ``[""]``
     - Names of ``[mpas_analysis]`` subtasks to depend on. Leave empty if
       no subsections are defined.
   * - ``plots_original``
     - No
     - ``"net_toa_flux_restom,..."``
     - Names of the standard plots to generate when ``make_viewer = False``.
       Available plots and their variable requirements:

       - ``net_toa_flux_restom`` — requires ``RESTOM``
       - ``net_atm_energy_imbalance`` — requires ``RESTOM``, ``RESSURF``
       - ``global_surface_air_temperature`` — requires ``TREFHT``
       - ``toa_radiation`` — requires ``FSNTOA``, ``FLUT``
       - ``net_atm_water_imbalance`` — requires ``PRECC``, ``PRECL``, ``QFLX``
       - ``change_ohc`` — requires ocean data
       - ``max_moc`` — requires ocean MOC data
       - ``change_sea_level`` — requires ocean data

       Remove the three ocean plots if you don't have ocean data.
   * - ``plots_atm``
     - No
     - ``""``
     - Extra atmosphere plots (when ``make_viewer = True``). These should be
       a subset of the variables from ``ts`` global subtasks.
   * - ``plots_lnd``
     - No
     - ``""``
     - Extra land plots (when ``make_viewer = True``). Set to ``"all"`` to
       include every variable in the land CSV file.
   * - ``plots_ocn``
     - No
     - ``""``
     - Extra ocean plots (when ``make_viewer = True``).
   * - ``plots_ice``
     - No
     - ``""``
     - Extra sea-ice plots (when ``make_viewer = True``).
