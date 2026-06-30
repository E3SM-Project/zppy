.. _dev-task-bundle:

bundle (Developer Reference)
==============================

Implementation
--------------

- **Python module**: ``zppy/bundle.py``
- **Jinja2 template**: ``zppy/templates/bundle.bash``

The ``Bundle`` class in ``bundle.py`` collects tasks that share the same
``bundle`` name. When ``handle_bundles()`` is called, it renders a single
SLURM script that runs all bundled tasks sequentially within one job.

A bundle is named by its ``[bundle] [[name]]`` subsection, and tasks
opt in by setting ``bundle = name``. Bundle parameters (walltime, nodes,
etc.) are taken from the first task added or from the ``[bundle]`` section.

Dependencies
------------

Bundles inherit the union of all their member tasks' dependencies. The
bundle job will not start until all upstream dependencies are satisfied
for all bundled tasks.

**Downstream:**

- Downstream tasks that depend on bundled tasks will list the bundle's
  status file as a dependency.
