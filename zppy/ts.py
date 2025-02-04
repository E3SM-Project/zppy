from typing import Any, Dict, List, Tuple

from configobj import ConfigObj

from zppy.bundle import handle_bundles
from zppy.utils import (
    ParameterGuessType,
    check_for_deprecated_parameters,
    check_status,
    define_or_guess,
    get_file_names,
    get_tasks,
    get_years,
    initialize_template,
    make_executable,
    set_component_and_prc_typ,
    set_grid,
    set_mapping_file,
    submit_script,
    write_settings_file,
)


# -----------------------------------------------------------------------------
def ts(config: ConfigObj, script_dir: str, existing_bundles, job_ids_file):

    template, _ = initialize_template(config, "ts.bash")

    # --- List of tasks ---
    tasks: List[Dict[str, Any]] = get_tasks(config, "ts")
    if len(tasks) == 0:
        return existing_bundles

    # --- Generate and submit ts scripts ---
    for c in tasks:
        deprecated_parameters = [
            # Removed in https://github.com/E3SM-Project/zppy/pull/650
            "e3sm_to_cmip_environment_commands",
            "ts_fmt",
        ]
        check_for_deprecated_parameters(c, deprecated_parameters)
        set_mapping_file(c)
        set_grid(c)
        set_component_and_prc_typ(c)
        year_sets: List[Tuple[int, int]] = get_years(c["years"])
        # Loop over year sets
        for s in year_sets:
            c["yr_start"] = s[0]
            c["yr_end"] = s[1]
            if ("last_year" in c.keys()) and (c["yr_end"] > c["last_year"]):
                continue  # Skip this year set
            c["ypf"] = s[1] - s[0] + 1
            c["scriptDir"] = script_dir
            sub: str = define_or_guess(
                c, "subsection", "grid", ParameterGuessType.SECTION_GUESS
            )
            prefix = f"ts_{sub}_{c['yr_start']:04d}-{c['yr_end']:04d}-{c['ypf']:04d}"
            print(prefix)
            c["prefix"] = prefix
            bash_file, settings_file, status_file = get_file_names(script_dir, prefix)
            skip: bool = check_status(status_file)
            if skip:
                continue
            # Create script
            with open(bash_file, "w") as f:
                f.write(template.render(**c))
            make_executable(bash_file)
            write_settings_file(settings_file, c, s)
            export = "ALL"
            existing_bundles = handle_bundles(
                c, bash_file, export, existing_bundles=existing_bundles
            )
            if not c["dry_run"]:
                if c["bundle"] == "":
                    # Submit job
                    submit_script(
                        bash_file,
                        status_file,
                        export,
                        job_ids_file,
                        fail_on_dependency_skip=c["fail_on_dependency_skip"],
                    )
                else:
                    print(f"...adding to bundle {c['bundle']}")

            print(f"   environment_commands={c['environment_commands']}")

    return existing_bundles
