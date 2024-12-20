from typing import Any, Dict, List, Tuple

from configobj import ConfigObj

from zppy.bundle import handle_bundles
from zppy.utils import (
    ParameterGuessType,
    add_dependencies,
    check_status,
    define_or_guess,
    define_or_guess2,
    get_file_names,
    get_tasks,
    get_years,
    initialize_template,
    make_executable,
    set_component_and_prc_typ,
    submit_script,
    write_settings_file,
)


# -----------------------------------------------------------------------------
def e3sm_to_cmip(config: ConfigObj, script_dir: str, existing_bundles, job_ids_file):

    template, _ = initialize_template(config, "e3sm_to_cmip.bash")

    # --- List of tasks ---
    tasks: List[Dict[str, Any]] = get_tasks(config, "e3sm_to_cmip")
    if len(tasks) == 0:
        return existing_bundles

    # --- Generate and submit e3sm_to_cmip scripts ---
    for c in tasks:
        dependencies: List[str] = []
        set_component_and_prc_typ(c)
        c["cmor_tables_prefix"] = c["diagnostics_base_path"]
        year_sets: List[Tuple[int, int]] = get_years(c["years"])
        # Loop over year sets
        for s in year_sets:
            c["yr_start"] = s[0]
            c["yr_end"] = s[1]
            if ("last_year" in c.keys()) and (c["yr_end"] > c["last_year"]):
                continue  # Skip this year set
            c["ypf"] = s[1] - s[0] + 1
            c["scriptDir"] = script_dir
            if "ts_num_years" in c.keys():
                c["ts_num_years"] = int(c["ts_num_years"])
            sub: str = define_or_guess(
                c, "subsection", "grid", ParameterGuessType.SECTION_GUESS
            )
            # Run default variables if none are specified
            if c["cmip_vars"] == "":
                if c["component"] == "atm":
                    c["cmip_vars"] = "pr, tas, rsds, rlds, rsus"
                elif c["component"] == "lnd":
                    c["cmip_vars"] = (
                        "mrsos, mrso, mrfso, mrros, mrro, prveg, evspsblveg, evspsblsoi, tran, tsl, lai, cLitter, cProduct, cSoilFast, cSoilMedium, cSoilSlow, fFire, fHarvest, cVeg, nbp, gpp, ra, rh"
                    )
            prefix = f"e3sm_to_cmip_{sub}_{c['yr_start']:04d}-{c['yr_end']:04d}-{c['ypf']:04d}"
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
            # Default to the name of this task if ts_subsection is not defined
            define_or_guess2(c, "ts_subsection", sub, ParameterGuessType.SECTION_GUESS)
            add_dependencies(
                dependencies,
                script_dir,
                "ts",
                c["ts_subsection"],
                c["yr_start"],
                c["yr_end"],
                c["ts_num_years"],
            )
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

    return existing_bundles
