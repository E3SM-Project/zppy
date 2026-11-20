.. _dev-task-simboard:

simboard (Developer Reference)
================================

Implementation
--------------

- **Python module**: ``zppy/simboard.py``
- **Jinja2 template**: none (configuration-only hook, no HPC job is submitted)

The ``simboard`` section is a configuration-only task hook, analogous to
:doc:`bundle`. It performs validation and, when ``enabled = True`` and
``[default] www`` is empty, infers ``www`` from Mache's
``web_portal.base_path``.

Key functions in ``zppy/simboard.py``:

- ``simboard(config, script_dir, existing_bundles, job_ids_file)``: the
  main hook registered in ``_launch_scripts``. Validates that the
  ``[simboard]`` section contains no subsections and returns
  ``existing_bundles`` unchanged.
- ``simboard_enabled(config)``: parses the ``enabled`` field from a bool
  or ``"true"``/``"false"`` string (case-insensitive).
- ``validate_simboard_config(config)``: rejects ``simulation_type = "none"``
  when ``enabled = True``.
- ``normalize_web_portal_base_path(path)``: strips leading/trailing
  whitespace and trailing slashes.
- ``infer_simboard_www(machine_info, config)``: builds
  ``<web_portal_base_path>/diagnostics_archive/<simulation_type>/``; raises
  a descriptive ``ValueError`` if Mache has no (or empty)
  ``web_portal.base_path`` for the machine.

``www`` inference is wired into ``_determine_parameters`` in
``zppy/__main__.py`` via the ``_set_default_www`` helper, which:

1. Always calls ``validate_simboard_config`` (checks ``simulation_type``
   even when ``www`` is already set).
2. Returns immediately if ``www`` is already set.
3. Otherwise requires ``simboard.enabled = True``; calls
   ``infer_simboard_www`` and sets ``config["default"]["www"]``.

Config defaults (``zppy/defaults/default.ini``)
------------------------------------------------

.. code-block:: ini

   [simboard]
   enabled = boolean(default=False)
   simulation_type = option("production", "development", "none", default="development")

Dependencies
------------

**Upstream (what simboard depends on):**

- None

**Downstream (what depends on simboard):**

- None (the ``[simboard]`` section has no downstream task dependencies; it
  only sets ``www``, which is consumed by every visual-output task)

Testing
-------

Unit tests are in ``tests/test_zppy_main.py`` and cover:

- ``www`` inference for both ``production`` and ``development`` types.
- Path normalization (trailing slash, leading/trailing whitespace).
- ``simboard_enabled`` parsing (bool, string, invalid).
- Explicit ``www`` is preserved when SimBoard is enabled.
- Error on empty ``www`` with SimBoard disabled.
- Error on ``simulation_type = "none"`` when enabled.
- Errors when Mache has no or empty ``web_portal.base_path``.
- Rejection of subsections under ``[simboard]``.
- Rejection of invalid ``simulation_type`` values via ConfigObj validation.

Integration tests are in ``tests/integration/test_simboard_settings.py``
and cover all four rows of the expected-behavior table using a real
``zppy`` config file with ``dry_run = True``.
