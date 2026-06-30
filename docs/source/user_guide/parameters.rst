.. _parameters:

***************
Parameters
***************

Parameters make use of inheritance. Parameters set in ``[default]`` can
be overridden by parameters set in a ``[section]``, which can themselves
be overridden by parameters set in a ``[[subsection]]``.

.. warning::
   Note that some parameters will be overridden by defaults if you define them too high up in the inheritance hierarchy.

See `this release's parameter defaults <https://github.com/E3SM-Project/zppy/blob/885d53cb989119d77a21b4f25fe6109fc74a043e/zppy/defaults/default.ini>`_
on GitHub for a complete list of parameters and their default values.
You can also view the most up-to-date,
`unreleased parameter defaults <https://github.com/E3SM-Project/zppy/blob/main/zppy/defaults/default.ini>`_.

Parameters for individual tasks
===============================

For per-task parameter tables, see the :ref:`Tasks <user-tasks>` section.

.. _parameters-top-level:

Parameters at the top-level
===========================

These parameters appear in the top-level ``[default]`` section of ``zppy/defaults/default.ini``. They can be overridden in individual tasks and subtasks.

There are 38 (non-deprecated) parameters that can be defined at the top level.

**Input specifics**

There are 2 input-specific parameters:

.. list-table::
   :header-rows: 1
   :widths: 22 10 18 50

   * - Parameter
     - Required
     - Default
     - Description
   * - ``case``
     - **Yes**
     - *(none)*
     - The case name of the simulation.
   * - ``input``
     - **Yes**
     - *(none)*
     - The top-level directory of the simulation output to post-process.

**Output specifics**

There are 6 output-specific parameters:

.. list-table::
   :header-rows: 1
   :widths: 22 10 18 50

   * - Parameter
     - Required
     - Default
     - Description
   * - ``output``
     - **Yes**
     - *(none)*
     - Where the post-processing results (``post/`` directory) should go.
   * - ``www``
     - **Yes**
     - *(none)*
     - Where the post-processing visuals should go (to be viewed online).
   * - ``campaign``
     - No
     - ``"none"``
     - Specify which campaign you are running. Campaigns can be found in ``zppy/defaults``. Possible campaigns include ``cryosphere`` and ``water_cycle``.
   * - ``debug``
     - No
     - ``False``
     - Set to True to have ``zppy`` produce more verbose output and retain temporary workdirs. This is helpful for debugging.
   * - ``dry_run``
     - No
     - ``False``
     - This should be set to True if you don't want the batch jobs to be submitted. I.e., you only want to see what *would* be submitted.
   * - ``fail_on_dependency_skip``
     - No
     - ``False``
     - If set to False, zppy will launch other jobs, if possible.

**Machine specifics**

There are 8 machine-specific parameters:

.. list-table::
   :header-rows: 1
   :widths: 22 10 18 50

   * - Parameter
     - Required
     - Default
     - Description
   * - ``account``
     - No
     - ``""``
     - SLURM account to charge.
   * - ``constraint``
     - No
     - ``""``
     - The constraint of the machine to run on.
   * - ``nodes``
     - No
     - ``1``
     - Number of compute nodes.
   * - ``parallel``
     - No
     - ``"mpi"``
     - The ``parallel`` option passed to ``ncclimo``.
   * - ``partition``
     - No
     - ``""``
     - SLURM partition to submit the job to.
   * - ``qos``
     - No
     - ``"regular"``
     - Quality of service
   * - ``reservation``
     - No
     - ``""``
     - If you have access to a node reservation, specify it here.
   * - ``walltime``
     - No
     - ``"02:00:00"``
     - Maximum wall time for the SLURM job.

**Environment specifics**

There are 3 environment-specific parameters:

.. list-table::
   :header-rows: 1
   :widths: 22 10 18 50

   * - Parameter
     - Required
     - Default
     - Description
   * - ``environment_commands``
     - No
     - ``""``
     - Shell commands to set up the software environment before running the
       task (e.g., ``source /path/to/e3sm_unified.sh``).
   * - ``environment_commands_secondary``
     - No
     - ``""``
     - Shell commands to set up the *secondary* software environment before running the task (e.g., ``source /path/to/e3sm_unified.sh``). This is currently only used for the ``pcmdi_diags`` task.
   * - ``nco_path``
     - No
     - ``""``
     - Keep as the empty string to use production-version NCO commands. Set to the development-version path to use that instead.

**Inference specifics**

There are 2 inference-specific parameters. See "Parameter checking & inferring" below for more info.

.. list-table::
   :header-rows: 1
   :widths: 22 10 18 50

   * - Parameter
     - Required
     - Default
     - Description
   * - ``infer_path_parameters``
     - No
     - ``True``
     - If true, infer file paths not given. 
   * - ``infer_section_parameters``
     - No
     - ``True``
     - If true, infer dependencies not given.

**Dependency specifics**

There are 7 dependency-specific parameters. See :ref:`Dependencies <dependency_graph>` for more info on which tasks depend on which.

.. list-table::
   :header-rows: 1
   :widths: 22 10 18 50

   * - Parameter
     - Required
     - Default
     - Description
   * - ``ts_atm_grid``
     - No
     - ``"180x360_aave"``
     - Grid name of the atmosphere ``[ts]`` subtask.
   * - ``ts_atm_subsection``
     - No
     - ``""``
     - Name of the ``[ts]`` atmosphere subtask (for multi-component runs).
   * - ``ts_grid``
     - No
     - ``"180x360_aave"``
     - Grid name of the ``[ts]`` subtask to depend on.
   * - ``ts_land_grid``
     - No
     - ``"180x360_aave"``
     - Grid name of the land ``[ts]`` subtask.
   * - ``ts_land_subsection``
     - No
     - ``""``
     - Name of the ``[ts]`` land subtask (for multi-component runs).
   * - ``ts_num_years``
     - No
     - ``5``
     - Years increment from the dependent ``[ts]`` task.
   * - ``ts_subsection``
     - No
     - ``""``
     - Name of the ``[ts]`` subtask to depend on. If empty and
       ``infer_section_parameters`` is ``True``, inferred from the
       subsection name.

**Task specifics**

There are 10 task-specific parameters:

.. list-table::
   :header-rows: 1
   :widths: 22 10 18 50

   * - Parameter
     - Required
     - Default
     - Description
   * - ``active``
     - No
     - ``False``
     - Set to ``True`` to enable this task.
   * - ``bundle``
     - No
     - ``""``
     - (Set on individual tasks) Name of the bundle to include this task
       in.
   * - ``frequency``
     - No
     - ``"monthly"``
     - The frequency of the data. Options include "monthly", "diurnal_8xdaily", "daily".
   * - ``grid``
     - No
     - ``""``
     - Name of the output grid (e.g., ``180x360_aave``). Used for naming
       output directories.
   * - ``input_files``
     - No
     - ``"eam.h0"``
     - Pattern matching the input history files (e.g., ``eam.h0``,
       ``eam.h1``).
   * - ``input_subdir``
     - No
     - ``"archive/atm/hist"``
     - Subdirectory under ``input``/``case`` containing the data files.
   * - ``mapping_file``
     - No
     - ``""``
     - Path to the mapping (regridding) file. Leave empty for no regridding.
   * - ``plugins``
     - No
     - ``""``
     - External zppy plugin modules
   * - ``vars``
     - No
     - ``"FSNTOA,FLUT,FSNT,FLNT,FSNS,FLNS,SHFLX,QFLX,TAUX,TAUY,PRECC,PRECL,PRECSC,PRECSL,TS,TREFHT,CLDTOT,CLDHGH,CLDMED,CLDLOW,U,PSL"``
     - Variables to process. An empty string processes all variables.
   * - ``years``
     - No
     - ``[""]``
     - Year ranges to process. Format: ``"start:end:increment"`` (e.g.,
       ``"1:100:20"``).

**Deprecated Parameters**

There is 1 deprecated parameter. Specifying it will have no effect.

.. code-block:: text

   ncclimo_cmd

Parameter checking & inferring
==============================

There are two types of inferences, each with their own parameter in ``default.ini``:

* ``infer_path_parameters``: infer paths that are not explicitly provided in the configuration file. Default is ``True``.
* ``infer_section_parameters``: infer subtask dependency names that are not explicitly provided in the configuration file. Default is ``True``.

**Section inferences**

For the ``climo``, ``ts``, ``e3sm_to_cmip``, and ``e3sm_diags`` tasks:

* If ``subsection`` (the name of the subtask) is undefined, just use the value of ``grid``.

For the ``e3sm_to_cmip`` task:

* If ``ts_subsection`` (the name of the ``ts`` subtask that this ``e3sm_to_cmip`` subtask is dependent on) is undefined, assume it had the same name as this ``e3sm_to_cmip`` subtask.

For the ``ilamb`` task:

* If ``ts_land_subsection`` (the name of the ``ts`` land-specific subtask that this ``ilamb`` task is dependent on), assume it is ``land_monthly``.
* If ``e3sm_to_cmip_land_subsection`` (the name of the ``e3sm_to_cmip`` land-specific subtask that this ``ilamb`` task is dependent on), again assume it is ``land_monthly``.
* If we are not doing a ``land_only`` run and ``ts_atm_subsection`` (the name of the ``ts`` atm-specific subtask that this ``ilamb`` task is dependent on), assume it is ``atm_monthly_180x360_aave``.
* If we are not doing a ``land_only`` run and ``e3sm_to_cmip_atm_subsection`` (the name of the ``e3sm_to_cmip`` atm-specific subtask that this ``ilamb`` task is dependent on), again assume it is ``atm_monthly_180x360_aave``.


For the ``livvkit`` task:

* A grid-native climatology must be generated, assumed to be ``land_monthly_climo_native``
* For each reanalysis comparison to be performed, a corresponding ``land_monthly_climo_GRID`` where ``GRID`` corresponds to the reanalysis grid name
* Available reanalysis comparisons are
   * racmo_gis, racmo_ais
   * merra2
   * era5
   * ceres (default cmip6 grid)

**Path inferences**

For the ``e3sm_diags`` task:

* If ``reference_data_path`` (the path to the reference data) is undefined, assume it is the ``diagnostics_base_path`` from Mache plus ``/observations/Atm/climatology/``. (So, it is important to change this for model-vs-model runs).


For the ``mpas_analysis`` task:

* ``reference_data_path`` and ``test_data_path`` are optional and are only used for model-vs-model comparisons.
  If provided, ``zppy`` uses them to locate the MPAS-Analysis config files from a *previous* MPAS-Analysis run and passes those through to MPAS-Analysis as ``controlRunConfigFile`` (reference) and ``mainRunConfigFile`` (test).

  The comparison type of the *current* MPAS-Analysis run is inferred implicitly:
  if ``reference_data_path`` is set, the run is treated as model-vs-model (``mvm``);
  otherwise it is treated as model-vs-observations (``mvo``). Users normally do
  not need to set a comparison type for the current run.

  .. note::

      These parameter names are intentionally consistent with the terminology used by ``e3sm_diags`` for model-vs-model runs: in both cases, ``reference_data_path`` identifies the *reference simulation's zppy-generated outputs*.

      The practical difference is what each downstream tool consumes:
      ``e3sm_diags`` needs ``reference_data_path`` to be the specific directory containing the reference climatology files (typically under the reference run's ``post/.../clim`` tree), whereas ``mpas_analysis`` needs to find the reference MPAS-Analysis config file.
      For MPAS-Analysis, ``zppy`` resolves the config file when ``reference_data_path`` points to the prior run's zppy output directory (the one containing ``post/``).

      ``reference_data_path`` is intended to point to the prior run's zppy output directory (the one containing ``post/``). ``zppy`` will then use:
      ``<reference_data_path>/post/analysis/mpas_analysis/<comparison_type>/cfg/mpas_analysis_<identifier>.cfg``
      where ``<comparison_type>`` is ``mvo`` or ``mvm``.

      For referenced prior runs, ``reference_comparison_type`` and
      ``test_comparison_type`` can be set to ``"auto"``, ``"mvo"``, or ``"mvm"``.
      The default is ``"auto"``. In auto mode:

      * if the path points to ``[[subsection]]``, zppy uses the referenced subsection's actual comparison type
      * if the path points to an external zppy output directory, zppy looks for the matching cfg under ``mvo`` and ``mvm``
      * if both exist for the same identifier, zppy raises an error and the user should set ``reference_comparison_type`` or ``test_comparison_type`` explicitly

      When ``reference_data_path`` is set to a non-subsection path, ``reference_case`` is required so the MVM output directory can include the reference case name. If ``reference_data_path`` is set to ``[[subsection]]``, ``reference_case`` is inferred to be the same as the current ``case``.


**MPAS-Analysis model-vs-model year ranges**

MPAS-Analysis comparisons are configured by year ranges, similar to other ``zppy`` tasks.
For model-vs-model comparisons, ``zppy`` supports separate year ranges for the test and reference runs:

* ``ts_years``, ``climo_years``, ``enso_years`` define the test run year ranges.
   If ``test_data_path`` references a prior ``[mpas_analysis]`` subsection using
   ``[[subsection]]``, and these values are not provided, zppy uses that
   subsection's year ranges instead.
* ``ref_ts_years``, ``ref_climo_years``, ``ref_enso_years`` optionally override the reference run year ranges.

If a ``ref_*_years`` parameter is not provided, it defaults to the corresponding test year ranges.
If ``reference_data_path`` references a prior ``[mpas_analysis]`` subsection using ``[[subsection]]``,
the defaults come from that subsection's year ranges instead.
If a ``ref_*_years`` parameter contains a single range and multiple test ranges are requested, the single reference range is used for each test range.


For the ``ilamb`` task:

* If ``ilamb_obs`` (the path to observation data for ``ilamb``) is undefined, assume it is the ``diagnostics_base_path`` from Mache plus ``/ilamb_data``.

Deprecated parameters
=====================

The following ``zppy`` parameters no longer perform any function.

These are no longer defined in ``zppy/defaults/default.ini``:

.. code-block:: text

   e3sm_to_cmip_environment_commands
   ts_fmt
   scratch
   atmosphere_only
   plot_names
   vars_exclude

These are still defined in ``zppy/defaults/default.ini``, but have no effect:

.. code-block:: text
   ncclimo_cmd
   nrows
   ncols
