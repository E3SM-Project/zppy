Testing zppy
============

Unit tests
----------

Run all unit tests by doing the following

    .. code::

        pip install . # Install your changes (`python -m pip install .` also works)
        python -m unittest tests/test_*.py # Run all unit tests

Integration tests
-----------------

Integration tests must be run on an LCRC machine.

    .. code::

        pip install . # Install your changes (`python -m pip install .` also works)
        python -m unittest tests/integration/test_*.py # Run all integration tests

Automated tests
---------------

We have a :ref:`GitHub Actions <ci-cd>` Continuous Integration / Continuous Delivery (CI/CD) workflow.

The unit tests are run automatically as part of this. As mentioned earlier,
integration tests must be run on an LCRC machine.

