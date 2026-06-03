.. _dev-task-ilamb:

ilamb (Developer Reference)
=============================

Implementation
--------------

- **Python module**: ``zppy/ilamb.py``
- **Jinja2 template**: ``zppy/templates/ilamb.bash``

Dependencies
------------

**Upstream (required):**

- :doc:`e3sm_to_cmip` — depends on CMIP-format land and (for non-land-only
  runs) atmosphere time-series files

  - Land subtask: ``e3sm_to_cmip_land_subsection`` (inferred as
    ``land_monthly`` if not set)
  - Atmosphere subtask: ``e3sm_to_cmip_atm_subsection`` (inferred as
    ``atm_monthly_180x360_aave`` if not set, skipped for land-only runs)

- :doc:`ts` — also depends on ``ts`` subtasks:

  - Land subtask: ``ts_land_subsection`` (inferred as ``land_monthly``)
  - Atmosphere subtask: ``ts_atm_subsection`` (inferred as
    ``atm_monthly_180x360_aave``, skipped for land-only runs)

**Downstream:**

- None.
