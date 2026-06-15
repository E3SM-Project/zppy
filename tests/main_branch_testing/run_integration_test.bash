#!/bin/bash
# zppy Integration Test Automation Script
#
# Usage:
#   1. Copy this file AND the sample config OUT of the zppy repo
#      (this script will change branches).
#   2. Edit your config file (see zppy_test.cfg.sample).
#   3. Run: ./run_integration_test.bash --config path/to/your.cfg
#
# Phases (set START_PHASE in your config):
#   1 - Full setup: build envs, run unit tests, generate configs, submit SLURM jobs
#   2 - Bundles Part 2 (run after Phase 1 jobs finish)
#   3 - Validation: status checks + pytest integration tests
#
# Notes:
#   - test_images.py must be run manually from a compute node (see Phase 3 output).
#   - To resume from Phase 2 or 3 on a later day, set EXPLICIT_TAG in your config
#     to the TAG printed at the start of Phase 1 (or stored in ~/.zppy_test_tag),
#     and set START_PHASE accordingly.

set -e  # Exit on error
set -u  # Exit on undefined variable

# ============================================================================
# Parse arguments
# ============================================================================

CONFIG_FILE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --config) CONFIG_FILE="$2"; shift 2 ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
done

if [[ -z "$CONFIG_FILE" ]]; then
    echo "Error: --config is required."
    echo "Usage: $0 --config path/to/your.cfg"
    exit 1
fi

if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "Error: Config file not found: $CONFIG_FILE"
    exit 1
fi

# Source the config. Variables defined there become the script's environment.
# shellcheck disable=SC1090
source "$CONFIG_FILE"

# Validate required config keys.
_required_vars=(
    MACHINE START_PHASE AUTO_MODE EXPLICIT_TAG
    RUN_NUMBER
    DIAGS_BASE_BRANCH E3SM_TO_CMIP_BASE_BRANCH MPAS_BASE_BRANCH ZI_BASE_BRANCH ZPPY_BASE_BRANCH
    DIAGS_ENV_TYPE E3SM_TO_CMIP_ENV_TYPE MPAS_ENV_TYPE ZI_ENV_TYPE
    CFGS_TO_RUN TASKS_TO_RUN
    HOME_DIR EZ_DIR
    E3SM_DIAGS_DIR E3SM_TO_CMIP_DIR MPAS_ANALYSIS_DIR ZPPY_INTERFACES_DIR ZPPY_DIR
    CONDA_PROFILE TAG_CACHE_FILE
)
_missing=()
for _var in "${_required_vars[@]}"; do
    if [[ -z "${!_var+x}" ]]; then
        _missing+=("$_var")
    fi
done
if [[ ${#_missing[@]} -gt 0 ]]; then
    echo "Error: The following required variables are missing from ${CONFIG_FILE}:"
    printf '  %s\n' "${_missing[@]}"
    exit 1
fi

# Apply defaults for optional *_EXISTING_ENV variables so the rest of the
# script can reference them unconditionally.
DIAGS_EXISTING_ENV="${DIAGS_EXISTING_ENV:-}"
E3SM_TO_CMIP_EXISTING_ENV="${E3SM_TO_CMIP_EXISTING_ENV:-}"
MPAS_EXISTING_ENV="${MPAS_EXISTING_ENV:-}"
ZI_EXISTING_ENV="${ZI_EXISTING_ENV:-}"
ZPPY_EXISTING_ENV="${ZPPY_EXISTING_ENV:-}"

# Validate MACHINE value.
case "$MACHINE" in
    chrysalis|compy|perlmutter) ;;
    *) echo "Error: Unknown MACHINE '${MACHINE}'. Valid values: chrysalis | compy | perlmutter"; exit 1 ;;
esac

# ============================================================================
# Machine-specific settings
# ============================================================================

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
esac

# Derive the filename suffix used by generated zppy cfg files.
case "$MACHINE" in
    chrysalis)  MACHINE_CFG_SUFFIX="chrysalis" ;;
    compy)      MACHINE_CFG_SUFFIX="compy" ;;
    perlmutter) MACHINE_CFG_SUFFIX="pm-cpu" ;;
esac

# Split comma-separated config lists into bash arrays.
# IFS = Internal Field Separator
IFS=',' read -ra CFGS_ARRAY  <<< "$CFGS_TO_RUN"
IFS=',' read -ra TASKS_ARRAY <<< "$TASKS_TO_RUN"
# ============================================================================
#
# Priority:
#   1. EXPLICIT_TAG from config (always wins when non-empty)
#   2. $TAG_CACHE_FILE written by a prior Phase 1 run (auto-resume)
#   3. Fresh timestamp (Phase 1 first run)
#
# Phase 1 always writes the resolved TAG to $TAG_CACHE_FILE so later phases
# can pick it up automatically without needing EXPLICIT_TAG.

if [[ -n "$EXPLICIT_TAG" ]]; then
    TAG="$EXPLICIT_TAG"
    DATE_STAMP="${TAG%%_run*}"
elif [[ "$START_PHASE" -gt 1 && -f "$TAG_CACHE_FILE" ]]; then
    TAG="$(cat "$TAG_CACHE_FILE")"
    DATE_STAMP="${TAG%%_run*}"
    echo "Loaded TAG from ${TAG_CACHE_FILE}: ${TAG}"
    echo "(Set EXPLICIT_TAG in your config to override.)"
else
    DATE_STAMP="$(date +%Y%m%d)"
    TAG="${DATE_STAMP}_run${RUN_NUMBER}"
fi

# ============================================================================
# Derived (probably no edits needed)
# ============================================================================

UNIQUE_ID="zppy_main_branch_test_${TAG}"

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
        if [[ "$conda_dir" == "none" ]]; then
            conda create --name "$env_name" --file dev-spec.txt --yes
        else
            conda env create -f "${conda_dir}/dev.yml" -n "$env_name"
        fi
    fi

    activate_env "$env_name"
    log_success "Environment '$env_name' ready"
}

# Resolve the conda env name for a "dev"-type component.
# If an existing env name is provided, log that it will be reused and echo it.
# Otherwise, echo the auto-generated name.
# Usage: env_name=$(resolve_dev_env "e3sm_diags" "$DIAGS_EXISTING_ENV" "test-diags-main-${TAG}")
resolve_dev_env() {
    local component="$1"
    local existing_env="$2"
    local auto_name="$3"

    if [[ -n "$existing_env" ]]; then
        log "Reusing existing '$component' env: $existing_env (skipping creation)"
        echo "$existing_env"
    else
        echo "$auto_name"
    fi
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

# Return the environment_commands string for a component.
# Usage: get_env_cmd "dev" "$ENV_NAME"
#        get_env_cmd "unified" ""
get_env_cmd() {
    local env_type="$1"
    local env_name="$2"
    if [[ "$env_type" == "dev" ]]; then
        echo "source ${CONDA_PROFILE}; conda activate ${env_name}"
    else
        echo "$UNIFIED_ENV_CMD"
    fi
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
            log_error "This script is going to exit now. However, the jobs in the queue will NOT be terminated. Once they finish, you may re-invoke this script with START_PHASE=2 or START_PHASE=3 in your config to continue."
            log_error "  TAG for this run: ${TAG}"
            log_error "  Resume: set START_PHASE=2 and EXPLICIT_TAG=${TAG} in your config, then re-run."
            log_error "  (TAG is also saved in ${TAG_CACHE_FILE})"
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
    # Save TAG immediately so later phases can find it even if the date changes.
    echo "$TAG" > "$TAG_CACHE_FILE"

    log "========================================="
    log "Phase 1: Setup"
    log "Config file: $CONFIG_FILE"
    log "Date stamp:  $DATE_STAMP"
    log "TAG:         $TAG  (saved to ${TAG_CACHE_FILE})"
    log "Unique ID:   $UNIQUE_ID"
    log ""
    log "To resume from a later phase, set in your config:"
    log "  START_PHASE=2"
    log "  EXPLICIT_TAG=${TAG}"
    log "========================================="

    # ------------------------------------------------------------------
    # e3sm_to_cmip
    # ------------------------------------------------------------------
    log "Setting up e3sm_to_cmip..."
    cd "$E3SM_TO_CMIP_DIR"
    ensure_test_branch "test_e3sm_to_cmip_${TAG}" "$E3SM_TO_CMIP_BASE_BRANCH"

    log "Latest e3sm_to_cmip commit (should match https://github.com/E3SM-Project/e3sm_to_cmip/commits/${E3SM_TO_CMIP_BASE_BRANCH}):"
    git log -1 --oneline

    local E3SM_TO_CMIP_ENV=""
    if [[ "$E3SM_TO_CMIP_ENV_TYPE" == "dev" ]]; then
        E3SM_TO_CMIP_ENV=$(resolve_dev_env \
            "e3sm_to_cmip" \
            "$E3SM_TO_CMIP_EXISTING_ENV" \
            "test-e3sm-to-cmip-${E3SM_TO_CMIP_BASE_BRANCH}-${TAG}")
        if [[ -z "$E3SM_TO_CMIP_EXISTING_ENV" ]]; then
            setup_conda_env "conda-env" "$E3SM_TO_CMIP_ENV"
        else
            activate_env "$E3SM_TO_CMIP_ENV"
        fi
    else
        log "Using unified env for e3sm_to_cmip (skipping conda env creation)"
    fi

    # ------------------------------------------------------------------
    # e3sm_diags
    # ------------------------------------------------------------------
    log "Setting up e3sm_diags..."
    cd "$E3SM_DIAGS_DIR"
    ensure_test_branch "test_e3sm_diags_${TAG}" "$DIAGS_BASE_BRANCH"

    log "Latest e3sm_diags commit (should match https://github.com/E3SM-Project/e3sm_diags/commits/${DIAGS_BASE_BRANCH}):"
    git log -1 --oneline

    local DIAGS_ENV=""
    if [[ "$DIAGS_ENV_TYPE" == "dev" ]]; then
        DIAGS_ENV=$(resolve_dev_env \
            "e3sm_diags" \
            "$DIAGS_EXISTING_ENV" \
            "test-diags-${DIAGS_BASE_BRANCH}-${TAG}")
        if [[ -z "$DIAGS_EXISTING_ENV" ]]; then
            setup_conda_env "conda-env" "$DIAGS_ENV"
        else
            activate_env "$DIAGS_ENV"
        fi
    else
        log "Using unified env for e3sm_diags (skipping conda env creation)"
    fi

    # ------------------------------------------------------------------
    # MPAS-Analysis
    # ------------------------------------------------------------------
    log "Setting up MPAS-Analysis..."
    cd "$MPAS_ANALYSIS_DIR"
    ensure_test_branch "test_mpas_${TAG}" "$MPAS_BASE_BRANCH"

    log "Latest MPAS-Analysis commit (should match https://github.com/MPAS-Dev/MPAS-Analysis/commits/${MPAS_BASE_BRANCH}):"
    git log -1 --oneline

    local MPAS_ENV=""
    if [[ "$MPAS_ENV_TYPE" == "dev" ]]; then
        MPAS_ENV=$(resolve_dev_env \
            "MPAS-Analysis" \
            "$MPAS_EXISTING_ENV" \
            "test-mpas-${MPAS_BASE_BRANCH}-${TAG}")
        if [[ -z "$MPAS_EXISTING_ENV" ]]; then
            setup_conda_env "none" "$MPAS_ENV"
        else
            activate_env "$MPAS_ENV"
        fi
    else
        log "Using unified env for MPAS-Analysis (skipping conda env creation)"
    fi

    # ------------------------------------------------------------------
    # zppy-interfaces (includes unit tests)
    # ------------------------------------------------------------------
    log "Setting up zppy-interfaces..."
    cd "$ZPPY_INTERFACES_DIR"
    ensure_test_branch "test_zi_${TAG}" "$ZI_BASE_BRANCH"

    log "Latest zppy-interfaces commit (should match https://github.com/E3SM-Project/zppy-interfaces/commits/${ZI_BASE_BRANCH}):"
    git log -1 --oneline

    local ZI_ENV=""
    if [[ "$ZI_ENV_TYPE" == "dev" ]]; then
        ZI_ENV=$(resolve_dev_env \
            "zppy-interfaces" \
            "$ZI_EXISTING_ENV" \
            "test-zi-${ZI_BASE_BRANCH}-${TAG}")
        if [[ -z "$ZI_EXISTING_ENV" ]]; then
            setup_conda_env "conda" "$ZI_ENV"
        else
            activate_env "$ZI_ENV"
        fi
    else
        log "Using unified env for zppy-interfaces (skipping conda env creation)"
    fi

    log "Running zppy-interfaces unit tests..."
    pytest tests/unit/global_time_series/test_*.py
    pytest tests/unit/pcmdi_diags/test_*.py
    log_success "zppy-interfaces unit tests passed"

    # ------------------------------------------------------------------
    # zppy (includes unit tests + config generation)
    # ------------------------------------------------------------------
    log "Setting up zppy..."
    cd "$ZPPY_DIR"
    ensure_test_branch "test_zppy_${TAG}" "$ZPPY_BASE_BRANCH"

    log "Latest zppy commit (should match https://github.com/E3SM-Project/zppy/commits/${ZPPY_BASE_BRANCH}):"
    git log -1 --oneline

    # Resolve ZPPY_ENV: if an existing env is specified, use it; otherwise use
    # the auto-generated name and create/update the env as normal.
    if [[ -n "$ZPPY_EXISTING_ENV" ]]; then
        ZPPY_ENV=$(resolve_dev_env "zppy" "$ZPPY_EXISTING_ENV" "$ZPPY_ENV")
        activate_env "$ZPPY_ENV"
    else
        setup_conda_env "conda" "$ZPPY_ENV"
    fi

    log "Running zppy unit tests..."
    pytest tests/test_*.py
    log_success "zppy unit tests passed"

    # ------------------------------------------------------------------
    # Generate config files (update utils.py TEST_SPECIFICS, then run it)
    # ------------------------------------------------------------------
    log "Generating config files..."

    local E3SM_TO_CMIP_CMD
    local DIAGS_CMD
    local MPAS_CMD
    local ZI_CMD
    E3SM_TO_CMIP_CMD=$(get_env_cmd "$E3SM_TO_CMIP_ENV_TYPE" "$E3SM_TO_CMIP_ENV")
    DIAGS_CMD=$(get_env_cmd "$DIAGS_ENV_TYPE" "$DIAGS_ENV")
    MPAS_CMD=$(get_env_cmd "$MPAS_ENV_TYPE" "$MPAS_ENV")
    ZI_CMD=$(get_env_cmd "$ZI_ENV_TYPE" "$ZI_ENV")

    UTILS_FILE="tests/integration/utils.py"

    # Build Python list literals from the bash arrays for injection into the heredoc.
    local CFGS_PY_LIST TASKS_PY_LIST cfg task
    CFGS_PY_LIST=""
    for cfg in "${CFGS_ARRAY[@]}"; do
        cfg="${cfg// /}"  # strip any accidental whitespace
        CFGS_PY_LIST+="        \"${cfg}\","$'\n'
    done
    TASKS_PY_LIST=""
    for task in "${TASKS_ARRAY[@]}"; do
        task="${task// /}"
        TASKS_PY_LIST+="\"${task}\", "
    done
    TASKS_PY_LIST="${TASKS_PY_LIST%, }"  # strip trailing comma+space

    python - <<PYEOF
import re

utils_file = "${UTILS_FILE}"
with open(utils_file, 'r') as f:
    content = f.read()

replacement = '''TEST_SPECIFICS: Dict[str, Any] = {
    "nco_path": "",
    "e3sm_to_cmip_environment_commands": "${E3SM_TO_CMIP_CMD}",
    "diags_environment_commands": "${DIAGS_CMD}",
    "mpas_analysis_environment_commands": "${MPAS_CMD}",
    "global_time_series_environment_commands": "${ZI_CMD}",
    "livvkit_environment_commands": "${UNIFIED_ENV_CMD}",
    "pcmdi_diags_environment_commands": "${ZI_CMD}",
    "environment_commands": "${UNIFIED_ENV_CMD}",
    "cfgs_to_run": [
${CFGS_PY_LIST}    ],
    "tasks_to_run": [${TASKS_PY_LIST}],
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
    local cfg
    for cfg in "${CFGS_ARRAY[@]}"; do
        cfg="${cfg// /}"
        zppy -c "tests/integration/generated/test_weekly_${cfg}_${MACHINE_CFG_SUFFIX}.cfg"
    done

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
    log "TAG: $TAG"
    log "========================================="

    cd "$ZPPY_DIR"
    activate_env "$ZPPY_ENV"
    ensure_test_branch "test_zppy_${TAG}" "$ZPPY_BASE_BRANCH"

    # Verify bundle status files are clean before submitting part 2.
    # These paths are fixed regardless of CFGS_TO_RUN; skip any that don't exist yet.
    log "Checking bundle status files before submitting part 2..."
    local all_ok=true
    check_status_files "$BUNDLES_OUTPUT"            "Bundles"              || all_ok=false
    check_status_files "$LEGACY_310_BUNDLES_OUTPUT" "Legacy 3.1.0 Bundles" || all_ok=false
    check_status_files "$LEGACY_300_BUNDLES_OUTPUT" "Legacy 3.0.0 Bundles" || all_ok=false

    if [ "$all_ok" = false ]; then
        log_error "One or more bundle status files have non-OK entries."
        checkpoint "Errors found. Continue anyway?"
    else
        log_success "Bundle status files look clean -- safe to submit part 2."
    fi

    log "Submitting bundles part 2..."
    local cfg
    for cfg in "${CFGS_ARRAY[@]}"; do
        cfg="${cfg// /}"
        if [[ "$cfg" == *bundle* ]]; then
            zppy -c "tests/integration/generated/test_weekly_${cfg}_${MACHINE_CFG_SUFFIX}.cfg"
        fi
    done

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
    log "TAG: $TAG"
    log "========================================="

    cd "$ZPPY_DIR"
    activate_env "$ZPPY_ENV"
    ensure_test_branch "test_zppy_${TAG}" "$ZPPY_BASE_BRANCH"

    # ------------------------------------------------------------------
    # Status file checks
    # ------------------------------------------------------------------
    log "Checking all status files..."
    local all_good=true

    check_status_files "$V2_OUTPUT"                 "v2"                   || all_good=false
    check_status_files "$LEGACY_310_V2_OUTPUT"      "Legacy 3.1.0 v2"      || all_good=false
    check_status_files "$LEGACY_300_V2_OUTPUT"      "Legacy 3.0.0 v2"      || all_good=false
    check_status_files "$V3_OUTPUT"                 "v3"                   || all_good=false
    check_status_files "$LEGACY_310_V3_OUTPUT"      "Legacy 3.1.0 v3"      || all_good=false
    check_status_files "$LEGACY_300_V3_OUTPUT"      "Legacy 3.0.0 v3"      || all_good=false
    check_status_files "$BUNDLES_OUTPUT"            "Bundles"              || all_good=false
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
    log "Config file:  $CONFIG_FILE"
    log "Machine:      $MACHINE"
    log "TAG:          $TAG"
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
            log_error "Invalid START_PHASE: $START_PHASE (must be 1, 2, or 3)"
            exit 1
            ;;
    esac

    log_success "Integration test automation complete!"
}

main
