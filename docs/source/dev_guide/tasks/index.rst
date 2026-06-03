.. _dev-tasks:

Tasks (Developer Reference)
============================

This section describes how each ``zppy`` task is implemented, what
templates and Python modules it uses, and what dependencies it has on
other tasks.

.. toctree::
   :maxdepth: 1

   climo
   ts
   e3sm_to_cmip
   e3sm_diags
   mpas_analysis
   global_time_series
   tc_analysis
   ilamb
   livvkit
   pcmdi_diags
   bundle

Dependency overview
-------------------

The diagram below summarizes the typical dependency relationships between
tasks. Arrows indicate "depends on":

.. code-block:: text

   climo ──────────────────────────────────────────► e3sm_diags
   ts ─────────────────────────────────────────────► e3sm_diags
   ts ─────────────────────────────────────────────► e3sm_to_cmip
   ts ─────────────────────────────────────────────► global_time_series
   ts ─────────────────────────────────────────────► pcmdi_diags (via e3sm_to_cmip)
   mpas_analysis ──────────────────────────────────► global_time_series
   e3sm_to_cmip ───────────────────────────────────► ilamb
   e3sm_to_cmip ───────────────────────────────────► pcmdi_diags
   climo ──────────────────────────────────────────► livvkit

All tasks are independent unless they share the above relationships.
