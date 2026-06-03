.. _task-pcmdi-diags:

pcmdi_diags — PCMDI Metrics
============================

The ``pcmdi_diags`` task runs `PCMDI Metrics Package (PMP)
<https://pcmdi.github.io/pcmdi_metrics/>`_ diagnostics to compute climate
model performance metrics. It depends on the :doc:`e3sm_to_cmip` task for
CMIP-format input data.

Diagnostic sets
---------------

The ``current_set`` parameter selects which PMP diagnostic to run:

- ``mean_climate`` — climatological mean metrics
- ``variability_modes_cpl`` — coupled variability modes (PDO, NPGO, AMO)
- ``variability_modes_atm`` — atmospheric variability modes (NAM, NAO, PNA, etc.)
- ``enso`` — ENSO metrics (not currently enabled by default)
- ``synthetic_plots`` — composite viewer page combining outputs from other sets

Parameters
----------

Most useful at the task level (all sets)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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
   * - ``run_type``
     - No
     - ``"model_vs_obs"``
     - ``"model_vs_obs"`` or ``"model_vs_model"``. Note: in PCMDI context,
       model-vs-model compares two model simulations against observations.
   * - ``figure_format``
     - No
     - ``"png"``
     - Output figure format.
   * - ``model_name``
     - No
     - ``"e3sm.historical.v3-LR.0051"``
     - Model name (required for MVO runs).
   * - ``model_tableID``
     - No
     - ``"Amon"``
     - CMIP table ID (required for MVO runs).
   * - ``model_name_ref``
     - No
     - ``"ERA5"``
     - Reference model name (required for MVM runs).
   * - ``model_tableID_ref``
     - No
     - ``"Amon"``
     - Reference CMIP table ID (required for MVM runs).
   * - ``e3sm_to_cmip_atm_subsection``
     - No
     - ``""``
     - Name of the ``[e3sm_to_cmip]`` atm subtask to depend on.
   * - ``generate_sftlf``
     - No
     - ``True``
     - Flag to process the land/sea mask within PCMDI.
   * - ``grid``
     - No
     - ``"180x360_aave"``
     - Model data grid after remapping.
   * - ``multiprocessing``
     - No
     - ``True``
     - Use multiprocessing.
   * - ``num_workers``
     - No
     - ``24``
     - Number of worker processes.
   * - ``obs_ts``
     - No
     - ``""``
     - Path to observation time-series data. Required for
       ``mean_climate``, ``variability_modes_*``, ``enso`` sets.
   * - ``ts_num_years``
     - No
     - ``5``
     - Year increment for test model data.
   * - ``ts_years``
     - No
     - ``[""]``
     - Year ranges for test model data.

Per-subtask parameters
~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 28 10 18 44

   * - Parameter
     - Required
     - Default
     - Description
   * - ``current_set``
     - No
     - ``""``
     - The diagnostic set to run. If not set, inferred from the subsection
       name.
   * - ``obs_sets``
     - No
     - ``"default"``
     - Observational datasets to use (see ``reference_alias.json``).
   * - ``ref_start_yr``
     - No
     - ``""``
     - Start year for reference data.
   * - ``ref_final_yr``
     - No
     - ``""``
     - End year for reference data.
   * - ``ref_years``
     - No
     - ``[""]``
     - Year ranges for reference data.

mean_climate parameters
~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 28 10 18 44

   * - Parameter
     - Required
     - Default
     - Description
   * - ``cmip_vars``
     - No
     - ``"pr,prw,psl,..."``
     - Variables from the CMIP6 table to use.
   * - ``clim_vars``
     - No
     - ``"pr,prw,psl,..."``
     - Variables for mean climate metrics.
   * - ``clim_regions``
     - No
     - ``"global,ocean,land"``
     - Regions for mean climate metrics.
   * - ``target_grid``
     - No
     - ``"1x1"``
     - Target regridding grid.
   * - ``target_grid_string``
     - No
     - ``"1px1p"``
     - Description string for the target grid.
   * - ``regrid_tool``
     - No
     - ``"esmf"``
     - Regridding tool.
   * - ``regrid_method``
     - No
     - ``"regrid2"``
     - Regridding method.

variability_modes parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 28 10 18 44

   * - Parameter
     - Required
     - Default
     - Description
   * - ``mova_vars``
     - No
     - ``"psl"``
     - Variables for ``variability_modes_atm``.
   * - ``mova_modes``
     - No
     - ``"NAM,NAO,PNA,NPO,SAM,PSA1,PSA2"``
     - Modes for ``variability_modes_atm``.
   * - ``movc_vars``
     - No
     - ``"ts"``
     - Variables for ``variability_modes_cpl``.
   * - ``movc_modes``
     - No
     - ``"PDO,NPGO,AMO"``
     - Modes for ``variability_modes_cpl``.
   * - ``CBF``
     - No
     - ``True``
     - Use Common Base Function approach.
   * - ``ConvEOF``
     - No
     - ``True``
     - Compute conventional EOF.
   * - ``EofScaling``
     - No
     - ``False``
     - Apply EOF scaling.
   * - ``eofn_mod_max``
     - No
     - ``3``
     - Maximum number of EOF modes for model.
   * - ``seasons``
     - No
     - ``"monthly"``
     - Seasons to analyze.
