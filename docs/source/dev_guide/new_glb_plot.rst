***************************************
Adding a new plot to Global Time Series
***************************************

This guide gives a general list of things to consider when adding a new
Global Time Series plot. The exact code changes required will differ amongst plots.

Note that unlike E3SM Diags and MPAS-Analysis which are packages called by ``zppy``, Global Time Series is built into ``zppy``.

- In `coupled_global.py <https://github.com/E3SM-Project/zppy/blob/main/zppy/templates/coupled_global.py>`_: Add variables under "# Variables to extract". Add the code for your new plot under "Plotting functions"; the name of your function should start with ``plot_``. In ``PLOT_DICT``, add ``"function name without plot_" : function name``.
- If this plot should be added to the defaults, then complete this step: for ``plot_names`` under ``[global_time_series]`` in `default.ini <https://github.com/E3SM-Project/zppy/blob/main/zppy/templates/default.ini>`_, add the function name without plot to the string.
- Optionally, after making your edits, you can run ``pre-commit run --all-files`` to clean up your code and check for any obvious errors.
- Run the `integration tests <https://e3sm-project.github.io/zppy/_build/html/main/dev_guide/testing.html#integration-tests>`_ and examine the differences from the expected files. If they match what you expect, update the expected files following "Commands to run to replace outdated expected files" on the machine-specific directions. (The commands to run all the integration tests are ``pip install .`` followed by ``python -u -m unittest tests/integration/test_*.py``).
