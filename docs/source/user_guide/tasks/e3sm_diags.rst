.. _task-e3sm-diags:

e3sm_diags — E3SM Diagnostics
==============================

The ``e3sm_diags`` task runs `E3SM Diagnostics
<https://e3sm-project.github.io/e3sm_diags/>`_ to produce a wide variety of
atmospheric, land, and river diagnostic plots. It depends on the :doc:`climo`
and/or :doc:`ts` tasks for its input files.

For a complete list of available E3SM Diags parameters, see the
`E3SM Diags documentation
<https://e3sm-project.github.io/e3sm_diags/_build/html/master/available-parameters.html>`_.

For a table of which diagnostic sets require which parameters, see
`Confluence
<https://acme-climate.atlassian.net/wiki/spaces/IPD/pages/4984209586/zppy+parameters+for+e3sm_diags>`_.

Diagnostic sets
---------------

The ``sets`` parameter controls which diagnostic sets are run. All 19
available sets are:

``aerosol_aeronet``, ``aerosol_budget``, ``annual_cycle_zonal_mean``,
``area_mean_time_series``, ``cosp_histogram``, ``diurnal_cycle``,
``enso_diags``, ``lat_lon``, ``meridional_mean_2d``, ``mp_partition``,
``polar``, ``precip_pdf``, ``qbo``, ``streamflow``, ``tc_analysis``,
``tropical_subseasonal``, ``zonal_mean_2d``, ``zonal_mean_2d_stratosphere``,
``zonal_mean_xy``

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
   * - ``sets``
     - No
     - ``"lat_lon,zonal_mean_xy,..."``
     - List of diagnostic sets to run.
   * - ``run_type``
     - No
     - ``"model_vs_obs"``
     - Comparison type: ``"model_vs_obs"`` or ``"model_vs_model"``.
   * - ``climo_subsection``
     - No
     - ``""``
     - Name of the ``[climo]`` subtask to depend on.
   * - ``backend``
     - No
     - ``"mpl"``
     - Plotting backend.
   * - ``cfg``
     - No
     - ``""``
     - Path to an additional E3SM Diags configuration file.
   * - ``multiprocessing``
     - No
     - ``True``
     - Use multiprocessing.
   * - ``num_workers``
     - No
     - ``24``
     - Number of worker processes.
   * - ``output_format``
     - No
     - ``["png"]``
     - Output plot formats.
   * - ``output_format_subplot``
     - No
     - ``[]``
     - Output formats for subplots.
   * - ``short_name``
     - No
     - ``""``
     - Short name used as test name and label.
   * - ``tag``
     - No
     - ``"model_vs_obs"``
     - Label for the results directory.
   * - ``swap_test_ref``
     - No
     - ``False``
     - Swap test and reference in model-vs-model runs.
   * - ``keep_mvm_case_name_in_fig``
     - No
     - ``True``
     - Include case name in model-vs-model output paths.
   * - ``obs_ts``
     - No
     - ``""``
     - Path to observation time-series data for ``enso_diags``, ``qbo``,
       ``area_mean_time_series`` sets.
   * - ``reference_data_path``
     - No*
     - ``""``
     - Path to reference climatology data.
       **Required for** ``run_type="model_vs_model"``.
   * - ``ref_name``
     - No*
     - ``""``
     - Reference dataset name.
       **Required for** ``run_type="model_vs_model"``.
   * - ``short_ref_name``
     - No*
     - ``""``
     - Short reference name.
       **Required for** ``run_type="model_vs_model"``.
   * - ``diff_title``
     - No
     - ``"Model - Observations"``
     - Title for difference plots.
   * - ``ref_years``
     - No
     - ``[""]``
     - Year ranges for reference data in model-vs-model runs.
   * - ``ref_start_yr``
     - No*
     - ``""``
     - Start year of reference data. Required for ``enso_diags``, ``qbo``.
   * - ``ref_final_yr``
     - No*
     - ``""``
     - End year of reference data. Required for ``qbo`` and certain
       model-vs-model sets.
   * - ``ts_subsection``
     - No
     - ``""``
     - Name of the ``[ts]`` subtask to depend on.
   * - ``ts_num_years_ref``
     - No
     - ``5``
     - Year increment for reference time-series data.
   * - ``ts_daily_subsection``
     - No
     - ``""``
     - ``[ts]`` subtask for daily data (required for ``tropical_subseasonal``).
   * - ``climo_diurnal_subsection``
     - No
     - ``""``
     - ``[climo]`` subtask for diurnal cycle data.
   * - ``climo_diurnal_frequency``
     - No
     - ``""``
     - Frequency name for the diurnal cycle ``[climo]`` subtask.
   * - ``dc_obs_climo``
     - No
     - ``""``
     - Path to observation climatology for ``diurnal_cycle`` set.
   * - ``reference_data_path_climo_diurnal``
     - No
     - ``""``
     - Reference climatology path for ``diurnal_cycle`` MVM runs.
   * - ``reference_data_path_tc``
     - No
     - ``""``
     - Reference data path for ``tc_analysis`` MVM runs.
   * - ``reference_data_path_ts``
     - No
     - ``""``
     - Reference time-series path for ``enso_diags``/``qbo``/``area_mean_time_series``.
   * - ``reference_data_path_ts_daily``
     - No
     - ``""``
     - Reference daily time-series path for ``tropical_subseasonal``.
   * - ``reference_data_path_ts_rof``
     - No
     - ``""``
     - Reference river time-series path for ``streamflow`` MVM runs.
   * - ``streamflow_obs_ts``
     - No
     - ``""``
     - Path to observation data for ``streamflow`` set.
   * - ``gauges_path``
     - No
     - ``""``
     - Path to stream gauge data for ``streamflow`` MVM runs.
   * - ``tc_obs``
     - No
     - ``""``
     - Path to observation data for ``tc_analysis`` set.

Dependencies
------------

**Upstream (what e3sm_diags depends on):**

- :doc:`climo` — Monthly-atm climo: lat_lon, zonal_mean_xy, zonal_mean_2d, polar, cosp_histogram, meridional_mean_2d, annual_cycle_zonal_mean, zonal_mean_2d_stratosphere, aerosol_aeronet, aerosol_budget. Monthly-lnd climo: lat_lon_land. Monthly dirunal-atm climo: diurnal_cycle
- :doc:`ts` — Monthly-atm ts: enso_diags, qbo, area_mean_time_series, mp_partition. Monthly-rof ts: streamflow. Daily-atm ts: tropical_subseasonal, precip_pdf.
- :doc:`tc_analysis` — Required for tc_analysis set.

**Downstream (what depends on e3sm_diags):**

- None.
