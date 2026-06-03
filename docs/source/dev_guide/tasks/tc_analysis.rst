.. _dev-task-tc-analysis:

tc_analysis (Developer Reference)
===================================

Implementation
--------------

- **Python module**: ``zppy/tc_analysis.py``
- **Jinja2 template**: ``zppy/templates/tc_analysis.bash``

``tc_analysis`` processes high-frequency atmospheric output (``eam.h2``)
to detect and track tropical cyclones.

Dependencies
------------

**Upstream:**

- None. Reads high-frequency EAM output directly.

**Downstream:**

- None within ``zppy``. TC analysis results can be used as input to the
  ``tc_analysis`` set in ``e3sm_diags`` (model-vs-model), but that
  dependency is specified separately in the ``[e3sm_diags]`` configuration.
