.. _dev-task-livvkit:

livvkit (Developer Reference)
==============================

Implementation
--------------

- **Python module**: ``zppy/livvkit.py``
- **Jinja2 template**: ``zppy/templates/livvkit.bash``

Dependencies
------------

**Upstream (required):**

- :doc:`climo` — depends on multiple ``[climo]`` subtasks:

  - A grid-native climatology: assumed ``land_monthly_climo_native``
  - Reanalysis-grid climatologies: one per reanalysis comparison, named
    ``land_monthly_climo_<GRID>``

  All required subtask names are listed in ``climo_subsections``.

**Downstream:**

- None.
