"""Tests for generating test cfgs from explicit settings.

The complete run passes its settings through these, rather than rewriting
TEST_SPECIFICS in tests/integration/utils.py by regex as the old driver did.
"""

import pytest

from tests.integration.utils import TEST_SPECIFICS, build_specifics


def test_defaults_are_preserved_when_nothing_is_passed() -> None:
    assert build_specifics() == TEST_SPECIFICS


def test_one_field_can_be_overridden_alone() -> None:
    specifics = build_specifics(unique_id="my_run")
    assert specifics["unique_id"] == "my_run"
    assert specifics["cfgs_to_run"] == TEST_SPECIFICS["cfgs_to_run"]


def test_building_specifics_does_not_mutate_the_module_default() -> None:
    before = dict(TEST_SPECIFICS)
    build_specifics(unique_id="other", cfgs_to_run=["weekly_bundles"])
    assert TEST_SPECIFICS == before


def test_env_commands_map_onto_their_cfg_keys() -> None:
    specifics = build_specifics(
        env_commands={
            "e3sm_diags": "source conda.sh; conda activate diags_env",
            "global_time_series": "source conda.sh; conda activate zi_env",
        }
    )
    # e3sm_diags writes to `diags_environment_commands`, not `e3sm_diags_...`.
    assert specifics["diags_environment_commands"].endswith("diags_env")
    assert specifics["global_time_series_environment_commands"].endswith("zi_env")


def test_unknown_task_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown task"):
        build_specifics(env_commands={"not_a_task": "source conda.sh"})


def test_empty_environment_commands_are_rejected() -> None:
    # An empty string prints `environment_commands = ""` into the cfg, which
    # overrides the value set higher up and leaves the task with no environment.
    with pytest.raises(ValueError, match="may not be empty"):
        build_specifics(env_commands={"e3sm_diags": ""})


def test_cfgs_and_tasks_are_copied_not_aliased() -> None:
    cfgs = ["weekly_bundles"]
    specifics = build_specifics(cfgs_to_run=cfgs)
    cfgs.append("weekly_comprehensive_v3")
    assert specifics["cfgs_to_run"] == ["weekly_bundles"]


def test_default_environment_commands_can_be_set() -> None:
    specifics = build_specifics(environment_commands="source unified.sh")
    assert specifics["environment_commands"] == "source unified.sh"


def test_cli_parses_repeated_options() -> None:
    from tests.integration.utils import _build_parser

    args = _build_parser().parse_args(
        [
            "--unique-id",
            "run1",
            "--cfg",
            "weekly_bundles",
            "--cfg",
            "weekly_comprehensive_v3",
            "--task",
            "e3sm_diags",
            "--env-cmd",
            "e3sm_diags=source conda.sh; conda activate x",
        ]
    )
    assert args.unique_id == "run1"
    assert args.cfgs == ["weekly_bundles", "weekly_comprehensive_v3"]
    assert args.tasks == ["e3sm_diags"]
    assert args.env_cmds == [("e3sm_diags", "source conda.sh; conda activate x")]


def test_cli_rejects_a_malformed_env_cmd() -> None:
    from tests.integration.utils import _build_parser

    with pytest.raises(SystemExit):
        _build_parser().parse_args(["--env-cmd", "no_equals_sign"])


def test_saved_run_settings_fill_only_what_was_not_passed(tmp_path) -> None:
    # The integration tests call get_expansions() with no arguments; in a
    # complete run they must check that run, not TEST_SPECIFICS' defaults.
    from tests.integration import utils

    path = str(tmp_path / "complete_run_settings.json")
    utils._save_run_settings(
        path,
        {
            "specifics": build_specifics(unique_id="run"),
            "run_dir": "/shared/runs/tag",
            "baseline_dir": "",
            "output_dir": "/scratch/tag/output",
        },
    )
    saved = utils._load_run_settings(path)

    specifics, run_dir, baseline_dir, output_dir = utils._resolve_settings(
        None, None, None, None, saved
    )
    assert specifics["unique_id"] == "run"
    assert run_dir == "/shared/runs/tag"
    # "" means "no baseline", and must not turn back into "resolve latest-main".
    assert baseline_dir == ""
    assert output_dir == "/scratch/tag/output"

    _, run_dir, _, _ = utils._resolve_settings(None, "/explicit", None, None, saved)
    assert run_dir == "/explicit"


def test_without_saved_settings_the_defaults_apply(tmp_path) -> None:
    from tests.integration import utils

    saved = utils._load_run_settings(str(tmp_path / "absent.json"))
    assert saved == {}
    specifics, run_dir, _, _ = utils._resolve_settings(None, None, None, None, saved)
    assert specifics is TEST_SPECIFICS
    assert run_dir is None
