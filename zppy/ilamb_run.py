import os
import pprint

import jinja2

from zppy.utils import checkStatus, getTasks, getYears, submitScript


# -----------------------------------------------------------------------------
def ilamb_run(config, scriptDir):

    # Initialize jinja2 template engine
    templateLoader = jinja2.FileSystemLoader(
        searchpath=config["default"]["templateDir"]
    )
    templateEnv = jinja2.Environment(loader=templateLoader)
    template = templateEnv.get_template("ilamb_run.bash")

    # --- List of ilamb_run tasks ---
    tasks = getTasks(config, "ilamb_run")
    if len(tasks) == 0:
        return

    # --- Generate and submit ilamb_run scripts ---
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

            # List of dependencies
            dependencies.append(
                os.path.join(
                    scriptDir,
                    "ts_%s_%04d-%04d-%04d.status"
                    % ("land_monthly", c["year1"], c["year2"], c["ts_num_years"]),
                ),
            )
            if not c["land_only"]:
                dependencies.append(
                    os.path.join(
                        scriptDir,
                        "ts_%s_%04d-%04d-%04d.status"
                        % (
                            "atm_monthly_180x360_aave",
                            c["year1"],
                            c["year2"],
                            c["ts_num_years"],
                        ),
                    ),
                )

            prefix = "ilamb_run_%04d-%04d" % (
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

            with open(settingsFile, "w") as sf:
                p = pprint.PrettyPrinter(indent=2, stream=sf)
                p.pprint(c)
                p.pprint(s)

            if not c["dry_run"]:
                # Submit job
                jobid = submitScript(
                    scriptFile, dependFiles=dependencies, export="NONE"
                )

                if jobid != -1:
                    # Update status file
                    with open(statusFile, "w") as f:
                        f.write("WAITING %d\n" % (jobid))
