.. _dev-task-tc-analysis:

tc_analysis (Developer Reference)
===================================

Implementation
--------------

- **Python module**: ``zppy/tc_analysis.py``
- **Jinja2 template**: ``zppy/templates/tc_analysis.bash``

``tc_analysis`` processes high-frequency atmospheric output (``eam.h2`` by
default) to detect and track tropical cyclones and African Easterly Waves
using TempestExtremes. Both EAM and EAMxx are supported.

Template variables
------------------

In addition to the standard top-level variables:

- ``{{ input_grid }}`` — native model grid string (e.g. ``ne30pg2``)
- ``{{ res }}`` — legacy explicit resolution override
- ``{{ tc_vars }}`` — comma-separated 7-variable sequence for TempestExtremes
- ``{{ default_case }}`` — default case ID used to construct output filenames

Dependencies
------------

**Upstream:** None.

**Downstream:**

- ``e3sm_diags`` — required for the ``tc_analysis`` diagnostic set.
