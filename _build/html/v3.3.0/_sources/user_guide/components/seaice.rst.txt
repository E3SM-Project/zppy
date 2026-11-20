.. _component-seaice:

Sea Ice — MPAS-seaice
======================

**MPAS-seaice** is E3SM's sea-ice model, also based on the MPAS framework
and running on the same unstructured mesh as MPAS-Ocean.

Relevant zppy tasks
-------------------

- :doc:`../tasks/mpas_analysis` — primary task for sea-ice diagnostics
- :doc:`../tasks/global_time_series` — sea-ice global time series plots

MPAS-Analysis for sea ice
--------------------------

MPAS-Analysis includes a suite of sea-ice diagnostics. These run
automatically alongside ocean diagnostics when ``[mpas_analysis]`` is
active. Sea-ice analyses can be controlled via the ``generate`` parameter:

.. code-block:: cfg

   [mpas_analysis]
   active = True
   # To disable specific sea-ice analyses:
   generate = all, no_icebergs, no_landIceCavities

Key MPAS-seaice-specific parameters:

- ``mpassi_nml``: name of the MPAS sea-ice namelist file (default:
  ``mpassi_in``)
- ``stream_ice``: name of the MPAS sea-ice streams file (default:
  ``streams.seaice``)

Global time series sea-ice plots
---------------------------------

The ``[global_time_series]`` task can produce sea-ice time series plots when
``make_viewer = True``. Use the ``plots_ice`` parameter to specify which
sea-ice variables to include.

Notes for MPAS-seaice developers
---------------------------------

- Sea-ice and ocean analyses share the same ``[mpas_analysis]`` section.
  They are differentiated internally by MPAS-Analysis based on the
  ``generate`` list.
- ``icebergs`` and ``landIceCavities`` are disabled by default in the
  standard ``generate`` list because most E3SM configurations do not include
  these features. Enable them if your simulation does.
- The ``anomalyRefYear`` parameter sets the reference year for anomaly
  plots in MPAS-Analysis. For historical simulations, this is typically
  set to the first year of the observational record.
