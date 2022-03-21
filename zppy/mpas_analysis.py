import os
import pprint

import jinja2

from zppy.utils import checkStatus, getTasks, getYears, handle_bundles, submitScript


# -----------------------------------------------------------------------------
def mpas_analysis(config, scriptDir, existing_bundles):

    # Initialize jinja2 template engine
    templateLoader = jinja2.FileSystemLoader(
        searchpath=config["default"]["templateDir"]
    )
    templateEnv = jinja2.Environment(loader=templateLoader)
    template = templateEnv.get_template("mpas_analysis.bash")

    # --- List of mpas_analysis tasks ---
    tasks = getTasks(config, "mpas_analysis")
    if len(tasks) == 0:
        return existing_bundles

    # --- Generate and submit mpas_analysis scripts ---

    # MPAS-Analysis uses a shared output directory, so only a single
    # job should run at once. To gracefully handle this, we make each
    # MAPS-Analysis task dependant on all previous ones. This may not
    # be 100% fool-proof, but should be a reasonable start
    dependencies = []

    for c in tasks:

        if config["mpas_analysis"]["shortTermArchive"]:
            c["subdir_ocean"] = "/archive/ocn/hist"
            c["subdir_ice"] = "/archive/ice/hist"
        else:
            c["subdir_ocean"] = "/run"
            c["subdir_ice"] = "/run"

        # Loop over year sets
        ts_year_sets = getYears(c["ts_years"])
        if c["climo_years"] != [""]:
            climo_year_sets = getYears(c["climo_years"])
        else:
            climo_year_sets = ts_year_sets
        if c["enso_years"] != [""]:
            enso_year_sets = getYears(c["enso_years"])
        else:
            enso_year_sets = ts_year_sets

        for s, rs, es in zip(ts_year_sets, climo_year_sets, enso_year_sets):

            c["ts_year1"] = s[0]
            c["ts_year2"] = s[1]
            if ("last_year" in c.keys()) and (c["ts_year2"] > c["last_year"]):
                continue  # Skip this year set
            c["climo_year1"] = rs[0]
            c["climo_year2"] = rs[1]
            if ("last_year" in c.keys()) and (c["climo_year2"] > c["last_year"]):
                continue  # Skip this year set
            c["enso_year1"] = es[0]
            c["enso_year2"] = es[1]
            if ("last_year" in c.keys()) and (c["enso_year2"] > c["last_year"]):
                continue  # Skip this year set
            c["scriptDir"] = scriptDir
            if c["subsection"]:
                prefix = "mpas_analysis_%s_ts_%04d-%04d_climo_%04d-%04d" % (
                    c["subsection"],
                    c["ts_year1"],
                    c["ts_year2"],
                    c["climo_year1"],
                    c["climo_year2"],
                )
            else:
                prefix = "mpas_analysis_ts_%04d-%04d_climo_%04d-%04d" % (
                    c["ts_year1"],
                    c["ts_year2"],
                    c["climo_year1"],
                    c["climo_year2"],
                )
            print(prefix)
            c["prefix"] = prefix
            scriptFile = os.path.join(scriptDir, "%s.bash" % (prefix))
            statusFile = os.path.join(scriptDir, "%s.status" % (prefix))
            settingsFile = os.path.join(scriptDir, "%s.settings" % (prefix))

            # Check if we can skip because it completed successfully before
            skip = checkStatus(statusFile)
            if skip:
                # Add to the dependency list
                dependencies.append(statusFile)
                continue

            # Create script
            with open(scriptFile, "w") as f:
                f.write(template.render(**c))

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
            if not ((c["bundle"] != "") or c["dry_run"]):
                # Submit job
                jobid = submitScript(scriptFile, export, dependFiles=dependencies)

                if jobid != -1:
                    # Update status file
                    with open(statusFile, "w") as f:
                        f.write("WAITING %d\n" % (jobid))

                # Note that this line should still be executed even if jobid == -1
                # The later MPAS-Analysis tasks still depend on this task (and thus will also fail).
                # Add to the dependency list
                dependencies.append(statusFile)
    return existing_bundles
