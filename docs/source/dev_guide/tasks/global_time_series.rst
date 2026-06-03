.. _dev-task-global-time-series:

global_time_series (Developer Reference)
==========================================

Implementation
--------------

- **Python module**: ``zppy/global_time_series.py``
- **Template**: ``zppy/templates/global_time_series.bash``


``global_time_series`` is called through the ``zppy-interfaces`` entry-point.

Dependencies
------------

**Upstream (required):**

- :doc:`ts` — depends on ``[ts]`` global-mean subtasks for atmospheric,
  land, and (optionally) ocean/sea-ice data

**Upstream (optional):**

- :doc:`mpas_analysis` — depends on MPAS-Analysis output for ocean and
  sea-ice time series plots. Specified via ``mpas_analysis_subsections``.

**Downstream:**

- None.
