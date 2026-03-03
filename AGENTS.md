# AGENTS

## Repository purpose

`zppy` is a post-processing workflow tool that runs specialized
post-processing tools.

Each task is defined by:

1. A Python task file in `zppy/` that reads user-provided `cfg` values.
2. A Jinja2 bash template in `zppy/templates/`.
3. A generated bash script that `zppy` launches.

`zppy-interfaces` is a distinct repository and contains plotting packages used
by `zppy`.

## Project overview

`zppy` orchestrates post-processing tasks from user config (`cfg`) values. The
task Python modules in `zppy/` translate cfg options into executable scripts
from templates in `zppy/templates/`, then launch those scripts.

## Key design decisions

- Keep task logic in Python and execution logic in Jinja2 bash templates.
- Keep repository boundaries clear: `zppy` controls workflow orchestration,
  while plotting packages live in `zppy-interfaces`.
- Prefer minimal changes for maintenance work to avoid altering behavior.

## Repository layout

- `docs/source`: documentation sources.
- `tests/`: test files.
- `zppy/`: Python task and workflow control logic.
- `zppy/templates`: bash templates used to control individual tasks.

## Tech stack

- Python for workflow/task orchestration.
- Jinja2 templates to generate bash scripts.
- pytest for unit and integration tests.

## Code style

- Follow existing style in nearby files and keep changes minimal/surgical.
- Avoid over-engineering; prefer straightforward updates.
- Do not change behavior in non-functional updates.

## Setting up a development environment

Use a clean environment and install from source:

```bash
python -m pip install .
```

For integration workflows, create separate conda environments for
`e3sm_diags`, `zppy-interfaces`, and `zppy`.

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
3. Update `tests/integration/utils.py` `TEST_SPECIFICS` environment command
   values for the current environment names.
4. Generate integration cfg files:

   ```bash
   python tests/integration/utils.py
   ```

5. Launch `zppy` with generated cfg files in `tests/integration/generated/`.
6. Check generated `*status` files (for example with `grep -v "OK" *status`).
7. Run integration pytest files under `tests/integration/`.
8. For `test_images.py`, run on a compute node and inspect
   `test_images_summary.md`.

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

## Git workflow

- Keep each change focused and as small as possible.
- Use the existing PR review process and address reviewer comments directly.

## Adding dependencies

- Add new dependencies only when necessary.
- Record dependency updates in the appropriate repository dependency files
  (for example, under `zppy/conda` when applicable), not only as imports.
