"""Where a complete run's results live, and which one is the baseline.

Every run writes into its own immutable directory under a shared, group-writable
root. Promotion does not copy anything: it points ``baselines/latest-<channel>``
at one of those run directories.

::

    <shared root>/
      runs/<tag>/                       one run, never modified after it finishes
        manifest.json  status.json
        complete-run-report.{json,md}
        env_descriptions/               one per task
        www/                            zppy www output -- the image baseline
        image_lists/                    image_list_<cfg>.txt
        settings/                       small bash/settings baselines
        image_check/<cfg>/<task>/       diffs and index.html
      baselines/
        latest-main -> ../runs/<tag>

Because the baseline is a run directory rather than a copy of one, promoting is
atomic and reversible, and the previous baseline still exists afterward.

A run's intermediate data -- zppy's post-processing output (climatologies, time
series, job scripts and logs) and the worktrees -- is large and worthless once
the run is validated, so it goes to per-user scratch instead::

    <scratch>/zppy_complete_run/<tag>/
      output/                           zppy post/scripts output
      worktrees/<repo>/                 detached checkouts

Everything a baseline needs from it is copied into the run directory during
validation.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional

from tests.complete_run.params import case_name_for_cfg
from tests.integration.weekly_cfgs import TASK_NAMES

# Runs write their zppy output under a fixed segment rather than a per-run
# unique_id: the run directory already carries the tag, so repeating it in the
# path below would be redundant.
RUN_SEGMENT: str = "run"

RUNS_DIRNAME: str = "runs"
BASELINES_DIRNAME: str = "baselines"
DEFAULT_CHANNEL: str = "main"

# Environment variable that overrides the shared root, for testing the
# machinery without writing into the real one.
SHARED_ROOT_ENV_VAR: str = "ZPPY_COMPLETE_RUN_ROOT"

# Group-writable and served by each machine's web portal, so reports and image
# diffs have a URL without being copied anywhere.
DEFAULT_SHARED_ROOTS: Dict[str, Optional[str]] = {
    "chrysalis": "/lcrc/group/e3sm/public_html/zppy_complete_run",
    "pm-cpu": "/global/cfs/cdirs/e3sm/www/zppy_complete_run",
    "perlmutter": "/global/cfs/cdirs/e3sm/www/zppy_complete_run",
    # Compy does not grant write access to /compyfs/www, so it has no shared
    # web-served location to default to. A maintainer must provision one and
    # pass it explicitly.
    "compy": None,
}

# The small baselines, by the name each test looks for.
SETTINGS_BASELINE_NAMES: tuple[str, ...] = (
    "expected_bash_files",
    "test_defaults_expected_files",
    "test_campaign_cryosphere_expected_files",
    "test_campaign_cryosphere_override_expected_files",
    "test_campaign_high_res_v1_expected_files",
    "test_campaign_none_expected_files",
    "test_campaign_water_cycle_expected_files",
    "test_campaign_water_cycle_override_expected_files",
    "expected_bundles",
)


def shared_root(machine: str, override: str = "") -> str:
    """Return the shared root for a machine.

    Raises
    ------
    ValueError
        If the machine has no default and none was supplied. Falling back to a
        personal directory would put results somewhere only one person can
        promote from, which is the situation this layout exists to end.
    """
    if override:
        return override.rstrip("/")

    from_environment: str = os.environ.get(SHARED_ROOT_ENV_VAR, "")
    if from_environment:
        return from_environment.rstrip("/")

    default: Optional[str] = DEFAULT_SHARED_ROOTS.get(machine)
    if default is None:
        raise ValueError(
            f"No shared complete-run root is defined for machine={machine!r}. "
            "Provision a group-writable directory and pass --shared-root "
            f"(or set {SHARED_ROOT_ENV_VAR})."
        )
    return default


def runs_root(root: str) -> str:
    """Return the directory holding every run."""
    return os.path.join(root, RUNS_DIRNAME)


def baselines_root(root: str) -> str:
    """Return the directory holding the baseline links."""
    return os.path.join(root, BASELINES_DIRNAME)


def baseline_link(root: str, channel: str = DEFAULT_CHANNEL) -> str:
    """Return the path of one channel's baseline link."""
    return os.path.join(baselines_root(root), f"latest-{channel}")


def baseline_overrides_path(root: str, channel: str = DEFAULT_CHANNEL) -> str:
    """Return the per-cfg/task override file for a baseline channel."""
    return os.path.join(baselines_root(root), f"latest-{channel}.overrides.json")


def baseline_overrides(root: str, channel: str = DEFAULT_CHANNEL) -> Dict[str, str]:
    """Read a channel's task overrides, ignoring malformed entries."""
    recorded: Dict[str, Any] = read_json_object(
        baseline_overrides_path(root, channel)
    )
    return {
        str(key): str(tag)
        for key, tag in recorded.items()
        if isinstance(key, str) and isinstance(tag, str) and tag
    }


def write_baseline_overrides(
    root: str, overrides: Mapping[str, str], channel: str = DEFAULT_CHANNEL
) -> str:
    """Atomically replace one channel's per-cfg/task overrides."""
    path: str = baseline_overrides_path(root, channel)
    os.makedirs(baselines_root(root), exist_ok=True)
    temporary: str = f"{path}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
    try:
        write_json(temporary, dict(overrides))
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)
    return path


def baseline_run_for(
    root: str,
    cfg: str,
    task: str,
    channel: str = DEFAULT_CHANNEL,
    requested: Mapping[str, str] | None = None,
) -> "RunLayout":
    """Resolve the baseline run for one cfg/task from overrides or channel default.

    ``requested`` accepts task-wide keys and exact ``cfg:task`` keys. Requested
    selectors take precedence over channel overrides; within each layer an exact
    cfg/task selection takes precedence over a task-wide selection.
    """
    requested = requested or {}
    stored: Dict[str, str] = baseline_overrides(root, channel)
    exact: str = f"{cfg}:{task}"
    tag: str = (
        requested.get(exact)
        or requested.get(task)
        or stored.get(exact)
        or stored.get(task)
        or ""
    )
    if not tag:
        return resolve_baseline(root, channel)

    if os.path.isabs(tag):
        if not os.path.isdir(tag):
            raise FileNotFoundError(f"Baseline run directory does not exist: {tag}")
        return RunLayout(os.path.realpath(tag))
    if os.path.basename(tag) != tag or tag in {".", ".."}:
        raise ValueError(f"Baseline override must be a run tag, got {tag!r}")
    selected: RunLayout = run_layout(root, tag)
    if not os.path.isdir(selected.root):
        raise FileNotFoundError(
            f"Baseline run {tag!r} for {cfg}/{task} does not exist: {selected.root}"
        )
    return selected


def parse_baseline_selections(values: list[str]) -> Dict[str, str]:
    """Parse ``TASK=TAG`` and ``CFG:TASK=TAG`` baseline selections."""
    selections: Dict[str, str] = {}
    for value in values:
        selector, separator, tag = value.partition("=")
        selector, tag = selector.strip(), tag.strip()
        if not separator or not selector or not tag:
            raise ValueError(
                f"Invalid baseline selection {value!r}; expected TASK=TAG or CFG:TASK=TAG"
            )
        if ":" in selector:
            cfg, task = selector.split(":", 1)
            if not cfg or task not in TASK_NAMES:
                raise ValueError(f"Invalid baseline selector {selector!r}")
            key = f"{cfg}:{task}"
        else:
            if selector not in TASK_NAMES:
                raise ValueError(f"Unknown baseline task {selector!r}")
            key = selector
        if key in selections:
            raise ValueError(f"Baseline selector specified more than once: {key}")
        selections[key] = tag
    return selections


@dataclass(frozen=True)
class RunLayout:
    """The directories of one run.

    ``output_root`` is where zppy's post-processing output goes. A complete run
    points it at scratch; left empty, it is ``<root>/output``.
    """

    root: str
    output_root: str = ""

    @property
    def manifest(self) -> str:
        return os.path.join(self.root, "manifest.json")

    @property
    def status(self) -> str:
        return os.path.join(self.root, "status.json")

    @property
    def env_descriptions(self) -> str:
        """Human-readable descriptions, one per task."""
        return os.path.join(self.root, "env_descriptions")

    @property
    def environments(self) -> str:
        """Reconstructible ``conda env export`` files, one per repository.

        These are what makes a run reproducible: `conda list` output describes
        an environment but cannot rebuild one, so a later run that wants to
        hold dependencies fixed builds from these instead.
        """
        return os.path.join(self.root, "environments")

    def environment_file(self, repo_name: str) -> str:
        """Return one repository's exported environment."""
        return os.path.join(self.environments, f"{repo_name}.yml")

    @property
    def output(self) -> str:
        """zppy's post/scripts output, as `user_output` expands to."""
        return self.output_root or os.path.join(self.root, "output")

    @property
    def www(self) -> str:
        """zppy's www output, as `user_www` expands to. This is the baseline."""
        return os.path.join(self.root, "www")

    @property
    def image_lists(self) -> str:
        return os.path.join(self.root, "image_lists")

    @property
    def settings(self) -> str:
        return os.path.join(self.root, "settings")

    @property
    def image_check(self) -> str:
        return os.path.join(self.root, "image_check")

    def image_list(self, cfg: str) -> str:
        """Return the list of images a cfg is expected to produce."""
        return os.path.join(self.image_lists, f"image_list_{cfg}.txt")

    def settings_baseline(self, name: str) -> str:
        """Return one small baseline directory."""
        return os.path.join(self.settings, name)

    def www_case_dir(self, cfg: str, case: str) -> str:
        """Return a cfg's plot directory: the image baseline for that cfg.

        ``cfg`` is the full template name, which already begins with "weekly_"
        -- so the directory is ``zppy_<cfg>_www``, matching
        :meth:`status_dir`. Note that
        ``image_checker`` names the same cfgs without that prefix.
        """
        return os.path.join(self.www, f"zppy_{cfg}_www", RUN_SEGMENT, case)

    def status_dir(self, cfg: str) -> str:
        """Return the post/scripts directory holding a cfg's job status files."""
        return os.path.join(
            self.output,
            f"zppy_{cfg}_output",
            RUN_SEGMENT,
            case_name_for_cfg(cfg),
            "post",
            "scripts",
        )

    def image_check_dir(self, cfg: str) -> str:
        """Return where a cfg's image diffs and viewer are written."""
        return os.path.join(self.image_check, cfg)


def run_layout(root: str, tag: str, output_root: str = "") -> RunLayout:
    """Return the layout of one run under a shared root."""
    return RunLayout(os.path.join(runs_root(root), tag), output_root)


def resolve_baseline(root: str, channel: str = DEFAULT_CHANNEL) -> RunLayout:
    """Return the layout of the run currently promoted to a channel.

    Raises
    ------
    FileNotFoundError
        If the link is missing or dangling. Both mean the tests have no
        baseline to compare against, which is worth failing loudly for rather
        than reporting as thousands of missing images.
    """
    link: str = baseline_link(root, channel)
    if not os.path.islink(link):
        raise FileNotFoundError(
            f"No baseline is promoted for channel {channel!r}: {link} does not "
            "exist. Promote a run with `python -m tests.complete_run.promote`."
        )

    target: str = os.path.realpath(link)
    if not os.path.isdir(target):
        raise FileNotFoundError(
            f"The baseline link for channel {channel!r} is broken: "
            f"{link} -> {target}"
        )
    return RunLayout(target)


def baseline_tag(root: str, channel: str = DEFAULT_CHANNEL) -> str:
    """Return the tag of the run currently promoted to a channel."""
    return os.path.basename(resolve_baseline(root, channel).root)


def read_json_object(path: str) -> Dict[str, Any]:
    """Load a JSON object, returning an empty one when absent or malformed.

    Run files are read back by later stages, reports, and promotion. A run that
    died partway leaves some of them missing or truncated, and every reader
    treats that as "nothing recorded" rather than an error.
    """
    try:
        with open(path) as stream:
            loaded = json.load(stream)
    except (OSError, json.JSONDecodeError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def write_json(path: str, data: Any) -> str:
    """Write sorted, indented JSON, creating the directory if needed."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as stream:
        json.dump(data, stream, indent=2, sort_keys=True, default=str)
        stream.write("\n")
    return path
