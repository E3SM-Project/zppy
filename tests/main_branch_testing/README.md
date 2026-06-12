# zppy Integration Test Automation

This automation system streamlines the zppy integration testing workflow, reducing manual steps and wait time while maintaining quality control checkpoints.

## Quick Start

### Basic Usage (Interactive Mode)
```bash
./run_integration_test.bash --config zppy_test.cfg
```

### Skip Straight to a Later Phase
Set `START_PHASE=2` or `START_PHASE=3` in your config file, then re-run:
```bash
./run_integration_test.bash --config zppy_test.cfg
```

### Non-Interactive (Auto) Mode
Set `AUTO_MODE=true` in your config file. All checkpoints are bypassed and the script runs end-to-end without waiting for user input.

## Configuration

Copy `zppy_test.cfg` and edit it before each test run. It has three sections:

### Runtime settings (update as needed each run)

| Variable | Description |
| --- | --- |
| `MACHINE` | `chrysalis`, `compy`, or `perlmutter` |
| `START_PHASE` | `1`, `2`, or `3` |
| `AUTO_MODE` | `true` to skip all interactive checkpoints |
| `EXPLICIT_TAG` | Leave empty to auto-generate; set to a prior TAG to resume |
| `RUN_NUMBER` | Increment if you run multiple tests on the same day |
| `DIAGS_BASE_BRANCH` | Branch to test for e3sm_diags (usually `main`) |
| `E3SM_TO_CMIP_BASE_BRANCH` | Branch to test for e3sm_to_cmip (usually `master`) |
| `MPAS_BASE_BRANCH` | Branch to test for MPAS-Analysis (usually `develop`) |
| `ZI_BASE_BRANCH` | Branch to test for zppy-interfaces (usually `main`) |
| `ZPPY_BASE_BRANCH` | Branch to test for zppy (usually `main`) |
| `DIAGS_ENV_TYPE` | `"dev"` to build a dedicated conda env; `"unified"` to use e3sm-unified |
| `E3SM_TO_CMIP_ENV_TYPE` | `"dev"` to build a dedicated conda env; `"unified"` to use e3sm-unified |
| `MPAS_ENV_TYPE` | `"dev"` to build a dedicated conda env; `"unified"` to use e3sm-unified |
| `ZI_ENV_TYPE` | `"dev"` to build a dedicated conda env; `"unified"` to use e3sm-unified |

### One-time setup (paths that rarely change)

| Variable | Description |
| --- | --- |
| `HOME_DIR` | Your home directory (default: `$HOME`) |
| `EZ_DIR` | Parent directory for all repos (default: `$HOME/ez`) |
| `E3SM_DIAGS_DIR` | Path to e3sm_diags repo |
| `E3SM_TO_CMIP_DIR` | Path to e3sm_to_cmip repo |
| `MPAS_ANALYSIS_DIR` | Path to MPAS-Analysis repo |
| `ZPPY_INTERFACES_DIR` | Path to zppy-interfaces repo |
| `ZPPY_DIR` | Path to zppy repo |
| `CONDA_PROFILE` | Path to your conda profile script |
| `TAG_CACHE_FILE` | Where the TAG is saved between phases (default: `~/.zppy_test_tag`) |

Machine-specific settings (`OUTPUT_WORKSPACE`, conda activation command, unified environment path, `salloc` command) are derived automatically from `MACHINE` and do not appear in the config.

## Workflow Phases

### Phase 1: Setup
- Creates conda environments for each component where `ENV_TYPE="dev"` (e3sm_to_cmip, e3sm_diags, MPAS-Analysis, zppy-interfaces, zppy); skips env creation and uses e3sm-unified for any component where `ENV_TYPE="unified"`
- Runs unit tests for zppy-interfaces and zppy
- Patches `tests/integration/utils.py` with test-specific environment commands, config list, and unique ID
- Generates config files via `python tests/integration/utils.py`
- Submits all 9 initial SLURM jobs (3 current + 3 legacy 3.1.0 + 3 legacy 3.0.0)
- Waits for jobs to complete (polls every 10 min, 4-hour max)

### Phase 2: Bundles Part 2
- Checks status files for all three bundles output directories; warns if any are non-OK before proceeding
- Submits bundles part 2 jobs (`weekly_bundles`, `legacy_3.1.0_bundles`, `legacy_3.0.0_bundles`)
- Waits for completion (polls every 10 min, 1-hour max)

### Phase 3: Validation
- Checks status files for all 9 output directories
- Runs pytest integration tests:
  - `test_last_year.py`
  - `test_bash_generation.py`
  - `test_campaign.py`
  - `test_defaults.py`
  - `test_bundles.py`
- Prints instructions for running `test_images.py` manually on a compute node

## Output and Logs

The script provides color-coded output:
- 🔵 **Blue**: Informational messages
- 🟢 **Green**: Success messages
- 🟡 **Yellow**: Warnings and checkpoints
- 🔴 **Red**: Errors

### SLURM Job Monitoring
The script automatically monitors SLURM jobs and shows:
```
Jobs remaining: 42 (elapsed: 1234s / max: 14400s)
```
If all remaining jobs enter `DependencyNeverSatisfied`, they are cancelled automatically and the script exits with an error.

### Status File Checking
Automatically checks for non-OK entries in all status directories:
```
✓ v2: All status files OK
✓ Legacy 3.1.0 v2: All status files OK
✓ Legacy 3.0.0 v2: All status files OK
...
```

## Customization

### Adjust Timeouts

```bash
# In phase_1_setup():
wait_for_slurm_jobs 600 14400   # Check every 10 min, max 4 hours

# In phase_2_bundles_part2():
wait_for_slurm_jobs 600 3600    # Check every 10 min, max 1 hour
```

## Troubleshooting

### Script Exits Early
Check the error message. The script uses `set -e`, so it exits on any error. Common causes:
- A unit test failure during Phase 1 setup
- A SLURM timeout (increase the max-wait argument to `wait_for_slurm_jobs`)
- `DependencyNeverSatisfied` on all queued jobs (check your cfg files and SLURM account)

Phase 2 checks bundle status files before resubmitting and warns if any are non-OK. Resolve any failures in the Phase 1 bundle runs before proceeding. You can restart from Phase 2 by setting `START_PHASE=2` in your config (the TAG from Phase 1 is saved in `~/.zppy_test_tag` and picked up automatically, or set `EXPLICIT_TAG` to be explicit):
```bash
./run_integration_test.bash --config zppy_test.cfg
```

### Environment Issues
```bash
# Remove and rebuild stale environments (only applies to components with ENV_TYPE="dev")
conda remove --yes --all --name test-e3sm-to-cmip-master-YYYYMMDD_runN
conda remove --yes --all --name test-diags-main-YYYYMMDD_runN
conda remove --yes --all --name test-mpas-develop-YYYYMMDD_runN
conda remove --yes --all --name test-zi-main-YYYYMMDD_runN
conda remove --yes --all --name test-zppy-main-YYYYMMDD_runN

# Then re-run from Phase 1
./run_integration_test.bash --config zppy_test.cfg
```

## Files Created

```
~/ez/zppy/
├── tests/integration/generated/
│   ├── test_weekly_bundles_chrysalis.cfg
│   ├── test_weekly_comprehensive_v2_chrysalis.cfg
│   ├── test_weekly_comprehensive_v3_chrysalis.cfg
│   ├── test_weekly_legacy_3.1.0_bundles_chrysalis.cfg
│   ├── test_weekly_legacy_3.1.0_comprehensive_v2_chrysalis.cfg
│   ├── test_weekly_legacy_3.1.0_comprehensive_v3_chrysalis.cfg
│   ├── test_weekly_legacy_3.0.0_bundles_chrysalis.cfg
│   ├── test_weekly_legacy_3.0.0_comprehensive_v2_chrysalis.cfg
│   └── test_weekly_legacy_3.0.0_comprehensive_v3_chrysalis.cfg
└── test_images_summary.md

/lcrc/group/e3sm/<user>/
├── zppy_weekly_bundles_output/zppy_main_branch_test_YYYYMMDD_runN/
├── zppy_weekly_comprehensive_v2_output/zppy_main_branch_test_YYYYMMDD_runN/
├── zppy_weekly_comprehensive_v3_output/zppy_main_branch_test_YYYYMMDD_runN/
├── zppy_weekly_legacy_3.1.0_bundles_output/zppy_main_branch_test_YYYYMMDD_runN/
├── zppy_weekly_legacy_3.1.0_comprehensive_v2_output/zppy_main_branch_test_YYYYMMDD_runN/
├── zppy_weekly_legacy_3.1.0_comprehensive_v3_output/zppy_main_branch_test_YYYYMMDD_runN/
├── zppy_weekly_legacy_3.0.0_bundles_output/zppy_main_branch_test_YYYYMMDD_runN/
├── zppy_weekly_legacy_3.0.0_comprehensive_v2_output/zppy_main_branch_test_YYYYMMDD_runN/
└── zppy_weekly_legacy_3.0.0_comprehensive_v3_output/zppy_main_branch_test_YYYYMMDD_runN/
```

## Example Run

```bash
# Confirm repos have no uncommitted changes
cd ~/ez/e3sm_to_cmip && git status
cd ~/ez/e3sm_diags && git status
cd ~/ez/MPAS-Analysis && git status
cd ~/ez/zppy-interfaces && git status
cd ~/ez/zppy && git status

# Confirm no jobs are currently running
squeue -u $USER

# Copy the script and config out of the repo (Phase 1 will change branches)
mkdir -p ~/ez/zppy_main_branch_tests/test_YYYYMMDD
cd ~/ez/zppy_main_branch_tests/test_YYYYMMDD
cp ~/ez/zppy/tests/main_branch_testing/run_integration_test.bash .
cp ~/ez/zppy/tests/main_branch_testing/zppy_test.cfg .

# Edit configuration parameters
emacs zppy_test.cfg

# Run inside a screen session so it will survive disconnections.
screen
cd ~/ez/zppy_main_branch_tests/test_YYYYMMDD
time ./run_integration_test.bash --config zppy_test.cfg 2>&1 | tee integration_test.log
# Ctrl-A D to detach from screen

# Monitor progress from another terminal
screen -ls                      # Find the screen session
tail -f integration_test.log    # Follow log output
```
