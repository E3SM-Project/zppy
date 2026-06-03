.. _dev-task-e3sm-diags:

e3sm_diags (Developer Reference)
==================================

Implementation
--------------

- **Python module**: ``zppy/e3sm_diags.py``
- **Jinja2 template**: ``zppy/templates/e3sm_diags.bash``

``e3sm_diags.py`` is the most complex task module in ``zppy``. It handles
a wide variety of diagnostic sets, each with different parameter
requirements.

Key functions in ``e3sm_diags.py``:

- ``check_parameter_defined(c, param)``: raises ``ParameterNotProvidedError``
  if a required parameter is missing.
- ``check_set_specific_parameter(c, sets, param)``: if any requested
  sets require this parameter, check it is present.
- ``check_parameters_for_bash(c)``: validates parameters needed for the
  bash template. Runs early because it has few conditions.
- ``check_mvm_only_parameters_for_bash(c)``: validates model-vs-model
  parameters.
- ``check_and_define_parameters(c)``: resolves all parameters (inference +
  validation). Called later in the pipeline.

Dependencies
------------

**Upstream (required — varies by diagnostic set):**

- :doc:`climo` — required for most sets (``lat_lon``, ``zonal_mean_xy``,
  etc.)
- :doc:`ts` — required for time-series sets (``enso_diags``, ``qbo``,
  ``area_mean_time_series``, ``tropical_subseasonal``, ``streamflow``)
- Diurnal cycle ``[climo]`` subtask — required for ``diurnal_cycle`` set
- Daily ``[ts]`` subtask — required for ``tropical_subseasonal`` set

The specific subtasks to depend on are set via:
``climo_subsection``, ``ts_subsection``, ``climo_diurnal_subsection``,
``ts_daily_subsection``.

**Downstream:**

- :doc:`global_time_series` — optionally

Adding a new diagnostic set
-----------------------------

See :doc:`../new_diags_set` for a step-by-step guide.
