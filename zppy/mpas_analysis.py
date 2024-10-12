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
    print_url,
    submit_script,
    write_settings_file,
)


# -----------------------------------------------------------------------------
def mpas_analysis(config: ConfigObj, script_dir: str, existing_bundles, job_ids_file):

    template, _ = initialize_template(config, "mpas_analysis.bash")

    # --- List of mpas_analysis tasks ---
    tasks: List[Dict[str, Any]] = get_tasks(config, "mpas_analysis")
    if len(tasks) == 0:
        return existing_bundles

    # --- Generate and submit mpas_analysis scripts ---
    # MPAS-Analysis uses a shared output directory, so only a single
    # job should run at once. To gracefully handle this, we make each
    # MPAS-Analysis task dependant on all previous ones. This may not
    # be 100% fool-proof, but should be a reasonable start
    dependencies = []
    for c in tasks:
        set_subdirs(config, c)
        # Loop over year sets
        ts_year_sets: List[Tuple[int, int]] = get_years(c["ts_years"])
        climo_year_sets: List[Tuple[int, int]]
        enso_year_sets: List[Tuple[int, int]]
        if c["climo_years"] != [""]:
            climo_year_sets = get_years(c["climo_years"])
        else:
            climo_year_sets = ts_year_sets
        if c["enso_years"] != [""]:
            enso_year_sets = get_years(c["enso_years"])
        else:
            enso_year_sets = ts_year_sets
        for s, rs, es in zip(ts_year_sets, climo_year_sets, enso_year_sets):
            c["ts_year1"] = s[0]
            c["ts_year2"] = s[1]
            if ("last_year" in c.keys()) and (c["ts_year2"] > c["last_year"]):
                continue  # Skip this year set
            c["climo_year1"] = rs[0]
            c["climo_year2"] = rs[1]
            if ("last_year" in c.keys()) and (c["climo_year2"] > c["last_year"]):
                continue  # Skip this year set
            c["enso_year1"] = es[0]
            c["enso_year2"] = es[1]
            if ("last_year" in c.keys()) and (c["enso_year2"] > c["last_year"]):
                continue  # Skip this year set
            c["scriptDir"] = script_dir
            prefix_suffix: str = f"_ts_{c['ts_year1']:04d}-{c['ts_year2']:04d}_climo_{c['climo_year1']:04d}-{c['climo_year2']:04d}"
            prefix: str
            if c["subsection"]:
                prefix = f"mpas_analysis_{c['subsection']}{prefix_suffix}"
            else:
                prefix = f"mpas_analysis{prefix_suffix}"
            print(prefix)
            c["prefix"] = prefix
            bash_file, settings_file, status_file = get_file_names(script_dir, prefix)
            # Check if we can skip because it completed successfully before
            skip: bool = check_status(status_file)
            if skip:
                # Add to the dependency list
                dependencies.append(status_file)
                continue
            # Create script
            with open(bash_file, "w") as f:
                f.write(template.render(**c))
            make_executable(bash_file)
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

                    # Note that this line should still be executed even if jobid == -1
                    # The later MPAS-Analysis tasks still depend on this task (and thus will also fail).
                    # Add to the dependency list
                    dependencies.append(status_file)
                else:
                    print(f"...adding to bundle {c['bundle']}")

            print(f"   environment_commands={c['environment_commands']}")
            print_url(c, "mpas_analysis")

    return existing_bundles


def set_subdirs(config: ConfigObj, c: Dict[str, Any]) -> None:
    if config["mpas_analysis"]["shortTermArchive"]:
        c["subdir_ocean"] = "/archive/ocn/hist"
        c["subdir_ice"] = "/archive/ice/hist"
    else:
        c["subdir_ocean"] = "/run"
        c["subdir_ice"] = "/run"
