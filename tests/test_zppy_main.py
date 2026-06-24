import configparser
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest
from configobj import ConfigObj
from validate import Validator

from zppy.__main__ import _determine_parameters


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
            "simboard_type": "prod",
            "www": "",
        }
    }


@pytest.mark.parametrize(
    ("simboard_type", "expected_www"),
    [
        ("prod", "/global/cfs/cdirs/e3sm/www/simboard/prod/"),
        ("dev", "/global/cfs/cdirs/e3sm/www/simboard/dev/"),
    ],
)
def test_determine_parameters_infers_simboard_www(
    simboard_type: str, expected_www: str
) -> None:
    config = _base_config()
    config["default"]["simboard_type"] = simboard_type

    updated = _determine_parameters(_fake_machine_info(), config)

    assert updated["default"]["www"] == expected_www


def test_determine_parameters_requires_www_without_path_inference() -> None:
    config = _base_config()
    config["default"]["infer_path_parameters"] = False

    with pytest.raises(
        ValueError, match="www must be provided when infer_path_parameters is False."
    ):
        _determine_parameters(_fake_machine_info(), config)


def test_default_ini_rejects_invalid_simboard_type(tmp_path: Path) -> None:
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
                "simboard_type = invalid",
            ]
        )
    )
    config = ConfigObj(
        str(config_path),
        configspec=str(default_ini),
    )

    result = config.validate(Validator())

    assert result is not True
    assert result["default"]["simboard_type"] is False
