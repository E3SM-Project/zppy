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
from typing import Any, Dict, List, Sequence

from tests.complete_run.layout import (
    DEFAULT_CHANNEL,
    RunLayout,
    baseline_link,
    baselines_root,
    read_json_object,
    run_layout,
    runs_root,
    shared_root,
)
from tests.complete_run.report import JSON_FILENAME

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

    _check_promotable(layout, allow_failed=allow_failed, allow_non_main=allow_non_main)

    link: str = baseline_link(root, channel)
    os.makedirs(baselines_root(root), exist_ok=True)
    previous: str = _current_target(link)

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

    if previous:
        logger.info("Promoted %s to latest-%s (was %s)", tag, channel, previous)
    else:
        logger.info("Promoted %s to latest-%s", tag, channel)
    return link


def show(root: str, channel: str = DEFAULT_CHANNEL) -> Dict[str, Any]:
    """Describe the run currently promoted to a channel."""
    link: str = baseline_link(root, channel)
    if not os.path.islink(link):
        raise PromotionError(f"No baseline is promoted for channel {channel!r}.")

    target: str = os.path.realpath(link)
    layout = RunLayout(target)
    manifest: Dict[str, Any] = read_json_object(layout.manifest)
    return {
        "channel": channel,
        "link": link,
        "run": target,
        "tag": os.path.basename(target),
        "exists": os.path.isdir(target),
        "machine": manifest.get("machine"),
        "generated": manifest.get("generated"),
        "repos": manifest.get("repos", {}),
    }


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
    return tags


def prune(root: str, *, keep: int = DEFAULT_KEEP, dry_run: bool = True) -> List[str]:
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

    for tag in doomed:
        path: str = os.path.join(runs, tag)
        if dry_run:
            logger.info("Would delete %s", path)
            continue
        logger.info("Deleting %s", path)
        shutil.rmtree(path, ignore_errors=True)

    return doomed


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
            doomed = prune(root, keep=args.keep, dry_run=not args.delete)
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
        "--delete", action="store_true", help="Actually delete; otherwise dry run."
    )
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
