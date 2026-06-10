#!/bin/bash
# zppy Integration Test Automation Script
#
# Usage:
#   1. Copy this file OUT of the zppy repo (this script will change branches).
#   2. Edit the "Check these every time" configuration section below.
#   3. Run: ./run_integration_test.bash --machine MACHINE [--phase N] [--auto]
#      MACHINE: chrysalis | compy | perlmutter
#
# Phases:
#   1 - Full setup: build envs, run unit tests, generate configs, submit SLURM jobs
#   2 - Bundles Part 2 (run after Phase 1 jobs finish)
#   3 - Validation: status checks + pytest integration tests
#
# Notes:
#   - test_images.py must be run manually from a compute node (see Phase 3 output).

set -e  # Exit on error
set -u  # Exit on undefined variable

# ============================================================================
# Parse arguments
# ============================================================================

AUTO_MODE=false
START_PHASE=1
MACHINE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --auto)    AUTO_MODE=true; shift ;;
        --phase)   START_PHASE="$2"; shift 2 ;;
        --machine) MACHINE="$2"; shift 2 ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
done

if [[ -z "$MACHINE" ]]; then
    echo "Error: --machine is required. Valid values: chrysalis | compy | perlmutter"
    exit 1
fi

# ============================================================================
# Configuration
# ============================================================================

# --- Check these every time --------------------------------------------------

RUN_NUMBER=1

# Base branches (what we're testing -- usually "main")
DIAGS_BASE_BRANCH="main"
ZI_BASE_BRANCH="main"
ZPPY_BASE_BRANCH="main"

# --- Set these up once -------------------------------------------------------

HOME_DIR="$HOME"
EZ_DIR="$HOME_DIR/ez"                          # Parent dir for all repos
E3SM_DIAGS_DIR="$EZ_DIR/e3sm_diags"
ZPPY_INTERFACES_DIR="$EZ_DIR/zppy-interfaces"
ZPPY_DIR="$EZ_DIR/zppy"
CONDA_PROFILE="$HOME_DIR/miniforge3/etc/profile.d/conda.sh"

# --- Machine-specific settings -----------------------------------------------

case "$MACHINE" in
    chrysalis)
        OUTPUT_WORKSPACE="/lcrc/group/e3sm/${USER}"
        CONDA_ACTIVATION_CMD="lcrc_conda"
        UNIFIED_ENV_CMD="source /lcrc/soft/climate/e3sm-unified/load_latest_e3sm_unified_chrysalis.sh"
        SALLOC_CMD="salloc --nodes=1 --partition=debug --time=02:00:00 --account=e3sm"
        ;;
    compy)
        OUTPUT_WORKSPACE="/compyfs/${USER}"
        CONDA_ACTIVATION_CMD="compy_conda"
        UNIFIED_ENV_CMD="source /share/apps/E3SM/conda_envs/load_latest_e3sm_unified_compy.sh"
        SALLOC_CMD="salloc --nodes=1 --partition=short --time=01:00:00 --account=e3sm"
        ;;
    perlmutter)
        OUTPUT_WORKSPACE="/global/cfs/cdirs/e3sm/${USER}"
        CONDA_ACTIVATION_CMD="nersc_conda"
        UNIFIED_ENV_CMD="source /global/common/software/e3sm/anaconda_envs/load_latest_e3sm_unified_pm-cpu.sh"
        SALLOC_CMD="salloc --nodes=1 --qos=interactive --time=01:00:00 --constraint=cpu --account=e3sm"
        ;;
    *)
        echo "Error: Unknown machine '$MACHINE'. Valid values: chrysalis | compy | perlmutter"
        exit 1
        ;;
esac

# --- Derived (probably no edits needed) --------------------------------------

DATE_STAMP="${DATE_STAMP:-$(date +%Y%m%d)}"
TAG="${DATE_STAMP}_run${RUN_NUMBER}"
UNIQUE_ID="zppy_main_branch_test_${TAG}"

DIAGS_ENV="test-diags-${DIAGS_BASE_BRANCH}-${TAG}"
ZI_ENV="test-zi-${ZI_BASE_BRANCH}-${TAG}"
ZPPY_ENV="test-zppy-${ZPPY_BASE_BRANCH}-${TAG}"

# Output directories (status file locations)
BUNDLES_OUTPUT="${OUTPUT_WORKSPACE}/zppy_weekly_bundles_output/${UNIQUE_ID}/v3.LR.historical_0051/post/scripts"
LEGACY_310_BUNDLES_OUTPUT="${OUTPUT_WORKSPACE}/zppy_weekly_legacy_3.1.0_bundles_output/${UNIQUE_ID}/v3.LR.historical_0051/post/scripts"
LEGACY_300_BUNDLES_OUTPUT="${OUTPUT_WORKSPACE}/zppy_weekly_legacy_3.0.0_bundles_output/${UNIQUE_ID}/v3.LR.historical_0051/post/scripts"
V2_OUTPUT="${OUTPUT_WORKSPACE}/zppy_weekly_comprehensive_v2_output/${UNIQUE_ID}/v2.LR.historical_0201/post/scripts"
LEGACY_310_V2_OUTPUT="${OUTPUT_WORKSPACE}/zppy_weekly_legacy_3.1.0_comprehensive_v2_output/${UNIQUE_ID}/v2.LR.historical_0201/post/scripts"
LEGACY_300_V2_OUTPUT="${OUTPUT_WORKSPACE}/zppy_weekly_legacy_3.0.0_comprehensive_v2_output/${UNIQUE_ID}/v2.LR.historical_0201/post/scripts"
V3_OUTPUT="${OUTPUT_WORKSPACE}/zppy_weekly_comprehensive_v3_output/${UNIQUE_ID}/v3.LR.historical_0051/post/scripts"
LEGACY_310_V3_OUTPUT="${OUTPUT_WORKSPACE}/zppy_weekly_legacy_3.1.0_comprehensive_v3_output/${UNIQUE_ID}/v3.LR.historical_0051/post/scripts"
LEGACY_300_V3_OUTPUT="${OUTPUT_WORKSPACE}/zppy_weekly_legacy_3.0.0_comprehensive_v3_output/${UNIQUE_ID}/v3.LR.historical_0051/post/scripts"

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
        read -rp "Press Enter to continue or Ctrl+C to abort..."
    else
        log "AUTO MODE: Passing checkpoint -- $message"
    fi
}

# Activate conda and (optionally) a named environment.
activate_env() {
    local env_name="${1:-}"
    set +u
    # shellcheck disable=SC1090
    source ~/.bashrc
    $CONDA_ACTIVATION_CMD  # Machine-specific conda init (lcrc_conda / compy_conda / nersc_conda)

    if [ -n "$env_name" ]; then
        conda activate "$env_name"
        log "Installing/updating package in '$env_name'..."
        python -m pip install .
    fi
    set -u
}

# Create (if needed) and activate a conda environment.
setup_conda_env() {
    local conda_dir="$1"   # Directory containing dev.yml (e.g. "conda" or "conda-env")
    local env_name="$2"

    activate_env  # Ensure conda itself is available

    if conda env list | grep -q "^${env_name} "; then
        log "Environment '$env_name' already exists, skipping creation"
    else
        log "Creating environment '$env_name' from ${conda_dir}/dev.yml..."
        rm -rf build
        conda clean --all --yes
        conda env create -f "${conda_dir}/dev.yml" -n "$env_name"
    fi

    activate_env "$env_name"
    log_success "Environment '$env_name' ready"
}

# Checkout test branch, creating it from upstream/<base> if it doesn't exist.
# Stashes/commits any in-progress work first.
ensure_test_branch() {
    local test_branch="$1"
    local base_branch="$2"
    local current_branch
    current_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)

    if [ "$current_branch" = "$test_branch" ]; then
        log "Already on branch '$test_branch'"
        return 0
    fi

    log "Saving current work before switching branches..."
    git add -A
    git commit -m "Auto-save before test" --no-verify || true

    if git show-ref --verify --quiet "refs/heads/$test_branch"; then
        log "Checking out existing branch '$test_branch'..."
        git checkout "$test_branch"
    else
        log "Creating new branch '$test_branch' from upstream/${base_branch}..."
        git fetch upstream "${base_branch}"
        git checkout -b "$test_branch" "upstream/${base_branch}"
    fi
    log_success "On branch '$test_branch'"
}

# Poll squeue until no user jobs remain (or timeout).
wait_for_slurm_jobs() {
    local check_interval=${1:-600}  # seconds between checks (default 10 min)
    local max_wait=${2:-14400}      # max total wait seconds (default 4 hours)

    log "Waiting for SLURM jobs to complete (checking every ${check_interval}s, max ${max_wait}s)..."
    local elapsed=0
    local prev_failed_count=0

    while true; do
        local job_count
        job_count=$(squeue -u "${USER}" | wc -l)
        job_count=$((job_count - 1))  # subtract header

        # Detect DependencyNeverSatisfied
        local failed_jobs
        failed_jobs=$(squeue -u "${USER}" | grep "DependencyNeverSatisfied" || true)
        local failed_count=0
        if [ -n "$failed_jobs" ]; then
            failed_count=$(echo "$failed_jobs" | wc -l)
        fi

        if [ "$failed_count" -gt "$prev_failed_count" ]; then
            log_error "Jobs with DependencyNeverSatisfied:"
            echo "$failed_jobs"
            if [ "$job_count" -eq "$failed_count" ]; then
                log_error "All remaining jobs have DependencyNeverSatisfied -- cancelling."
                scancel -u "${USER}"
                return 1
            fi
        fi
        prev_failed_count=$failed_count

        if [ "$job_count" -eq 0 ]; then
            log_success "All SLURM jobs completed!"
            return 0
        fi

        if [ "$elapsed" -ge "$max_wait" ]; then
            log_error "Timeout after ${max_wait}s waiting for SLURM jobs"
            return 1
        fi

        echo -ne "\r${YELLOW}Jobs remaining: $job_count${NC} (elapsed: ${elapsed}s / max: ${max_wait}s)"
        sleep "$check_interval"
        elapsed=$((elapsed + check_interval))
    done
    echo ""
}

# Grep status files in a directory for any non-OK lines.
# Returns 0 if all OK, 1 if any failures found.
check_status_files() {
    local dir="$1"
    local name="$2"

    if [ ! -d "$dir" ]; then
        log_warning "$name: Directory not found: $dir"
        return 1
    fi

    local errors
    errors=$(grep -v "OK" "${dir}"/*status 2>/dev/null || true)

    if [ -z "$errors" ]; then
        log_success "$name: All status files OK in ${dir}"
        return 0
    else
        log_error "$name: Non-OK statuses found in ${dir}:"
        echo "$errors"
        return 1
    fi
}

# ============================================================================
# Phase 1: Environment Setup + Initial SLURM Jobs
# ============================================================================

phase_1_setup() {
    log "========================================="
    log "Phase 1: Setup"
    log "Date stamp:  $DATE_STAMP"
    log "Unique ID:   $UNIQUE_ID"
    log "========================================="

    # ------------------------------------------------------------------
    # e3sm_diags
    # ------------------------------------------------------------------
    log "Setting up e3sm_diags environment..."
    cd "$E3SM_DIAGS_DIR"
    ensure_test_branch "test_e3sm_diags_${TAG}" "$DIAGS_BASE_BRANCH"

    log "Latest e3sm_diags commit (should match https://github.com/E3SM-Project/e3sm_diags/commits/${DIAGS_BASE_BRANCH}):"
    git log -1 --oneline
    setup_conda_env "conda-env" "$DIAGS_ENV"

    # ------------------------------------------------------------------
    # zppy-interfaces (includes unit tests)
    # ------------------------------------------------------------------
    log "Setting up zppy-interfaces environment..."
    cd "$ZPPY_INTERFACES_DIR"
    ensure_test_branch "test_zi_${TAG}" "$ZI_BASE_BRANCH"

    log "Latest zppy-interfaces commit (should match https://github.com/E3SM-Project/zppy-interfaces/commits/${ZI_BASE_BRANCH}):"
    git log -1 --oneline
    setup_conda_env "conda" "$ZI_ENV"

    log "Running zppy-interfaces unit tests..."
    pytest tests/unit/global_time_series/test_*.py
    pytest tests/unit/pcmdi_diags/test_*.py
    log_success "zppy-interfaces unit tests passed"

    # ------------------------------------------------------------------
    # zppy (includes unit tests + config generation)
    # ------------------------------------------------------------------
    log "Setting up zppy environment..."
    cd "$ZPPY_DIR"
    ensure_test_branch "test_zppy_${TAG}" "$ZPPY_BASE_BRANCH"

    log "Latest zppy commit (should match https://github.com/E3SM-Project/zppy/commits/${ZPPY_BASE_BRANCH}):"
    git log -1 --oneline
    setup_conda_env "conda" "$ZPPY_ENV"

    log "Running zppy unit tests..."
    pytest tests/test_*.py
    log_success "zppy unit tests passed"

    # ------------------------------------------------------------------
    # Generate config files (update utils.py TEST_SPECIFICS, then run it)
    # ------------------------------------------------------------------
    log "Generating config files..."

    UTILS_FILE="tests/integration/utils.py"

    python - <<PYEOF
import re

utils_file = "${UTILS_FILE}"
with open(utils_file, 'r') as f:
    content = f.read()

replacement = '''TEST_SPECIFICS: Dict[str, Any] = {
    "nco_path": "",
    "diags_environment_commands": "source ${CONDA_PROFILE}; conda activate ${DIAGS_ENV}",
    "mpas_analysis_environment_commands": "${UNIFIED_ENV_CMD}",
    "global_time_series_environment_commands": "source ${CONDA_PROFILE}; conda activate ${ZI_ENV}",
    "livvkit_environment_commands": "${UNIFIED_ENV_CMD}",
    "pcmdi_diags_environment_commands": "source ${CONDA_PROFILE}; conda activate ${ZI_ENV}",
    "environment_commands": "${UNIFIED_ENV_CMD}",
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
    "tasks_to_run": ["e3sm_diags", "mpas_analysis", "global_time_series", "ilamb", "livvkit", "pcmdi_diags"],
    "unique_id": "${UNIQUE_ID}",
}'''

pattern = r'TEST_SPECIFICS: Dict\[str, Any\] = \{.*?\n\}'
content = re.sub(pattern, replacement, content, flags=re.DOTALL)

with open(utils_file, 'w') as f:
    f.write(content)

print("Updated TEST_SPECIFICS in utils.py")
PYEOF

    log "Running utils.py to generate cfg files..."
    python tests/integration/utils.py
    log_success "Config files generated"

    checkpoint "About to submit initial SLURM jobs. Review the generated configs if needed."

    # ------------------------------------------------------------------
    # Submit initial SLURM jobs
    # ------------------------------------------------------------------
    log "Submitting SLURM jobs..."

    zppy -c tests/integration/generated/test_weekly_comprehensive_v3_chrysalis.cfg
    zppy -c tests/integration/generated/test_weekly_bundles_chrysalis.cfg
    zppy -c tests/integration/generated/test_weekly_comprehensive_v2_chrysalis.cfg

    zppy -c tests/integration/generated/test_weekly_legacy_3.1.0_comprehensive_v3_chrysalis.cfg
    zppy -c tests/integration/generated/test_weekly_legacy_3.1.0_bundles_chrysalis.cfg
    zppy -c tests/integration/generated/test_weekly_legacy_3.1.0_comprehensive_v2_chrysalis.cfg

    zppy -c tests/integration/generated/test_weekly_legacy_3.0.0_comprehensive_v3_chrysalis.cfg
    zppy -c tests/integration/generated/test_weekly_legacy_3.0.0_bundles_chrysalis.cfg
    zppy -c tests/integration/generated/test_weekly_legacy_3.0.0_comprehensive_v2_chrysalis.cfg

    local job_count
    job_count=$(squeue -u "${USER}" | wc -l)
    job_count=$((job_count - 1))
    log_success "Submitted jobs. Current queue depth: $job_count"

    checkpoint "Phase 1 jobs submitted. Waiting for them to finish..."
    wait_for_slurm_jobs 600 14400  # Check every 10 min, max 4 hours

    log_success "Phase 1 complete!"
}

# ============================================================================
# Phase 2: Bundles Part 2
# ============================================================================

phase_2_bundles_part2() {
    log "========================================="
    log "Phase 2: Bundles Part 2"
    log "========================================="

    cd "$ZPPY_DIR"
    activate_env "$ZPPY_ENV"
    ensure_test_branch "test_zppy_${TAG}" "$ZPPY_BASE_BRANCH"

    # Verify all bundle status files are clean before submitting part 2.
    log "Checking bundle status files before submitting part 2..."
    local all_ok=true
    check_status_files "$BUNDLES_OUTPUT"         "Bundles"         || all_ok=false
    check_status_files "$LEGACY_310_BUNDLES_OUTPUT" "Legacy 3.1.0 Bundles" || all_ok=false
    check_status_files "$LEGACY_300_BUNDLES_OUTPUT" "Legacy 3.0.0 Bundles" || all_ok=false

    if [ "$all_ok" = false ]; then
        log_error "One or more bundle status files have non-OK entries."
        checkpoint "Errors found. Continue anyway?"
    else
        log_success "Bundle status files look clean -- safe to submit part 2."
    fi

    log "Submitting bundles part 2..."
    zppy -c tests/integration/generated/test_weekly_bundles_chrysalis.cfg
    zppy -c tests/integration/generated/test_weekly_legacy_3.1.0_bundles_chrysalis.cfg
    zppy -c tests/integration/generated/test_weekly_legacy_3.0.0_bundles_chrysalis.cfg

    local job_count
    job_count=$(squeue -u "${USER}" | wc -l)
    job_count=$((job_count - 1))
    log_success "Bundles part 2 submitted. Current queue depth: $job_count"

    wait_for_slurm_jobs 600 3600  # Check every 10 min, max 1 hour

    log_success "Phase 2 complete!"
}

# ============================================================================
# Phase 3: Validation (status checks + pytest integration tests)
# ============================================================================

phase_3_validation() {
    log "========================================="
    log "Phase 3: Validation"
    log "========================================="

    cd "$ZPPY_DIR"
    activate_env "$ZPPY_ENV"
    ensure_test_branch "test_zppy_${TAG}" "$ZPPY_BASE_BRANCH"

    # ------------------------------------------------------------------
    # Status file checks
    # ------------------------------------------------------------------
    log "Checking all status files..."
    local all_good=true

    check_status_files "$V2_OUTPUT"               "v2"               || all_good=false
    check_status_files "$LEGACY_310_V2_OUTPUT"    "Legacy 3.1.0 v2"  || all_good=false
    check_status_files "$LEGACY_300_V2_OUTPUT"    "Legacy 3.0.0 v2"  || all_good=false
    check_status_files "$V3_OUTPUT"               "v3"               || all_good=false
    check_status_files "$LEGACY_310_V3_OUTPUT"    "Legacy 3.1.0 v3"  || all_good=false
    check_status_files "$LEGACY_300_V3_OUTPUT"    "Legacy 3.0.0 v3"  || all_good=false
    check_status_files "$BUNDLES_OUTPUT"          "Bundles"          || all_good=false
    check_status_files "$LEGACY_310_BUNDLES_OUTPUT" "Legacy 3.1.0 Bundles" || all_good=false
    check_status_files "$LEGACY_300_BUNDLES_OUTPUT" "Legacy 3.0.0 Bundles" || all_good=false

    if [ "$all_good" = false ]; then
        log_error "Some status checks failed!"
        checkpoint "Errors found in status files. Continue to pytest anyway?"
    else
        log_success "All status files clean!"
    fi

    # ------------------------------------------------------------------
    # pytest integration tests
    # ------------------------------------------------------------------
    log "Running integration tests..."

    log "Running test_last_year.py (no expected results dir)..."
    pytest tests/integration/test_last_year.py \
        || log_warning "test_last_year.py had failures"

    log "Running test_bash_generation.py..."
    pytest tests/integration/test_bash_generation.py \
        || log_warning "test_bash_generation.py had failures"

    log "Running test_campaign.py..."
    pytest tests/integration/test_campaign.py \
        || log_warning "test_campaign.py had failures"

    log "Running test_defaults.py..."
    pytest tests/integration/test_defaults.py \
        || log_warning "test_defaults.py had failures"

    log "Running test_bundles.py..."
    pytest tests/integration/test_bundles.py \
        || log_warning "test_bundles.py had failures"

    # ------------------------------------------------------------------
    # test_images.py -- must run from a compute node
    # ------------------------------------------------------------------
    log_warning "test_images.py requires a compute node and must be run manually."
    log "To run it on ${MACHINE}:"
    log "  ${SALLOC_CMD}"
    log "  source ${CONDA_PROFILE}"
    log "  conda activate ${ZPPY_ENV}"
    log "  cd ${ZPPY_DIR}"
    log "  pytest tests/integration/test_images.py"
    log "  cat test_images_summary.md"

    log_success "Phase 3 automated tests complete!"
    log_success "Remember to run test_images.py manually from a compute node."
}

# ============================================================================
# Main
# ============================================================================

main() {
    log "Starting zppy integration test automation"
    log "Machine:      $MACHINE"
    log "Date stamp:   $DATE_STAMP"
    log "Auto mode:    $AUTO_MODE"
    log "Start phase:  $START_PHASE"

    case "$START_PHASE" in
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
            log_error "Invalid phase: $START_PHASE (must be 1, 2, or 3)"
            exit 1
            ;;
    esac

    log_success "Integration test automation complete!"
}

main
