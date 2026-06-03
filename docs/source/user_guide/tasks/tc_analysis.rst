.. _task-tc-analysis:

tc_analysis — Tropical Cyclone Analysis
========================================

The ``tc_analysis`` task performs tropical cyclone (TC) analysis on E3SM
output. It uses high-frequency atmospheric data (typically ``eam.h2``) to
detect and track TCs.

Parameters
----------

.. list-table::
   :header-rows: 1
   :widths: 22 10 18 50

   * - Parameter
     - Required
     - Default
     - Description
   * - ``active``
     - No
     - ``False``
     - Set to ``True`` to enable this task.
   * - ``input_files``
     - No
     - ``"eam.h2"``
     - Input history file pattern. Overrides the ``[default]`` value
       (``eam.h0``).
   * - ``res``
     - No
     - ``""``
     - Resolution string for the ``--res`` option. If not set, ``zppy``
       attempts to infer it from the topography file.

Inherited common parameters most relevant to ``tc_analysis``
------------------------------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 22 10 18 50

   * - Parameter
     - Required
     - Default
     - Description
   * - ``case``
     - **Yes**
     - *(none)*
     - The case name of the simulation.
   * - ``input``
     - **Yes**
     - *(none)*
     - The top-level directory of the simulation output.
   * - ``output``
     - **Yes**
     - *(none)*
     - Where the post-processing results go.
   * - ``years``
     - No
     - ``[""]``
     - Year ranges to process.
   * - ``input_subdir``
     - No
     - ``"archive/atm/hist"``
     - Subdirectory under ``input``/``case`` containing the data files.
   * - ``environment_commands``
     - No
     - ``""``
     - Shell commands to activate the software environment.
   * - ``walltime``
     - No
     - ``"02:00:00"``
     - Maximum wall time for the SLURM job.
