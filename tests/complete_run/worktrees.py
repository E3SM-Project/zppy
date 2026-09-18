"""Detached per-SHA git worktrees for the complete run test.

A complete run must never alter a developer's checkout, and must test one
immutable revision even if the branch moves while jobs are queued. Both follow
from resolving a branch to a SHA once and checking that SHA out into a throwaway
detached worktree.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import List

from tests.complete_run.commands import CommandError, run_command

logger: logging.Logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Checkout:
    """One repository checked out at one revision for one run."""

    name: str
    # The developer's clone, used only as a source of objects.
    source_repo: str
    # The detached worktree the run actually uses.
    path: str
    sha: str
    short_sha: str
    branch: str
    remote: str


def preferred_remote(repo: str) -> str:
    """Return the remote holding the official branches.

    Prefers ``upstream``, since a developer's ``origin`` is usually their fork.
    """
    for remote in ("upstream", "origin"):
        try:
            run_command(["git", "-C", repo, "remote", "get-url", remote])
        except CommandError:
            continue
        return remote

    raise CommandError(
        ["git", "-C", repo, "remote"],
        1,
        f"No 'upstream' or 'origin' remote in {repo}.",
    )


# Recorded as the "remote" of a branch that exists only in the local clone.
LOCAL_REMOTE: str = "local"


def resolve_sha(repo: str, branch: str, remote: str | None = None) -> tuple[str, str]:
    """Fetch a branch and resolve it to an immutable SHA.

    The remote's branch wins whenever it exists, so an official branch such as
    ``main`` can never come from a stale local copy. Only a branch the remote
    does not have -- work not yet pushed -- is resolved from the local clone,
    which is how an unpushed branch is tested. Uncommitted changes are never
    included either way: a worktree holds exactly one commit.

    Returns the remote used (``"local"`` for a local branch) and the full SHA.
    """
    resolved_remote: str = remote or preferred_remote(repo)
    try:
        run_command(["git", "-C", repo, "fetch", resolved_remote, branch])
    except CommandError as fetch_error:
        try:
            sha: str = run_command(
                ["git", "-C", repo, "rev-parse", "--verify", f"{branch}^{{commit}}"]
            )
        except CommandError:
            raise fetch_error from None
        logger.warning(
            "%s: %s is not on %s; testing the local branch at %s",
            repo,
            branch,
            resolved_remote,
            sha,
        )
        return LOCAL_REMOTE, sha

    sha = run_command(["git", "-C", repo, "rev-parse", f"{resolved_remote}/{branch}"])
    logger.info("%s: %s/%s resolves to %s", repo, resolved_remote, branch, sha)
    return resolved_remote, sha


def add_worktree(repo: str, dest: str, sha: str) -> str:
    """Create a detached worktree of ``sha`` at ``dest``.

    Raises
    ------
    FileExistsError
        If ``dest`` already exists. A run never reuses a worktree, so an
        existing one means a previous run was interrupted and its state should
        be reviewed rather than silently overwritten.
    """
    if os.path.exists(dest):
        raise FileExistsError(
            "Refusing to reuse an existing worktree; review it or remove it "
            f"before rerunning: {dest}"
        )

    os.makedirs(os.path.dirname(dest), exist_ok=True)
    run_command(["git", "-C", repo, "worktree", "add", "--detach", dest, sha])
    logger.info("Created worktree %s at %s", dest, sha[:12])
    return dest


def remove_worktree(repo: str, dest: str) -> None:
    """Remove a worktree and prune its administrative entry.

    Never raises: cleanup failure must not mask the run's own outcome. A
    worktree left behind is visible in ``git worktree list``.
    """
    try:
        run_command(["git", "-C", repo, "worktree", "remove", "--force", dest])
    except CommandError as error:
        logger.warning("Could not remove worktree %s: %s", dest, error)
    try:
        run_command(["git", "-C", repo, "worktree", "prune"])
    except CommandError as error:
        logger.warning("Could not prune worktrees in %s: %s", repo, error)


def create_checkout(name: str, repo: str, branch: str, worktree_root: str) -> Checkout:
    """Resolve a branch to a SHA and check it out into a detached worktree."""
    remote, sha = resolve_sha(repo, branch)
    short_sha: str = sha[:8]
    path: str = os.path.join(worktree_root, name)
    add_worktree(repo, path, sha)
    return Checkout(
        name=name,
        source_repo=repo,
        path=path,
        sha=sha,
        short_sha=short_sha,
        branch=branch,
        remote=remote,
    )


def remove_checkouts(checkouts: List[Checkout]) -> None:
    """Remove every worktree created for a run."""
    for checkout in checkouts:
        remove_worktree(checkout.source_repo, checkout.path)
