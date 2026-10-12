import os
import pwd
from configparser import NoOptionError, NoSectionError
from stat import filemode
from typing import List

from configobj import ConfigObj
from mache import MachineInfo

from zppy.bundle import Bundle
from zppy.logger import _setup_custom_logger

logger = _setup_custom_logger(__name__)


def normalize_web_portal_base_path(web_portal_base_path: str) -> str:
    return web_portal_base_path.strip().rstrip("/")


def _normalize_case_group(case_group: str) -> str:
    """Return the trailing-slashed path segment for a case group, or "".

    A case group comes from `env_case.xml` or the cfg, so it is free-form text.
    Only a single path component is meaningful here; anything containing a
    separator is rejected rather than silently used to build a deeper tree.
    """
    case_group = (case_group or "").strip().strip("/")
    if not case_group:
        return ""
    if "/" in case_group or case_group in (".", ".."):
        raise ValueError(
            f"Invalid case_group '{case_group}': it becomes a single directory "
            "name in the SimBoard archive path, so it cannot contain '/' or be "
            "'.' or '..'."
        )
    return f"{case_group}/"


def simboard(
    config: ConfigObj,
    _script_dir: str,
    existing_bundles: List[Bundle],
    _job_ids_file: str,
) -> List[Bundle]:
    """Validate the configuration-only `[simboard]` task hook.

    This section is an explicit top-level SimBoard configuration entry point,
    analogous to `[bundle]`: it influences how other tasks are configured, but
    it does not launch an HPC job of its own. The unused task-like parameters
    are retained so this hook matches the call signature of other zppy tasks.
    This hook assumes the config has already been read and validated.
    """
    if "simboard" not in config:
        raise ValueError(
            "Missing [simboard] section. Validate the config against "
            "default.ini before calling simboard()."
        )
    if config["simboard"].sections:
        raise ValueError("The [simboard] section does not support subsections.")
    return existing_bundles


def simboard_enabled(config: ConfigObj) -> bool:
    """Return whether SimBoard publishing is enabled.

    Assumes `config` has already been validated against `default.ini`, which
    provides the `[simboard]` section and its default values.
    """
    enabled = config["simboard"]["enabled"]
    if isinstance(enabled, bool):
        return enabled
    if isinstance(enabled, str):
        enabled_lower = enabled.lower()
        if enabled_lower == "true":
            return True
        if enabled_lower == "false":
            return False
    raise ValueError(
        f"Invalid value '{enabled}' for simboard.enabled. Expected boolean "
        "or string 'true'/'false'."
    )


def validate_simboard_config(config: ConfigObj) -> None:
    if not simboard_enabled(config):
        return

    simulation_type = config["simboard"]["simulation_type"]
    if simulation_type == "none":
        raise ValueError(
            "simboard.simulation_type must be 'production' or 'development' "
            "when simboard.enabled is True."
        )


def _owner_name(uid: int) -> str:
    try:
        return pwd.getpwuid(uid).pw_name
    except KeyError:
        return str(uid)


def validate_www_access(config: ConfigObj, www: str, case: str) -> None:
    """Fail before any task is launched if the www case directory is unusable.

    `www` is a shared, published location. Without this check, a collision with
    another user surfaces only when a task copies its results to the web
    server, after the job has already consumed its full runtime.
    """
    www_case_dir = os.path.join(www, case)
    if not os.path.exists(www_case_dir):
        return

    current_uid = os.getuid()
    me = _owner_name(current_uid)
    case_dir_stat = os.stat(www_case_dir)
    owner = _owner_name(case_dir_stat.st_uid)
    if case_dir_stat.st_uid != current_uid:
        if simboard_enabled(config):
            if config["simboard"]["simulation_type"] == "production":
                raise ValueError(
                    f"Cannot publish case '{case}': {www_case_dir} already "
                    f"exists and is owned by {owner}, not {me}. A production "
                    "case has one authoritative diagnostics path. Coordinate "
                    f"with {owner}, or set [default] www to a path you own "
                    "to publish a separate copy."
                )
            raise ValueError(
                f"Cannot publish case '{case}': {www_case_dir} already exists "
                f"and is owned by {owner}, not {me}. Set [default] www to a "
                "path you own to publish a separate copy."
            )
        logger.warning(
            "%s already exists and is owned by %s, not %s. Tasks may fail or "
            "overwrite existing results when they copy to the web server.",
            www_case_dir,
            owner,
            me,
        )

    if not os.access(www_case_dir, os.W_OK | os.X_OK):
        remedy = (
            "Update its permissions"
            if case_dir_stat.st_uid == current_uid
            else f"Ask {owner} to grant write access"
        )
        raise ValueError(
            f"Cannot write to www case directory {www_case_dir} (owner "
            f"{owner}, mode {filemode(case_dir_stat.st_mode)}) as {me}. "
            f"{remedy}, or set [default] www to a path you own."
        )


def infer_simboard_www(
    machine_info: MachineInfo, config: ConfigObj, case_group: str = ""
) -> str:
    simulation_type = config["simboard"]["simulation_type"]
    try:
        web_portal_base_path = machine_info.config.get("web_portal", "base_path")
    except (NoSectionError, NoOptionError) as exc:
        raise ValueError(
            f"www is empty and simboard.enabled is True, but machine "
            f"'{machine_info.machine}' has no web_portal.base_path in mache; "
            "cannot infer a diagnostics_archive path."
        ) from exc

    web_portal_base_path = normalize_web_portal_base_path(web_portal_base_path)
    if web_portal_base_path == "":
        raise ValueError(
            f"www is empty and simboard.enabled is True, but machine "
            f"'{machine_info.machine}' has an empty web_portal.base_path in "
            "mache; cannot infer a diagnostics_archive path."
        )

    # Group the simulation under its case group when it has one, so SimBoard
    # sees e.g. `.../production/v3.LR/<case>/` instead of a flat list of cases.
    case_group_segment = _normalize_case_group(case_group)
    # Development output is per-user: several people may run diagnostics on the
    # same case. Production stays unnested -- one authoritative path per case.
    user_segment = (
        f"{machine_info.username}/" if simulation_type == "development" else ""
    )
    inferred_www = (
        f"{web_portal_base_path}/diagnostics_archive/"
        f"{simulation_type}/{case_group_segment}{user_segment}"
    )
    logger.info(
        "Inferred www=%s from mache web_portal.base_path because "
        "simboard.enabled is True.",
        inferred_www,
    )
    return inferred_www
