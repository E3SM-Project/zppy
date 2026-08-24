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

   <web_portal_base_path>/diagnostics_archive/<simulation_type>/<case_group>/

``<case_group>`` is included only when the simulation has one. It is read from
``CASE_GROUP`` in ``env_case.xml`` (e.g. ``v3.LR``), falling back to the
``case_group`` parameter in ``[default]``. ``CASE_GROUP`` is optional in CIME,
so when neither is set ``zppy`` warns and publishes directly under
``<simulation_type>/``.

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

Before you publish
-------------------

SimBoard links diagnostics to an *existing* SimBoard case; it does not
create the case for you. Before running zppy with ``[simboard] enabled =
True``, confirm the following:

1. The intended case is already visible in SimBoard. If it is not,
   contact the SimBoard administrator (`Tom Vo <mailto:vo13@llnl.gov>`_)
   before publishing.
2. The provenance that zppy will record — ``case_name``, ``machine``, and
   ``hpc_username`` — matches that SimBoard case.
3. The archive layout that results from your ``[simboard]`` and
   ``[default]`` settings agrees with that provenance:

   - Ungrouped output must land at ``<simulation_type>/<case>``.
   - Grouped output must land at
     ``<simulation_type>/<case_group>/<case>``, using the ``CASE_GROUP``
     value from your E3SM run script configuration (see the ``<case_group>``
     inference described above). ``CASE_GROUP`` is not itself a zppy
     configuration option — zppy only reads it to build the path.

If the layout and the provenance disagree, SimBoard's discovery process
will not find the output, even if the diagnostics are otherwise published
correctly.

Publishing diagnostics and linking the case
--------------------------------------------

Once ``[simboard]`` is configured and the checklist above is satisfied:

1. Run and publish the zppy diagnostics using the configured
   ``simulation_type``. This produces the ``provenance.settings`` file
   that SimBoard uses to discover and link the output.
2. Confirm the published diagnostics output is complete and opens
   successfully in a browser.
3. Confirm the completed output is at the archive path matching the
   grouped or ungrouped layout described above.
4. Wait for the scheduled SimBoard scanner to link the case — linking is
   not immediate, and the scanner runs periodically (currently every 15
   minutes).
5. Once the link appears, open the case in SimBoard and follow its
   diagnostics link.

SimBoard's discovery always uses the *latest valid* provenance for a
published diagnostics case. If a run's provenance is incomplete or
invalid, re-run and re-publish the zppy diagnostics to regenerate it
rather than editing the provenance file by hand — manually edited or
stale provenance files are not used for discovery.

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

This move/copy is the only supported way to promote diagnostics.
Promotion is a zppy-side archive change, not a SimBoard link update — do
not expect SimBoard to move or re-link existing output on its own.

Stable URLs and moved, deleted, or missing output
---------------------------------------------------

The external URL SimBoard links to is stable for a given published case
path: once a case is first linked, updating the content at that same
path keeps working with the existing link.

If diagnostics output is later deleted or moved to a different path:

- Restore the output at its original URL to keep the existing SimBoard
  link working, **or**
- Manually update or remove the link in SimBoard.

SimBoard does not dynamically check for or remove links whose external
output has become unavailable, so a link left pointing at deleted or
moved output will continue to appear valid in SimBoard until it is
corrected.

Troubleshooting
----------------

**The case does not receive a diagnostics link.**
Check, in order: the configured ``simulation_type``; whether the output
follows the correct grouped or ungrouped archive layout; whether the
latest provenance and its paired settings file are present and valid;
whether the case identity (``case_name``, ``machine``, ``hpc_username``)
matches the SimBoard case; and whether the completed output is publicly
accessible. If the link is still missing after checking all of these,
contact `Tom Vo <mailto:vo13@llnl.gov>`_.

**The link opens the wrong output.**
Check ``simulation_type``, ``case_group``, and the published path.
SimBoard does not semantically validate whether the ``simulation_type``
you chose is appropriate for the output — an incorrect value will still
produce a link, just to the wrong place.

**The link no longer opens.**
Restore the output at its original URL, or manually update or remove the
SimBoard link — see `Stable URLs and moved, deleted, or missing output`_
above.

For SimBoard scanner implementation details beyond zppy's configuration,
see SimBoard's own `Diagnostics Linkage Architecture
<https://github.com/E3SM-Project/SimBoard/blob/main/docs/architecture/diagnostics-linkage.md>`_
documentation.
