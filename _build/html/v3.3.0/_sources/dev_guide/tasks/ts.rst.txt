.. _dev-task-ts:

ts (Developer Reference)
=========================

Implementation
--------------

- **Python module**: ``zppy/ts.py``
- **Jinja2 template**: ``zppy/templates/ts.bash``

The ``ts`` function iterates over all ``[ts]`` tasks and generates a SLURM
bash script from the ``ts.bash`` Jinja2 template for each
year-range/subsection combination.

Key steps in ``ts.py``:

1. Load the ``ts.bash`` template.
2. Call ``get_tasks(config, "ts")`` for all subtasks.
3. For each task:

   a. Resolve mapping file, grid, and component type.
   b. Render the template and write the bash script.
   c. Submit the script.

Vertical remapping
~~~~~~~~~~~~~~~~~~

When ``vrt_remap_vars`` is non-empty, the template also calls ``ncremap``
after ``ncclimo`` to remap specified variables from model levels to pressure
levels. Output is written to a sibling ``ts_vrt_remap/`` directory.
