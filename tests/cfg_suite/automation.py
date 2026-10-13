"""Orchestrate zppy's cfg suite test.

One command builds immutable checkouts and environments for zppy and the four
packages whose tasks it launches, generates the weekly cfgs, submits them,
validates the results, and renders a report.

Usage
-----
On Chrysalis::

    python -m tests.cfg_suite.automation --machine chrysalis --account e3sm

Every stage writes ``status.json`` under the run directory, so an interrupted
run can be resumed with ``--start-stage`` and a crashed one still produces a
report.
"""

from __future__ import annotations

import argparse
import configparser
import glob
import json
import logging
import os
import re
import shlex
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime
from typing import Callable, Dict, List, Sequence, Set, Tuple

from tests.cfg_suite import changes as changes_module
from tests.cfg_suite import environments as environments_module
from tests.cfg_suite import envdiff, provenance
from tests.cfg_suite import report as report_module
from tests.cfg_suite import validate
from tests.cfg_suite.commands import CommandError, run_command, run_command_status
from tests.cfg_suite.environments import (
    ENV_TYPE_BASELINE,
    ENV_TYPE_DEV,
    ENV_TYPE_UNIFIED,
    ENV_TYPES,
    SOLVERS,
    Environment,
    create_environment,
    environment_from_status,
    environments_by_task,
    resolve_solver,
    unified_environment,
)
from tests.cfg_suite.layout import (
    RUN_SEGMENT,
    RunLayout,
    baseline_run_for,
    parse_baseline_selections,
    read_json_object,
    run_layout,
    shared_root,
    write_json,
)
from tests.cfg_suite.params import (
    DEFAULT_CFGS_TO_RUN,
    DEFAULT_TASKS_TO_RUN,
    IMAGE_HELPER_TEST_FILES,
    REPO_SPECS,
    REPO_SPECS_BY_NAME,
    SUITE_ROOT_DIRNAME,
    ZPPY_INTERFACES_UNIT_TESTS,
    ZPPY_TASK_UNIT_TESTS,
    ZPPY_UNIT_TESTS,
    integration_test_files_for_tasks,
    MachineProfile,
    RepoSpec,
    generated_cfg_path,
    is_bundles_cfg,
    repo_for_task,
    resolve_machine,
)
from tests.cfg_suite.slurm import queued_job_ids, wait_for_user_jobs
from tests.integration.weekly_cfgs import (
    PLOTTING_TASKS,
    TASK_NAMES,
    expand_task_selection,
    task_for_status_file,
    task_sections_for_cfg,
)
from tests.cfg_suite.worktrees import Checkout, create_checkout, remove_checkouts

logger: logging.Logger = logging.getLogger(__name__)

STAGES: Tuple[str, ...] = (
    "prepare",
    "generate",
    "submit",
    "bundles",
    "validate",
    "report",
)

# Terminal stages that are not a pass. Each leaves worktrees and results in
# place so a maintainer can see what happened.
FAILURE_STAGES: Tuple[str, ...] = (
    "prepare_failed",
    "submission_failed",
    "dependency_never_satisfied",
    "timed_out",
    "validation_failed",
)

# The terminal stage an unexpected command or filesystem error maps to, by the
# stage it happened in.
_FAILURE_FOR_STAGE: Dict[str, str] = {
    "prepare": "prepare_failed",
    "generate": "submission_failed",
    "submit": "submission_failed",
    "bundles": "submission_failed",
    "validate": "validation_failed",
}

class StageError(RuntimeError):
    """A stage failed in a way that ends the run."""

    def __init__(self, stage: str, message: str) -> None:
        self.stage: str = stage
        super().__init__(message)


@dataclass
class _Run:
    """Everything the stages of one run share."""

    args: argparse.Namespace
    machine: MachineProfile
    root: str
    layout: RunLayout
    # Per-run scratch directory for intermediate data: worktrees and zppy's
    # post-processing output. Nothing in it is needed once the run is done.
    scratch_dir: str
    tag: str
    username: str
    cfgs: List[str]
    selected_tasks: List[str]
    tasks: List[str]
    status: Dict[str, object]
    checkouts: List[Checkout] = field(default_factory=list)
    environments: Dict[str, Environment] = field(default_factory=dict)

    @property
    def worktree_root(self) -> str:
        return os.path.join(self.scratch_dir, "worktrees")

    @property
    def zppy_worktree(self) -> str:
        """Return the zppy worktree, from this run or a resumed one."""
        entry = _mapping(self.status.get("repos")).get("zppy")
        if isinstance(entry, dict) and entry.get("worktree"):
            return str(entry["worktree"])

        candidate: str = os.path.join(self.worktree_root, "zppy")
        if os.path.isdir(candidate):
            return candidate

        raise StageError(
            "prepare_failed",
            f"No zppy worktree found at {candidate}. Run the prepare stage first, "
            "or pass --start-stage prepare.",
        )

    def environment(self, repo_name: str) -> Environment:
        """Return a repository's dev environment, which a stage needs to run in."""
        environment = self.environments.get(repo_name)
        if environment is None or (
            not environment.name and environment.env_type != ENV_TYPE_UNIFIED
        ):
            raise StageError(
                "prepare_failed",
                f"No {repo_name} environment is recorded for this run. Run the "
                "prepare stage first, or pass --start-stage prepare.",
            )
        return environment

    def write_status(self) -> None:
        write_json(self.layout.status, self.status)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the cfg suite test and return a process exit code."""
    raw_args: Sequence[str] = argv if argv is not None else sys.argv[1:]
    config_parser = argparse.ArgumentParser(add_help=False)
    config_parser.add_argument("--config", default="")
    config_args, _ = config_parser.parse_known_args(raw_args)
    try:
        config_values = _read_config(config_args.config)
    except ValueError as error:
        _build_parser().error(str(error))
    parser = _build_parser(config_values)
    args: argparse.Namespace = parser.parse_args(raw_args)
    if not args.machine:
        parser.error("--machine is required, either directly or in --config")
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
    )
    try:
        run = _start_run(args)
    except ValueError as error:
        parser.error(str(error))
    logger.info(
        "Effective cfg-suite configuration:\n%s",
        json.dumps(run.status["configuration"], indent=2, sort_keys=True),
    )
    return run_cfg_suite(run)


def _start_run(args: argparse.Namespace) -> _Run:
    """Resolve the run's settings, carrying forward a resumed run's selections.

    Raises
    ------
    ValueError
        For an unknown machine, a machine with no shared root, or a stage range
        that runs backwards.
    """
    load_script_was_requested: bool = bool(args.unified_load_script)
    machine: MachineProfile = resolve_machine(args.machine)
    if args.unified_load_script:
        load_script: str = os.path.abspath(
            os.path.expanduser(args.unified_load_script)
        )
        if not os.path.isfile(load_script):
            raise ValueError(
                f"Unified load script does not exist: {args.unified_load_script}"
            )
        args.unified_load_script = load_script
        machine = replace(
            machine, unified_env_cmd=f"source {shlex.quote(load_script)}"
        )
    else:
        args.unified_load_script = _unified_load_script(machine)
    for attribute in ("repo_root", "shared_root", "scratch_root", "conda_profile"):
        value: str = str(getattr(args, attribute, "") or "")
        if value:
            setattr(args, attribute, os.path.expanduser(value))
    args.repo_paths = {
        name: os.path.expanduser(path) for name, path in args.repo_paths.items()
    }
    _stages_to_run(args.start_stage, args.stop_after)
    tag: str = args.tag or _default_tag(args.label)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", tag):
        raise ValueError(f"Invalid run tag {tag!r}")
    root: str = shared_root(machine.cfg_suffix, args.shared_root)
    username: str = args.username or os.environ.get("USER", "")
    scratch_dir: str = os.path.join(
        args.scratch_root
        or os.path.join(machine.scratch_workspace(username), SUITE_ROOT_DIRNAME),
        tag,
    )
    # zppy's post-processing output is intermediate data: only the plots, and
    # what validation copies out, belong in the shared run directory.
    layout: RunLayout = run_layout(root, tag, os.path.join(scratch_dir, "output"))
    if args.tag:
        if not os.path.isdir(layout.root) or not os.path.isfile(layout.status):
            raise ValueError(
                f"--tag {tag!r} is only for resuming an existing run with status.json"
            )
    elif os.path.exists(layout.root):
        raise ValueError(
            f"Run {tag!r} already exists; use --tag {tag} to resume it."
        )
    else:
        os.makedirs(os.path.dirname(layout.root), exist_ok=True)
        try:
            os.mkdir(layout.root)
        except FileExistsError as error:
            raise ValueError(
                f"Run {tag!r} already exists; use --tag {tag} to resume it."
            ) from error

    status: Dict[str, object] = read_json_object(layout.status)
    manifest: Dict[str, object] = read_json_object(layout.manifest)
    created_at: str = str(
        status.get("created_at")
        or manifest.get("created_at")
        or manifest.get("generated")
        or datetime.now().astimezone().isoformat()
    )
    recorded_load_script: str = str(status.get("unified_load_script") or "")
    default_load_script: str = _unified_load_script(machine)
    if (
        not load_script_was_requested
        and recorded_load_script
        and recorded_load_script != default_load_script
    ):
        if not os.path.isfile(recorded_load_script):
            raise ValueError(
                f"Recorded Unified load script does not exist: {recorded_load_script}"
            )
        args.unified_load_script = recorded_load_script
        machine = replace(
            machine, unified_env_cmd=f"source {shlex.quote(recorded_load_script)}"
        )
    selected_tasks: List[str] = list(
        args.tasks
        or _string_list(status.get("selected_tasks"))
        or _string_list(status.get("tasks"))
        or DEFAULT_TASKS_TO_RUN
    )
    baseline_overrides: Dict[str, str] = (
        parse_baseline_selections(args.baseline)
        if args.baseline
        else {
            str(key): str(tag)
            for key, tag in _mapping(status.get("baseline_overrides")).items()
            if isinstance(tag, str)
        }
    )
    args.baseline_overrides = baseline_overrides
    tasks, _ = expand_task_selection(selected_tasks)
    run = _Run(
        args=args,
        machine=machine,
        root=root,
        layout=layout,
        scratch_dir=scratch_dir,
        tag=tag,
        username=username,
        # A resumed run keeps the selections it started with unless overridden.
        cfgs=list(args.cfgs or _string_list(status.get("cfgs")) or DEFAULT_CFGS_TO_RUN),
        selected_tasks=selected_tasks,
        tasks=tasks,
        status=status,
    )
    status.update(
        {
            "tag": tag,
            "created_at": created_at,
            "machine": machine.name,
            "cfgs": run.cfgs,
            "selected_tasks": run.selected_tasks,
            "tasks": run.tasks,
            "run_dir": layout.root,
            "shared_root": root,
            "scratch_dir": scratch_dir,
            "output_dir": layout.output,
            "worktree_root": run.worktree_root,
            "configuration": _effective_configuration(args, run.cfgs, run.tasks),
            "pin_dependencies": list(args.pin_dependencies),
            "unified_load_script": args.unified_load_script,
            "baseline_overrides": baseline_overrides,
        }
    )
    status.setdefault("repos", {})
    return run


def run_cfg_suite(run: _Run) -> int:
    """Drive every requested stage, always leaving a status file behind."""
    status = run.status
    stages: List[str] = _stages_to_run(run.args.start_stage, run.args.stop_after)
    if "prepare" not in stages:
        run.environments = _environments_from_status(run)

    current: str = stages[0]
    try:
        for current in stages:
            if current == "report":
                continue  # Always rendered below, whatever happened.
            logger.info("=== Stage: %s ===", current)
            status["stage"] = current
            _STAGE_FUNCTIONS[current](run)
            run.write_status()
    except StageError as error:
        logger.error("%s", error)
        status["stage"] = error.stage
        status["error"] = str(error)
    except (CommandError, OSError) as error:
        logger.error("Stage %s failed: %s", current, error)
        status["stage"] = _FAILURE_FOR_STAGE.get(current, "validation_failed")
        status["error"] = str(error)

    # Always render a report, even from a partial run: an unexplained failure is
    # the case where a maintainer most needs one.
    try:
        _stage_report(run, stages)
    except OSError as error:
        logger.warning("Could not render the report: %s", error)
    run.write_status()

    failed: bool = str(status.get("stage")) in FAILURE_STAGES
    # Only a finished, passing run gives up its worktrees. One stopped early
    # with --stop-after needs them to resume.
    if (
        run.checkouts
        and status.get("stage") == "passed"
        and not run.args.keep_worktrees
    ):
        remove_checkouts(run.checkouts)
    elif run.checkouts:
        logger.info(
            "Leaving %s worktrees in place under %s",
            len(run.checkouts),
            run.worktree_root,
        )

    return 1 if failed else 0


def _stage_prepare(run: _Run) -> None:
    """Create worktrees and environments, then run the gating unit tests."""
    selected_repos: Set[str] = _repos_for_tasks(run.tasks)
    env_types: Dict[str, str] = {
        name: value
        for name, value in run.args.env_types.items()
        if name in selected_repos
    }

    baseline: RunLayout | None = _record_baseline(run)
    if env_types.get("zppy") == ENV_TYPE_UNIFIED:
        run.environments["zppy"] = unified_environment("zppy", run.machine)
        _record_unified_zppy(run)
        unified_packages: str = provenance.conda_package_list(run.environment("zppy"))
        run.status["unified"] = provenance.describe_unified(
            unified_packages, run.args.unified_load_script
        )

    repos: Dict[str, object] = {}
    to_build: List[Tuple[RepoSpec, Checkout, str]] = []
    for spec in REPO_SPECS:
        if spec.name not in selected_repos:
            continue
        env_type: str = env_types.get(spec.name, ENV_TYPE_DEV)
        if env_type == ENV_TYPE_UNIFIED:
            run.environments[spec.name] = unified_environment(spec.name, run.machine)
            if spec.name == "zppy":
                checkout = create_checkout(
                    spec.name,
                    _repo_path(run.args, spec),
                    run.args.branches.get(spec.name, spec.default_branch),
                    run.worktree_root,
                )
                run.checkouts.append(checkout)
                repos[spec.name] = {
                    "sha": checkout.sha,
                    "branch": checkout.branch,
                    "worktree": checkout.path,
                    "environment_type": ENV_TYPE_UNIFIED,
                }
            else:
                # Released packages do not need a source checkout.
                repos[spec.name] = {"environment_type": ENV_TYPE_UNIFIED}
            continue

        checkout: Checkout = create_checkout(
            spec.name,
            _repo_path(run.args, spec),
            run.args.branches.get(spec.name, spec.default_branch),
            run.worktree_root,
        )
        run.checkouts.append(checkout)
        environment_file: str = ""
        if env_type == ENV_TYPE_BASELINE:
            repo_baseline = _baseline_for_repo(run, spec, baseline)
            if repo_baseline is None:
                raise StageError(
                    "prepare_failed",
                    "No baseline is available to rebuild environments from. Promote "
                    "a run with `python -m tests.cfg_suite.promote`, or use "
                    "--env-type dev.",
                )
            environment_file = repo_baseline.environment_file(spec.name)
        to_build.append((spec, checkout, environment_file))

    for (spec, checkout, environment_file), environment in zip(
        to_build, _build_environments(run, to_build)
    ):
        run.environments[spec.name] = environment
        repos[spec.name] = {
            "sha": checkout.sha,
            "branch": checkout.branch,
            "worktree": checkout.path,
            "environment": environment.name,
            "environment_type": environment.env_type,
            "environment_source": environment_file or spec.env_file(),
            "solver": resolve_solver(run.args.solver),
        }
    run.status["repos"] = repos

    _apply_dependency_pins(run, repos)
    _run_unit_tests(run)
    for name, environment in sorted(run.environments.items()):
        provenance.export_environment_file(
            environment, run.layout.environment_file(name)
        )
    _write_env_descriptions(run)
    _write_manifest(run)


def _build_environments(
    run: _Run, to_build: List[Tuple[RepoSpec, Checkout, str]]
) -> List[Environment]:
    """Create each repository's environment, optionally several at once.

    Solving environments dominates the prepare stage. They are independent, so
    ``--parallel-envs`` can overlap them; it defaults to one at a time because
    concurrent solves on a shared login node are not always welcome.
    """

    solver: str = resolve_solver(run.args.solver)

    def build(item: Tuple[RepoSpec, Checkout, str]) -> Environment:
        spec, checkout, environment_file = item
        return create_environment(
            spec,
            checkout,
            run.tag,
            run.args.conda_profile,
            existing_env=run.args.existing_envs.get(spec.name, ""),
            allow_existing=run.args.allow_existing_envs,
            environment_file=environment_file,
            solver=solver,
        )

    workers: int = max(1, run.args.parallel_envs)
    if workers == 1:
        return [build(item) for item in to_build]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(build, to_build))


def _apply_dependency_pins(run: _Run, repos: Dict[str, object]) -> None:
    """Apply requested pins before capturing environment provenance."""
    applied: Dict[str, List[str]] = {}
    run.status["applied_pins"] = applied
    for repo_name, environment in sorted(run.environments.items()):
        applicable: List[str] = []
        for configured in run.args.pin_dependencies:
            prefix, separator, spec = configured.partition(":")
            if separator and prefix in REPO_SPECS_BY_NAME:
                if prefix == repo_name and spec:
                    applicable.append(spec)
            elif configured:
                applicable.append(configured)

        if environment.env_type == ENV_TYPE_UNIFIED:
            if applicable:
                logger.warning(
                    "Ignoring dependency pins for %s: E3SM-Unified is immutable",
                    repo_name,
                )
            continue
        if not applicable:
            continue
        try:
            environments_module.apply_dependency_pins(environment, applicable)
        except CommandError as error:
            raise StageError(
                "prepare_failed",
                f"Could not apply dependency pins to {repo_name}: {error}",
            ) from error
        environment = replace(environment, pinned=tuple(applicable))
        run.environments[repo_name] = environment
        applied[repo_name] = applicable
        repo_entry = repos.get(repo_name)
        if isinstance(repo_entry, dict):
            repo_entry["pinned"] = applicable


def _record_unified_zppy(run: _Run) -> None:
    """Check and record the zppy installation available in E3SM-Unified."""
    command = [
        "env",
        "-u",
        "PYTHONPATH",
        "python",
        "-c",
        (
            "import json, pathlib, shutil, sys, pytest, zppy; "
            "print(json.dumps({'executable': shutil.which('zppy') or "
            "(sys.executable + ' -m zppy'), "
            "'version': zppy.__version__, 'path': str(pathlib.Path(zppy.__file__).resolve()), "
            "'python': sys.executable}))"
        ),
    ]
    returncode, output = run_command_status(
        run.environment("zppy").run_args(command), cwd="/"
    )
    if returncode:
        raise StageError(
            "prepare_failed",
            "E3SM-Unified must provide importable pytest and zppy to test zppy "
            f"without installing it there:\n{output[-2000:]}",
        )
    try:
        runtime_line: str = next(
            (line for line in reversed(output.splitlines()) if line.strip()), ""
        )
        runtime: Dict[str, str] = json.loads(runtime_line)
    except json.JSONDecodeError as error:
        raise StageError(
            "prepare_failed", f"Could not identify zppy in E3SM-Unified: {output}"
        ) from error
    run.status["zppy_runtime"] = runtime
    logger.info(
        "Unified zppy: executable=%s version=%s package=%s",
        runtime.get("executable", ""),
        runtime.get("version", ""),
        runtime.get("path", ""),
    )


def _record_baseline(run: _Run) -> RunLayout | None:
    """Record the channel default and the resolved run for every cfg/task."""
    try:
        default = baseline_run_for(run.root, "", "")
    except FileNotFoundError as error:
        logger.info("No default baseline to compare against: %s", error)
        default = None

    baseline_by_cfg_task: Dict[str, Dict[str, object]] = {}
    for cfg, tasks in _tasks_by_cfg(run).items():
        for task in tasks & set(TASK_NAMES):
            try:
                selected = baseline_run_for(
                    run.root,
                    cfg,
                    task,
                    requested=run.args.baseline_overrides,
                )
            except FileNotFoundError as error:
                requested = run.args.baseline_overrides
                if f"{cfg}:{task}" in requested or task in requested:
                    raise StageError(
                        "prepare_failed",
                        f"Could not resolve the requested baseline for "
                        f"{cfg}/{task}: {error}",
                    ) from error
                logger.info("No baseline for %s/%s: %s", cfg, task, error)
                baseline_by_cfg_task[f"{cfg}:{task}"] = {
                    "state": "not-compared",
                    "reason": "new cfg",
                    "tag": "",
                    "run_dir": "",
                    "generated": "",
                    "repos": {},
                }
                continue
            manifest = read_json_object(selected.manifest)
            if cfg not in _string_list(manifest.get("cfgs")):
                logger.info("No baseline for new cfg %s in %s", cfg, selected.root)
                baseline_by_cfg_task[f"{cfg}:{task}"] = {
                    "state": "not-compared",
                    "reason": "new cfg",
                    "tag": "",
                    "run_dir": "",
                    "generated": "",
                    "repos": {},
                }
                continue
            baseline_by_cfg_task[f"{cfg}:{task}"] = {
                "tag": str(manifest.get("tag") or os.path.basename(selected.root)),
                "run_dir": selected.root,
                "generated": manifest.get("generated", ""),
                "repos": manifest.get("repos", {}),
            }

    run.status["baseline_by_cfg_task"] = baseline_by_cfg_task
    if default is None:
        run.status["baseline"] = {}
        return None

    manifest = read_json_object(default.manifest)
    baseline_info = {
        "tag": str(manifest.get("tag") or os.path.basename(default.root)),
        "run_dir": default.root,
        "generated": manifest.get("generated", ""),
        "repos": manifest.get("repos", {}),
    }
    run.status["baseline"] = baseline_info
    return default


def _baseline_for_repo(
    run: _Run, spec: RepoSpec, default: RunLayout | None
) -> RunLayout | None:
    """Resolve one baseline environment source for all selected repo tasks."""
    matching: Set[str] = set()
    missing: List[str] = []
    for cfg, tasks in _tasks_by_cfg(run).items():
        for task in tasks & set(spec.tasks) & set(run.tasks):
            entry = _mapping(
                _mapping(run.status.get("baseline_by_cfg_task")).get(f"{cfg}:{task}")
            )
            selected = str(entry.get("run_dir") or "")
            if selected:
                matching.add(selected)
            elif default is None:
                missing.append(f"{cfg}/{task}")
    if missing:
        raise StageError(
            "prepare_failed",
            f"No baseline run resolves for {spec.name} task(s): "
            f"{', '.join(sorted(missing))}.",
        )
    if len(matching) > 1:
        raise StageError(
            "prepare_failed",
            f"Repository {spec.name} has selected tasks resolving to different "
            f"baseline runs: {', '.join(sorted(matching))}. Use one baseline for "
            "all tasks sharing this environment.",
        )
    if matching:
        return RunLayout(next(iter(matching)))
    return default


def _run_unit_tests(run: _Run) -> None:
    """Run the unit tests that gate a cfg suite, each in its own environment.

    A failure here means the run would be testing known-broken code, so it stops
    the run rather than being recorded and carried forward.
    """
    if run.args.skip_unit_tests:
        logger.warning("Skipping unit tests at the caller's request")
        return

    by_name: Dict[str, Checkout] = {checkout.name: checkout for checkout in run.checkouts}
    targets_by_repo: Dict[str, Set[str]] = {"zppy": set(ZPPY_UNIT_TESTS)}
    for task in run.tasks:
        targets_by_repo["zppy"].update(ZPPY_TASK_UNIT_TESTS.get(task, ()))
        spec = repo_for_task(task)
        if spec is not None:
            targets_by_repo.setdefault(spec.name, set()).update(
                ZPPY_INTERFACES_UNIT_TESTS.get(task, ())
            )
    if set(run.tasks) & set(PLOTTING_TASKS):
        targets_by_repo["zppy"].update(IMAGE_HELPER_TEST_FILES)

    for repo_name, repo_targets in targets_by_repo.items():
        checkout = by_name.get(repo_name)
        if checkout is None:
            continue  # Running from E3SM-Unified; there is no worktree to test.
        # No shell runs these commands, so globs are expanded here.
        targets: List[str] = sorted(
            os.path.relpath(path, checkout.path)
            for target in repo_targets
            for path in glob.glob(os.path.join(checkout.path, target))
        )
        if not targets:
            logger.warning("%s: no selected unit tests were found; skipping", repo_name)
            continue

        logger.info("Running %s unit tests: %s", repo_name, ", ".join(targets))
        returncode, output = run_command_status(
            run.environment(repo_name).run_args(["python", "-m", "pytest", *targets]),
            cwd=checkout.path,
        )
        if returncode != 0:
            raise StageError(
                "prepare_failed",
                f"{repo_name} unit tests failed:\n{output[-2000:]}",
            )


def _write_env_descriptions(run: _Run) -> None:
    """Write one environment description per selected task."""
    by_name: Dict[str, Checkout] = {
        checkout.name: checkout for checkout in run.checkouts
    }
    # Several tasks can share one environment; list its packages once. Snapshot
    # every environment, including zppy's controller environment.
    package_lists: Dict[str, str] = {}
    snapshots: Dict[str, Dict[str, str]] = {}
    for name, environment in sorted(run.environments.items()):
        key: str = environment.name or environment.activation_command
        if key not in package_lists:
            package_lists[key] = provenance.conda_package_list(environment)
        snapshots[name] = envdiff.parse_package_list_details(package_lists[key])
    run.status["environment_snapshots_prepare"] = snapshots

    for task, environment in sorted(
        environments_by_task(run.environments, run.machine).items()
    ):
        if task not in run.tasks:
            continue
        key: str = environment.name or environment.activation_command
        if key not in package_lists:
            package_lists[key] = provenance.conda_package_list(environment)
            snapshots[task] = envdiff.parse_package_list_details(package_lists[key])
        if environment.env_type == ENV_TYPE_UNIFIED:
            run.status["unified"] = provenance.describe_unified(
                package_lists[key],
                run.args.unified_load_script or _unified_load_script(run.machine),
            )
        provenance.write_env_description(
            run.layout.env_descriptions,
            task,
            by_name.get(environment.repo_name),
            environment,
            package_list=package_lists[key],
            pinned=environment.pinned,
            unified_load_script=(
                run.args.unified_load_script or _unified_load_script(run.machine)
                if environment.env_type == ENV_TYPE_UNIFIED
                else ""
            ),
        )


def _write_manifest(run: _Run) -> None:
    """Record what this run is testing."""
    from zppy import __version__

    manifest = provenance.build_manifest(
        tag=run.tag,
        machine=run.machine.name,
        checkouts=run.checkouts,
        environments=run.environments,
        cfgs=run.cfgs,
        tasks=run.tasks,
        zppy_version=str(
            _mapping(run.status.get("zppy_runtime")).get("version") or __version__
        ),
        unified=_mapping(run.status.get("unified")) or None,
        pins={
            name: list(environment.pinned)
            for name, environment in run.environments.items()
            if environment.pinned
        },
        unified_load_script=run.args.unified_load_script,
        zppy_runtime=_mapping(run.status.get("zppy_runtime")),
        requested_pins=list(run.args.pin_dependencies),
        username=run.username,
        created_at=str(run.status.get("created_at") or ""),
    )
    provenance.write_manifest(run.layout.root, manifest)


def _unified_load_script(machine: MachineProfile) -> str:
    """Return the script the machine's Unified activation command sources."""
    command: str = machine.unified_env_cmd.strip()
    return shlex.split(command)[1] if command.startswith("source ") else ""


def _stage_generate(run: _Run) -> None:
    """Generate the machine-specific cfgs from their templates."""
    command: List[str] = [
        "python",
        "-m",
        "tests.integration.utils",
        # The run directory already carries the tag, so the cfgs use a fixed
        # segment rather than repeating it inside every path.
        "--unique-id",
        RUN_SEGMENT,
        "--run-dir",
        run.layout.root,
        "--output-dir",
        run.layout.output,
        "--environment-commands",
        run.machine.unified_env_cmd,
    ]
    for cfg in run.cfgs:
        command.extend(["--cfg", cfg])
    for task in run.selected_tasks:
        command.extend(["--task", task])
    for key, entry in _mapping(run.status.get("baseline_by_cfg_task")).items():
        if isinstance(entry, dict) and entry.get("tag"):
            command.extend(["--baseline", f"{key}={entry['tag']}"])
        elif isinstance(entry, dict) and entry.get("state") == "not-compared":
            command.extend(["--not-compared-baseline", key])
    for task, environment in sorted(
        environments_by_task(run.environments, run.machine).items()
    ):
        command.extend(["--env-cmd", f"{task}={environment.activation_command}"])
    if run.args.nco_path:
        command.extend(["--nco-path", run.args.nco_path])

    run_command(run.environment("zppy").run_args(command), cwd=run.zppy_worktree)
    logger.info("Generated %s cfgs for %s", len(run.cfgs), run.machine.cfg_suffix)


def _stage_submit(run: _Run) -> None:
    """Submit every cfg, then wait for the queue to drain."""
    _submit_cfgs(run, run.cfgs, run.args.max_wait_submit)


def _stage_bundles(run: _Run) -> None:
    """Resubmit the bundles cfgs, which need a second pass."""
    bundle_cfgs: List[str] = [cfg for cfg in run.cfgs if is_bundles_cfg(cfg)]
    if not bundle_cfgs:
        logger.info("No bundles cfgs selected; skipping the second bundles pass")
        return
    _submit_cfgs(run, bundle_cfgs, run.args.max_wait_bundles)


def _clear_stale_status_files(run: _Run, cfgs: Sequence[str]) -> int:
    """Drop status files that claim a job is queued when it no longer is.

    ``zppy`` skips a task whose status file begins with OK, WAITING or RUNNING.
    WAITING and RUNNING outlive the jobs they name whenever a run is cancelled
    or dies, so resuming into the same output directory would skip exactly the
    tasks that never ran, and validation would then sweep a tree whose every
    status file reads OK. Removing them lets zppy resubmit those tasks. OK and
    ERROR files are left alone: OK means the work is done, and zppy already
    resubmits ERROR.
    """
    try:
        live: Set[str] = queued_job_ids(run.username)
    except CommandError as error:
        # Without the queue there is no way to tell a stale file from a job
        # that is genuinely pending, and deleting a live one would submit the
        # task twice. Leaving them is what this harness did before.
        logger.warning(
            "Could not read the queue; leaving status files alone: %s", error
        )
        return 0
    cleared: int = 0
    tasks_by_cfg: Dict[str, Set[str]] = _tasks_by_cfg(run, cfgs)
    for cfg in cfgs:
        for status_file in sorted(
            glob.glob(os.path.join(run.layout.status_dir(cfg), "*status"))
        ):
            if task_for_status_file(status_file) not in tasks_by_cfg[cfg]:
                continue
            try:
                with open(status_file, encoding="utf-8") as stream:
                    fields: List[str] = stream.read().split()
            except OSError as error:
                logger.warning("Could not read %s: %s", status_file, error)
                continue
            if not fields or fields[0] not in ("WAITING", "RUNNING"):
                continue
            # "WAITING <jobid>". A job still in the queue is genuinely pending,
            # so only the ones SLURM has forgotten are stale.
            if len(fields) > 1 and fields[1] in live:
                continue
            try:
                os.remove(status_file)
            except OSError as error:
                logger.warning("Could not remove %s: %s", status_file, error)
                continue
            logger.info(
                "Cleared stale status file %s (%s)",
                os.path.basename(status_file),
                " ".join(fields),
            )
            cleared += 1
    if cleared:
        logger.info("Cleared %s stale status file(s) before submitting", cleared)
    return cleared


def _submit_cfgs(run: _Run, cfgs: Sequence[str], max_wait: int) -> None:
    """Submit cfgs with the zppy under test, then wait for the queue to drain."""
    _clear_stale_status_files(run, cfgs)
    worktree: str = run.zppy_worktree
    zppy_env: Environment = run.environment("zppy")
    for cfg in cfgs:
        cfg_path: str = generated_cfg_path(worktree, cfg, run.machine.cfg_suffix)
        if not os.path.isfile(cfg_path):
            raise StageError(
                "submission_failed",
                f"Generated cfg not found: {cfg_path}. Check that {cfg!r} names "
                "a template in tests/integration/.",
            )
        logger.info("Submitting %s", cfg_path)
        run_command(zppy_env.run_args(["zppy", "-c", cfg_path]), cwd=worktree)

    _wait(run, max_wait, cfgs)


def _wait(run: _Run, max_wait: int, cfgs: Sequence[str] | None = None) -> None:
    """Wait for the queue to drain, mapping the outcome onto a terminal stage."""
    job_ids: Set[str] = set()
    selected_cfgs: Sequence[str] = cfgs if cfgs is not None else run.cfgs
    tasks_by_cfg: Dict[str, Set[str]] = _tasks_by_cfg(run, selected_cfgs)
    for cfg in selected_cfgs:
        for status_file in glob.glob(
            os.path.join(run.layout.status_dir(cfg), "*status")
        ):
            if task_for_status_file(status_file) not in tasks_by_cfg[cfg]:
                continue
            try:
                with open(status_file, encoding="utf-8") as stream:
                    fields: List[str] = stream.read().split()
            except OSError as error:
                logger.warning("Could not read %s: %s", status_file, error)
                continue
            if len(fields) > 1 and fields[0] in ("WAITING", "RUNNING"):
                job_ids.add(fields[1])

    outcome: str = wait_for_user_jobs(
        run.username,
        job_ids=job_ids,
        check_interval=run.args.poll_seconds,
        max_wait=max_wait,
    )
    if outcome == "dependency_never_satisfied":
        raise StageError(
            "dependency_never_satisfied",
            "One or more jobs had an unsatisfiable dependency; blocked jobs were "
            "cancelled after this run's queue drained. Check the status files of "
            "the jobs that failed first.",
        )
    if outcome == "timed_out":
        raise StageError("timed_out", f"Jobs did not finish within {max_wait} seconds.")


def _stage_validate(run: _Run) -> None:
    """Sweep status files, run the integration tests, and check the images."""
    status = run.status
    layout = run.layout
    worktree: str = run.zppy_worktree
    zppy_env: Environment = run.environment("zppy")

    tasks_by_cfg: Dict[str, Set[str]] = _tasks_by_cfg(run)
    sweep = validate.sweep_status_files(layout, run.cfgs, tasks_by_cfg)
    task_status_by_cfg = validate.task_statuses_by_cfg(sweep, tasks_by_cfg)
    status["status_sweep"] = {
        "passed": sweep.passed,
        "failure_count": sweep.failure_count,
        "failures_by_cfg": sweep.failures_by_cfg,
        "missing_dirs": sweep.missing_dirs,
        "job_counts_by_cfg_task": sweep.job_counts_by_cfg_task,
        "failed_jobs_by_cfg_task": sweep.failed_jobs_by_cfg_task,
    }
    status["task_status_by_cfg"] = task_status_by_cfg

    status["www_root_by_cfg"] = provenance.distribute_env_descriptions(
        layout.env_descriptions,
        worktree,
        run.cfgs,
        run.tasks,
        run.machine.cfg_suffix,
    )

    plotting_selected: bool = bool(set(run.tasks) & set(PLOTTING_TASKS))
    integration_tests: Sequence[str] = integration_test_files_for_tasks(run.tasks)
    pytest_results = validate.run_pytest_files(
        worktree, zppy_env, test_files=integration_tests
    )
    status["pytest_results"] = [asdict(result) for result in pytest_results]

    if plotting_selected:
        image_result = validate.run_image_checker(
            worktree,
            layout.root,
            run.tag,
            run.machine,
            zppy_env.name,
            run.args.conda_profile,
            account=run.args.account,
            max_wait=run.args.max_wait_images,
            environment=zppy_env,
        )
    else:
        image_result = validate.ImageCheckResult(state="NOT_APPLICABLE")
        logger.info("Image check not applicable: no plotting tasks selected")
    status["image_check"] = asdict(image_result)

    # A run is only promotable if it describes itself: the images it produced,
    # and the small settings baselines the cheaper tests compare against.
    status["image_counts"] = (
        validate.write_image_lists(layout, run.cfgs) if plotting_selected else {}
    )
    validate.capture_settings_baselines(worktree, layout, run.cfgs, zppy_env)

    validate.collect_artifacts(worktree, layout.root)

    if not sweep.passed or not all(result.passed for result in pytest_results):
        raise StageError(
            "validation_failed",
            "Validation found failures; see the report for details.",
        )
    if plotting_selected and not image_result.passed:
        raise StageError(
            "validation_failed",
            f"The image checker did not pass (state {image_result.state}).",
        )


def _compare_environments(run: _Run) -> Tuple[List[envdiff.EnvironmentDiff], str]:
    """Compare this run's environments against the promoted baseline's."""
    diffs: List[envdiff.EnvironmentDiff] = []
    modes: Dict[str, str] = {}
    baselines: Dict[str, object] = _mapping(run.status.get("baseline_by_cfg_task"))
    for key, entry in baselines.items():
        cfg, separator, task = key.partition(":")
        if not separator or task not in run.tasks:
            continue
        spec = repo_for_task(task)
        if spec is None or spec.name not in run.environments:
            continue
        selected = _mapping(entry)
        baseline_dir = str(selected.get("run_dir") or "")
        if not baseline_dir:
            continue
        diffs.extend(
            envdiff.compare_run_environments(
                run.layout,
                RunLayout(baseline_dir),
                [spec.name],
                cfg=cfg,
                task=task,
            )
        )
        modes[spec.name] = str(run.args.env_types.get(spec.name, ENV_TYPE_DEV))
    if not diffs:
        return [], ""
    note: str = envdiff.interpretation(diffs, modes)
    logger.info("%s", note)
    return diffs, note


def _stage_report(run: _Run, stages_run: Sequence[str] = ()) -> None:
    """Render the run's JSON and Markdown reports.

    A run only reports "passed" once validation has actually run. Stopping early
    with ``--stop-after`` leaves the stage as it was, so a partial run is never
    mistaken for a clean one.
    """
    if run.environments:
        _refresh_environment_snapshots(run)

    repo_paths = {
        spec.name: _repo_path(run.args, spec)
        for spec in REPO_SPECS
        if spec.name in _mapping(run.status.get("repos"))
    }
    run.status["changes_since_baseline"] = changes_module.collect_changes(
        run.status,
        repo_paths,
        run.layout.env_descriptions,
    )

    if run.environments:
        diffs, note = _compare_environments(run)
        run.status["environment_diff"] = envdiff.summarize(diffs)
        run.status["environment_note"] = note
        if run.status.get("status_sweep"):
            _write_environment_viewers(run, diffs, note)

    if "validate" in stages_run and str(run.status.get("stage")) not in FAILURE_STAGES:
        run.status["stage"] = "passed"
    report = report_module.render_report(run.status, run.layout)
    json_path, markdown_path = report_module.write_report(report, run.layout.root)
    logger.info("Run reports: %s and %s", json_path, markdown_path)
    logger.info("Job scripts and logs: %s", run.layout.output)


def _refresh_environment_snapshots(run: _Run) -> None:
    """Capture the environments as used and update all recorded package lists."""
    package_lists: Dict[str, str] = {}
    final_snapshots: Dict[str, Dict[str, str]] = {}
    prepared: Dict[str, object] = _mapping(
        run.status.get("environment_snapshots_prepare")
    )
    drift: Dict[str, List[Dict[str, object]]] = {}

    for name, environment in sorted(run.environments.items()):
        key: str = environment.name or environment.activation_command
        if key not in package_lists:
            package_lists[key] = provenance.conda_package_list(environment)
        package_list: str = package_lists[key]
        if environment.env_type == ENV_TYPE_UNIFIED:
            run.status["unified"] = provenance.describe_unified(
                package_list,
                run.args.unified_load_script or _unified_load_script(run.machine),
            )
        final_snapshots[name] = envdiff.parse_package_list_details(package_list)
        try:
            provenance.export_environment_file(
                environment, run.layout.environment_file(name)
            )
        except OSError as error:
            logger.warning(
                "Could not refresh environment export for %s: %s", name, error
            )
        before: Dict[str, object] = _mapping(prepared.get(name))
        changes: List[envdiff.PackageChange] = (
            envdiff.diff_package_maps(before, final_snapshots[name])
            if before and final_snapshots[name]
            else []
        )
        if changes:
            drift[name] = [
                {
                    "name": change.name,
                    "prepared": change.baseline,
                    "final": change.candidate,
                }
                for change in changes
            ]
            logger.warning(
                "Environment changed during run for %s: %s",
                name,
                ", ".join(
                    f"{change.name} ({change.baseline or '—'} -> "
                    f"{change.candidate or '—'})"
                    for change in changes
                ),
            )

    for task, environment in environments_by_task(
        run.environments, run.machine
    ).items():
        if task not in run.tasks:
            continue
        key: str = environment.name or environment.activation_command
        if key not in package_lists:
            package_lists[key] = provenance.conda_package_list(environment)
        package_list: str = package_lists[key]
        if environment.env_type == ENV_TYPE_UNIFIED:
            run.status["unified"] = provenance.describe_unified(
                package_list,
                run.args.unified_load_script or _unified_load_script(run.machine),
            )
        if environment.repo_name not in final_snapshots:
            final_snapshots[task] = envdiff.parse_package_list_details(package_list)
            before: Dict[str, object] = _mapping(prepared.get(task))
            changes: List[envdiff.PackageChange] = (
                envdiff.diff_package_maps(before, final_snapshots[task])
                if before and final_snapshots[task]
                else []
            )
            if changes:
                drift[task] = [
                    {
                        "name": change.name,
                        "prepared": change.baseline,
                        "final": change.candidate,
                    }
                    for change in changes
                ]
                logger.warning(
                    "Environment changed during run for %s: %s",
                    task,
                    ", ".join(
                        f"{change.name} ({change.baseline or '—'} -> "
                        f"{change.candidate or '—'})"
                        for change in changes
                    ),
                )
        path = os.path.join(run.layout.env_descriptions, f"{task}.txt")
        if not provenance.refresh_env_description_packages(path, package_list):
            logger.warning("Could not refresh environment description for %s", task)

    run.status["environment_snapshots_final"] = final_snapshots
    run.status["environment_drift"] = {
        "changed_environments": sorted(drift),
        "change_count": sum(len(changes) for changes in drift.values()),
        "environments": drift,
    }

    provenance.refresh_distributed_env_descriptions(
        run.layout.env_descriptions,
        _mapping(run.status.get("www_root_by_cfg")),
        run.cfgs,
        run.tasks,
    )


def _write_environment_viewers(
    run: _Run, diffs: List[envdiff.EnvironmentDiff], note: str
) -> None:
    """Write the viewer pages after report-time environment refresh."""
    baseline_entries = _mapping(run.status.get("baseline_by_cfg_task"))
    baseline_tags = {
        str(_mapping(value).get("tag") or "")
        for value in baseline_entries.values()
        if _mapping(value).get("tag")
    }
    summary_baseline = (
        "mixed per cfg/task"
        if len(baseline_tags) > 1
        else (
            next(iter(baseline_tags))
            if baseline_tags
            else str(_mapping(run.status.get("baseline")).get("tag", ""))
        )
    )
    try:
        viewers = validate.write_viewers(
            run.layout,
            run.cfgs,
            tasks=run.tasks,
            environment_diffs=diffs,
            environment_note=note,
            repos=_mapping(run.status.get("repos")),
            baseline=summary_baseline,
            task_status_by_cfg=_mapping(run.status.get("task_status_by_cfg")),
            baselines_by_cfg_task=baseline_entries,
            changes_since_baseline=_sequence(
                run.status.get("changes_since_baseline")
            ),
            changes_note=str(run.status.get("changes_since_baseline_note") or ""),
        )
    except OSError as error:
        logger.warning("Could not refresh environment viewers: %s", error)
        return
    run.status["viewers"] = viewers
    if viewers:
        run.status["image_review"] = viewers[-1]


_STAGE_FUNCTIONS: Dict[str, Callable[[_Run], None]] = {
    "prepare": _stage_prepare,
    "generate": _stage_generate,
    "submit": _stage_submit,
    "bundles": _stage_bundles,
    "validate": _stage_validate,
}


def _environments_from_status(run: _Run) -> Dict[str, Environment]:
    """Rebuild the environments a resumed run's prepare stage recorded."""
    return {
        name: environment_from_status(name, entry, run.machine, run.args.conda_profile)
        for name, entry in _mapping(run.status.get("repos")).items()
        if isinstance(entry, dict)
    }


def _repo_path(args: argparse.Namespace, spec: RepoSpec) -> str:
    """Resolve where a repository is cloned."""
    return args.repo_paths.get(spec.name) or os.path.join(
        args.repo_root, spec.clone_dirname
    )


def _repos_for_tasks(tasks: Sequence[str]) -> Set[str]:
    """Return repositories needed by these tasks, always including zppy."""
    repos: Set[str] = {"zppy"}
    for task in tasks:
        spec = repo_for_task(task)
        if spec is not None:
            repos.add(spec.name)
    return repos


def _tasks_by_cfg(run: _Run, cfgs: Sequence[str] | None = None) -> Dict[str, Set[str]]:
    """Return the selected task sections available in each generated cfg."""
    selected_cfgs: Sequence[str] = cfgs if cfgs is not None else run.cfgs
    tasks_by_cfg: Dict[str, Set[str]] = {}
    for cfg in selected_cfgs:
        tasks = set(task_sections_for_cfg(cfg)) & set(run.tasks)
        if is_bundles_cfg(cfg) and tasks:
            tasks.add("bundle")
        tasks_by_cfg[cfg] = tasks
    return tasks_by_cfg


def _default_tag(label: str = "") -> str:
    """Build a timestamped tag for a new run, optionally with a label."""
    timestamp: str = datetime.now().strftime("%Y%m%d_%H%M%S")
    if not label:
        return timestamp
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", label):
        raise ValueError(f"Invalid run label {label!r}")
    return f"{timestamp}_{label}"


def _stages_to_run(start_stage: str, stop_after: str | None) -> List[str]:
    """Return the stages to run, from ``start_stage`` through ``stop_after``."""
    start: int = STAGES.index(start_stage)
    stop: int = STAGES.index(stop_after) if stop_after else len(STAGES) - 1
    if stop < start:
        raise ValueError(
            f"--stop-after {stop_after} comes before --start-stage {start_stage}"
        )
    return list(STAGES[start : stop + 1])


def _mapping(value: object) -> Dict[str, object]:
    """Return a dict, whatever the input was."""
    return value if isinstance(value, dict) else {}


def _sequence(value: object) -> List[Dict[str, object]]:
    """Return a list of dictionaries from a status field of unknown shape."""
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _string_list(value: object) -> List[str]:
    """Return a list of strings from a status field of unknown shape."""
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


class _KeyValueAction(argparse.Action):
    """Collect repeated ``REPO=value`` arguments into a dict."""

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str,
        option_string: str | None = None,
    ) -> None:
        mapping: Dict[str, str] = dict(getattr(namespace, self.dest, None) or {})
        name, separator, value = str(values).partition("=")
        name, value = name.strip(), value.strip()
        if not separator:
            raise argparse.ArgumentError(self, f"expected REPO=VALUE, got {values!r}")
        if self.dest == "env_types" and value not in ENV_TYPES:
            raise argparse.ArgumentError(
                self,
                f"env type must be one of {', '.join(ENV_TYPES)}, got {value!r}",
            )
        if name not in REPO_SPECS_BY_NAME:
            raise argparse.ArgumentError(
                self,
                f"unknown repository {name!r}; expected one of "
                f"{', '.join(sorted(REPO_SPECS_BY_NAME))}",
            )
        mapping[name] = value
        setattr(namespace, self.dest, mapping)


class _ListAction(argparse.Action):
    """Replace a configured list on its first CLI occurrence, then append."""

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str,
        option_string: str | None = None,
    ) -> None:
        seen: Set[str] = set(getattr(namespace, "_cli_list_dest_seen", set()))
        current: List[str] = list(getattr(namespace, self.dest, None) or [])
        if self.dest not in seen:
            current = []
            seen.add(self.dest)
            setattr(namespace, "_cli_list_dest_seen", seen)
        current.append(str(values))
        setattr(namespace, self.dest, current)


_CONFIG_DESTINATIONS: Dict[str, str] = {
    "machine": "machine",
    "account": "account",
    "username": "username",
    "tag": "tag",
    "label": "label",
    "shared_root": "shared_root",
    "scratch_root": "scratch_root",
    "repo_root": "repo_root",
    "repo_path": "repo_paths",
    "branch": "branches",
    "env_type": "env_types",
    "existing_env": "existing_envs",
    "allow_existing_envs": "allow_existing_envs",
    "solver": "solver",
    "parallel_envs": "parallel_envs",
    "conda_profile": "conda_profile",
    "cfg": "cfgs",
    "task": "tasks",
    "nco_path": "nco_path",
    "pin_dependencies": "pin_dependencies",
    "unified_load_script": "unified_load_script",
    "baseline": "baseline",
    "start_stage": "start_stage",
    "stop_after": "stop_after",
    "poll_seconds": "poll_seconds",
    "max_wait_submit": "max_wait_submit",
    "max_wait_bundles": "max_wait_bundles",
    "max_wait_images": "max_wait_images",
    "skip_unit_tests": "skip_unit_tests",
    "keep_worktrees": "keep_worktrees",
    "verbose": "verbose",
}
_CONFIG_LIST_KEYS: Set[str] = {"cfg", "task", "pin_dependencies", "baseline"}
_CONFIG_MAPPING_KEYS: Set[str] = {
    "repo_path",
    "branch",
    "env_type",
    "existing_env",
}
_CONFIG_BOOLEAN_KEYS: Set[str] = {
    "allow_existing_envs",
    "skip_unit_tests",
    "keep_worktrees",
    "verbose",
}
_CONFIG_INTEGER_KEYS: Set[str] = {
    "parallel_envs",
    "poll_seconds",
    "max_wait_submit",
    "max_wait_bundles",
    "max_wait_images",
}
_CONFIG_PATH_KEYS: Set[str] = {
    "shared_root",
    "scratch_root",
    "repo_root",
    "repo_path",
    "conda_profile",
    "unified_load_script",
}


def _read_config(path: str) -> Dict[str, object]:
    """Read supported automation options from a cfg-suite INI file."""
    if not path:
        return {}
    config = configparser.ConfigParser(interpolation=None)
    try:
        with open(os.path.expanduser(path), encoding="utf-8") as stream:
            config.read_file(stream)
    except (OSError, configparser.Error) as error:
        raise ValueError(f"Could not read config {path}: {error}") from error
    if config.sections() != ["cfg_suite"]:
        raise ValueError("Config must contain exactly one [cfg_suite] section")
    section = config["cfg_suite"]
    for key in section:
        if key not in _CONFIG_DESTINATIONS:
            raise ValueError(f"Unknown configuration key: {key}")

    return {
        _CONFIG_DESTINATIONS[key]: _parse_config_value(key, raw.strip())
        for key, raw in section.items()
    }


def _parse_config_mapping(key: str, value: str) -> Dict[str, str]:
    """Parse a comma-separated repository mapping from the config."""
    mapping: Dict[str, str] = {}
    for item in value.split(",") if value else []:
        repo, separator, selected = item.partition("=")
        repo, selected = repo.strip(), selected.strip()
        if not separator or repo not in REPO_SPECS_BY_NAME or not selected:
            raise ValueError(
                f"Invalid {key} entry {item.strip()!r}; expected repo=value"
            )
        if key == "env_type" and selected not in ENV_TYPES:
            raise ValueError(
                f"Invalid env_type {selected!r}; expected one of "
                f"{', '.join(ENV_TYPES)}"
            )
        mapping[repo] = selected
    return mapping


def _parse_config_value(key: str, value: str) -> object:
    """Convert one validated config value to its CLI representation."""
    if key in _CONFIG_LIST_KEYS:
        return [item.strip() for item in value.split(",") if item.strip()]
    if key in _CONFIG_MAPPING_KEYS:
        return _parse_config_mapping(key, value)
    if key in _CONFIG_BOOLEAN_KEYS:
        normalized = value.lower()
        if normalized not in {"true", "false", "yes", "no", "1", "0"}:
            raise ValueError(f"Invalid boolean for {key}: {value!r}")
        return normalized in {"true", "yes", "1"}
    if key in _CONFIG_INTEGER_KEYS:
        try:
            return int(value)
        except ValueError as error:
            raise ValueError(f"Invalid integer for {key}: {value!r}") from error
    return _parse_config_scalar(key, value)


def _parse_config_scalar(key: str, value: str) -> str | None:
    """Validate and normalize a scalar config value."""
    if key in _CONFIG_PATH_KEYS:
        value = os.path.expanduser(value)
    if key == "solver" and value not in SOLVERS:
        raise ValueError(f"Invalid solver for {key}: {value!r}")
    if key == "start_stage" and value not in STAGES:
        raise ValueError(f"Invalid stage for {key}: {value!r}")
    if key == "stop_after" and value and value not in STAGES:
        raise ValueError(f"Invalid stage for {key}: {value!r}")
    return value or (None if key == "stop_after" else value)


def _effective_configuration(
    args: argparse.Namespace, cfgs: Sequence[str], tasks: Sequence[str]
) -> Dict[str, object]:
    """Return the resolved, JSON-safe run configuration."""
    return {
        key: value
        for key, value in vars(args).items()
        if not key.startswith("_")
    } | {"cfgs": list(cfgs), "tasks": list(tasks)}


def _build_parser(
    config_values: Dict[str, object] | None = None,
) -> argparse.ArgumentParser:
    """Build the cfg suite CLI."""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=__doc__,
    )
    parser.add_argument("--config", default="", help="INI automation configuration.")
    parser.add_argument("--machine", default=None, help="chrysalis | compy | perlmutter")
    parser.add_argument(
        "--account", default="e3sm", help="SLURM account for the image checker."
    )
    parser.add_argument("--username", default="", help="Defaults to $USER.")
    parser.add_argument(
        "--tag", default="", help="Resume an existing run with this tag."
    )
    parser.add_argument(
        "--label", default="", help="Append a label to the default timestamped tag."
    )
    parser.add_argument(
        "--shared-root",
        default="",
        help=(
            "Group-writable root holding runs/ and baselines/. Defaults to the "
            "machine's web-served location, or $ZPPY_CFG_SUITE_ROOT."
        ),
    )
    parser.add_argument(
        "--scratch-root",
        default="",
        help=(
            "Where intermediate data (worktrees, zppy's post-processing output) "
            "goes, one <tag> directory per run. Defaults to the user's scratch "
            f"space, e.g. /lcrc/globalscratch/$USER/{SUITE_ROOT_DIRNAME} on Chrysalis."
        ),
    )
    parser.add_argument(
        "--repo-root",
        default=os.path.expanduser("~/ez"),
        help="Directory holding the five repository clones.",
    )
    parser.add_argument(
        "--repo-path",
        dest="repo_paths",
        action=_KeyValueAction,
        default={},
        metavar="REPO=PATH",
        help="Override one repository's clone location. Repeatable.",
    )
    parser.add_argument(
        "--branch",
        dest="branches",
        action=_KeyValueAction,
        default={},
        metavar="REPO=BRANCH",
        help="Override one repository's branch. Repeatable.",
    )
    parser.add_argument(
        "--env-type",
        dest="env_types",
        action=_KeyValueAction,
        default={},
        metavar="REPO=dev|unified|baseline",
        help=(
            "How to build a repository's environment. 'dev' solves its dev.yml "
            "afresh, 'unified' uses E3SM-Unified, and 'baseline' rebuilds the "
            "environment the current baseline was produced with."
        ),
    )
    parser.add_argument(
        "--existing-env",
        dest="existing_envs",
        action=_KeyValueAction,
        default={},
        metavar="REPO=ENV",
        help="Reuse a named conda environment for a repository. Repeatable.",
    )
    parser.add_argument(
        "--allow-existing-envs",
        action=argparse.BooleanOptionalAction,
        help="Reuse an environment whose name this run would have created.",
    )
    parser.add_argument(
        "--solver",
        choices=SOLVERS,
        default="mamba",
        help=(
            "Tool that solves and creates the environments; falls back to conda "
            "if mamba is not installed. Everything else uses conda."
        ),
    )
    parser.add_argument(
        "--parallel-envs",
        type=int,
        default=1,
        help="How many environments to build at once.",
    )
    parser.add_argument(
        "--conda-profile",
        default=os.path.expanduser("~/miniforge3/etc/profile.d/conda.sh"),
        help="Conda profile sourced by generated task scripts.",
    )
    parser.add_argument("--cfg", dest="cfgs", action=_ListAction, help="Repeatable.")
    parser.add_argument(
        "--task",
        dest="tasks",
        action=_ListAction,
        choices=TASK_NAMES,
        help="Task to run; repeatable.",
    )
    parser.add_argument("--nco-path", default="", help="Development-version NCO path.")
    parser.add_argument(
        "--pin",
        dest="pin_dependencies",
        action=_ListAction,
        default=[],
        metavar="SPEC",
        help="Temporarily pin a dependency; repeatable.",
    )
    parser.add_argument(
        "--unified-load-script",
        default="",
        help="Override the E3SM-Unified load script.",
    )
    parser.add_argument(
        "--baseline",
        action=_ListAction,
        default=[],
        metavar="TASK=TAG|CFG:TASK=TAG",
        help="Use a selected baseline run; repeatable.",
    )
    parser.add_argument("--start-stage", choices=STAGES, default="prepare")
    parser.add_argument("--stop-after", choices=STAGES, default=None)
    parser.add_argument(
        "--poll-seconds",
        type=int,
        default=600,
        help="How often to check whether the queue has drained.",
    )
    parser.add_argument("--max-wait-submit", type=int, default=14400)
    parser.add_argument("--max-wait-bundles", type=int, default=3600)
    parser.add_argument("--max-wait-images", type=int, default=7200)
    parser.add_argument(
        "--skip-unit-tests",
        action=argparse.BooleanOptionalAction,
        help="Skip the unit tests that gate the run.",
    )
    parser.add_argument(
        "--keep-worktrees",
        action=argparse.BooleanOptionalAction,
        help="Keep worktrees even when the run passes.",
    )
    parser.add_argument("--verbose", action=argparse.BooleanOptionalAction)
    if config_values:
        parser.set_defaults(**config_values)
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
