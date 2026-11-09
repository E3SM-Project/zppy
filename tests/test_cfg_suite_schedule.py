"""Static checks on the scheduled controller and its crontab template.

These assets run unattended on a login node, where a mistake is discovered a
week later by a run that never happened.
"""

import os

CFG_SUITE_DIR: str = os.path.join(os.path.dirname(__file__), "cfg_suite")


def _read(name: str) -> str:
    with open(os.path.join(CFG_SUITE_DIR, name)) as stream:
        return stream.read()


def test_controller_requires_its_configuration() -> None:
    controller = _read("cfg-suite-controller.sh")
    for variable in (
        "REPO_ROOT",
        "CFG_SUITE_CONFIG",
        "CONDA_BASE",
        "CONTROLLER_ENV",
    ):
        # `: "${VAR:?}"` fails loudly rather than running with an empty value.
        assert f': "${{{variable}:?}}"' in controller


def test_controller_serializes_runs() -> None:
    controller = _read("cfg-suite-controller.sh")
    # Two overlapping runs would see each other's jobs in the queue.
    assert "flock -n 9" in controller
    # Per operator, not in the group-owned shared root: the queue being
    # drained is the operator's own.
    assert 'LOCK_FILE="${LOCK_FILE:-$HOME/.zppy_cfg_suite.lock}"' in controller
    assert 'exec 9>"$LOCK_FILE"' in controller


def test_controller_initializes_conda_explicitly() -> None:
    controller = _read("cfg-suite-controller.sh")
    # cron does not run a login shell.
    assert 'source "$CONDA_BASE/etc/profile.d/conda.sh"' in controller
    assert 'conda activate "$CONTROLLER_ENV"' in controller


def test_controller_clears_inherited_slurm_settings() -> None:
    controller = _read("cfg-suite-controller.sh")
    assert "unset SLURM_MEM_PER_CPU SLURM_OPEN_MODE" in controller
    assert 'for variable in "${!SLURM_@}"' in controller


def test_controller_can_gate_a_weekly_schedule_to_biweekly() -> None:
    controller = _read("cfg-suite-controller.sh")
    # Standard cron cannot express "every second Monday" across month ends.
    assert "date +%V" in controller
    assert "10#$(date +%V)" in controller
    assert "WEEK_PARITY" in controller


def test_controller_invokes_the_automation_cli() -> None:
    controller = _read("cfg-suite-controller.sh")
    assert "python -m tests.cfg_suite.automation" in controller
    assert "--config" in controller
    assert "--results-root" not in controller


def test_controller_flags_are_accepted_by_the_cli() -> None:
    # A flag the parser does not define fails every scheduled run.
    import re

    from tests.cfg_suite.automation import _build_parser

    controller = _read("cfg-suite-controller.sh")
    defined = {
        option
        for action in _build_parser()._actions
        for option in action.option_strings
    }
    for flag in set(re.findall(r"(--[a-z][a-z-]+)", controller)):
        assert flag in defined, f"controller passes {flag}, which the CLI rejects"


def test_controller_retains_artifacts_on_failure() -> None:
    controller = _read("cfg-suite-controller.sh")
    assert "retained" in controller
    assert 'exit "$AUTOMATION_EXIT"' in controller


def test_crontab_template_invokes_the_controller() -> None:
    template = _read("cfg-suite.crontab.template")
    assert "cfg-suite-controller.sh" in template
    assert "{{REPO_ROOT}}" in template
    assert "{{CONFIG_FILE}}" in template
    assert "{{LOG_DIR}}" in template


def test_crontab_template_warns_that_crontabs_are_per_login_node() -> None:
    template = _read("cfg-suite.crontab.template")
    # An entry on chrlogin1 does not exist on chrlogin2; this has bitten people.
    assert "PER NODE" in template
    assert "scrontab" in template


def test_config_template_documents_every_required_variable() -> None:
    controller = _read("cfg-suite-controller.sh")
    config = _read("cfg-suite.config.env.template")
    required = [
        line.split("{")[1].split(":?")[0]
        for line in controller.splitlines()
        if line.startswith(': "${')
    ]
    for variable in required:
        assert f"{variable}=" in config, f"{variable} is required but undocumented"


def test_controller_is_executable() -> None:
    assert os.access(os.path.join(CFG_SUITE_DIR, "cfg-suite-controller.sh"), os.X_OK)
