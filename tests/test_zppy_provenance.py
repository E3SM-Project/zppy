"""Unit tests for zppy.provenance helpers (issue #831)."""

import configparser
import os
import textwrap
from typing import Dict, Optional
from unittest.mock import MagicMock

from zppy.provenance import (
    append_provenance_fields,
    build_diagnostics_url,
    build_provenance_extras,
    parse_env_case_xml,
)


def _write_env_case_xml(input_dir: str, entries: Dict[str, Optional[str]]) -> str:
    """Create <input_dir>/case_scripts/env_case.xml with the given entries.

    If a value is None, write the entry tag without a value= attribute so we
    can exercise the missing-attribute branch.
    """
    case_scripts = os.path.join(input_dir, "case_scripts")
    os.makedirs(case_scripts, exist_ok=True)
    xml_path = os.path.join(case_scripts, "env_case.xml")
    lines = ['<?xml version="1.0"?>', "<file>"]
    for entry_id, value in entries.items():
        if value is None:
            lines.append(f'  <entry id="{entry_id}"><type>char</type></entry>')
        else:
            lines.append(
                f'  <entry id="{entry_id}" value="{value}"><type>char</type></entry>'
            )
    lines.append("</file>")
    with open(xml_path, "w") as f:
        f.write("\n".join(lines))
    return xml_path


def _fake_machine_info(
    machine: str = "pm-cpu", web_portal: Optional[Dict[str, str]] = None
) -> MagicMock:
    """Build a MachineInfo-like mock whose .config is a real ConfigParser.

    Real ConfigParser is used so the production code path that catches
    NoSectionError / NoOptionError is exercised.
    """
    cp = configparser.ConfigParser()
    if web_portal is not None:
        cp["web_portal"] = web_portal
    mi = MagicMock()
    mi.machine = machine
    mi.config = cp
    return mi


# ---------------------------------------------------------------------------
# parse_env_case_xml
# ---------------------------------------------------------------------------


def test_parse_env_case_xml_happy(tmp_path):
    _write_env_case_xml(
        str(tmp_path),
        {"CASE": "v3.LR.historical_0051", "MACH": "chrysalis", "REALUSER": "ac.wlin"},
    )
    result = parse_env_case_xml(str(tmp_path))
    assert result == {
        "case_name": "v3.LR.historical_0051",
        "machine": "chrysalis",
        "hpc_username": "ac.wlin",
    }


def test_parse_env_case_xml_missing_file(tmp_path):
    # No case_scripts dir at all.
    assert parse_env_case_xml(str(tmp_path)) == {}


def test_parse_env_case_xml_partial(tmp_path):
    _write_env_case_xml(
        str(tmp_path), {"CASE": "v3.LR.historical_0051", "MACH": "chrysalis"}
    )
    result = parse_env_case_xml(str(tmp_path))
    assert result == {"case_name": "v3.LR.historical_0051", "machine": "chrysalis"}
    assert "hpc_username" not in result


def test_parse_env_case_xml_entry_without_value(tmp_path):
    _write_env_case_xml(
        str(tmp_path),
        {"CASE": "v3.LR.historical_0051", "MACH": None, "REALUSER": "ac.wlin"},
    )
    result = parse_env_case_xml(str(tmp_path))
    assert "machine" not in result
    assert result["case_name"] == "v3.LR.historical_0051"
    assert result["hpc_username"] == "ac.wlin"


def test_parse_env_case_xml_malformed(tmp_path):
    case_scripts = tmp_path / "case_scripts"
    case_scripts.mkdir()
    (case_scripts / "env_case.xml").write_text("<not-valid-xml")
    assert parse_env_case_xml(str(tmp_path)) == {}


# ---------------------------------------------------------------------------
# build_diagnostics_url
# ---------------------------------------------------------------------------


def test_build_diagnostics_url_happy():
    mi = _fake_machine_info(
        web_portal={
            "base_path": "/global/cfs/cdirs/e3sm/www",
            "base_url": "https://portal.nersc.gov/cfs/e3sm",
        }
    )
    url = build_diagnostics_url(
        "/global/cfs/cdirs/e3sm/www/zppy_demo",
        "v3.LR.historical_0051",
        mi,
    )
    assert url == "https://portal.nersc.gov/cfs/e3sm/zppy_demo/v3.LR.historical_0051"


def test_build_diagnostics_url_www_outside_base_path():
    mi = _fake_machine_info(
        web_portal={
            "base_path": "/global/cfs/cdirs/e3sm/www",
            "base_url": "https://portal.nersc.gov/cfs/e3sm",
        }
    )
    assert build_diagnostics_url("/tmp/elsewhere", "case", mi) is None


def test_build_diagnostics_url_missing_machine_cfg():
    mi = _fake_machine_info(web_portal=None)
    assert build_diagnostics_url("/some/www", "case", mi) is None


def test_build_diagnostics_url_empty_www():
    mi = _fake_machine_info(web_portal={"base_path": "/x", "base_url": "https://x"})
    assert build_diagnostics_url("", "case", mi) is None


# ---------------------------------------------------------------------------
# append_provenance_fields
# ---------------------------------------------------------------------------


def test_append_provenance_fields_appends(tmp_path):
    src = tmp_path / "user.cfg"
    src.write_text(
        textwrap.dedent(
            """\
        [default]
        case = v3.LR.historical_0051
        # a comment the user wrote
        input = /lcrc/group/e3sm2/x/v3.LR.historical_0051
    """
        )
    )
    append_provenance_fields(
        str(src),
        {
            "case_name": "v3.LR.historical_0051",
            "machine": "chrysalis",
            "diagnostics_url": "https://portal/x/case",
        },
    )
    content = src.read_text()
    # Original content preserved verbatim
    assert "# a comment the user wrote" in content
    assert "case = v3.LR.historical_0051" in content
    # Additions present, marked, and under a [default] header so configobj
    # picks them up as default-section keys.
    assert "# --- zppy provenance additions (issue #831) ---" in content
    assert "case_name = v3.LR.historical_0051" in content
    assert "machine = chrysalis" in content
    assert "diagnostics_url = https://portal/x/case" in content
    # The addition block follows the user content.
    assert content.index("# a comment the user wrote") < content.index(
        "# --- zppy provenance additions (issue #831) ---"
    )


def test_append_provenance_fields_skips_empty(tmp_path):
    src = tmp_path / "user.cfg"
    src.write_text("[default]\ncase = c\n")
    append_provenance_fields(str(src), {})
    assert src.read_text() == "[default]\ncase = c\n"
    append_provenance_fields(str(src), {"case_name": "", "machine": None})
    assert src.read_text() == "[default]\ncase = c\n"


def test_append_provenance_fields_skips_falsy_values(tmp_path):
    src = tmp_path / "user.cfg"
    src.write_text("[default]\n")
    append_provenance_fields(
        str(src),
        {"case_name": "good", "machine": "", "hpc_username": None},
    )
    content = src.read_text()
    assert "case_name = good" in content
    assert "machine =" not in content.split("# --- zppy provenance additions")[1]
    assert "hpc_username" not in content.split("# --- zppy provenance additions")[1]


# ---------------------------------------------------------------------------
# build_provenance_extras (integration of the three pieces)
# ---------------------------------------------------------------------------


def test_build_provenance_extras_full(tmp_path):
    input_dir = tmp_path / "v3.LR.historical_0051"
    input_dir.mkdir()
    _write_env_case_xml(
        str(input_dir),
        {"CASE": "v3.LR.historical_0051", "MACH": "pm-cpu", "REALUSER": "ac.zhang40"},
    )
    mi = _fake_machine_info(
        machine="pm-cpu",
        web_portal={
            "base_path": "/global/cfs/cdirs/e3sm/www",
            "base_url": "https://portal.nersc.gov/cfs/e3sm",
        },
    )
    cfg_default = {
        "input": str(input_dir),
        "case": "v3.LR.historical_0051",
        "www": "/global/cfs/cdirs/e3sm/www/ac.zhang40/zppy_demo",
    }
    extras = build_provenance_extras(cfg_default, mi)
    assert extras["case_name"] == "v3.LR.historical_0051"
    assert extras["machine"] == "pm-cpu"
    assert extras["hpc_username"] == "ac.zhang40"
    assert extras["diagnostics_url"] == (
        "https://portal.nersc.gov/cfs/e3sm/ac.zhang40/zppy_demo/v3.LR.historical_0051"
    )


def test_build_provenance_extras_missing_input(tmp_path, caplog):
    mi = _fake_machine_info(web_portal={"base_path": "/x", "base_url": "https://x"})
    cfg_default = {"input": "", "case": "c", "www": "/x/y"}
    extras = build_provenance_extras(cfg_default, mi)
    # No case identity fields, but diagnostics_url is still computed.
    assert "case_name" not in extras
    assert extras["diagnostics_url"] == "https://x/y/c"


def test_build_provenance_extras_case_mismatch_warns(tmp_path, caplog):
    input_dir = tmp_path / "case_input"
    input_dir.mkdir()
    _write_env_case_xml(str(input_dir), {"CASE": "actual_case_name"})
    mi = _fake_machine_info(web_portal=None)
    cfg_default = {"input": str(input_dir), "case": "user_typo_case", "www": ""}
    with caplog.at_level("WARNING"):
        extras = build_provenance_extras(cfg_default, mi)
    # case_name is authoritative from env_case.xml.
    assert extras["case_name"] == "actual_case_name"
    # Warning surfaced (best-effort: don't pin exact text).
    assert any("does not match" in r.message for r in caplog.records)


def test_build_provenance_extras_unsupported_machine(tmp_path):
    """Machine has no web_portal config -> diagnostics_url omitted,
    case identity fields still emitted."""
    input_dir = tmp_path / "case_input"
    input_dir.mkdir()
    _write_env_case_xml(
        str(input_dir),
        {"CASE": "c", "MACH": "anvil", "REALUSER": "u"},
    )
    mi = _fake_machine_info(machine="anvil", web_portal=None)
    cfg_default = {"input": str(input_dir), "case": "c", "www": "/some/www"}
    extras = build_provenance_extras(cfg_default, mi)
    assert extras == {"case_name": "c", "machine": "anvil", "hpc_username": "u"}
    assert "diagnostics_url" not in extras


def test_build_provenance_extras_empty_when_nothing_resolvable(tmp_path):
    mi = _fake_machine_info(web_portal=None)
    cfg_default = {"input": "", "case": "", "www": ""}
    assert build_provenance_extras(cfg_default, mi) == {}
