"""Orchestration for zppy's cfg suite test.

The cfg suite test builds development environments for ``zppy`` and the four
packages whose tasks it launches, submits the weekly test configurations to
SLURM, validates the finished output, and renders a report.

It is driven by :mod:`tests.cfg_suite.automation`; see
``docs/source/dev_guide/tests/automated_test.rst``.
"""
