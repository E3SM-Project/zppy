import os
import pprint
from typing import List

import jinja2

from zppy.bundle import handle_bundles
from zppy.utils import checkStatus, getTasks, getYears, makeExecutable, submitScript


# -----------------------------------------------------------------------------
def tc_analysis(config, scriptDir, existing_bundles):

    # Initialize jinja2 template engine
    templateLoader = jinja2.FileSystemLoader(
        searchpath=config["default"]["templateDir"]
    )
    templateEnv = jinja2.Environment(loader=templateLoader)
    template = templateEnv.get_template("tc_analysis.bash")

    # --- List of <task-name> tasks ---
    tasks = getTasks(config, "tc_analysis")
    if len(tasks) == 0:
        return existing_bundles

    # --- Generate and submit <task-name> scripts ---

    # There is a `GenerateConnectivityFile: error while loading shared libraries: libnetcdf.so.11: cannot open shared object file: No such file or directory` error
    # when multiple year_sets are run simultaneously. Therefore, we will wait for the completion of one year_set before moving on to the next.
    dependencies: List[str] = []

    for c in tasks:

        # Loop over year sets
        year_sets = getYears(c["years"])
        for s in year_sets:
            c["year1"] = s[0]
            c["year2"] = s[1]
            if ("last_year" in c.keys()) and (c["year2"] > c["last_year"]):
                continue  # Skip this year set
            c["scriptDir"] = scriptDir
            if c["input_files"]:
                c["atm_name"] = c["input_files"].split(".")[0]
            else:
                raise ValueError("No value was given for `input_files`.")
            prefix = "tc_analysis_%04d-%04d" % (
                c["year1"],
                c["year2"],
            )
            print(prefix)
            c["prefix"] = prefix
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

            export = "NONE"
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
                        scriptFile, statusFile, export, dependFiles=dependencies
                    )

                    # Note that this line should still be executed even if jobid == -1
                    # The later tc_analysis tasks still depend on this task (and thus will also fail).
                    # Add to the dependency list
                    dependencies.append(statusFile)
                else:
                    print("...adding to bundle '%s'" % (c["bundle"]))

    return existing_bundles
