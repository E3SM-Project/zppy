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

Dependencies
------------

**Upstream (what ts depends on):**

- None.

**Downstream (what depends on ts):**

- :doc:`e3sm_to_cmip` — Monthly-atm ts: monthly-atm e3sm_to_cmip. Monthly-lnd ts: monthly-lnd e3sm_to_cmip.
- :doc:`e3sm_diags` — Monthly-atm ts: enso_diags, qbo, area_mean_time_series, mp_partition. Monthly-rof ts: streamflow. Daily-atm ts: tropical_subseasonal, precip_pdf.
- :doc:`global_time_series` — Monthly-atm-glb ts: the 5 classic atm plots, plots for specific atm variables. Monthly-lnd-glb ts: plots for specific lnd variables.
- :doc:`ilamb` -- Monthly-lnd ts: required. Monthly-atm ts: optional.
- :doc:`livvkit` -- Monthly-lnd ts.
- :doc:`pcmdi_diags` — Monthly-atm ts: mean_climate, variability_modes_atm,variability_modes_cpl, enso
