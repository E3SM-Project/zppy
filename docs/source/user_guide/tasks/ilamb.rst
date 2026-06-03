.. _task-ilamb:

ilamb — Land Benchmarking
==========================

The ``ilamb`` task runs `ILAMB <https://www.ilamb.org/>`_ (International
Land Model Benchmarking) to evaluate E3SM's land component against
observational benchmarks. It depends on the :doc:`e3sm_to_cmip` task to
provide CMIP-format land and atmosphere time-series files.

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
   * - ``cfg``
     - No
     - ``"inclusions/ilamb/ilamb.cfg"``
     - Path to the ILAMB configuration file.
   * - ``e3sm_to_cmip_atm_subsection``
     - No
     - ``""``
     - Name of the ``[e3sm_to_cmip]`` atmosphere subtask to depend on.
       Inferred as ``atm_monthly_180x360_aave`` if not specified.
   * - ``e3sm_to_cmip_land_subsection``
     - No
     - ``""``
     - Name of the ``[e3sm_to_cmip]`` land subtask to depend on. Inferred
       as ``land_monthly`` if not specified.
   * - ``ilamb_obs``
     - No
     - ``""``
     - Path to ILAMB observational data. Defaults to
       ``diagnostics_base_path/ilamb_data`` if empty.
   * - ``land_only``
     - No
     - ``False``
     - Set to ``True`` for land-only runs (skips atmosphere dependencies).
   * - ``ts_atm_subsection``
     - No
     - ``""``
     - Name of the ``[ts]`` atmosphere subtask to depend on. Inferred as
       ``atm_monthly_180x360_aave`` if not specified and not a land-only run.
   * - ``ts_land_subsection``
     - No
     - ``""``
     - Name of the ``[ts]`` land subtask to depend on. Inferred as
       ``land_monthly`` if not specified.

Dependency inference
--------------------

When ``infer_section_parameters = True`` (the default), ``zppy`` will
automatically determine the following if not explicitly set:

- ``ts_land_subsection`` defaults to ``land_monthly``
- ``e3sm_to_cmip_land_subsection`` defaults to ``land_monthly``
- ``ts_atm_subsection`` defaults to ``atm_monthly_180x360_aave`` (for
  non-land-only runs)
- ``e3sm_to_cmip_atm_subsection`` defaults to ``atm_monthly_180x360_aave``
  (for non-land-only runs)
