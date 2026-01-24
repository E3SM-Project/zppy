# zppy Integration Test Automation

This automation system streamlines the zppy integration testing workflow, reducing manual steps and wait time while maintaining quality control checkpoints.

## Quick Start

### Basic Usage (Interactive Mode)
```bash
./run_integration_test.bash
```
This will:
- Use today's date as the test identifier
- Stop at checkpoints for you to verify
- Set up all environments from scratch
- Run the complete test suite

### Fully Automated Mode
```bash
./run_integration_test.bash --auto
```
Runs end-to-end without stopping (suitable for CI or overnight runs).

### Custom Date Stamp
```bash
./run_integration_test.bash --date 20260123
```

### Resume from Specific Phase
```bash
# If Phase 1 completed but you need to re-run Phase 2
./run_integration_test.bash --phase 2 --date 20260123
```

## Complete Options

```
./run_integration_test.bash [OPTIONS]

Options:
  --date YYYYMMDD       Date stamp for test (default: today)
  --auto                Run fully automated (no checkpoints)
  --phase N             Start from phase N (1=setup, 2=bundles_part2, 3=validation)
  --help                Show help message
```

## Workflow Phases

### Phase 1: Setup (~2-4 hours including SLURM wait)
- Sets up e3sm_diags conda environment
- Sets up zppy-interfaces conda environment
- Sets up zppy conda environment
- Applies optional cherry-pick
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

## Common Workflows

### Full Test with Custom Date
```bash
# Interactive mode with checkpoints
./run_integration_test.bash --date 20260123

# When prompted, allocate compute node for images:
salloc --nodes=1 --partition=debug --time=02:00:00 --account=e3sm
./run_image_tests.bash --date 20260123
```

### Overnight Automated Run
```bash
# Start before leaving for the day
nohup ./run_integration_test.bash --auto --date 20260123 > test_run.log 2>&1 &

# Next morning, run image tests manually
salloc --nodes=1 --partition=debug --time=02:00:00 --account=e3sm
./run_image_tests.bash --date 20260123
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

## Environment Variables

You can set these before running the script:

```bash
export DATE_STAMP=20260123
export UNIQUE_ID="custom_test_id"
./run_integration_test.bash
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

### Add Custom Checks

Add your own validation in `phase_3_validation()`:

```bash
# Custom validation example
log "Running custom checks..."
if [ -f "$ZPPY_DIR/my_custom_check.bash" ]; then
    bash "$ZPPY_DIR/my_custom_check.bash"
fi
```

## Troubleshooting

### Script Exits Early
Check the error message. The script uses `set -e`, so it exits on any error.

### Jobs Don't Complete
- Check SLURM queue: `squeue -u ac.forsyth2`
- Check job logs in the output directories
- Increase timeout: edit `wait_for_slurm_jobs` calls

### Environment Issues
```bash
# Clean and rebuild
conda remove --y --all --name test-diags-main-20260123
conda remove --y --all --name test-zi-main-20260123
conda remove --y --all --name test-zppy-main-20260123-env

# Re-run
./run_integration_test.bash --date 20260123
```

### Git Issues
```bash
# If git operations fail, manually clean up:
cd ~/ez/zppy
git reset --hard upstream/main
git clean -fd
./run_integration_test.bash --date 20260123
```

### Checkpoint Issues in Auto Mode
The script will proceed automatically but log warnings. Review logs after completion.

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
├── zppy_weekly_bundles_output/zppy_main_branch_test_YYYYMMDD/
├── zppy_weekly_comprehensive_v2_output/zppy_main_branch_test_YYYYMMDD/
├── zppy_weekly_comprehensive_v3_output/zppy_main_branch_test_YYYYMMDD/
└── zppy_weekly_legacy_3.0.0_*/zppy_main_branch_test_YYYYMMDD/
```

## Tips

1. **Use descriptive date stamps**: Instead of the current date, use a meaningful identifier like `20260123_bugfix` or `20260123_pr769`

2. **Run overnight**: The full test takes 2-4 hours. Start it before leaving:
   ```bash
   nohup ./run_integration_test.bash --auto > test.log 2>&1 &
   ```

3. **Keep logs**: Redirect output to files for later review:
   ```bash
   ./run_integration_test.bash --auto 2>&1 | tee test_$(date +%Y%m%d).log
   ```

4. **Parallel testing**: Run different date stamps to test multiple branches:
   ```bash
   ./run_integration_test.bash --date 20260123_main &
   ./run_integration_test.bash --date 20260123_feature --cherry-pick abc123 &
   ```

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the script output for error messages
3. Check SLURM logs in the output directories
4. Contact the zppy development team

## Example run

```bash
# For safety, confirm branches have no uncommitted changes beforehand:
cd ~/ez/e3sm_diags
git status
cd ~/ez/zppy-interfaces
git status
cd ~/ez/zppy
git status

cd /home/ac.forsyth2/ez/zppy_main_branch_tests/test_20260123
cp ~/ez/zppy/tests/main_branch_testing/* . # Copy, so the script isn't affected by the branch change
emacs run_integration_test.bash # Configure parameters

screen # Run on screen
cd /home/ac.forsyth2/ez/zppy_main_branch_tests/test_20260123 # If not there already
# Bypass manual checkpoints, tee output:
time ./run_integration_test.bash --date 20260123_run1 --auto 2>&1 | tee integration_test.log
# CTRL A D to exit screen
screen -ls # Check which node the screen is on.
tail -f integration_test.log # Follow log updates
```
