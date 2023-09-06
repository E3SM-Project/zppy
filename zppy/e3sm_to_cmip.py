import os
import pprint
import re

import jinja2

from zppy.bundle import handle_bundles
from zppy.utils import (
    checkStatus,
    getComponent,
    getTasks,
    getYears,
    makeExecutable,
    setMappingFile,
    submitScript,
)


# -----------------------------------------------------------------------------
def e3sm_to_cmip(config, scriptDir, existing_bundles, job_ids_file):

    # --- Initialize jinja2 template engine ---
    templateLoader = jinja2.FileSystemLoader(
        searchpath=config["default"]["templateDir"]
    )
    templateEnv = jinja2.Environment(loader=templateLoader)
    template = templateEnv.get_template("e3sm_to_cmip.bash")

    # --- List of tasks ---
    tasks = getTasks(config, "e3sm_to_cmip")
    print(config["e3sm_to_cmip"])
    if len(tasks) == 0:
        return existing_bundles

    # --- Generate and submit e3sm_to_cmip scripts ---
    dependencies = []

    for c in tasks:

        setMappingFile(c)

        # Grid name (if not explicitly defined)
        #   'native' if no remapping
        #   or extracted from mapping filename
        if c["grid"] == "":
            if c["mapping_file"] == "":
                c["grid"] = "native"
            elif c["mapping_file"] == "glb":
                c["grid"] = "glb"
            else:
                tmp = os.path.basename(c["mapping_file"])
                # FIXME: W605 invalid escape sequence '\.'
                tmp = re.sub("\.[^.]*\.nc$", "", tmp)  # noqa: W605
                tmp = tmp.split("_")
                if tmp[0] == "map":
                    c["grid"] = "%s_%s" % (tmp[-2], tmp[-1])
                else:
                    raise ValueError(
                        "Cannot extract target grid name from mapping file %s"
                        % (c["mapping_file"])
                    )

        # Component
        c["component"] = getComponent(c["input_files"])

        c["cmor_tables_prefix"] = c["diagnostics_base_path"]

        # Loop over year sets
        year_sets = getYears(c["years"])
        for s in year_sets:

            c["yr_start"] = s[0]
            c["yr_end"] = s[1]
            if ("last_year" in c.keys()) and (c["yr_end"] > c["last_year"]):
                continue  # Skip this year set
            c["ypf"] = s[1] - s[0] + 1
            c["scriptDir"] = scriptDir
            if c["subsection"]:
                sub = c["subsection"]
            else:
                sub = c["grid"]

            # List of dependencies
            dependencies.append(
                os.path.join(
                    scriptDir,
                    "ts_%s_%04d-%04d-%04d.status"
                    % (
                        c[
                            "subsection"
                        ],  # Depends on the ts subtask with the same name.
                        c["yr_start"],
                        c["yr_end"],
                        c["ypf"],
                    ),
                ),
            )

            prefix = "e3sm_to_cmip_%s_%04d-%04d-%04d" % (
                sub,
                c["yr_start"],
                c["yr_end"],
                c["ypf"],
            )
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

            export = "ALL"
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

    return existing_bundles