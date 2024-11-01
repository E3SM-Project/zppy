import os
import pprint
from typing import List

import jinja2

from zppy.bundle import handle_bundles
from zppy.utils import (
    add_dependencies,
    check_status,
    get_tasks,
    get_years,
    make_executable,
    print_url,
    submit_script,
)


# -----------------------------------------------------------------------------
def pcmdi_diags(config, script_dir, existing_bundles, job_ids_file):

    # Initialize jinja2 template engine
    templateLoader = jinja2.FileSystemLoader(
        searchpath=config["default"]["templateDir"]
    )
    templateEnv = jinja2.Environment(loader=templateLoader)
    template = templateEnv.get_template("pcmdi_diags.bash")

    # --- List of pcmdi_diags tasks ---
    tasks = get_tasks(config, "pcmdi_diags")
    if len(tasks) == 0:
        return existing_bundles

    # --- Generate and submit pcmdi_diags scripts ---
    dependencies: List[str] = []

    for c in tasks:

        c["scriptDir"] = script_dir

        if "ts_num_years" in c.keys():
            c["ts_num_years"] = int(c["ts_num_years"])

        # procedure type for e3sm_to_cmip
        c["cmor_tables_prefix"] = c["diagnostics_base_path"]

        # Loop over year sets
        year_sets = get_years(c["ts_years"])
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
            if c["subsection"]:
                c["sub"] = c["subsection"]
            else:
                c["sub"] = c["grid"]
            # Make a guess for observation paths, if need be
            if ("ts_num_years" in c.keys()) and (c["obs_ts"] == ""):
                c["obs_ts"] = (
                    f"{c['diagnostics_base_path']}/observations/Atm/time-series/"
                )
            if c["run_type"] == "model_vs_obs":
                prefix = "pcmdi_diags_%s_%s_%04d-%04d" % (
                    c["sub"],
                    c["tag"],
                    c["year1"],
                    c["year2"],
                )
            elif c["run_type"] == "model_vs_model":
                prefix = "pcmdi_diags_%s_%s_%04d-%04d_vs_%04d-%04d" % (
                    c["sub"],
                    c["tag"],
                    c["year1"],
                    c["year2"],
                    c["ref_year1"],
                    c["ref_year2"],
                )
                reference_data_path = (
                    c["reference_data_path"].split("/post")[0] + "/post"
                )
                if ("ts_num_years" in c.keys()) and (c["reference_data_path_ts"] == ""):
                    c["reference_data_path_ts"] = (
                        f"{reference_data_path}/atm/{c['grid']}/cmip_ts/monthly"
                    )
            else:
                raise ValueError("Invalid run_type={}".format(c["run_type"]))
            print(prefix)
            c["prefix"] = prefix
            scriptFile = os.path.join(script_dir, "%s.bash" % (prefix))
            statusFile = os.path.join(script_dir, "%s.status" % (prefix))
            settingsFile = os.path.join(script_dir, "%s.settings" % (prefix))
            skip = check_status(statusFile)
            if skip:
                continue

            # Create script
            with open(scriptFile, "w") as f:
                f.write(template.render(**c))
            make_executable(scriptFile)

            # Iterate from year1 to year2 incrementing by the number of years per time series file.
            if "ts_num_years" in c.keys():
                for yr in range(c["year1"], c["year2"], c["ts_num_years"]):
                    start_yr = yr
                    end_yr = yr + c["ts_num_years"] - 1
                    if (
                        ("mean_climate" in c["sets"])
                        or ("variability_mode_atm" in c["sets"])
                        or ("variability_mode_cpl" in c["sets"])
                        or ("enso" in c["sets"])
                    ):
                        add_dependencies(
                            dependencies,
                            script_dir,
                            "ts",
                            "atm_monthly_180x360_aave",
                            start_yr,
                            end_yr,
                            c["ts_num_years"],
                        )
            with open(settingsFile, "w") as sf:
                p = pprint.PrettyPrinter(indent=2, stream=sf)
                p.pprint(c)
                p.pprint(s)

            export = "ALL"
            existing_bundles = handle_bundles(
                c,
                scriptFile,
                export,
                dependFiles=dependencies,
                existing_bundles=existing_bundles,
            )
            if not c["dry_run"]:
                if c["bundle"] == "":
                    # Submit job
                    submit_script(
                        scriptFile,
                        statusFile,
                        export,
                        job_ids_file,
                        dependFiles=dependencies,
                    )

                else:
                    print("...adding to bundle '%s'" % (c["bundle"]))

            print(f"   environment_commands={c['environment_commands']}")
            print_url(c, "pcmdi_diags")

    return existing_bundles
