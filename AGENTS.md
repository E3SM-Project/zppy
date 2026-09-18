# AGENTS

## Instructions

You are an agent responding to a request about the `zppy` package. First, determine which of the following three categories you match, and then follow the corresponding instructions:

1. Agents doing code review
2. Agents performing analysis
3. Agents adding commits

In all cases:
- Do _not_ install packages, run tests, run `pre-commit`, or run the `zppy` codebase in any way. Assume permission is _not_ granted to do any installations or runs yourself. Please proceed as best you can with these limitations.

### (1) Specific instructions for agents doing code review

These instructions apply if your task is code review. This happens when someone marks Copilot as a reviewer on a pull request.

Your goal is to leave review comments on the following topics:
- Pull request objectives that are not met
- Logic errors
- Test cases that might fail
- Dependencies that need to be added
- Possible performance slowdowns

### (2) Specific instructions for agents performing analysis

These instructions apply if your task is analysis-only. This happens when a request mentions that it is "analysis-only" or otherwise does not require a commit to be made.

- Your goal is to produce a Markdown comment answering the request.
- If you are not able to produce a Markdown comment, it's ok to add a commit to the package including your analysis in a new file called `ANALYSIS.md`.

### (3) Specific instructions for agents adding commits

These instructions apply if your task is to make changes in the repository. This happens when someone marks Copilot as an assignee on an issue, when someone tags Copilot in a comment, or when someone interacts with Copilot via the "Agents" tab.

- Your goal is to produce a commit that can be reviewed and tested manually by the developer.
- Changes should be as minimal as possible. For example, if increasing the version of Python breaks something, check if there's a way to default to previous working behavior before implementing a big fix. Small changes should always be preferred over large changes.
- All code changes should be done based on (1) the request from the person who launched the agent and (2) the code logic of the `zppy` package.
- Type annotations should _always_ be used.

When to add tests:
- Adding new features or internal functions (add unit and/or integration tests
  for the changed behavior).
- Fixing a bug (add a regression test that fails before the fix and passes
  after it).

When to modify tests:
- Modifying existing features or internal functions.

When _not_ to modify tests:
- Non-functional changes that should not change behavior (for example,
  documentation-only updates, formatting-only changes, or compatibility updates
  for new Python versions).

When to add dependencies:
- Do so only if absolutely necessary or specifically requested.
- Record the dependency updates in the appropriate repository dependency files
  (for example, in `conda/dev.yml`), not only as imports.

## Context for all agents

This context applies to _all_ agents.

### Architecture

`zppy` is the E3SM post-processing toolchain. It reads a user-provided `.cfg` file, renders Jinja2 bash script templates for each requested task, and submits those scripts to SLURM (`sbatch`) with appropriate dependencies. It does _not_ run analysis itself - rather, it orchestrates batch job submission on HPC clusters. Note: `zppy-interfaces` is a distinct repository which contains plotting packages used by `zppy`.

Each task is defined by:

1. A Python task file in `zppy/` that reads user-provided values from the given configuration file.
2. A Jinja2 bash template in `zppy/templates/`.
3. A generated bash script that `zppy` launches.

## Code style

Before merging, a human runs `pre-commit run --all-files` to make sure the code changes meet the repository's code style guidelines.

### Available tasks

Each task type has a corresponding Python file in `zppy/`:
- `ts.py` — time series (uses `ncclimo`)
- `climo.py` — climatologies (uses `ncclimo`)
- `e3sm_to_cmip.py` — CMIP variable conversion (uses [e3sm_to_cmip](https://github.com/E3SM-Project/e3sm_to_cmip))
- `tc_analysis.py` — tropical cyclone analysis
- `e3sm_diags.py` — E3SM Diags diagnostic plots (uses [e3sm_diags](https://github.com/e3sm-project/e3sm_diags))
- `mpas_analysis.py` — MPAS ocean/sea-ice analysis (uses [MPAS-Analysis](https://github.com/MPAS-Dev/MPAS-Analysis))
- `global_time_series.py` — global time series plots (uses [zppy-interfaces](https://github.com/E3SM-Project/zppy-interfaces))
- `ilamb.py` — ILAMB land model benchmarking (uses [ILAMB](https://github.com/rubisco-sfa/ILAMB))
- `livvkit.py` — LIVVkit land ice plots (uses [LIVVkit](https://github.com/LIVVkit/LIVVkit))
- `pcmdi_diags.py` — PCMDI diagnostics (uses [zppy-interfaces](https://github.com/E3SM-Project/zppy-interfaces))

### Configuration

The configuration file given by the user in `zppy -c config_file.cfg` contains all the user-specified values to use. If the user specifies a campaign, values from `zppy/defaults/campaign_name.cfg` may also be used. The final default for any parameter is `zppy/defaults/default.ini`.

Configuration files are set up hierarchically. Parameters defined in `[default]` apply to all tasks, unless overridden. Parameters defined for a task apply to all subtasks, unless overridden.

### Inclusions

Some tasks (`e3sm_to_cmip`, `e3sm_diags`, `ilamb`, `livvkit`, `pcmdi_diags`) have additional files that can be specified, with defaults in `zppy/templates/inclusions`. For example, `ilamb.bash` has the following code block where `cfg` is a parameter that is passed in:

```bash
# include cfg file
cat > ilamb.cfg << EOF
{% include cfg %}
EOF
```

There are two other files in `zppy/templates/inclusions`: `boilerplate.bash` and `slurm_header.bash`, which appear at the top of every bash script.

```bash
{% include 'inclusions/slurm_header.bash' %}
{% include 'inclusions/boilerplate.bash' %}
```

### Output directories

There are two output directories: the paths specified by `output` and `www`.

`output/post/scripts/` contains:
- The rendered `.bash` scripts, which are created by applying values from the configuration to the bash templates in `zppy/templates/`.
- The `.settings` files, which show the actual values each parameter was assigned. This is useful for debugging if values are getting passed in from the configuration as intended.
- The `.o` files, which are the output files.
- The `.status` files, which indicate the status of the corresponding job.

`www` is where visual output (i.e., plots) is sent. If `www` is set to a directory that has a web server, the plots can then be viewed online.

### DevOps

Multiple files cover DevOps for `zppy`. The most important is `conda/dev.yml` which builds the development environment. Other relevant files include  `.github/*`, `.vscode/*`, `.flake8.cfg`, `.pre-commit-config.yaml`, `pyproject.toml`, `setup.py`, and `tbump.toml`.

### Testing

You should _not_ run tests. However, it is important for you to understand how
humans will run them.

There are two tiers:

1. **Unit tests** — `pytest tests/test_*.py`. No HPC access needed; this is what
   CI runs on every pull request.
2. **The complete run test** — the weekly integration test on the `main` branch.
   It builds development environments for `zppy` and the four packages whose
   tasks it launches (`e3sm_diags`, `e3sm_to_cmip`, `MPAS-Analysis`,
   `zppy-interfaces`), submits the weekly cfgs to SLURM, and checks the
   resulting plots against expected results.

The complete run test is driven by `tests/complete_run/`, orchestrated from
`tests/complete_run/automation.py`. A human runs it with a single command:

```bash
python -m tests.complete_run.automation --machine chrysalis --account e3sm
```

Key properties to keep in mind when changing this code:

- **Repositories are used through detached `git worktree` checkouts of one
  resolved commit.** A run must never commit, switch branches, or otherwise
  modify a developer's clone. Code that checks out a branch in a developer's
  repository is a regression.
- **Configuration is passed as arguments, never written into source.** The run
  drives cfg generation through `python -m tests.integration.utils` flags; it
  does not edit `TEST_SPECIFICS` in `tests/integration/utils.py`.
- **`env_description.txt` has a fixed format** (see
  `tests/complete_run/provenance.py`). Every task's plots carry one, including
  in promoted baselines and older expected-results directories, and
  maintainers and tools read the `Generated:` line to date them per task.
  Changing the format silently breaks that. (The report dates the baseline as
  a whole from its `manifest.json`.)
- **Every stage writes `status.json`**, so an interrupted run can resume and a
  crashed one still produces a report. A resumed run rebuilds its environments
  and selections from that file; stages must not rely on in-memory state that
  only `prepare` produces.
- **Anything that exercises zppy runs in the environment under test**, via
  `Environment.run_args` (`conda run -n <env>`). A bare `zppy` or
  `python -m pytest` would use the controller's environment, not the commit
  being tested.
- **Tests go through the real CLI** (`automation.main([...])` or
  `_build_parser().parse_args`), not hand-built `argparse.Namespace` objects,
  which is how a flag the parser never defined once went unnoticed.
- **Three environment modes**, selected per repository with `--env-type`:
  `dev` (solve the repo's dev.yml afresh), `unified` (E3SM-Unified), and
  `baseline` (rebuild what the baseline was produced with). Every run exports
  `environments/<repo>.yml` via `conda env export` so `baseline` is possible --
  `conda list` output, which `env_description.txt` carries, is readable but
  cannot rebuild an environment. Note this is *not* frozen-environment testing,
  which the team decided against; it exists so a branch can be evaluated against
  known-good dependencies.
- **Every image viewer and report states how the environment differed from the
  baseline's** (`tests/complete_run/envdiff.py`). This is not decoration: in a
  fresh-solve run the dependency list *is* the finding, and in a
  `--env-type <repo>=baseline` run a non-empty diff means the reproduction
  failed and the image differences are not attributable to code. The comparison
  ignores `name:` and `prefix:`, which differ on every run by design.
- **Runs are written to a shared, group-writable root**, not a personal
  directory, so any maintainer can inspect and promote any run. The cfg
  templates no longer encode whose account is running.
- **A run is its own baseline material.** Expected results are not a copy of a
  run; `baselines/latest-main` is a symlink pointing at one. Promotion
  (`python -m tests.complete_run.promote`) flips that link, so it is atomic,
  instant, and does not destroy the previous baseline. Code that copies a run
  over a baseline directory is a regression.
- **A complete run never promotes on its own.** Promotion is always a separate,
  explicit command, and it refuses a run that did not pass or came from a
  feature branch unless overridden.

Layout (see `tests/complete_run/layout.py`, the single source of truth):

```
<shared root>/runs/<tag>/     one immutable run: www/, image_lists/, settings/,
                              image_check/, manifest.json, reports
<shared root>/baselines/latest-main -> ../runs/<tag>
<scratch>/zppy_complete_run/<tag>/   intermediate data: output/ (zppy post
                              output, job logs) and worktrees/
```

Intermediate data goes to per-user scratch (`/lcrc/globalscratch/$USER` on
Chrysalis) because it is large and worthless after validation. Anything a
baseline needs from it must be copied into the run directory during
`validate`; never make a baseline or a later run read from scratch, which is
purged. The integration tests find a run's locations through
`tests/integration/generated/complete_run_settings.json`, which cfg generation
writes into the run's worktree.

Note two naming conventions for the same cfgs: the complete run uses the full
template name (`weekly_comprehensive_v3`), while `tests/integration/image_checker.py`
uses it without the `weekly_` prefix (`comprehensive_v3`). Doubling the prefix
is an easy mistake; `RunLayout.www_case_dir` takes the full name.

Test selection is configurable. The weekly cfgs, the case each runs against,
and the tasks whose plots are image-checked are defined once, in
`tests/integration/weekly_cfgs.py`; `DEFAULT_CFGS_TO_RUN` and
`test_images.py` both read that table, and `tests/test_weekly_cfgs.py` fails
if it disagrees with the templates. Adding a plotting task to a weekly cfg
means adding it to `image_tasks` there. Legacy cfgs exist only to exercise
older cfg syntax; one that has become a copy of a current cfg apart from its
paths should be removed, not kept. `DEFAULT_TASKS_TO_RUN` is in
`tests/complete_run/params.py`.
When testing a pull request, a human typically reduces these to the minimum
relevant set with `--cfg` and `--task`.

Each task's `.bash` file begins with `{{ environment_commands }}`, which
specifies the environment that task runs in. That environment is usually
distinct from the one `zppy` itself runs in, which is why the complete run test
builds several.

For the full procedure, including the manual fallback, see
`docs/source/dev_guide/tests/`.
