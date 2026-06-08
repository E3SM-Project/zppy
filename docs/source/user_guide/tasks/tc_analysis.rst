.. _task-tc-analysis:

tc_analysis — Tropical Cyclone Analysis
========================================

The ``tc_analysis`` task performs tropical cyclone (TC) analysis on E3SM
output. It uses high-frequency atmospheric data (typically ``eam.h2``) to
detect and track TCs.

Parameters
----------

This parameter is specific to the ``tc_analysis`` task:

.. list-table::
   :header-rows: 1
   :widths: 22 10 18 50

   * - Parameter
     - Required
     - Default
     - Description
   * - ``res``
     - No
     - ``""``
     - Resolution string for the ``--res`` option. If not set, ``zppy``
       attempts to infer it from the topography file.

Parameters at the top-level
~~~~~~~~~~~~~~~~~~~~~~~~~~~

This parameter has a ``tc_analysis``-specific default, which means even if it is set at the top level (``[default]``) section, the default value will be used instead. Therefore, to specify a custom value, this parameter must be defined inside ``[tc_analysis]``:

.. list-table::
   :header-rows: 1
   :widths: 22 10 18 50

   * - Parameter
     - Required
     - Default
     - Description
   * - ``input_files``
     - No
     - ``"eam.h2"``
     - Input history file pattern. Overrides the ``[default]`` value
       (``eam.h0``).

For other top-level parameters, see :ref:`top-level parameters <parameters-top-level>`.

Dependencies
------------

**Upstream (what tc_analysis depends on):**

- None.

**Downstream (what depends on tc_analysis):**

- :doc:`e3sm_diags` — Required for tc_analysis set.
