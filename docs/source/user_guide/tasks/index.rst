.. _user-tasks:

*****
Tasks
*****

``zppy`` is organized around **tasks**. Each task corresponds to a specific
post-processing operation. Tasks are defined as sections (``[task_name]``) in
the configuration file and may contain subsections (``[[subsection_name]]``)
for multiple independent runs of the same task.

**Available tasks:**

Listed by the order they are evaluated in `__main__.py`:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Task
     - Description
   * - :doc:`bundle`
     - Bundle multiple tasks into a single SLURM job
   * - :doc:`climo`
     - Generate climatology files using NCO's ``ncclimo``
   * - :doc:`ts`
     - Generate time-series files using NCO's ``ncclimo``
   * - :doc:`e3sm_to_cmip`
     - Convert E3SM output to CMIP6 format using ``e3sm_to_cmip``
   * - :doc:`tc_analysis`
     - Tropical cyclone analysis
   * - :doc:`e3sm_diags`
     - Run E3SM Diagnostics (atmosphere, land, river diagnostics, etc.)
   * - :doc:`mpas_analysis`
     - Run MPAS-Analysis (ocean and sea-ice diagnostics)
   * - :doc:`global_time_series`
     - Generate global time series plots
   * - :doc:`ilamb`
     - Run ILAMB land benchmarking
   * - :doc:`livvkit`
     - Run LIVVkit ice sheet validation
   * - :doc:`pcmdi_diags`
     - Run PCMDI metrics diagnostics


**Common (default) parameters** shared by all tasks are documented on the
:doc:`../parameters` page.

.. toctree::
   :hidden:

   bundle
   climo
   ts
   e3sm_to_cmip
   tc_analysis
   e3sm_diags
   mpas_analysis
   global_time_series
   ilamb
   livvkit
   pcmdi_diags
