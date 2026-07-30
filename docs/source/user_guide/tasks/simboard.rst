.. _task-simboard:

simboard — SimBoard Publishing Configuration
============================================

The ``simboard`` section is a configuration-only hook that controls
SimBoard-compatible publishing behavior. Like :doc:`bundle`, it does not
launch an HPC job of its own; instead it influences how other tasks are
configured — specifically, it can infer the ``www`` output path from the
machine's Mache configuration.

When ``enabled = True`` and ``www`` is left empty in ``[default]``,
``zppy`` derives ``www`` from the ``web_portal.base_path`` recorded in
Mache for the current machine:

.. code-block:: text

   <web_portal_base_path>/diagnostics_archive/<simulation_type>/

This gives SimBoard a single, predictable archive root to scan for
diagnostics.

Expected behavior
-----------------

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - ``simboard.enabled``
     - ``www``
     - Behavior
   * - ``False``
     - any
     - ``zppy`` does nothing SimBoard-specific.
   * - ``True``
     - empty
     - Infer the SimBoard archive path from Mache's
       ``web_portal.base_path``.
   * - ``True``
     - set
     - Use the explicit ``www`` path and do not override it.
       ``simboard.enabled`` still controls SimBoard-specific validation
       (e.g., ``simulation_type`` must not be ``"none"``).
   * - ``True``
     - empty, but path cannot be inferred
     - Raise a clear configuration error.

Configuration example
---------------------

.. code-block:: cfg

   [default]
   case = v3.LR.historical_0051
   input = /path/to/input
   output = /path/to/output
   # Leave www empty to let zppy infer it from Mache when simboard is enabled.
   www =

   [simboard]
   enabled = True
   simulation_type = development

Parameters
----------

.. list-table::
   :header-rows: 1
   :widths: 22 10 18 50

   * - Parameter
     - Required
     - Default
     - Description
   * - ``enabled``
     - No
     - ``False``
     - Set to ``True`` to enable SimBoard-compatible publishing behavior.
       When enabled and ``[default] www`` is empty, ``zppy`` infers
       ``www`` from Mache's ``web_portal.base_path``.
   * - ``simulation_type``
     - No
     - ``"development"``
     - Diagnostic classification for the archive path. One of
       ``"production"``, ``"development"``, or ``"none"``.
       Must not be ``"none"`` when ``enabled = True``.
       Defaults to ``"development"`` — see :ref:`simboard-promotion` below.

.. note::
   The ``[simboard]`` section does not support subsections.

.. _simboard-promotion:

Promoting diagnostics from development to production
-----------------------------------------------------

The default ``simulation_type`` is ``"development"`` rather than
``"production"``. Accidentally placing development diagnostics under the
``production`` archive is more harmful than placing production diagnostics
under ``development``, so production is an explicit opt-in.

To promote a run's diagnostics to the production archive:

1. Update ``simulation_type`` to be ``production`` on the SimBoard UI itself.
2. Manually move (or copy) the existing diagnostic output from
   ``<web_portal_base_path>/diagnostics_archive/development/<case>/`` to
   ``<web_portal_base_path>/diagnostics_archive/production/<case>/``.
