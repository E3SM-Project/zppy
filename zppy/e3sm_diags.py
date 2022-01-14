import os
import pprint

import jinja2

from zppy.utils import checkStatus, getTasks, getYears, submitScript


# -----------------------------------------------------------------------------
def e3sm_diags(config, scriptDir):

    # Initialize jinja2 template engine
    templateLoader = jinja2.FileSystemLoader(
        searchpath=config["default"]["templateDir"]
    )
    templateEnv = jinja2.Environment(loader=templateLoader)
    template = templateEnv.get_template("e3sm_diags.bash")

    # --- List of e3sm_diags tasks ---
    tasks = getTasks(config, "e3sm_diags")
    if len(tasks) == 0:
        return

    # --- Generate and submit e3sm_diags scripts ---
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
                sub = c["subsection"]
            else:
                sub = c["grid"]
            prefix = "e3sm_diags_%s_%s_%04d-%04d" % (
                sub,
                c["tag"],
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

            # List of dependencies
            dependencies.append(
                os.path.join(
                    scriptDir,
                    "climo_%s_%04d-%04d.status" % (sub, c["year1"], c["year2"]),
                ),
            )
            if "diurnal_cycle" in c["sets"]:
                dependencies.append(
                    os.path.join(
                        scriptDir,
                        "climo_%s_%04d-%04d.status"
                        % (c["climo_diurnal_subsection"], c["year1"], c["year2"]),
                    )
                )
            if "tc_analysis" in c["sets"]:
                dependencies.append(
                    os.path.join(
                        scriptDir,
                        "tc_analysis_%04d-%04d.status" % (c["year1"], c["year2"]),
                    )
                )
            # Iterate from year1 to year2 incrementing by the number of years per time series file.
            if "ts_num_years" in c.keys():
                for yr in range(c["year1"], c["year2"], c["ts_num_years"]):
                    start_yr = yr
                    end_yr = yr + c["ts_num_years"] - 1
                    if (
                        ("enso_diags" in c["sets"])
                        or ("qbo" in c["sets"])
                        or ("area_mean_time_series" in c["sets"])
                    ):
                        dependencies.append(
                            os.path.join(
                                scriptDir,
                                "ts_%s_%04d-%04d-%04d.status"
                                % (sub, start_yr, end_yr, c["ts_num_years"]),
                            )
                        )
                    if "streamflow" in c["sets"]:
                        dependencies.append(
                            os.path.join(
                                scriptDir,
                                "ts_rof_monthly_%04d-%04d-%04d.status"
                                % (start_yr, end_yr, c["ts_num_years"]),
                            )
                        )
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

                # Due to a `socket.gaierror: [Errno -2] Name or service not known` error when running e3sm_diags with tc_analysis
                # on multiple year_sets, if tc_analysis is in sets, then e3sm_diags should be run sequentially.
                if "tc_analysis" in c["sets"]:
                    # Note that this line should still be executed even if jobid == -1
                    # The later tc_analysis-using e3sm_diags tasks still depend on this task (and thus will also fail).
                    # Add to the dependency list
                    dependencies.append(statusFile)
