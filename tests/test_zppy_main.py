import configparser
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest
from configobj import ConfigObj
from validate import Validator

from zppy.__main__ import _determine_parameters
from zppy.simboard import simboard


def _fake_machine_info() -> MagicMock:
    config = configparser.ConfigParser()
    config["e3sm_unified"] = {"base_path": "/unified"}
    config["diagnostics"] = {"base_path": "/diagnostics"}
    config["web_portal"] = {
        "base_path": "/global/cfs/cdirs/e3sm/www",
        "base_url": "https://portal.nersc.gov/cfs/e3sm",
    }
    machine_info = MagicMock()
    machine_info.machine = "pm-cpu"
    machine_info.config = config
    machine_info.get_account_defaults.return_value = ("e3sm", "regular", "cpu", None)
    return machine_info


def _base_config() -> Dict[str, Dict[str, Any]]:
    return {
        "default": {
            "machine": "",
            "account": "",
            "partition": "",
            "constraint": "",
            "environment_commands": "",
            "infer_path_parameters": True,
            "www": "",
        },
        "simboard": {
            "enabled": False,
            "simulation_type": "production",
        },
    }


@pytest.mark.parametrize(
    ("simulation_type", "expected_www"),
    [
        (
            "production",
            "/global/cfs/cdirs/e3sm/www/diagnostics_archive/production/",
        ),
        (
            "development",
            "/global/cfs/cdirs/e3sm/www/diagnostics_archive/development/",
        ),
    ],
)
def test_determine_parameters_infers_simboard_www(
    simulation_type: str, expected_www: str
) -> None:
    config = _base_config()
    config["simboard"]["enabled"] = True
    config["simboard"]["simulation_type"] = simulation_type

    updated = _determine_parameters(_fake_machine_info(), config)

    assert updated["default"]["www"] == expected_www


def test_determine_parameters_preserves_explicit_www_when_simboard_enabled() -> None:
    config = _base_config()
    config["default"]["www"] = "/custom/www"
    config["simboard"]["enabled"] = True

    updated = _determine_parameters(_fake_machine_info(), config)

    assert updated["default"]["www"] == "/custom/www"


def test_determine_parameters_requires_www_without_simboard() -> None:
    config = _base_config()

    with pytest.raises(
        ValueError,
        match=(
            r"www is empty\. Provide \[default\] www or set `enabled = True` "
            r"in the \[simboard\] section"
        ),
    ):
        _determine_parameters(_fake_machine_info(), config)


def test_determine_parameters_rejects_none_simulation_type_when_enabled() -> None:
    config = _base_config()
    config["simboard"]["enabled"] = True
    config["simboard"]["simulation_type"] = "none"

    with pytest.raises(
        ValueError,
        match=(
            "simboard.simulation_type must be 'production' or 'development' "
            "when simboard.enabled is True."
        ),
    ):
        _determine_parameters(_fake_machine_info(), config)


def test_determine_parameters_requires_inferable_web_root() -> None:
    config = _base_config()
    config["simboard"]["enabled"] = True
    machine_info = _fake_machine_info()
    machine_info.config.remove_option("web_portal", "base_path")

    with pytest.raises(
        ValueError,
        match=(
            "www is empty and simboard.enabled is True, but machine 'pm-cpu' "
            "has no web_portal.base_path in mache; cannot infer a "
            "diagnostics_archive path."
        ),
    ):
        _determine_parameters(machine_info, config)


def test_determine_parameters_rejects_empty_web_root() -> None:
    config = _base_config()
    config["simboard"]["enabled"] = True
    machine_info = _fake_machine_info()
    machine_info.config["web_portal"]["base_path"] = "   "

    with pytest.raises(
        ValueError,
        match=(
            "www is empty and simboard.enabled is True, but machine 'pm-cpu' "
            "has an empty web_portal.base_path in mache; cannot infer a "
            "diagnostics_archive path."
        ),
    ):
        _determine_parameters(machine_info, config)


def test_simboard_rejects_subsections(tmp_path: Path) -> None:
    config_path = tmp_path / "bad_simboard_subsection.cfg"
    default_ini = Path(__file__).resolve().parents[1] / "zppy" / "defaults" / "default.ini"
    config_path.write_text(
        "\n".join(
            [
                "[default]",
                "case = case_name",
                "input = /input",
                "output = /output",
                "www = /www",
                "",
                "[simboard]",
                "enabled = False",
                "simulation_type = production",
                "",
                "  [[nested]]",
                "  placeholder = value",
            ]
        )
    )
    config = ConfigObj(str(config_path), configspec=str(default_ini))

    with pytest.raises(
        ValueError, match="The \\[simboard\\] section does not support subsections."
    ):
        simboard(config, "", [], "")


def test_default_ini_rejects_invalid_simulation_type(tmp_path: Path) -> None:
    config_path = tmp_path / "bad_simboard.cfg"
    default_ini = Path(__file__).resolve().parents[1] / "zppy" / "defaults" / "default.ini"
    config_path.write_text(
        "\n".join(
            [
                "[default]",
                "case = case_name",
                "input = /input",
                "output = /output",
                "www = /www",
                "",
                "[simboard]",
                "simulation_type = invalid",
            ]
        )
    )
    config = ConfigObj(
        str(config_path),
        configspec=str(default_ini),
    )

    result = config.validate(Validator())

    assert result is not True
    assert result["simboard"]["simulation_type"] is False
