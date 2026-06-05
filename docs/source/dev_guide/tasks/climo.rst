.. _dev-task-climo:

climo (Developer Reference)
============================

Implementation
--------------

- **Python module**: ``zppy/climo.py``
- **Jinja2 template**: ``zppy/templates/climo.bash``

The ``climo`` function in ``climo.py`` iterates over all ``[climo]``
tasks defined in the configuration file and generates a SLURM bash script
from the ``climo.bash`` Jinja2 template for each year-range/subsection
combination.

Key steps in ``climo.py``:

1. Load the ``climo.bash`` template via ``initialize_template()``.
2. Call ``get_tasks(config, "climo")`` to retrieve all ``[climo]``
   subsection configurations.
3. For each task:

   a. Call ``set_mapping_file()``, ``set_grid()``,
      ``set_component_and_prc_typ()`` to resolve path and component
      inference.
   b. Construct the output filename prefix. For EAMxx, the subsection-level
      ``case`` is used as the stream ID so ``ncclimo`` can locate input
      files.
   c. Render the template and write the bash script.
   d. Submit the script via ``submit_script()``, registering it with
      any bundle if requested.

Dependencies
------------

**Upstream (what climo depends on):**

- None

**Downstream (what depends on climo):**

- :doc:`e3sm_diags` — Monthly-atm climo: lat_lon, zonal_mean_xy, zonal_mean_2d, polar, cosp_histogram, meridional_mean_2d, annual_cycle_zonal_mean, zonal_mean_2d_stratosphere, aerosol_aeronet, aerosol_budget. Monthly-lnd climo: lat_lon_land. Monthly dirunal-atm climo: diurnal_cycle
- :doc:`livvkit` — Monthly-lnd climo

Template variables
------------------

The ``climo.bash`` template receives all configuration parameters as Jinja2
variables. Key template variables:

- ``{{ case }}``, ``{{ input }}``, ``{{ output }}`` — from ``[default]``
- ``{{ mapping_file }}``, ``{{ grid }}`` — resolved by ``set_mapping_file()``
  and ``set_grid()``
- ``{{ vars }}`` — variables to process (empty = all)
- ``{{ parallel }}`` — ncclimo parallel mode (default: ``mpi``)
- ``{{ nodes }}`` — number of nodes (default: 4)
- ``{{ environment_commands }}`` — environment setup
