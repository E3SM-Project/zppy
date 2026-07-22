from configparser import NoOptionError, NoSectionError
from typing import List

from configobj import ConfigObj
from mache import MachineInfo

from zppy.bundle import Bundle
from zppy.logger import _setup_custom_logger

logger = _setup_custom_logger(__name__)


def simboard(
    config: ConfigObj,
    _script_dir: str,
    existing_bundles: List[Bundle],
    _job_ids_file: str,
) -> List[Bundle]:
    """Validate the configuration-only `[simboard]` task hook.

    This section is an explicit top-level SimBoard configuration entry point,
    analogous to `[bundle]`: it influences how other tasks are configured, but
    it does not launch an HPC job of its own.
    """
    if config["simboard"].sections:
        raise ValueError("The [simboard] section does not support subsections.")
    return existing_bundles


def simboard_enabled(config: ConfigObj) -> bool:
    """Return whether SimBoard publishing is enabled.

    Assumes `config` has already been validated against `default.ini`, which
    provides the `[simboard]` section and its default values.
    """
    return bool(config["simboard"]["enabled"])


def validate_simboard_config(config: ConfigObj) -> None:
    if not simboard_enabled(config):
        return

    simulation_type = str(config["simboard"]["simulation_type"])
    if simulation_type == "none":
        raise ValueError(
            "simboard.simulation_type must be 'production' or 'development' "
            "when simboard.enabled is True."
        )


def infer_simboard_www(machine_info: MachineInfo, config: ConfigObj) -> str:
    simulation_type = str(config["simboard"]["simulation_type"])
    try:
        web_portal_base_path = machine_info.config.get("web_portal", "base_path")
    except (NoSectionError, NoOptionError) as exc:
        raise ValueError(
            f"www is empty and simboard.enabled is True, but machine "
            f"'{machine_info.machine}' has no web_portal.base_path in mache; "
            "cannot infer a diagnostics_archive path."
        ) from exc

    web_portal_base_path = web_portal_base_path.rstrip("/")
    if web_portal_base_path == "":
        raise ValueError(
            f"www is empty and simboard.enabled is True, but machine "
            f"'{machine_info.machine}' has an empty web_portal.base_path in "
            "mache; cannot infer a diagnostics_archive path."
        )

    inferred_www = (
        f"{web_portal_base_path}/diagnostics_archive/{simulation_type}/"
    )
    logger.info(
        "Inferred www=%s from mache web_portal.base_path because "
        "simboard.enabled is True.",
        inferred_www,
    )
    return inferred_www
