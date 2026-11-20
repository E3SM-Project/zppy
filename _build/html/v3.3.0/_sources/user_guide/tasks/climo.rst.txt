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

These 3 parameters are specific to the ``climo`` task:

.. list-table::
   :header-rows: 1
   :widths: 22 10 18 50

   * - Parameter
     - Required
     - Default
     - Description
   * - ``exclude``
     - No
     - ``False``
     - Set to ``True`` to exclude this subtask from running (subsection-level).
   * - ``climo_jobs``
     - No
     - ``0``
     - Number of simultaneous ``ncclimo`` jobs. ``0`` uses ``ncclimo``'s
       default.
   * - ``input_component``
     - No
     - ``""``
     - Model component that generated the input files (e.g., ``eam``,
       ``eamxx``, ``elm``, ``mosart``). Used to set processing type
       internally.


Parameters at the top-level
~~~~~~~~~~~~~~~~~~~~~~~~~~~

These 3 parameters have ``climo``-specific defaults, which means even if they are set at the top level (``[default]``) section, these default values will be used instead. Therefore, to specify a custom value, these parameters must be defined inside ``[climo]``:

.. list-table::
   :header-rows: 1
   :widths: 22 10 18 50

   * - Parameter
     - Required
     - Default
     - Description
   * - ``parallel``
     - No
     - ``"mpi"``
     - The ``parallel`` option passed to ``ncclimo``.
       Overrides the ``[default]`` value (which is ``""``).
   * - ``nodes``
     - No
     - ``4``
     - Number of compute nodes. Overrides the ``[default]`` value (``1``).
   * - ``vars``
     - No
     - ``""``
     - Variables to process. An empty string processes *all* variables (no
       ``-v`` flag is passed to ``ncclimo``). Overrides the ``[default]``
       value.

For other top-level parameters, see :ref:`top-level parameters <parameters-top-level>`.

Dependencies
------------

**Upstream (what climo depends on):**

- None

**Downstream (what depends on climo):**

- :doc:`e3sm_diags` — Monthly-atm climo: lat_lon, zonal_mean_xy, zonal_mean_2d, polar, cosp_histogram, meridional_mean_2d, annual_cycle_zonal_mean, zonal_mean_2d_stratosphere, aerosol_aeronet, aerosol_budget. Monthly-lnd climo: lat_lon_land. Monthly diurnal-atm climo: diurnal_cycle
- :doc:`livvkit` — Monthly-lnd climo
