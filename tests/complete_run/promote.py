"""Promote a complete run to a baseline, and prune the ones nobody needs.

Promotion points ``baselines/latest-<channel>`` at a run directory. It copies
nothing, so it is atomic, it takes no time regardless of how many images the run
produced, and the run that was the baseline a moment ago still exists -- rolling
back is promoting it again.

A run is only promotable if its own report says it passed and its manifest says
it came from ``main``. Both are read from the run itself rather than supplied on
the command line, so a promotion cannot claim something the run did not.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Sequence, Set, Tuple

from tests.complete_run.layout import (
    DEFAULT_CHANNEL,
    RunLayout,
    baseline_link,
    baseline_overrides,
    baselines_root,
    read_json_object,
    run_layout,
    runs_root,
    shared_root,
    write_baseline_overrides,
)
from tests.complete_run.report import JSON_FILENAME
from tests.complete_run.params import repo_for_task
from tests.complete_run.validate import _latest_diff_subdirs, load_scores
from tests.complete_run.validate import reviewable_count
from tests.complete_run.viewer import count_severities
from tests.integration.weekly_cfgs import (
    PLOTTING_TASKS,
    TASK_NAMES,
    WEEKLY_CFGS_BY_NAME,
    task_sections_for_cfg,
)

logger: logging.Logger = logging.getLogger(__name__)

# Unpromoted runs kept by `prune`, newest first. Roughly two months of weekly
# runs.
DEFAULT_KEEP: int = 8


class PromotionError(RuntimeError):
    """A run cannot be promoted as asked."""


def promote(
    root: str,
    tag: str,
    *,
    channel: str = DEFAULT_CHANNEL,
    allow_failed: bool = False,
    allow_non_main: bool = False,
    cfgs: Sequence[str] = (),
    tasks: Sequence[str] = (),
) -> str:
    """Point a channel's baseline link at one run.

    Parameters
    ----------
    allow_failed : bool
        Promote even though the run did not pass. Needed only when a maintainer
        has reviewed the differences and decided the new results are correct.
    allow_non_main : bool
        Promote a run built from something other than ``main``.

    Returns
    -------
    str
        The baseline link that now points at this run.
    """
    layout: RunLayout = run_layout(root, tag)
    if not os.path.isdir(layout.root):
        raise PromotionError(f"No such run: {layout.root}")

    link: str = baseline_link(root, channel)
    os.makedirs(baselines_root(root), exist_ok=True)
    previous: str = _current_target(link)
    partial: bool = bool(cfgs or tasks)
    if partial:
        entries = _selected_entries(layout, cfgs, tasks)
        _check_selected_entries(
            layout,
            entries,
            allow_failed=allow_failed,
            allow_non_main=allow_non_main,
        )
        overrides = baseline_overrides(root, channel)
        default_tag = os.path.basename(previous) if previous else ""
        for cfg, task in entries:
            key = f"{cfg}:{task}"
            if tag == default_tag:
                overrides.pop(key, None)
            else:
                overrides[key] = tag
        write_baseline_overrides(root, overrides, channel)
        logger.info("Promoted %s for %s cfg/task entries", tag, len(entries))
        return baseline_link(root, channel)

    _check_promotable(layout, allow_failed=allow_failed, allow_non_main=allow_non_main)

    # Build the new link beside the old one and rename over it: os.replace is
    # atomic, so a reader never sees a missing or half-written baseline.
    temporary: str = os.path.join(
        baselines_root(root), f".latest-{channel}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
    )
    relative_target: str = os.path.relpath(layout.root, baselines_root(root))
    try:
        os.symlink(relative_target, temporary)
        os.replace(temporary, link)
    finally:
        if os.path.islink(temporary):
            os.unlink(temporary)

    write_baseline_overrides(root, {}, channel)
    if previous:
        logger.info("Promoted %s to latest-%s (was %s)", tag, channel, previous)
    else:
        logger.info("Promoted %s to latest-%s", tag, channel)
    return link


def _selected_entries(
    layout: RunLayout, cfgs: Sequence[str], tasks: Sequence[str]
) -> List[Tuple[str, str]]:
    """Select only cfg/task pairs this run actually contains."""
    manifest = read_json_object(layout.manifest)
    run_cfgs: List[str] = [str(cfg) for cfg in manifest.get("cfgs", [])]
    run_tasks: Set[str] = {str(task) for task in manifest.get("tasks", [])}
    selected_cfgs: List[str] = list(cfgs) if cfgs else run_cfgs
    selected_tasks: Set[str] = set(tasks) if tasks else run_tasks
    unknown: Set[str] = selected_tasks - set(TASK_NAMES)
    if unknown:
        raise PromotionError(f"Unknown task(s): {', '.join(sorted(unknown))}")
    missing_cfgs: Set[str] = set(selected_cfgs) - set(run_cfgs)
    if missing_cfgs:
        raise PromotionError(
            f"Run {os.path.basename(layout.root)} did not include cfg(s): "
            f"{', '.join(sorted(missing_cfgs))}"
        )

    entries: List[Tuple[str, str]] = []
    for cfg in selected_cfgs:
        available = set(task_sections_for_cfg(cfg)) & run_tasks
        entries.extend((cfg, task) for task in sorted(available & selected_tasks))
    if not entries:
        raise PromotionError("The selected run contains no matching cfg/task entries.")
    return entries


def _check_selected_entries(
    layout: RunLayout,
    entries: Sequence[Tuple[str, str]],
    *,
    allow_failed: bool,
    allow_non_main: bool,
) -> None:
    """Apply promotion safety checks only to the cfg/task entries selected."""
    status = read_json_object(layout.status)
    task_status = status.get("task_status_by_cfg", {})
    task_status = task_status if isinstance(task_status, dict) else {}
    baseline_by_cfg_task = status.get("baseline_by_cfg_task", {})
    baseline_by_cfg_task = (
        baseline_by_cfg_task if isinstance(baseline_by_cfg_task, dict) else {}
    )
    manifest = read_json_object(layout.manifest)
    repositories = manifest.get("repos", {})
    repositories = repositories if isinstance(repositories, dict) else {}

    for cfg, task in entries:
        selected_status = task_status.get(cfg, {})
        selected_status = selected_status if isinstance(selected_status, dict) else {}
        result = str(selected_status.get(task, "not run"))
        if result != "OK" and not allow_failed:
            raise PromotionError(
                f"Refusing to promote {cfg}/{task}: job status is {result!r}."
            )

        image_checked: bool = (
            cfg in WEEKLY_CFGS_BY_NAME
            and task in WEEKLY_CFGS_BY_NAME[cfg].image_tasks
        )
        if task in PLOTTING_TASKS and image_checked:
            scores = _latest_diff_subdirs(layout, cfg).get(task)
            entries_for_task = load_scores(scores) if scores else None
            baseline_entry = baseline_by_cfg_task.get(f"{cfg}:{task}", {})
            baseline_entry = (
                baseline_entry if isinstance(baseline_entry, dict) else {}
            )
            first_comparison = (
                baseline_entry.get("state") == "not-compared"
                and baseline_entry.get("reason") == "new cfg"
            )
            if entries_for_task is None and not allow_failed and not first_comparison:
                raise PromotionError(
                    f"Refusing to promote {cfg}/{task}: no image comparison was recorded."
                )
            if (
                entries_for_task is not None
                and reviewable_count(count_severities(entries_for_task))
                and not allow_failed
            ):
                raise PromotionError(
                    f"Refusing to promote {cfg}/{task}: images need review."
                )

        spec = repo_for_task(task)
        repo_entry = repositories.get(spec.name, {}) if spec else {}
        if isinstance(repo_entry, dict):
            branch = str(repo_entry.get("branch") or "")
            if branch and branch not in ("main", "master", "develop") and not allow_non_main:
                raise PromotionError(
                    f"Refusing to promote {cfg}/{task} from feature branch "
                    f"{branch!r}; pass --allow-non-main after review."
                )


def show(root: str, channel: str = DEFAULT_CHANNEL) -> Dict[str, Any]:
    """Describe the channel default and every cfg/task override."""
    try:
        default = baseline_run_for(root, "", "", channel)
    except FileNotFoundError as error:
        raise PromotionError(str(error)) from error
    overrides = baseline_overrides(root, channel)
    tags: Set[str] = {os.path.basename(default.root), *overrides.values()}
    described = {tag: _describe_run(root, tag) for tag in sorted(tags)}
    manifest = read_json_object(default.manifest)
    return {
        "channel": channel,
        "link": baseline_link(root, channel),
        "run": default.root,
        "tag": os.path.basename(default.root),
        "exists": os.path.isdir(default.root),
        "machine": manifest.get("machine"),
        "generated": manifest.get("generated"),
        "repos": manifest.get("repos", {}),
        "unified": manifest.get("unified", {}),
        "default_run": described[os.path.basename(default.root)],
        "overrides": {
            key: described[tag] for key, tag in sorted(overrides.items())
        },
        "runs": described,
    }


def _describe_run(root: str, tag: str) -> Dict[str, Any]:
    """Describe a referenced run, including commit dates and age."""
    path = os.path.join(runs_root(root), tag)
    manifest = read_json_object(RunLayout(path).manifest)
    repos: Dict[str, Any] = {}
    for name, entry in manifest.get("repos", {}).items():
        if not isinstance(entry, dict):
            continue
        recorded = dict(entry)
        sha_date = str(recorded.get("sha_date") or "")
        recorded["age_days"] = _age_days(sha_date)
        repos[str(name)] = recorded
    return {
        "tag": tag,
        "run": path,
        "exists": os.path.isdir(path),
        "generated": manifest.get("generated", ""),
        "repos": repos,
    }


def _age_days(iso_date: str) -> int | None:
    if not iso_date:
        return None
    try:
        parsed = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return max((datetime.now(timezone.utc) - parsed).days, 0)


def promoted_tags(root: str) -> List[str]:
    """Return the tag of every run any channel points at."""
    baselines: str = baselines_root(root)
    if not os.path.isdir(baselines):
        return []

    tags: List[str] = []
    for name in sorted(os.listdir(baselines)):
        link: str = os.path.join(baselines, name)
        if os.path.islink(link):
            tags.append(os.path.basename(os.path.realpath(link)))
        elif name.endswith(".overrides.json"):
            channel = name[: -len(".overrides.json")]
            tags.extend(baseline_overrides(root, channel).values())

    return sorted(set(tags))


def prune(
    root: str,
    *,
    keep: int = DEFAULT_KEEP,
    dry_run: bool = True,
    older_than: int | None = None,
) -> List[str]:
    """Delete old runs, never one a channel points at.

    Parameters
    ----------
    keep : int
        Unpromoted runs to retain, newest first.
    dry_run : bool
        Report what would be deleted without deleting it. The default, because
        a run directory holds tens of thousands of images.

    Returns
    -------
    List[str]
        The tags deleted, or that would be deleted.
    """
    runs: str = runs_root(root)
    if not os.path.isdir(runs):
        return []

    protected: set = set(promoted_tags(root))
    candidates: List[str] = [
        name
        for name in os.listdir(runs)
        if os.path.isdir(os.path.join(runs, name)) and name not in protected
    ]
    # Tags lead with a date stamp, so newest last by name.
    candidates.sort()
    doomed: List[str] = candidates[: max(len(candidates) - keep, 0)]
    if older_than is not None:
        threshold = datetime.now(timezone.utc).timestamp() - older_than * 86400
        doomed = [tag for tag in doomed if _run_timestamp(root, tag) <= threshold]

    for tag in doomed:
        path: str = os.path.join(runs, tag)
        if dry_run:
            logger.info("Would delete %s", path)
            continue
        logger.info("Deleting %s", path)
        shutil.rmtree(path, ignore_errors=True)

    return doomed


def _run_timestamp(root: str, tag: str) -> float:
    """Return the production timestamp of a run, falling back to its tag."""
    manifest = read_json_object(RunLayout(os.path.join(runs_root(root), tag)).manifest)
    generated = str(manifest.get("generated") or "")
    if generated:
        try:
            parsed = datetime.fromisoformat(generated.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.timestamp()
        except ValueError:
            pass
    try:
        return datetime.strptime(tag[:8], "%Y%m%d").replace(
            tzinfo=timezone.utc
        ).timestamp()
    except ValueError:
        return os.path.getmtime(os.path.join(runs_root(root), tag))


def _check_promotable(
    layout: RunLayout, *, allow_failed: bool, allow_non_main: bool
) -> None:
    """Refuse to promote a run that does not vouch for itself."""
    report_path: str = os.path.join(layout.root, JSON_FILENAME)
    report: Dict[str, Any] = read_json_object(report_path)
    if not report:
        raise PromotionError(
            f"No report at {report_path}. Only a finished run can be promoted."
        )

    status: str = str(report.get("status", "unknown"))
    if status != "passed" and not allow_failed:
        raise PromotionError(
            f"Refusing to promote a run whose status is {status!r}. Review the "
            "differences first; pass --allow-failed once you have decided the "
            "new results are correct."
        )

    manifest: Dict[str, Any] = read_json_object(layout.manifest)
    branches: List[str] = sorted(
        {
            str(entry.get("branch"))
            for entry in manifest.get("repos", {}).values()
            if isinstance(entry, dict) and entry.get("branch")
        }
    )
    non_main: List[str] = [
        branch for branch in branches if branch not in ("main", "master", "develop")
    ]
    if non_main and not allow_non_main:
        raise PromotionError(
            "Refusing to promote a run built from a feature branch "
            f"({', '.join(non_main)}). Merge it first, or pass --allow-non-main."
        )


def _current_target(link: str) -> str:
    """Return the tag a link points at, or an empty string."""
    if not os.path.islink(link):
        return ""
    return os.path.basename(os.path.realpath(link))


def main(argv: Sequence[str] | None = None) -> int:
    """Promote, inspect, or prune baselines."""
    args = _build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")
    root: str = shared_root(args.machine, args.shared_root)

    try:
        if args.command == "show":
            print(json.dumps(show(root, args.channel), indent=2, sort_keys=True))
        elif args.command == "prune":
            doomed = prune(
                root,
                keep=args.keep,
                dry_run=not args.delete,
                older_than=args.older_than,
            )
            if not doomed:
                print("Nothing to prune.")
            elif args.delete:
                print(f"Deleted {len(doomed)} runs.")
            else:
                print(
                    f"Would delete {len(doomed)} runs; rerun with --delete:\n  "
                    + "\n  ".join(doomed)
                )
        else:
            link = promote(
                root,
                args.tag,
                channel=args.channel,
                allow_failed=args.allow_failed,
                allow_non_main=args.allow_non_main,
                cfgs=args.cfgs,
                tasks=args.tasks,
            )
            print(f"{link} -> {args.tag}")
    except PromotionError as error:
        logger.error("%s", error)
        return 1

    return 0


def _build_parser() -> argparse.ArgumentParser:
    """Build the promotion CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--machine", required=True)
    parser.add_argument("--shared-root", default="")
    subparsers = parser.add_subparsers(dest="command", required=True)

    promote_parser = subparsers.add_parser("run", help="Promote a run.")
    promote_parser.add_argument("tag", help="The run to promote.")
    promote_parser.add_argument("--channel", default=DEFAULT_CHANNEL)
    promote_parser.add_argument(
        "--cfg", dest="cfgs", action="append", default=[], help="Promote only this cfg."
    )
    promote_parser.add_argument(
        "--task",
        dest="tasks",
        action="append",
        choices=TASK_NAMES,
        default=[],
        help="Promote only this task.",
    )
    promote_parser.add_argument(
        "--allow-failed",
        action="store_true",
        help="Promote a run that did not pass, after reviewing its differences.",
    )
    promote_parser.add_argument(
        "--allow-non-main",
        action="store_true",
        help="Promote a run built from a feature branch.",
    )

    show_parser = subparsers.add_parser("show", help="Describe a baseline.")
    show_parser.add_argument("--channel", default=DEFAULT_CHANNEL)

    prune_parser = subparsers.add_parser("prune", help="Delete old runs.")
    prune_parser.add_argument("--keep", type=int, default=DEFAULT_KEEP)
    prune_parser.add_argument(
        "--older-than",
        type=int,
        default=None,
        metavar="DAYS",
        help="Among runs beyond --keep, prune only those older than this many days.",
    )
    prune_parser.add_argument(
        "--delete", action="store_true", help="Actually delete; otherwise dry run."
    )
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
