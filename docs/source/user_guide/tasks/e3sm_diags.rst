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

The ``sets`` parameter controls which diagnostic sets are run. All 20
available sets are:

``aerosol_aeronet``, ``aerosol_budget``, ``annual_cycle_zonal_mean``,
``area_mean_time_series``, ``cosp_histogram``, ``diurnal_cycle``,
``enso_diags``, ``lat_lon``, ``lat_lon_land``, ``meridional_mean_2d``, ``mp_partition``,
``polar``, ``precip_pdf``, ``qbo``, ``streamflow``, ``tc_analysis``,
``tropical_subseasonal``, ``zonal_mean_2d``, ``zonal_mean_2d_stratosphere``,
``zonal_mean_xy``

Parameters
----------

These 35 parameters are specific to the ``e3sm_diags`` task.

General parameters
~~~~~~~~~~~~~~~~~~

There are 12 general parameters:

.. list-table::
   :header-rows: 1
   :widths: 28 10 18 44

   * - Parameter
     - Required
     - Default
     - Description
   * - ``backend``
     - No
     - ``"mpl"``
     - Plotting backend.
   * - ``cfg``
     - No
     - ``""``
     - Path to an additional E3SM Diags configuration file.
   * - ``keep_mvm_case_name_in_fig``
     - No
     - ``True``
     - Include case name in model-vs-model output paths.
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
   * - ``run_type``
     - No
     - ``"model_vs_obs"``
     - Comparison type: ``"model_vs_obs"`` or ``"model_vs_model"``.
   * - ``sets``
     - No
     - ``"lat_lon,zonal_mean_xy,..."``
     - List of diagnostic sets to run.
   * - ``short_name``
     - No
     - ``""``
     - Short name used as test name and label.
   * - ``swap_test_ref``
     - No
     - ``False``
     - Swap test and reference in model-vs-model runs.
   * - ``tag``
     - No
     - ``"model_vs_obs"``
     - Label for the results directory.

Set-specific parameters
~~~~~~~~~~~~~~~~~~~~~~~

There are 23 set-specific parameters.

**Overview by set**

We will review useful parameters by set. To do this, we will group them by dependency. For more info on dependencies, see :ref:`Dependencies <dependency_graph>`.

.. list-table::
   :header-rows: 1
   :stub-columns: 1
   :widths: 20 80

   * - Group
     - Sets
   * - ``climo_month_atm``
     - ``lat_lon``, ``zonal_mean_xy``, ``zonal_mean_2d``, ``polar``,
       ``cosp_histogram``, ``meridional_mean_2d``,
       ``annual_cycle_zonal_mean``, ``zonal_mean_2d_stratosphere``,
       ``aerosol_aeronet``, ``aerosol_budget``
   * - ``climo_month_lnd``
     - ``lat_lon_land``
   * - ``diurnal``
     - ``diurnal_cycle``
   * - ``ts_month_atm``
     - ``enso_diags``, ``qbo``, ``area_mean_time_series``, ``mp_partition``
   * - ``ts_daily_atm``
     - ``tropical_subseasonal``, ``precip_pdf``
   * - ``streamflow``
     - ``streamflow``
   * - ``tc``
     - ``tc_analysis``

Cell values: **Always** = required for both run types;
**MvO** = ``model_vs_obs`` only; **MvM** = ``model_vs_model`` only;
**—** = not used. Values marked with \* differ across sets within the group
(see notes below the table).

.. list-table::
   :header-rows: 1
   :stub-columns: 1
   :widths: 30 14 14 10 16 14 12 10

   * - Parameter
     - ``climo_month_atm``
     - ``climo_month_lnd``
     - ``diurnal``
     - ``ts_month_atm``
     - ``ts_daily_atm``
     - ``streamflow``
     - ``tc``
   * - ``climo_diurnal_frequency``
     - —
     - —
     - Always
     - —
     - —
     - —
     - —
   * - ``climo_diurnal_subsection``
     - —
     - —
     - Always
     - —
     - —
     - —
     - —
   * - ``climo_subsection`` [#subsection]_
     - Always
     - Always
     - —
     - —
     - —
     - —
     - —
   * - ``dc_obs_climo`` [#dc_obs]_
     - —
     - —
     - MvO
     - —
     - —
     - —
     - —
   * - ``diff_title``
     - —
     - —
     - —
     - MvM
     - MvM
     - MvM
     - MvM
   * - ``gauges_path`` [#inferred]_
     - —
     - —
     - —
     - —
     - —
     - MvM
     - —
   * - ``obs_ts`` [#inferred]_
     - —
     - —
     - —
     - MvO
     - MvO
     - —
     - —
   * - ``ref_final_yr`` \*
     - —
     - —
     - —
     - Always \*
     - MvM
     - MvM
     - MvM
   * - ``ref_name``
     - —
     - —
     - —
     - MvM
     - MvM
     - MvM
     - MvM
   * - ``ref_start_yr`` \*
     - —
     - —
     - —
     - Always \*
     - MvM
     - MvM
     - MvM
   * - ``reference_data_path`` [#refpath]_
     - Always
     - Always
     - Always
     - —
     - —
     - —
     - —
   * - ``reference_data_path_climo_diurnal`` [#inferred]_
     - —
     - —
     - MvM
     - —
     - —
     - —
     - —
   * - ``reference_data_path_tc`` [#inferred]_
     - —
     - —
     - —
     - —
     - —
     - —
     - MvM
   * - ``reference_data_path_ts`` [#inferred]_
     - —
     - —
     - —
     - MvM
     - —
     - —
     - —
   * - ``reference_data_path_ts_daily`` [#inferred]_
     - —
     - —
     - —
     - —
     - MvM
     - —
     - —
   * - ``reference_data_path_ts_rof`` [#inferred]_
     - —
     - —
     - —
     - —
     - —
     - MvM
     - —
   * - ``short_ref_name``
     - —
     - —
     - —
     - MvM
     - MvM
     - MvM
     - MvM
   * - ``streamflow_obs_ts`` [#inferred]_
     - —
     - —
     - —
     - —
     - —
     - MvO
     - —
   * - ``tc_obs`` [#inferred]_
     - —
     - —
     - —
     - —
     - —
     - —
     - MvO
   * - ``ts_daily_subsection`` [#subsection]_
     - —
     - —
     - —
     - —
     - Always
     - —
     - —
   * - ``ts_num_years_ref``
     - —
     - —
     - —
     - MvM
     - MvM
     - MvM
     - —
   * - ``ts_subsection`` [#subsection]_
     - —
     - —
     - —
     - Always
     - —
     - —
     - —

.. [#subsection] Falls back to ``sub`` → ``grid`` if not set.
.. [#refpath] Inferred from ``diagnostics_base_path`` if not set. In MvM,
   also used as a base path from which ``reference_data_path_climo_diurnal``
   and ``reference_data_path_ts`` are derived.
.. [#dc_obs] Inferred from ``reference_data_path`` if not set (MvO only).
.. [#inferred] Inferred from ``diagnostics_base_path`` (or a sibling path)
   if not set.

Note on \* cells (``ts_month_atm``): within ``ts_month_atm`` the four sets do not behave uniformly for ``ref_start_yr`` and ``ref_final_yr``:

.. list-table::
   :header-rows: 1
   :widths: 30 20 20 20 20

   * - Parameter
     - ``enso_diags``
     - ``qbo``
     - ``area_mean_time_series``
     - ``mp_partition``
   * - ``ref_final_yr``
     - MvM
     - Always
     - —
     - MvM
   * - ``ref_start_yr``
     - Always
     - Always
     - —
     - MvM


**Parameter list**

.. list-table::
   :header-rows: 1
   :widths: 28 10 18 44

   * - Parameter
     - Required
     - Default
     - Description
   * - ``climo_diurnal_frequency``
     - No
     - ``""``
     - Frequency name for the diurnal cycle ``[climo]`` subtask.
   * - ``climo_diurnal_subsection``
     - No
     - ``""``
     - ``[climo]`` subtask for diurnal cycle data.
   * - ``climo_subsection``
     - No
     - ``""``
     - Name of the ``[climo]`` subtask to depend on.
   * - ``dc_obs_climo``
     - No
     - ``""``
     - Path to observation climatology for the ``diurnal_cycle`` set.
   * - ``diff_title``
     - No
     - ``"Model - Observations"``
     - Title for difference plots.
   * - ``gauges_path``
     - No
     - ``""``
     - Path to stream gauge data for ``streamflow`` model-vs-model runs.
   * - ``obs_ts``
     - No
     - ``""``
     - Path to observation time-series data for ``enso_diags``, ``qbo``, and
       ``area_mean_time_series``.
   * - ``ref_final_yr``
     - No*
     - ``""``
     - End year of reference data. Required for ``qbo`` and certain
       model-vs-model sets.
   * - ``ref_name``
     - No*
     - ``""``
     - Reference dataset name.
       **Required for** ``run_type="model_vs_model"``.
   * - ``ref_start_yr``
     - No*
     - ``""``
     - Start year of reference data. Required for ``enso_diags``, ``qbo``.
   * - ``reference_data_path``
     - No*
     - ``""``
     - Path to reference climatology data.
       **Required for** ``run_type="model_vs_model"``.
   * - ``reference_data_path_climo_diurnal``
     - No
     - ``""``
     - Reference climatology path for ``diurnal_cycle`` MVM runs.
   * - ``ref_years``
     - No
     - ``[""]``
     - Year ranges for reference data in model-vs-model runs.
   * - ``reference_data_path_tc``
     - No
     - ``""``
     - Reference data path for ``tc_analysis`` MVM runs.
   * - ``reference_data_path_ts``
     - No
     - ``""``
     - Reference time-series path for ``enso_diags``, ``qbo``, ``area_mean_time_series``.
   * - ``reference_data_path_ts_daily``
     - No
     - ``""``
     - Reference daily time-series path for ``tropical_subseasonal``.
   * - ``reference_data_path_ts_rof``
     - No
     - ``""``
     - Reference river time-series path for ``streamflow`` MVM runs.
   * - ``short_ref_name``
     - No*
     - ``""``
     - Short reference name.
       **Required for** ``run_type="model_vs_model"``.
   * - ``streamflow_obs_ts``
     - No
     - ``""``
     - Path to observation data for ``streamflow`` set.
   * - ``tc_obs``
     - No
     - ``""``
     - Path to observation data for ``tc_analysis`` set.
   * - ``ts_daily_subsection``
     - No
     - ``""``
     - ``[ts]`` subtask for daily data (required for
       ``tropical_subseasonal``).
   * - ``ts_num_years_ref``
     - No
     - ``5``
     - Year increment for reference time-series data.
   * - ``ts_subsection``
     - No
     - ``""``
     - Name of the ``[ts]`` subtask to depend on.

Parameters at the top-level
~~~~~~~~~~~~~~~~~~~~~~~~~~~

For top-level parameters, see :ref:`top-level parameters <parameters-top-level>`.

Dependencies
------------

**Upstream (what e3sm_diags depends on):**

- :doc:`climo` — Monthly-atm climo: lat_lon, zonal_mean_xy, zonal_mean_2d, polar, cosp_histogram, meridional_mean_2d, annual_cycle_zonal_mean, zonal_mean_2d_stratosphere, aerosol_aeronet, aerosol_budget. Monthly-lnd climo: lat_lon_land. Monthly diurnal-atm climo: diurnal_cycle
- :doc:`ts` — Monthly-atm ts: enso_diags, qbo, area_mean_time_series, mp_partition. Monthly-rof ts: streamflow. Daily-atm ts: tropical_subseasonal, precip_pdf.
- :doc:`tc_analysis` — Required for tc_analysis set.

**Downstream (what depends on e3sm_diags):**

- None.
