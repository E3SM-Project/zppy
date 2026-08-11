#!/bin/bash
# zppy Integration Test Automation Script
#
# Usage:
#   1. Copy this file AND the sample config OUT of the zppy repo
#      (this script will change branches).
#   2. Edit your config file (see zppy_test.cfg).
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
#
# Frozen dependency base (see FREEZE_DEPENDENCIES in the config):
#   - Each component listed in FROZEN_BASE_COMPONENTS gets its OWN dedicated,
#     fully-resolved conda env (BASE_ENV_LOCK_FILE_<COMPONENT>) instead of
#     solving its dev.yml fresh every run. A test env for that component is
#     then built by cloning its frozen base and `pip install`ing the branch
#     under test on top, so unrelated dependency drift (e.g. matplotlib)
#     can't produce false-positive diffs in test_images.py. See the README
#     section "Regenerating a component's frozen base lock file" for how/when
#     to update a BASE_ENV_LOCK_FILE_<COMPONENT> entry.

set -e  # Exit on error
set -u  # Exit on undefined variable

SCRIPT_RUN_DIR="$PWD"

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

# Apply defaults for the optional frozen-dependency-base variables.
FREEZE_DEPENDENCIES="${FREEZE_DEPENDENCIES:-false}"
FROZEN_BASE_COMPONENTS="${FROZEN_BASE_COMPONENTS:-}"

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
IFS=',' read -ra FROZEN_BASE_ARRAY <<< "$FROZEN_BASE_COMPONENTS"
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

# ============================================================================
# Debug Helper Functions
# ============================================================================

# Capture a full environment snapshot to both stdout and a log file.
# Usage: debug_env_snapshot "label-string"
debug_env_snapshot() {
    local label="$1"
    local out_file="${SCRIPT_RUN_DIR}/debug_env_${TAG}.txt"
    {
        echo "========================================"
        echo "ENV SNAPSHOT: $label"
        echo "Timestamp: $(date)"
        echo "----------------------------------------"
        echo "--- conda info ---"
        conda info 2>/dev/null || echo "(conda not available)"
        echo "--- CONDA_DEFAULT_ENV: ${CONDA_DEFAULT_ENV:-<unset>}"
        echo "--- CONDA_PREFIX: ${CONDA_PREFIX:-<unset>}"
        echo "--- Active python: $(which python 2>/dev/null || echo '<not found>')"
        echo "--- Python version: $(python --version 2>/dev/null || echo '<unavailable>')"
        echo "--- LD_LIBRARY_PATH: ${LD_LIBRARY_PATH:-<unset>}"
        echo "--- PYTHONPATH: ${PYTHONPATH:-<unset>}"
        echo "--- PYTHONHOME: ${PYTHONHOME:-<unset>}"
        echo "--- PATH (first 5 entries):"
        echo "$PATH" | tr ':' '\n' | head -5
        echo "--- ulimit -s (stack size): $(ulimit -s)"
        echo "--- ulimit -v (virtual mem): $(ulimit -v)"
        echo "--- OMP_NUM_THREADS: ${OMP_NUM_THREADS:-<unset>}"
        echo "--- MKL_NUM_THREADS: ${MKL_NUM_THREADS:-<unset>}"
        echo "--- OPENBLAS_NUM_THREADS: ${OPENBLAS_NUM_THREADS:-<unset>}"
        echo "========================================"
    } | tee -a "$out_file"
}

# Capture MPAS-specific preflight diagnostics to both stdout and a log file.
# Checks the mpas_analysis binary, shared library linkage, and key Python
# packages (numpy BLAS config, ESMF, cartopy) that are common segfault sources.
# Usage: debug_mpas_preflight "label-string"
debug_mpas_preflight() {
    local label="$1"
    local out_file="${SCRIPT_RUN_DIR}/debug_mpas_${TAG}.txt"
    {
        echo "========================================"
        echo "MPAS PREFLIGHT: $label"
        echo "Timestamp: $(date)"
        echo "----------------------------------------"
        echo "--- mpas_analysis binary: $(which mpas_analysis 2>/dev/null || echo '<not found>')"
        echo "--- mpas_analysis version: $(mpas_analysis --version 2>/dev/null || echo '<unavailable>')"
        echo "--- ldd on mpas_analysis binary (if applicable):"
        _mpas_bin="$(which mpas_analysis 2>/dev/null || true)"
        if [[ -n "$_mpas_bin" && -f "$_mpas_bin" ]]; then
            ldd "$_mpas_bin" 2>/dev/null | grep -i "not found" && echo "(^ missing libs above)" || echo "(all libs found)"
        else
            echo "(mpas_analysis not a regular file or not found, skipping ldd)"
        fi
        echo "--- numpy config (segfaults often trace to BLAS/LAPACK mismatches):"
        python -c "import numpy; numpy.show_config()" 2>/dev/null || echo "(numpy not importable)"
        echo "--- ESMF version:"
        python -c "import ESMF; print(ESMF.__version__)" 2>/dev/null || echo "(ESMF not importable)"
        echo "--- cartopy version:"
        python -c "import cartopy; print(cartopy.__version__)" 2>/dev/null || echo "(cartopy not importable)"
        echo "========================================"
    } | tee -a "$out_file"
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
        # Log every activation so we can spot env-stack contamination between subshells.
        echo "[DEBUG activate_env] $(date) | activated: $env_name | python: $(which python 2>/dev/null || echo '<not found>') | CONDA_PREFIX: ${CONDA_PREFIX:-<unset>} | LD_LIBRARY_PATH: ${LD_LIBRARY_PATH:-<unset>}" \
            >> "${SCRIPT_RUN_DIR}/debug_activate_log_${TAG}.txt"
        log "Installing/updating package in '$env_name'..."
        python -m pip install .
    fi
    set -u
}

# Activate the machine-specific unified environment.
# UNIFIED_ENV_CMD is always "source /path/to/script.sh" (set in the
# machine-specific case block above), so we strip the leading "source "
# and source the path directly -- no eval required.
activate_unified_env() {
    set +u
    # shellcheck disable=SC1090
    source ~/.bashrc
    $CONDA_ACTIVATION_CMD
    # shellcheck disable=SC1090
    source "${UNIFIED_ENV_CMD#source }"
    set -u
}

# Return 0 (true) if the given component key uses a dedicated frozen base
# env (rather than solving its own dev.yml fresh each run). component_key is
# one of: e3sm_to_cmip, e3sm_diags, mpas_analysis, zppy_interfaces, zppy
uses_frozen_base() {
    local component="$1"
    [[ "$FREEZE_DEPENDENCIES" == true ]] || return 1
    local c
    for c in "${FROZEN_BASE_ARRAY[@]}"; do
        c="${c// /}"
        if [[ "$c" == "$component" ]]; then
            return 0
        fi
    done
    return 1
}

# Resolve the lock file for a component's dedicated frozen base.
# Each component in FROZEN_BASE_COMPONENTS must have its own
# BASE_ENV_LOCK_FILE_<COMPONENT> (uppercase) set in the config -- there is no
# shared/fallback lock file. Each component gets its own resolved environment
# because their dependency stacks don't need to (and may not be able to)
# co-resolve into one universal env -- e3sm_diags's cdat-based stack,
# mpas_analysis's ESMF/MPAS libs, and e3sm_to_cmip's cmor can each be frozen
# independently without needing to agree with one another.
get_component_lock_file() {
    local component="$1"
    local var="BASE_ENV_LOCK_FILE_${component^^}"
    echo "${!var:-}"
}

# Build (once per TAG) the dedicated, pinned base env for one component.
# The lock file must be a FULLY RESOLVED spec (e.g. the output of
# `conda list --explicit` from a known-good env for that component), not a
# dev.yml -- a dev.yml re-solves and can silently drift between runs even
# unmodified.
#
# This is what makes "freeze everything else" possible: every test env
# cloned from base_env_name starts from byte-identical package versions, so
# any image diff that shows up after `pip install .`-ing the branch under
# test can be attributed to that branch rather than to incidental dependency
# movement.
setup_base_env() {
    local component="$1"
    local base_env_name="$2"
    local lock_file="$3"

    activate_env  # Ensure conda itself is available

    if conda env list | grep -q "^${base_env_name} "; then
        log "Base env '$base_env_name' already exists, skipping creation"
        return 0
    fi

    if [[ -z "$lock_file" || ! -f "$lock_file" ]]; then
        log_error "FREEZE_DEPENDENCIES=true and '${component}' is in FROZEN_BASE_COMPONENTS, but BASE_ENV_LOCK_FILE_${component^^} is missing or not found: '${lock_file}'"
        log_error "Generate one from a known-good env for this component, e.g.:"
        log_error "  conda env create -f <${component}'s dev.yml> -n tmp-lock-gen"
        log_error "  conda activate tmp-lock-gen"
        log_error "  conda list --explicit > /path/to/frozen-base-${component}.txt"
        log_error "Then set BASE_ENV_LOCK_FILE_${component^^} in your config to that path."
        exit 1
    fi

    log "Creating dedicated frozen base '$base_env_name' for '${component}' from ${lock_file}..."
    conda create --name "$base_env_name" --file "$lock_file" --yes
    log_success "Base env '$base_env_name' ready"
}

# Create (if needed) and activate a conda environment for a component.
#
# component_key: one of e3sm_to_cmip, e3sm_diags, mpas_analysis,
#                zppy_interfaces, zppy -- used to check FROZEN_BASE_COMPONENTS
#                via uses_frozen_base() and to look up this component's own
#                BASE_ENV_LOCK_FILE_<COMPONENT>.
# conda_dir:     directory containing dev.yml (e.g. "conda" or "conda-env"),
#                or "none" to use dev-spec.txt instead. Ignored when this
#                component is using its frozen base.
# env_name:      name of the environment to create/activate.
setup_conda_env() {
    local component_key="$1"
    local conda_dir="$2"
    local env_name="$3"

    activate_env  # Ensure conda itself is available

    if conda env list | grep -q "^${env_name} "; then
        log "Environment '$env_name' already exists, skipping creation"
    elif uses_frozen_base "$component_key"; then
        local base_env_name lock_file
        base_env_name="test-frozen-base-${component_key}-${TAG}"
        lock_file="$(get_component_lock_file "$component_key")"
        setup_base_env "$component_key" "$base_env_name" "$lock_file"  # no-op if it already exists this run
        log "Cloning '$env_name' from '${component_key}'s frozen base '$base_env_name' (deps pinned)..."
        conda create --name "$env_name" --clone "$base_env_name" --yes
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

    # For frozen-base envs, snapshot the exact package set before the
    # `pip install .` that activate_env() below performs, so we can tell
    # whether the package under test pulled in anything beyond itself.
    local _pre_install_file="${SCRIPT_RUN_DIR}/pre_install_${env_name}_${TAG}.txt"
    if uses_frozen_base "$component_key"; then
        conda list --explicit > "$_pre_install_file" 2>/dev/null || true
    fi

    activate_env "$env_name"
    log_success "Environment '$env_name' ready"

    if uses_frozen_base "$component_key"; then
        local _post_install_file="${SCRIPT_RUN_DIR}/post_install_${env_name}_${TAG}.txt"
        conda list --explicit > "$_post_install_file" 2>/dev/null || true
        if [[ -f "$_pre_install_file" ]] && ! diff -q "$_pre_install_file" "$_post_install_file" > /dev/null 2>&1; then
            log_warning "'$env_name': package set changed beyond the frozen base after 'pip install .'."
            log_warning "This is expected ONLY if '${component_key}' itself added or bumped a dependency:"
            diff "$_pre_install_file" "$_post_install_file" || true
        fi
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

    if ! compgen -G "${dir}/*status" > /dev/null; then
        log_warning "$name: No status files found in ${dir}"
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
    if [[ "$FREEZE_DEPENDENCIES" == true ]]; then
        log "Frozen base: ENABLED for components: ${FROZEN_BASE_COMPONENTS} (each has its own dedicated frozen base env)"
    else
        log "Frozen base: disabled (each dev env solves its own dev.yml)"
    fi
    log ""
    log "To resume from a later phase, set in your config:"
    log "  START_PHASE=2"
    log "  EXPLICIT_TAG=${TAG}"
    log "========================================="

    # Capture the baseline environment before any component setup so we have
    # a clean reference to diff against later snapshots.
    debug_env_snapshot "phase-1-start"

    # ------------------------------------------------------------------
    # e3sm_to_cmip
    # ------------------------------------------------------------------
    log "Setting up e3sm_to_cmip..."

    local E3SM_TO_CMIP_ENV=""
    if [[ "$E3SM_TO_CMIP_ENV_TYPE" == "dev" ]]; then
        if [[ -n "$E3SM_TO_CMIP_EXISTING_ENV" ]]; then
            E3SM_TO_CMIP_ENV="$E3SM_TO_CMIP_EXISTING_ENV"
        else
            E3SM_TO_CMIP_ENV="test-e3sm-to-cmip-${E3SM_TO_CMIP_BASE_BRANCH}-${TAG}"
        fi
    fi

    (
        cd "$E3SM_TO_CMIP_DIR"
        ensure_test_branch "test_e3sm_to_cmip_${TAG}" "$E3SM_TO_CMIP_BASE_BRANCH"

        log "Latest e3sm_to_cmip commit (should match https://github.com/E3SM-Project/e3sm_to_cmip/commits/${E3SM_TO_CMIP_BASE_BRANCH}):"
        git log -1 --oneline

        if [[ "$E3SM_TO_CMIP_ENV_TYPE" == "dev" ]]; then
            if [[ -n "$E3SM_TO_CMIP_EXISTING_ENV" ]]; then
                log "Reusing existing 'e3sm_to_cmip' env: $E3SM_TO_CMIP_EXISTING_ENV (skipping creation)"
                activate_env "$E3SM_TO_CMIP_EXISTING_ENV"
            else
                setup_conda_env "e3sm_to_cmip" "conda-env" "$E3SM_TO_CMIP_ENV"
            fi
        else
            log "Using unified env for e3sm_to_cmip (skipping conda env creation)"
        fi
    )

    # ------------------------------------------------------------------
    # e3sm_diags
    # ------------------------------------------------------------------
    log "Setting up e3sm_diags..."

    local DIAGS_ENV=""
    if [[ "$DIAGS_ENV_TYPE" == "dev" ]]; then
        if [[ -n "$DIAGS_EXISTING_ENV" ]]; then
            DIAGS_ENV="$DIAGS_EXISTING_ENV"
        else
            DIAGS_ENV="test-diags-${DIAGS_BASE_BRANCH}-${TAG}"
        fi
    fi

    (
        cd "$E3SM_DIAGS_DIR"
        ensure_test_branch "test_e3sm_diags_${TAG}" "$DIAGS_BASE_BRANCH"

        log "Latest e3sm_diags commit (should match https://github.com/E3SM-Project/e3sm_diags/commits/${DIAGS_BASE_BRANCH}):"
        git log -1 --oneline

        if [[ "$DIAGS_ENV_TYPE" == "dev" ]]; then
            if [[ -n "$DIAGS_EXISTING_ENV" ]]; then
                log "Reusing existing 'e3sm_diags' env: $DIAGS_EXISTING_ENV (skipping creation)"
                activate_env "$DIAGS_EXISTING_ENV"
            else
                setup_conda_env "e3sm_diags" "conda-env" "$DIAGS_ENV"
            fi
        else
            log "Using unified env for e3sm_diags (skipping conda env creation)"
        fi
    )

    # ------------------------------------------------------------------
    # MPAS-Analysis
    # ------------------------------------------------------------------
    log "Setting up MPAS-Analysis..."

    # Snapshot the environment immediately before entering the MPAS subshell.
    # Compare this against the post-activate snapshot to spot any leakage
    # from the e3sm_to_cmip or e3sm_diags subshells above (LD_LIBRARY_PATH,
    # CONDA_PREFIX nesting, PYTHONPATH, etc.).
    debug_env_snapshot "before-mpas-subshell"

    local MPAS_ENV=""
    if [[ "$MPAS_ENV_TYPE" == "dev" ]]; then
        if [[ -n "$MPAS_EXISTING_ENV" ]]; then
            MPAS_ENV="$MPAS_EXISTING_ENV"
        else
            MPAS_ENV="test-mpas-${MPAS_BASE_BRANCH}-${TAG}"
        fi
    fi

    (
        cd "$MPAS_ANALYSIS_DIR"
        ensure_test_branch "test_mpas_${TAG}" "$MPAS_BASE_BRANCH"

        log "Latest MPAS-Analysis commit (should match https://github.com/MPAS-Dev/MPAS-Analysis/commits/${MPAS_BASE_BRANCH}):"
        git log -1 --oneline

        if [[ "$MPAS_ENV_TYPE" == "dev" ]]; then
            if [[ -n "$MPAS_EXISTING_ENV" ]]; then
                log "Reusing existing 'MPAS-Analysis' env: $MPAS_EXISTING_ENV (skipping creation)"
                activate_env "$MPAS_EXISTING_ENV"
                # Snapshot after activating the pre-existing env. A mismatch
                # between this and the before-mpas-subshell snapshot (especially
                # in LD_LIBRARY_PATH) is a likely segfault cause.
                debug_env_snapshot "mpas-subshell-after-activate-existing"
                debug_mpas_preflight "mpas-existing-env"
            else
                setup_conda_env "mpas_analysis" "none" "$MPAS_ENV"
                # Snapshot after a fresh env creation + activation. Check that
                # CONDA_PREFIX is clean and LD_LIBRARY_PATH only contains paths
                # from this env, not any prior one.
                debug_env_snapshot "mpas-subshell-after-setup-conda"
                debug_mpas_preflight "mpas-new-env"
            fi
        else
            log "Using unified env for MPAS-Analysis (skipping conda env creation)"
            # Snapshot even for the unified-env path -- the unified env loader
            # modifies LD_LIBRARY_PATH in ways that can conflict with prior envs.
            debug_env_snapshot "mpas-subshell-unified-env"
            debug_mpas_preflight "mpas-unified-env"
        fi
    )

    # ------------------------------------------------------------------
    # zppy-interfaces (includes unit tests)
    # ------------------------------------------------------------------
    log "Setting up zppy-interfaces..."

    local ZI_ENV=""
    if [[ "$ZI_ENV_TYPE" == "dev" ]]; then
        if [[ -n "$ZI_EXISTING_ENV" ]]; then
            ZI_ENV="$ZI_EXISTING_ENV"
        else
            ZI_ENV="test-zi-${ZI_BASE_BRANCH}-${TAG}"
        fi
    fi

    (
        cd "$ZPPY_INTERFACES_DIR"
        ensure_test_branch "test_zi_${TAG}" "$ZI_BASE_BRANCH"

        log "Latest zppy-interfaces commit (should match https://github.com/E3SM-Project/zppy-interfaces/commits/${ZI_BASE_BRANCH}):"
        git log -1 --oneline

        if [[ "$ZI_ENV_TYPE" == "dev" ]]; then
            if [[ -n "$ZI_EXISTING_ENV" ]]; then
                log "Reusing existing 'zppy-interfaces' env: $ZI_EXISTING_ENV (skipping creation)"
                activate_env "$ZI_EXISTING_ENV"
            else
                setup_conda_env "zppy_interfaces" "conda" "$ZI_ENV"
            fi
        else
            log "Using unified env for zppy-interfaces..."
            activate_unified_env
        fi

        log "Running zppy-interfaces unit tests..."
        pytest tests/unit/global_time_series/test_*.py
        pytest tests/unit/pcmdi_diags/test_*.py
        log_success "zppy-interfaces unit tests passed"
    )

    # ------------------------------------------------------------------
    # zppy (includes unit tests + config generation)
    # ------------------------------------------------------------------
    log "Setting up zppy..."

    # Resolve ZPPY_ENV name before the subshell so it's available for
    # config generation and later phases.
    if [[ -n "$ZPPY_EXISTING_ENV" ]]; then
        ZPPY_ENV="$ZPPY_EXISTING_ENV"
    fi
    # (If ZPPY_EXISTING_ENV is empty, ZPPY_ENV retains the auto-generated
    # name set at the top of the script.)

    (
        cd "$ZPPY_DIR"
        ensure_test_branch "test_zppy_${TAG}" "$ZPPY_BASE_BRANCH"

        log "Latest zppy commit (should match https://github.com/E3SM-Project/zppy/commits/${ZPPY_BASE_BRANCH}):"
        git log -1 --oneline

        if [[ -n "$ZPPY_EXISTING_ENV" ]]; then
            log "Reusing existing 'zppy' env: $ZPPY_EXISTING_ENV (skipping creation)"
            activate_env "$ZPPY_ENV"
        else
            setup_conda_env "zppy" "conda" "$ZPPY_ENV"
        fi

        log "Running zppy unit tests..."
        pytest tests/test_*.py
        log_success "zppy unit tests passed"
    )

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

    # Config generation and job submission run in the parent shell so that
    # the zppy command is available and cd/env state is consistent.
    cd "$ZPPY_DIR"
    activate_env "$ZPPY_ENV"
    ensure_test_branch "test_zppy_${TAG}" "$ZPPY_BASE_BRANCH"

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
    env > "${SCRIPT_RUN_DIR}/env_${TAG}.txt"
    local cfg cfg_path
    for cfg in "${CFGS_ARRAY[@]}"; do
        cfg="${cfg// /}"
        cfg_path="tests/integration/generated/test_${cfg}_${MACHINE_CFG_SUFFIX}.cfg"
        if [[ ! -f "$cfg_path" ]]; then
            log_error "Config file not found: $cfg_path"
            log_error "Check that each CFGS_TO_RUN entry matches a cfg name generated by tests/integration/utils.py (e.g., weekly_comprehensive_v3)."
            exit 1
        fi
        log "Submitting: $cfg_path"
        zppy -c "$cfg_path"
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
    local cfg cfg_path
    for cfg in "${CFGS_ARRAY[@]}"; do
        cfg="${cfg// /}"
        if [[ "$cfg" == *bundle* ]]; then
            cfg_path="tests/integration/generated/test_${cfg}_${MACHINE_CFG_SUFFIX}.cfg"
            if [[ ! -f "$cfg_path" ]]; then
                log_error "Config file not found: $cfg_path"
                log_error "Check that each CFGS_TO_RUN entry matches a cfg name generated by tests/integration/utils.py (e.g., weekly_bundles)."
                exit 1
            fi
            log "Submitting: $cfg_path"
            zppy -c "$cfg_path"
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
    if [[ "$FREEZE_DEPENDENCIES" == true ]]; then
        log "  (Frozen base was used for: ${FROZEN_BASE_COMPONENTS} -- any diffs here"
        log "   should trace back to those packages, not unrelated dependency drift.)"
    fi

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
