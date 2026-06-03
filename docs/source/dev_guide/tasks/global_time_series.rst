.. _dev-task-global-time-series:

global_time_series (Developer Reference)
==========================================

Implementation
--------------

- **Python module**: ``zppy/global_time_series.py``
- **Template**: ``zppy/templates/global_time_series.bash`` and
  ``zppy/templates/coupled_global.py``

Unlike ``e3sm_diags`` and ``mpas_analysis``, the Global Time Series
functionality is **built into** ``zppy`` rather than calling an external
package. The main plotting logic lives in ``coupled_global.py``.

Adding new plots
~~~~~~~~~~~~~~~~

See :doc:`../new_glb_plot` for a step-by-step guide to adding new global
time series plots.

The plot registry is in ``PLOT_DICT`` in ``coupled_global.py``. Each entry
maps a short name (used in ``plots_original``) to a function named
``plot_<name>``.

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
