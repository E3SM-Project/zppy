.. _task-ts:

ts — Time Series Files
======================

The ``ts`` task generates per-variable time-series files from E3SM
simulation output using NCO's ``ncclimo``. It produces one file per variable
covering a specified year range. Time-series files produced by ``ts`` are
required inputs for the :doc:`e3sm_diags`, :doc:`global_time_series`,
:doc:`e3sm_to_cmip`, :doc:`ilamb`, and :doc:`pcmdi_diags` tasks.

Configuration example
---------------------

.. code-block:: cfg

   [ts]
   active = True
   years = 1:100:10

     [[atm_monthly_180x360_aave]]
     input_files = eam.h0
     input_subdir = archive/atm/hist
     mapping_file = /path/to/map_ne30pg2_to_cmip6_180x360_aave.nc
     grid = 180x360_aave
     vars = FSNTOA,FLUT,FSNT,FLNT,FSNS,FLNS,SHFLX,QFLX,TS,TREFHT

     [[land_monthly]]
     input_files = elm.h0
     input_subdir = archive/lnd/hist
     input_component = elm
     mapping_file = /path/to/map_r05_to_cmip6_180x360_aave.nc
     grid = 180x360_aave

Parameters
----------

The following parameters are specific to the ``ts`` task.

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
   * - ``area_nm``
     - No
     - ``"area"``
     - Name of the area variable in the input files.
   * - ``dpf``
     - No
     - ``30``
     - Days per file (for daily or sub-daily data).
   * - ``extra_vars``
     - No
     - ``""``
     - Additional variables to include alongside the primary ``vars`` list.
   * - ``job_nbr``
     - No
     - ``0``
     - Number of simultaneous ``ncclimo`` jobs. ``0`` uses ``ncclimo``'s
       default.
   * - ``tpd``
     - No
     - ``1``
     - Time-steps per day (for sub-daily data, e.g., ``8`` for 3-hourly).
   * - ``input_component``
     - No
     - ``""``
     - Model component that generated the input files (e.g., ``eam``,
       ``eamxx``, ``elm``, ``mosart``). Used to set processing type
       internally.
   * - ``vrt_remap_vars``
     - No
     - ``""``
     - Variables to additionally regrid from model levels to pressure levels
       after generating time-series files. Output is written to a sibling
       ``ts_vrt_remap/`` directory. Empty string disables vertical remapping.
   * - ``vrt_remap_file``
     - No
     - ``""``
     - Path to the target vertical grid file (pressure levels) for
       ``ncremap``. Defaults to a standard file under
       ``diagnostics_base_path`` when empty.
   * - ``vrt_in_file``
     - No
     - ``""``
     - Path to the source vertical coordinate file for ``ncremap``. Required
       for EAMxx (L128 grid). Defaults to a standard file under
       ``diagnostics_base_path`` when ``input_component`` is ``eamxx`` and
       this is left empty.

Inherited common parameters most relevant to ``ts``
---------------------------------------------------

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
   * - ``output``
     - **Yes**
     - *(none)*
     - Where the post-processing results (``post/`` directory) should go.
   * - ``years``
     - No
     - ``[""]``
     - Year ranges to process. Format: ``"start:end:increment"`` (e.g.,
       ``"1:100:10"``).
   * - ``input_files``
     - No
     - ``"eam.h0"``
     - Pattern matching the input history files.
   * - ``input_subdir``
     - No
     - ``"archive/atm/hist"``
     - Subdirectory under ``input``/``case`` containing the data files.
   * - ``mapping_file``
     - No
     - ``""``
     - Path to the mapping (regridding) file. Leave empty for no regridding.
   * - ``grid``
     - No
     - ``""``
     - Name of the output grid (e.g., ``180x360_aave``).
   * - ``vars``
     - No
     - ``"FSNTOA,FLUT,..."``
     - Variables to process. An empty string processes all variables.
   * - ``walltime``
     - No
     - ``"02:00:00"``
     - Maximum wall time for the SLURM job.
   * - ``partition``
     - No
     - ``""``
     - SLURM partition to submit the job to.
   * - ``account``
     - No
     - ``""``
     - SLURM account to charge.
