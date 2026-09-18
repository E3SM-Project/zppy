"""Validation stage of the complete run test.

Three checks, in order: every submitted job reported OK, the integration tests
pass, and the image checker -- submitted as its own batch job, since it needs a
compute node -- finds no reviewable differences.
"""

from __future__ import annotations

import glob
import json
import logging
import os
import shutil
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from tests.complete_run.commands import run_command_status
from tests.complete_run.envdiff import EnvironmentDiff
from tests.complete_run.environments import Environment
from tests.complete_run.layout import SETTINGS_BASELINE_NAMES, RunLayout
from tests.complete_run.params import (
    INTEGRATION_TEST_FILES,
    MachineProfile,
    case_name_for_cfg,
    package_for_task,
    repo_for_task,
)
from tests.complete_run.slurm import (
    JobOutcome,
    build_batch_script,
    job_passed,
    submit,
    wait_for_job,
)
from tests.complete_run.viewer import (
    REVIEW_SUMMARY_FILENAME,
    SummaryRow,
    count_severities,
    load_scores,
    write_summary,
    write_viewer,
)
from tests.integration.image_severity import REVIEWABLE_SEVERITIES, SEVERITY_ORDER
from tests.integration.weekly_cfgs import WEEKLY_CFGS_BY_NAME, checker_name

logger: logging.Logger = logging.getLogger(__name__)

SUMMARY_FILENAME: str = "test_images_summary.md"
EARLY_SUMMARY_FILENAME: str = "early_test_images_summary.md"

# The single image-checker job is polled more often than the queue as a whole:
# it runs for minutes, not hours, and a long interval would dominate its wait.
IMAGE_CHECK_POLL_SECONDS: int = 120

# Artifacts zppy writes inside its own repo. A run works from a throwaway
# worktree, so these must be collected before the worktree is removed.
IN_REPO_ARTIFACTS: tuple[str, ...] = (
    SUMMARY_FILENAME,
    EARLY_SUMMARY_FILENAME,
    "images_logs",
    "tests/integration/generated",
)


@dataclass
class StatusSweep:
    """Result of grepping every cfg's job status files for non-OK entries."""

    # cfg name -> the non-OK status lines found for it.
    failures_by_cfg: Dict[str, List[str]] = field(default_factory=dict)
    # cfgs whose status directory did not exist at all.
    missing_dirs: List[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.failures_by_cfg and not self.missing_dirs

    @property
    def failure_count(self) -> int:
        return sum(len(lines) for lines in self.failures_by_cfg.values())


@dataclass
class PytestResult:
    """Outcome of one pytest file."""

    path: str
    returncode: int
    output: str

    @property
    def passed(self) -> bool:
        return self.returncode == 0


@dataclass
class ImageCheckResult:
    """Outcome of the image-checker batch job."""

    job_id: str = ""
    state: str = "NOT_RUN"
    exit_code: str = "N/A"
    # "final", "early", or "missing" -- which summary file was recovered.
    summary_source: str = "missing"
    summary_path: str = ""
    stdout_path: str = ""
    stderr_path: str = ""
    severity_counts: "OrderedDict[str, int]" = field(default_factory=OrderedDict)

    @property
    def passed(self) -> bool:
        return job_passed(self.state, self.exit_code)

    @property
    def reviewable_count(self) -> int:
        return reviewable_count(self.severity_counts)


def reviewable_count(severity_counts: Dict[str, int]) -> int:
    """Count the images a human must look at.

    ``IDENTICAL`` and ``NEGLIGIBLE`` differences do not fail a run.
    """
    return sum(
        int(count)
        for severity, count in severity_counts.items()
        if severity in REVIEWABLE_SEVERITIES
    )


def sweep_status_files(layout: RunLayout, cfgs: Sequence[str]) -> StatusSweep:
    """Check every cfg's status files for entries that are not OK.

    This is the Python form of the documented ``grep -v "OK" *status`` sweep.
    """
    sweep = StatusSweep()
    for cfg in cfgs:
        status_dir: str = layout.status_dir(cfg)
        if not os.path.isdir(status_dir):
            logger.warning("Status directory not found for %s: %s", cfg, status_dir)
            sweep.missing_dirs.append(cfg)
            continue

        failures: List[str] = []
        for status_file in sorted(glob.glob(os.path.join(status_dir, "*status"))):
            try:
                with open(status_file) as stream:
                    for line in stream:
                        stripped: str = line.strip()
                        if stripped and stripped != "OK":
                            failures.append(
                                f"{os.path.basename(status_file)}: {stripped}"
                            )
            except OSError as error:
                failures.append(
                    f"{os.path.basename(status_file)}: unreadable ({error})"
                )

        if failures:
            logger.error("%s: %s non-OK status entries", cfg, len(failures))
            sweep.failures_by_cfg[cfg] = failures
        else:
            logger.info("%s: all status files OK", cfg)

    return sweep


def run_pytest_files(
    workdir: str,
    environment: Environment,
    test_files: Sequence[str] = INTEGRATION_TEST_FILES,
) -> List[PytestResult]:
    """Run each pytest file, recording its outcome rather than aborting.

    The files run in the zppy environment under test: they shell out to
    ``zppy -c`` themselves, which must be the revision being tested.
    """
    results: List[PytestResult] = []
    for test_file in test_files:
        logger.info("Running %s", test_file)
        returncode, output = run_command_status(
            environment.run_args(["python", "-m", "pytest", test_file]), cwd=workdir
        )
        if returncode != 0:
            logger.error("%s failed (exit %s)", test_file, returncode)
        results.append(
            PytestResult(path=test_file, returncode=returncode, output=output)
        )
    return results


def summarize_severities(results_dir: str) -> "OrderedDict[str, int]":
    """Count image comparisons by severity across every ``image_scores.json``.

    Severities are reported in ``SEVERITY_ORDER`` so two runs' reports line up,
    and every severity appears even at zero.
    """
    counts: "OrderedDict[str, int]" = OrderedDict(
        (severity, 0) for severity in SEVERITY_ORDER
    )
    pattern: str = os.path.join(results_dir, "**", "image_scores.json")
    for scores_file in sorted(glob.glob(pattern, recursive=True)):
        try:
            with open(scores_file) as stream:
                entries = json.load(stream)
        except (OSError, json.JSONDecodeError) as error:
            logger.warning("Could not read %s: %s", scores_file, error)
            continue
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            severity = entry.get("severity")
            if isinstance(severity, str) and severity in counts:
                counts[severity] += 1

    return counts


def run_image_checker(
    workdir: str,
    results_dir: str,
    tag: str,
    machine: MachineProfile,
    env_name: str,
    *,
    account: str = "",
    check_interval: int = IMAGE_CHECK_POLL_SECONDS,
    max_wait: int = 7200,
) -> ImageCheckResult:
    """Submit the image checker as a batch job and wait for it.

    The image checker needs a compute node for multiprocessing, which is why it
    was historically the one step left to run by hand.
    """
    os.makedirs(results_dir, exist_ok=True)
    script_path: str = os.path.join(results_dir, f"image_checker_{tag}.sbatch")
    output_prefix: str = os.path.join(results_dir, f"image_checker_{tag}")

    # A stale summary from an earlier attempt would be silently reported as this
    # run's result.
    for name in (SUMMARY_FILENAME, EARLY_SUMMARY_FILENAME):
        stale: str = os.path.join(workdir, name)
        if os.path.exists(stale):
            os.remove(stale)

    script: str = build_batch_script(
        job_name=f"zppy_image_checker_{tag}",
        output_prefix=output_prefix,
        directives=machine.sbatch_directives
        + ((f"#SBATCH --account={account}",) if account else ()),
        conda_activation_cmd=machine.conda_activation_cmd,
        env_name=env_name,
        workdir=workdir,
        body="python -m pytest tests/integration/test_images.py",
    )
    with open(script_path, "w") as stream:
        stream.write(script)

    result = ImageCheckResult()
    try:
        result.job_id = submit(script_path)
    except Exception as error:  # noqa: BLE001 - recorded, not raised
        logger.error("Could not submit the image checker: %s", error)
        result.state = "SUBMISSION_FAILED"
        return result

    result.stdout_path = f"{output_prefix}.o{result.job_id}"
    result.stderr_path = f"{output_prefix}.e{result.job_id}"

    outcome: JobOutcome = wait_for_job(
        result.job_id, check_interval=check_interval, max_wait=max_wait
    )
    result.state = outcome.state
    result.exit_code = outcome.exit_code

    result.summary_source, result.summary_path = _collect_summary(
        workdir, results_dir, tag
    )
    result.severity_counts = summarize_severities(results_dir)
    return result


def _collect_summary(workdir: str, results_dir: str, tag: str) -> tuple[str, str]:
    """Recover the image summary, preferring a complete one over an early one."""
    destination: str = os.path.join(results_dir, f"test_images_summary_{tag}.md")
    for name, source_label in (
        (SUMMARY_FILENAME, "final"),
        (EARLY_SUMMARY_FILENAME, "early"),
    ):
        candidate: str = os.path.join(workdir, name)
        if os.path.isfile(candidate):
            shutil.copy(candidate, destination)
            if source_label == "early":
                logger.warning("Only an early image summary was produced")
            return source_label, destination

    logger.warning("No image summary was produced in %s", workdir)
    return "missing", ""


def collect_artifacts(workdir: str, results_dir: str) -> List[str]:
    """Copy the artifacts zppy leaves inside its repo into the results dir.

    The run works from a throwaway worktree, so anything left behind in the
    repo is lost when that worktree is removed.
    """
    collected: List[str] = []
    artifacts_dir: str = os.path.join(results_dir, "artifacts")
    os.makedirs(artifacts_dir, exist_ok=True)

    for relative in IN_REPO_ARTIFACTS:
        source: str = os.path.join(workdir, relative)
        if not os.path.exists(source):
            continue
        destination: str = os.path.join(artifacts_dir, os.path.basename(relative))
        try:
            if os.path.isdir(source):
                shutil.copytree(source, destination, dirs_exist_ok=True)
            else:
                shutil.copy(source, destination)
        except OSError as error:
            logger.warning("Could not collect %s: %s", source, error)
            continue
        collected.append(destination)

    return collected


# Baseline material ###########################################################
# A run is promotable only if it describes itself: the images it produced, and
# the small settings baselines the cheaper tests compare against. Both are
# captured from the run rather than copied at promotion time, so a baseline's
# image list can never disagree with its images.

# Diff directories live inside the www tree but are this run's review output,
# not part of the baseline it offers.
_DIFF_DIR_MARKER: str = "image_check_failures"

# Where each small baseline comes from in the zppy working tree.
_SETTINGS_SOURCES: Dict[str, str] = {
    "expected_bash_files": "test_bash_generation_output/post/scripts",
    "test_defaults_expected_files": "test_defaults_output/post/scripts",
    "test_campaign_cryosphere_expected_files": "test_campaign_cryosphere_output/post/scripts",
    "test_campaign_cryosphere_override_expected_files": "test_campaign_cryosphere_override_output/post/scripts",
    "test_campaign_high_res_v1_expected_files": "test_campaign_high_res_v1_output/post/scripts",
    "test_campaign_none_expected_files": "test_campaign_none_output/post/scripts",
    "test_campaign_water_cycle_expected_files": "test_campaign_water_cycle_output/post/scripts",
    "test_campaign_water_cycle_override_expected_files": "test_campaign_water_cycle_override_output/post/scripts",
}


def write_image_lists(layout: RunLayout, cfgs: Sequence[str]) -> Dict[str, int]:
    """List the images each cfg produced, for a future run to compare against.

    Returns the image count per cfg. A cfg that produced nothing is recorded as
    zero rather than skipped, so promoting an empty run is visible.
    """
    os.makedirs(layout.image_lists, exist_ok=True)
    counts: Dict[str, int] = {}

    for cfg in cfgs:
        case: str = case_name_for_cfg(cfg)
        case_dir: str = layout.www_case_dir(cfg, case)
        images: List[str] = []
        for directory, subdirectories, filenames in os.walk(case_dir):
            # Do not offer this run's own diff output as expected images.
            subdirectories[:] = [
                name for name in subdirectories if _DIFF_DIR_MARKER not in name
            ]
            for filename in sorted(filenames):
                if filename.endswith(".png"):
                    relative = os.path.relpath(
                        os.path.join(directory, filename), case_dir
                    )
                    images.append(f"./{relative}")

        images.sort()
        with open(layout.image_list(cfg), "w") as stream:
            stream.write("\n".join(images))
            if images:
                stream.write("\n")
        counts[cfg] = len(images)
        if not images:
            logger.warning("%s produced no images under %s", cfg, case_dir)
        else:
            logger.info("%s: listed %s images", cfg, len(images))

    return counts


def capture_settings_baselines(
    workdir: str, layout: RunLayout, cfgs: Sequence[str]
) -> List[str]:
    """Copy the small settings and bash baselines out of the working tree.

    These are produced by the cheaper integration tests, which write into the
    repository. The run works from a throwaway worktree, so they have to be
    captured before it is removed.
    """
    os.makedirs(layout.settings, exist_ok=True)
    captured: List[str] = []

    for name, relative_source in _SETTINGS_SOURCES.items():
        source: str = os.path.join(workdir, relative_source)
        if not os.path.isdir(source):
            logger.warning("No settings baseline material at %s", source)
            continue
        destination: str = layout.settings_baseline(name)
        shutil.rmtree(destination, ignore_errors=True)
        try:
            shutil.copytree(source, destination)
        except OSError as error:
            logger.warning("Could not capture %s: %s", name, error)
            continue
        # Provenance files carry a timestamp, so they would differ on every run.
        for stale in glob.glob(os.path.join(destination, "provenance*")):
            os.remove(stale)
        captured.append(destination)

    bundle_source: str = layout.status_dir("weekly_bundles")
    if "weekly_bundles" in cfgs and os.path.isdir(bundle_source):
        bundle_destination: str = os.path.join(
            layout.settings_baseline("expected_bundles"), "bundle_files"
        )
        os.makedirs(bundle_destination, exist_ok=True)
        for bundle in sorted(glob.glob(os.path.join(bundle_source, "bundle*.bash"))):
            shutil.copy(bundle, bundle_destination)
        captured.append(bundle_destination)

    missing = [
        name
        for name in SETTINGS_BASELINE_NAMES
        if not os.path.exists(layout.settings_baseline(name))
    ]
    if missing:
        logger.warning(
            "This run is missing %s settings baselines and cannot be promoted "
            "as a complete one: %s",
            len(missing),
            ", ".join(missing),
        )

    return captured


def write_viewers(
    layout: RunLayout,
    cfgs: Sequence[str],
    tasks: Optional[Sequence[str]] = None,
    environment_diffs: Optional[List[EnvironmentDiff]] = None,
    environment_note: str = "",
    repos: Optional[Dict[str, object]] = None,
    baseline: str = "",
) -> List[str]:
    """Write a review page for every checked task, and a summary above them.

    The summary (``<run>/index.html``) has one table across every package and
    one row per cfg and task, each linking to its review page. A task the image
    checker was expected to cover but recorded nothing for still gets a row: a
    check that silently did not happen is a finding.

    The environment comparison is repeated on each page: a reviewer opens one
    task's diffs and needs to know there whether a dependency moved, rather
    than having to find that out somewhere else.

    Returns the paths written, the summary last.
    """
    summary_path: str = os.path.join(layout.root, REVIEW_SUMMARY_FILENAME)
    written: List[str] = []
    rows: List[SummaryRow] = []

    for cfg in cfgs:
        diff_subdirs: Dict[str, str] = _latest_diff_subdirs(layout, cfg)
        weekly = WEEKLY_CFGS_BY_NAME.get(cfg)
        expected: List[str] = [
            task
            for task in (weekly.image_tasks if weekly else ())
            if tasks is None or task in tasks
        ]
        for task in expected + sorted(set(diff_subdirs) - set(expected)):
            diff_subdir: str = diff_subdirs.get(task, "")
            scores = load_scores(diff_subdir) if diff_subdir else None
            viewer_href: str = ""
            if scores is not None:
                path: str = write_viewer(
                    diff_subdir,
                    cfg,
                    task,
                    environment_diffs=environment_diffs,
                    environment_note=environment_note,
                    summary_href=os.path.relpath(summary_path, diff_subdir),
                )
                if path:
                    written.append(path)
                    viewer_href = os.path.relpath(path, layout.root)
            rows.append(
                SummaryRow(
                    package=package_for_task(task),
                    task=task,
                    cfg=cfg,
                    counts=count_severities(scores) if scores is not None else {},
                    viewer_href=viewer_href,
                    tested_at=_tested_at(task, repos or {}),
                )
            )

    # Grouped by package, in the order the cfgs were run.
    cfg_order: Dict[str, int] = {cfg: index for index, cfg in enumerate(cfgs)}
    rows.sort(key=lambda row: (row.package.lower(), row.task, cfg_order[row.cfg]))
    written.append(
        write_summary(
            summary_path,
            rows,
            os.path.basename(layout.root),
            baseline=baseline,
            environment_diffs=environment_diffs,
            environment_note=environment_note,
        )
    )
    return written


def _latest_diff_subdirs(layout: RunLayout, cfg: str) -> Dict[str, str]:
    """Map each task to its newest scored diff directory for a cfg.

    The image checker names diffs after the cfg without its "weekly_" prefix,
    and a rerun writes ``_tryN`` beside the first attempt rather than over it,
    so the newest attempt is the one to show.
    """
    case_dir: str = layout.www_case_dir(cfg, case_name_for_cfg(cfg))
    base: str = f"{_DIFF_DIR_MARKER}_{checker_name(cfg)}"
    try:
        attempts: List[str] = [
            os.path.join(case_dir, name)
            for name in sorted(os.listdir(case_dir))
            if name == base or name.startswith(f"{base}_")
        ]
    except OSError:
        return {}

    newest: Dict[str, tuple] = {}
    for attempt in attempts:
        for task in sorted(os.listdir(attempt)):
            scores_path: str = os.path.join(attempt, task, "image_scores.json")
            if not os.path.isfile(scores_path):
                continue
            modified: float = os.path.getmtime(scores_path)
            if task not in newest or modified >= newest[task][0]:
                newest[task] = (modified, os.path.join(attempt, task))
    return {task: path for task, (_, path) in newest.items()}


def _tested_at(task: str, repos: Dict[str, object]) -> str:
    """Say what a task's package was tested at, from the run's recorded repos."""
    spec = repo_for_task(task)
    entry = repos.get(spec.name) if spec is not None else None
    if not isinstance(entry, dict) or entry.get("environment_type") == "unified":
        return "E3SM-Unified"
    sha: str = str(entry.get("sha") or "")
    branch: str = str(entry.get("branch") or "")
    return f"{branch} @ {sha[:8]}" if sha else branch or "unknown"
