.. _component-rivers:

Rivers — MOSART
================

**MOSART** (Model for Scale Adaptive River Transport) is E3SM's river
routing component. It routes runoff from ELM through river networks to
the ocean.

Relevant zppy tasks
-------------------

- :doc:`../tasks/ts` — generate river time-series files
- :doc:`../tasks/e3sm_diags` — streamflow diagnostics (``streamflow`` set)

MOSART time-series configuration
---------------------------------

MOSART output is in monthly ``mosart.h0`` files. Configuration example:

.. code-block:: cfg

   [ts]
   active = True

     [[rof_monthly]]
     input_files = mosart.h0
     input_subdir = archive/rof/hist
     input_component = mosart
     years = 1:100:10

E3SM Diags streamflow set
--------------------------

The ``streamflow`` set in ``e3sm_diags`` compares MOSART-simulated
streamflow against stream gauge observations. It requires:

1. A river time-series subtask in ``[ts]``
2. The ``streamflow_obs_ts`` parameter pointing to observational gauge data

Example configuration:

.. code-block:: cfg

   [ts]
     [[rof_monthly]]
     input_files = mosart.h0
     input_subdir = archive/rof/hist
     input_component = mosart
     years = 1:100:10

   [e3sm_diags]
     [[streamflow_diags]]
     sets = streamflow
     ts_subsection = rof_monthly
     streamflow_obs_ts = /path/to/obs/streamflow
     # For model-vs-model:
     # run_type = model_vs_model
     # reference_data_path_ts_rof = /path/to/reference/post/atm/...
     # gauges_path = /path/to/gauges.nc

Notes for MOSART developers
----------------------------

- The ``input_component = mosart`` parameter tells ``zppy`` how to
  handle MOSART output files.
- River routing output can differ between E3SM configurations, so
  the ``input_files`` stream name (``mosart.h0``) should be verified
  for your specific simulation.
