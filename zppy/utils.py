import os
import os.path
import re
import shlex
import time
from subprocess import PIPE, Popen
from typing import Set

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
# Bundles
class Bundle(object):
    def __init__(self, c):
        self.bundle_name: str = c["bundle"]
        self.dry_run: bool = c[
            "dry_run"
        ]  # Value is taken from the first task in the bundle
        self.script_dir: str = c[
            "scriptDir"
        ]  # Value is taken from the first task in the bundle

        self.bundle_file: str = f"{self.script_dir}/{self.bundle_name}.bash"
        self.bundle_status: str = f"{self.script_dir}/{self.bundle_name}.status"
        self.bundle_output: str = self.bundle_file.strip(".bash") + ".o%j"

        self.dependencies_in_bundle_file: Set[str] = set()
        self.dependencies_not_in_bundle_file: Set[str] = set()

        self.export: str = "NONE"

    def create_header(self, scriptFile):
        if os.path.exists(f"{self.bundle_status}"):
            error_message = f"create_header is being applied to an existing bundle: {self.bundle_name}. If {self.bundle_name} was running and you re-ran zppy, that is the likely cause of this error. If {self.bundle_name} is not currently running, delete {self.bundle_name}.status and run zppy again."
            # By failing, zppy is prevented from restarting / overwriting work the bundle is currently doing.
            raise FileExistsError(error_message)

        # Create header or structure to keep info for the header.
        with open(self.bundle_file, "w") as destination_file:
            destination_file.write("#!/bin/bash\n")
            with open(scriptFile, "r") as source_file:
                for line in source_file:
                    # Copy to bundle_file all lines from script_file that contain "SBATCH"
                    if re.search("SBATCH", line):
                        if re.search("--output", line):
                            destination_file.write(
                                f"#SBATCH --output={self.bundle_output}\n"
                            )
                        elif re.search("--job-name", line):
                            destination_file.write(
                                f"#SBATCH --job-name={self.bundle_name}\n"
                            )
                        else:
                            destination_file.write(line)
                # If any script fails, no new ones should try to run.
                # It's possible the failed script is a dependency for later scripts.
                destination_file.write("set -e # Exit on failure\n")
                # Enter directory
                destination_file.write(f"cd {self.script_dir}\n")
                # Create status file
                # We can only determine if the bundle has begun running.
                # The script exits on failure (`set -e` above), so we can't set the status to "ERROR".
                # We can't tell which call to `add_script` is the last, so we don't know when we can set the status to "OK".
                destination_file.write(
                    f"echo 'HAS BEGUN RUNNING' > {self.bundle_name}.status\n"
                )

    def handle_dependencies(self, dependFiles):
        # Handle dependencies
        for dependFile in dependFiles:
            required_script = os.path.split(dependFile)[-1].rstrip(".status") + ".bash"
            with open(self.bundle_file, "r") as f:
                for line in f:
                    if re.search(required_script, line):
                        # The required script is actually in this bundle.
                        # Therefore, this dependency will be fulfilled
                        # by the time we get to the current script
                        # (since __main__.py runs the tasks in dependency order).
                        # So, continue on to next dependency.
                        self.dependencies_in_bundle_file.add(
                            dependFile
                        )  # Useful for debugging
                        break
                else:
                    # If we're in this block, then we did not `break` from the for-loop.
                    # So, the dependency is not in this bundle.
                    # So, the dependency will need to be finished before we can run this bundle.
                    # We must pass this information on via dependencies_not_in_bundle_file
                    self.dependencies_not_in_bundle_file.add(dependFile)

    def add_script(self, scriptFile):
        # Add script file to bundle
        with open(self.bundle_file, "a") as f:
            # Add scriptFile to the list of scripts to run
            # The header in scriptFile will simply be ignored
            file_name_only = os.path.split(scriptFile)[-1]
            # Put blank line between each script call
            f.write("\n")
            # Allow script to be run
            f.write(f"chmod 760 {file_name_only}\n")  # Default is 660
            # Run script
            f.write(f"./{file_name_only}\n")
            # Add exit logic
            # If any script fails, no new ones should try to run.
            # It's possible the failed script is a dependency for later scripts.
            # f.write("if [ $? != 0 ]; then\n")
            # f.write(f"  cd {self.script_dir}\n")
            # f.write(f"  echo 'ERROR on {file_name_only}' > {self.bundle_name}.status\n")
            # f.write("  exit 1\n")
            # f.write("fi\n")

    # Useful for debugging
    def display_dependencies(self):
        print(f"Displaying dependencies for {self.bundle_name}")
        print("dependencies_in_bundle_file:")
        for dependency in self.dependencies_in_bundle_file:
            d = os.path.split(dependency)[-1]
            print(f"  {d}")
        else:
            # If we're in this block, then the list is empty.
            print("  None")
        print("dependencies_not_in_bundle_file:")
        for dependency in self.dependencies_not_in_bundle_file:
            d = os.path.split(dependency)[-1]
            print(f"  {d}")
        else:
            # If we're in this block, then the list is empty.
            print("  None")


def handle_bundles(c, scriptFile, export, dependFiles=[], existing_bundles=[]):
    bundle_name = c["bundle"]
    if bundle_name == "":
        return existing_bundles
    for b in existing_bundles:
        if b.bundle_name == bundle_name:
            # This bundle already exists
            bundle = b
            break
    else:
        # If we're in this block, then we did not `break` from the for-loop.
        # So, the bundle does not already exist
        bundle = Bundle(c)
        bundle.create_header(scriptFile)
        existing_bundles.append(bundle)
    bundle.handle_dependencies(dependFiles)
    bundle.add_script(scriptFile)
    if export == "ALL":
        # If one task requires export="ALL", then the bundle script will need it as well
        bundle.export = export
    return existing_bundles


# -----------------------------------------------------------------------------
def submitScript(scriptFile, export, dependFiles=[]):

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
