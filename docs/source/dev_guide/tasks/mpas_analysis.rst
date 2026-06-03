.. _dev-task-mpas-analysis:

mpas_analysis (Developer Reference)
=====================================

Implementation
--------------

- **Python module**: ``zppy/mpas_analysis.py``
- **Jinja2 template**: ``zppy/templates/mpas_analysis.bash``

The ``mpas_analysis`` module generates one SLURM job per combination of
year range (from ``ts_years``, ``climo_years``, ``enso_years``) and
subsection.

Model-vs-model logic
~~~~~~~~~~~~~~~~~~~~

When ``reference_data_path`` is set, the run is treated as MVM. The module
locates MPAS-Analysis config files from prior runs:

.. code-block:: text

   <reference_data_path>/post/analysis/mpas_analysis/<comparison_type>/cfg/
     mpas_analysis_<identifier>.cfg

``comparison_type`` is either ``mvo`` or ``mvm``. In ``auto`` mode:

- If only one type is found, that type is used.
- If both are found, an error is raised and the user must set
  ``reference_comparison_type`` or ``test_comparison_type`` explicitly.
- If ``reference_data_path`` points to a ``[[subsection]]``, zppy uses
  that subsection's actual comparison type.

Dependencies
------------

**Upstream:**

- None required. MPAS-Analysis reads MPAS-Ocean and MPAS-seaice output
  directly from the simulation archive.

**Downstream (optional):**

- :doc:`global_time_series` — can optionally depend on MPAS-Analysis output
  for ocean/sea-ice time series plots
