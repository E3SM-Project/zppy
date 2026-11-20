.. _component-ocean:

Ocean — MPAS-Ocean
===================

**MPAS-Ocean** is E3SM's ocean model, based on the Model for Prediction
Across Scales (MPAS) framework. It uses an unstructured mesh that allows
variable horizontal resolution.

Relevant zppy tasks
-------------------

- :doc:`../tasks/mpas_analysis` — ocean and sea-ice analysis (primary task)
- :doc:`../tasks/global_time_series` — ocean global time series plots

MPAS-Analysis for ocean
------------------------

MPAS-Analysis is the primary tool for MPAS-Ocean diagnostics. It operates
on MPAS-Ocean's native unstructured mesh. The ``[mpas_analysis]`` task in
``zppy`` calls MPAS-Analysis automatically.

Typical ``[mpas_analysis]`` configuration:

.. code-block:: cfg

   [mpas_analysis]
   active = True
   walltime = 06:00:00
   shortTermArchive = True
   ts_years = 1:100:50
   climo_years = 1:100:50
   enso_years = 1:100:50
   generate = all, no_landIceCavities, no_BGC, no_icebergs, no_min, no_max

Key MPAS-Ocean-specific parameters:

- ``mpaso_nml``: name of the MPAS-Ocean namelist file (default: ``mpaso_in``)
- ``stream_ocn``: name of the MPAS-Ocean streams file (default: ``streams.ocean``)
- ``PostMOC``: whether to post-process MOC (meridional overturning
  circulation) data

Model-vs-model ocean comparisons
---------------------------------

MPAS-Analysis supports comparing two model simulations. In ``zppy``, this
is configured via ``reference_data_path``:

.. code-block:: cfg

   [mpas_analysis]

     [[main_run]]
     ts_years = 1:100:50
     climo_years = 1:100:50

     [[mvm_run]]
     ts_years = 1:100:50
     climo_years = 1:100:50
     reference_data_path = [[main_run]]
     # or: reference_data_path = /path/to/prior/zppy/output

See the :doc:`../tasks/mpas_analysis` page and the :ref:`tutorial <tutorial>`
for a complete model-vs-model example.

Global time series ocean plots
-------------------------------

The ``[global_time_series]`` task can produce ocean time series plots such
as:

- ``change_ohc`` — ocean heat content change
- ``max_moc`` — maximum meridional overturning circulation
- ``change_sea_level`` — global mean sea level change

These require access to MPAS-Ocean output. The ``input_subdir`` in
``[global_time_series]`` should be set to ``archive/ocn/hist`` (the default).

Notes for MPAS-Ocean developers
---------------------------------

- The ``generate`` parameter in ``[mpas_analysis]`` controls which
  MPAS-Analysis tasks to run. Use ``no_*`` filters to exclude irrelevant
  analyses for your simulation (e.g., ``no_BGC`` if biogeochemistry is not
  enabled, ``no_landIceCavities`` if land ice cavities are not used).
- The ``environment_commands`` for ``[mpas_analysis]`` must be consistent
  across all year-range runs. Mixing environments can cause MPAS-Analysis to
  fail.
- MPAS-Analysis caches intermediate results (``cache = True`` by default).
  Set ``purge = True`` to clear previous output and start fresh.
