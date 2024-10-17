import os
import os.path
import pprint
import re
import shlex
import stat
import time
from enum import Enum
from subprocess import PIPE, Popen
from typing import Any, Dict, List, Set, Tuple

import jinja2
from configobj import ConfigObj


# Classes #####################################################################
class ParameterGuessType(Enum):
    PATH_GUESS = 1
    SECTION_GUESS = 2


class ParameterNotProvidedError(RuntimeError):
    pass


class DependencySkipError(RuntimeError):
    pass


# Utitlities for this file ####################################################


def get_active_status(task: Dict[str, Any]) -> bool:
    active: Any = task["active"]
    if isinstance(active, bool):
        return active
    elif isinstance(active, str):
        active_lower_case: str = active.lower()
        if active_lower_case == "true":
            return True
        elif active_lower_case == "false":
            return False
        raise ValueError(f"Invalid value {active} for 'active'")
    raise TypeError(f"Invalid type {type(active)} for 'active'")


def get_guess_type_parameter(guess_type: ParameterGuessType) -> str:
    guess_type_parameter: str
    if guess_type == ParameterGuessType.PATH_GUESS:
        guess_type_parameter = "guess_path_parameters"
    elif guess_type == ParameterGuessType.SECTION_GUESS:
        guess_type_parameter = "guess_section_parameters"
    else:
        raise ValueError(f"Invalid guess_type: {guess_type}")
    return guess_type_parameter


def get_url_message(c: Dict[str, Any], task: str) -> str:
    base_path = c["web_portal_base_path"]
    base_url = c["web_portal_base_url"]
    www = c["www"]
    case = c["case"]
    url_msg: str
    if www.startswith(base_path):
        # TODO: python 3.9 introduces `removeprefix`
        # This will begin with a "/"
        www_suffix = www[len(base_path) :]
        url_msg = f"URL: {base_url}{www_suffix}/{case}/{task}"
    else:
        url_msg = f"Could not determine URL from www={www}"
    return url_msg


# Beginning steps #############################################################


# TODO: determine return type
def initialize_template(config: ConfigObj, template_name: str) -> Tuple[Any, Any]:
    # --- Initialize jinja2 template engine ---
    template_loader = jinja2.FileSystemLoader(
        searchpath=config["default"]["templateDir"]
    )
    template_env = jinja2.Environment(loader=template_loader)
    template = template_env.get_template(template_name)
    return template, template_env


# TODO: type aliases require python 3.12 or higher
# type TaskDict = Dict[str, Any]


# Process specified section and its sub-sections to build the list of tasks.
# If the section includes sub-sections, one task will be created for each
# sub-section and no task will be created for the main section.
def get_tasks(config: ConfigObj, section_name: str) -> List[Dict[str, Any]]:

    # mypy: resolves error: Need type annotation for "tasks" (hint: "tasks: List[<type>] = ...")
    tasks: List[Dict[str, Any]] = []

    # Sanity check
    # flake8: resolves E713 test for membership should be 'not in'
    if section_name not in config:
        print(f'WARNING: Skipping section not found = "{section_name}"')
        return tasks

    # List of sub-sections
    sub_section_names: List[str] = config[section_name].sections

    # Merge default with current section. Need to work with copies to avoid contamination
    section_cfg: Dict[str, Any] = config["default"].copy()
    section_cfg.update(config[section_name].copy())

    # Construct list of tasks
    task: Dict[str, Any]
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
            tmp: Dict[str, Any] = config[section_name][sub_section_name].copy()
            # Remove all empty fields (None). These will be inherited from section
            sub: Dict[str, Any] = {k: v for k, v in tmp.items() if v is not None}
            # Merge content of sub-secton into section
            task.update(sub)
            # At this point, task will still include dictionary entries for
            # all sub-sections. Remove them to clean up.
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
            if (isinstance(c[key], str)) and ("$USER" in c[key]):
                c[key] = c[key].replace("$USER", username)

    return tasks


# `for c in tasks` steps ######################################################


def set_mapping_file(c: Dict[str, Any]) -> None:
    if c["mapping_file"] and (c["mapping_file"] != "glb"):
        directory: str = os.path.dirname(c["mapping_file"])
        if not directory:
            # We use the mapping file from Mache's [diagnostics > base_path].
            # However, new mapping files should be added to Mache's [sync > public_diags].
            # These files will then be synced over.
            c["mapping_file"] = os.path.join(
                c["diagnostics_base_path"], "maps", c["mapping_file"]
            )


def set_grid(c: Dict[str, Any]) -> None:
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
                c["grid"] = f"{tmp[-2]}_{tmp[-1]}"
            else:
                raise ValueError(
                    f"Cannot extract target grid name from mapping file {c['mapping_file']}"
                )
    # If grid is defined, just use that


# Output component (for directory structure) and procedure type for ncclimo
def set_component_and_prc_typ(c: Dict[str, Any]) -> None:
    if c["input_component"] != "":
        tmp = c["input_component"]
    else:
        tmp = c["input_files"].split(".")[0]
    component: str
    # Default ncclim procedure type is "sgs"
    prc_typ: str = "sgs"
    if tmp in ("cam", "eam", "eamxx"):
        component = "atm"
        prc_typ = tmp
    elif tmp in ("cpl",):
        component = "cpl"
    elif tmp in ("clm2",):
        component = "lnd"
        prc_typ = "clm"
    elif tmp in ("elm",):
        component = "lnd"
        prc_typ = tmp
    elif tmp in ("mosart",):
        component = "rof"
    else:
        raise ValueError(
            f"Cannot extract output component name from {c['input_component']} or {c['input_files']}."
        )
    c["component"] = component
    c["prc_typ"] = prc_typ


def check_required_parameters(
    c: Dict[str, Any], sets_with_requirement: Set[str], relevant_parameter: str
) -> None:
    requested_sets = set(c["sets"])
    if (
        (sets_with_requirement & requested_sets)
        and (relevant_parameter in c.keys())
        and (c[relevant_parameter] == "")
    ):
        raise ParameterNotProvidedError(relevant_parameter)


# Return all year sets from a configuration given by a list of strings
# "year_begin:year_end:year_freq"
# "year_begin-year_end"
def get_years(years_input) -> List[Tuple[int, int]]:
    years_list: List[str]
    if isinstance(years_input, str):
        # This will be the case if years_list is missing a trailing comma
        years_list = [years_input]
    else:
        years_list = years_input
    year_sets: List[Tuple[int, int]] = []
    for years in years_list:
        if years.count(":") == 2:
            year_begin: int
            year_end: int
            year_freq: int
            year_begin, year_end, year_freq = tuple(
                map(lambda y: int(y), years.split(":"))
            )
            year1: int = year_begin
            year2: int = year1 + year_freq - 1
            while year2 <= year_end:
                year_sets.append((year1, year2))
                year1 = year2 + 1
                year2 = year1 + year_freq - 1
        elif years.count("-") == 1:
            year1, year2 = tuple(map(lambda y: int(y), years.split("-")))
            year_sets.append((year1, year2))
        elif years != "":
            error_str = f"Error interpreting years {years}"
            print(error_str)
            raise ValueError(error_str)
    return year_sets


# `for s in year_sets` steps ##################################################


# This returns a value
def define_or_guess(
    c: Dict[str, Any],
    first_choice_parameter: str,
    second_choice_parameter: str,
    guess_type: ParameterGuessType,
) -> Any:
    # Determine which type of guess to use.
    guess_type_parameter: str = get_guess_type_parameter(guess_type)
    # Define a value, if possible.
    value: Any
    if (first_choice_parameter in c.keys()) and c[first_choice_parameter]:
        value = c[first_choice_parameter]
    elif c[guess_type_parameter]:
        # first_choice_parameter isn't defined,
        # so let's make a guess for the value.
        value = c[second_choice_parameter]
    else:
        raise ParameterNotProvidedError(first_choice_parameter)
    return value


# This updates the dict c
def define_or_guess2(
    c: Dict[str, Any],
    parameter: str,
    backup_option: str,
    guess_type: ParameterGuessType,
) -> None:
    # Determine which type of guess to use.
    guess_type_parameter: str = get_guess_type_parameter(guess_type)
    # Define a value, if possible.
    if (parameter in c.keys()) and (c[parameter] == ""):
        if c[guess_type_parameter]:
            c[parameter] = backup_option
        else:
            raise ParameterNotProvidedError(parameter)


def check_parameter_defined(c: Dict[str, Any], relevant_parameter: str) -> None:
    if (relevant_parameter not in c.keys()) or (c[relevant_parameter] == ""):
        raise ParameterNotProvidedError(relevant_parameter)


def get_file_names(script_dir: str, prefix: str):
    return tuple(
        [
            os.path.join(script_dir, f"{prefix}.{suffix}")
            for suffix in ["bash", "settings", "status"]
        ]
    )


def check_status(status_file: str) -> bool:
    skip: bool = False
    if os.path.isfile(status_file):
        with open(status_file, "r") as f:
            tmp: List[str] = f.read().split()
        if tmp[0] in ("OK", "WAITING", "RUNNING"):
            skip = True
            print(f"...skipping because status file says '{tmp[0]}'")

    return skip


def make_executable(script_file: str) -> None:
    st = os.stat(script_file)
    os.chmod(script_file, st.st_mode | stat.S_IEXEC)


def add_dependencies(
    dependencies: List[str],
    scriptDir: str,
    prefix: str,
    sub: str,
    start_yr: int,
    end_yr: int,
    num_years: int,
) -> None:
    y1: int = start_yr
    y2: int = start_yr + num_years - 1
    while y2 <= end_yr:
        dependencies.append(
            os.path.join(
                scriptDir, f"{prefix}_{sub}_{y1:04d}-{y2:04d}-{num_years:04d}.status"
            )
        )
        y1 += num_years
        y2 += num_years


def write_settings_file(
    settings_file: str, task_dict: Dict[str, Any], year_tuple: Tuple[int, int]
):
    with open(settings_file, "w") as sf:
        p = pprint.PrettyPrinter(indent=2, stream=sf)
        p.pprint(task_dict)
        p.pprint(year_tuple)


def submit_script(
    script_file: str,
    status_file: str,
    export,
    job_ids_file,
    dependFiles: List[str] = [],
    fail_on_dependency_skip: bool = False,
):
    # id of submitted job, or -1 if not submitted
    jobid = None

    # Handle dependencies
    dependIds: List[int] = []
    for dependFile in dependFiles:
        if os.path.isfile(dependFile):
            tmp: List[str]
            with open(dependFile, "r") as f:
                tmp = f.read().split()
            if tmp[0] in ("OK"):
                pass
            elif tmp[0] in ("WAITING", "RUNNING"):
                dependIds.append(int(tmp[1]))
            else:
                skip_message = f"...skipping because dependency says '{tmp[0]}'"
                if fail_on_dependency_skip:
                    raise DependencySkipError(skip_message)
                else:
                    print(skip_message)
                    jobid = -1
                    break
        else:
            skip_message = f"...skipping because of dependency status file missing\n   {dependFile}"
            if fail_on_dependency_skip:
                raise DependencySkipError(skip_message)
            else:
                print(skip_message)
                jobid = -1
                break

    # If no exception occurred during dependency check, proceed with submission
    if jobid != -1:

        # Submit command
        command: str
        if len(dependIds) == 0:
            command = f"sbatch --export={export} {script_file}"
        else:
            jobs: str = ""
            for i in dependIds:
                jobs += ":{:d}".format(i)
            # Note that `--dependency` does handle bundles even though it lists individual tasks, not bundles.
            # Since each task of a bundle lists "RUNNING <Job ID of bundle>", the bundle's job ID will be included.
            command = (
                f"sbatch --export={export} --dependency=afterok{jobs} {script_file}"
            )

        # Actual submission
        p1 = Popen(shlex.split(command), stdout=PIPE, stderr=PIPE)
        (stdout, stderr) = p1.communicate()
        status = p1.returncode
        out = stdout.decode().strip()
        print(f"...{out}")
        if status != 0 or not out.startswith("Submitted batch job"):
            error_str = f"Problem submitting script {script_file}"
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
        with open(status_file, "w") as f:
            f.write(f"WAITING {jobid:d}\n")

    return jobid


def print_url(c: Dict[str, Any], task: str) -> None:
    print(get_url_message(c, task))
