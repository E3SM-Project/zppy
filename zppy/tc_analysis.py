import os
import pprint

import jinja2

from zppy.utils import checkStatus, getTasks, getYears, submitScript


# -----------------------------------------------------------------------------
def tc_analysis(config, scriptDir):

    # Initialize jinja2 template engine
    templateLoader = jinja2.FileSystemLoader(
        searchpath=config["default"]["templateDir"]
    )
    templateEnv = jinja2.Environment(loader=templateLoader)
    template = templateEnv.get_template("tc_analysis.bash")

    # --- List of <task-name> tasks ---
    tasks = getTasks(config, "tc_analysis")
    if len(tasks) == 0:
        return

    # --- Generate and submit <task-name> scripts ---
    for c in tasks:

        # Loop over year sets
        year_sets = getYears(c["years"])
        for s in year_sets:
            c["year1"] = s[0]
            c["year2"] = s[1]
            c["scriptDir"] = scriptDir
            if c["input_files"]:
                c["atm_name"] = c["input_files"].split(".")[0]
            else:
                raise Exception("No value was given for `input_files`.")
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

            with open(settingsFile, "w") as sf:
                p = pprint.PrettyPrinter(indent=2, stream=sf)
                p.pprint(c)
                p.pprint(s)

            if not c["dry_run"]:
                # Submit job
                jobid = submitScript(scriptFile, export="NONE")

                if jobid != -1:
                    # Update status file
                    with open(statusFile, "w") as f:
                        f.write("WAITING %d\n" % (jobid))
