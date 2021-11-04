.. _tutorial:

***************
Tutorial
***************

These examples are for use on LCRC machines (e.g., Chrysalis). Some parameters
must be changed for use on other machines. These include the paths for
``input``, ``output``, ``www``, ``mapping_file``, ``reference_data_path``, ``obs_ts``,
``streamflow_obs_ts``, and ``dc_obs_climo``. Different machines also have different partition names, so
``partition`` may need to be changed as well.


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

Because we have specified ``campaign = "water_cycle"``, some parameters will
be automatically set. ``zppy/templates/water_cycle.cfg`` specifies what
``[e3sm_diags] > sets``, ``[e3sm_diags_vs_model] > sets``, and
``[mpas_analysis] > generate`` should be for the water cycle campaign.
Users may specify their own values for any of these parameters,
allowing for easy configuration changes. For example, a user could set
``campaign = "water_cycle"`` but specify their own value for ``[e3sm_diags] > sets``.

Example 2
=========

This is another example of a configuration file, this time using a RRM simulation.

.. literalinclude:: post.rrm_simulation.cfg
   :language: cfg
   :linenos:
