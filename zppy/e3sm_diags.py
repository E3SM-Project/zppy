import os
import pprint

import jinja2

from zppy.bundle import handle_bundles

from zppy.utils import (
    checkStatus,
    getTasks,
    getYears,
    makeExecutable,
    submitScript,
)


# -----------------------------------------------------------------------------
# FIXME: C901 'e3sm_diags' is too complex (20)
def e3sm_diags(config, scriptDir, existing_bundles):  # noqa: C901

    # Initialize jinja2 template engine
    templateLoader = jinja2.FileSystemLoader(
        searchpath=config["default"]["templateDir"]
    )
    templateEnv = jinja2.Environment(loader=templateLoader)
    template = templateEnv.get_template("e3sm_diags.bash")

    # --- List of e3sm_diags tasks ---
    tasks = getTasks(config, "e3sm_diags")
    if len(tasks) == 0:
        return existing_bundles

    # --- Generate and submit e3sm_diags scripts ---
    dependencies = []

    for c in tasks:

        if "ts_num_years" in c.keys():
            c["ts_num_years"] = int(c["ts_num_years"])

        # Loop over year sets
        year_sets = getYears(c["years"])
        if ("ref_years" in c.keys()) and (c["ref_years"] != [""]):
            ref_year_sets = getYears(c["ref_years"])
        else:
            ref_year_sets = year_sets
        for s, rs in zip(year_sets, ref_year_sets):
            c["year1"] = s[0]
            c["year2"] = s[1]
            if ("last_year" in c.keys()) and (c["year2"] > c["last_year"]):
                continue  # Skip this year set
            c["ref_year1"] = rs[0]
            c["ref_year2"] = rs[1]
            c["scriptDir"] = scriptDir
            if c["subsection"]:
                c["sub"] = c["subsection"]
            else:
                c["sub"] = c["grid"]
            if c["run_type"] == "model_vs_obs":
                prefix = "e3sm_diags_%s_%s_%04d-%04d" % (
                    c["sub"],
                    c["tag"],
                    c["year1"],
                    c["year2"],
                )
            elif c["run_type"] == "model_vs_model":
                prefix = "e3sm_diags_%s_%s_%04d-%04d_vs_%04d-%04d" % (
                    c["sub"],
                    c["tag"],
                    c["year1"],
                    c["year2"],
                    c["ref_year1"],
                    c["ref_year2"],
                )
                reference_data_path = (
                    c["reference_data_path"].split("/post")[0] + "/post"
                )
                if c["reference_data_path_climo_diurnal"] == "":
                    c[
                        "reference_data_path_climo_diurnal"
                    ] = f"{reference_data_path}/atm/{c['grid']}/clim_diurnal_8xdaily"
                if c["reference_data_path_tc"] == "":
                    c[
                        "reference_data_path_tc"
                    ] = f"{reference_data_path}/atm/tc-analysis_{c['ref_year1']}_{c['ref_year2']}"
                if c["reference_data_path_ts"] == "":
                    c[
                        "reference_data_path_ts"
                    ] = f"{reference_data_path}/atm/{c['grid']}/ts/monthly"
                if c["reference_data_path_ts_rof"] == "":
                    c[
                        "reference_data_path_ts_rof"
                    ] = f"{reference_data_path}/rof/native/ts/monthly"
                if c["gauges_path"] == "":
                    gauges_path_suffix = (
                        "time-series/GSIM/GSIM_catchment_characteristics_all_1km2.csv"
                    )
                    if c["machine"] == "compy":
                        gauges_path_prefix = (
                            "/compyfs/e3sm_diags_data/obs_for_e3sm_diags/"
                        )
                    elif c["machine"] == "cori":
                        gauges_path_prefix = (
                            "/global/cfs/cdirs/e3sm/e3sm_diags/obs_for_e3sm_diags/"
                        )
                    elif c["machine"] in ["anvil", "chrysalis"]:
                        gauges_path_prefix = "/lcrc/group/e3sm/public_html/e3sm_diags_test_data/unit_test_complete_run/obs/"
                    else:
                        raise ValueError(f"Invalid machine={c['machine']}")
                    c["gauges_path"] = os.path.join(
                        gauges_path_prefix, gauges_path_suffix
                    )
            else:
                raise ValueError("Invalid run_type={}".format(c["run_type"]))
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

            # List of dependencies
            depend_on_climo = set(
                [
                    "lat_lon",
                    "zonal_mean_xy",
                    "zonal_mean_2d",
                    "polar",
                    "cosp_histogram",
                    "meridional_mean_2d",
                    "annual_cycle_zonal_mean",
                    "zonal_mean_2d_stratosphere",
                ]
            )
            in_sets = set(c["sets"])
            # Check if any requested sets depend on climo:
            if depend_on_climo & in_sets:
                if "climo_subsection" in c.keys() and c["climo_subsection"] != "":
                    climo_sub = c["climo_subsection"]
                else:
                    climo_sub = c["sub"]
                dependencies.append(
                    os.path.join(
                        scriptDir,
                        "climo_%s_%04d-%04d.status"
                        % (climo_sub, c["year1"], c["year2"]),
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
                    if "ts_subsection" in c.keys() and c["ts_subsection"] != "":
                        ts_sub = c["ts_subsection"]
                    else:
                        ts_sub = c["sub"]
                    if (
                        ("enso_diags" in c["sets"])
                        or ("qbo" in c["sets"])
                        or ("area_mean_time_series" in c["sets"])
                    ):
                        dependencies.append(
                            os.path.join(
                                scriptDir,
                                "ts_%s_%04d-%04d-%04d.status"
                                % (ts_sub, start_yr, end_yr, c["ts_num_years"]),
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
                    jobid = submitScript(scriptFile, statusFile, export, dependFiles=dependencies)

                    # Due to a `socket.gaierror: [Errno -2] Name or service not known` error when running e3sm_diags with tc_analysis
                    # on multiple year_sets, if tc_analysis is in sets, then e3sm_diags should be run sequentially.
                    if "tc_analysis" in c["sets"]:
                        # Note that this line should still be executed even if jobid == -1
                        # The later tc_analysis-using e3sm_diags tasks still depend on this task (and thus will also fail).
                        # Add to the dependency list
                        dependencies.append(statusFile)
                else:
                    print("...adding to bundle '%s'" % (c["bundle"]))

    return existing_bundles
