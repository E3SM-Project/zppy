.. _task-global-time-series:

global_time_series — Global Time Series Plots
=============================================

The ``global_time_series`` task generates global time series plots of
key climate metrics. It can optionally produce a Viewer page. It depends on
 the :doc:`ts` task (for atmospheric and land global-mean time series)
 and on :doc:`mpas_analysis` when ocean plots are requested.

Parameters
----------

These 14 parameters are specific to the ``global_time_series`` task.

Core plotting options
~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 28 10 18 44

   * - Parameter
     - Required
     - Default
     - Description
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
   * - ``ts_years``
     - No
     - ``[""]``
     - Year ranges for the time-series sub-runs to depend on.
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

Viewer-specific plot options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 28 10 18 44

   * - Parameter
     - Required
     - Default
     - Description
   * - ``plots_atm``
     - No
     - ``""``
     - Extra atmosphere plots (when ``make_viewer = True``). These should be
       a subset of the variables from ``ts`` global subtasks.
   * - ``plots_ice``
     - No
     - ``""``
     - Extra sea-ice plots (when ``make_viewer = True``).
   * - ``plots_lnd``
     - No
     - ``""``
     - Extra land plots (when ``make_viewer = True``). Set to ``"all"`` to
       include every variable in the land CSV file.
   * - ``plots_ocn``
     - No
     - ``""``
     - Extra ocean plots (when ``make_viewer = True``).

Parameters at the top-level
~~~~~~~~~~~~~~~~~~~~~~~~~~~

This parameter has a ``global_time_series``-specific default, which means even
if it is set at the top level (``[default]``) section, this default value will
be used instead. Therefore, to specify a custom value, this parameter must be
defined inside ``[global_time_series]``:

.. list-table::
   :header-rows: 1
   :widths: 28 10 18 44

   * - Parameter
     - Required
     - Default
     - Description
   * - ``input_subdir``
     - No
     - ``"archive/ocn/hist"``
     - Subdirectory with ocean data. Overrides the ``[default]`` value
       (``archive/atm/hist``).

Deprecated parameters
~~~~~~~~~~~~~~~~~~~~~

The following parameters are still in ``default.ini`` but are deprecated and
have no effect: ``ncols``, ``nrows``.

Dependencies
------------

**Upstream (what global_time_series depends on):**

- :doc:`ts` — Monthly-atm-glb ts: the 5 classic atm plots, plots for specific atm variables. Monthly-lnd-glb ts: plots for specific lnd variables.
- :doc:`mpas_analysis` — the 3 classic ocn plots, plots for specific ocn variables.

**Downstream (what depends on global_time_series):**

- None.