# zppy Integration Test Automation

This automation system streamlines the zppy integration testing workflow, reducing manual steps and wait time while maintaining quality control checkpoints.

## Quick Start

### Basic Usage (Interactive Mode)
```bash
./run_integration_test.bash
```

## Workflow Phases

### Phase 1: Setup (~2-4 hours including SLURM wait)
- Sets up e3sm_diags conda environment
- Sets up zppy-interfaces conda environment
- Sets up zppy conda environment
- Generates config files
- Submits initial SLURM jobs (6 configs)
- Waits for jobs to complete

### Phase 2: Bundles Part 2 (~30-60 minutes including SLURM wait)
- Checks status of bundles runs
- Submits bundles part 2 jobs
- Waits for completion

### Phase 3: Validation (~15 minutes, excluding image tests)
- Checks all status files
- Runs pytest integration tests:
  - test_bash_generation.py
  - test_campaign.py
  - test_defaults.py
  - test_last_year.py
  - test_bundles.py
- Provides instructions for running test_images.py on compute node

## Running Image Tests

The image tests require a compute node allocation. Two options:

### Option 1: Manual Allocation (Recommended)
```bash
salloc --nodes=1 --partition=debug --time=02:00:00 --account=e3sm
./run_image_tests.bash --date 20260123
```

### Option 2: Automatic Allocation
```bash
./run_image_tests.bash --date 20260123 --auto
```

## Output and Logs

The script provides color-coded output:
- 🔵 **Blue**: Informational messages
- 🟢 **Green**: Success messages
- 🟡 **Yellow**: Warnings and checkpoints
- 🔴 **Red**: Errors

### SLURM Job Monitoring
The script automatically monitors SLURM jobs and shows:
```
Jobs remaining: 42 (elapsed: 1234s)
```

### Status File Checking
Automatically checks for errors in status files:
```
✓ v2: No errors found
✓ Legacy v2: No errors found
✓ v3: No errors found
...
```

## Customization

### Modify Test Configurations

Edit the script to change which configs are run:

```bash
# In the generated Python code section, modify:
"cfgs_to_run": [
    "weekly_bundles",
    "weekly_comprehensive_v2",
    # Add or remove configs here
],
```

### Adjust Timeouts

```bash
# In phase_1_setup(), change max wait time:
wait_for_slurm_jobs 30 14400  # 30s interval, 4hr max

# In phase_2_bundles_part2():
wait_for_slurm_jobs 30 3600   # 30s interval, 1hr max
```

## Troubleshooting

### Script Exits Early
Check the error message. The script uses `set -e`, so it exits on any error.

### Jobs Don't Complete
- Check SLURM queue: `squeue -u <user>`
- Check job logs in the output directories
- Increase timeout: edit `wait_for_slurm_jobs` calls

### Environment Issues
```bash
# Clean and rebuild
conda remove --y --all --name test-diags-main-YYYYMMDD
conda remove --y --all --name test-zi-main-YYYYMMDD
conda remove --y --all --name test-zppy-main-YYYYMMDD

# Check configurations and then re-run
./run_integration_test.bash
```

## Files Created

```
~/ez/zppy/
├── tests/integration/generated/
│   ├── test_weekly_bundles_chrysalis.cfg
│   ├── test_weekly_comprehensive_v2_chrysalis.cfg
│   ├── test_weekly_comprehensive_v3_chrysalis.cfg
│   ├── test_weekly_legacy_3.0.0_bundles_chrysalis.cfg
│   ├── test_weekly_legacy_3.0.0_comprehensive_v2_chrysalis.cfg
│   └── test_weekly_legacy_3.0.0_comprehensive_v3_chrysalis.cfg
└── test_images_summary.md

/lcrc/group/e3sm/ac.forsyth2/
├── zppy_weekly_bundles_output/zppy_main_branch_test_YYYYMMDD_run1/
├── zppy_weekly_comprehensive_v2_output/zppy_main_branch_test_YYYYMMDD_run1/
├── zppy_weekly_comprehensive_v3_output/zppy_main_branch_test_YYYYMMDD_run1/
└── zppy_weekly_legacy_3.0.0_*/zppy_main_branch_test_YYYYMMDD_run1/
```

## Example run

```bash
# For safety, confirm branches have no uncommitted changes beforehand:
cd ~/ez/e3sm_diags
git status
cd ~/ez/zppy-interfaces
git status
cd ~/ez/zppy
git status

cd /home/ac.forsyth2/ez/zppy_main_branch_tests/test_20260126
cp ~/ez/zppy/tests/main_branch_testing/* . # Copy, so the script isn't affected by the branch change
emacs run_integration_test.bash # Configure parameters

screen # Run on screen
cd /home/ac.forsyth2/ez/zppy_main_branch_tests/test_20260126 # If not there already
# Bypass manual checkpoints, tee output:
time ./run_integration_test.bash --date 20260126_run1 --auto 2>&1 | tee integration_test.log
# CTRL A D to exit screen
screen -ls # Check which node the screen is on.
tail -f integration_test.log # Follow log updates
```
