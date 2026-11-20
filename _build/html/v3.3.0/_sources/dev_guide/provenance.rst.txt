.. _dev-provenance:

Provenance (Developer Reference)
==================================

Overview
--------

Every ``zppy`` run writes two provenance files for each invocation:

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - File
     - Contents
   * - ``provenance.<ts_utc>.cfg``
     - A verbatim copy of the user-supplied ``.cfg`` configuration file.
   * - ``provenance.<ts_utc>.settings``
     - Key-value metadata about the run: ``case_name``, ``machine``,
       ``hpc_username``, and ``diagnostics_url``. Only written when at least
       one field resolves to a non-empty value.

Both files are written to the script directory
(``<output>/post/scripts/``) and mirrored under ``<www>/<case>/`` when
that directory is accessible.

The ``.settings`` file format
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

One ``key = value`` pair per line, e.g.:

.. code-block:: text

   case_name = v3.LR.historical_0051
   machine = pm-cpu
   hpc_username = ac.zhang40
   diagnostics_url = https://portal.nersc.gov/cfs/e3sm/ac.zhang40/zppy_demo/v3.LR.historical_0051

Fields with empty or ``None`` values are omitted.

Implementation
--------------

- **Python module**: ``zppy/provenance.py``
- **Called from**: ``zppy/__main__.py``

``zppy/provenance.py`` exports four public helpers:

``parse_env_case_xml(input_dir)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Reads ``<input_dir>/case_scripts/env_case.xml`` and returns a dict with any
of ``case_name``, ``machine``, and ``hpc_username`` that were successfully
parsed. Degrades gracefully on a missing file, missing entries, or malformed
XML (logs a warning and returns a partial or empty dict).

``build_diagnostics_url(www, case, machine_info)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Constructs the public web-portal URL for the run's diagnostics output using
the machine's ``web_portal`` ``base_path`` and ``base_url`` from the
``mache`` ``MachineInfo`` config. Returns ``None`` when ``www`` is empty,
when ``www`` is not under the machine's ``base_path``, or when the machine
config lacks ``web_portal`` entries.

``write_provenance_settings(settings_path, extras)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Writes the ``provenance.settings`` file from a dict, skipping empty and
``None`` values. Does nothing if no usable entries remain.

``build_provenance_extras(config_default, machine_info)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Orchestrates the other three functions. Reads ``case_name``, ``machine``,
and ``hpc_username`` from ``env_case.xml`` under ``cfg["default"]["input"]``,
builds ``diagnostics_url`` from ``cfg["default"]["www"]`` and
``cfg["default"]["case"]``, and returns the assembled extras dict. Logs a
warning if the case name in the cfg disagrees with the value in
``env_case.xml`` (the XML value is treated as authoritative).

Unit tests
----------

``tests/test_zppy_provenance.py`` covers all four public helpers, including
missing-file, partial-entry, malformed-XML, unsupported-machine, and
case-mismatch scenarios.
