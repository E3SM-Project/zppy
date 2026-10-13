"""Tests for baseline-to-tested repository and package changes."""

import os
import subprocess
from pathlib import Path
from typing import Any, Dict, Tuple

from tests.cfg_suite import changes


def _git(path: Path, *args: str, env: Dict[str, str] | None = None) -> str:
    completed = subprocess.run(
        ["git", "-C", str(path), *args],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return completed.stdout.strip()


def _new_repo(tmp_path: Path) -> Tuple[Path, Path]:
    repo = tmp_path / "zppy"
    remote = tmp_path / "remote.git"
    subprocess.run(
        ["git", "init", "--bare", str(remote)], check=True, capture_output=True
    )
    subprocess.run(
        ["git", "init", "-b", "main", str(repo)], check=True, capture_output=True
    )
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "remote", "add", "upstream", str(remote))
    return repo, remote


def _commit(
    repo: Path, message: str, date: str, filename: str, content: str
) -> str:
    (repo / filename).write_text(content)
    _git(repo, "add", filename)
    env = os.environ.copy()
    env["GIT_AUTHOR_DATE"] = date
    env["GIT_COMMITTER_DATE"] = date
    _git(repo, "commit", "-m", message, env=env)
    return _git(repo, "rev-parse", "HEAD")


def _status(baseline_sha: str, tested_sha: str) -> Dict[str, object]:
    return {
        "repos": {"zppy": {"sha": tested_sha, "branch": "feature"}},
        "baseline_by_cfg_task": {
            "weekly_cfg:climo": {
                "tag": "baseline-run",
                "generated": "2021-01-01T00:00:00Z",
                "repos": {"zppy": {"sha": baseline_sha}},
            }
        },
    }


def test_collects_commit_range_and_github_links(
    tmp_path: Path, monkeypatch: Any
) -> None:
    repo, remote = _new_repo(tmp_path)
    baseline = _commit(repo, "Baseline", "2020-01-01T00:00:00Z", "base", "base")
    _git(repo, "push", "-u", "upstream", "main")
    tested = _commit(repo, "Fix issue (#42)", "2022-01-01T00:00:00Z", "fix", "fix")
    _git(repo, "push", "upstream", "main")
    monkeypatch.setattr(
        changes,
        "_preferred_remote",
        lambda _repo: (
            "upstream",
            "https://github.com/E3SM-Project/zppy.git",
            "",
        ),
    )

    result = changes.collect_changes(
        _status(baseline, tested), {"zppy": str(repo)}, str(tmp_path / "envs")
    )[0]

    assert result["count"] == 1
    assert result["range_type"] == "commit"
    assert result["commits"][0]["sha"] == tested
    assert result["commits"][0]["pr_url"] == (
        "https://github.com/E3SM-Project/zppy/pull/42"
    )
    assert result["commits"][0]["commit_url"] == (
        f"https://github.com/E3SM-Project/zppy/commit/{tested}"
    )
    assert remote.is_dir()


def test_non_ancestor_baseline_uses_merge_base(tmp_path: Path) -> None:
    repo, _remote = _new_repo(tmp_path)
    root = _commit(repo, "Root", "2020-01-01T00:00:00Z", "root", "root")
    _git(repo, "checkout", "-b", "baseline")
    baseline = _commit(
        repo, "Baseline-only", "2021-01-01T00:00:00Z", "base", "base"
    )
    _git(repo, "push", "upstream", "baseline")
    _git(repo, "checkout", "main")
    tested = _commit(
        repo, "Tested change", "2022-01-01T00:00:00Z", "tested", "tested"
    )
    _git(repo, "push", "-u", "upstream", "main")

    result = changes.collect_changes(
        _status(baseline, tested), {"zppy": str(repo)}, str(tmp_path / "envs")
    )[0]

    assert result["range_type"] == "merge-base"
    assert result["merge_base"] == root
    assert [entry["subject"] for entry in result["commits"]] == ["Tested change"]


def test_missing_baseline_sha_uses_generated_date(tmp_path: Path) -> None:
    repo, _remote = _new_repo(tmp_path)
    _commit(repo, "Before baseline", "2020-01-01T00:00:00Z", "old", "old")
    tested = _commit(repo, "After baseline", "2022-01-01T00:00:00Z", "new", "new")
    _git(repo, "push", "-u", "upstream", "main")
    status = _status("", tested)

    result = changes.collect_changes(
        status, {"zppy": str(repo)}, str(tmp_path / "envs")
    )[0]

    assert result["range_type"] == "date-based"
    assert [entry["subject"] for entry in result["commits"]] == ["After baseline"]


def test_unified_task_reports_package_version_change(tmp_path: Path) -> None:
    baseline_dir = tmp_path / "baseline"
    env_dir = tmp_path / "envs"
    baseline_envs = baseline_dir / "env_descriptions"
    baseline_envs.mkdir(parents=True)
    env_dir.mkdir()
    (baseline_envs / "ilamb.txt").write_text(
        "# Name Version Build Channel\nILAMB 1.2 py_0 conda-forge\n"
    )
    (env_dir / "ilamb.txt").write_text(
        "# Name Version Build Channel\nILAMB 2.0 py_0 conda-forge\n"
    )
    status = {
        "unified": {"packages": {"ILAMB": "2.0"}},
        "baseline_by_cfg_task": {
            "weekly_cfg:ilamb": {
                "tag": "baseline-run",
                "run_dir": str(baseline_dir),
                "repos": {},
            }
        },
    }

    result = changes.collect_changes(status, {}, str(env_dir))[0]

    assert result["range_type"] == "package-version"
    assert result["changes"] == [
        {"name": "ILAMB", "baseline": "1.2", "tested": "2.0"}
    ]
