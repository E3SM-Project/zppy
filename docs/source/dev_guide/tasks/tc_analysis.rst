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

**Upstream (what tc_analysis depends on):**

- None.

**Downstream (what depends on tc_analysis):**

- :doc:`e3sm_diags` — Required for tc_analysis set.
