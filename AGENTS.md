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

## Key directories

- `docs/source`: documentation sources.
- `tests/`: test files.
- `zppy/`: Python task and workflow control logic.
- `zppy/templates`: bash templates used to control individual tasks.

## Typical test workflow

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
