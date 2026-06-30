.. _task-tc-analysis:

tc_analysis — Tropical Cyclone Analysis
========================================

The ``tc_analysis`` task performs tropical cyclone (TC) and African Easterly
Wave (AEW) analysis on E3SM output. It uses high-frequency atmospheric data
(typically ``eam.h2``) to detect and track TCs and AEWs using TempestExtremes.

Both EAM and EAMxx output are supported. EAMxx requires the ``input_grid``
parameter to be set because its output sets ``topography_file="NONE"``,
preventing automatic grid inference.

Configuration example
---------------------

EAM:

.. code-block:: cfg

   [tc_analysis]
   active = True
   input_grid = ne30pg2
   years = 1:100:10

EAMxx:

.. code-block:: cfg

   [tc_analysis]
   active = True
   input_grid = ne30pg2
   tc_vars = SeaLevelPressure,T_mid_at_200hPa,T_mid_at_500hPa,U_at_model_bot,V_at_model_bot,U_at_850hPa,V_at_850hPa
   years = 1:100:10

Parameters
----------

These 3 parameters are specific to the ``tc_analysis`` task:

.. list-table::
   :header-rows: 1
   :widths: 22 10 18 50

   * - Parameter
     - Required
     - Default
     - Description
   * - ``input_grid``
     - No
     - ``""``
     - Native model grid of the input files, e.g. ``ne30pg2``, ``ne120pg2``,
       ``ne30np4``. When set, the resolution and pg2 flag are derived from
       this value automatically. Required for EAMxx. Accepted formats:
       ``neXpg2`` or ``neXnp4`` (e.g. ``ne30pg2``, ``ne120np4``).
   * - ``res``
     - No
     - ``""``
     - Explicit ``--res`` value for TempestExtremes (EAM only). Used when
       ``input_grid`` is empty. If both are empty, ``zppy`` attempts to infer
       ``res`` from the ``topography_file`` global attribute of the input
       files (EAM only).
   * - ``tc_vars``
     - No
     - ``"PSL,T200,T500,UBOT,VBOT,U850,V850"``
     - Ordered list of exactly 7 comma-separated variable names in the
       sequence required by the TempestExtremes workflow:
       ``SLP, T@200hPa, T@500hPa, U@model_bottom, V@model_bottom, U@850hPa,
       V@850hPa``. The default covers EAM output. EAMxx users should set this
       to the corresponding EAMxx variable names, e.g.
       ``SeaLevelPressure,T_mid_at_200hPa,T_mid_at_500hPa,U_at_model_bot,V_at_model_bot,U_at_850hPa,V_at_850hPa``.

Parameters at the top-level
~~~~~~~~~~~~~~~~~~~~~~~~~~~

This parameter has a ``tc_analysis``-specific default, which means even if it
is set at the top level (``[default]``) section, the default value will be
used instead. Therefore, to specify a custom value, this parameter must be
defined inside ``[tc_analysis]``:

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
