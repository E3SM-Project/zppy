# zppy Agentic AI Integration Analysis

**Date:** 2026-01-07
**Purpose:** Scope how agentic AI can help auto-setup and run zppy on HPCs

---

## zppy Overview

**zppy** (pronounced "zippee") is an E3SM (Energy Exascale Earth System Model) post-processing toolchain written in Python that automates common post-processing tasks.

### Key Characteristics:
- **Purpose**: Speed up post-processing of E3SM climate simulations
- **Workflow**: Configuration-driven task orchestration
- **Execution**: Generates and submits SLURM batch scripts with dependency management
- **Supported HPCs**: Perlmutter (pm-cpu/pm-gpu), Chrysalis, Anvil, Compy
- **Main Tasks**:
  - `climo`: Climate climatologies (monthly, diurnal)
  - `ts`: Time series generation
  - `e3sm_diags`: Diagnostic analysis
  - `e3sm_to_cmip`: CMIP format conversion
  - `mpas_analysis`: Ocean/ice analysis
  - `ilamb`: Land model benchmarking
  - `tc_analysis`: Tropical cyclone analysis
  - `global_time_series`: Global time series plots

### Current Architecture:
```
User creates .cfg → zppy validates → Generates .bash scripts →
Submits to SLURM → Monitors .status files → Manages dependencies
```

---

## Key Agentic AI Opportunities

### 1. Configuration File Generation & Validation

**Current Challenge:**
- Users must manually create complex `.cfg` files with 100+ parameters
- Configuration requires deep knowledge of:
  - Parameter schema (default.ini has ~100 parameters)
  - HPC-specific paths, accounts, partitions
  - Task dependencies and parameter interactions
- Easy to make syntax errors or incompatible parameter combinations
- Example minimal config still needs ~15 parameters set correctly

**AI Agent Capabilities:**

**Interactive Configuration Builder**
```
Agent: "What would you like to analyze?"
User: "I want to run atmospheric diagnostics for my simulation"

Agent: "Let me help configure this. I've detected you're on Perlmutter."
      → Auto-detects machine from hostname/environment

Agent: "What's your case name?"
User: "v3.LR.historical_0101"

Agent: "I found your data at /global/cfs/cdirs/e3sm/...
       I see 50 years of monthly output (1985-2034).
       Which years should I process?"
User: "1985-1989"

Agent: "For atmospheric diagnostics, I recommend these sets:
       - lat_lon (geographic distributions)
       - zonal_mean_xy (zonal averages)
       - annual_cycle_zonal_mean (seasonal cycles)
       Would you like to add more?"

→ Generates complete validated cfg file
```

**Intelligent Defaults & Inference**
- Automatically set `mapping_file` based on grid resolution detected from input files
- Infer `component` (atm/lnd/ocn) from `input_files` pattern
- Set `environment_commands` based on detected E3SM-Unified installation
- Choose optimal `partition` and `qos` based on job size

**Validation & Error Prevention**
- Check parameter compatibility before submission
- Verify required dependencies exist (e.g., e3sm_diags needs climo or ts)
- Validate paths and file existence
- Warn about common mistakes:
  - Missing trailing comma in `years` list
  - Incorrect `mapping_file` path
  - Incompatible `grid` and `mapping_file` combinations

**Template Customization**
- Adapt predefined campaigns (water_cycle, cryosphere, high_res_v1) to user needs
- Learn from user's previous configs to suggest personalized defaults

---

### 2. Intelligent Dependency Management

**Current Challenge:**
- Complex dependency chains require manual specification:
  ```
  e3sm_diags → depends on → climo → depends on → raw model output
                    or
  e3sm_diags → depends on → ts → depends on → raw model output
  ```
- Users must understand task relationships and specify them correctly
- Bundle configuration requires grouping compatible tasks manually
- Errors in dependency specification cause cascading failures

**AI Agent Capabilities:**

**Automatic Dependency Discovery**
```python
User: "I want to run e3sm_diags with lat_lon set"

Agent analyzes:
- lat_lon set requires climatology data
- No [climo] section in config
- Automatically adds climo task with matching parameters:
  [climo]
    grid = "180x360_aave"  # matches e3sm_diags grid
    years = "1985:1989:4"   # matches e3sm_diags years
    frequency = "monthly"    # required for lat_lon
```

**Optimal Task Bundling**
- Analyze walltime, resource requirements, and dependencies
- Group compatible tasks into bundles to reduce queue wait time
- Suggested bundles based on efficiency analysis:
  ```
  Bundle 1: All climo tasks (similar walltime, no dependencies)
  Bundle 2: All ts tasks (run in parallel)
  Bundle 3: e3sm_diags tasks (run after Bundle 1 completes)
  ```

**Dependency Graph Visualization**
```
Agent: "Here's your workflow plan:

┌─────────────────┐
│ climo_monthly   │ (30 min)
│ 1985-1989       │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ e3sm_diags      │ (2 hours)
│ lat_lon, zonal  │
└─────────────────┘

Total estimated time: 2.5 hours
Resource cost: ~150 node-hours
Proceed? (y/n)"
```

**Smart Recovery**
```
Agent monitors:
climo_monthly_1985-1989.status → "ERROR (3)"

Agent reads log:
"ncclimo: Missing input file for 1987-06"

Agent: "Climatology job failed due to missing June 1987 data.
       Options:
       1. Run for 1985-1986, 1988-1989 separately (exclude 1987)
       2. Check if data exists elsewhere
       3. Skip this task and continue with ts-based diagnostics

       I recommend option 3 - I can reconfigure e3sm_diags
       to use time series instead. Should I proceed?"
```

---

### 3. HPC Environment Setup & Detection

**Current Challenge:**
- Manual environment configuration required:
  - Load E3SM-Unified environment
  - Set machine-specific parameters (account, partition, constraint)
  - Configure paths (diagnostics_base_path, web_portal paths)
  - Ensure proper conda/module environment
- Different procedures for different machines
- Users may not know their account name, available partitions, or resource limits

**AI Agent Capabilities:**

**Auto-Environment Detection**
```python
Agent detects:
├─ Machine: Perlmutter (from hostname perlmutter-p1.nersc.gov)
├─ Architecture: pm-cpu (from SLURM constraint)
├─ User: chengzhu
├─ Available accounts: e3sm, m1234, m5678
├─ Default account: e3sm (from sacctmgr)
├─ Available partitions: regular, debug, premium
├─ E3SM-Unified: /global/common/software/e3sm/anaconda_envs/
│   └─ Latest: load_latest_e3sm_unified_pm-cpu.sh
├─ Input data conventions: /global/cfs/cdirs/e3sm/
└─ Web portal: /global/cfs/cdirs/e3sm/www → https://portal.nersc.gov/cfs/e3sm/

Auto-generates environment_commands:
"source /global/common/software/e3sm/anaconda_envs/load_latest_e3sm_unified_pm-cpu.sh"
```

**Environment Setup Automation**
- For new/unsupported machines, generate setup scripts
- Test environment before job submission
- Detect and warn about missing dependencies (ncclimo, e3sm_diags, etc.)

**Account & Partition Selection**
```
Agent: "I found 3 accounts available to you:
       - e3sm (priority: normal, QOS: regular)
       - m1234 (priority: high, QOS: premium)
       - m5678 (priority: low, QOS: regular)

       Your jobs will take ~150 node-hours.
       I recommend 'm1234' for fastest turnaround.

       For partition, I suggest:
       - 'regular' for climo (short jobs, <30min)
       - 'regular' for e3sm_diags (long jobs, 2+ hours)

       Estimated queue wait: 15 minutes"
```

**Path Inference**
```python
# Agent searches common locations:
search_patterns = [
    "/global/cfs/cdirs/e3sm/{case}",
    "/global/cscratch1/sd/{user}/{case}",
    "$SCRATCH/{case}",
]

Agent: "Searching for case 'v3.LR.historical_0101'...
       Found at: /global/cfs/cdirs/e3sm/www/Tutorials/v3.LR.historical_0101

       Detected structure:
       ├─ archive/atm/hist/ (EAM monthly: eam.h0)
       ├─ archive/lnd/hist/ (ELM monthly: elm.h0)
       └─ archive/ocn/hist/ (MPAS-Ocean)

       Auto-setting input paths for all components."
```

---

### 4. Job Monitoring & Adaptive Execution

**Current Challenge:**
- Manual monitoring required:
  ```bash
  cd /path/to/scripts
  grep -v "OK" *status  # Check for non-OK statuses
  squeue -u $USER       # Check SLURM queue
  cat *.status          # Read individual status files
  ```
- No automatic retry on transient failures (node failures, timeout on I/O)
- Resource waste: jobs may request too much/too little time or nodes
- Users must periodically check and manually intervene

**AI Agent Capabilities:**

**Real-time Job Monitoring Dashboard**
```
Agent: "Monitoring your zppy run...

┌──────────────────────────────────────────────┐
│ zppy Job Status - v3.LR.historical_0101      │
├──────────────────────────────────────────────┤
│ ✓ climo_monthly_1985-1989      OK (25m 34s) │
│ ⟳ e3sm_diags_lat_lon           RUNNING       │
│   └─ Job ID: 12345678                        │
│   └─ Progress: 65% (13/20 sets complete)     │
│   └─ Runtime: 1h 23m / 2h limit              │
│   └─ ETA: 37 minutes                         │
│ ⏸ e3sm_diags_zonal_mean        WAITING       │
│   └─ Dependency: e3sm_diags_lat_lon          │
└──────────────────────────────────────────────┘

Last updated: 2026-01-07 14:32:15
```

**Failure Analysis & Auto-Retry**
```python
# Analyze error patterns
error_patterns = {
    "ncclimo: error while loading shared libraries": {
        "type": "environment",
        "fix": "reload_module",
        "retry": True
    },
    "slurmstepd: error: .*: Killed": {
        "type": "out_of_memory",
        "fix": "increase_memory",
        "retry": True
    },
    "FileNotFoundError: .*\.nc": {
        "type": "missing_data",
        "fix": "manual_intervention",
        "retry": False
    }
}

Agent: "Job climo_monthly_1985-1989 failed with:
       'slurmstepd: error: Killed (memory limit)'

       This is a transient resource issue.
       I'm resubmitting with 2x memory (was 64GB → now 128GB)

       Retry 1/3... Job submitted: 12345679"
```

**Resource Optimization via Learning**
```python
# Track completed jobs
job_history = {
    "climo_monthly_4yr": {
        "requested_walltime": "00:30:00",
        "actual_runtime": "00:18:32",
        "efficiency": 62%,
        "nodes": 1
    }
}

Agent: "Based on 15 previous climo jobs for 4-year periods:
       - Average runtime: 19 minutes
       - Your current config requests: 30 minutes

       Recommendation: Keep 30 min (good buffer for variability)

       For e3sm_diags lat_lon set:
       - Your config requests: 2 hours, 8 workers
       - Historical average: 1h 15m with 8 workers
       - Suggestion: Request 1:30:00 to reduce queue wait time"
```

**Proactive Notifications**
```
Agent (Slack/Email):
"🎉 Your zppy run completed successfully!

Summary:
- Total runtime: 3h 42m
- Jobs completed: 5/5
- Output location: /global/cfs/.../post/
- Web viewer: https://portal.nersc.gov/.../

View results: https://portal.nersc.gov/cfs/e3sm/chengzhu/..."
```

---

### 5. Intelligent Workflow Orchestration

**Current Challenge:**
- zppy generates all scripts upfront with static parameters
- Cannot adapt to:
  - Partial data availability
  - Runtime discoveries (e.g., finding only 3 years of data instead of expected 5)
  - Intermediate results quality
- Users must manually run zppy multiple times for multi-stage workflows
- No coordination between multiple related campaigns

**AI Agent Capabilities:**

**Dynamic Workflow Adjustment**
```python
# During climo execution, agent discovers data availability
Agent: "Processing climatology for 1985-1989...

       ⚠️  Input data availability check:
       ✓ 1985: Complete (12 months)
       ✓ 1986: Complete (12 months)
       ✓ 1987: Partial (11 months - missing June)
       ✓ 1988: Complete (12 months)
       ✗ 1989: Missing

       Options:
       1. Process 1985-1988 (excluding 1989)
       2. Process 1985-1986, 1988 separately (excluding 1987-June)
       3. Continue with gaps (may produce incorrect climatology)

       I recommend option 1. Should I adjust the workflow?"

User: "yes"

Agent: "Adjusting workflow:
       - Updating climo years: 1985-1988
       - Propagating to downstream tasks (e3sm_diags)
       - Resubmitting jobs with corrected parameters..."
```

**Data Availability Checking**
```python
# Before job submission
Agent: "Validating input data for all tasks...

Checking: /global/cfs/cdirs/e3sm/v3.LR.historical_0101/archive/atm/hist/
├─ Expected files: v3.LR.historical_0101.eam.h0.1985-*.nc (12 files)
├─ Found: 12/12 ✓
├─ Total size: 45 GB
└─ Date range: 1985-01 to 1985-12 ✓

Checking: Years 1986-1989...
└─ All files present ✓

Checking: Mapping file
├─ Path: /global/cfs/cdirs/e3sm/diagnostics/maps/
│        map_ne30pg2_to_cmip6_180x360_aave.20200201.nc
└─ Exists ✓ (234 MB)

✅ All input data validated. Safe to proceed."
```

**Multi-stage Orchestration**
```
# Complex workflow example
User: "I want to run a full diagnostic suite comparing 3 simulations"

Agent creates multi-stage plan:

Stage 1: Process individual simulations (parallel)
├─ Simulation A: climo + ts + e3sm_diags
├─ Simulation B: climo + ts + e3sm_diags
└─ Simulation C: climo + ts + e3sm_diags

Stage 2: Comparison diagnostics (after Stage 1)
├─ e3sm_diags: A vs B
├─ e3sm_diags: A vs C
└─ e3sm_diags: B vs C

Stage 3: Summary generation
└─ Aggregate results into comparison dashboard

Agent: "This workflow will:
       - Submit 9 jobs in Stage 1 (3 sims × 3 tasks)
       - Wait for Stage 1 completion
       - Auto-submit 3 comparison jobs
       - Generate final dashboard

       Estimated total time: 6 hours
       I'll notify you at each stage completion."
```

**Parallel Campaign Management**
```
Agent tracks multiple concurrent workflows:

Campaign: v3_LR_historical (Status: Running)
├─ 1850-1900: ✓ Complete
├─ 1900-1950: ⟳ Running (65%)
└─ 1950-2000: ⏸ Queued

Campaign: v3_HR_amip (Status: Running)
├─ 1980-1990: ✓ Complete
└─ 1990-2000: ⟳ Running (23%)

Campaign: v2_LR_piControl (Status: Queued)
└─ Waiting for resources (current load: 85%)

Agent: "High cluster load detected (85% utilization).
       Delaying v2_LR_piControl submission by 2 hours
       to avoid long queue times."
```

---

### 6. Testing & Validation Automation

**Current Challenge:**
- Complex integration test setup:
  ```bash
  # Edit UNIQUE_ID in tests/integration/utils.py
  pip install .
  python tests/integration/utils.py  # Generate test configs
  zppy -c tests/integration/generated/test_*_chrysalis.cfg
  cd output/post/scripts
  grep -v "OK" *status  # Manual verification
  pytest tests/integration/test_*.py  # Run comparisons
  ```
- Manual comparison of generated bash scripts vs expected files
- Tedious process to update expected files after code changes
- No automated validation of scientific correctness of outputs

**AI Agent Capabilities:**

**Automated Test Execution**
```python
Agent: "Running zppy integration tests...

Setting up test environment:
├─ Detected machine: Chrysalis
├─ Generating test configs (UNIQUE_ID: 20260107_143215)
├─ Installing zppy: pip install .
└─ Generated 47 test configurations

Executing tests (in parallel):
├─ test_min_case_e3sm_diags_depend_on_climo ⟳
├─ test_bundles ⟳
├─ test_campaign_high_res_v1 ⏸
└─ ...

Progress: 12/47 complete (25%)
ETA: 2 hours 15 minutes
```

**Result Validation with Diff Analysis**
```python
Agent: "Comparing outputs vs expected results...

test_bash_generation:
├─ climo.bash: ✓ Match
├─ e3sm_diags.bash: ⚠️  Difference found
│   Line 45: Expected '-v FSNTOA,FLUT'
│            Got      '-v FSNTOA,FLUT,RESTOM'
│
│   This is due to your recent change adding RESTOM to default vars.
│   Action: Update expected file? (y/n)
│
└─ ts.bash: ✓ Match

test_settings_files:
├─ climo_atm_monthly_1985-1989.settings: ✓ Match
└─ e3sm_diags_lat_lon_1985-1989.settings: ✓ Match
```

**Regression Detection**
```python
Agent: "⚠️  Regression detected!

Your change to utils.py:get_years() affects 23 test cases:
├─ test_min_case_e3sm_diags_* (12 cases) ✗
├─ test_campaign_* (8 cases) ✗
└─ test_bundles (3 cases) ✗

Common failure pattern:
  Expected year range: 1985-1989
  Got year range: 1985-1988

Root cause: Off-by-one error in year range calculation

Suggested fix:
  Line 274: while year2 <= year_end:
  Should be: while year2 <= year_end + 1:

Apply fix? (y/n)"
```

**Test Configuration Generation**
```python
User: "I just added a new 'precipitation_analysis' task"

Agent: "I'll create integration tests for your new task.

Generating test configurations:
├─ test_min_case_precipitation_analysis.cfg
│   └─ Minimal config testing basic functionality
├─ test_precipitation_analysis_depend_on_climo.cfg
│   └─ Tests dependency on climatology
└─ test_precipitation_analysis_custom_regions.cfg
    └─ Tests with regional subsetting

Adding test to test_suite.py:
├─ test_precipitation_analysis_bash_generation()
├─ test_precipitation_analysis_settings_files()
└─ test_precipitation_analysis_execution()

Running new tests... (3/3 passed ✓)
```

---

### 7. Documentation & Tutorial Generation

**Current Challenge:**
- Extensive documentation, but hard to find relevant information
- Generic examples don't match user's specific scenario
- Parameter interactions not always clear from docs
- Steep learning curve for new users

**AI Agent Capabilities:**

**Context-Aware Help**
```python
User: "What does mapping_file do?"

Agent: "In your current config, you have:
       mapping_file = 'map_ne30pg2_to_cmip6_180x360_aave.20200201.nc'

       This tells ncclimo to regrid your native ne30pg2 data to a
       regular 180×360 lat-lon grid using area-averaging.

       The mapping file specifies the weights for this regridding.

       Options:
       - Keep current (recommended for standard analysis)
       - Use '' (empty) to keep native grid
       - Use 'glb' for global averages only

       Note: Your e3sm_diags task expects '180x360_aave' grid,
       so changing this would require updating e3sm_diags config too."

# Contextual to user's actual config, not generic docs
```

**Example Generation**
```python
User: "Show me an example for MPAS ocean analysis"

Agent: "Based on your case 'v3.LR.historical_0101', here's a complete
       config for MPAS ocean analysis:

[default]
case = "v3.LR.historical_0101"
input = "/global/cfs/cdirs/e3sm/v3.LR.historical_0101"
output = "/global/cscratch1/sd/chengzhu/zppy_output/v3.LR.historical_0101"
www = "/global/cfs/cdirs/e3sm/www/chengzhu/v3.LR.historical_0101"
partition = "regular"
account = "e3sm"

[mpas_analysis]
active = True
walltime = "3:00:00"
mesh = "EC30to60E2r2"
years = "1985:1989:5",

  [[climo]]
  input_subdir = "archive/ocn/hist"

  [[timeSeries]]
  input_subdir = "archive/ocn/hist"

This will:
1. Generate ocean climatologies for 1985-1989
2. Create time series of ocean variables
3. Run MPAS-Analysis diagnostic plots
4. Publish results to web portal

Estimated runtime: 3 hours
Save this config? (y/n)"
```

**Troubleshooting Assistant**
```python
User: "I'm getting 'ERROR (3)' in climo status"

Agent: "Let me analyze your climo log file...

Found error:
'ncclimo: error while loading shared libraries: libnetcdf.so.19'

This is an environment issue. The ncclimo tool can't find NetCDF library.

Diagnosis:
├─ Your environment_commands:
│   "source /global/common/.../load_latest_e3sm_unified_pm-cpu.sh"
├─ This should provide NetCDF, but something went wrong
└─ Possible causes:
    1. E3SM-Unified environment not activated in job
    2. Module conflicts
    3. Corrupted conda environment

Fix:
Add this to your config's environment_commands:

environment_commands = '''
source /global/common/software/e3sm/anaconda_envs/load_latest_e3sm_unified_pm-cpu.sh
which ncclimo  # Verify ncclimo is found
ldd $(which ncclimo) | grep netcdf  # Verify NetCDF library
'''

This adds diagnostics to verify the environment is correct.

Apply this fix? (y/n)"
```

**Best Practices Suggestions**
```python
Agent: "Analyzing your config for optimization opportunities...

✓ Good: You're using bundles to group tasks efficiently
✓ Good: walltime estimates are reasonable
⚠️  Suggestion: Your e3sm_diags runs all sets sequentially

Recommended improvement:
Instead of:
  [e3sm_diags]
  sets = "lat_lon","zonal_mean_xy","polar",...

Split into subsections for parallel execution:
  [e3sm_diags]

    [[quick_sets]]
    sets = "lat_lon","zonal_mean_xy"
    walltime = "00:30:00"

    [[medium_sets]]
    sets = "polar","cosp_histogram"
    walltime = "01:00:00"

    [[slow_sets]]
    sets = "meridional_mean_2d","aerosol_budget"
    walltime = "02:00:00"

Benefit:
- All three run in parallel (total time: 2hr vs 3.5hr sequential)
- Better resource allocation (fast jobs don't wait in queue)
- More granular restarts if one fails

Apply this optimization? (y/n)"
```

---

### 8. Autonomous Execution & Workflow Control

**Current Challenge:**
- Users must manually run `zppy -c config.cfg` after creating configurations
- No end-to-end automation from intent to results
- Multi-stage workflows require manual intervention between stages
- Users must remember to check on jobs and resubmit failures

**AI Agent Capabilities:**

**End-to-End Workflow Execution**
```python
# Full autonomous mode
$ zppy-ai run "analyze v3.LR.historical_0101 with e3sm_diags for 1985-1989"

Agent: "Understanding your request...

       I will:
       1. Generate configuration for e3sm_diags
       2. Add required climo dependency
       3. Validate all inputs exist
       4. Submit jobs to SLURM
       5. Monitor until completion
       6. Notify you when done

       Estimated cost: 50 node-hours on 'e3sm' allocation

       Proceeding... (use --confirm to require approval)

       ✓ Config generated: /tmp/zppy_ai_20260107_143215.cfg
       ✓ Validation passed
       ✓ Submitted: climo_monthly_1985-1989 (Job 12345678)
       ✓ Submitted: e3sm_diags_lat_lon (Job 12345679, depends on 12345678)

       Monitoring jobs... (Ctrl+C to detach, jobs continue running)"
```

**Configurable Autonomy Levels**
```python
# Level 0: Advisory only (current behavior)
$ zppy-ai configure "e3sm_diags for my simulation"
→ Generates config, shows it, exits
→ User manually runs: zppy -c config.cfg

# Level 1: Confirm before submit (default)
$ zppy-ai run "e3sm_diags for my simulation"
→ Generates config
→ Shows summary: "This will submit 3 jobs using 50 node-hours"
→ Asks: "Proceed? (y/n)"
→ User confirms, then submits

# Level 2: Auto-submit with limits
$ zppy-ai run --auto-submit --max-node-hours=100 "full diagnostics"
→ Generates config
→ Validates cost < 100 node-hours
→ Submits automatically
→ Monitors and retries failures

# Level 3: Full autonomy (power users)
$ zppy-ai run --autonomous "process all pending simulations"
→ Discovers simulations needing processing
→ Generates configs for each
→ Manages submission queue to respect allocation limits
→ Handles all failures automatically
→ Reports summary when complete
```

**Execution Safeguards**
```python
# Built-in safety controls
class ExecutionSafeguards:
    max_node_hours_per_run: int = 100      # Prevent runaway costs
    max_concurrent_jobs: int = 10          # Don't flood queue
    require_confirmation_above: int = 50   # Confirm large runs
    allowed_partitions: List[str] = ["regular", "debug"]  # No premium without explicit ok
    blocked_actions: List[str] = ["delete", "overwrite"]  # Never auto-delete

    # Audit trail
    log_all_submissions: bool = True       # Record what was submitted
    log_file: str = "~/.zppy-ai/audit.log"

# Example safeguard in action
Agent: "⚠️  This workflow would use 250 node-hours.
       Your limit is set to 100 node-hours per run.

       Options:
       1. Submit partial workflow (first 100 node-hours)
       2. Increase limit: --max-node-hours=250
       3. Cancel and review config

       Choose [1/2/3]:"
```

**Workflow Chaining**
```python
# Define multi-stage autonomous workflows
$ zppy-ai run --workflow=full_analysis "v3.LR.historical_0101"

# Workflow definition (YAML or discovered from intent)
full_analysis:
  stage1:
    - climo_monthly
    - ts_monthly
  stage2:  # Runs after stage1 completes
    - e3sm_diags (depends: climo_monthly)
    - global_time_series (depends: ts_monthly)
  stage3:  # Runs after stage2 completes
    - publish_to_portal
    - notify_user

Agent: "Executing 'full_analysis' workflow...

       Stage 1: Generating climatologies and time series
       ├─ climo_monthly: RUNNING (Job 12345678)
       └─ ts_monthly: RUNNING (Job 12345679)

       Stage 2: Waiting for Stage 1...
       Stage 3: Waiting for Stage 2...

       [Auto-advancing when dependencies complete]"
```

**Detached Execution with Reconnect**
```python
# Start a long workflow and detach
$ zppy-ai run --detach "full diagnostics for v3.LR.historical"
Agent: "Workflow started. Session ID: zppy-ai-20260107-143215

       To check status:  zppy-ai status zppy-ai-20260107-143215
       To reconnect:     zppy-ai attach zppy-ai-20260107-143215
       To cancel:        zppy-ai cancel zppy-ai-20260107-143215

       You'll receive email notification when complete."

# Later, reconnect to see progress
$ zppy-ai attach zppy-ai-20260107-143215
Agent: "Reconnected to workflow 'zppy-ai-20260107-143215'

       Progress: Stage 2 of 3 (67% complete)
       ├─ Stage 1: ✓ Complete
       ├─ Stage 2: ⟳ Running (2/3 jobs done)
       └─ Stage 3: ⏸ Waiting

       ETA: 45 minutes"
```

---

## Implementation Architecture

### Suggested AI Agent Stack

```
┌─────────────────────────────────────────────────────────┐
│                    User Interface Layer                 │
│  ┌────────────┬──────────────┬─────────────────────┐   │
│  │ CLI Agent  │ Web Dashboard│ Slack/Email Notifs  │   │
│  └────────────┴──────────────┴─────────────────────┘   │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│              Core Orchestration Layer                   │
│  ┌──────────────────────────────────────────────────┐  │
│  │         Configuration Agent (Primary)             │  │
│  │  - User interaction & requirements gathering      │  │
│  │  - Config generation & validation                 │  │
│  │  - RAG over zppy docs + examples                  │  │
│  └──────────────────────────────────────────────────┘  │
│                          │                              │
│  ┌──────────────────────▼───────────────────────────┐  │
│  │          Execution Agent (NEW)                    │  │
│  │  - Autonomy level management (0-3)                │  │
│  │  - Safeguards & cost control                      │  │
│  │  - Workflow orchestration & chaining              │  │
│  │  - Session management (detach/attach)             │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                         │
    ┌────────────────┬───┴───┬────────────────┐
    │                │       │                │
┌───▼────────┐ ┌─────▼─────┐ │ ┌──────────────▼─┐
│ HPC Env    │ │ Execution │ │ │ Data Validation│
│ Agent      │ │ Monitor   │ │ │ Agent          │
│            │ │ Agent     │ │ │                │
│ - Machine  │ │ - Job     │ │ │ - Input file   │
│   detection│ │   status  │ │ │   verification │
│ - Resource │ │ - Log     │ │ │ - Output QC    │
│   allocation│ │  analysis │ │ │ - Dependency   │
│ - Queue    │ │ - Auto-   │ │ │   resolution   │
│   mgmt     │ │   retry   │ │ │                │
└────────────┘ └───────────┘ │ └────────────────┘
    │                │       │        │
    └────────────────┴───────┴────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                 Integration Layer                       │
│  ┌───────────┬──────────┬────────────┬──────────────┐  │
│  │ SLURM API │ Filesystem│ zppy Core │ Vector DB    │  │
│  │ (sacct,   │ (glob,    │ (import   │ (docs, logs, │  │
│  │  squeue)  │  stat)    │  zppy.*)  │  examples)   │  │
│  └───────────┴──────────┴────────────┴──────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Component Details

#### 1. Configuration Agent (Primary Interface)
**Technologies:**
- LLM: GPT-4o / Claude 3.5 Sonnet for config generation
- RAG: Vector DB (Pinecone/Weaviate) over:
  - zppy documentation (docs/source/*.rst)
  - default.ini schema + comments
  - Example configs from tests/integration/
  - Historical user configs (anonymized)
- Schema validation: ConfigObj + custom validators

**Key Functions:**
```python
class ConfigurationAgent:
    def interactive_config_builder(self):
        """Step-by-step config generation via Q&A"""

    def validate_config(self, cfg: ConfigObj):
        """Deep validation beyond schema checking"""

    def suggest_improvements(self, cfg: ConfigObj):
        """Optimize config for efficiency"""

    def explain_parameter(self, param: str, context: dict):
        """Context-aware parameter documentation"""
```

#### 2. Execution Agent (NEW)
**Technologies:**
- Subprocess management: Python subprocess for zppy/sbatch calls
- Session persistence: SQLite or JSON for workflow state
- Background execution: Threading/asyncio for detached mode
- Notification: Slack API, email (smtplib)

**Key Functions:**
```python
class ExecutionAgent:
    def __init__(self, autonomy_level: int = 1):
        self.autonomy = autonomy_level  # 0=advisory, 1=confirm, 2=auto, 3=full
        self.safeguards = ExecutionSafeguards()
        self.session_store = SessionStore("~/.zppy-ai/sessions.db")

    def run_workflow(self, request: str, config: ConfigObj = None):
        """End-to-end workflow execution"""
        # 1. Generate config if not provided
        if config is None:
            config = self.config_agent.generate_from_request(request)

        # 2. Validate inputs
        validation = self.validator.verify_inputs(config)
        if not validation.passed:
            self.handle_validation_failure(validation)

        # 3. Estimate cost
        cost = self.estimate_node_hours(config)
        if not self.safeguards.approve_cost(cost, self.autonomy):
            return  # User declined or cost exceeded limits

        # 4. Execute zppy
        self.submit_zppy(config)

        # 5. Monitor (if not detached)
        if not self.detached:
            self.monitor.watch_until_complete(config)

    def submit_zppy(self, config: ConfigObj):
        """Actually run zppy to submit jobs"""
        config_path = self.write_config(config)
        result = subprocess.run(
            ['zppy', '-c', config_path],
            capture_output=True, text=True
        )
        self.audit_log.record(config_path, result)
        return result

    def detach(self, session_id: str):
        """Detach from running workflow, continue in background"""
        self.session_store.save(session_id, self.state)
        self.start_background_monitor(session_id)

    def attach(self, session_id: str):
        """Reconnect to detached workflow"""
        self.state = self.session_store.load(session_id)
        return self.get_current_status()

    def estimate_node_hours(self, config: ConfigObj) -> float:
        """Estimate total resource cost before submission"""
        total = 0.0
        for task in self.extract_tasks(config):
            walltime = self.parse_walltime(task['walltime'])
            nodes = task.get('nodes', 1)
            total += walltime * nodes
        return total


class ExecutionSafeguards:
    """Safety controls for autonomous execution"""

    def __init__(self):
        self.max_node_hours = 100
        self.max_concurrent_jobs = 10
        self.require_confirm_above = 50
        self.allowed_partitions = ["regular", "debug"]
        self.audit_log = AuditLog("~/.zppy-ai/audit.log")

    def approve_cost(self, cost: float, autonomy: int) -> bool:
        """Check if execution should proceed"""
        if cost > self.max_node_hours:
            print(f"Cost {cost} exceeds limit {self.max_node_hours}")
            return False

        if autonomy <= 1 and cost > self.require_confirm_above:
            return self.prompt_user_confirmation(cost)

        return True

    def check_queue_capacity(self) -> bool:
        """Ensure we don't flood the queue"""
        current_jobs = self.count_user_jobs()
        return current_jobs < self.max_concurrent_jobs
```

#### 3. HPC Environment Agent
**Technologies:**
- Machine detection: hostname parsing, SLURM env vars
- SLURM APIs: pyslurm or subprocess calls to sacct, squeue, sinfo
- Filesystem: pathlib, glob for path discovery
- Mache integration: Use existing MachineInfo class

**Key Functions:**
```python
class HPCEnvironmentAgent:
    def detect_machine(self) -> MachineInfo:
        """Auto-detect HPC system"""

    def find_available_resources(self):
        """Query SLURM for accounts, partitions, QOS"""

    def optimize_resource_request(self, task_type, data_size):
        """Suggest optimal nodes/walltime"""

    def verify_environment(self, env_commands: str):
        """Test environment setup before submission"""
```

#### 3. Execution Monitor Agent
**Technologies:**
- Job monitoring: Parse .status files, SLURM sacct/squeue
- Log analysis: LLM-based error interpretation
- Time-series DB: Store job metrics for learning
- Notification: Slack API, email (smtplib)

**Key Functions:**
```python
class ExecutionMonitorAgent:
    def monitor_jobs(self, script_dir: str):
        """Real-time job status tracking"""

    def analyze_failure(self, log_file: str) -> FailureAnalysis:
        """LLM-based error diagnosis"""

    def adaptive_retry(self, job: Job, failure: FailureAnalysis):
        """Auto-retry with fixes"""

    def estimate_completion(self, job: Job) -> timedelta:
        """Predict job completion time"""
```

#### 4. Data Validation Agent
**Technologies:**
- NetCDF validation: netCDF4-python, xarray
- File system scanning: concurrent.futures for parallel checks
- Pattern matching: regex for filename validation

**Key Functions:**
```python
class DataValidationAgent:
    def verify_input_files(self, config: dict) -> ValidationReport:
        """Check all input files exist and are valid"""

    def check_output_quality(self, output_dir: str) -> QualityReport:
        """Validate scientific correctness of outputs"""

    def resolve_dependencies(self, tasks: List[Task]) -> DependencyGraph:
        """Build and validate task dependency graph"""
```

---

### Key Technologies

#### LLM Selection
- **Primary**: Claude 3.5 Sonnet or GPT-4o
  - Config generation (complex reasoning)
  - Error interpretation (natural language understanding)
  - Documentation Q&A
- **Secondary**: GPT-4o-mini / Claude Haiku
  - Status updates (simple tasks)
  - Log parsing (pattern matching)
  - Notifications

#### RAG (Retrieval-Augmented Generation)
**Vector Database**: Pinecone, Weaviate, or ChromaDB
**Indexed Content**:
```python
documents = {
    "zppy_docs": {
        "source": "docs/source/**/*.rst",
        "chunks": 500,  # Chunk size
        "metadata": {"type": "documentation", "version": "3.1.0"}
    },
    "example_configs": {
        "source": "tests/integration/*.cfg",
        "chunks": 1000,
        "metadata": {"type": "example", "tested": True}
    },
    "error_patterns": {
        "source": "historical_logs/*.err",
        "chunks": 200,
        "metadata": {"type": "error_pattern", "resolution": "..."}
    },
    "parameter_schema": {
        "source": "zppy/defaults/default.ini",
        "chunks": 100,
        "metadata": {"type": "schema", "required": True/False}
    }
}
```

**Query Examples**:
```python
# User asks: "How do I configure e3sm_diags?"
rag_query("e3sm_diags configuration examples", top_k=5)
→ Returns: example configs, relevant doc sections, parameter descriptions

# Agent needs: "What causes 'ERROR (3)' in climo?"
rag_query("climo ERROR (3) ncclimo failure", top_k=3)
→ Returns: similar error logs with resolutions
```

#### Code Analysis
**Purpose**: Understand zppy internals for better assistance
```python
import ast
import inspect

class ZppyCodeAnalyzer:
    def parse_parameter_relationships(self):
        """Extract parameter dependencies from utils.py"""
        # Example: mapping_file affects grid calculation

    def extract_task_dependencies(self):
        """Build task dependency graph from __main__.py"""
        # Example: e3sm_diags requires climo OR ts

    def identify_validation_rules(self):
        """Find all parameter validation logic"""
        # Example: grid must match mapping_file target
```

#### HPC APIs
**SLURM Integration**:
```python
import subprocess
import json

def get_queue_status(user: str):
    """Query SLURM queue"""
    result = subprocess.run(
        ['squeue', '-u', user, '-o', '%i,%T,%M,%L'],
        capture_output=True, text=True
    )
    # Parse and return job statuses

def get_job_efficiency(job_id: int):
    """Get resource utilization"""
    result = subprocess.run(
        ['sacct', '-j', job_id, '--format=JobID,Elapsed,TotalCPU,MaxRSS'],
        capture_output=True, text=True
    )
    # Calculate efficiency metrics

def get_available_accounts():
    """List user's accounts and limits"""
    result = subprocess.run(
        ['sacctmgr', 'show', 'associations', 'user=$USER', '-P'],
        capture_output=True, text=True
    )
    # Parse account information
```

#### Graph Database (Optional)
**Purpose**: Store task dependency relationships
**Tool**: Neo4j or NetworkX (in-memory)
```python
# Example graph structure
graph = {
    "nodes": [
        {"id": "climo_monthly", "type": "task", "walltime": 1800},
        {"id": "e3sm_diags", "type": "task", "walltime": 7200},
        {"id": "ts_monthly", "type": "task", "walltime": 2400}
    ],
    "edges": [
        {"from": "climo_monthly", "to": "e3sm_diags", "type": "dependency"},
        {"from": "ts_monthly", "to": "e3sm_diags", "type": "dependency"}
    ]
}

# Query: "What tasks can run in parallel?"
# Answer: climo_monthly and ts_monthly (no interdependencies)
```

---

## Quick Win Opportunities

**Ranked by Impact vs Implementation Effort**

### 1. Config File Generator (HIGHEST IMPACT)
**Impact**: 80% time savings on initial setup
**Effort**: Medium (2-3 weeks)
**MVP**:
```python
# Simple CLI interface
$ zppy-ai configure

Agent: "What machine are you on?"
User: "Perlmutter"

Agent: "What's your case name?"
User: "v3.LR.historical_0101"

Agent: "What tasks? (climo/ts/e3sm_diags/mpas_analysis/...)"
User: "climo, e3sm_diags"

Agent: "What years?"
User: "1985-1989"

→ Generates complete validated config
→ Saves to post.v3.LR.historical_0101.cfg
→ Shows zppy command to run
```

### 2. Job Monitor Dashboard (HIGH IMPACT)
**Impact**: Eliminates manual status checking
**Effort**: Low (1 week)
**MVP**:
```python
# Auto-refresh terminal dashboard
$ zppy-ai monitor /path/to/scripts

┌─ zppy Monitor ─────────────────────────────┐
│ Refreshing every 30s... (Press 'q' to quit)│
├────────────────────────────────────────────┤
│ ✓ climo_monthly         OK                 │
│ ⟳ e3sm_diags_lat_lon    RUNNING (65%)      │
│ ⏸ e3sm_diags_zonal      WAITING            │
└────────────────────────────────────────────┘
```

### 3. Auto-Recovery System (HIGH IMPACT)
**Impact**: Handles transient failures without human intervention
**Effort**: Medium (2 weeks)
**MVP**:
```python
# Background daemon watching for failures
$ zppy-ai watch /path/to/scripts --auto-retry

Agent: "Monitoring 15 jobs..."
       "Job climo_monthly_1985-1989 failed (OOM)"
       "Auto-retrying with 2x memory..."
       "Resubmitted: Job 12345679"
```

### 4. Resource Optimizer (MEDIUM IMPACT)
**Impact**: 20-30% reduction in resource waste
**Effort**: Medium (2 weeks)
**MVP**:
```python
# Analyze historical jobs and suggest improvements
$ zppy-ai optimize my_config.cfg

Agent: "Analyzing your config...

       Recommendations:
       - climo: walltime=00:30:00 → 00:20:00 (saves queue time)
       - e3sm_diags: nodes=1 → nodes=2 (faster by 40%)

       Apply optimizations? (y/n)"
```

### 5. Environment Validator (MEDIUM IMPACT)
**Impact**: Catches environment errors before submission
**Effort**: Low (3 days)
**MVP**:
```python
# Pre-flight check before job submission
$ zppy-ai validate my_config.cfg

Agent: "Validating environment...
       ✓ Machine: Perlmutter (detected)
       ✓ Account: e3sm (valid)
       ✓ E3SM-Unified: found at /global/common/...
       ✓ ncclimo: version 5.2.3
       ✓ Input files: all present (1985-1989)
       ⚠️ Mapping file: not found at specified path
          Found at: /global/cfs/.../diagnostics/maps/...
          Update config? (y/n)"
```

### 6. Execution Agent with Hybrid Autonomy (HIGH IMPACT)
**Impact**: End-to-end automation with configurable control
**Effort**: Medium (2-3 weeks)
**MVP**:
```python
# Level 1: Confirm mode (default) - simplest to implement first
$ zppy-ai run "e3sm_diags for v3.LR.historical_0101"

Agent: "Generating configuration...
       ✓ Config: e3sm_diags with lat_lon, zonal_mean sets
       ✓ Dependencies: climo_monthly (auto-added)
       ✓ Years: 1985-1989

       This will submit 2 jobs:
       - climo_monthly_1985-1989 (30 min, 1 node)
       - e3sm_diags_lat_lon (2 hours, 1 node)

       Estimated cost: 2.5 node-hours on 'e3sm' allocation

       Proceed? [Y/n]"

User: "y"

Agent: "✓ Submitted climo_monthly_1985-1989 (Job 12345678)
       ✓ Submitted e3sm_diags_lat_lon (Job 12345679)

       Monitoring... (Ctrl+C to detach)

       [=========>          ] 45% - e3sm_diags running..."
```

**Implementation priority**:
1. First: Level 1 (confirm mode) - generates config, shows summary, waits for 'y'
2. Then: Monitoring integration - watch jobs after submission
3. Then: Level 2 (auto-submit) - add safeguards and limits
4. Finally: Level 3 (full autonomy) - add discovery and multi-workflow management

**Key safeguards to implement**:
```python
# ~/.zppy-ai/config.yaml
safeguards:
  max_node_hours_per_run: 100
  max_concurrent_jobs: 10
  require_confirmation_above: 50  # node-hours
  allowed_partitions: ["regular", "debug"]
  audit_log: "~/.zppy-ai/audit.log"

# All submissions logged for accountability
# audit.log format:
# 2026-01-07T14:32:15 | user=chengzhu | config=/tmp/zppy_ai_xxx.cfg | jobs=12345678,12345679 | cost=2.5nh
```

---

## Specific Code Integration Points

### Where to Hook AI Agents into zppy

#### 1. zppy/__main__.py
**Current**: Entry point, validates config, submits jobs
**Integration**:
```python
# Line 31-84: main() function
def main():
    args = _get_args()

    # NEW: AI-enhanced config loading
    if args.interactive:
        config_agent = ConfigurationAgent()
        user_config = config_agent.interactive_builder()
    else:
        user_config = ConfigObj(args.config, configspec=default_config)

    # NEW: Pre-submission validation
    validator_agent = DataValidationAgent()
    validation_report = validator_agent.verify_inputs(user_config)
    if not validation_report.passed:
        validator_agent.suggest_fixes(validation_report)
        if not confirm("Continue anyway?"):
            return

    # Existing zppy code continues...
    config = _handle_campaigns(user_config, default_config, defaults_dir)

    # NEW: Monitor jobs after submission
    if args.monitor:
        monitor_agent = ExecutionMonitorAgent()
        monitor_agent.watch(script_dir, auto_retry=args.auto_retry)
```

#### 2. zppy/utils.py
**Current**: Core utilities (submit_script, check_status, etc.)
**Integration**:
```python
# Line 403-486: submit_script() function
def submit_script(script_file, status_file, export, job_ids_file,
                  dependFiles=[], fail_on_dependency_skip=False):

    # NEW: Resource optimization
    if os.environ.get('ZPPY_AI_OPTIMIZE'):
        optimizer = ResourceOptimizer()
        optimized_script = optimizer.tune_resources(script_file)
        script_file = optimized_script

    # Existing submission code...
    jobid = int(out.split()[-1])

    # NEW: Register job with monitor
    if os.environ.get('ZPPY_AI_MONITOR'):
        monitor_agent.register_job(jobid, script_file, status_file)

    return jobid

# Line 356-365: check_status() function
def check_status(status_file: str) -> bool:
    skip: bool = False
    if os.path.isfile(status_file):
        with open(status_file, "r") as f:
            tmp = f.read().split()
        if tmp[0] in ("OK", "WAITING", "RUNNING"):
            skip = True

            # NEW: Enhanced status tracking
            if os.environ.get('ZPPY_AI_MONITOR'):
                monitor_agent.update_status(status_file, tmp[0])

    return skip
```

#### 3. zppy/bundle.py
**Current**: Bundle management and task grouping
**Integration**:
```python
# Line 98-123: handle_bundles() function
def handle_bundles(c, script_file, export, dependFiles=[], existing_bundles=[]):

    # NEW: AI-suggested bundling
    if os.environ.get('ZPPY_AI_BUNDLE'):
        bundler = IntelligentBundler()
        optimal_bundle = bundler.suggest_bundle(c, existing_bundles)
        c["bundle"] = optimal_bundle.name

    # Existing bundling logic...
    bundle_name = c["bundle"]
    # ...
```

#### 4. Machine Detection Enhancement
**Current**: zppy/__main__.py:171-184 (_get_machine_info)
**Integration**:
```python
def _get_machine_info(config: ConfigObj) -> MachineInfo:
    # NEW: Enhanced machine detection
    env_agent = HPCEnvironmentAgent()

    if ("machine" not in config["default"]) or (config["default"]["machine"] == ""):
        # Use AI agent for better detection
        machine_info = env_agent.detect_and_configure()

        # Auto-fill machine-specific parameters
        config["default"]["account"] = machine_info.recommended_account
        config["default"]["partition"] = machine_info.optimal_partition
        config["default"]["environment_commands"] = machine_info.env_commands

        return machine_info
    else:
        # Fall back to existing logic
        machine = config["default"]["machine"]
        return MachineInfo(machine=machine)
```

#### 5. New zppy/ai_agents/ Module
**Structure**:
```
zppy/
├── ai_agents/
│   ├── __init__.py
│   ├── config_agent.py       # Configuration generation
│   ├── execution_agent.py    # Workflow execution & autonomy control (NEW)
│   ├── hpc_env_agent.py      # Machine detection & setup
│   ├── monitor_agent.py      # Job monitoring & retry
│   ├── data_validator.py     # Input/output validation
│   ├── optimizer.py          # Resource optimization
│   ├── safeguards.py         # Cost limits & safety controls (NEW)
│   ├── session_manager.py    # Detach/attach session persistence (NEW)
│   └── rag/
│       ├── vector_store.py   # RAG implementation
│       └── embeddings/       # Cached embeddings
├── ai_cli.py                 # New zppy-ai entry point (NEW)
├── __main__.py
├── utils.py
└── ...
```

**New entry point (zppy-ai)**:
```python
# zppy/ai_cli.py - separate entry point for AI-enhanced CLI
from zppy.ai_agents import ConfigAgent, ExecutionAgent, MonitorAgent

def main():
    args = parse_args()

    if args.command == 'configure':
        agent = ConfigAgent()
        config = agent.generate_from_request(args.description)
        agent.save_config(config, args.output)

    elif args.command == 'run':
        agent = ExecutionAgent(autonomy_level=args.autonomy)
        agent.run_workflow(args.description, config=args.config)

    elif args.command == 'status':
        agent = ExecutionAgent()
        print(agent.get_status(args.session_id))

    elif args.command == 'attach':
        agent = ExecutionAgent()
        agent.attach(args.session_id)

    elif args.command == 'cancel':
        agent = ExecutionAgent()
        agent.cancel(args.session_id)

# setup.py entry_points:
# 'console_scripts': [
#     'zppy = zppy.__main__:main',
#     'zppy-ai = zppy.ai_cli:main',  # NEW
# ]
```

#### 6. New CLI Commands
**Add to zppy/__main__.py or new zppy-ai entry point**:
```python
# Extended argument parser for zppy-ai CLI
parser = argparse.ArgumentParser(prog='zppy-ai')
subparsers = parser.add_subparsers(dest='command')

# zppy-ai configure "description"
configure_parser = subparsers.add_parser('configure',
    help='Generate config from natural language description')
configure_parser.add_argument('description', type=str,
    help='Natural language description of what to run')
configure_parser.add_argument('--output', '-o', type=str,
    help='Output config file path')

# zppy-ai run "description" [options]
run_parser = subparsers.add_parser('run',
    help='Generate config AND execute workflow')
run_parser.add_argument('description', type=str,
    help='Natural language description of what to run')
run_parser.add_argument('--config', '-c', type=str,
    help='Use existing config instead of generating')

# Autonomy controls
run_parser.add_argument('--autonomy', type=int, choices=[0,1,2,3], default=1,
    help='Autonomy level: 0=advisory, 1=confirm (default), 2=auto-submit, 3=full')
run_parser.add_argument('--auto-submit', action='store_true',
    help='Shortcut for --autonomy=2')
run_parser.add_argument('--autonomous', action='store_true',
    help='Shortcut for --autonomy=3')
run_parser.add_argument('--confirm', action='store_true',
    help='Always require confirmation (--autonomy=1)')

# Safeguards
run_parser.add_argument('--max-node-hours', type=int, default=100,
    help='Maximum node-hours allowed (default: 100)')
run_parser.add_argument('--max-jobs', type=int, default=10,
    help='Maximum concurrent jobs (default: 10)')

# Session management
run_parser.add_argument('--detach', action='store_true',
    help='Start workflow and detach (continue in background)')
run_parser.add_argument('--monitor', action='store_true',
    help='Monitor jobs after submission')
run_parser.add_argument('--auto-retry', action='store_true',
    help='Automatically retry failed jobs')

# zppy-ai status <session-id>
status_parser = subparsers.add_parser('status',
    help='Check status of a running/completed workflow')
status_parser.add_argument('session_id', type=str)

# zppy-ai attach <session-id>
attach_parser = subparsers.add_parser('attach',
    help='Reconnect to a detached workflow')
attach_parser.add_argument('session_id', type=str)

# zppy-ai cancel <session-id>
cancel_parser = subparsers.add_parser('cancel',
    help='Cancel a running workflow')
cancel_parser.add_argument('session_id', type=str)

# zppy-ai validate <config>
validate_parser = subparsers.add_parser('validate',
    help='Validate config without submitting')
validate_parser.add_argument('config', type=str)

# zppy-ai optimize <config>
optimize_parser = subparsers.add_parser('optimize',
    help='Suggest resource optimizations for config')
optimize_parser.add_argument('config', type=str)
```

**Example usage patterns:**
```bash
# Level 0: Just generate config (advisory)
zppy-ai configure "e3sm_diags for v3.LR.historical_0101, years 1985-1989"

# Level 1: Generate and run with confirmation (default)
zppy-ai run "e3sm_diags for v3.LR.historical_0101"

# Level 2: Auto-submit within limits
zppy-ai run --auto-submit --max-node-hours=50 "climo for my simulation"

# Level 3: Full autonomy
zppy-ai run --autonomous "process all simulations in /path/to/data"

# Detached execution
zppy-ai run --detach "full diagnostic suite"
zppy-ai status zppy-ai-20260107-143215
zppy-ai attach zppy-ai-20260107-143215

# Use existing config with AI monitoring
zppy-ai run --config=my_config.cfg --monitor --auto-retry
```

---

## Data Flow Example

### Flow A: Advisory Mode (Autonomy Level 0)
**User maintains full control**:

```
1. User: "zppy-ai configure 'e3sm_diags for v3.LR.historical'"
   ↓
2. ConfigAgent: Analyze request, detect machine, find data
   ↓
3. ConfigAgent: Generate config → my_run.cfg
   ↓
4. User reviews config, makes manual edits
   ↓
5. User: "zppy -c my_run.cfg"  ← User runs manually
   ↓
6. User monitors jobs manually
```

### Flow B: Confirm Mode (Autonomy Level 1 - Default)
**AI executes with user approval**:

```
1. User: "zppy-ai run 'e3sm_diags for v3.LR.historical'"
   ↓
2. ConfigAgent: Generate config
   ↓
3. DataValidator: Check inputs → ✓ All valid
   ↓
4. ExecutionAgent: Estimate cost → 50 node-hours
   ↓
5. ExecutionAgent: "This will submit 3 jobs using 50 node-hours.
                    Proceed? (y/n)"
   ↓
6. User: "y"
   ↓
7. ExecutionAgent: subprocess.run(['zppy', '-c', 'config.cfg'])
   ↓
8. MonitorAgent: Watch until completion
   ↓
9. MonitorAgent: Notify user of results
```

### Flow C: Auto-Submit Mode (Autonomy Level 2)
**AI executes within defined limits**:

```
1. User: "zppy-ai run --auto-submit --max-node-hours=100 'full diagnostics'"
   ↓
2. ConfigAgent: Generate config
   ↓
3. ExecutionAgent: Estimate cost → 75 node-hours
   ↓
4. Safeguards: 75 < 100 limit → ✓ Approved
   ↓
5. ExecutionAgent: Submit automatically (no user prompt)
   ↓
6. MonitorAgent: Watch jobs
   → Job climo_monthly: RUNNING → OK
   → Job e3sm_diags: RUNNING → FAILED (OOM)
   ↓
7. MonitorAgent: Analyze failure, auto-retry with 2x memory
   ↓
8. MonitorAgent: → Job e3sm_diags_retry: OK
   ↓
9. Notify: "✅ Complete! View results at: ..."
```

### Flow D: Full Autonomy Mode (Autonomy Level 3)
**AI handles everything, including discovery**:

```
1. User: "zppy-ai run --autonomous 'process all new simulations'"
   ↓
2. ExecutionAgent: Discover simulations needing processing
   → Found: v3.LR.historical_0101 (unprocessed)
   → Found: v3.LR.historical_0102 (unprocessed)
   → Found: v3.LR.amip_0001 (already processed, skip)
   ↓
3. For each simulation:
   ├─ ConfigAgent: Generate appropriate config
   ├─ DataValidator: Verify inputs
   ├─ Safeguards: Check cumulative cost within limits
   └─ ExecutionAgent: Submit (respecting max concurrent jobs)
   ↓
4. ExecutionAgent: Manage submission queue
   → Simulation 1: Submitted (3 jobs)
   → Simulation 2: Queued (waiting for capacity)
   ↓
5. MonitorAgent: Watch all workflows
   → Handle failures, retry as needed
   → Auto-advance queued simulations as capacity frees
   ↓
6. Summary report when all complete:
   "Processed 2 simulations:
    - v3.LR.historical_0101: ✓ Complete
    - v3.LR.historical_0102: ✓ Complete
    Total: 150 node-hours, 6 jobs, 2 auto-retries
    Results: https://portal.nersc.gov/..."
```

### Flow E: Detached Execution
**Start workflow, disconnect, reconnect later**:

```
1. User: "zppy-ai run --detach 'full diagnostic suite'"
   ↓
2. ExecutionAgent: Generate session ID → zppy-ai-20260107-143215
   ↓
3. ExecutionAgent: Submit jobs, start background monitor
   ↓
4. ExecutionAgent: "Workflow started. Session: zppy-ai-20260107-143215
                    Detaching... (jobs continue in background)"
   ↓
5. User disconnects SSH, goes home
   ↓
   ... 3 hours later ...
   ↓
6. User: "zppy-ai attach zppy-ai-20260107-143215"
   ↓
7. ExecutionAgent: Load session state from ~/.zppy-ai/sessions.db
   ↓
8. ExecutionAgent: "Reconnected. Status: Complete ✓
                    All 5 jobs finished successfully.
                    Results: https://portal.nersc.gov/..."
```

---

## Conclusion

zppy is an **excellent candidate** for agentic AI enhancement because:

1. **Well-defined workflows**: Clear task structure (climo → ts → diags)
2. **Configuration complexity**: 100+ parameters provide high value for AI assistance
3. **HPC integration**: Machine-specific setup is tedious and error-prone
4. **Manual overhead**: Status checking, error recovery are time-consuming
5. **Rich documentation**: Good training data for RAG
6. **Existing structure**: Clean Python codebase easy to extend

**Expected impact**:
- **80% reduction** in configuration time
- **60% reduction** in monitoring overhead
- **40% improvement** in resource efficiency
- **90% reduction** in manual error recovery

**Next steps**:
1. Start with Config Generator (quick win, high impact)
2. Add Job Monitor (easy, immediate value)
3. Implement Auto-Recovery (medium effort, high reliability)
4. Build Resource Optimizer (learn from job history)
5. Create full orchestration system (long-term vision)

---

## Additional Resources

### Key Files Analyzed:
- `/global/u2/c/chengzhu/zppy/README.md` - Project overview
- `/global/u2/c/chengzhu/zppy/zppy/__main__.py` - Main entry point (302 lines)
- `/global/u2/c/chengzhu/zppy/zppy/utils.py` - Core utilities (491 lines)
- `/global/u2/c/chengzhu/zppy/zppy/bundle.py` - Bundle management (141 lines)
- `/global/u2/c/chengzhu/zppy/zppy/defaults/default.ini` - Config schema (100+ params)
- `/global/u2/c/chengzhu/zppy/zppy/templates/*.bash` - Job templates (Jinja2)

### Documentation:
- Official docs: https://docs.e3sm.org/zppy (redirect from e3sm-project.github.io/zppy)
- GitHub: https://github.com/E3SM-Project/zppy

### Contact:
- Authors: Ryan Forsyth, Chris Golaz
- Email: forsyth2@llnl.gov, golaz1@llnl.gov
- Q&A: https://github.com/E3SM-Project/zppy/discussions/categories/q-a
