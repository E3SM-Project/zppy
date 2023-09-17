import os
import os.path
import shlex
import stat
import time
from subprocess import PIPE, Popen
from typing import Any, Dict, List

# -----------------------------------------------------------------------------
# Process specified section and its sub-sections to build list of tasks
#
# If the section includes sub-sections, one task will be created for each
# sub-section and no task will be created for the main section.


def getTasks(config, section_name):

    # mypy: resolves error: Need type annotation for "tasks" (hint: "tasks: List[<type>] = ...")
    tasks: List[Dict[str, Any]] = []

    # Sanity check
    # flake8: resolves E713 test for membership should be 'not in'
    if section_name not in config:
        print('WARNING: Skipping section not found = "%s"' % (section_name))
        return tasks

    # List of sub-sections
    sub_section_names = config[section_name].sections

    # Merge default with current section. Need to work with copies to avoid contamination
    section_cfg = config["default"].copy()
    section_cfg.update(config[section_name].copy())

    # Construct list of tasks
    if len(sub_section_names) == 0:

        # No sub-section, single task

        # Merge current section with default. Work with copies to avoid contamination
        task = config["default"].copy()
        task.update(config[section_name].copy())
        # Set 'subsection' in dictionary to None
        task["subsection"] = None
        # Add to list of tasks if it is active
        if get_active_status(task):
            tasks.append(task)

    else:

        # One task for each sub-section
        for sub_section_name in sub_section_names:

            # Merge current section with default
            task = config["default"].copy()
            task.update(config[section_name].copy())
            # Merge sub-section with section. Start with a dictionary copy of sub-section
            tmp = config[section_name][sub_section_name].copy()
            # Remove all empty fields (None). These will be inherited from section
            sub = {k: v for k, v in tmp.items() if v is not None}
            # Merge content of sub-secton into section
            task.update(sub)
            # At this point, task will still include dictionary entries for
            # all sub-sections. Remove them to clean-up
            for s in sub_section_names:
                task.pop(s)
            # Finally, add name of subsection to dictionary
            task["subsection"] = sub_section_name
            # Add to list of tasks if it is active
            if get_active_status(task):
                tasks.append(task)

    # This replaces `$USER` from the cfg file with the actual username
    username = os.environ.get("USER")
    for c in tasks:
        for key in c:
            if (type(c[key]) == str) and ("$USER" in c[key]):
                c[key] = c[key].replace("$USER", username)

    return tasks


# -----------------------------------------------------------------------------
def get_active_status(task):
    active = task["active"]
    if type(active) == bool:
        return active
    elif type(active) == str:
        active_lower_case = active.lower()
        if active_lower_case == "true":
            return True
        elif active_lower_case == "false":
            return False
        raise ValueError("Invalid value {} for 'active'".format(active))
    raise TypeError("Invalid type {} for 'active'".format(type(active)))


# -----------------------------------------------------------------------------
# Return all year sets from a configuration given by a list of strings
# "year_begin:year_end:year_freq"
# "year_begin-year_end"


def getYears(years_list):
    if type(years_list) == str:
        # This will be the case if years_list is missing a trailing comma
        years_list = [years_list]
    year_sets = []
    for years in years_list:

        if years.count(":") == 2:

            year_begin, year_end, year_freq = years.split(":")
            year_begin = int(year_begin)
            year_end = int(year_end)
            year_freq = int(year_freq)

            year1 = year_begin
            year2 = year1 + year_freq - 1
            while year2 <= year_end:
                year_sets.append((year1, year2))
                year1 = year2 + 1
                year2 = year1 + year_freq - 1

        elif years.count("-") == 1:
            year1, year2 = years.split("-")
            year1 = int(year1)
            year2 = int(year2)
            year_sets.append((year1, year2))

        elif years != "":
            error_str = "Error interpreting years %s" % (years)
            print(error_str)
            raise ValueError(error_str)

    return year_sets


# -----------------------------------------------------------------------------
# Return component name from input files (e.g. 'cam.h0', 'clm2.h0', ...)


def getComponent(input_files):

    tmp = input_files.split(".")[0]
    if tmp in ("cam", "eam"):
        component = "atm"
    elif tmp in ("cpl",):
        component = "cpl"
    elif tmp in ("clm2", "elm"):
        component = "lnd"
    elif tmp in ("mosart",):
        component = "rof"
    else:
        raise ValueError(
            "Cannot extract component name from input_files %s" % (input_files)
        )

    return component


# -----------------------------------------------------------------------------


def setMappingFile(c):
    if c["mapping_file"] and (c["mapping_file"] != "glb"):
        directory = os.path.dirname(c["mapping_file"])
        if not directory:
            # We use the mapping file from Mache's [diagnostics > base_path].
            # However, new mapping files should be added to Mache's [sync > public_diags].
            # These files will then be synced over.
            c["mapping_file"] = os.path.join(
                c["diagnostics_base_path"], "maps", c["mapping_file"]
            )


# -----------------------------------------------------------------------------
def submitScript(scriptFile, statusFile, export, job_ids_file, dependFiles=[]):

    # id of submitted job, or -1 if not submitted
    jobid = None

    # Handle dependencies
    dependIds = []
    for dependFile in dependFiles:
        if os.path.isfile(dependFile):
            with open(dependFile, "r") as f:
                tmp = f.read().split()
            if tmp[0] in ("OK"):
                pass
            elif tmp[0] in ("WAITING", "RUNNING"):
                dependIds.append(int(tmp[1]))
            else:
                print("...skipping because dependency says '%s'" % (tmp[0]))
                jobid = -1
                break
        else:
            print(
                "...skipping because of dependency status file missing\n   %s"
                % (dependFile)
            )
            jobid = -1
            break

    # If no exception occurred during dependency check, proceed with submission
    if jobid != -1:

        # Submit command
        if len(dependIds) == 0:
            command = f"sbatch --export={export} {scriptFile}"
        else:
            jobs = ""
            for i in dependIds:
                jobs += ":{:d}".format(i)
            # Note that `--dependency` does handle bundles even though it lists individual tasks, not bundles.
            # Since each task of a bundle lists "RUNNING <Job ID of bundle>", the bundle's job ID will be included.
            command = (
                f"sbatch --export={export} --dependency=afterok{jobs} {scriptFile}"
            )

        # Actual submission
        p1 = Popen(shlex.split(command), stdout=PIPE, stderr=PIPE)
        (stdout, stderr) = p1.communicate()
        status = p1.returncode
        out = stdout.decode().strip()
        print(f"...{out}")
        if status != 0 or not out.startswith("Submitted batch job"):
            error_str = f"Problem submitting script {scriptFile}"
            print(error_str)
            print(command)
            print(stderr)
            raise RuntimeError(error_str)
        jobid = int(out.split()[-1])
        with open(job_ids_file, "a") as j:
            # To include the scriptFile, use this line:
            # j.write(f"{scriptFile}: {jobid}\n")
            # To cancel all jobs associated with this zppy run, use `xargs scancel < jobids.txt`.
            j.write(f"{jobid}\n")

        # Small pause to avoid overloading queueing system
        time.sleep(0.2)

    # Create status file if job has been submitted
    if jobid != -1:
        with open(statusFile, "w") as f:
            f.write("WAITING %d\n" % (jobid))

    return jobid


# -----------------------------------------------------------------------------
def checkStatus(statusFile):

    skip = False
    if os.path.isfile(statusFile):
        with open(statusFile, "r") as f:
            tmp = f.read().split()
        if tmp[0] in ("OK", "WAITING", "RUNNING"):
            skip = True
            print(f"...skipping because status file says '{tmp[0]}'")

    return skip


# -----------------------------------------------------------------------------
def makeExecutable(scriptFile):

    st = os.stat(scriptFile)
    os.chmod(scriptFile, st.st_mode | stat.S_IEXEC)

    return


# -----------------------------------------------------------------------------
def print_url(c, task):
    base_path = c["web_portal_base_path"]
    base_url = c["web_portal_base_url"]
    www = c["www"]
    case = c["case"]
    if www.startswith(base_path):
        # TODO: python 3.9 introduces `removeprefix`
        # This will begin with a "/"
        www_suffix = www[len(base_path) :]
        print(f"URL: {base_url}{www_suffix}/{case}/{task}")
    else:
        print(f"Could not determine URL from www={www}")
