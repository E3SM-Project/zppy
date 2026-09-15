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
- ``enso`` — ENSO metrics
- ``synthetic_plots`` — composite viewer page combining outputs from other sets

Parameters
----------

These 71 parameters are specific to the ``pcmdi_diags`` task.

Task-level parameters (all sets)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There are 6 task-level (all sets) parameters:

.. list-table::
   :header-rows: 1
   :widths: 28 10 18 44

   * - Parameter
     - Required
     - Default
     - Description
   * - ``figure_format``
     - No
     - ``"png"``
     - Output figure format.
   * - ``run_type``
     - No
     - ``"model_vs_obs"``
     - ``"model_vs_obs"`` or ``"model_vs_model"``.
   * - ``model_name``
     - No
     - ``"e3sm.historical.v3-LR.0051"``
     - Model name (required for model-vs-observations runs).
   * - ``model_tableID``
     - No
     - ``"Amon"``
     - CMIP table ID (required for model-vs-observations runs).
   * - ``model_name_ref``
     - No
     - ``"ERA5"``
     - Reference model name (required for model-vs-model runs).
   * - ``model_tableID_ref``
     - No
     - ``"Amon"``
     - Reference CMIP table ID (required for model-vs-model runs).

Task-level parameters (all sets except synthetic_plots)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There are 14 task-level (all sets except synthetic_plots) parameters:

.. list-table::
   :header-rows: 1
   :widths: 28 10 18 44

   * - Parameter
     - Required
     - Default
     - Description
   * - ``e3sm_to_cmip_atm_subsection``
     - No
     - ``""``
     - Name of the ``[e3sm_to_cmip]`` atmosphere subtask to depend on.
   * - ``generate_sftlf``
     - No
     - ``True``
     - Process the land/sea mask within PCMDI.
   * - ``mov_plot_obs``
     - No
     - ``True``
     - Generate variability-modes observation plots.
   * - ``mov_plot_model``
     - No
     - ``True``
     - Generate variability-modes model plots.
   * - ``mov_nc_out_obs``
     - No
     - ``True``
     - Write variability-modes observation NetCDF output.
   * - ``mov_nc_out_model``
     - No
     - ``True``
     - Write variability-modes model NetCDF output.
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
     - Path to observation time-series data.
   * - ``pcmdi_debug``
     - No
     - ``False``
     - Enable debug mode in PCMDI diagnostics.
   * - ``save_test_clims``
     - No
     - ``True``
     - Save derived test climatology data.
   * - ``reference_data_path``
     - No
     - ``""``
     - Path to reference model data for model-vs-model runs.
   * - ``reference_data_path_ts``
     - No
     - ``""``
     - Path to reference model time-series data for model-vs-model runs.
   * - ``ts_years``
     - No
     - ``[""]``
     - Year ranges for test model data.

Per-subtask shared parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There are 8 per-subtask shared parameters:

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
     - Diagnostic set to run.
   * - ``clim_obs_sets``
     - No
     - ``"default"``
     - Observational dataset alias for mean-climate diagnostics.
   * - ``enso_obs_sets``
     - No
     - ``"alternate3,default,alternatd4,..."``
     - Per-variable observational dataset aliases for ENSO diagnostics.
   * - ``mova_obs_sets``
     - No
     - ``"alternate4"``
     - NOAA-20C alias for atmospheric variability modes.
   * - ``movc_obs_sets``
     - No
     - ``"alternatd4"``
     - HadISST2 alias for coupled variability modes.
   * - ``ref_final_yr``
     - No
     - ``""``
     - End year for reference data.
   * - ``ref_start_yr``
     - No
     - ``""``
     - Start year for reference data.
   * - ``ref_years``
     - No
     - ``[""]``
     - Year ranges for reference data.

For non-synthetic subtasks, zppy selects the diagnostic-specific observation
alias based on ``current_set`` and passes it downstream as ``obs_sets``.
When a selector contains a comma-separated list, its entries correspond
positionally to the associated ``*_vars`` parameter.

Mean_climate parameters
~~~~~~~~~~~~~~~~~~~~~~~

There are 7 mean_climate parameters:

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
     - CMIP variables to include for mean-climate diagnostics.
   * - ``target_grid``
     - No
     - ``"1x1"``
     - Target regridding grid.
   * - ``target_grid_string``
     - No
     - ``"1px1p"``
     - Descriptor string for the target grid.
   * - ``regrid_tool``
     - No
     - ``"esmf"``
     - Regridding tool for atmosphere fields.
   * - ``regrid_tool_ocn``
     - No
     - ``"esmf"``
     - Regridding tool for ocean fields.
   * - ``regrid_method``
     - No
     - ``"regrid2"``
     - Regridding method for atmosphere fields.
   * - ``regrid_method_ocn``
     - No
     - ``"conservative"``
     - Regridding method for ocean fields.

Mean_climate & synthetic_plots parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There are 2 mean_climate & synthetic_plots parameters:

.. list-table::
   :header-rows: 1
   :widths: 28 10 18 44

   * - Parameter
     - Required
     - Default
     - Description
   * - ``clim_vars``
     - No
     - ``"pr,prw,psl,..."``
     - Variables for mean-climate and synthetic-plot diagnostics.
   * - ``clim_regions``
     - No
     - ``"global,ocean,land"``
     - Regions used for mean-climate metrics.

Variability_modes parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There are 9 variability_modes parameters:

.. list-table::
   :header-rows: 1
   :widths: 28 10 18 44

   * - Parameter
     - Required
     - Default
     - Description
   * - ``CBF``
     - No
     - ``True``
     - Use Common Base Function approach.
   * - ``ConvEOF``
     - No
     - ``True``
     - Compute conventional EOF.
   * - ``eofn_mod_max``
     - No
     - ``3``
     - Maximum number of EOF modes for model data.
   * - ``EofScaling``
     - No
     - ``False``
     - Apply EOF scaling.
   * - ``landmask``
     - No
     - ``False``
     - Apply land-mask handling in variability diagnostics.
   * - ``ModUnitsAdjust``
     - No
     - ``""``
     - Unit-adjustment keywords for model data.
   * - ``ObsUnitsAdjust``
     - No
     - ``""``
     - Unit-adjustment keywords for observation data.
   * - ``RmDomainMean``
     - No
     - ``True``
     - Remove domain mean before variability calculations.
   * - ``seasons``
     - No
     - ``"monthly"``
     - Seasons/frequency bins to analyze.

Variability_modes & synthetic_plots parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There are 4 variability_modes & synthetic_plots parameters:

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

ENSO parameters
~~~~~~~~~~~~~~~

There is 1 ENSO parameter:

.. list-table::
   :header-rows: 1
   :widths: 28 10 18 44

   * - Parameter
     - Required
     - Default
     - Description
   * - ``enso_groups``
     - No
     - ``"ENSO_perf,ENSO_proc,ENSO_tel"``
     - ENSO metric groups to run.

ENSO & synthetic_plots parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There is 1 ENSO & synthetic_plots parameter:

.. list-table::
   :header-rows: 1
   :widths: 28 10 18 44

   * - Parameter
     - Required
     - Default
     - Description
   * - ``enso_vars``
     - No
     - ``"psl,pr,ts,tas,tauu,tauv,hfls,hfss,rlds,rsds,rlus,rlut,rsdt"``
     - Variables used by ENSO diagnostics.

Sea-surface height is opt-in because an ``ssh`` model time series is not
generally available in the atmospheric CMIP time-series directory. To include
it, append ``ssh`` to ``enso_vars`` and its observational alias (``default``
for AVISO) to ``enso_obs_sets`` in the same position. The model data must first
be provided as an ``ssh`` time series; ``zppy`` does not translate ``zos`` to
``ssh``.

Synthetic_plots parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~

There are 22 synthetic_plots parameters:

.. list-table::
   :header-rows: 1
   :widths: 28 10 18 44

   * - Parameter
     - Required
     - Default
     - Description
   * - ``clim_viewer``
     - No
     - ``True``
     - Include mean-climate panels in the synthetic viewer.
   * - ``clim_years``
     - No
     - ``""``
     - Year range used for mean-climate synthetic panels.
   * - ``mova_viewer``
     - No
     - ``True``
     - Include atmospheric variability-mode panels in the synthetic viewer.
   * - ``mova_years``
     - No
     - ``""``
     - Year range used for atmospheric variability synthetic panels.
   * - ``movc_viewer``
     - No
     - ``True``
     - Include coupled variability-mode panels in the synthetic viewer.
   * - ``movc_years``
     - No
     - ``""``
     - Year range used for coupled variability synthetic panels.
   * - ``enso_viewer``
     - No
     - ``True``
     - Include ENSO panels in the synthetic viewer.
   * - ``enso_years``
     - No
     - ``""``
     - Year range used for ENSO synthetic panels.
   * - ``save_all_data``
     - No
     - ``True``
     - Save all intermediate synthetic-diagnostic data.
   * - ``reference_alias``
     - No
     - ``"inclusions/pcmdi_diags/reference_alias.json"``
     - Observation alias file.
   * - ``regions_specs``
     - No
     - ``"inclusions/pcmdi_diags/regions_specs.json"``
     - Region-specification file.
   * - ``pcmdi_version``
     - No
     - ``"v3.8.2"``
     - Version tag for the zppy-pcmdi workflow.
   * - ``pcmdi_viewer_template``
     - No
     - ``"pcmdi_data/viewer"``
     - Template directory for synthetic-viewer generation.
   * - ``pcmdi_webtitle``
     - No
     - ``"E3SM-PMP-Diagnostics"``
     - Title used in generated PCMDI web output.
   * - ``synthetic_metrics_list``
     - No
     - ``"inclusions/pcmdi_diags/synthetic_metrics_list.json"``
     - Metrics-list file used to assemble synthetic plots.
   * - ``synthetic_sets``
     - No
     - ``"portrait,parcoord"``
     - Synthetic plot types to generate.
   * - ``cmip_clim_dir``
     - No
     - ``""``
     - Directory containing CMIP mean-climate metrics.
   * - ``cmip_enso_dir``
     - No
     - ``""``
     - Directory containing CMIP ENSO metrics.
   * - ``cmip_movs_dir``
     - No
     - ``""``
     - Directory containing CMIP variability-mode metrics.
   * - ``cmip_clim_set``
     - No
     - ``"cmip6.historical.v20250707"``
     - CMIP mean-climate metrics set ID.
   * - ``cmip_enso_set``
     - No
     - ``"cmip6.historical.v20210620"``
     - CMIP ENSO metrics set ID.
   * - ``cmip_movs_set``
     - No
     - ``"cmip6.historical.v20220825"``
     - CMIP variability-mode metrics set ID.

Parameters at the top-level
~~~~~~~~~~~~~~~~~~~~~~~~~~~

These 3 parameters have ``pcmdi_diags``-specific defaults, which means even if
they are set at the top level (``[default]``) section, these default values
will be used instead. Therefore, to specify custom values, these parameters
must be defined inside ``[pcmdi_diags]``:

.. list-table::
   :header-rows: 1
   :widths: 28 10 18 44

   * - Parameter
     - Required
     - Default
     - Description
   * - ``grid``
     - No
     - ``"180x360_aave"``
     - Model data grid after remapping. Overrides the ``[default]`` value
       (``""``).
   * - ``ts_num_years``
     - No
     - ``5``
     - Year increment for test model data. Overrides the
       ``[default]`` value (``5``), which in this case is actually the same value.
   * - ``frequency``
     - No
     - ``"mo"``
     - Data frequency for variability-mode calculations. Overrides the
       ``[default]`` value (``"monthly"``).

For other top-level parameters, see :ref:`top-level parameters <parameters-top-level>`.

Dependencies
------------

**Upstream (what pcmdi_diags depends on):**

- :doc:`ts` — Monthly-atm ts: mean_climate, variability_modes_atm,variability_modes_cpl, enso
- :doc:`e3sm_to_cmip` — Monthly-atm e3sm_to_cmip: mean_climate, variability_modes_atm,variability_modes_cpl, enso
- Note that the synthetic_plots set depends on the other sets.

**Downstream (what depends on pcmdi_diags):**

- None.
