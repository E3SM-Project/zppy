import os
import pprint
from typing import List

import jinja2

from zppy.bundle import handle_bundles
from zppy.utils import (
    add_dependencies,
    checkStatus,
    getTasks,
    getYears,
    makeExecutable,
    print_url,
    submitScript,
)


# -----------------------------------------------------------------------------
# FIXME: C901 'run' is too complex (19)
def global_time_series(config, scriptDir, existing_bundles, job_ids_file):  # noqa: C901

    # Initialize jinja2 template engine
    templateLoader = jinja2.FileSystemLoader(
        searchpath=config["default"]["templateDir"]
    )
    templateEnv = jinja2.Environment(loader=templateLoader)
    template = templateEnv.get_template("global_time_series.bash")

    # --- List of global_time_series tasks ---
    tasks = getTasks(config, "global_time_series")
    if len(tasks) == 0:
        return existing_bundles

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

            # Handle legacy parameter
            if c["plot_names"]:
                print("warning: plot_names for global_time_series is deprecated.")
                print(
                    "Setting plot_names will override the new parameter, plots_original."
                )
                c["plots_original"] = c["plot_names"]

            # Determine which components are needed
            c["use_atm"] = False
            c["use_ice"] = False
            c["use_lnd"] = False
            c["use_ocn"] = False
            if c["plots_original"]:
                c["use_atm"] = True
                if c["atmosphere_only"]:
                    print(
                        "warning: atmosphere_only for global_time_series is deprecated."
                    )
                    print(
                        "preferred method: remove the 3 ocean plots (change_ohc,max_moc,change_sea_level) from plots_original."
                    )
                has_original_ocn_plots = (
                    ("change_ohc" in c["plots_original"])
                    or ("max_moc" in c["plots_original"])
                    or ("change_sea_level" in c["plots_original"])
                )
                if (not c["atmosphere_only"]) and has_original_ocn_plots:
                    c["use_ocn"] = True
            else:
                # For better string processing in global_time_series.bash
                c["plots_original"] = "None"
            if c["plots_atm"]:
                c["use_atm"] = True
            else:
                # For better string processing in global_time_series.bash
                c["plots_atm"] = "None"
            if c["plots_ice"]:
                c["use_ice"] = True
            else:
                # For better string processing in global_time_series.bash
                c["plots_ice"] = "None"
            if c["plots_lnd"]:
                c["use_lnd"] = True
            else:
                # For better string processing in global_time_series.bash
                c["plots_lnd"] = "None"
            if c["plots_ocn"]:
                c["use_ocn"] = True
            else:
                # For better string processing in global_time_series.bash
                c["plots_ocn"] = "None"

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
                makeExecutable(script_file)

            # Create script
            with open(scriptFile, "w") as f:
                f.write(template.render(**c))
            makeExecutable(scriptFile)

            # List of dependencies
            dependencies: List[str] = []
            # Add Time Series dependencies
            if c["use_atm"]:
                # Iterate from year1 to year2 incrementing by the number of years per time series file.
                for yr in range(c["year1"], c["year2"], c["ts_num_years"]):
                    start_yr = yr
                    end_yr = yr + c["ts_num_years"] - 1
                    add_dependencies(
                        dependencies,
                        scriptDir,
                        "ts",
                        "atm_monthly_glb",
                        start_yr,
                        end_yr,
                        c["ts_num_years"],
                    )
            if c["use_lnd"]:
                for yr in range(c["year1"], c["year2"], c["ts_num_years"]):
                    start_yr = yr
                    end_yr = yr + c["ts_num_years"] - 1
                    add_dependencies(
                        dependencies,
                        scriptDir,
                        "ts",
                        "lnd_monthly_glb",
                        start_yr,
                        end_yr,
                        c["ts_num_years"],
                    )
            if c["use_ocn"]:
                # Add MPAS Analysis dependencies
                ts_year_sets = getYears(c["ts_years"])
                climo_year_sets = getYears(c["climo_years"])
                if (not ts_year_sets) or (not climo_year_sets):
                    raise Exception(
                        "ts_years and climo_years must both be set for ocn plots."
                    )
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
                        scriptFile,
                        statusFile,
                        export,
                        job_ids_file,
                        dependFiles=dependencies,
                    )
                else:
                    print("...adding to bundle '%s'" % (c["bundle"]))

            print(f"   environment_commands={c['environment_commands']}")
            print_url(c, "global_time_series")

    return existing_bundles
