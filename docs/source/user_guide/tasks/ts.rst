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

These 9 parameters are specific to the ``ts`` task.

.. list-table::
   :header-rows: 1
   :widths: 22 10 18 50

   * - Parameter
     - Required
     - Default
     - Description
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

Parameters at the top-level
~~~~~~~~~~~~~~~~~~~~~~~~~~~

For top-level parameters, see :ref:`top-level parameters <parameters-top-level>`.


Dependencies
------------

**Upstream (what ts depends on):**

- None.

**Downstream (what depends on ts):**

- :doc:`e3sm_to_cmip` — Monthly-atm ts: monthly-atm e3sm_to_cmip. Monthly-lnd ts: monthly-lnd e3sm_to_cmip.
- :doc:`e3sm_diags` — Monthly-atm ts: enso_diags, qbo, area_mean_time_series, mp_partition. Monthly-rof ts: streamflow. Daily-atm ts: tropical_subseasonal, precip_pdf.
- :doc:`global_time_series` — Monthly-atm-glb ts: the 5 classic atm plots, plots for specific atm variables. Monthly-lnd-glb ts: plots for specific lnd variables.
- :doc:`ilamb` -- Monthly-lnd ts: required. Monthly-atm ts: optional.
- :doc:`livvkit` -- Monthly-lnd ts.
- :doc:`pcmdi_diags` — Monthly-atm ts: mean_climate, variability_modes_atm,variability_modes_cpl, enso
