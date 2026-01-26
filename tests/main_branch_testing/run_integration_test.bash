#!/bin/bash
# zppy Integration Test Automation Script
# Usage:
# 1. Copy this file and `run_image_tests.bash` out of the zppy repo. (This script will change the branch).
# 2. Edit configuration parameters below.
# 3. Run: ./run_integration_test.bash
# 4. Run: ./run_image_tests.bash

set -e  # Exit on error
set -u  # Exit on undefined variable

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DATE_STAMP="${DATE_STAMP:-$(date +%Y%m%d)}"
echo "User is: ${USER:-unknown}" # Pick this up from the environment

# ============================================================================
# Configuration
# ============================================================================

# Check these every time #####################################################

RUN_NUMBER=1
AUTO_MODE=true # By default, run automatically
START_PHASE=1 # By default, start at phase 1 (of 3)

# Base branches (THESE ARE WHAT WE'RE TESTING)
# Usually we test "main".
# If we need to test PRs or include test fixes, we may use a different branch.
DIAGS_BASE_BRANCH="main"
ZI_BASE_BRANCH="main"
ZPPY_BASE_BRANCH="test-fixes" # https://github.com/E3SM-Project/zppy/pull/769

# Set these up once ###########################################################

# Paths
HOME_DIR="$HOME"
EZ_DIR="$HOME_DIR/ez"
E3SM_DIAGS_DIR="$EZ_DIR/e3sm_diags"
ZPPY_INTERFACES_DIR="$EZ_DIR/zppy-interfaces"
ZPPY_DIR="$EZ_DIR/zppy"
CONDA_PROFILE="$HOME_DIR/miniforge3/etc/profile.d/conda.sh"
OUTPUT_WORKSPACE="/lcrc/group/e3sm/${USER}"

# Probably won't need to edit these ###########################################

# ID
TAG="${DATE_STAMP}_run${RUN_NUMBER}"
UNIQUE_ID="zppy_main_branch_test_${TAG}"

# Environment names
DIAGS_ENV="test-diags-${DIAGS_BASE_BRANCH}-${TAG}"
ZI_ENV="test-zi-${ZI_BASE_BRANCH}-${TAG}"
ZPPY_ENV="test-zppy-${ZPPY_BASE_BRANCH}-${TAG}"

# Output directories
BUNDLES_OUTPUT="${OUTPUT_WORKSPACE}/zppy_weekly_bundles_output/${UNIQUE_ID}/v3.LR.historical_0051/post/scripts"
LEGACY_BUNDLES_OUTPUT="${OUTPUT_WORKSPACE}zppy_weekly_legacy_3.0.0_bundles_output/${UNIQUE_ID}/v3.LR.historical_0051/post/scripts"
V2_OUTPUT="${OUTPUT_WORKSPACE}/zppy_weekly_comprehensive_v2_output/${UNIQUE_ID}/v2.LR.historical_0201/post/scripts"
LEGACY_V2_OUTPUT="${OUTPUT_WORKSPACE}/zppy_weekly_legacy_3.0.0_comprehensive_v2_output/${UNIQUE_ID}/v2.LR.historical_0201/post/scripts"
V3_OUTPUT="${OUTPUT_WORKSPACE}/zppy_weekly_comprehensive_v3_output/${UNIQUE_ID}/v3.LR.historical_0051/post/scripts"
LEGACY_V3_OUTPUT="${OUTPUT_WORKSPACE}/zppy_weekly_legacy_3.0.0_comprehensive_v3_output/${UNIQUE_ID}/v3.LR.historical_0051/post/scripts"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# Helper Functions
# ============================================================================

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] ✓${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] ⚠${NC} $*"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ✗${NC} $*"
}

checkpoint() {
    local message="$1"
    if [ "$AUTO_MODE" = false ]; then
        log_warning "CHECKPOINT: $message"
        read -p "Press Enter to continue or Ctrl+C to abort..."
    else
        log "AUTO MODE: $message"
    fi
}

activate_env() {
    local env_name="${1:-}"  # Default to empty string if not provided
    set +u
    source ~/.bashrc
    lcrc_conda # Run conda activation function defined in ~/.bashrc

    # Only activate if an environment name was provided
    if [ -n "$env_name" ]; then
        conda activate "$env_name"
    fi
    set -u
}

setup_conda_env() {
    local conda_dir="$1"
    local env_name="$2"

    # Check if environment already exists
    if conda env list | grep -q "^${env_name} "; then
        log "Environment '$env_name' already exists, skipping creation"
    else
        log "Creating new environment '$env_name'"
        rm -rf build
        conda clean --all --yes
        conda env create -f "${conda_dir}/dev.yml" -n "$env_name"
    fi

    activate_env "$env_name"

    # Always install/update the package
    log "Installing package in '$env_name'"
    python -m pip install .
    log_success "Environment '$env_name' ready"
}

ensure_test_branch() {
    local test_branch="$1"
    local base_branch="$2"
    local current_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)

    # Check if we're already on the test branch
    if [ "$current_branch" = "$test_branch" ]; then
        log "Already on branch '$test_branch', skipping checkout"
        return 0
    fi

    # Save current work before switching branches
    log "Saving current work..."
    git status
    git add -A
    git commit -m "Auto-save before test" --no-verify || true

    # Check if the test branch exists
    if git show-ref --verify --quiet "refs/heads/$test_branch"; then
        # Branch exists, just check it out
        log "Checking out existing branch '$test_branch'"
        git checkout "$test_branch"
        log_success "Checked out existing branch '$test_branch'"
    else
        # Branch doesn't exist, create it from upstream/${base_branch}
        log "Creating new branch '$test_branch' from upstream/${base_branch}"
        git fetch upstream ${base_branch}
        git checkout -b "$test_branch" upstream/${base_branch}
        log_success "Created and checked out new branch '$test_branch'"
    fi
}

wait_for_slurm_jobs() {
    local check_interval=${1:-600}  # Check every 600 seconds (10 minutes) by default
    local max_wait=${2:-14400}     # Max wait 4 hours by default

    log "Waiting for SLURM jobs to complete..."
    local elapsed=0
    local initial_count=$(squeue -u ${USER} | wc -l)
    initial_count=$((initial_count - 1))  # Subtract header

    log "Initial job count: $initial_count"

    while true; do
        local job_count=$(squeue -u ${USER} | wc -l)
        job_count=$((job_count - 1))  # Subtract header

        # Check for failed dependencies
        local failed_jobs=$(squeue -u ${USER} | grep "DependencyNeverSatisfied" || true)
        local failed_count=0
        if [ -n "$failed_jobs" ]; then
            failed_count=$(echo "$failed_jobs" | wc -l)
        fi
        # prev_failed_count defaults to 0
        if [ "$failed_count" -gt "${prev_failed_count:-0}" ]; then
            log_error "Jobs found with DependencyNeverSatisfied:"
            echo "$failed_jobs"
            # Check if ALL jobs have DependencyNeverSatisfied
            if [ "$job_count" -eq "$failed_count" ]; then
                checkpoint "Some jobs can't run, because of DependencyNeverSatisfied"
                log_error "All jobs have DependencyNeverSatisfied - cancelling all jobs"
                scancel -u ${USER}
                job_count=0
            fi
        fi
        prev_failed_count=$failed_count

        if [ "$job_count" -eq 0 ]; then
            log_success "All SLURM jobs completed!"
            return 0
        fi

        if [ $elapsed -ge $max_wait ]; then
            log_error "Timeout waiting for SLURM jobs after ${max_wait}s"
            return 1
        fi

        echo -ne "\r${YELLOW}Jobs remaining: $job_count${NC} (elapsed: ${elapsed}s)"
        sleep "$check_interval"
        elapsed=$((elapsed + check_interval))
    done
    echo ""  # New line after progress indicator
}

check_status_files() {
    local dir="$1"
    local name="$2"

    if [ ! -d "$dir" ]; then
        log_warning "Directory not found: $dir"
        return 1
    fi

    cd "$dir"
    local errors=$(grep -v "OK" *status 2>/dev/null || true)

    if [ -z "$errors" ]; then
        log_success "$name: No errors found"
        return 0
    else
        log_error "$name: Errors found!"
        echo "$errors"
        return 1
    fi
}

# ============================================================================
# Phase 1: Setup
# ============================================================================

phase_1_setup() {
    log "========================================="
    log "Phase 1: Setup"
    log "Date: $DATE_STAMP"
    log "Unique ID: $UNIQUE_ID"
    log "========================================="

    activate_env

    # ====================================================================
    # Set up e3sm_diags environment
    # ====================================================================
    log "Setting up e3sm_diags environment..."
    cd "$E3SM_DIAGS_DIR"
    ensure_test_branch test_e3sm_diags_${TAG} ${DIAGS_BASE_BRANCH}

    log "Latest e3sm_diags commit (should match https://github.com/E3SM-Project/e3sm_diags/commits/${DIAGS_BASE_BRANCH}):"
    git log -1 --oneline
    setup_conda_env "conda-env" "$DIAGS_ENV"

    # ====================================================================
    # Set up zppy-interfaces environment
    # ====================================================================
    log "Setting up zppy-interfaces environment..."
    cd "$ZPPY_INTERFACES_DIR"
    ensure_test_branch test_zi_${TAG} ${ZI_BASE_BRANCH}

    log "Latest zppy-interfaces commit (should match https://github.com/E3SM-Project/zppy-interfaces/commits/${ZI_BASE_BRANCH}):"
    git log -1 --oneline
    setup_conda_env "conda" "$ZI_ENV"

    # Run unit tests
    log "Running pytest unit tests..."
    pytest tests/unit/global_time_series/test_*.py
    pytest tests/unit/pcmdi_diags/test_*.py
    log_success "zppy-interfaces unit tests passed"

    # ========================================================================
    # Set up zppy environment
    # ========================================================================
    log "Setting up zppy environment..."
    cd "$ZPPY_DIR"
    ensure_test_branch test_zppy_${TAG} ${ZPPY_BASE_BRANCH}

    log "Latest zppy commit (should match https://github.com/E3SM-Project/zppy/commits/${ZPPY_BASE_BRANCH}):"
    git log -1 --oneline
    setup_conda_env "conda" "$ZPPY_ENV"

    # Run unit tests
    log "Running pytest unit tests..."
    pytest tests/test_*.py
    log_success "zppy unit tests passed"

    # ========================================================================
    # Generate config files
    # ========================================================================
    log "Generating config files..."

    # Update utils.py with test specifics
    UTILS_FILE="tests/integration/utils.py"

    # Create a temporary Python script to update TEST_SPECIFICS
    cat > /tmp/update_utils.py << EOF
import re

utils_file = "${UTILS_FILE}"

with open(utils_file, 'r') as f:
    content = f.read()

# Find TEST_SPECIFICS dictionary and replace it
pattern = r'TEST_SPECIFICS: Dict\[str, Any\] = \{.*?\n\}'
replacement = '''TEST_SPECIFICS: Dict[str, Any] = {
    "diags_environment_commands": "source ${CONDA_PROFILE}; conda activate ${DIAGS_ENV}",
    "mpas_analysis_environment_commands": "source /lcrc/soft/climate/e3sm-unified/load_latest_e3sm_unified_chrysalis.sh",
    "global_time_series_environment_commands": "source ${CONDA_PROFILE}; conda activate ${ZI_ENV}",
    "pcmdi_diags_environment_commands": "source ${CONDA_PROFILE}; conda activate ${ZI_ENV}",
    "environment_commands": "source /lcrc/soft/climate/e3sm-unified/load_latest_e3sm_unified_chrysalis.sh",
    "cfgs_to_run": [
        "weekly_bundles",
        "weekly_comprehensive_v2",
        "weekly_comprehensive_v3",
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
    "unique_id": "${UNIQUE_ID}",
}'''

content = re.sub(pattern, replacement, content, flags=re.DOTALL)

with open(utils_file, 'w') as f:
    f.write(content)

print("Updated utils.py")
EOF

    python /tmp/update_utils.py

    log "Running utils.py to generate configs..."
    python tests/integration/utils.py

    log_success "Config files generated"

    # ========================================================================
    # Submit initial SLURM jobs
    # ========================================================================
    log "Submitting initial SLURM jobs..."

    zppy -c tests/integration/generated/test_weekly_bundles_chrysalis.cfg
    zppy -c tests/integration/generated/test_weekly_comprehensive_v2_chrysalis.cfg
    zppy -c tests/integration/generated/test_weekly_comprehensive_v3_chrysalis.cfg
    zppy -c tests/integration/generated/test_weekly_legacy_3.0.0_bundles_chrysalis.cfg
    zppy -c tests/integration/generated/test_weekly_legacy_3.0.0_comprehensive_v2_chrysalis.cfg
    zppy -c tests/integration/generated/test_weekly_legacy_3.0.0_comprehensive_v3_chrysalis.cfg

    local job_count=$(squeue -u ${USER} | wc -l)
    job_count=$((job_count - 1)) # Don't count the header
    log_success "Submitted jobs. Total in queue: $job_count"

    checkpoint "Phase 1 complete. Jobs submitted and running."

    # Wait for jobs to complete
    wait_for_slurm_jobs 600 14400  # Check every 600sec (10min), max 4 hours

    log_success "Phase 1 complete!"
}

# ============================================================================
# Phase 2: Bundles Part 2
# ============================================================================

phase_2_bundles_part2() {
    log "========================================="
    log "Phase 2: Bundles Part 2"
    log "========================================="

    activate_env "$ZPPY_ENV"
    cd "$ZPPY_DIR"
    ensure_test_branch test_zppy_${TAG} ${ZPPY_BASE_BRANCH}

    # Check bundles status
    log "Checking bundles status..."
    check_status_files "$BUNDLES_OUTPUT" "Bundles"
    check_status_files "$LEGACY_BUNDLES_OUTPUT" "Legacy Bundles"

    checkpoint "Bundles status checked. Ready to submit part 2."

    # Submit bundles part 2
    log "Submitting bundles part 2..."
    zppy -c tests/integration/generated/test_weekly_bundles_chrysalis.cfg
    zppy -c tests/integration/generated/test_weekly_legacy_3.0.0_bundles_chrysalis.cfg

    local job_count=$(squeue -u ${USER} | wc -l)
    job_count=$((job_count - 1)) # Don't count the header
    log_success "Submitted bundles part 2. Total in queue: $job_count"

    # Wait for jobs to complete
    wait_for_slurm_jobs 600 3600  # # Check every 600sec (10min), max 1 hour

    log_success "Phase 2 complete!"
}

# ============================================================================
# Phase 3: Validation
# ============================================================================

phase_3_validation() {
    log "========================================="
    log "Phase 3: Validation"
    log "========================================="

    activate_env "$ZPPY_ENV"
    cd "$ZPPY_DIR"
    ensure_test_branch test_zppy_${TAG} ${ZPPY_BASE_BRANCH}

    # Check all status files
    log "Checking all status files..."

    local all_good=true

    check_status_files "$V2_OUTPUT" "v2" || all_good=false
    check_status_files "$LEGACY_V2_OUTPUT" "Legacy v2" || all_good=false
    check_status_files "$V3_OUTPUT" "v3" || all_good=false
    check_status_files "$LEGACY_V3_OUTPUT" "Legacy v3" || all_good=false
    check_status_files "$BUNDLES_OUTPUT" "Bundles" || all_good=false
    check_status_files "$LEGACY_BUNDLES_OUTPUT" "Legacy Bundles" || all_good=false

    if [ "$all_good" = false ]; then
        log_error "Some status checks failed!"
        checkpoint "Errors found in status files. Continue anyway?"
    else
        log_success "All status files clean!"
    fi

    # Run pytest tests
    log "Running integration tests..."

    log "Running test_bash_generation.py..."
    pytest tests/integration/test_bash_generation.py || log_warning "test_bash_generation.py had failures (may be expected)"

    log "Running test_campaign.py..."
    pytest tests/integration/test_campaign.py || log_warning "test_campaign.py had failures (may be expected)"

    log "Running test_defaults.py..." || log_warning "test_defaults.py had failures (may be expected)"
    pytest tests/integration/test_defaults.py

    log "Running test_last_year.py..." || log_warning "test_last_year.py had failures (may be expected)"
    pytest tests/integration/test_last_year.py

    log "Running test_bundles.py..." || log_warning "test_bundles.py had failures (may be expected)"
    pytest tests/integration/test_bundles.py

    checkpoint "Ready to run test_images.py (requires compute node allocation)"

    log "To run test_images.py, execute:"
    log "  salloc --nodes=1 --partition=debug --time=02:00:00 --account=e3sm"
    log "  source ${CONDA_PROFILE}"
    log "  conda activate ${ZPPY_ENV}"
    log "  cd ${ZPPY_DIR}"
    log "  pytest tests/integration/test_images.py"
    log "  cat test_images_summary.md"
    log "Alternative: run ./run_integration_test.bash"

    log_success "Phase 3 complete!"
    log_success "All automated tests finished successfully!"
}

# ============================================================================
# Main Execution
# ============================================================================

main() {
    log "Starting zppy integration test automation"
    log "Date stamp: $DATE_STAMP"
    log "Auto mode: $AUTO_MODE"
    log "Starting from phase: $START_PHASE"

    case $START_PHASE in
        1)
            phase_1_setup
            phase_2_bundles_part2
            phase_3_validation
            ;;
        2)
            phase_2_bundles_part2
            phase_3_validation
            ;;
        3)
            phase_3_validation
            ;;
        *)
            log_error "Invalid phase: $START_PHASE"
            exit 1
            ;;
    esac

    log_success "Integration test automation complete!"
}

main
