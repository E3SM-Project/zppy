import os
from typing import Any, Dict, List, Set, Tuple

from configobj import ConfigObj

from zppy.bundle import handle_bundles
from zppy.utils import (
    ParameterInferenceType,
    ParameterNotProvidedError,
    add_dependencies,
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
def e3sm_diags(config: ConfigObj, script_dir: str, existing_bundles, job_ids_file):

    template, _ = initialize_template(config, "e3sm_diags.bash")

    # --- List of e3sm_diags tasks ---
    tasks: List[Dict[str, Any]] = get_tasks(config, "e3sm_diags")
    if len(tasks) == 0:
        return existing_bundles

    # --- Generate and submit e3sm_diags scripts ---
    for c in tasks:
        dependencies: List[str] = []
        check_parameters_for_bash(c)
        c["scriptDir"] = script_dir
        if "ts_num_years" in c.keys():
            c["ts_num_years"] = int(c["ts_num_years"])
        # Loop over year sets
        year_sets: List[Tuple[int, int]] = get_years(c["years"])
        ref_year_sets: List[Tuple[int, int]]
        if ("ref_years" in c.keys()) and (c["ref_years"] != [""]):
            ref_year_sets = get_years(c["ref_years"])
            # For model_vs_model, use the single reference year set for all test year sets
            if c["run_type"] == "model_vs_model" and len(ref_year_sets) == 1:
                ref_year_sets = ref_year_sets * len(year_sets)
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
            add_climo_dependencies(c, dependencies, script_dir)
            # Iterate from year1 to year2 incrementing by the number of years per time series file.
            if "ts_num_years" in c.keys():
                for yr in range(c["year1"], c["year2"], c["ts_num_years"]):
                    add_ts_dependencies(c, dependencies, script_dir, yr)
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
            print_url(c, "e3sm_diags")

    return existing_bundles


def check_parameter_defined(
    c: Dict[str, Any], relevant_parameter: str, explanation: str = ""
) -> None:
    if (relevant_parameter not in c.keys()) or (c[relevant_parameter] == ""):
        if explanation:
            message = f"{relevant_parameter} is needed because {explanation}"
        else:
            message = f"{relevant_parameter} is not defined."
        raise ParameterNotProvidedError(message)


def check_set_specific_parameter(
    c: Dict[str, Any], sets_with_requirement: Set[str], relevant_parameter: str
) -> None:
    requested_sets = set(c["sets"])
    intersection = sets_with_requirement & requested_sets
    if (
        intersection
        and (relevant_parameter in c.keys())
        and (c[relevant_parameter] == "")
    ):
        raise ParameterNotProvidedError(
            f"{relevant_parameter} is required because the sets {intersection} were requested."
        )


def check_parameters_for_bash(c: Dict[str, Any]) -> None:
    # Check parameters that aren't used until e3sm_diags.bash is run
    check_set_specific_parameter(c, set(["qbo"]), "ref_final_yr")
    check_set_specific_parameter(c, set(["enso_diags", "qbo"]), "ref_start_yr")
    check_set_specific_parameter(c, set(["diurnal_cycle"]), "climo_diurnal_frequency")


def check_mvm_only_parameters_for_bash(c: Dict[str, Any]) -> None:
    # Check mvm-specific parameters that aren't used until e3sm_diags.bash is run.
    check_parameter_defined(c, "diff_title", "mvm requires it.")
    check_parameter_defined(c, "ref_name", "mvm requires it.")
    check_parameter_defined(c, "short_ref_name", "mvm requires it.")

    check_set_specific_parameter(
        c,
        set(["enso_diags", "tropical_subseasonal", "streamflow", "tc_analysis"]),
        "ref_final_yr",
    )
    check_set_specific_parameter(
        c, set(["tropical_subseasonal", "streamflow", "tc_analysis"]), "ref_start_yr"
    )
    ts_sets = set(
        [
            "enso_diags",
            "qbo",
            "area_mean_time_series",
            "tropical_subseasonal",
            "streamflow",
        ]
    )
    check_set_specific_parameter(c, ts_sets, "ts_num_years_ref")
    check_set_specific_parameter(c, ts_sets, "ts_subsection")


def check_and_define_parameters(c: Dict[str, Any]) -> None:
    c["sub"] = get_value_from_parameter(
        c, "subsection", "grid", ParameterInferenceType.SECTION_INFERENCE
    )
    set_value_of_parameter_if_undefined(
        c,
        "reference_data_path",
        f"{c['diagnostics_base_path']}/observations/Atm/climatology/",
        ParameterInferenceType.PATH_INFERENCE,
    )
    if "tc_analysis" in c["sets"]:
        set_value_of_parameter_if_undefined(
            c,
            "tc_obs",
            f"{c['diagnostics_base_path']}/observations/Atm/tc-analysis/",
            ParameterInferenceType.PATH_INFERENCE,
        )
    # TODO: do this based on sets, rather than by relying on the user setting ts_num_years
    if "ts_num_years" in c.keys():
        set_value_of_parameter_if_undefined(
            c,
            "obs_ts",
            f"{c['diagnostics_base_path']}/observations/Atm/time-series/",
            ParameterInferenceType.PATH_INFERENCE,
        )
    prefix: str
    if c["run_type"] == "model_vs_obs":
        prefix = f"e3sm_diags_{c['sub']}_{c['tag']}_{c['year1']:04d}-{c['year2']:04d}"
        if "diurnal_cycle" in c["sets"]:
            set_value_of_parameter_if_undefined(
                c,
                "dc_obs_climo",
                c["reference_data_path"],
                ParameterInferenceType.PATH_INFERENCE,
            )
        if "streamflow" in c["sets"]:
            set_value_of_parameter_if_undefined(
                c,
                "streamflow_obs_ts",
                c["obs_ts"],
                ParameterInferenceType.PATH_INFERENCE,
            )
    elif c["run_type"] == "model_vs_model":
        check_mvm_only_parameters_for_bash(c)
        prefix = f"e3sm_diags_{c['sub']}_{c['tag']}_{c['year1']:04d}-{c['year2']:04d}_vs_{c['ref_year1']:04d}-{c['ref_year2']:04d}"
        reference_data_path = c["reference_data_path"].split("/post")[0] + "/post"
        if "diurnal_cycle" in c["sets"]:
            set_value_of_parameter_if_undefined(
                c,
                "reference_data_path_climo_diurnal",
                f"{reference_data_path}/atm/{c['grid']}/clim_diurnal_8xdaily",
                ParameterInferenceType.PATH_INFERENCE,
            )
        if ("tc_analysis" in c["sets"]) and (c["reference_data_path_tc"] == ""):
            # We have to infer parameters here,
            # because multiple year sets are defined in a single subtask.
            c["reference_data_path_tc"] = (
                f"{reference_data_path}/atm/tc-analysis_{c['ref_year1']}_{c['ref_year2']}"
            )
        if set(["enso_diags", "qbo", "area_mean_time_series"]) & set(c["sets"]):
            set_value_of_parameter_if_undefined(
                c,
                "reference_data_path_ts",
                f"{reference_data_path}/atm/{c['grid']}/ts/monthly",
                ParameterInferenceType.PATH_INFERENCE,
            )
        if "tropical_subseasonal" in c["sets"]:
            set_value_of_parameter_if_undefined(
                c,
                "reference_data_path_ts_daily",
                f"{reference_data_path}/atm/{c['grid']}/ts/daily",
                ParameterInferenceType.PATH_INFERENCE,
            )
        if "streamflow" in c["sets"]:
            set_value_of_parameter_if_undefined(
                c,
                "reference_data_path_ts_rof",
                f"{reference_data_path}/rof/native/ts/monthly",
                ParameterInferenceType.PATH_INFERENCE,
            )
            set_value_of_parameter_if_undefined(
                c,
                "gauges_path",
                os.path.join(
                    c["diagnostics_base_path"],
                    "observations/Atm/time-series/GSIM/GSIM_catchment_characteristics_all_1km2.csv",
                ),
                ParameterInferenceType.PATH_INFERENCE,
            )
    else:
        raise ValueError(f"Invalid run_type={c['run_type']}")
    print(prefix)
    c["prefix"] = prefix


def add_climo_dependencies(
    c: Dict[str, Any], dependencies: List[str], script_dir: str
) -> None:
    depend_on_climo: Set[str] = set(
        [
            "lat_lon",
            # Note: often `lat_lon_land` will require a different climo_subsection
            # than the other sets (e.g., a climo subsection that includes land).
            # That means this set will often need to be run as a separate subtask.
            "lat_lon_land",
            "zonal_mean_xy",
            "zonal_mean_2d",
            "polar",
            "cosp_histogram",
            "meridional_mean_2d",
            "annual_cycle_zonal_mean",
            "zonal_mean_2d_stratosphere",
            "aerosol_aeronet",
            "aerosol_budget",
        ]
    )
    # Check if any requested sets depend on climo:
    status_suffix: str = f"_{c['year1']:04d}-{c['year2']:04d}.status"
    if depend_on_climo & set(c["sets"]):
        climo_sub = get_value_from_parameter(
            c, "climo_subsection", "sub", ParameterInferenceType.SECTION_INFERENCE
        )
        dependencies.append(
            os.path.join(script_dir, f"climo_{climo_sub}{status_suffix}"),
        )
    if "diurnal_cycle" in c["sets"]:
        check_parameter_defined(
            c, "climo_diurnal_subsection", "the set `diurnal_cycle` requires it."
        )
        dependencies.append(
            os.path.join(
                script_dir, f"climo_{c['climo_diurnal_subsection']}{status_suffix}"
            )
        )
    if "tc_analysis" in c["sets"]:
        dependencies.append(os.path.join(script_dir, f"tc_analysis{status_suffix}"))


def add_ts_dependencies(
    c: Dict[str, Any], dependencies: List[str], script_dir: str, yr: int
):
    start_yr = yr
    end_yr = yr + c["ts_num_years"] - 1
    ts_sub = get_value_from_parameter(
        c, "ts_subsection", "sub", ParameterInferenceType.SECTION_INFERENCE
    )
    ts_daily_sub = get_value_from_parameter(
        c, "ts_daily_subsection", "sub", ParameterInferenceType.SECTION_INFERENCE
    )
    depend_on_ts: Set[str] = set(["enso_diags", "qbo", "area_mean_time_series"])
    if depend_on_ts & set(c["sets"]):
        # ts task
        add_dependencies(
            dependencies,
            script_dir,
            "ts",
            ts_sub,
            start_yr,
            end_yr,
            c["ts_num_years"],
        )
    if "streamflow" in c["sets"]:
        add_dependencies(
            dependencies,
            script_dir,
            "ts",
            "rof_monthly",
            start_yr,
            end_yr,
            c["ts_num_years"],
        )
    if "tropical_subseasonal" in c["sets"]:
        add_dependencies(
            dependencies,
            script_dir,
            "ts",
            ts_daily_sub,
            start_yr,
            end_yr,
            c["ts_num_years"],
        )
