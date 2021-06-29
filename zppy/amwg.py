import os

import jinja2

from zppy.utils import checkStatus, getTasks, getYears, submitScript


# -----------------------------------------------------------------------------
def amwg(config, scriptDir):

    # Initialize jinja2 template engine
    templateLoader = jinja2.FileSystemLoader(
        searchpath=config["default"]["templateDir"]
    )
    templateEnv = jinja2.Environment(loader=templateLoader)
    template = templateEnv.get_template("amwg.csh")

    # --- List of amwg tasks ---
    tasks = getTasks(config, "amwg")
    if len(tasks) == 0:
        return

    # --- Generate and submit amwg scripts ---
    for c in tasks:

        if ".sh" in c["environment_commands"]:
            c["environment_commands"] = c["environment_commands"].replace(".sh", ".csh")

        # Loop over year sets
        year_sets = getYears(c["years"])
        for s in year_sets:

            c["year1"] = s[0]
            c["year2"] = s[1]
            c["scriptDir"] = scriptDir
            if c["subsection"]:
                sub = c["subsection"]
            else:
                sub = c["grid"]
            prefix = "amwg_%s_%s_%04d-%04d" % (sub, c["tag"], c["year1"], c["year2"])
            print(prefix)
            c["prefix"] = prefix
            scriptFile = os.path.join(scriptDir, "%s.csh" % (prefix))
            statusFile = os.path.join(scriptDir, "%s.status" % (prefix))
            skip = checkStatus(statusFile)
            if skip:
                continue

            # Create script
            with open(scriptFile, "w") as f:
                f.write(template.render(**c))

            # List of dependencies
            dependencies = [
                os.path.join(
                    scriptDir,
                    "climo_%s_%04d-%04d.status" % (c["grid"], c["year1"], c["year2"]),
                ),
            ]

            if not c["dry_run"]:
                # Submit job
                jobid = submitScript(
                    scriptFile, dependFiles=dependencies, export="NONE"
                )

                # Update status file
                with open(statusFile, "w") as f:
                    f.write("WAITING %d\n" % (jobid))
