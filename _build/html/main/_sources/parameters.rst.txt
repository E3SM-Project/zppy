.. _parameters:

***************
Parameters
***************

Parameters make use of inheritance. Parameters set in ``[default]`` can
be overridden by parameters set in a ``[section]``, which can themselves
be overridden by parameters set in a ``[[subsection]``.

.. warning::
   Note that some parameters will be overriden by defaults if you define them too high up in the inheritance hierarchy.

See `this release's parameter defaults <https://github.com/E3SM-Project/zppy/blob/bfbba5f9c3794cd7e399e35f8153866b1c8f6910/zppy/defaults/default.ini>`_
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


For the ``livvkit`` task:

* A grid-native climatology must be generated, assumed to be ``land_monthly_climo_native``
* For each reanalysis comparison to be performed, a corresponding ``land_monthly_climo_GRID`` where ``GRID`` corresponds to the reanalysis grid name
* Available reanalysis comparisons are
   * racmo_gis, racmo_ais
   * merra2
   * era5
   * ceres (default cmip6 grid)

**Path inferences**

For the ``e3sm_diags`` task:

* If ``reference_data_path`` (the path to the reference data) is undefined, assume it is the ``diagnostics_base_path`` from Mache plus ``/observations/Atm/climatology/``. (So, it is important to change this for model-vs-model runs).


For the ``mpas_analysis`` task:

* ``reference_data_path`` and ``test_data_path`` are optional and are only used for model-vs-model comparisons.
  If provided, ``zppy`` uses them to locate the MPAS-Analysis config files from a *previous* MPAS-Analysis run and passes those through to MPAS-Analysis as ``controlRunConfigFile`` (reference) and ``mainRunConfigFile`` (test).

  The comparison type of the *current* MPAS-Analysis run is inferred implicitly:
  if ``reference_data_path`` is set, the run is treated as model-vs-model (``mvm``);
  otherwise it is treated as model-vs-observations (``mvo``). Users normally do
  not need to set a comparison type for the current run.

  .. note::
     These parameter names are intentionally consistent with the terminology used by ``e3sm_diags`` for model-vs-model runs: in both cases, ``reference_data_path`` identifies the *reference simulation's zppy-generated outputs*.

     The practical difference is what each downstream tool consumes:
     ``e3sm_diags`` needs ``reference_data_path`` to be the specific directory containing the reference climatology files (typically under the reference run's ``post/.../clim`` tree), whereas ``mpas_analysis`` needs to find the reference MPAS-Analysis config file.
     For MPAS-Analysis, ``zppy`` resolves the config file when ``reference_data_path`` points to the prior run's zppy output directory (the one containing ``post/``).

   ``reference_data_path`` is intended to point to the prior run's zppy output directory (the one containing ``post/``). ``zppy`` will then use:
   ``<reference_data_path>/post/analysis/mpas_analysis/<comparison_type>/cfg/mpas_analysis_<identifier>.cfg``
   where ``<comparison_type>`` is ``mvo`` or ``mvm``.

   For referenced prior runs, ``reference_comparison_type`` and
   ``test_comparison_type`` can be set to ``"auto"``, ``"mvo"``, or ``"mvm"``.
   The default is ``"auto"``. In auto mode:

   * if the path points to ``[[subsection]]``, zppy uses the referenced subsection's actual comparison type
   * if the path points to an external zppy output directory, zppy looks for the matching cfg under ``mvo`` and ``mvm``
   * if both exist for the same identifier, zppy raises an error and the user should set ``reference_comparison_type`` or ``test_comparison_type`` explicitly

   When ``reference_data_path`` is set to a non-subsection path, ``reference_case`` is required so the MVM output directory can include the reference case name. If ``reference_data_path`` is set to ``[[subsection]]``, ``reference_case`` is inferred to be the same as the current ``case``.


**MPAS-Analysis model-vs-model year ranges**

MPAS-Analysis comparisons are configured by year ranges, similar to other ``zppy`` tasks.
For model-vs-model comparisons, ``zppy`` supports separate year ranges for the test and reference runs:

* ``ts_years``, ``climo_years``, ``enso_years`` define the test run year ranges.
   If ``test_data_path`` references a prior ``[mpas_analysis]`` subsection using
   ``[[subsection]]``, and these values are not provided, zppy uses that
   subsection's year ranges instead.
* ``ref_ts_years``, ``ref_climo_years``, ``ref_enso_years`` optionally override the reference run year ranges.

If a ``ref_*_years`` parameter is not provided, it defaults to the corresponding test year ranges.
If ``reference_data_path`` references a prior ``[mpas_analysis]`` subsection using ``[[subsection]]``,
the defaults come from that subsection's year ranges instead.
If a ``ref_*_years`` parameter contains a single range and multiple test ranges are requested, the single reference range is used for each test range.


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
