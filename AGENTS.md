# AGENTS

## Repository purpose

`zppy` is an E3SM post-processing toolchain. It reads a user-provided `.cfg` file, validates it, renders Jinja2 bash script templates for each requested task, and submits those scripts to SLURM (`sbatch`) with appropriate dependencies. It does not run analysis itself -- it orchestrates batch job submission on HPC clusters.

Each task is defined by:

1. A Python task file in `zppy/` that reads user-provided `cfg` values.
2. A Jinja2 bash template in `zppy/templates/`.
3. A generated bash script that `zppy` launches.

`zppy-interfaces` is a distinct repository and contains plotting packages used by `zppy`.

## Architecture

### Core Flow (`zppy/__main__.py`)

1. Parse CLI args (`-c config_file`)
2. Load and validate config with `configobj` against `zppy/defaults/default.ini`
3. Optionally merge a campaign config from `zppy/defaults/<campaign>.cfg`
4. Load machine info via `mache.MachineInfo` (auto-discovers HPC machine)
5. For each task type, call the task module function, which generates bash scripts and submits them to SLURM
6. After all tasks, submit any bundle jobs

### Task Modules

Each task type has a corresponding Python module in `zppy/`:
- `ts.py` — time series (uses `ncclimo`)
- `climo.py` — climatologies (uses `ncclimo`)
- `e3sm_diags.py` — E3SM Diags diagnostic plots
- `e3sm_to_cmip.py` — CMIP variable conversion
- `tc_analysis.py` — tropical cyclone analysis
- `mpas_analysis.py` — MPAS ocean/sea-ice analysis
- `global_time_series.py` — global time series plots
- `ilamb.py` — ILAMB land model benchmarking
- `pcmdi_diags.py` — PCMDI diagnostics

All task modules follow the same pattern:
1. `initialize_template(config, "<task>.bash")` — load the Jinja2 template
2. `get_tasks(config, "<section>")` — read tasks from config, merging `[default]` with task section and sub-sections
3. For each task and year set: render template → write `.bash` file → optionally call `submit_script()`

### Config System (`zppy/defaults/default.ini`)

Uses `configobj` with validation. The `[default]` section sets global parameters; task sections (e.g., `[ts]`) can override them. Sub-sections (e.g., `[[native]]` inside `[ts]`) create separate task instances. Key parameters: `case`, `input`, `output`, `www`, `years`, `mapping_file`, `machine`, `account`, `partition`.

### Template System (`zppy/templates/`)

Jinja2 `.bash` templates for each task. Templates receive the merged task dictionary as their render context. The rendered scripts are written to `<output>/post/scripts/`.

### Bundle System (`zppy/bundle.py`)

Tasks can be grouped into a single SLURM job via `bundle = <name>` in the config. The `Bundle` class accumulates tasks and their dependencies, then renders a single `bundle.bash` that runs them sequentially. Dependencies are classified as internal (within the bundle) or external (to other jobs).

### Status Files

Each script has a `.status` file. `check_status()` returns `True` (skip) if the status is `OK`, `WAITING`, or `RUNNING`. This prevents re-running already-submitted or completed jobs.

### Campaigns

Pre-defined parameter sets in `zppy/defaults/*.cfg` (e.g., `water_cycle.cfg`, `high_res_v1.cfg`). Activated by `campaign = <name>` in the user config; user config values take priority over campaign defaults.

### Plugins

External Python packages can extend zppy with new task types via `plugins = <module_name>` in `[default]`. Each plugin must have a `defaults/default.ini` and a callable named after the module.

## Key Utilities (`zppy/utils.py`)

- `get_tasks(config, section)` — merges `[default]` + `[section]` + sub-sections into a list of task dicts
- `get_years(years_input)` — parses year specs like `"1:100:10"` (begin:end:freq) or `"1-10"` (explicit range) into `[(y1, y2), ...]`
- `submit_script()` — calls `sbatch`, handles `--dependency=afterok:<ids>`, writes WAITING status file
- `set_component_and_prc_typ()` — infers `component` (atm/lnd/rof/cpl) and `prc_typ` from `input_files`
- `set_grid()` — infers grid name from mapping file if not explicitly set

## Code Style

- Formatted with `black` (line length 88) and `isort`
- Type annotations are used throughout; `mypy` is enforced
- `flake8` configured in `.flake8.cfg`

## Repository layout

- `conda/`: dev environment setup.
- `docs/source/`: documentation sources.
- `tests/`: test files.
- `zppy/`: Python task and workflow control logic.
- `zppy/templates/`: bash templates used to control individual tasks.

## Tech stack

- Python for workflow/task orchestration.
- Jinja2 templates to generate bash scripts.
- pytest for unit and integration tests.

## Pull request style

- Follow existing style in nearby files and keep changes minimal/surgical.
- Avoid over-engineering; prefer straightforward updates.
- Do not change behavior in non-functional updates.

## Setting up a development environment

```bash
lcrc_conda # bash function to activate conda. Alternatives: nersc_conda, compy_conda
rm -rf build
conda clean --all --y
conda env create -f conda/dev.yml -n env-name
conda activate env-name
pre-commit run --all-files
python -m pip install .
```

For integration workflows, create separate conda environments for
`e3sm_diags`, `zppy-interfaces`, and `zppy`.

## Common Commands

**Run unit tests:**
```bash
pytest tests/test_*.py
```

**Run a single test:**
```bash
pytest tests/test_zppy_utils.py::test_get_years
```

**Run integration tests** (requires HPC access):
```bash
pytest tests/integration/test_*.py
```

**Run all linting/formatting checks:**
```bash
pre-commit run --all-files
```

**Run individual checks:**
```bash
pre-commit run black --all-files
pre-commit run isort --all-files
pre-commit run flake8 --all-files
pre-commit run mypy --all-files
```

**Run zppy:**
```bash
zppy -c config_file.cfg
```

## Testing

### Unit and integration tests in this repo

```bash
python -m pip install .
pytest tests/test_*.py
```

For integration tests, see `tests/integration/` and run:

```bash
pytest tests/integration/test_*.py
```

### Full weekly/integration workflow context

The common workflow is:

1. Prepare clean conda environments for:
   - `e3sm_diags`
   - `zppy-interfaces`
   - `zppy`
2. Install each package from source in its environment.
3. Update `tests/integration/utils.py`'s `TEST_SPECIFICS` parameter values for the current environment names.
4. Generate integration cfg files:

   ```bash
   python tests/integration/utils.py
   ```

5. Launch `zppy` with generated cfg files in `tests/integration/generated/`.
6. Check generated `*status` files (for example with `grep -v "OK" *status`).
7. Run integration pytest files under `tests/integration/`.
8. For `test_images.py`, run on a compute node and inspect `test_images_summary.md`.

### When to add or modify tests

When to add tests:
- Adding new features or internal functions (add unit and/or integration tests
  for the changed behavior).
- Fixing a bug (add a regression test that fails before the fix and passes
  after it).

When to modify tests:
- Modifying existing features or internal functions.

When not to modify tests:
- Non-functional changes that should not change behavior (for example,
  documentation-only updates, formatting-only changes, or compatibility updates
  for new Python versions).

## Adding dependencies

- Add new dependencies only when necessary.
- Record dependency updates in the appropriate repository dependency files
  (for example, in `conda/dev.yml` ), not only as imports.
