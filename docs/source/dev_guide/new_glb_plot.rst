***************************************
Adding a new plot to Global Time Series
***************************************

This guide gives a general list of things to consider when adding a new
Global Time Series plot. The exact code changes required will differ amongst plots.

- Add the code for your new plot under "Plotting functions" in `coupled_global.py <https://github.com/E3SM-Project/zppy/blob/main/zppy/templates/coupled_global.py>`_. The name of your function should start with ``plot_``.
- In ``PLOT_DICT``, add ``"function name without plot_" : function name``.
- If this plot should be added to the defaults, complete this step: for ``plot_names`` under ``[global_time_series]`` in `default.ini <https://github.com/E3SM-Project/zppy/blob/main/zppy/templates/default.ini>`_, add the function name without plot to the string.
- Run the `integration tests <https://e3sm-project.github.io/zppy/_build/html/main/dev_guide/testing.html#integration-tests>`_ and examine the differences from the expected files. If they match what you expect, update the expected files following "Commands to run to replace outdated expected files" on the machine-specific directions.
