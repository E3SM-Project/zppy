.. _tutorial:

***************
Tutorial
***************

Example 1
=========

Let's say we want to post-process 100 years of an existing simulation.

Copy and paste the following into ``post.mysimulation.cfg``

.. literalinclude:: post.mysimulation.cfg
   :language: cfg
   :linenos:

Now we can run ``zppy -c post.mysimulation.cfg``.

The ``[climo]`` subsections (``[[ atm_monthly_180x360_aave ]]`` and
``[[ atm_monthly_diurnal_8xdaily_180x360_aave ]]``), the ``[ts]`` subsections
(``[[ atm_monthly_180x360_aave ]]``, ``[[ atm_daily_180x360_aave ]]``,
``[[ atm_monthly_glb ]]`` and ``[[ land_monthly ]]``), and
the ``[mpas_analysis]`` section will run first because they have
no dependencies.

Once the ``[climo]`` subsections and the ``[ts]`` subsection
``[[ atm_monthly_180x360_aave ]]`` finish, ``[e3sm_diags]`` will run.

Once the ``[ts]`` subsection ``[[ atm_monthly_glb ]]`` and the ``[mpas_analysis]``
section finish, ``[global_time_series]`` will run.

Post-processing results will be located in ``output`` and ``www``. Some machines have
a web server. ``www`` should be pointed to that so that E3SM Diags, MPAS-Analysis, and
the global time series plots will be visible online.

Example 2
=========

This is another example of a configuration file, this time using a RRM simulation.

.. literalinclude:: post.rrm_simulation.cfg
   :language: cfg
   :linenos:
