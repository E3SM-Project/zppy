"""Changes between the baseline commits and the revisions tested by a run."""

from __future__ import annotations

import os
import re
import subprocess
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

from tests.cfg_suite.envdiff import parse_package_list
from tests.cfg_suite.params import repo_for_task
from tests.cfg_suite.provenance import read_generated_date

_PR_NUMBER = re.compile(r"\(#(\d+)\)")
_UNIFIED_TASK_PACKAGES = {"ilamb": "ILAMB", "livvkit": "LIVVkit"}


def collect_changes(
    status: Dict[str, Any], repo_paths: Dict[str, str], env_descriptions: str
) -> List[Dict[str, Any]]:
    """Collect commit or Unified-package changes for every selected baseline."""
    tested_repos = _mapping(status.get("repos"))
    selections = _mapping(status.get("baseline_by_cfg_task"))
    groups: Dict[Tuple[str, str, str, str, str], Dict[str, Any]] = {}
    unified_changes: List[Dict[str, Any]] = []

    for selection_key, raw_selection in sorted(selections.items()):
        cfg, separator, task = selection_key.partition(":")
        if not separator:
            continue
        selected = _mapping(raw_selection)
        if selected.get("state") == "not-compared":
            continue
        baseline_repos = _mapping(selected.get("repos"))

        if task in _UNIFIED_TASK_PACKAGES:
            item = _unified_package_change(
                task,
                cfg,
                selected,
                baseline_repos,
                _mapping(status.get("unified")),
                env_descriptions,
            )
            if item:
                unified_changes.append(item)
            continue

        spec = repo_for_task(task)
        if spec is None:
            continue
        repo = spec.name
        tested = _mapping(tested_repos.get(repo))
        tested_sha = str(tested.get("sha") or "")
        if not tested_sha:
            continue
        baseline_repo = _mapping(baseline_repos.get(repo))
        baseline_sha = str(baseline_repo.get("sha") or "")
        baseline_tag = str(selected.get("tag") or "unknown")
        generated = str(selected.get("generated") or "")
        if not baseline_sha:
            generated = _baseline_task_date(
                str(selected.get("run_dir") or ""), task
            ) or generated
        # zppy-interfaces baselines can intentionally vary by task. Other tasks
        # share one repository section when their baseline revision is the same.
        task_group = task if repo == "zppy_interfaces" else repo
        group_key = (repo, task_group, baseline_tag, baseline_sha, generated)
        group = groups.setdefault(
            group_key,
            {
                "repo": repo,
                "tasks": [],
                "cfgs": [],
                "baseline": {
                    "tag": baseline_tag,
                    "generated": generated,
                    "commit": baseline_sha,
                },
                "tested": {
                    "branch": str(tested.get("branch") or "unknown"),
                    "commit": tested_sha,
                },
                "source_repo": repo_paths.get(repo, ""),
                "default_branch": spec.default_branch,
            },
        )
        if task not in group["tasks"]:
            group["tasks"].append(task)
        if cfg not in group["cfgs"]:
            group["cfgs"].append(cfg)

    changes: List[Dict[str, Any]] = []
    for group in groups.values():
        changes.append(_collect_repository_log(group))
    changes.extend(unified_changes)
    changes.sort(key=lambda item: (str(item.get("repo", "")), str(item.get("task", ""))))

    if _mapping(tested_repos.get("zppy")).get("environment_type") == "unified":
        status["changes_since_baseline_note"] = (
            "The listed zppy commits describe the worktree under test; they may "
            "not be included in the E3SM-Unified release used to run zppy."
        )
    return changes


def _collect_repository_log(group: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch and list first-parent commits for one repository baseline."""
    source_repo = str(group["source_repo"])
    baseline = _mapping(group.get("baseline"))
    tested = _mapping(group.get("tested"))
    result: Dict[str, Any] = {
        **group,
        "count": 0,
        "range_type": "commit",
        "merge_base": "",
        "commits": [],
        "error": "",
    }
    if not source_repo or not os.path.isdir(source_repo):
        result["error"] = f"Repository clone unavailable: {source_repo or 'unknown'}."
        return result

    remote, remote_url, remote_error = _preferred_remote(source_repo)
    if not remote:
        result["error"] = remote_error
        return result
    result["repository_url"] = _github_repository_url(remote_url)
    fetch = _git(source_repo, "fetch", "--quiet", "--no-tags", remote)
    fetch_warning = ""
    if fetch[0] != 0:
        fetch_warning = f"Could not fetch {remote}: {fetch[2].strip()}"

    tested_sha = str(tested.get("commit") or "")
    baseline_sha = str(baseline.get("commit") or "")
    if baseline_sha:
        if _git(source_repo, "cat-file", "-e", f"{baseline_sha}^{{commit}}")[0] != 0:
            _git(source_repo, "fetch", "--quiet", "--no-tags", remote, baseline_sha)
        if _git(source_repo, "cat-file", "-e", f"{baseline_sha}^{{commit}}")[0] != 0:
            result["error"] = (
                f"Baseline commit {baseline_sha} is unavailable in {source_repo}."
            )
            if fetch_warning:
                result["error"] += f" {fetch_warning}"
            return result

        ancestor = _git(
            source_repo,
            "merge-base",
            "--is-ancestor",
            baseline_sha,
            tested_sha,
        )
        if ancestor[0] == 0:
            start = baseline_sha
        else:
            merge_base = _git(source_repo, "merge-base", baseline_sha, tested_sha)
            if merge_base[0] != 0:
                result["error"] = (
                    f"No merge-base exists between {baseline_sha} and {tested_sha}."
                )
                return result
            start = merge_base[1].strip()
            result["range_type"] = "merge-base"
            result["merge_base"] = start
    else:
        generated = str(baseline.get("generated") or "")
        date = generated[:10]
        if not date:
            result["error"] = (
                "Baseline manifest has no repository commit and its task "
                "environment description has no Generated date."
            )
            return result
        branch_ref = f"{remote}/{group['default_branch']}"
        if _git(source_repo, "rev-parse", "--verify", branch_ref)[0] != 0:
            branch_ref = str(group["default_branch"])
        if _git(source_repo, "rev-parse", "--verify", branch_ref)[0] != 0:
            result["error"] = f"Default branch {branch_ref} is unavailable."
            return result
        result["range_type"] = "date-based"
        log = _git(
            source_repo,
            "log",
            "--first-parent",
            f"--since={date}",
            "--format=%H|%cs|%s",
            branch_ref,
        )
        start = ""
        if log[0] != 0:
            result["error"] = log[2].strip() or "Could not read the default branch log."
            return result
        result["commits"] = _parse_log(
            log[1], str(result.get("repository_url") or "")
        )
        result["count"] = len(result["commits"])
        if fetch_warning:
            result["warning"] = fetch_warning
        return result

    log = _git(
        source_repo,
        "log",
        "--first-parent",
        "--format=%H|%cs|%s",
        f"{start}..{tested_sha}",
    )
    if log[0] != 0:
        result["error"] = log[2].strip() or "Could not read the repository commit log."
        return result
    result["commits"] = _parse_log(log[1], str(result.get("repository_url") or ""))
    result["count"] = len(result["commits"])
    if result["range_type"] == "merge-base":
        result["note"] = (
            "The baseline commit is not an ancestor of the tested commit; "
            "the log starts at their merge-base."
        )
    if fetch_warning:
        result["warning"] = fetch_warning
    return result


def _parse_log(output: str, repository_url: str) -> List[Dict[str, str]]:
    commits: List[Dict[str, str]] = []
    for line in output.splitlines():
        sha, separator, rest = line.partition("|")
        date, separator, subject = rest.partition("|")
        if not separator:
            continue
        match = _PR_NUMBER.search(subject)
        pr_url = f"{repository_url}/pull/{match.group(1)}" if match else ""
        commits.append(
            {
                "sha": sha,
                "date": date,
                "subject": subject,
                "commit_url": f"{repository_url}/commit/{sha}" if repository_url else "",
                "pr_url": pr_url,
                "url": pr_url or (f"{repository_url}/commit/{sha}" if repository_url else ""),
            }
        )
    return commits


def _unified_package_change(
    task: str,
    cfg: str,
    selection: Dict[str, Any],
    baseline_repos: Dict[str, Any],
    tested_unified: Dict[str, Any],
    env_descriptions: str,
) -> Dict[str, Any] | None:
    baseline_repo = _mapping(baseline_repos.get(task))
    package = str(baseline_repo.get("package") or _UNIFIED_TASK_PACKAGES[task])
    baseline_version = str(baseline_repo.get("package_version") or "")
    if not baseline_version:
        baseline_version = _package_version(
            os.path.join(
                str(selection.get("run_dir") or ""),
                "env_descriptions",
                f"{task}.txt",
            ),
            package,
        )
    tested_version = _package_from_mapping(
        _mapping(tested_unified.get("packages")), package
    ) or _package_version(os.path.join(env_descriptions, f"{task}.txt"), package)
    if not baseline_version and not tested_version:
        return {
            "repo": task,
            "task": task,
            "cfgs": [cfg],
            "baseline": {
                "tag": str(selection.get("tag") or "unknown"),
                "generated": str(selection.get("generated") or ""),
            },
            "tested": {"branch": "E3SM-Unified", "commit": ""},
            "range_type": "package-version",
            "count": 0,
            "changes": [],
            "error": f"Could not find package version for {package}.",
        }
    package_changes = (
        [{"name": package, "baseline": baseline_version, "tested": tested_version}]
        if baseline_version != tested_version
        else []
    )
    return {
        "repo": task,
        "task": task,
        "cfgs": [cfg],
        "baseline": {
            "tag": str(selection.get("tag") or "unknown"),
            "generated": str(selection.get("generated") or ""),
        },
        "tested": {"branch": "E3SM-Unified", "commit": ""},
        "range_type": "package-version",
        "count": len(package_changes),
        "changes": package_changes,
        "error": "",
    }


def _baseline_task_date(baseline_run: str, task: str) -> str:
    base_path = os.path.join(baseline_run, "env_descriptions", f"{task}.txt")
    return read_generated_date(base_path) or ""


def _package_version(path: str, package: str) -> str:
    if not os.path.isfile(path):
        return ""
    try:
        with open(path, encoding="utf-8") as stream:
            packages = parse_package_list(stream.read())
    except OSError:
        return ""
    return _package_from_mapping(packages, package)


def _package_from_mapping(packages: Dict[str, Any], package: str) -> str:
    target = package.lower().replace("-", "_")
    for name, version in packages.items():
        if str(name).lower().replace("-", "_").removeprefix("pip:") == target:
            return str(version)
    return ""


def _preferred_remote(repo: str) -> Tuple[str, str, str]:
    for remote in ("upstream", "origin"):
        code, url, _ = _git(repo, "remote", "get-url", remote)
        if code == 0 and url.strip():
            return remote, url.strip(), ""
    return "", "", f"No upstream or origin remote is configured for {repo}."


def _github_repository_url(remote_url: str) -> str:
    if remote_url.startswith("git@github.com:"):
        path = remote_url.removeprefix("git@github.com:")
    else:
        parsed = urlparse(remote_url)
        if parsed.hostname != "github.com":
            return ""
        path = parsed.path.lstrip("/")
    return "https://github.com/" + path.removesuffix(".git").strip("/")


def _git(repo: str, *args: str) -> Tuple[int, str, str]:
    environment = os.environ.copy()
    environment["GIT_TERMINAL_PROMPT"] = "0"
    try:
        completed = subprocess.run(
            ["git", "-C", repo, *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            env=environment,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as error:
        return -1, "", str(error)
    return completed.returncode, completed.stdout, completed.stderr


def _mapping(value: object) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}
