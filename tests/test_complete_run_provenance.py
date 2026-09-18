"""Tests for complete run provenance.

The ``env_description.txt`` format is a contract with every expected-results
directory already promoted on disk: a later run reads its ``Generated:`` line
back to date the baselines it is testing against. These tests guard that
format, not merely the code that writes it.
"""

import json
import os
from datetime import datetime
from typing import List

import pytest

from tests.complete_run import provenance
from tests.complete_run.environments import ENV_TYPE_DEV, ENV_TYPE_UNIFIED, Environment
from tests.complete_run.worktrees import Checkout

# A file in the format promoted baselines already carry.
PROMOTED_EXAMPLE = """Task: global_time_series
Generated: 2026-08-04 11:22:33

Repository: /home/user/ez/zppy-interfaces
Commit: 1234567890abcdef1234567890abcdef12345678
Commit (short): 12345678
Branch: main

Conda environment (dev): test-zppy_interfaces-main-20260804_run1

Package versions:
-----------------
# packages in environment at /home/user/envs/test:
xarray                    2025.1.0           pyhd8ed1ab_0
"""


@pytest.fixture
def checkout() -> Checkout:
    return Checkout(
        name="zppy_interfaces",
        source_repo="/home/user/ez/zppy-interfaces",
        path="/scratch/worktrees/zppy_interfaces",
        sha="1234567890abcdef1234567890abcdef12345678",
        short_sha="12345678",
        branch="main",
        remote="upstream",
    )


@pytest.fixture
def dev_environment() -> Environment:
    return Environment(
        repo_name="zppy_interfaces",
        env_type=ENV_TYPE_DEV,
        name="test-zppy_interfaces-main-20260804_run1",
        activation_command="source conda.sh; conda activate test",
    )


def test_render_matches_the_promoted_format(
    checkout: Checkout, dev_environment: Environment
) -> None:
    rendered = provenance.render_env_description(
        "global_time_series",
        checkout,
        dev_environment,
        "# packages in environment at /home/user/envs/test:\n"
        "xarray                    2025.1.0           pyhd8ed1ab_0",
        generated=datetime(2026, 8, 4, 11, 22, 33),
    )
    assert rendered == PROMOTED_EXAMPLE


def test_generated_date_round_trips(
    tmp_path, checkout: Checkout, dev_environment: Environment
) -> None:
    rendered = provenance.render_env_description(
        "global_time_series",
        checkout,
        dev_environment,
        "packages",
        generated=datetime(2026, 8, 4, 11, 22, 33),
    )
    path = tmp_path / "env_description.txt"
    path.write_text(rendered)

    assert provenance.read_generated_date(str(path)) == "2026-08-04"


def test_generated_date_reads_a_promoted_baseline(tmp_path) -> None:
    path = tmp_path / "env_description.txt"
    path.write_text(PROMOTED_EXAMPLE)
    assert provenance.read_generated_date(str(path)) == "2026-08-04"


def test_generated_date_is_unknown_rather_than_an_error(tmp_path) -> None:
    # Baselines promoted before environment descriptions existed are still
    # valid; their date is simply unknown.
    missing = tmp_path / "absent.txt"
    assert provenance.read_generated_date(str(missing)) is None

    dateless = tmp_path / "dateless.txt"
    dateless.write_text("Task: e3sm_diags\n")
    assert provenance.read_generated_date(str(dateless)) is None


def test_unified_environment_records_no_repository() -> None:
    rendered = provenance.render_env_description(
        "livvkit",
        None,
        Environment("livvkit", ENV_TYPE_UNIFIED, "", "source unified.sh"),
        "packages",
        generated=datetime(2026, 8, 4, 11, 22, 33),
    )
    assert (
        "Repository: N/A (uses a released package via the unified environment)"
        in rendered
    )
    assert "Conda environment: E3SM-Unified" in rendered
    assert "Commit:" not in rendered


def test_www_root_is_read_verbatim_from_the_cfg(tmp_path) -> None:
    # The cfg's www value is already fully resolved. Re-deriving it would create
    # a duplicate subtree the expected-results updater never picks up.
    cfg = tmp_path / "test_weekly_comprehensive_v3_chrysalis.cfg"
    cfg.write_text(
        "[default]\n"
        "output = /lcrc/group/e3sm/user/zppy_weekly_comprehensive_v3_output/id\n"
        "www = /lcrc/group/e3sm/public_html/user/zppy_weekly_comprehensive_v3_www/id\n"
    )
    assert (
        provenance.www_root_from_cfg(str(cfg))
        == "/lcrc/group/e3sm/public_html/user/zppy_weekly_comprehensive_v3_www/id"
    )


def test_www_root_missing_is_none(tmp_path) -> None:
    cfg = tmp_path / "no_www.cfg"
    cfg.write_text("[default]\noutput = /tmp/out\n")
    assert provenance.www_root_from_cfg(str(cfg)) is None
    assert provenance.www_root_from_cfg(str(tmp_path / "absent.cfg")) is None


def test_distribute_appends_only_case_and_task(tmp_path) -> None:
    www_root = tmp_path / "zppy_weekly_comprehensive_v3_www" / "unique_id"
    generated = tmp_path / "tests" / "integration" / "generated"
    generated.mkdir(parents=True)
    (generated / "test_weekly_comprehensive_v3_chrysalis.cfg").write_text(
        f"www = {www_root}\n"
    )

    env_dir = tmp_path / "env_descriptions"
    env_dir.mkdir()
    (env_dir / "e3sm_diags.txt").write_text(PROMOTED_EXAMPLE)

    roots = provenance.distribute_env_descriptions(
        str(env_dir),
        str(tmp_path),
        ["weekly_comprehensive_v3"],
        ["e3sm_diags"],
        "chrysalis",
    )

    assert roots == {"weekly_comprehensive_v3": str(www_root)}
    expected = www_root / "v3.LR.historical_0051" / "e3sm_diags" / "env_description.txt"
    assert expected.is_file()
    # The www prefix must appear exactly once in the path.
    assert str(expected).count("zppy_weekly_comprehensive_v3_www") == 1


def test_distribute_uses_the_v2_case_for_v2_cfgs(tmp_path) -> None:
    www_root = tmp_path / "www"
    generated = tmp_path / "tests" / "integration" / "generated"
    generated.mkdir(parents=True)
    (generated / "test_weekly_comprehensive_v2_chrysalis.cfg").write_text(
        f"www = {www_root}\n"
    )
    env_dir = tmp_path / "env"
    env_dir.mkdir()
    (env_dir / "ilamb.txt").write_text(PROMOTED_EXAMPLE)

    provenance.distribute_env_descriptions(
        str(env_dir),
        str(tmp_path),
        ["weekly_comprehensive_v2"],
        ["ilamb"],
        "chrysalis",
    )

    assert (
        www_root / "v2.LR.historical_0201" / "ilamb" / "env_description.txt"
    ).is_file()


def test_manifest_records_every_repository(
    tmp_path, checkout: Checkout, dev_environment: Environment
) -> None:
    manifest = provenance.build_manifest(
        tag="20260804_run1",
        machine="chrysalis",
        checkouts=[checkout],
        environments={"zppy_interfaces": dev_environment},
        cfgs=["weekly_comprehensive_v3"],
        tasks=["global_time_series"],
        zppy_version="v3.2.0",
    )
    path = provenance.write_manifest(str(tmp_path), manifest)

    with open(path) as stream:
        written = json.load(stream)

    assert written["tag"] == "20260804_run1"
    assert written["repos"]["zppy_interfaces"]["sha"] == checkout.sha
    assert written["repos"]["zppy_interfaces"]["environment"] == dev_environment.name
    assert os.path.basename(path) == provenance.MANIFEST_FILENAME


def test_package_list_failure_is_recorded_not_raised(
    monkeypatch: pytest.MonkeyPatch, dev_environment: Environment
) -> None:
    # A run that already spent hours of compute must not die here.
    monkeypatch.setattr(provenance, "run_command", lambda *args, **kwargs: "")
    listing = provenance.conda_package_list(dev_environment)
    assert "unable to list packages" in listing


def test_unified_package_list_loads_unified_first(monkeypatch) -> None:
    # A bare `conda list` would describe the controller's environment instead.
    seen: List[List[str]] = []

    def run(args: List[str], **kwargs) -> str:
        seen.append(args)
        return "pkgs"

    monkeypatch.setattr(provenance, "run_command", run)
    unified = Environment("livvkit", "unified", "", "source load_unified.sh")
    assert provenance.conda_package_list(unified) == "pkgs"
    assert seen[0][:2] == ["bash", "-c"]
    assert seen[0][2].startswith("source load_unified.sh")
    assert seen[0][2].endswith("conda list")
