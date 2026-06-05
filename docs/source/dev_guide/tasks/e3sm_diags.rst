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

**Upstream (what e3sm_diags depends on):**

- :doc:`climo` — Monthly-atm climo: lat_lon, zonal_mean_xy, zonal_mean_2d, polar, cosp_histogram, meridional_mean_2d, annual_cycle_zonal_mean, zonal_mean_2d_stratosphere, aerosol_aeronet, aerosol_budget. Monthly-lnd climo: lat_lon_land. Monthly dirunal-atm climo: diurnal_cycle
- :doc:`ts` — Monthly-atm ts: enso_diags, qbo, area_mean_time_series, mp_partition. Monthly-rof ts: streamflow. Daily-atm ts: tropical_subseasonal, precip_pdf.
- :doc:`tc_analysis` — Required for tc_analysis set.

**Downstream (what depends on e3sm_diags):**

- None.

Adding a new diagnostic set
-----------------------------

See :doc:`../new_diags_set` for a step-by-step guide.
