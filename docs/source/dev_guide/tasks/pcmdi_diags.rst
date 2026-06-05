.. _dev-task-pcmdi-diags:

pcmdi_diags (Developer Reference)
===================================

Implementation
--------------

- **Python module**: ``zppy/pcmdi_diags.py``
- **Jinja2 template**: ``zppy/templates/pcmdi_diags.bash``

``pcmdi_diags.py`` handles multiple diagnostic sets (``mean_climate``,
``variability_modes_cpl``, ``variability_modes_atm``, ``enso``,
``synthetic_plots``). The ``current_set`` parameter (or the subsection
name) determines which set to run.

Dependencies
------------

**Upstream (what pcmdi_diags depends on):**

- :doc:`ts` — Monthly-atm ts: mean_climate, variability_modes_atm,variability_modes_cpl, enso
- :doc:`e3sm_to_cmip` — Monthly-atm e3sm_to_cmip: mean_climate, variability_modes_atm,variability_modes_cpl, enso
- Note that the synthetic_plots set depends on the other sets.

**Downstream (what depends on pcmdi_diags):**

- None.
