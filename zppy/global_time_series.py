import os
import pprint

import jinja2

from zppy.utils import checkStatus, getTasks, getYears, submitScript


# -----------------------------------------------------------------------------
def global_time_series(config, scriptDir):

    # Initialize jinja2 template engine
    templateLoader = jinja2.FileSystemLoader(
        searchpath=config["default"]["templateDir"]
    )
    templateEnv = jinja2.Environment(loader=templateLoader)
    template = templateEnv.get_template("global_time_series.bash")

    # --- List of global_time_series tasks ---
    tasks = getTasks(config, "global_time_series")
    if len(tasks) == 0:
        return

    # --- Generate and submit global_time_series scripts ---
    for c in tasks:

        c["ts_num_years"] = int(c["ts_num_years"])

        # Loop over year sets
        year_sets = getYears(c["years"])
        for s in year_sets:
            c["year1"] = s[0]
            c["year2"] = s[1]
            if ("last_year" in c.keys()) and (c["year2"] > c["last_year"]):
                continue  # Skip this year set
            c["scriptDir"] = scriptDir
            prefix = "global_time_series_%04d-%04d" % (c["year1"], c["year2"])
            print(prefix)
            c["prefix"] = prefix
            scriptFile = os.path.join(scriptDir, "%s.bash" % (prefix))
            statusFile = os.path.join(scriptDir, "%s.status" % (prefix))
            settingsFile = os.path.join(scriptDir, "%s.settings" % (prefix))
            skip = checkStatus(statusFile)
            if skip:
                continue

            # Load useful scripts
            c["global_time_series_dir"] = os.path.join(
                scriptDir, "{}_dir".format(prefix)
            )
            if not os.path.exists(c["global_time_series_dir"]):
                os.mkdir(c["global_time_series_dir"])
            scripts = ["coupled_global.py", "readTS.py", "ocean_month.py"]
            for script in scripts:
                script_template = templateEnv.get_template(script)
                script_file = os.path.join(c["global_time_series_dir"], script)
                with open(script_file, "w") as f:
                    f.write(script_template.render(**c))

            # Create script
            with open(scriptFile, "w") as f:
                f.write(template.render(**c))

            # List of dependencies
            dependencies = []
            # Add Time Series dependencies
            # Iterate from year1 to year2 incrementing by the number of years per time series file.
            for yr in range(c["year1"], c["year2"], c["ts_num_years"]):
                start_yr = yr
                end_yr = yr + c["ts_num_years"] - 1
                dependencies.append(
                    os.path.join(
                        scriptDir,
                        "ts_%s_%04d-%04d-%04d.status"
                        % ("atm_monthly_glb", start_yr, end_yr, c["ts_num_years"]),
                    )
                )
            if not c["atmosphere_only"]:
                # Add MPAS Analysis dependencies
                ts_year_sets = getYears(c["ts_years"])
                climo_year_sets = getYears(c["climo_years"])
                for ts_year_set, climo_year_set in zip(ts_year_sets, climo_year_sets):
                    c["ts_year1"] = ts_year_set[0]
                    c["ts_year2"] = ts_year_set[1]
                    c["climo_year1"] = climo_year_set[0]
                    c["climo_year2"] = climo_year_set[1]
                    dependencies.append(
                        os.path.join(
                            scriptDir,
                            "mpas_analysis_ts_%04d-%04d_climo_%04d-%04d.status"
                            % (
                                c["ts_year1"],
                                c["ts_year2"],
                                c["climo_year1"],
                                c["climo_year2"],
                            ),
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
