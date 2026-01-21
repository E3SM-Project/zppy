from typing import Dict, Optional, Set

from mache import MachineInfo
from simulation_output_reviewer import ARCHIVE_DIR, DirectoryMetadata

ZPPY_CFG_SUFFIX_OUTPUT = "datathon_placeholder/"
ZPPY_CFG_SUFFIX_WWW = "datathon_placeholder/"


class Dependency(object):
    def __init__(
        self,
        subtask_label: str,
        var_str: str,
        years_str: str,
        year_increment: int,
        climo_years: str = "",
        ts_years: str = "",
    ):
        self.subtask_label: str = subtask_label
        self.var_str: str = var_str
        self.years_str: str = years_str
        self.year_increment: int = year_increment
        self.climo_years: str = climo_years
        self.ts_years: str = ts_years


def get_machine_specifics() -> Dict[str, str]:
    machine_info = MachineInfo()
    machine: str = machine_info.machine
    config = machine_info.config
    username: str = config.get("web_portal", "username")
    web_base_path: str = config.get("web_portal", "base_path")

    output_base_path: str = ""
    partition: str = ""
    qos: str = ""
    if machine == "chrysalis":
        output_base_path = "/lcrc/group/e3sm/"
        partition = "compute"
        qos = "regular"
    elif machine == "perlmutter":
        output_base_path = "/global/cfs/cdirs/e3sm/"
        partition = ""
        qos = "regular"
    elif machine == "compy":
        output_base_path = "/compyfs/"
        partition = "slurm"
        qos = "regular"
    else:
        print(f"Warning: invalid machine={machine}")

    return {
        "input_path": ARCHIVE_DIR,
        "output_path": f"{output_base_path}{username}/{ZPPY_CFG_SUFFIX_OUTPUT}/",
        "www_path": f"{web_base_path}/{username}/{ZPPY_CFG_SUFFIX_WWW}/",
        "partition": partition,
        "qos": qos,
    }


def get_case_name(metadata: Dict[str, Optional[DirectoryMetadata]]) -> str:
    found_case_names: Set[str] = set()
    for component in metadata.keys():
        metadata_for_component: Optional[DirectoryMetadata] = metadata[component]
        if metadata_for_component is None:
            continue  # No metadata to look through
        case_names: Set[str] = metadata_for_component.case_names
        if len(case_names) > 1:
            print(
                f"Warning: more than 1 case name found for component={component}. Cases: {case_names}"
            )
        for case_name in case_names:
            found_case_names.add(case_name)
    if len(found_case_names) > 1:
        print(
            f"Warning: more than 1 case name found across components. Cases: {found_case_names}"
        )
    return list(found_case_names)[0]
