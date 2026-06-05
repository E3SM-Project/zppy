.. _task-climo:

climo — Climatology Files
=========================

The ``climo`` task generates climatology files from E3SM simulation output
using NCO's ``ncclimo``. It produces time-averaged files (monthly and/or
seasonal means) over a specified set of years, optionally regridding the
output to a target grid.

Climatology files produced by ``climo`` are required inputs for the
:doc:`e3sm_diags` task.

Configuration example
---------------------

.. code-block:: cfg

   [climo]
   active = True
   nodes = 4
   years = 1:100:20

     [[atm_monthly_180x360_aave]]
     input_files = eam.h0
     input_subdir = archive/atm/hist
     mapping_file = /path/to/map_ne30pg2_to_cmip6_180x360_aave.nc
     grid = 180x360_aave
     vars = FSNTOA,FLUT,FSNT,FLNT,FSNS,FLNS,SHFLX,QFLX,TS,TREFHT,CLDTOT

Parameters
----------

The following parameters are specific to the ``climo`` task. In addition,
all :ref:`common parameters <parameters>` from the ``[default]`` section apply.

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
   * - ``exclude``
     - No
     - ``False``
     - Set to ``True`` to exclude this subtask from running (subsection-level).
   * - ``parallel``
     - No
     - ``"mpi"``
     - The ``parallel`` option passed to ``ncclimo``.
       Overrides the ``[default]`` value (which is ``""``).
   * - ``nodes``
     - No
     - ``4``
     - Number of compute nodes. Overrides the ``[default]`` value (``1``).
   * - ``climo_jobs``
     - No
     - ``0``
     - Number of simultaneous ``ncclimo`` jobs. ``0`` uses ``ncclimo``'s
       default.
   * - ``vars``
     - No
     - ``""``
     - Variables to process. An empty string processes *all* variables (no
       ``-v`` flag is passed to ``ncclimo``). Overrides the ``[default]``
       value.
   * - ``input_component``
     - No
     - ``""``
     - Model component that generated the input files (e.g., ``eam``,
       ``eamxx``, ``elm``, ``mosart``). Used to set processing type
       internally.

Inherited common parameters most relevant to ``climo``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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
       ``"1:100:20"``).
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
   * - ``grid``
     - No
     - ``""``
     - Name of the output grid (e.g., ``180x360_aave``). Used for naming
       output directories.
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
   * - ``environment_commands``
     - No
     - ``""``
     - Shell commands to set up the software environment before running the
       task (e.g., ``source /path/to/e3sm_unified.sh``).

Dependencies
------------

**Upstream (what climo depends on):**

- None

**Downstream (what depends on climo):**

- :doc:`e3sm_diags` — Monthly-atm climo: lat_lon, zonal_mean_xy, zonal_mean_2d, polar, cosp_histogram, meridional_mean_2d, annual_cycle_zonal_mean, zonal_mean_2d_stratosphere, aerosol_aeronet, aerosol_budget. Monthly-lnd climo: lat_lon_land. Monthly dirunal-atm climo: diurnal_cycle
- :doc:`livvkit` — Monthly-lnd climo
