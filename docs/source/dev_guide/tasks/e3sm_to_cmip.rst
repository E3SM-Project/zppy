.. _dev-task-e3sm-to-cmip:

e3sm_to_cmip (Developer Reference)
====================================

Implementation
--------------

- **Python module**: ``zppy/e3sm_to_cmip.py``
- **Jinja2 template**: ``zppy/templates/e3sm_to_cmip.bash``

Dependencies
------------

**Upstream (what e3sm_to_cmip depends on):**

- :doc:`ts` — Monthly-atm ts: monthly-atm e3sm_to_cmip. Monthly-lnd ts: monthly-lnd e3sm_to_cmip.

**Downstream (what depends on e3sm_to_cmip):**

- :doc:`ilamb` — Monthly-lnd e3sm_to_cmip: required. Monthly-atm e3sm_to_cmip: optional.
- :doc:`pcmdi_diags` — Monthly-atm e3sm_to_cmip: mean_climate, variability_modes_atm,variability_modes_cpl, enso
