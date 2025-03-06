.. _parameters:

***************
Parameters
***************

Parameters make use of inheritance. Parameters set in ``[default]`` can
be overridden by parameters set in a ``[section]``, which can themselves
be overridden by parameters set in a ``[[subsection]``.

.. warning::
   Note that some parameters will be overriden by defaults if you define them too high up in the inheritance hierarchy.

See `this release's parameter defaults <https://github.com/E3SM-Project/zppy/blob/ac90fa116b1a62eaacfa9c4efbe4d31c8c1a5e5c/zppy/templates/default.ini>`_
on GitHub for a complete list of parameters and their default values. 
You can also view the most up-to-date, 
`unreleased parameter defaults <https://github.com/E3SM-Project/zppy/blob/main/zppy/templates/default.ini>`_.

Deprecated parameters
=====================

The following parameters no longer perform any function:
   ::

        "e3sm_to_cmip_environment_commands"
        "ts_fmt"
        "scratch"
        "atmosphere_only"
        "plot_names"

Parameter checking & inferring -- for users
===========================================

There are two types of inferences, each with their own parameter in ``default.ini``:

* ``infer_path_parameters``: infer paths that are not explicitly provided in the configuraiton file. Default is ``True``.
* ``infer_section_parameters``: infer subtask dependency names that are not explicitly provided in the configuration file. Default is ``True``.

**Section inferences**

For the ``climo``, ``ts``, ``e3sm_to_cmip``, and ``e3sm_diags`` tasks:

* If ``subsection`` (the name of the subtask) is undefined, just use the value of ``grid``.

For the ``e3sm_to_cmip`` task:

* If ``ts_subsection`` (the name of the ``ts`` subtask that this ``e3sm_to_cmip`` subtask is dependent on) is undefined, assume it had the same name as this ``e3sm_to_cmip`` subtask.

For the ``ilamb`` task:

* If ``ts_land_subsection`` (the name of the ``ts`` land-specific subtask that this ``ilamb`` task is dependent on), assume it is ``land_monthly``.
* If ``e3sm_to_cmip_land_subsection`` (the name of the ``e3sm_to_cmip`` land-specific subtask that this ``ilamb`` task is dependent on), again assume it is ``land_monthly``.
* If we are not doing a ``land_only`` run and ``ts_atm_subsection`` (the name of the ``ts`` atm-specific subtask that this ``ilamb`` task is dependent on), assume it is ``atm_monthly_180x360_aave``.
* If we are not doing a ``land_only`` run and ``e3sm_to_cmip_atm_subsection`` (the name of the ``e3sm_to_cmip`` atm-specific subtask that this ``ilamb`` task is dependent on), again assume it is ``atm_monthly_180x360_aave``.


**Path inferences**

For the ``e3sm_diags`` task:

* If ``reference_data_path`` (the path to the reference data) is undefined, assume it is the ``diagnostics_base_path`` from Mache plus ``/observations/Atm/climatology/``. (So, it is important to change this for model-vs-model runs).


For the ``ilamb`` task:

* If ``ilamb_obs`` (the path to observation data for ``ilamb``) is undefined, assume it is the ``diagnostics_base_path`` from Mache plus ``/ilamb_data``.

**Required parameters, by e3sm_diags set**

See `Confluence <https://acme-climate.atlassian.net/wiki/spaces/IPD/pages/4984209586/zppy+parameters+for+e3sm_diags>`_ for tables of which sets require which parameters.

Parameter checking & inferring -- for developers
================================================

There are many parameter-handling functions.

In ``utils.py``:

* ``get_value_from_parameter``: check if parameter is in the configuration dictionary. If not, if inference is turned on (the default), then just use the value of ``second_choice_parameter``. If inferenceis turned off, raise a ``ParameterNotProvidedError``. Use this function if the backup option 
* ``set_value_of_parameter_if_undefined``: check if parameter is in the configuration dictionary. If not, if inferenceis turned on (the default), then just set the parameter's value to the ``backup_option``. If inferenceis turned off, raise a ``ParameterNotProvidedError``.

In ``e3sm_diags.py``:

* ``check_parameter_defined``: check if parameter is in the configuration dictionary, and if not raise a ``ParameterNotProvidedError``.
* ``check_set_specific_parameter``: if any requested ``e3sm_diags`` sets require this parameter, make sure it is present. If not, raise a ``ParameterNotProvidedError``.
* ``check_parameters_for_bash``: use ``check_set_specific_parameter`` to check the existence of parameters that aren't used until the bash script.
* ``check_mvm_only_parameters_for_bash``: similar, but these are specifically parameters used for model-vs-model runs. Uses ``check_parameter_defined`` in addition to ``check_set_specific_parameter``.
* ``check_and_define_parameters``: make sure all parameters are defined, using ``utils.py get_value_from_parameter``, ``utils.py set_value_of_parameter_if_undefined``,  and ``check_mvm_only_parameters_for_bash``. 

``check_parameters_for_bash`` can be run immediately for each subtask because it has very few conditions. Other checks are included in ``check_and_define_parameters`` later on in the code.