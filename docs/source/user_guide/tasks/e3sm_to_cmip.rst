.. _task-e3sm-to-cmip:

e3sm_to_cmip — CMIP6 Conversion
=================================

The ``e3sm_to_cmip`` task converts E3SM output to CMIP6-compliant format
using the ``e3sm_to_cmip`` package. It depends on the :doc:`ts` task to
provide input time-series files. Its output is consumed by :doc:`ilamb`
and :doc:`pcmdi_diags`.

Parameters
----------

These 6 parameters are specific to the ``e3sm_to_cmip`` task.

.. list-table::
   :header-rows: 1
   :widths: 22 10 18 50

   * - Parameter
     - Required
     - Default
     - Description
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

Parameters at the top-level
~~~~~~~~~~~~~~~~~~~~~~~~~~~

For top-level parameters, see :ref:`top-level parameters <parameters-top-level>`.

Dependencies
------------

**Upstream (what e3sm_to_cmip depends on):**

- :doc:`ts` — Monthly-atm ts: monthly-atm e3sm_to_cmip. Monthly-lnd ts: monthly-lnd e3sm_to_cmip.

**Downstream (what depends on e3sm_to_cmip):**

- :doc:`ilamb` — Monthly-lnd e3sm_to_cmip: required. Monthly-atm e3sm_to_cmip: optional.
- :doc:`pcmdi_diags` — Monthly-atm e3sm_to_cmip: mean_climate, variability_modes_atm,variability_modes_cpl, enso
