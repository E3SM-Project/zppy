import os

import pytest
from configobj import ConfigObj

from zppy.simboard import validate_www_access

pytestmark = pytest.mark.skipif(
    os.getuid() == 0, reason="root bypasses the permission bits under test"
)


def _config(enabled: bool, simulation_type: str = "production") -> ConfigObj:
    config = ConfigObj()
    config["simboard"] = {"enabled": enabled, "simulation_type": simulation_type}
    return config


def _make_foreign(monkeypatch, path) -> None:
    foreign_uid = os.stat(path).st_uid + 1
    monkeypatch.setattr("zppy.simboard.os.getuid", lambda: foreign_uid)


def test_missing_case_dir_is_allowed(tmp_path) -> None:
    validate_www_access(_config(True), str(tmp_path), "case")


def test_case_dir_owned_by_current_user_is_allowed(tmp_path) -> None:
    (tmp_path / "case").mkdir()
    validate_www_access(_config(True), str(tmp_path), "case")


def test_foreign_production_case_dir_is_rejected(tmp_path, monkeypatch) -> None:
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    _make_foreign(monkeypatch, case_dir)
    with pytest.raises(ValueError, match="one authoritative diagnostics path"):
        validate_www_access(_config(True, "production"), str(tmp_path), "case")


def test_foreign_development_case_dir_is_rejected(tmp_path, monkeypatch) -> None:
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    _make_foreign(monkeypatch, case_dir)
    with pytest.raises(ValueError, match=r"\[default\] www"):
        validate_www_access(_config(True, "development"), str(tmp_path), "case")


def test_foreign_case_dir_only_warns_when_simboard_disabled(
    tmp_path, monkeypatch, caplog
) -> None:
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    _make_foreign(monkeypatch, case_dir)
    validate_www_access(_config(False), str(tmp_path), "case")
    assert "is owned by" in caplog.text


def test_unwritable_case_dir_is_rejected(tmp_path) -> None:
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    case_dir.chmod(0o555)
    try:
        with pytest.raises(ValueError, match="Cannot write to www case directory"):
            validate_www_access(_config(True), str(tmp_path), "case")
    finally:
        case_dir.chmod(0o755)
