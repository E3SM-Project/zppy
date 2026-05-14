************
Testing zppy
************

Unit tests
==========

Run all unit tests by doing the following:

    .. code::

        pip install . # Install your changes (`python -m pip install .` also works)
        pytest tests/test_*.py # Run all unit tests

Integration tests
=================

Integration tests can be run on Chrysalis, Compy, or Perlmutter.
First review `machine-specific directions <https://github.com/E3SM-Project/zppy/tree/main/tests/integration/generated>`_.

Run all integration tests by doing the following:

    .. code::

        pip install . # Install your changes (`python -m pip install .` also works)

        pytest tests/integration/test_*.py # Run all integration tests

Automated tests
===============

We have a :ref:`GitHub Actions <ci-cd>` Continuous Integration / Continuous Delivery (CI/CD) workflow.

The unit tests are run automatically as part of this. Integration tests must be run on a machine specified above.
