"""Orchestrate zppy's complete run test.

One command builds immutable checkouts and environments for zppy and the four
packages whose tasks it launches, generates the weekly cfgs, submits them,
validates the results, and renders a report.

Usage
-----
On Chrysalis::

    python -m tests.complete_run.automation --machine chrysalis --account e3sm

Every stage writes ``status.json`` under the run directory, so an interrupted
run can be resumed with ``--start-stage`` and a crashed one still produces a
report.
"""

from __future__ import annotations

import argparse
import glob
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Callable, Dict, List, Sequence, Set, Tuple

from tests.complete_run import envdiff, provenance
from tests.complete_run import report as report_module
from tests.complete_run import validate
from tests.complete_run.commands import CommandError, run_command, run_command_status
from tests.complete_run.environments import (
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
from tests.complete_run.layout import (
    RUN_SEGMENT,
    RunLayout,
    read_json_object,
    resolve_baseline,
    run_layout,
    shared_root,
    write_json,
)
from tests.complete_run.params import (
    DEFAULT_CFGS_TO_RUN,
    DEFAULT_TASKS_TO_RUN,
    IMAGE_HELPER_TEST_FILES,
    REPO_SPECS,
    REPO_SPECS_BY_NAME,
    MachineProfile,
    RepoSpec,
    generated_cfg_path,
    is_bundles_cfg,
    resolve_machine,
)
from tests.complete_run.slurm import queued_job_ids, wait_for_user_jobs
from tests.complete_run.worktrees import Checkout, create_checkout, remove_checkouts

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

# Unit tests that gate a run, as (repository, path or glob in its worktree). A
# failure means the run would be testing known-broken code.
UNIT_TEST_TARGETS: Tuple[Tuple[str, str], ...] = (
    ("zppy_interfaces", "tests/unit/global_time_series"),
    ("zppy_interfaces", "tests/unit/pcmdi_diags"),
    ("zppy", "tests/test_*.py"),
    # The tests of the image checker itself; a regression there would make the
    # run's own verdict untrustworthy.
    *(("zppy", path) for path in IMAGE_HELPER_TEST_FILES),
)


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
        if environment is None or not environment.name:
            raise StageError(
                "prepare_failed",
                f"No {repo_name} environment is recorded for this run. Run the "
                "prepare stage first, or pass --start-stage prepare.",
            )
        return environment

    def write_status(self) -> None:
        write_json(self.layout.status, self.status)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the complete run test and return a process exit code."""
    parser = _build_parser()
    args: argparse.Namespace = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
    )
    try:
        run = _start_run(args)
    except ValueError as error:
        parser.error(str(error))
    return run_complete_test(run)


def _start_run(args: argparse.Namespace) -> _Run:
    """Resolve the run's settings, carrying forward a resumed run's selections.

    Raises
    ------
    ValueError
        For an unknown machine, a machine with no shared root, or a stage range
        that runs backwards.
    """
    machine: MachineProfile = resolve_machine(args.machine)
    _stages_to_run(args.start_stage, args.stop_after)
    tag: str = args.tag or _default_tag(args.run_number)
    root: str = shared_root(machine.cfg_suffix, args.shared_root)
    username: str = args.username or os.environ.get("USER", "")
    scratch_dir: str = os.path.join(
        args.scratch_root
        or os.path.join(machine.scratch_workspace(username), "zppy_complete_run"),
        tag,
    )
    # zppy's post-processing output is intermediate data: only the plots, and
    # what validation copies out, belong in the shared run directory.
    layout: RunLayout = run_layout(root, tag, os.path.join(scratch_dir, "output"))

    status: Dict[str, object] = read_json_object(layout.status)
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
        tasks=list(
            args.tasks or _string_list(status.get("tasks")) or DEFAULT_TASKS_TO_RUN
        ),
        status=status,
    )
    status.update(
        {
            "tag": tag,
            "machine": machine.name,
            "cfgs": run.cfgs,
            "tasks": run.tasks,
            "run_dir": layout.root,
            "shared_root": root,
            "scratch_dir": scratch_dir,
            "output_dir": layout.output,
            "worktree_root": run.worktree_root,
        }
    )
    status.setdefault("repos", {})
    return run


def run_complete_test(run: _Run) -> int:
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
    env_types: Dict[str, str] = run.args.env_types
    if env_types.get("zppy") == ENV_TYPE_UNIFIED:
        raise StageError(
            "prepare_failed",
            "zppy itself cannot run from E3SM-Unified: the run installs the "
            "revision under test and runs pytest from its worktree.",
        )

    baseline: RunLayout | None = _record_baseline(run)
    if ENV_TYPE_BASELINE in env_types.values() and baseline is None:
        raise StageError(
            "prepare_failed",
            "No baseline is promoted to rebuild environments from. Promote a run "
            "with `python -m tests.complete_run.promote`, or use --env-type dev.",
        )

    repos: Dict[str, object] = {}
    to_build: List[Tuple[RepoSpec, Checkout, str]] = []
    for spec in REPO_SPECS:
        env_type: str = env_types.get(spec.name, ENV_TYPE_DEV)
        if env_type == ENV_TYPE_UNIFIED:
            # Nothing to check out: the task runs from a released package.
            run.environments[spec.name] = unified_environment(spec.name, run.machine)
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
        if env_type == ENV_TYPE_BASELINE and baseline is not None:
            environment_file = baseline.environment_file(spec.name)
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


def _record_baseline(run: _Run) -> RunLayout | None:
    """Record which promoted run this one is compared against, if any."""
    try:
        baseline: RunLayout = resolve_baseline(run.root)
    except FileNotFoundError as error:
        logger.info("No baseline to compare against: %s", error)
        run.status["baseline"] = {}
        return None

    manifest = read_json_object(baseline.manifest)
    run.status["baseline"] = {
        "tag": os.path.basename(baseline.root),
        "run_dir": baseline.root,
        "generated": manifest.get("generated", ""),
    }
    return baseline


def _run_unit_tests(run: _Run) -> None:
    """Run the unit tests that gate a complete run, each in its own environment.

    A failure here means the run would be testing known-broken code, so it stops
    the run rather than being recorded and carried forward.
    """
    if run.args.skip_unit_tests:
        logger.warning("Skipping unit tests at the caller's request")
        return

    by_name: Dict[str, Checkout] = {
        checkout.name: checkout for checkout in run.checkouts
    }
    for repo_name, pattern in UNIT_TEST_TARGETS:
        checkout = by_name.get(repo_name)
        if checkout is None:
            continue  # Running from E3SM-Unified; there is no worktree to test.
        # No shell runs these commands, so globs are expanded here.
        targets: List[str] = sorted(
            os.path.relpath(path, checkout.path)
            for path in glob.glob(os.path.join(checkout.path, pattern))
        )
        if not targets:
            logger.warning("%s: nothing matches %s; skipping", repo_name, pattern)
            continue

        logger.info("Running %s unit tests: %s", repo_name, pattern)
        returncode, output = run_command_status(
            run.environment(repo_name).run_args(["python", "-m", "pytest", *targets]),
            cwd=checkout.path,
        )
        if returncode != 0:
            raise StageError(
                "prepare_failed",
                f"{repo_name} unit tests failed ({pattern}):\n{output[-2000:]}",
            )


def _write_env_descriptions(run: _Run) -> None:
    """Write one environment description per selected task."""
    by_name: Dict[str, Checkout] = {
        checkout.name: checkout for checkout in run.checkouts
    }
    # Several tasks can share one environment; list its packages once.
    package_lists: Dict[str, str] = {}
    for task, environment in sorted(
        environments_by_task(run.environments, run.machine).items()
    ):
        if task not in run.tasks:
            continue
        key: str = environment.name or environment.activation_command
        if key not in package_lists:
            package_lists[key] = provenance.conda_package_list(environment)
            if environment.env_type == ENV_TYPE_UNIFIED:
                run.status["unified"] = provenance.describe_unified(
                    package_lists[key], _unified_load_script(run.machine)
                )
        provenance.write_env_description(
            run.layout.env_descriptions,
            task,
            by_name.get(environment.repo_name),
            environment,
            package_list=package_lists[key],
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
        zppy_version=__version__,
        unified=_mapping(run.status.get("unified")) or None,
    )
    provenance.write_manifest(run.layout.root, manifest)


def _unified_load_script(machine: MachineProfile) -> str:
    """Return the script the machine's Unified activation command sources."""
    command: str = machine.unified_env_cmd.strip()
    return command.split(None, 1)[1] if command.startswith("source ") else ""


def _stage_generate(run: _Run) -> None:
    """Generate the machine-specific cfgs from their templates."""
    baseline_dir: str = str(_mapping(run.status.get("baseline")).get("run_dir", ""))
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
        # Pinned to what prepare recorded, so the cfgs compare against the
        # baseline the report names -- empty meaning none.
        "--baseline-dir",
        baseline_dir,
        "--environment-commands",
        run.machine.unified_env_cmd,
    ]
    for cfg in run.cfgs:
        command.extend(["--cfg", cfg])
    for task in run.tasks:
        command.extend(["--task", task])
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
    for cfg in cfgs:
        for status_file in sorted(
            glob.glob(os.path.join(run.layout.status_dir(cfg), "*status"))
        ):
            try:
                with open(status_file) as stream:
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

    _wait(run, max_wait)


def _wait(run: _Run, max_wait: int) -> None:
    """Wait for the queue to drain, mapping the outcome onto a terminal stage."""
    outcome: str = wait_for_user_jobs(
        run.username, check_interval=run.args.poll_seconds, max_wait=max_wait
    )
    if outcome == "dependency_never_satisfied":
        raise StageError(
            "dependency_never_satisfied",
            "Every remaining job had an unsatisfiable dependency; they were "
            "cancelled. Check the status files of the jobs that failed first.",
        )
    if outcome == "timed_out":
        raise StageError("timed_out", f"Jobs did not finish within {max_wait} seconds.")


def _stage_validate(run: _Run) -> None:
    """Sweep status files, run the integration tests, and check the images."""
    status = run.status
    layout = run.layout
    worktree: str = run.zppy_worktree
    zppy_env: Environment = run.environment("zppy")

    sweep = validate.sweep_status_files(layout, run.cfgs)
    status["status_sweep"] = {
        "passed": sweep.passed,
        "failure_count": sweep.failure_count,
        "failures_by_cfg": sweep.failures_by_cfg,
        "missing_dirs": sweep.missing_dirs,
    }

    status["www_root_by_cfg"] = provenance.distribute_env_descriptions(
        layout.env_descriptions,
        worktree,
        run.cfgs,
        run.tasks,
        run.machine.cfg_suffix,
    )

    pytest_results = validate.run_pytest_files(worktree, zppy_env)
    status["pytest_results"] = [asdict(result) for result in pytest_results]

    image_result = validate.run_image_checker(
        worktree,
        layout.root,
        run.tag,
        run.machine,
        zppy_env.name,
        run.args.conda_profile,
        account=run.args.account,
        max_wait=run.args.max_wait_images,
    )
    status["image_check"] = asdict(image_result)

    # A run is only promotable if it describes itself: the images it produced,
    # and the small settings baselines the cheaper tests compare against.
    status["image_counts"] = validate.write_image_lists(layout, run.cfgs)
    validate.capture_settings_baselines(worktree, layout, run.cfgs, zppy_env)

    # An image difference is only interpretable alongside what changed in the
    # environment, so the comparison goes on every viewer page and in the
    # report rather than being left for a reader to work out.
    diffs, note = _compare_environments(run)
    status["environment_diff"] = envdiff.summarize(diffs)
    status["environment_note"] = note
    viewers: List[str] = validate.write_viewers(
        layout,
        run.cfgs,
        tasks=run.tasks,
        environment_diffs=diffs,
        environment_note=note,
        repos=_mapping(status.get("repos")),
        baseline=str(_mapping(status.get("baseline")).get("tag", "")),
    )
    status["viewers"] = viewers
    # The summary is written last; it is the page a reviewer starts from.
    status["image_review"] = viewers[-1]

    validate.collect_artifacts(worktree, layout.root)

    if not sweep.passed or not all(result.passed for result in pytest_results):
        raise StageError(
            "validation_failed",
            "Validation found failures; see the report for details.",
        )
    if not image_result.passed:
        raise StageError(
            "validation_failed",
            f"The image checker did not pass (state {image_result.state}).",
        )


def _compare_environments(run: _Run) -> Tuple[List[envdiff.EnvironmentDiff], str]:
    """Compare this run's environments against the promoted baseline's."""
    repos: List[str] = sorted(
        name
        for name, entry in _mapping(run.status.get("repos")).items()
        if isinstance(entry, dict) and entry.get("environment_type") == ENV_TYPE_DEV
    )
    baseline_dir: str = str(_mapping(run.status.get("baseline")).get("run_dir", ""))
    if not repos or not baseline_dir:
        return [], ""

    diffs = envdiff.compare_run_environments(run.layout, RunLayout(baseline_dir), repos)
    modes: Dict[str, str] = {
        name: str(run.args.env_types.get(name, ENV_TYPE_DEV)) for name in repos
    }
    note: str = envdiff.interpretation(diffs, modes)
    logger.info("%s", note)
    return diffs, note


def _stage_report(run: _Run, stages_run: Sequence[str] = ()) -> None:
    """Render the run's JSON and Markdown reports.

    A run only reports "passed" once validation has actually run. Stopping early
    with ``--stop-after`` leaves the stage as it was, so a partial run is never
    mistaken for a clean one.
    """
    if "validate" in stages_run and str(run.status.get("stage")) not in FAILURE_STAGES:
        run.status["stage"] = "passed"
    report = report_module.render_report(run.status, run.layout)
    report_module.write_report(report, run.layout.root)


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


def _default_tag(run_number: int) -> str:
    """Build the default tag for a run started today."""
    return f"{datetime.now().strftime('%Y%m%d')}_run{run_number}"


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


def _string_list(value: object) -> List[str]:
    """Return a list of strings from a status field of unknown shape."""
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


class _KeyValueAction(argparse.Action):
    """Collect repeated ``REPO=value`` arguments into a dict."""

    def __call__(self, parser, namespace, values, option_string=None) -> None:
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


def _build_parser() -> argparse.ArgumentParser:
    """Build the complete run CLI."""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=__doc__,
    )
    parser.add_argument(
        "--machine", required=True, help="chrysalis | compy | perlmutter"
    )
    parser.add_argument(
        "--account", default="e3sm", help="SLURM account for the image checker."
    )
    parser.add_argument("--username", default="", help="Defaults to $USER.")
    parser.add_argument("--tag", default="", help="Run tag; defaults to <date>_run<N>.")
    parser.add_argument("--run-number", type=int, default=1)
    parser.add_argument(
        "--shared-root",
        default="",
        help=(
            "Group-writable root holding runs/ and baselines/. Defaults to the "
            "machine's web-served location, or $ZPPY_COMPLETE_RUN_ROOT."
        ),
    )
    parser.add_argument(
        "--scratch-root",
        default="",
        help=(
            "Where intermediate data (worktrees, zppy's post-processing output) "
            "goes, one <tag> directory per run. Defaults to the user's scratch "
            "space, e.g. /lcrc/globalscratch/$USER/zppy_complete_run on Chrysalis."
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
        action="store_true",
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
    parser.add_argument("--cfg", dest="cfgs", action="append", help="Repeatable.")
    parser.add_argument("--task", dest="tasks", action="append", help="Repeatable.")
    parser.add_argument("--nco-path", default="", help="Development-version NCO path.")
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
        action="store_true",
        help="Skip the unit tests that gate the run.",
    )
    parser.add_argument(
        "--keep-worktrees",
        action="store_true",
        help="Keep worktrees even when the run passes.",
    )
    parser.add_argument("--verbose", action="store_true")
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
