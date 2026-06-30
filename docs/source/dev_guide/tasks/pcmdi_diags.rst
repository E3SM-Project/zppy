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
