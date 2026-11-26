.. _rendered-script-snapshots:

*************************
Rendered script snapshots
*************************

``tests/test_rendered_scripts.py`` checks the scripts that ``zppy`` renders
from its templates against snapshots checked into the repository. Unlike
``tests/integration/test_bash_generation.py``, it does not need an HPC
machine: it runs ``zppy``'s task functions in ``dry_run`` mode with made-up
machine information in place of ``mache``. It runs with the other unit tests,
including in CI:

.. code-block:: bash

    pytest tests/test_rendered_scripts.py

What is checked
===============

Each scenario renders one configuration file from ``tests/rendering/`` as if
``zppy`` were run on a given machine:

* ``comprehensive_chrysalis``: ``comprehensive.cfg``, which exercises as many
  branches of the templates as practical.
* ``machines_compy``, ``machines_dane``, ``machines_pm-cpu``: ``machines.cfg``,
  one job per task, to cover the machine-specific parts of the templates.
* ``last_year_chrysalis``: ``last_year.cfg`` with ``last_year = 1986``.

For each scenario, ``tests/rendering/snapshots/<scenario>/`` holds every
rendered job script (``.bash``), every file ``zppy`` writes next to them for the
jobs to use (such as an E3SM Diags run script, ``.py``, or an MPAS-Analysis
config file, ``.cfg``), and ``dependencies.json``, which lists the status files
each job depends on. The temporary directory each scenario runs in is written
as ``/zppy_snapshot``, so the snapshots do not depend on where the tests run.

The tests also check that every rendered script passes ``bash -n``, that the
rendered Python files compile, and that the MPAS-Analysis config files can be
parsed.

Updating the snapshots
======================

A change to a template, to a task's Python file, or to ``default.ini`` may
change the rendered scripts. If the change is intended, regenerate the
snapshots and review the differences before committing them:

.. code-block:: bash

    ZPPY_UPDATE_SNAPSHOTS=1 pytest tests/test_rendered_scripts.py
    git diff tests/rendering/snapshots

The snapshot diff shows exactly how a pull request changes what ``zppy``
generates, so please include it in the same commit as the change that causes
it.

Adding a scenario
=================

Add a configuration file to ``tests/rendering/`` (or reuse one) and add a
``Scenario`` to ``SCENARIOS`` in ``tests/rendering/scenarios.py``. To render
for a machine that is not yet in ``MACHINES``, add its paths from ``mache``'s
machine config file. Then regenerate the snapshots as described above.

Other tests can check specific behavior of the rendered scripts with
``render_scenario``, which renders each scenario only once per test session:

.. code-block:: python

    from tests.rendering.scenarios import SCENARIOS_BY_NAME, render_scenario

    files = render_scenario(SCENARIOS_BY_NAME["comprehensive_chrysalis"])
