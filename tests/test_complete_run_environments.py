"""Tests for how a run's environments are built and reproduced.

Three modes matter, because a difference in results is only attributable if one
of code and dependencies was held fixed:

* ``dev`` solves each repository's dev.yml afresh -- differences may come from
  either.
* ``baseline`` rebuilds the environment the baseline was produced with, so a
  difference is attributable to code.
* ``unified`` runs a task from the released E3SM-Unified environment.
"""

import os
from typing import List

import pytest

from tests.complete_run import environments, provenance
from tests.complete_run.environments import (
    ENV_TYPE_BASELINE,
    ENV_TYPE_DEV,
    ENV_TYPE_UNIFIED,
    Environment,
)
from tests.complete_run.params import MACHINE_PROFILES, REPO_SPECS_BY_NAME
from tests.complete_run.worktrees import Checkout

EXPORTED = """name: test-e3sm_diags-main-20260901_run1
channels:
  - conda-forge
dependencies:
  - python=3.13.1
  - xarray=2025.1.0
  - pip:
    - e3sm-diags==3.0.0
"""


@pytest.fixture
def checkout(tmp_path) -> Checkout:
    path = tmp_path / "worktree"
    path.mkdir()
    return Checkout(
        name="e3sm_diags",
        source_repo=str(tmp_path / "clone"),
        path=str(path),
        sha="a" * 40,
        short_sha="a" * 8,
        branch="main",
        remote="upstream",
    )


def _record(monkeypatch, calls):
    monkeypatch.setattr(
        environments,
        "run_command",
        lambda args, **kwargs: calls.append(list(args)) or "",
    )
    monkeypatch.setattr(environments, "environment_exists", lambda name: False)


def test_dev_solves_the_repository_env_file(monkeypatch, checkout) -> None:
    calls: List[List[str]] = []
    _record(monkeypatch, calls)

    environments.create_environment(
        REPO_SPECS_BY_NAME["e3sm_diags"], checkout, "20260918_run1", "/conda.sh"
    )

    created = [c for c in calls if c[:3] == ["conda", "env", "create"]]
    assert created[0][:5] == ["conda", "env", "create", "-f", "conda-env/dev.yml"]


def test_mpas_analysis_uses_dev_spec_not_dev_yml(monkeypatch, checkout) -> None:
    calls: List[List[str]] = []
    _record(monkeypatch, calls)

    environments.create_environment(
        REPO_SPECS_BY_NAME["mpas_analysis"], checkout, "tag", "/conda.sh"
    )

    # MPAS-Analysis pins its environment differently from the others.
    assert ["conda", "create"] == calls[0][:2]
    assert "dev-spec.txt" in calls[0]


def test_baseline_rebuilds_from_the_exported_environment(
    monkeypatch, checkout, tmp_path
) -> None:
    exported = tmp_path / "e3sm_diags.yml"
    exported.write_text(EXPORTED)
    calls: List[List[str]] = []
    _record(monkeypatch, calls)

    environments.create_environment(
        REPO_SPECS_BY_NAME["e3sm_diags"],
        checkout,
        "tag",
        "/conda.sh",
        environment_file=str(exported),
    )

    created = [c for c in calls if c[:3] == ["conda", "env", "create"]]
    # Dependencies come from the baseline, not from a fresh solve.
    assert str(exported) in created[0]
    assert "conda-env/dev.yml" not in " ".join(created[0])


def test_baseline_still_installs_the_code_under_test(
    monkeypatch, checkout, tmp_path
) -> None:
    exported = tmp_path / "e3sm_diags.yml"
    exported.write_text(EXPORTED)
    calls: List[List[str]] = []
    _record(monkeypatch, calls)

    environments.create_environment(
        REPO_SPECS_BY_NAME["e3sm_diags"],
        checkout,
        "tag",
        "/conda.sh",
        environment_file=str(exported),
    )

    # The whole point: baseline dependencies, the revision under test.
    installs = [c for c in calls if "pip" in c and "install" in c]
    assert installs, "the worktree must still be installed"


def test_missing_export_explains_why(monkeypatch, checkout, tmp_path) -> None:
    _record(monkeypatch, [])
    with pytest.raises(FileNotFoundError, match="predates environment exports"):
        environments.create_environment(
            REPO_SPECS_BY_NAME["e3sm_diags"],
            checkout,
            "tag",
            "/conda.sh",
            environment_file=str(tmp_path / "absent.yml"),
        )


def test_existing_environment_is_not_silently_reused(monkeypatch, checkout) -> None:
    monkeypatch.setattr(environments, "run_command", lambda args, **kwargs: "")
    monkeypatch.setattr(environments, "environment_exists", lambda name: True)

    with pytest.raises(FileExistsError, match="already exists"):
        environments.create_environment(
            REPO_SPECS_BY_NAME["e3sm_diags"], checkout, "tag", "/conda.sh"
        )


def test_nominated_environment_is_reused_and_reinstalled(monkeypatch, checkout) -> None:
    calls: List[List[str]] = []
    _record(monkeypatch, calls)

    environment = environments.create_environment(
        REPO_SPECS_BY_NAME["e3sm_diags"],
        checkout,
        "tag",
        "/conda.sh",
        existing_env="my-env",
    )

    assert environment.reused
    assert environment.name == "my-env"
    # Reused or not, the code under test is installed from the worktree.
    assert any("pip" in c and "install" in c for c in calls)


def test_unified_tasks_get_the_machine_activation_command() -> None:
    machine = MACHINE_PROFILES["chrysalis"]
    environment = environments.unified_environment("mpas_analysis", machine)
    assert environment.env_type == ENV_TYPE_UNIFIED
    assert environment.activation_command == machine.unified_env_cmd
    assert "e3sm-unified" in environment.activation_command


def test_task_environment_commands_cover_every_task() -> None:
    machine = MACHINE_PROFILES["chrysalis"]
    built = {
        name: Environment(name, ENV_TYPE_DEV, f"env-{name}", f"activate env-{name}")
        for name in REPO_SPECS_BY_NAME
    }
    by_task = environments.environments_by_task(built, machine)

    assert by_task["e3sm_diags"].activation_command == "activate env-e3sm_diags"
    # zppy-interfaces backs two tasks.
    assert by_task["global_time_series"] is by_task["pcmdi_diags"]
    # livvkit has no dev repo of its own.
    assert by_task["livvkit"].activation_command == machine.unified_env_cmd


def test_run_args_run_inside_the_environment() -> None:
    environment = Environment("zppy", ENV_TYPE_DEV, "env-zppy", "activate")
    assert environment.run_args(["zppy", "-c", "x.cfg"]) == [
        "conda",
        "run",
        "--no-capture-output",
        "-n",
        "env-zppy",
        "zppy",
        "-c",
        "x.cfg",
    ]
    with pytest.raises(ValueError, match="no name"):
        Environment("livvkit", ENV_TYPE_UNIFIED, "", "source u.sh").run_args(["x"])


def test_environment_from_status_restores_a_resumed_run() -> None:
    machine = MACHINE_PROFILES["chrysalis"]
    dev = environments.environment_from_status(
        "zppy",
        {"environment": "test-zppy-main-t", "environment_type": ENV_TYPE_DEV},
        machine,
        "/conda.sh",
    )
    assert dev.name == "test-zppy-main-t"
    assert dev.activation_command == "source /conda.sh; conda activate test-zppy-main-t"

    unified = environments.environment_from_status(
        "e3sm_diags", {"environment_type": ENV_TYPE_UNIFIED}, machine, "/conda.sh"
    )
    assert unified.activation_command == machine.unified_env_cmd


def test_activation_sources_the_profile_first() -> None:
    # Task scripts are not login shells, so `conda activate` alone would fail.
    command = environments.activation_command("/home/me/conda.sh", "my-env")
    assert command.index("source /home/me/conda.sh") < command.index("conda activate")


def test_export_writes_a_reconstructible_file(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(provenance, "run_command", lambda *a, **k: EXPORTED)
    environment = Environment("e3sm_diags", ENV_TYPE_DEV, "my-env", "activate")

    written = provenance.export_environment_file(
        environment, str(tmp_path / "environments" / "e3sm_diags.yml")
    )

    # `conda list` output cannot rebuild an environment; this can.
    assert "dependencies:" in open(written).read()


def test_export_skips_unified(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(provenance, "run_command", lambda *a, **k: EXPORTED)
    environment = Environment("livvkit", ENV_TYPE_UNIFIED, "", "source unified.sh")

    # E3SM-Unified is versioned and loaded by its own script; a snapshot of it
    # is not something anything rebuilds from.
    assert (
        provenance.export_environment_file(environment, str(tmp_path / "x.yml")) == ""
    )


def test_export_failure_does_not_abort_the_run(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(provenance, "run_command", lambda *a, **k: "")
    environment = Environment("zppy", ENV_TYPE_DEV, "my-env", "activate")

    # Hours of compute have already been spent by this point.
    assert (
        provenance.export_environment_file(environment, str(tmp_path / "x.yml")) == ""
    )
    assert not os.path.exists(tmp_path / "x.yml")


def test_env_types_are_the_three_documented_modes() -> None:
    assert set(environments.ENV_TYPES) == {
        ENV_TYPE_DEV,
        ENV_TYPE_UNIFIED,
        ENV_TYPE_BASELINE,
    }
