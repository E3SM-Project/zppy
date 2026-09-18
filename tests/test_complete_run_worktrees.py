"""Tests for the detached worktrees the complete run test checks out."""

import os
from typing import Dict, List, Sequence

import pytest

from tests.complete_run import worktrees
from tests.complete_run.commands import CommandError


def test_preferred_remote_prefers_upstream(monkeypatch: pytest.MonkeyPatch) -> None:
    def run(args: Sequence[str], **kwargs) -> str:
        return "git@github.com:E3SM-Project/zppy.git"

    monkeypatch.setattr(worktrees, "run_command", run)
    assert worktrees.preferred_remote("/repo") == "upstream"


def test_preferred_remote_falls_back_to_origin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def run(args: Sequence[str], **kwargs) -> str:
        if "upstream" in args:
            raise CommandError(args, 2, "No such remote")
        return "git@github.com:me/zppy.git"

    monkeypatch.setattr(worktrees, "run_command", run)
    assert worktrees.preferred_remote("/repo") == "origin"


def test_preferred_remote_raises_when_neither_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def run(args: Sequence[str], **kwargs) -> str:
        raise CommandError(args, 2, "No such remote")

    monkeypatch.setattr(worktrees, "run_command", run)
    with pytest.raises(CommandError):
        worktrees.preferred_remote("/repo")


def test_resolve_sha_fetches_then_resolves(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: List[List[str]] = []

    def run(args: Sequence[str], **kwargs) -> str:
        calls.append(list(args))
        if "rev-parse" in args:
            return "a" * 40
        return ""

    monkeypatch.setattr(worktrees, "run_command", run)
    remote, sha = worktrees.resolve_sha("/repo", "main", remote="upstream")

    assert remote == "upstream"
    assert sha == "a" * 40
    # The fetch has to precede the resolve, or the SHA could be stale.
    assert calls == [
        ["git", "-C", "/repo", "fetch", "upstream", "main"],
        ["git", "-C", "/repo", "rev-parse", "upstream/main"],
    ]


def test_add_worktree_is_detached(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    calls: List[List[str]] = []

    def run(args: Sequence[str], **kwargs) -> str:
        calls.append(list(args))
        return ""

    monkeypatch.setattr(worktrees, "run_command", run)

    dest = str(tmp_path / "worktrees" / "zppy")
    worktrees.add_worktree("/repo", dest, "b" * 40)

    assert calls == [
        ["git", "-C", "/repo", "worktree", "add", "--detach", dest, "b" * 40]
    ]


def test_add_worktree_refuses_to_reuse_an_existing_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setattr(worktrees, "run_command", lambda args, **kwargs: "")
    dest = tmp_path / "zppy"
    dest.mkdir()

    with pytest.raises(FileExistsError, match="Refusing to reuse"):
        worktrees.add_worktree("/repo", str(dest), "c" * 40)


def test_remove_worktree_never_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def run(args: Sequence[str], **kwargs) -> str:
        raise CommandError(args, 1, "worktree is dirty")

    monkeypatch.setattr(worktrees, "run_command", run)
    # Cleanup failure must not mask the run's own outcome.
    worktrees.remove_worktree("/repo", "/scratch/worktrees/zppy")


def test_create_checkout_records_provenance(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    def run(args: Sequence[str], **kwargs) -> str:
        if "remote" in args:
            return "git@github.com:E3SM-Project/zppy.git"
        if "rev-parse" in args:
            return "d" * 40
        return ""

    monkeypatch.setattr(worktrees, "run_command", run)
    checkout = worktrees.create_checkout(
        "zppy", "/repo", "main", str(tmp_path / "worktrees")
    )

    assert checkout.sha == "d" * 40
    assert checkout.short_sha == "d" * 8
    assert checkout.branch == "main"
    assert checkout.remote == "upstream"
    assert checkout.path == os.path.join(str(tmp_path / "worktrees"), "zppy")


def test_remove_checkouts_removes_every_worktree(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    removed: Dict[str, str] = {}
    monkeypatch.setattr(
        worktrees,
        "remove_worktree",
        lambda repo, dest: removed.setdefault(repo, dest),
    )
    checkouts = [
        worktrees.Checkout(
            "zppy", "/a", "/wt/a", "1" * 40, "1" * 8, "main", "upstream"
        ),
        worktrees.Checkout("diags", "/b", "/wt/b", "2" * 40, "2" * 8, "main", "origin"),
    ]

    worktrees.remove_checkouts(checkouts)
    assert removed == {"/a": "/wt/a", "/b": "/wt/b"}


def test_an_unpushed_branch_resolves_locally(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: List[List[str]] = []

    def run(args: Sequence[str], **kwargs) -> str:
        calls.append(list(args))
        if "fetch" in args:
            raise CommandError(args, 128, "couldn't find remote ref my-branch")
        return "b" * 40

    monkeypatch.setattr(worktrees, "run_command", run)
    remote, sha = worktrees.resolve_sha("/repo", "my-branch", remote="origin")

    assert (remote, sha) == ("local", "b" * 40)
    assert calls[-1] == [
        "git",
        "-C",
        "/repo",
        "rev-parse",
        "--verify",
        "my-branch^{commit}",
    ]


def test_a_branch_on_neither_side_raises_the_fetch_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def run(args: Sequence[str], **kwargs) -> str:
        raise CommandError(args, 128, "couldn't find remote ref nope")

    monkeypatch.setattr(worktrees, "run_command", run)
    with pytest.raises(CommandError, match="remote ref nope"):
        worktrees.resolve_sha("/repo", "nope", remote="origin")
