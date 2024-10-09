from typing import Any, Dict, List, Tuple

from configobj import ConfigObj

from zppy.bundle import handle_bundles
from zppy.utils import (
    check_status,
    get_file_names,
    get_tasks,
    get_years,
    initialize_template,
    make_executable,
    submit_script,
    write_settings_file,
)


# -----------------------------------------------------------------------------
def tc_analysis(config: ConfigObj, script_dir: str, existing_bundles, job_ids_file):

    template, _ = initialize_template(config, "tc_analysis.bash")

    # --- List of <task-name> tasks ---
    tasks: List[Dict[str, Any]] = get_tasks(config, "tc_analysis")
    if len(tasks) == 0:
        return existing_bundles

    # --- Generate and submit <task-name> scripts ---
    # There is a `GenerateConnectivityFile: error while loading shared libraries: libnetcdf.so.11: cannot open shared object file: No such file or directory` error
    # when multiple year_sets are run simultaneously. Therefore, we will wait for the completion of one year_set before moving on to the next.
    dependencies: List[str] = []

    for c in tasks:
        # Loop over year sets
        year_sets: List[Tuple[int, int]] = get_years(c["years"])
        for s in year_sets:
            c["year1"] = s[0]
            c["year2"] = s[1]
            if ("last_year" in c.keys()) and (c["year2"] > c["last_year"]):
                continue  # Skip this year set
            c["scriptDir"] = script_dir
            if c["input_files"]:
                c["atm_name"] = c["input_files"].split(".")[0]
            else:
                raise ValueError("No value was given for `input_files`.")
            prefix = f"tc_analysis_{c['year1']:04d}-{c['year2']:04d}"
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

                    # Note that this line should still be executed even if jobid == -1
                    # The later tc_analysis tasks still depend on this task (and thus will also fail).
                    # Add to the dependency list
                    dependencies.append(status_file)
                else:
                    print(f"...adding to bundle {c['bundle']}")

            print(f"   environment_commands={c['environment_commands']}")

    return existing_bundles
