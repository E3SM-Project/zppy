import ast
import configparser
import re
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import MagicMock

import pytest
from configobj import ConfigObj
from validate import Validator

from zppy.__main__ import _determine_parameters
from zppy.utils import write_settings_file

_WEB_PORTAL_BASE_PATH = "/global/cfs/cdirs/e3sm/www"


def _default_ini_path() -> Path:
    return Path(__file__).resolve().parents[2] / "zppy" / "defaults" / "default.ini"


def _write_cfg(tmp_path: Path, *, www: str, simboard_enabled: bool) -> Path:
    config_path = tmp_path / "simboard_settings.cfg"
    config_path.write_text(
        "\n".join(
            [
                "[default]",
                "case = test_case",
                "input = /input",
                f"output = {tmp_path / 'output'}",
                "dry_run = True",
                "machine = pm-cpu",
                f"www = {www}",
                "",
                "[simboard]",
                f"enabled = {'True' if simboard_enabled else 'False'}",
                "simulation_type = production",
                "",
            ]
        )
    )
    return config_path


def _validated_config(config_path: Path) -> ConfigObj:
    config = ConfigObj(str(config_path), configspec=str(_default_ini_path()))
    validation_result = config.validate(Validator())
    assert validation_result is True
    return config


def _fake_machine_info(
    web_portal_base_path: Optional[str] = _WEB_PORTAL_BASE_PATH,
) -> MagicMock:
    machine_config = configparser.ConfigParser()
    machine_config["e3sm_unified"] = {"base_path": "/unified"}
    machine_config["diagnostics"] = {"base_path": "/diagnostics"}
    machine_config["web_portal"] = {"base_url": "https://portal.nersc.gov/cfs/e3sm"}
    if web_portal_base_path is not None:
        machine_config["web_portal"]["base_path"] = web_portal_base_path

    machine_info = MagicMock()
    machine_info.machine = "pm-cpu"
    machine_info.config = machine_config
    machine_info.get_account_defaults.return_value = ("e3sm", "regular", "cpu", None)
    return machine_info


def _write_default_settings(tmp_path: Path, config: ConfigObj) -> Path:
    settings_path = tmp_path / "resolved_default.settings"
    write_settings_file(str(settings_path), dict(config["default"]), (1, 1))
    return settings_path


def _read_default_settings(settings_path: Path) -> Dict[str, Any]:
    settings_text = settings_path.read_text()
    parsed_settings = ast.parse(settings_text, mode="exec")
    assert parsed_settings.body
    first_expression = parsed_settings.body[0]
    assert isinstance(first_expression, ast.Expr)
    default_settings = ast.literal_eval(first_expression.value)
    assert isinstance(default_settings, dict)
    return default_settings


def test_simboard_disabled_preserves_explicit_www(tmp_path: Path) -> None:
    config_path = _write_cfg(
        tmp_path, www="/some/explicit/path", simboard_enabled=False
    )
    config = _validated_config(config_path)

    updated_config = _determine_parameters(_fake_machine_info(), config)
    settings_path = _write_default_settings(tmp_path, updated_config)
    default_settings = _read_default_settings(settings_path)

    assert default_settings["www"] == "/some/explicit/path"


def test_simboard_enabled_infers_www_from_machine_info(tmp_path: Path) -> None:
    config_path = _write_cfg(tmp_path, www="", simboard_enabled=True)
    config = _validated_config(config_path)
    expected_www = f"{_WEB_PORTAL_BASE_PATH}/diagnostics_archive/production/"

    updated_config = _determine_parameters(_fake_machine_info(), config)
    settings_path = _write_default_settings(tmp_path, updated_config)
    default_settings = _read_default_settings(settings_path)

    assert default_settings["www"] == expected_www


def test_simboard_enabled_preserves_explicit_www(tmp_path: Path) -> None:
    config_path = _write_cfg(tmp_path, www="/custom/path", simboard_enabled=True)
    config = _validated_config(config_path)

    updated_config = _determine_parameters(_fake_machine_info(), config)
    settings_path = _write_default_settings(tmp_path, updated_config)
    default_settings = _read_default_settings(settings_path)

    assert default_settings["www"] == "/custom/path"


def test_simboard_enabled_empty_www_requires_inferable_path(tmp_path: Path) -> None:
    config_path = _write_cfg(tmp_path, www="", simboard_enabled=True)
    config = _validated_config(config_path)
    expected_message = (
        "www is empty and simboard.enabled is True, but machine 'pm-cpu' "
        "has no web_portal.base_path in mache; cannot infer a "
        "diagnostics_archive path."
    )

    with pytest.raises(ValueError, match=re.escape(expected_message)):
        _determine_parameters(_fake_machine_info(web_portal_base_path=None), config)
