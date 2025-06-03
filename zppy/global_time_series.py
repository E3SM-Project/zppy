import os
from typing import Any, Dict, List

from zppy.bundle import handle_bundles
from zppy.logger import _setup_custom_logger
from zppy.utils import (
    add_dependencies,
    check_status,
    get_file_names,
    get_tasks,
    get_years,
    initialize_template,
    make_executable,
    print_url,
    submit_script,
    write_settings_file,
)

logger = _setup_custom_logger(__name__)


# -----------------------------------------------------------------------------
def global_time_series(config, script_dir, existing_bundles, job_ids_file):

    template, template_env = initialize_template(config, "global_time_series.bash")

    # --- List of global_time_series tasks ---
    tasks: List[Dict[str, Any]] = get_tasks(config, "global_time_series")
    if len(tasks) == 0:
        return existing_bundles

    # --- Generate and submit global_time_series scripts ---
    for c in tasks:
        c["ts_num_years"] = int(c["ts_num_years"])
        # Loop over year sets
        year_sets = get_years(c["years"])
        for s in year_sets:
            c["year1"] = s[0]
            c["year2"] = s[1]
            if ("last_year" in c.keys()) and (c["year2"] > c["last_year"]):
                continue  # Skip this year set
            c["scriptDir"] = script_dir
            prefix: str
            if c["subsection"]:
                prefix = f"global_time_series_{c['subsection']}_{c['year1']:04d}-{c['year2']:04d}"
            else:
                prefix = f"global_time_series_{c['year1']:04d}-{c['year2']:04d}"
            print(prefix)
            c["prefix"] = prefix
            bash_file, settings_file, status_file = get_file_names(script_dir, prefix)
            skip: bool = check_status(status_file)
            if skip:
                continue
            determine_components(c)
            # Create script
            with open(bash_file, "w") as f:
                f.write(template.render(**c))
            make_executable(bash_file)
            # List of dependencies
            dependencies: List[str] = []
            # Add Global Time Series dependencies
            determine_and_add_dependencies(c, dependencies, script_dir)
            c["dependencies"] = dependencies
            write_settings_file(settings_file, c, s)
            export = "NONE"
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
            print_url(c, "global_time_series")

    return existing_bundles


def determine_components(c: Dict[str, Any]) -> None:
    # Determine which components are needed
    c["use_atm"] = False
    c["use_ice"] = False
    c["use_lnd"] = False
    c["use_ocn"] = False
    if c["plots_original"]:
        c["use_atm"] = True
        has_original_ocn_plots = (
            ("change_ohc" in c["plots_original"])
            or ("max_moc" in c["plots_original"])
            or ("change_sea_level" in c["plots_original"])
        )
        if has_original_ocn_plots:
            c["use_ocn"] = True
    else:
        # For better string processing in global_time_series.bash
        c["plots_original"] = "None"
    if c["plots_atm"]:
        c["use_atm"] = True
    else:
        # For better string processing in global_time_series.bash
        c["plots_atm"] = "None"
    if c["plots_ice"]:
        c["use_ice"] = True
    else:
        # For better string processing in global_time_series.bash
        c["plots_ice"] = "None"
    if c["plots_lnd"]:
        c["use_lnd"] = True
    else:
        # For better string processing in global_time_series.bash
        c["plots_lnd"] = "None"
    if c["plots_ocn"]:
        c["use_ocn"] = True
    else:
        # For better string processing in global_time_series.bash
        c["plots_ocn"] = "None"
    if ("moc_file" not in c.keys()) or (not c["moc_file"]):
        # For better string processing in global_time_series.bash
        c["moc_file"] = "None"


def determine_and_add_dependencies(
    c: Dict[str, Any], dependencies: List[str], script_dir: str
) -> None:
    if c["use_atm"]:
        # Iterate from year1 to year2 incrementing by the number of years per time series file.
        for yr in range(c["year1"], c["year2"], c["ts_num_years"]):
            start_yr = yr
            end_yr = yr + c["ts_num_years"] - 1
            add_dependencies(
                dependencies,
                script_dir,
                "ts",
                "atm_monthly_glb",
                start_yr,
                end_yr,
                c["ts_num_years"],
            )
    if c["use_lnd"]:
        for yr in range(c["year1"], c["year2"], c["ts_num_years"]):
            start_yr = yr
            end_yr = yr + c["ts_num_years"] - 1
            add_dependencies(
                dependencies,
                script_dir,
                "ts",
                "lnd_monthly_glb",
                start_yr,
                end_yr,
                c["ts_num_years"],
            )
    if c["use_ocn"]:
        # Add MPAS Analysis dependencies
        ts_year_sets = get_years(c["ts_years"])
        climo_year_sets = get_years(c["climo_years"])
        if (not ts_year_sets) or (not climo_year_sets):
            raise Exception("ts_years and climo_years must both be set for ocn plots.")
        for ts_year_set, climo_year_set in zip(ts_year_sets, climo_year_sets):
            c["ts_year1"] = ts_year_set[0]
            c["ts_year2"] = ts_year_set[1]
            c["climo_year1"] = climo_year_set[0]
            c["climo_year2"] = climo_year_set[1]
            dependencies.append(
                os.path.join(
                    script_dir,
                    f"mpas_analysis_ts_{c['ts_year1']:04d}-{c['ts_year2']:04d}_climo_{c['climo_year1']:04d}-{c['climo_year2']:04d}.status",
                )
            )
