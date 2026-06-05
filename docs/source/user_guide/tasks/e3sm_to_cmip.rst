.. _task-e3sm-to-cmip:

e3sm_to_cmip — CMIP6 Conversion
=================================

The ``e3sm_to_cmip`` task converts E3SM output to CMIP6-compliant format
using the ``e3sm_to_cmip`` package. It depends on the :doc:`ts` task to
provide input time-series files. Its output is consumed by :doc:`ilamb`
and :doc:`pcmdi_diags`.

Parameters
----------

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
   * - ``cmip_metadata``
     - No
     - ``"inclusions/e3sm_to_cmip/default_metadata.json"``
     - Path to the CMIP metadata JSON file.
   * - ``cmip_plevdata``
     - No
     - ``""``
     - Path to pressure-level data NetCDF file. Defaults to a file under
       ``diagnostics_base_path`` when empty.
   * - ``cmip_vars``
     - No
     - ``""``
     - Variables to convert to CMIP format. Leave empty to convert all
       supported variables.
   * - ``input_component``
     - No
     - ``""``
     - Model component (e.g., ``eam``, ``eamxx``, ``elm``).
   * - ``interp_vars``
     - No
     - ``"U,V,T,Q,RELHUM,OMEGA,Z3"``
     - Variables to interpolate to pressure levels during conversion.
   * - ``vrt_in_file``
     - No
     - ``""``
     - Source vertical coordinate file for ``ncremap``. Required for
       EAMxx (L128 grid).
   * - ``ts_subsection``
     - No
     - ``""``
     - Name of the ``[ts]`` subtask to depend on. If empty and
       ``infer_section_parameters`` is ``True``, inferred from the
       subsection name.
   * - ``ts_atm_subsection``
     - No
     - ``""``
     - Name of the ``[ts]`` atmosphere subtask (for multi-component runs).
   * - ``ts_land_subsection``
     - No
     - ``""``
     - Name of the ``[ts]`` land subtask (for multi-component runs).

Inherited common parameters most relevant to ``e3sm_to_cmip``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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
     - The top-level directory of the simulation output.
   * - ``output``
     - **Yes**
     - *(none)*
     - Where the post-processing results go.
   * - ``years``
     - No
     - ``[""]``
     - Year ranges to process.
   * - ``ts_grid``
     - No
     - ``"180x360_aave"``
     - Grid name of the ``[ts]`` subtask to depend on.
   * - ``ts_atm_grid``
     - No
     - ``"180x360_aave"``
     - Grid name of the atmosphere ``[ts]`` subtask.
   * - ``ts_land_grid``
     - No
     - ``"180x360_aave"``
     - Grid name of the land ``[ts]`` subtask.
   * - ``ts_num_years``
     - No
     - ``5``
     - Years increment from the dependent ``[ts]`` task.
   * - ``environment_commands``
     - No
     - ``""``
     - Shell commands to activate the software environment.

Dependencies
------------

**Upstream (what e3sm_to_cmip depends on):**

- :doc:`ts` — Monthly-atm ts: monthly-atm e3sm_to_cmip. Monthly-lnd ts: monthly-lnd e3sm_to_cmip.

**Downstream (what depends on e3sm_to_cmip):**

- :doc:`ilamb` — Monthly-lnd e3sm_to_cmip: required. Monthly-atm e3sm_to_cmip: optional.
- :doc:`pcmdi_diags` — Monthly-atm e3sm_to_cmip: mean_climate, variability_modes_atm,variability_modes_cpl, enso
