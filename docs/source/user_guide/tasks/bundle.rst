.. _task-bundle:

bundle — Job Bundling
======================

The ``bundle`` task groups multiple ``zppy`` tasks into a single SLURM job
script. This is useful for running many lightweight tasks together on a
single node, avoiding scheduler overhead and resource waste.

When a task specifies ``bundle = "<name>"`` in its configuration, it will
be included in the named bundle. The bundle itself is defined in a
``[bundle]`` section.

.. note::
   Bundle parameters (e.g., ``walltime``, ``nodes``) are taken from the
   *first task* added to the bundle, or from the ``[bundle]`` section
   itself. The ``active`` parameter in ``[bundle]`` always overrides the
   ``[default]`` value and defaults to ``True``.

Configuration example
---------------------

.. code-block:: cfg

   [bundle]
     [[long_jobs]]
     walltime = 08:00:00
     nodes = 1

   [climo]
     [[atm_monthly_180x360_aave]]
     bundle = long_jobs
     years = 1:100:20

   [ts]
     [[atm_monthly_180x360_aave]]
     bundle = long_jobs
     years = 1:100:10

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
     - ``True``
     - Whether the bundle is active. Overrides the ``[default]`` value.
   * - ``bundle``
     - No
     - ``""``
     - (Set on individual tasks) Name of the bundle to include this task
       in.
