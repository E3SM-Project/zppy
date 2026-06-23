"""Helpers for emitting authoritative case identity and explicit
diagnostics URLs into zppy provenance metadata files.

See https://github.com/E3SM-Project/zppy/issues/831.
"""

import configparser
import os
import xml.etree.ElementTree as ET
from typing import Dict, Mapping, Optional

from mache import MachineInfo

from zppy.logger import _setup_custom_logger

logger = _setup_custom_logger(__name__)

# Map of zppy provenance field name -> env_case.xml entry id.
_ENV_CASE_FIELDS = {
    "case_name": "CASE",
    "machine": "MACH",
    "hpc_username": "REALUSER",
}


def parse_env_case_xml(input_dir: str) -> Dict[str, str]:
    """Parse `<input_dir>/case_scripts/env_case.xml` and return the subset of
    case identity fields needed for SimBoard matching.

    Returns a dict with any of {case_name, machine, hpc_username} that were
    successfully read. Missing file, missing entries, or malformed XML degrade
    gracefully to an empty / partial dict and a warning.
    """
    xml_path = os.path.join(input_dir, "case_scripts", "env_case.xml")
    if not os.path.isfile(xml_path):
        logger.warning(
            f"env_case.xml not found at {xml_path}; case identity fields will be "
            f"omitted from provenance."
        )
        return {}
    try:
        root = ET.parse(xml_path).getroot()
    except ET.ParseError as exc:
        logger.warning(
            f"Could not parse {xml_path}: {exc}; case identity fields will be omitted from provenance."
        )
        return {}

    values: Dict[str, str] = {}
    for field, entry_id in _ENV_CASE_FIELDS.items():
        # CIME nests <entry> elements inside <group id="..."> wrappers, so we
        # need a descendant search rather than a direct-child lookup.
        entry = root.find(f".//entry[@id='{entry_id}']")
        if entry is None or entry.get("value") is None:
            logger.warning(
                f"env_case.xml at {xml_path} has no '{entry_id}' entry; "
                f"'{field}' will be omitted from provenance."
            )
            continue
        values[field] = entry.get("value", "")
    return values


def build_diagnostics_url(
    www: str, case: str, machine_info: MachineInfo
) -> Optional[str]:
    """Build the public diagnostics web portal URL for a case.

    Mirrors `zppy.utils.get_url_message` but returns just the case-scoped URL
    (no per-task suffix). Returns None when www is empty, when www is not under
    the machine's web_portal base path, or when the machine config lacks the
    needed web_portal entries.
    """
    if not www:
        logger.warning("www is empty; diagnostics_url will be omitted from provenance.")
        return None
    try:
        base_path = machine_info.config.get("web_portal", "base_path")
        base_url = machine_info.config.get("web_portal", "base_url")
    except (configparser.NoSectionError, configparser.NoOptionError) as exc:
        logger.warning(
            f"Machine '{machine_info.machine}' has no web_portal config ({exc}); "
            f"diagnostics_url will be omitted from provenance."
        )
        return None
    if not www.startswith(base_path):
        logger.warning(
            f"www={www} is not under web_portal base_path={base_path}; "
            f"diagnostics_url will be omitted from provenance."
        )
        return None
    www_suffix = www[len(base_path) :]
    return f"{base_url}{www_suffix}/{case}"


def write_provenance_settings(
    settings_path: str, extras: Mapping[str, Optional[str]]
) -> None:
    """Write extra provenance metadata to a separate settings file.

    Empty / None values are skipped. A no-op if `extras` contains no usable
    entries, so callers can avoid creating an empty settings file.
    """
    usable = {k: v for k, v in extras.items() if v}
    if not usable:
        return

    with open(settings_path, "w") as f:
        for key, value in usable.items():
            f.write(f"{key} = {value}\n")


def build_provenance_extras(
    config_default: Dict[str, str], machine_info: MachineInfo
) -> Dict[str, str]:
    """Assemble the dict of extra provenance metadata fields.

    - `case_name`, `machine`, `hpc_username` from `env_case.xml` under cfg `input`.
    - `diagnostics_url` from cfg `www` + `case` + machine `web_portal` config.
    - Warns (but does not fail) when cfg `case` disagrees with env_case.xml `CASE`.
    """
    input_dir = config_default.get("input", "")
    case = config_default.get("case", "")
    www = config_default.get("www", "")

    extras: Dict[str, str] = {}
    if input_dir:
        extras.update(parse_env_case_xml(input_dir))
    else:
        logger.warning(
            "cfg 'input' is empty; cannot read env_case.xml — case identity "
            "fields will be omitted from provenance."
        )

    xml_case = extras.get("case_name")
    if xml_case and case and xml_case != case:
        logger.warning(
            f"cfg case='{case}' does not match env_case.xml CASE='{xml_case}'; "
            f"using env_case.xml value as authoritative case_name."
        )

    diag_url = build_diagnostics_url(www, case, machine_info)
    if diag_url:
        extras["diagnostics_url"] = diag_url
    return extras
