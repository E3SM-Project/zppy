import os
import shlex
import time
from subprocess import PIPE, Popen

# -----------------------------------------------------------------------------
# Process specified section and its sub-sections to build list of tasks
#
# If the section includes sub-sections, one task will be created for each
# sub-section and no task will be created for the main section.


def getTasks(config, section_name):

    tasks = []

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
        raise Exception(
            "Cannot extract component name from input_files %s" % (input_files)
        )

    return component


# -----------------------------------------------------------------------------
def submitScript(scriptFile, dependFiles=[], export="ALL"):

    # Handle dependency
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
                return -1
        else:
            print(
                "...skipping because of dependency status file missing\n   %s"
                % (dependFile)
            )
            return -1

    # Submit command
    if len(dependIds) == 0:
        command = "sbatch --export=%s %s" % (export, scriptFile)
    else:
        jobs = ""
        for i in dependIds:
            jobs += ":{:d}".format(i)
        command = "sbatch --export=%s --dependency=afterok%s %s" % (
            export,
            jobs,
            scriptFile,
        )

    # Actual submission
    p1 = Popen(shlex.split(command), stdout=PIPE, stderr=PIPE)
    (stdout, stderr) = p1.communicate()
    status = p1.returncode
    out = stdout.decode().strip()
    print("...%s" % (out))
    if status != 0 or not out.startswith("Submitted batch job"):
        error_str = "Problem submitting script %s" % (scriptFile)
        print(error_str)
        print(command)
        print(stderr)
        raise Exception(error_str)
    jobid = int(out.split()[-1])

    # Small pause to avoid overloading queueing system
    time.sleep(0.5)

    return jobid


# -----------------------------------------------------------------------------
def checkStatus(statusFile):

    skip = False
    if os.path.isfile(statusFile):
        with open(statusFile, "r") as f:
            tmp = f.read().split()
        if tmp[0] in ("OK", "WAITING", "RUNNING"):
            skip = True
            print("...skipping because status file says '%s'" % (tmp[0]))

    return skip
