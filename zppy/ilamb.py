import os
from typing import Any, Dict, List

from configobj import ConfigObj

from zppy.bundle import handle_bundles
from zppy.utils import (
    ParameterGuessType,
    add_dependencies,
    check_status,
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
def ilamb(config: ConfigObj, script_dir: str, existing_bundles, job_ids_file):

    template, _ = initialize_template(config, "ilamb.bash")

    # --- List of ilamb tasks ---
    tasks: List[Dict[str, Any]] = get_tasks(config, "ilamb")
    if len(tasks) == 0:
        return existing_bundles

    # --- Generate and submit ilamb scripts ---
    for c in tasks:

        dependencies: List[str] = []

        if "ts_num_years" in c.keys():
            c["ts_num_years"] = int(c["ts_num_years"])
        # Loop over year sets
        year_sets = get_years(c["years"])
        for s in year_sets:
            c["year1"] = s[0]
            c["year2"] = s[1]
            c["scriptDir"] = script_dir
            define_or_guess2(
                c,
                "ilamb_obs",
                os.path.join(c["diagnostics_base_path"], "ilamb_data"),
                ParameterGuessType.PATH_GUESS,
            )
            # List of dependencies
            determine_and_add_dependencies(c, dependencies, script_dir)
            prefix: str = f"ilamb_{c['year1']:04d}-{c['year2']:04d}"
            c["prefix"] = prefix
            print(prefix)
            bash_file, settings_file, status_file = get_file_names(script_dir, prefix)
            skip: bool = check_status(status_file)
            if skip:
                continue
            # Create script
            with open(bash_file, "w") as f:
                f.write(template.render(**c))
            make_executable(bash_file)
            c["dependencies"] = dependencies
            write_settings_file(settings_file, c, s)

            # Note --export=All is needed to make sure the executable is copied and executed on the nodes.
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
                    print("...adding to bundle '{c['bundle']}'")

            print(f"   environment_commands={c['environment_commands']}")
            print_url(c, "ilamb")

    return existing_bundles


def determine_and_add_dependencies(
    c: Dict[str, Any], dependencies: List[str], script_dir: str
) -> None:
    define_or_guess2(
        c, "ts_land_subsection", "land_monthly", ParameterGuessType.SECTION_GUESS
    )
    add_dependencies(
        dependencies,
        script_dir,
        "ts",
        c["ts_land_subsection"],
        c["year1"],
        c["year2"],
        c["ts_num_years"],
    )
    add_dependencies(
        dependencies,
        script_dir,
        "e3sm_to_cmip",
        c[
            "ts_land_subsection"
        ],  # Relies on having the same subsection name as the corresponding ts subsection!
        c["year1"],
        c["year2"],
        c["ts_num_years"],
    )
    if not c["land_only"]:
        define_or_guess2(
            c,
            "ts_atm_subsection",
            "atm_monthly_180x360_aave",
            ParameterGuessType.SECTION_GUESS,
        )
        add_dependencies(
            dependencies,
            script_dir,
            "ts",
            c["ts_atm_subsection"],
            c["year1"],
            c["year2"],
            c["ts_num_years"],
        )
        add_dependencies(
            dependencies,
            script_dir,
            "e3sm_to_cmip",
            c[
                "ts_atm_subsection"
            ],  # Relies on having the same subsection name as the corresponding ts subsection!
            c["year1"],
            c["year2"],
            c["ts_num_years"],
        )
