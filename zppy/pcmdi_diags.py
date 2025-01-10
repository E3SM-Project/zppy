import os
from typing import Any, Dict, List, Set, Tuple

from zppy.bundle import handle_bundles
from zppy.utils import (
    ParameterGuessType,
    add_dependencies,
    check_parameter_defined,
    check_required_parameters,
    check_status,
    define_or_guess,
    define_or_guess2,
    get_file_names,
    get_tasks,
    get_years,
    initialize_template,
    make_executable,
    print_url,
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
        check_parameters_for_bash(c)
        c["scriptDir"] = script_dir
        if "ts_num_years" in c.keys():
            c["ts_num_years"] = int(c["ts_num_years"])

        # procedure type for e3sm_to_cmip
        c["cmor_tables_prefix"] = c["diagnostics_base_path"]

        # check and set parameter for pcmdi
        c["pcmdi_external_prefix"] = c["diagnostics_base_path"]
        check_parameters_for_pcmdi(c)

        # Loop over year sets
        year_sets: List[Tuple[int, int]] = get_years(c["ts_years"])
        ref_year_sets: List[Tuple[int, int]]
        if ("ref_years" in c.keys()) and (c["ref_years"] != [""]):
            ref_year_sets = get_years(c["ref_years"])
        else:
            ref_year_sets = year_sets
        for s, rs in zip(year_sets, ref_year_sets):
            c["year1"] = s[0]
            c["year2"] = s[1]
            if ("last_year" in c.keys()) and (c["year2"] > c["last_year"]):
                continue  # Skip this year set

            c["ref_year1"] = rs[0]
            c["ref_year2"] = rs[1]

            check_and_define_parameters(c)
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

            add_pcmdi_dependencies(c, dependencies, script_dir)

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
    check_required_parameters(
        c,
        set(["mean_climate", "variability_mode_cpl", "variability_mode_atm", "enso"]),
        "ref_final_yr",
    )
    check_required_parameters(
        c, set(["variability_mode_cpl", "variability_mode_atm", "enso"]), "ref_start_yr"
    )
    check_required_parameters(
        c, set(["variability_mode_cpl", "variability_mode_atm", "enso"]), "ref_end_yr"
    )


def check_parameters_for_pcmdi(c: Dict[str, Any]) -> None:
    # check and set up the external data needed by pcmdi
    if set(["synthetic_plots"]) & set(c["sets"]):
        define_or_guess2(
            c,
            "cmip_enso_dir",
            f"{c['diagnostics_base_path']}/pcmdi_data/metrics_data/enso_metric",
            ParameterGuessType.PATH_GUESS,
        )
        define_or_guess2(
            c,
            "cmip_clim_dir",
            f"{c['diagnostics_base_path']}/pcmdi_data/metrics_data/mean_climate",
            ParameterGuessType.PATH_GUESS,
        )
        define_or_guess2(
            c,
            "cmip_movs_dir",
            f"{c['diagnostics_base_path']}/pcmdi_data/metrics_data/variability_modes",
            ParameterGuessType.PATH_GUESS,
        )


def check_mvm_only_parameters_for_bash(c: Dict[str, Any]) -> None:
    check_parameter_defined(c, "diff_title")
    check_parameter_defined(c, "ref_name")
    check_parameter_defined(c, "short_ref_name")

    check_required_parameters(
        c,
        set(["mean_climate", "variability_mode_cpl", "variability_mode_atm", "enso"]),
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
    check_required_parameters(c, ts_sets, "ts_num_years_ref")
    check_required_parameters(c, ts_sets, "ts_subsection")


def check_and_define_parameters(c: Dict[str, Any]) -> None:
    c["sub"] = define_or_guess(
        c, "subsection", "grid", ParameterGuessType.SECTION_GUESS
    )
    # TODO: do this based on sets, rather than by relying on the user setting ts_num_years
    if "ts_num_years" in c.keys():
        define_or_guess2(
            c,
            "obs_ts",
            f"{c['diagnostics_base_path']}/observations/Atm/time-series/",
            ParameterGuessType.PATH_GUESS,
        )
    prefix: str
    if c["run_type"] == "model_vs_obs":
        prefix = f"pcmdi_diags_{c['sub']}_{c['tag']}_{c['year1']:04d}-{c['year2']:04d}"

    elif c["run_type"] == "model_vs_model":
        check_mvm_only_parameters_for_bash(c)
        prefix = f"pcmdi_diags_{c['sub']}_{c['tag']}_{c['year1']:04d}-{c['year2']:04d}_vs_{c['ref_year1']:04d}-{c['ref_year2']:04d}"
        reference_data_path = c["reference_data_path"].split("/post")[0] + "/post"
        if set(
            ["mean_climate", "variability_mode_cpl", "variability_mode_atm", "enso"]
        ) & set(c["sets"]):
            define_or_guess2(
                c,
                "reference_data_path_ts",
                f"{reference_data_path}/atm/{c['grid']}/cmip_ts/monthly",
                ParameterGuessType.PATH_GUESS,
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
    pcmdi_sub = define_or_guess(
        c, "pcmdi_diags", "sub", ParameterGuessType.SECTION_GUESS
    )
    status_suffix: str = f"_{c['year1']:04d}-{c['year2']:04d}.status"
    if "synthetic_plots" in pcmdi_sub:
        check_parameter_defined(c, "run_type")
        if "mean_climate" in c["sets"]:
            dependencies.append(
                os.path.join(
                    script_dir,
                    f"pcmdi_diags_mean_climate_{c['run_type']}{status_suffix}",
                )
            )
        if "variability_mode_cpl" in c["sets"]:
            dependencies.append(
                os.path.join(
                    script_dir,
                    f"pcmdi_diags_variability_mode_cpl_{c['run_type']}{status_suffix}",
                )
            )
        if "variability_mode_atm" in c["sets"]:
            dependencies.append(
                os.path.join(
                    script_dir,
                    f"pcmdi_diags_variability_mode_atm_{c['run_type']}{status_suffix}",
                )
            )
        if "enso" in c["sets"]:
            dependencies.append(
                os.path.join(
                    script_dir, f"pcmdi_diags_enso_{c['run_type']}{status_suffix}"
                )
            )
