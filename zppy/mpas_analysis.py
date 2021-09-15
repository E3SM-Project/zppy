import os

import jinja2

from zppy.utils import checkStatus, getTasks, getYears, submitScript


# -----------------------------------------------------------------------------
def mpas_analysis(config, scriptDir):

    # Initialize jinja2 template engine
    templateLoader = jinja2.FileSystemLoader(
        searchpath=config["default"]["templateDir"]
    )
    templateEnv = jinja2.Environment(loader=templateLoader)
    template = templateEnv.get_template("mpas_analysis.bash")

    # --- List of mpas_analysis tasks ---
    tasks = getTasks(config, "mpas_analysis")
    if len(tasks) == 0:
        return

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

        if c["campaign"] == "water_cycle":
            c["generate"] = [
                "all",
                "no_landIceCavities",
                "no_BGC",
                "no_icebergs",
                "no_min",
                "no_max",
                "no_sose",
                "no_climatologyMapAntarcticMelt",
                "no_regionalTSDiagrams",
                "no_timeSeriesAntarcticMelt",
                "no_timeSeriesOceanRegions",
                "no_climatologyMapSose",
                "no_woceTransects",
                "no_soseTransects",
                "no_geojsonTransects",
                "no_oceanRegionalProfiles",
                "no_hovmollerOceanRegions",
            ]

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
            c["climo_year1"] = rs[0]
            c["climo_year2"] = rs[1]
            c["enso_year1"] = es[0]
            c["enso_year2"] = es[1]
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

            # Check if we can skip because it completed successfully before
            skip = checkStatus(statusFile)
            if skip:
                # Add to the dependency list
                dependencies.append(statusFile)
                continue

            # Create script
            with open(scriptFile, "w") as f:
                f.write(template.render(**c))

            if not c["dry_run"]:
                # Submit job
                jobid = submitScript(scriptFile, dependFiles=dependencies)

                if jobid != -1:
                    # Update status file
                    with open(statusFile, "w") as f:
                        f.write("WAITING %d\n" % (jobid))

                # Note that this line should still be executed even if jobid == -1
                # The later MPAS-Analysis tasks still depend on this task (and thus will also fail).
                # Add to the dependency list
                dependencies.append(statusFile)
