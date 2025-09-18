import os
from typing import Any, Dict, List, Set, Tuple

from zppy.bundle import handle_bundles
from zppy.utils import (
    ParameterInferenceType,
    add_dependencies,
    check_parameter_defined,
    check_set_specific_parameter,
    check_status,
    get_file_names,
    get_tasks,
    get_value_from_parameter,
    get_years,
    initialize_template,
    make_executable,
    print_url,
    set_value_of_parameter_if_undefined,
    submit_script,
    write_settings_file,
)


# -----------------------------------------------------------------------------
def pcmdi_diags(config, script_dir, existing_bundles, job_ids_file):

    template, _ = initialize_template(config, "pcmdi_diags.bash")

    # --- List of pcmdi_diags tasks ---
    tasks: List[Dict[str, Any]] = get_tasks(config, "pcmdi_diags")
    if len(tasks) == 0:
        return existing_bundles

    # --- Generate and submit pcmdi_diags scripts ---
    for c in tasks:
        dependencies: List[str] = []
        c["sub"] = get_value_from_parameter(
            c, "subsection", "sub", ParameterInferenceType.SECTION_INFERENCE
        )
        check_parameters_for_bash(c)

        c["scriptDir"] = script_dir
        if "ts_num_years" in c.keys():
            c["ts_num_years"] = int(c["ts_num_years"])

        # procedure type for e3sm_to_cmip
        c["cmor_tables_prefix"] = c["diagnostics_base_path"]

        # check and set parameter for pcmdi
        check_parameters_for_pcmdi(c)

        # Loop over year sets
        year_sets: List[Tuple[int, int]]
        if c["sub"] != "synthetic_plots":
            year_sets = get_years(c["ts_years"])
        else:
            year_sets = get_years(c["figure_sets_period"].split(","))

        ref_year_sets: List[Tuple[int, int]]
        if ("ref_years" in c.keys()) and (c["ref_years"] != [""]):
            ref_year_sets = get_years(c["ref_years"])
        else:
            ref_year_sets = year_sets

        for i, (s, rs) in enumerate(zip(year_sets, ref_year_sets)):
            c["year1"] = s[0]
            c["year2"] = s[1]
            if ("last_year" in c.keys()) and (c["year2"] > c["last_year"]):
                continue  # Skip this year set

            c["ref_year1"] = rs[0]
            c["ref_year2"] = rs[1]

            if c["sub"] != "synthetic_plots":
                check_and_define_parameters(c)
            else:
                prefix = f"pcmdi_diags_{c['sub']}_{c['run_type']}"
                print(prefix)
                c["prefix"] = prefix

            bash_file, settings_file, status_file = get_file_names(
                script_dir, c["prefix"]
            )
            skip: bool = check_status(status_file)
            if skip:
                continue

            # Create script
            with open(bash_file, "w") as f:
                f.write(template.render(**c))
            make_executable(bash_file)

            # List of dependencies
            # Iterate from year1 to year2 incrementing by the number of years per time series file.
            if "ts_num_years" in c.keys():
                for yr in range(c["year1"], c["year2"], c["ts_num_years"]):
                    add_ts_dependencies(c, dependencies, script_dir, yr)
                    set_value_of_parameter_if_undefined(
                        c,
                        "e3sm_to_cmip_atm_subsection",
                        "atm_monthly_180x360_aave",
                        ParameterInferenceType.SECTION_INFERENCE,
                    )
                    add_dependencies(
                        dependencies,
                        script_dir,
                        "e3sm_to_cmip",
                        c["e3sm_to_cmip_atm_subsection"],
                        c["year1"],
                        c["year2"],
                        c["ts_num_years"],
                    )

            if c["sub"] == "synthetic_plots":
                add_pcmdi_dependencies(c, dependencies, script_dir)
                if i < len(year_sets) - 1:
                    continue

            c["dependencies"] = dependencies
            write_settings_file(settings_file, c, s)

            export = "ALL"
            existing_bundles = handle_bundles(
                c,
                bash_file,
                export,
                dependFiles=dependencies,
                existing_bundles=existing_bundles,
            )
            if not c["dry_run"]:
                if c["bundle"] == "":
                    # Submit job
                    submit_script(
                        bash_file,
                        status_file,
                        export,
                        job_ids_file,
                        dependFiles=dependencies,
                        fail_on_dependency_skip=c["fail_on_dependency_skip"],
                    )
                else:
                    print(f"...adding to bundle {c['bundle']}")
            print(f"   environment_commands={c['environment_commands']}")
            print_url(c, "pcmdi_diags")

    return existing_bundles


def check_parameters_for_bash(c: Dict[str, Any]) -> None:
    if c["sub"] != "synthetic_plots":
        check_set_specific_parameter(
            c,
            set(
                ["mean_climate", "variability_mode_cpl", "variability_mode_atm", "enso"]
            ),
            "ref_final_yr",
        )
        check_set_specific_parameter(
            c,
            set(
                ["mean_climate", "variability_mode_cpl", "variability_mode_atm", "enso"]
            ),
            "ref_start_yr",
        )
        check_set_specific_parameter(
            c,
            set(
                ["mean_climate", "variability_mode_cpl", "variability_mode_atm", "enso"]
            ),
            "ref_end_yr",
        )


def check_parameters_for_pcmdi(c: Dict[str, Any]) -> None:
    # check and set up the external data needed by pcmdi
    if c["sub"] == "synthetic_plots":
        set_value_of_parameter_if_undefined(
            c,
            "cmip_enso_dir",
            f"{c['diagnostics_base_path']}/pcmdi_data/metrics_data/enso_metric",
            ParameterInferenceType.PATH_INFERENCE,
        )
        set_value_of_parameter_if_undefined(
            c,
            "cmip_clim_dir",
            f"{c['diagnostics_base_path']}/pcmdi_data/metrics_data/mean_climate",
            ParameterInferenceType.PATH_INFERENCE,
        )
        set_value_of_parameter_if_undefined(
            c,
            "cmip_movs_dir",
            f"{c['diagnostics_base_path']}/pcmdi_data/metrics_data/variability_modes",
            ParameterInferenceType.PATH_INFERENCE,
        )


def check_mvm_only_parameters_for_bash(c: Dict[str, Any]) -> None:
    check_parameter_defined(c, "reference_data_path_ts")
    check_parameter_defined(c, "model_name_ref")
    check_parameter_defined(c, "model_tableID_ref")
    if c["sub"] != "synthetic_plots":
        check_set_specific_parameter(
            c,
            set(
                ["mean_climate", "variability_mode_cpl", "variability_mode_atm", "enso"]
            ),
            "ref_start_yr",
        )
        ts_sets = set(
            [
                "mean_climate",
                "variability_mode_cpl",
                "variability_mode_atm",
                "enso",
            ]
        )
        check_set_specific_parameter(c, ts_sets, "ts_subsection")


def check_and_define_parameters(c: Dict[str, Any]) -> None:
    # TODO, future PR: do this based on sets, rather than by relying on the user setting ts_num_years
    # This is the same item as for e3sm_diags.
    # Here, we'd have to determine which sets of sets "mean_climate","variability_modes_atm","variability_modes_cpl","enso","synthetic_plots" require `ts`
    if "ts_num_years" in c.keys():
        set_value_of_parameter_if_undefined(
            c,
            "obs_ts",
            f"{c['diagnostics_base_path']}/observations/Atm/time-series/",
            ParameterInferenceType.PATH_INFERENCE,
        )
    prefix: str
    if c["run_type"] == "model_vs_obs":
        prefix = (
            f"pcmdi_diags_{c['sub']}_{c['run_type']}_{c['year1']:04d}-{c['year2']:04d}"
        )
    elif c["run_type"] == "model_vs_model":
        check_mvm_only_parameters_for_bash(c)
        prefix = f"pcmdi_diags_{c['sub']}_{c['run_type']}_{c['year1']:04d}-{c['year2']:04d}_vs_{c['ref_year1']:04d}-{c['ref_year2']:04d}"
        reference_data_path = c["reference_data_path"].split("/post")[0] + "/post"
        if set(
            ["mean_climate", "variability_mode_cpl", "variability_mode_atm", "enso"]
        ) & set(c["sets"]):
            set_value_of_parameter_if_undefined(
                c,
                "reference_data_path_ts",
                f"{reference_data_path}/atm/{c['grid']}/cmip_ts/monthly",
                ParameterInferenceType.PATH_INFERENCE,
            )
    else:
        raise ValueError(f"Invalid run_type={c['run_type']}")
    print(prefix)
    c["prefix"] = prefix


def add_ts_dependencies(
    c: Dict[str, Any], dependencies: List[str], script_dir: str, yr: int
):
    start_yr = yr
    end_yr = yr + c["ts_num_years"] - 1
    depend_on_ts: Set[str] = set(
        ["mean_climate", "variability_mode_atm", "variability_mode_cpl", "enso"]
    )
    if depend_on_ts & set(c["sets"]):
        add_dependencies(
            dependencies,
            script_dir,
            "ts",
            "atm_monthly_180x360_aave",
            start_yr,
            end_yr,
            c["ts_num_years"],
        )


def add_pcmdi_dependencies(
    c: Dict[str, Any], dependencies: List[str], script_dir: str
) -> None:
    check_parameter_defined(c, "run_type")
    if c["run_type"] == "model_vs_obs":
        status_suffix = f"_{c['year1']:04d}-{c['year2']:04d}"
    elif c["run_type"] == "model_vs_model":
        status_suffix = f"_{c['year1']:04d}-{c['year2']:04d}_vs_{c['ref_year1']:04d}-{c['ref_year2']:04d}"
    if "mean_climate" in c["sets"]:
        status_file = os.path.join(
            script_dir,
            f"pcmdi_diags_mean_climate_{c['run_type']}{status_suffix}.status",
        )
        if os.path.exists(status_file):
            dependencies.append(status_file)
    if "variability_modes_cpl" in c["sets"]:
        status_file = os.path.join(
            script_dir,
            f"pcmdi_diags_variability_modes_cpl_{c['run_type']}{status_suffix}.status",
        )
        if os.path.exists(status_file):
            dependencies.append(status_file)
    if "variability_modes_atm" in c["sets"]:
        status_file = os.path.join(
            script_dir,
            f"pcmdi_diags_variability_modes_atm_{c['run_type']}{status_suffix}.status",
        )
        if os.path.exists(status_file):
            dependencies.append(status_file)
    if "enso" in c["sets"]:
        status_file = os.path.join(
            script_dir, f"pcmdi_diags_enso_{c['run_type']}{status_suffix}.status"
        )
        if os.path.exists(status_file):
            dependencies.append(status_file)
