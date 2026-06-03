.. _dev-task-e3sm-to-cmip:

e3sm_to_cmip (Developer Reference)
====================================

Implementation
--------------

- **Python module**: ``zppy/e3sm_to_cmip.py``
- **Jinja2 template**: ``zppy/templates/e3sm_to_cmip.bash``

Dependencies
------------

**Upstream (required):**

- :doc:`ts` — depends on one or more ``[ts]`` subtasks to provide
  input time-series files

The ``ts_subsection``, ``ts_atm_subsection``, and ``ts_land_subsection``
parameters specify which ``[ts]`` subtasks to depend on. With
``infer_section_parameters = True``, these default to the subsection name,
``atm_monthly_180x360_aave``, and ``land_monthly`` respectively.

**Downstream (what depends on e3sm_to_cmip):**

- :doc:`ilamb` — requires CMIP-format land and atmosphere data
- :doc:`pcmdi_diags` — requires CMIP-format atmosphere data
