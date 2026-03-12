# AGENTS

## Instructions

You are an agent responding to a request about the `zppy` package. First, determine which of the following three categories you match, and then follow the corresponding instructions.

In all cases:
- Do _not_ install packages, run tests, run pre-commit, or run the code in any way. Assume permission is _not_ granted to do any installations or runs yourself. Please proceed as best you can without these.

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
- If you are not able to produce a Markdown comment, add a commit to the package including your analysis in a new file called `ANALYSIS.md`.

### (3) Specific instructions for agents adding commits

These instructions apply if you task is to make changes in the repository. This happens when someone marks Copilot as an assignee on an issue, when someone tags Copilot in a comment, or when someone interacts with Copilot via the "Agents" tab.

- Your goal is to produce a commit that can be reviewed and tested manually by the developer.
- Changes should be as minimal as possible. For example, if increasing the version of Python breaks something, check if there's a way to default to previous working behavior before implementing a big fix. Small changes should always be preferred over large changes.
- All code changes should be done based on (1) the request from the person who launching the agent and (2) the code logic of the `zppy` package.
- Type annotations should _always_ be used.

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

When to add dependencies:
- Do so only if absolutely necessary or specifically requested.
- Record the dependency updates in the appropriate repository dependency files
  (for example, in `conda/dev.yml` ), not only as imports.

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
- `e3sm_to_cmip.py` — CMIP variable conversion (uses `e3sm_to_cmip`)
- `tc_analysis.py` — tropical cyclone analysis
- `e3sm_diags.py` — E3SM Diags diagnostic plots (uses `e3sm_diags`)
- `mpas_analysis.py` — MPAS ocean/sea-ice analysis (uses `mpas_analysis`)
- `global_time_series.py` — global time series plots (uses `zppy-interfaces`)
- `ilamb.py` — ILAMB land model benchmarking (uses `ilamb`)
- `pcmdi_diags.py` — PCMDI diagnostics (uses `zppy-interfaces`)

### Configuration

The configuration file given by the user in `zppy -c config_file.cfg` contains all the user-specified values to use. If the user specifies a campaign, values from `zppy/defaults/campaign_name.cfg` may also be used. The final default for any paramter is `zppy/defaults/default.ini`.

Configuration files are set up hierarchically. Parameters defined in `[default]` apply to all tasks, unless overridden. Parameters defined for a task apply to all subtasks, unless overridden.

### Inclusions

Some tasks (`e3sm_diags`, `e3sm_to_cmip`, `ilamb`, `pcmdi_diags`) have extended configuration files that can be specified. These can be found in `zppy/templates/inclusions`. The entire text of these files is used in the bash scripts. For example, `ilamb.bash` has the following code block where `cfg` is a parameter that is passed in.

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

You should _not_ run tests. However, it is important for you to understand how humans will run the tests. The following code is an example of the integration testing we do weekly on the `main` branch. When testing pull requests, we typically reduce the number of tests run to the minimum relevant set. Again, this code block is just for context and you yourself should _not_ run it.

Step 1: Set up environments for tasks and run `zppy-interfaces` unit tests

```bash
lcrc_conda # Bash function to activate conda

# Set up e3sm_diags env
cd ~/ez/e3sm_diags
git status # Check that branch is `main`, and for "nothing to commit, working tree clean"
git fetch upstream main
git checkout main
git reset --hard upstream/main
git log --oneline # Check that last commit matches https://github.com/E3SM-Project/e3sm_diags/commits/main
rm -rf build
conda clean --all --y
conda env create -f conda-env/dev.yml -n test-diags-main-yyyymmdd # Use today's date
conda activate test-diags-main-yyyymmdd
python -m pip install .

# Set up zppy-interfaces env
cd ~/ez/zppy-interfaces
git status # Check that branch is `main`, and for "nothing to commit, working tree clean"
git fetch upstream main
git checkout main
git reset --hard upstream/main
git log --oneline # Check that last commit matches https://github.com/E3SM-Project/zppy-interfaces/commits/main
rm -rf build
conda clean --all --y
conda env create -f conda/dev.yml -n test-zi-main-yyyymmdd # Use today's date
conda activate test-zi-main-yyyymmdd
python -m pip install .
pytest tests/unit/global_time_series/test_*.py
pytest tests/unit/pcmdi_diags/test_*.py
```

Step 2: Set up `zppy` environment and run `zppy` unit tests

```bash
# zppy itself #################################################################
cd ~/ez/zppy
git status # Check that branch is `main`, and for "nothing to commit, working tree clean"
git fetch upstream main
git checkout -b test-zppy-main-yyyymmdd upstream/main # Use today's date
git log --oneline # Check that last commit matches https://github.com/E3SM-Project/zppy/commits/main
rm -rf build
conda clean --all --y
conda env create -f conda/dev.yml -n test-zppy-main-yyyymmdd # Use today's date
conda activate test-zppy-main-yyyymmdd
python -m pip install .
pytest tests/test_*.py
```

Step 3: Edit `tests/integration/utils.py` to properly set up integration tests

```python
TEST_SPECIFICS: Dict[str, Any] = {
    # These are custom environment_commands for specific tasks.
    # Never set these to "", because they will print the line
    # `environment_commands = ""` for the corresponding task,
    # thus overriding the value set higher up in the cfg.
    # That is, there will be no environment set.
    # (`environment_commands = ""` only redirects to Unified
    # if specified under the [default] task)
    "diags_environment_commands": "source /gpfs/fs1/home/ac.forsyth2/miniforge3/etc/profile.d/conda.sh; conda activate test-diags-main-yyyymmdd",
    "mpas_analysis_environment_commands": "source /home/ac.xylar/chrysalis/miniforge3/etc/profile.d/conda.sh && conda activate mpas_analysis_dev",
    "global_time_series_environment_commands": "source /gpfs/fs1/home/ac.forsyth2/miniforge3/etc/profile.d/conda.sh; conda activate test-zi-main-yyyymmdd",
    "pcmdi_diags_environment_commands": "source /gpfs/fs1/home/ac.forsyth2/miniforge3/etc/profile.d/conda.sh; conda activate test-zi-main-yyyymmdd",
    # This is the environment setup for other tasks.
    # Leave as "" to use the latest Unified environment.
    "environment_commands": "source /lcrc/soft/climate/e3sm-unified/load_latest_e3sm_unified_chrysalis.sh",
    # For a complete test, run the set of latest cfgs and at least one set of legacy cfgs
    "cfgs_to_run": [
        "weekly_bundles",
        "weekly_comprehensive_v2",
        "weekly_comprehensive_v3",
        "weekly_legacy_3.1.0_bundles",
        "weekly_legacy_3.1.0_comprehensive_v2",
        "weekly_legacy_3.1.0_comprehensive_v3",
        "weekly_legacy_3.0.0_bundles",
        "weekly_legacy_3.0.0_comprehensive_v2",
        "weekly_legacy_3.0.0_comprehensive_v3",
    ],
    "tasks_to_run": [
        "e3sm_diags",
        "mpas_analysis",
        "global_time_series",
        "ilamb",
        "pcmdi_diags",
    ],
    "unique_id": "zppy_main_branch_test_yyyymmdd",
}

```

A few things are worth pointing out here:
- The environment `zppy` runs in can, and often is, distinct from the environment that the tasks run in. Each task's `.bash` file begins with `{{ environment_commands }}`, which specifies the environment to use. That is why we had to create a fresh environment for `e3sm_diags` and `zppy_interfaces` earlier. Soon, we will run `tests/integration/utils.py`, which will set the proper `environment_commands` value for each task.
- There are 3 main test configuration files: `bundles`, `comprehensive_v2`, `comprehensive_v3`. There are also 3 versions of these tests: the most recent ones, the files as they existed when `v3.1.0` was released, and as they existed when `v3.0.0` were released. The latter two categories are "legacy" tests in the sense that they allow us to test backwards compatibility.
- Specific tasks to run can be toggled on/off so that only relevant jobs will be launched during testing.

Step 4: Launch jobs

```bash
git diff # Check the diff of tests/integration/utils.py
python tests/integration/utils.py # Generate the actual cfgs we'll use for testing

zppy -c tests/integration/generated/test_weekly_comprehensive_v3_chrysalis.cfg
zppy -c tests/integration/generated/test_weekly_bundles_chrysalis.cfg
zppy -c tests/integration/generated/test_weekly_comprehensive_v2_chrysalis.cfg

zppy -c tests/integration/generated/test_weekly_legacy_3.1.0_bundles_chrysalis.cfg
zppy -c tests/integration/generated/test_weekly_legacy_3.1.0_comprehensive_v2_chrysalis.cfg
zppy -c tests/integration/generated/test_weekly_legacy_3.1.0_comprehensive_v3_chrysalis.cfg

zppy -c tests/integration/generated/test_weekly_legacy_3.0.0_bundles_chrysalis.cfg
zppy -c tests/integration/generated/test_weekly_legacy_3.0.0_comprehensive_v2_chrysalis.cfg
zppy -c tests/integration/generated/test_weekly_legacy_3.0.0_comprehensive_v3_chrysalis.cfg
```

Step 5: Once bundles jobs finish, rerun them to launch any remaining jobs

```bash
# Check bundles status
cd /lcrc/group/e3sm/ac.forsyth2/zppy_weekly_bundles_output/zppy_main_branch_test_yyyymmdd/v3.LR.historical_0051/post/scripts
grep -v "OK" *status # Check for any errors. No results is good.
cd /lcrc/group/e3sm/ac.forsyth2/zppy_weekly_legacy_3.1.0_bundles_output/zppy_main_branch_test_yyyymmdd/v3.LR.historical_0051/post/scripts
grep -v "OK" *status # Check for any errors. No results is good.
cd /lcrc/group/e3sm/ac.forsyth2/zppy_weekly_legacy_3.0.0_bundles_output/zppy_main_branch_test_yyyymmdd/v3.LR.historical_0051/post/scripts
grep -v "OK" *status # Check for any errors. No results is good.

# Now, run bundles part 2 (bundles tests require a second run):
cd ~/ez/zppy
git status # Confirm branch and environment are unchanged (they might be different if we've done other work while jobs were running)
zppy -c tests/integration/generated/test_weekly_bundles_chrysalis.cfg
zppy -c tests/integration/generated/test_weekly_legacy_3.1.0_bundles_chrysalis.cfg
zppy -c tests/integration/generated/test_weekly_legacy_3.0.0_bundles_chrysalis.cfg
```

Step 6: Review finished runs

```bash
### v2  ###
cd /lcrc/group/e3sm/ac.forsyth2/zppy_weekly_comprehensive_v2_output/zppy_main_branch_test_yyyymmdd/v2.LR.historical_0201/post/scripts
grep -v "OK" *status # Check for any errors. No results is good.
cd /lcrc/group/e3sm/ac.forsyth2/zppy_weekly_legacy_3.1.0_comprehensive_v2_output/zppy_main_branch_test_yyyymmdd/v2.LR.historical_0201/post/scripts
grep -v "OK" *status # Check for any errors. No results is good.
cd /lcrc/group/e3sm/ac.forsyth2/zppy_weekly_legacy_3.0.0_comprehensive_v2_output/zppy_main_branch_test_yyyymmdd/v2.LR.historical_0201/post/scripts
grep -v "OK" *status # Check for any errors. No results is good.

### v3 ###
cd /lcrc/group/e3sm/ac.forsyth2/zppy_weekly_comprehensive_v3_output/zppy_main_branch_test_yyyymmdd/v3.LR.historical_0051/post/scripts
grep -v "OK" *status # Check for any errors. No results is good.
cd /lcrc/group/e3sm/ac.forsyth2/zppy_weekly_legacy_3.1.0_comprehensive_v3_output/zppy_main_branch_test_yyyymmdd/v3.LR.historical_0051/post/scripts
grep -v "OK" *status # Check for any errors. No results is good.
cd /lcrc/group/e3sm/ac.forsyth2/zppy_weekly_legacy_3.0.0_comprehensive_v3_output/zppy_main_branch_test_yyyymmdd/v3.LR.historical_0051/post/scripts
grep -v "OK" *status # Check for any errors. No results is good.

### bundles ###
cd /lcrc/group/e3sm/ac.forsyth2/zppy_weekly_bundles_output/zppy_main_branch_test_yyyymmdd/v3.LR.historical_0051/post/scripts
grep -v "OK" *status # Check for any errors. No results is good.
cd /lcrc/group/e3sm/ac.forsyth2/zppy_weekly_legacy_3.1.0_bundles_output/zppy_main_branch_test_yyyymmdd/v3.LR.historical_0051/post/scripts
grep -v "OK" *status # Check for any errors. No results is good.
cd /lcrc/group/e3sm/ac.forsyth2/zppy_weekly_legacy_3.0.0_bundles_output/zppy_main_branch_test_yyyymmdd/v3.LR.historical_0051/post/scripts
grep -v "OK" *status # Check for any errors. No results is good.
```

Step 7: Run Python tests

```bash
cd ~/ez/zppy
git status # Confirm branch and environment are unchanged (they might be different if we've done other work while jobs were running)
pytest tests/integration/test_bash_generation.py
pytest tests/integration/test_campaign.py
pytest tests/integration/test_defaults.py
pytest tests/integration/test_last_year.py
pytest tests/integration/test_bundles.py
salloc --nodes=1 --partition=debug --time=02:00:00 --account=e3sm
# We need to reactivate conda now that we're on a compute node
lcrc_conda # Bash function to activate conda
conda activate test-zppy-main-yyyymmdd
pytest tests/integration/test_images.py
```
