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

.. literalinclude:: ../post.mysimulation.cfg
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
a web server. ``www`` should be pointed to that so that the plotting tasks (here: ``e3sm_diags``, ``mpas_analysis``, ``global_time_series``, ``livvkit``) will be visible online.

Because we have specified ``campaign = "water_cycle"``, some parameters will
be automatically set. ``zppy/defaults/water_cycle.cfg`` specifies what
``[e3sm_diags] > sets``, and
``[mpas_analysis] > generate`` should be for the water cycle campaign.
Users may specify their own values for any of these parameters,
allowing for easy configuration changes. For example, a user could set
``campaign = "water_cycle"`` but specify their own value for ``[e3sm_diags] > sets``.

Example 2
=========

This is another example of a configuration file, this time using a RRM simulation.

.. literalinclude:: ../post.rrm_simulation.cfg
   :language: cfg
   :linenos:


Example 3
=========

MPAS-Analysis model vs. model
-----------------------------

MPAS-Analysis supports "main vs. control" (model-vs-model) comparisons.
In ``zppy``, this is configured in the ``[mpas_analysis]`` section using
``reference_data_path`` (and optionally ``test_data_path``), consistent with the
terminology used for ``e3sm_diags`` model-vs-model runs.

Unlike ``e3sm_diags`` (where ``run_type = "model_vs_model"`` and ``reference_data_path``
points directly at reference climatology output), MPAS-Analysis comparisons are driven
by MPAS-Analysis config files. For model-vs-model mode, ``zppy`` locates the matching
config file(s) from prior MPAS-Analysis output and passes them to MPAS-Analysis.
The current run's type is inferred automatically: setting ``reference_data_path``
makes it an ``mvm`` run, otherwise it is an ``mvo`` run. If a referenced prior
run could resolve to either ``mvo`` or ``mvm``, use ``reference_comparison_type``
or ``test_comparison_type`` to disambiguate.

.. literalinclude:: ../post.mpas_analysis_model_vs_model.cfg
   :language: cfg
   :linenos:

Debugging failures
==================

.. code-block:: bash

	grep "output =" your_zppy_config.cfg # Easy way to remember your output directory
	cd your_output_dir/post/scripts
	grep -v "OK" *status # See what failed

	# Say failing_task.status is showing a non-OK status, then:
	ls failing_task* # See everything associated with it

	# Say its job ID was 123456, then:
	emacs failing_task.o123456 # Review the output
	emacs failing_task.settings # Review how each of its parameters was set/configured.

	# If an error is obvious, make a fix in the bash file and rerun:
	sbatch failing_task.bash
	
	# If the error is not obvious, do the following:
	emacs failing_task.bash
	# In this file, set `debug = True`. This will provide more information.
	# Note: another option is to set `debug = True` in your `cfg` and rerun `zppy -c`.
	sbatch failing_task.bash
