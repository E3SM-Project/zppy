# TODO: Make mappings:
# These variables => run these tasks, sets
# These model components => run these tasks, sets

import os
import re
import shlex
import subprocess
from typing import Dict, List, Optional, Set

ARCHIVE_DIR: str = "/lcrc/group/e3sm2/ac.wlin/E3SMv3/v3.LR.historical_0051/"


class DirectoryMetadata(object):
    def __init__(self, simulation_dir: str, component: str):
        component_path: str = f"{simulation_dir}/archive/{component}/hist/"
        component_files: List[str] = os.listdir(component_path)
        metadata_dict: Dict[str, Set[str]] = get_available_filename_metadata(
            component_files
        )
        dates: Set[str] = metadata_dict["dates"]

        h_values: Set[str] = metadata_dict["h_values"]
        h_value_to_first_file: Dict[str, str] = get_h_value_representative_files(
            component_files, h_values
        )
        variables_by_h_value: Dict[str, List[str]] = {}
        for h_value in h_values:
            representative_file: str = h_value_to_first_file[h_value]
            variables_by_h_value[h_value] = get_netcdf_var_names(
                f"{component_path}{representative_file}"
            )

        self.component: str = component
        self.versions: Set[str] = metadata_dict["versions"]
        self.resolutions: Set[str] = metadata_dict["resolutions"]
        self.case_names: Set[str] = metadata_dict["case_names"]
        self.components: Set[str] = metadata_dict["components"]
        self.h_values: Set[str] = h_values
        self.year_ranges: List[str] = collapse_year_range(dates)
        self.file_extensions: Set[str] = metadata_dict["file_extensions"]
        self.variables_by_h_value: Dict[str, List[str]] = variables_by_h_value

    def print_attributes(self, verbose=False):
        print(f"\nPrinting directory metadata for component={self.component}")
        print(f"versions={self.versions}")
        print(f"resolutions={self.resolutions}")
        print(f"case_names={self.case_names}")
        print(f"components={self.components}")
        print(f"h_values={self.h_values}")
        for h_value in sorted(self.h_values):
            vars: List[str] = self.variables_by_h_value[h_value]
            print(f"  {h_value} has {len(vars)} vars")
            if verbose:
                for i, var in enumerate(vars):
                    print(f"    {i}. {var}")
        print(f"year_ranges={self.year_ranges}")
        print(f"file_extensions={self.file_extensions}")


def main(verbose: bool = False):
    metadata_by_component: Dict[str, Optional[DirectoryMetadata]] = (
        get_metadata_by_component(ARCHIVE_DIR)
    )
    for component in metadata_by_component:
        m: Optional[DirectoryMetadata] = metadata_by_component[component]
        if m:
            m.print_attributes(verbose)


def get_metadata_by_component(
    simulation_dir: str,
) -> Dict[str, Optional[DirectoryMetadata]]:
    metadata_by_component: Dict[str, Optional[DirectoryMetadata]] = {
        "atm": None,
        "cpl": None,
        "ice": None,
        "lnd": None,
        "ocn": None,
        "rof": None,
    }
    for component in metadata_by_component.keys():
        metadata_by_component[component] = DirectoryMetadata(simulation_dir, component)
    return metadata_by_component


def get_netcdf_var_names(filename: str) -> List[str]:
    cmd = f"ncdump -h {shlex.quote(filename)}"
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ncdump failed: {e.stderr}") from e

    lines = result.stdout.splitlines()

    var_names = []
    in_variables = False

    # Regex:
    #   start of line (optional spaces)
    #   type (word)
    #   spaces
    #   name (word)
    #   optional spaces
    #   '('  ...  ')'   then ';'
    #   optionally followed by spaces and comments
    decl_re = re.compile(
        r"^\s*"  # leading spaces
        r"(\w+)\s+"  # type, e.g., float, double, int
        r"([A-Za-z0-9_]+)"  # variable name
        r"\s*\("  # opening parenthesis for dims
    )

    for raw_line in lines:
        line = raw_line.rstrip()

        # Detect start of variables block
        if line.strip().startswith("variables:"):
            in_variables = True
            continue

        if not in_variables:
            continue

        # End of variables block
        if line.strip().startswith("//") or line.strip() == "":
            break

        # Skip attribute lines, which usually have ':'
        # e.g.: "    AODSO4:long_name = "Some name" ;"
        stripped = line.strip()
        if ":" in stripped or "=" in stripped:
            # If it is exactly a declaration line with attributes folded later,
            # it will still be matched by the regex above without ':'
            # but attribute-only lines we want to skip.
            # A conservative approach: only skip if it starts with ":" or has " = ".
            if stripped.startswith(":") or " = " in stripped:
                continue

        m = decl_re.match(line)
        if m:
            var_name = m.group(2)
            var_names.append(var_name)

    return var_names


# Pure functions -- can be unit tested ########################################
def get_h_value_representative_files(
    component_files: List[str], available_h_values: Set[str]
) -> Dict[str, str]:
    # Map each h-value to the first file containing it
    h_value_to_first_file: Dict[str, str] = {}
    for filename in component_files:
        for h_value in available_h_values:
            if (h_value in filename) and (h_value not in h_value_to_first_file):
                h_value_to_first_file[h_value] = filename
                break
    return h_value_to_first_file


def get_available_filename_metadata(files: List[str]) -> Dict[str, Set[str]]:
    metadata_dict: Dict[str, Set[str]] = {
        "versions": set(),
        "resolutions": set(),
        "case_names": set(),
        "components": set(),
        "h_values": set(),
        "dates": set(),
        "file_extensions": set(),
    }
    for data_file in files:
        parse_filename(data_file, metadata_dict)
    return metadata_dict


def parse_filename(data_file: str, metadata_dict: Dict[str, Set[str]]):
    parsed_string: List[str] = data_file.split(".")
    num_entries: int = len(parsed_string)
    if num_entries == 7:
        # atm, cpl, lnd, rof
        metadata_dict["versions"].add(parsed_string[0])
        metadata_dict["resolutions"].add(parsed_string[1])
        metadata_dict["case_names"].add(parsed_string[2])
        metadata_dict["components"].add(parsed_string[3])
        metadata_dict["h_values"].add(parsed_string[4])
        metadata_dict["dates"].add(parsed_string[5])
        metadata_dict["file_extensions"].add(parsed_string[6])
    elif num_entries == 9:
        # ice, ocn
        metadata_dict["versions"].add(parsed_string[0])
        metadata_dict["resolutions"].add(parsed_string[1])
        metadata_dict["case_names"].add(parsed_string[2])
        metadata_dict["components"].add(parsed_string[3])
        metadata_dict["h_values"].add(
            f"{parsed_string[4]}.{parsed_string[5]}.{parsed_string[6]}"
        )
        metadata_dict["dates"].add(parsed_string[7])
        metadata_dict["file_extensions"].add(parsed_string[8])
    elif num_entries == 10:
        # ice, ocn
        metadata_dict["versions"].add(parsed_string[0])
        metadata_dict["resolutions"].add(parsed_string[1])
        metadata_dict["case_names"].add(parsed_string[2])
        metadata_dict["components"].add(parsed_string[3])
        metadata_dict["h_values"].add(
            f"{parsed_string[4]}.{parsed_string[5]}.{parsed_string[6]}"
        )
        metadata_dict["dates"].add(f"{parsed_string[7]}-{parsed_string[8]}")
        metadata_dict["file_extensions"].add(parsed_string[9])


def is_valid_year_range_format(date_str: str) -> bool:
    """
    Check if a string matches a format accepted by collapse_year_range.

    Accepted formats:
    - YYYY-MM-DD-XXXXX (e.g., "1851-01-01-00000")
    - YYYY-MM (e.g., "1985-03")
    - YYYY-... (any string starting with a 4-digit year followed by hyphen)

    Args:
        date_str: The string to validate

    Returns:
        True if the string matches an accepted format, False otherwise
    """
    if not date_str or not isinstance(date_str, str):
        return False

    # Pattern: starts with 4 digits (year), followed by hyphen and anything
    # Or just 4 digits (year only)
    pattern = r"^\d{4}(-.*)?$"

    if not re.match(pattern, date_str):
        return False

    # Extract and validate the year is reasonable (e.g., between 1000-9999)
    year_str = date_str.split("-")[0]
    try:
        year = int(year_str)
        return 1000 <= year <= 9999
    except ValueError:
        return False


def collapse_year_range(year_ranges: Set[str]) -> List[str]:
    if not year_ranges:
        return []

    # Extract years from the date strings
    years = set()
    for date_str in year_ranges:
        year = int(date_str.split("-")[0])
        years.add(year)

    # Sort years
    sorted_years = sorted(years)

    # Group consecutive years into ranges
    result = []
    i = 0
    while i < len(sorted_years):
        start = sorted_years[i]
        end = start

        # Find consecutive years
        while i + 1 < len(sorted_years) and sorted_years[i + 1] == sorted_years[i] + 1:
            i += 1
            end = sorted_years[i]

        # Add range or single year
        if start == end:
            result.append(str(start))
        else:
            result.append(f"{start}-{end}")

        i += 1

    return result


# Run #########################################################################
if __name__ == "__main__":
    main(True)
