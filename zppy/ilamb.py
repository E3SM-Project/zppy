import os
import pprint

import jinja2

from zppy.bundle import handle_bundles
from zppy.utils import (
    checkStatus,
    getTasks,
    getYears,
    makeExecutable,
    print_url,
    submitScript,
)


# -----------------------------------------------------------------------------
def ilamb(config, scriptDir, existing_bundles, job_ids_file):

    # Initialize jinja2 template engine
    templateLoader = jinja2.FileSystemLoader(
        searchpath=config["default"]["templateDir"]
    )
    templateEnv = jinja2.Environment(loader=templateLoader)
    template = templateEnv.get_template("ilamb.bash")

    # --- List of ilamb tasks ---
    tasks = getTasks(config, "ilamb")
    if len(tasks) == 0:
        return existing_bundles

    # --- Generate and submit ilamb scripts ---
    dependencies = []

    for c in tasks:

        if "ts_num_years" in c.keys():
            c["ts_num_years"] = int(c["ts_num_years"])

        # Loop over year sets
        year_sets = getYears(c["years"])
        for s in year_sets:
            c["year1"] = s[0]
            c["year2"] = s[1]
            c["scriptDir"] = scriptDir
            if c["subsection"]:
                c["sub"] = c["subsection"]
            else:
                c["sub"] = c["grid"]

            if c["ilamb_obs"] == "":
                ilamb_obs_prefix = c["diagnostics_base_path"]
                ilamb_obs_suffix = "ilamb_data"
                c["ilamb_obs"] = os.path.join(ilamb_obs_prefix, ilamb_obs_suffix)

            # List of dependencies
            dependencies.append(
                os.path.join(
                    scriptDir,
                    "ts_%s_%04d-%04d-%04d.status"
                    % (
                        c["ts_land_subsection"],
                        c["year1"],
                        c["year2"],
                        c["ts_num_years"],
                    ),
                )
            )
            dependencies.append(
                os.path.join(
                    scriptDir,
                    "e3sm_to_cmip_%s_%04d-%04d-%04d.status"
                    % (
                        c["ts_land_subsection"],
                        c["year1"],
                        c["year2"],
                        c["ts_num_years"],
                    ),
                ),
            )
            if not c["land_only"]:
                dependencies.append(
                    os.path.join(
                        scriptDir,
                        "ts_%s_%04d-%04d-%04d.status"
                        % (
                            c["ts_atm_subsection"],
                            c["year1"],
                            c["year2"],
                            c["ts_num_years"],
                        ),
                    ),
                )
                dependencies.append(
                    os.path.join(
                        scriptDir,
                        "e3sm_to_cmip_%s_%04d-%04d-%04d.status"
                        % (
                            c["ts_atm_subsection"],
                            c["year1"],
                            c["year2"],
                            c["ts_num_years"],
                        ),
                    ),
                )

            prefix = "ilamb_%04d-%04d" % (
                c["year1"],
                c["year2"],
            )
            c["prefix"] = prefix
            print(prefix)
            scriptFile = os.path.join(scriptDir, "%s.bash" % (prefix))
            statusFile = os.path.join(scriptDir, "%s.status" % (prefix))
            settingsFile = os.path.join(scriptDir, "%s.settings" % (prefix))
            skip = checkStatus(statusFile)
            if skip:
                continue

            # Create script
            with open(scriptFile, "w") as f:
                f.write(template.render(**c))
            makeExecutable(scriptFile)

            with open(settingsFile, "w") as sf:
                p = pprint.PrettyPrinter(indent=2, stream=sf)
                p.pprint(c)
                p.pprint(s)

            # Note --export=All is needed to make sure the executable is copied and executed on the nodes.
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
                    submitScript(
                        scriptFile,
                        statusFile,
                        export,
                        job_ids_file,
                        dependFiles=dependencies,
                    )
                else:
                    print("...adding to bundle '%s'" % (c["bundle"]))

                print_url(c, "ilamb")

    return existing_bundles
