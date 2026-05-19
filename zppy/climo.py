from typing import Any, Dict, List, Tuple

from configobj import ConfigObj

from zppy.bundle import handle_bundles
from zppy.utils import (
    ParameterInferenceType,
    check_status,
    get_file_names,
    get_tasks,
    get_value_from_parameter,
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
def climo(config: ConfigObj, script_dir: str, existing_bundles, job_ids_file):

    template, _ = initialize_template(config, "climo.bash")

    # --- List of climo tasks ---
    tasks: List[Dict[str, Any]] = get_tasks(config, "climo")
    if len(tasks) == 0:
        return existing_bundles

    # --- Generate and submit climo scripts ---
    for c in tasks:
        set_mapping_file(c)
        set_grid(c)
        set_component_and_prc_typ(c)
        # Compose the climo output filename prefix. For EAMxx, subsection-level
        # `case` (e.g., "1ma_ne30pg2") is the stream id ncclimo needs to find
        # input files; prefixing with the top-level case keeps output names
        # unified across streams so a single e3sm_diags subsection can consume
        # both monthly and diurnal climo via one `case` setting.
        if c["prc_typ"] == "eamxx" and c["case"] != c["default_case"]:
            c["fml_nm"] = f"{c['default_case']}.{c['case']}"
        else:
            c["fml_nm"] = c["case"]
        year_sets: List[Tuple[int, int]] = get_years(c["years"])
        # Loop over year sets
        for s in year_sets:
            c["yr_start"] = s[0]
            c["yr_end"] = s[1]
            if ("last_year" in c.keys()) and (c["yr_end"] > c["last_year"]):
                continue  # Skip this year set
            c["scriptDir"] = script_dir
            sub: str = get_value_from_parameter(
                c, "subsection", "grid", ParameterInferenceType.SECTION_INFERENCE
            )
            prefix: str = f"climo_{sub}_{c['yr_start']:04d}-{c['yr_end']:04d}"
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
