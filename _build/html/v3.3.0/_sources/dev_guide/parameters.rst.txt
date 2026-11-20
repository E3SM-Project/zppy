.. _parameters_for_developers:

************************************************
Parameter checking & inferring -- for developers
************************************************

There are many parameter-handling functions.

In ``utils.py``:

* ``get_value_from_parameter``: check if parameter is in the configuration dictionary. If not, if inference is turned on (the default), then just use the value of ``second_choice_parameter``. If inference is turned off, raise a ``ParameterNotProvidedError``. Use this function if the backup option is another parameter (rather than a fixed value).
* ``set_value_of_parameter_if_undefined``: check if parameter is in the configuration dictionary. If not, if inference is turned on (the default), then just set the parameter's value to the ``backup_option``. If inference is turned off, raise a ``ParameterNotProvidedError``.

In ``e3sm_diags.py``:

* ``check_parameter_defined``: check if parameter is in the configuration dictionary, and if not raise a ``ParameterNotProvidedError``.
* ``check_set_specific_parameter``: if any requested ``e3sm_diags`` sets require this parameter, make sure it is present. If not, raise a ``ParameterNotProvidedError``.
* ``check_parameters_for_bash``: use ``check_set_specific_parameter`` to check the existence of parameters that aren't used until the bash script.
* ``check_mvm_only_parameters_for_bash``: similar, but these are specifically parameters used for model-vs-model runs. Uses ``check_parameter_defined`` in addition to ``check_set_specific_parameter``.
* ``check_and_define_parameters``: make sure all parameters are defined, using ``utils.py get_value_from_parameter``, ``utils.py set_value_of_parameter_if_undefined``,  and ``check_mvm_only_parameters_for_bash``.

``check_parameters_for_bash`` can be run immediately for each subtask because it has very few conditions. Other checks are included in ``check_and_define_parameters`` later on in the code.