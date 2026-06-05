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

**Upstream (what global_time_series depends on):**

- :doc:`ts` — Monthly-atm-glb ts: the 5 classic atm plots, plots for specific atm variables. Monthly-lnd-glb ts: plots for specific lnd variables.
- :doc:`mpas_analysis` — Monthly-atm-glb ts: the 3 classic ocn plots, plots for specific ocn variables.

**Downstream (what depends on global_time_series):**

- None.
