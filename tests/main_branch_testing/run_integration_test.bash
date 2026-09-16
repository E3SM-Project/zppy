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
#   3 - Validation: status checks + pytest integration tests + image checker
#
# Notes:
#   - test_images.py (the image checker) is now launched automatically by
#     Phase 3 via a SLURM batch job -- no manual compute-node step needed.
#   - A Markdown report is written to ${SCRIPT_RUN_DIR}/test_report_<TAG>.md
#     at the end of Phase 3, summarizing every automated step.
#   - An env_description.txt is written for each task, recording the commit
#     hash of the relevant package (or "release" for unified-env tasks) and
#     the conda environment's package versions.
#   - To resume from Phase 2 or 3 on a later day, set EXPLICIT_TAG in your config
#     to the TAG printed at the start of Phase 1 (or stored in ~/.zppy_test_tag),
#     and set START_PHASE accordingly.
#   - To run this script unattended on a schedule (e.g. a weekly cron job),
#     see docs/source/dev_guide/tests/automated_test.rst.

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

# Apply defaults for optional *_EXPECTED_RESULTS_BRANCH variables. Each
# defaults to that component's own *_BASE_BRANCH (i.e. "assume expected
# results were generated from whatever branch we're testing"). Override
# in the config only when testing a variant/feature branch whose expected
# results are still based on a different branch (typically the project's
# default branch, e.g. "main") -- see Step 2 of the Markdown report.
DIAGS_EXPECTED_RESULTS_BRANCH="${DIAGS_EXPECTED_RESULTS_BRANCH:-$DIAGS_BASE_BRANCH}"
E3SM_TO_CMIP_EXPECTED_RESULTS_BRANCH="${E3SM_TO_CMIP_EXPECTED_RESULTS_BRANCH:-$E3SM_TO_CMIP_BASE_BRANCH}"
MPAS_EXPECTED_RESULTS_BRANCH="${MPAS_EXPECTED_RESULTS_BRANCH:-$MPAS_BASE_BRANCH}"
ZI_EXPECTED_RESULTS_BRANCH="${ZI_EXPECTED_RESULTS_BRANCH:-$ZI_BASE_BRANCH}"
ZPPY_EXPECTED_RESULTS_BRANCH="${ZPPY_EXPECTED_RESULTS_BRANCH:-$ZPPY_BASE_BRANCH}"

# Optional: used to auto-populate Step 1 / Step 2 of the Markdown report.
# Leave EXPECTED_RESULTS_DIR empty to skip those sections entirely.
EXPECTED_RESULTS_DIR="${EXPECTED_RESULTS_DIR:-}"

# Apply defaults for optional *_EXPECTED_RESULTS_DATE variables (leave
# empty here; auto-detection happens further down once CFGS_ARRAY exists).
DIAGS_EXPECTED_RESULTS_DATE="${DIAGS_EXPECTED_RESULTS_DATE:-}"
MPAS_EXPECTED_RESULTS_DATE="${MPAS_EXPECTED_RESULTS_DATE:-}"
ZI_GLOBAL_TIME_SERIES_EXPECTED_RESULTS_DATE="${ZI_GLOBAL_TIME_SERIES_EXPECTED_RESULTS_DATE:-}"
ZI_PCMDI_DIAGS_EXPECTED_RESULTS_DATE="${ZI_PCMDI_DIAGS_EXPECTED_RESULTS_DATE:-}"
# e3sm_to_cmip and zppy produce no task subdirs of their own, so there's no
# "expected results" to track for them -- just whether anything has changed
# since the last time we tested this dependency at all.
E3SM_TO_CMIP_LAST_TESTED_DATE="${E3SM_TO_CMIP_LAST_TESTED_DATE:-}"
ZPPY_LAST_TESTED_DATE="${ZPPY_LAST_TESTED_DATE:-}"

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
        # SBATCH directives (one per line) for the auto-launched image checker job.
        SBATCH_DIRECTIVES=$'#SBATCH --partition=debug\n#SBATCH --time=02:00:00\n#SBATCH --account=e3sm'
        ;;
    compy)
        OUTPUT_WORKSPACE="/compyfs/${USER}"
        CONDA_ACTIVATION_CMD="compy_conda"
        UNIFIED_ENV_CMD="source /share/apps/E3SM/conda_envs/load_latest_e3sm_unified_compy.sh"
        SALLOC_CMD="salloc --nodes=1 --partition=short --time=01:00:00 --account=e3sm"
        SBATCH_DIRECTIVES=$'#SBATCH --partition=short\n#SBATCH --time=01:00:00\n#SBATCH --account=e3sm'
        ;;
    perlmutter)
        OUTPUT_WORKSPACE="/global/cfs/cdirs/e3sm/${USER}"
        CONDA_ACTIVATION_CMD="nersc_conda"
        UNIFIED_ENV_CMD="source /global/common/software/e3sm/anaconda_envs/load_latest_e3sm_unified_pm-cpu.sh"
        SALLOC_CMD="salloc --nodes=1 --qos=debug --time=01:00:00 --constraint=cpu --account=e3sm"
        SBATCH_DIRECTIVES=$'#SBATCH --qos=debug\n#SBATCH --time=01:00:00\n#SBATCH --constraint=cpu\n#SBATCH --account=e3sm'
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
# Expected-results production dates (per dependency)
# ============================================================================
#
# EXPECTED_RESULTS_DIR holds one "expected_<cfg>/" subdirectory per cfg
# (e.g. "expected_comprehensive_v3/"), each containing one subdirectory per
# task (e.g. "e3sm_diags/"). Once promoted, each task directory carries the
# env_description.txt written by capture_env_description() during the run
# that produced it, whose "Generated: YYYY-MM-DD HH:MM:SS" line records
# when those results were actually PRODUCED.
#
# That is a different question from when they were last PROMOTED (copied
# into place), and a directory's mtime correctly answers the latter, not
# the former. The two routinely differ, by design: a run's results
# normally sit under review while a task developer confirms whether the
# diffs look acceptable, and only get promoted as the new expected results
# later -- often right before the *next* test run needs a fresh baseline,
# not right after the run that produced them. E.g. e3sm_diags's expected
# results were correctly copied into place on 9/4, but that promotion
# carried forward the 8/28 run's output (confirmed acceptable only after
# the fact) rather than a fresh 9/4 run. mtime isn't wrong about 9/4; it's
# just answering "when was this promoted", not "when was this produced",
# and those two questions can have very different answers as a routine
# part of the workflow. So we read the production date out of
# env_description.txt's own content instead, which records that
# regardless of when/how much later the directory gets copied.
#
# A single top-level or single per-cfg date is also the wrong shape: a cfg
# directory's mtime reflects whichever task inside it was touched most
# recently (e.g. "expected_comprehensive_v3/" looking freshly updated
# because only pcmdi_diags was refreshed), and the top-level directory's
# mtime is dominated by files like image_list_expected_*.txt that get
# rewritten on every single run regardless of which task's data actually
# changed. So detection here is per (cfg, task), scanned across every cfg
# actually being tested.
#
# zppy-interfaces bundles two unrelated tasks (global_time_series and
# pcmdi_diags) that get refreshed independently -- one can be updated on
# one date and the other much later -- so their expected-results dates are
# tracked and reported separately (ZI_GLOBAL_TIME_SERIES_EXPECTED_RESULTS_DATE
# / ZI_PCMDI_DIAGS_EXPECTED_RESULTS_DATE) rather than folded into one ZI date.
#
# e3sm_to_cmip and zppy, on the other hand, produce no task subdir of their
# own at all, so there's no per-task "expected results" file to read a
# production date from -- the only meaningful question for them is whether
# anything has changed since the last time we tested that dependency, full
# stop. That's a different concept from "when were the expected results
# produced", so those two use *_LAST_TESTED_DATE variables instead of
# *_EXPECTED_RESULTS_DATE, even though the detection mechanics below are
# shared with the other dependencies.

# Extract the "YYYY-MM-DD" date portion of the "Generated:" line from one
# env_description.txt, or nothing if the file/line isn't present.
_read_env_description_date() {
    local desc_file="$1"
    [[ -f "$desc_file" ]] || return 0
    awk -F': ' '/^Generated:/ { print $2; exit }' "$desc_file" 2>/dev/null | awk '{print $1}'
}

# Scans every cfg in CFGS_ARRAY for the given task name(s)'
# env_description.txt (or, with no task names given, every task
# subdirectory present) and prints the EARLIEST "Generated:" date found.
# Earliest is a deliberately conservative choice: it surfaces at least as
# many candidate upstream commits as could plausibly explain a diff,
# rather than risking missing the real cause (as happened when only the
# 9/4 promotion date was considered for e3sm_diags).
_detect_expected_results_date() {
    local -a tasks=("$@")
    local earliest="" cfg cfg_dirname task_dir task found_date

    [[ -n "$EXPECTED_RESULTS_DIR" && -d "$EXPECTED_RESULTS_DIR" ]] || return 0

    for cfg in "${CFGS_ARRAY[@]}"; do
        cfg="${cfg// /}"
        cfg_dirname="expected_${cfg#weekly_}"
        [[ -d "${EXPECTED_RESULTS_DIR}/${cfg_dirname}" ]] || continue

        if [[ ${#tasks[@]} -eq 0 ]]; then
            # No specific task: consider every task subdirectory present.
            for task_dir in "${EXPECTED_RESULTS_DIR}/${cfg_dirname}"/*/; do
                [[ -d "$task_dir" ]] || continue
                found_date="$(_read_env_description_date "${task_dir}env_description.txt")"
                if [[ -n "$found_date" && ( -z "$earliest" || "$found_date" < "$earliest" ) ]]; then
                    earliest="$found_date"
                fi
            done
        else
            for task in "${tasks[@]}"; do
                found_date="$(_read_env_description_date "${EXPECTED_RESULTS_DIR}/${cfg_dirname}/${task}/env_description.txt")"
                if [[ -n "$found_date" && ( -z "$earliest" || "$found_date" < "$earliest" ) ]]; then
                    earliest="$found_date"
                fi
            done
        fi
    done

    echo "$earliest"
}

# Apply per-dependency EXPECTED_RESULTS_DATE / LAST_TESTED_DATE: an explicit
# config value always wins (e.g. when a human has determined, as in the
# e3sm_diags case above, that the auto-detected/promoted date doesn't
# reflect the truth); otherwise auto-detect from env_description.txt as
# described above. e3sm_to_cmip and zppy have no dedicated task directory of
# their own, so they fall back to the earliest production date found across
# ALL tasks.
if [[ -z "$DIAGS_EXPECTED_RESULTS_DATE" ]]; then
    DIAGS_EXPECTED_RESULTS_DATE="$(_detect_expected_results_date "e3sm_diags")"
fi
if [[ -z "$MPAS_EXPECTED_RESULTS_DATE" ]]; then
    MPAS_EXPECTED_RESULTS_DATE="$(_detect_expected_results_date "mpas_analysis")"
fi
if [[ -z "$ZI_GLOBAL_TIME_SERIES_EXPECTED_RESULTS_DATE" ]]; then
    ZI_GLOBAL_TIME_SERIES_EXPECTED_RESULTS_DATE="$(_detect_expected_results_date "global_time_series")"
fi
if [[ -z "$ZI_PCMDI_DIAGS_EXPECTED_RESULTS_DATE" ]]; then
    ZI_PCMDI_DIAGS_EXPECTED_RESULTS_DATE="$(_detect_expected_results_date "pcmdi_diags")"
fi
if [[ -z "$E3SM_TO_CMIP_LAST_TESTED_DATE" ]]; then
    E3SM_TO_CMIP_LAST_TESTED_DATE="$(_detect_expected_results_date)"
fi
if [[ -z "$ZPPY_LAST_TESTED_DATE" ]]; then
    ZPPY_LAST_TESTED_DATE="$(_detect_expected_results_date)"
fi
for _dep_entry in \
    "e3sm_diags:$DIAGS_EXPECTED_RESULTS_DATE:DIAGS_EXPECTED_RESULTS_DATE" \
    "mpas_analysis:$MPAS_EXPECTED_RESULTS_DATE:MPAS_EXPECTED_RESULTS_DATE" \
    "zppy-interfaces (global_time_series):$ZI_GLOBAL_TIME_SERIES_EXPECTED_RESULTS_DATE:ZI_GLOBAL_TIME_SERIES_EXPECTED_RESULTS_DATE" \
    "zppy-interfaces (pcmdi_diags):$ZI_PCMDI_DIAGS_EXPECTED_RESULTS_DATE:ZI_PCMDI_DIAGS_EXPECTED_RESULTS_DATE" \
    "e3sm_to_cmip:$E3SM_TO_CMIP_LAST_TESTED_DATE:E3SM_TO_CMIP_LAST_TESTED_DATE" \
    "zppy:$ZPPY_LAST_TESTED_DATE:ZPPY_LAST_TESTED_DATE"
do
    IFS=':' read -r _dep_name _dep_date _dep_var <<< "$_dep_entry"
    if [[ -z "$_dep_date" && -n "$EXPECTED_RESULTS_DIR" ]]; then
        echo "Warning: Could not auto-detect a date for ${_dep_name} from ${EXPECTED_RESULTS_DIR} (no env_description.txt with a Generated: line found). Set ${_dep_var} in the config to fix Step 2 of the report." >&2
    fi
done
unset _dep_entry _dep_name _dep_date _dep_var
unset _dep_label

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
if [[ -n "$ZPPY_EXISTING_ENV" ]]; then
    ZPPY_ENV="$ZPPY_EXISTING_ENV"
fi

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

# Where cached env_description.txt snippets (one per task) are staged before
# being copied out to each cfg's "_www" output tree. See capture_env_description
# and distribute_env_descriptions below.
ENV_DESC_DIR="${SCRIPT_RUN_DIR}/env_descriptions_${TAG}"

# Where the auto-generated Markdown report and image-checker artifacts land.
REPORT_FILE="${SCRIPT_RUN_DIR}/test_report_${TAG}.md"
IMAGE_CHECKER_SBATCH="${SCRIPT_RUN_DIR}/image_checker_${TAG}.sbatch"
IMAGE_CHECKER_STDOUT_PREFIX="${SCRIPT_RUN_DIR}/image_checker_${TAG}"
IMAGE_CHECKER_JOB_ID=""
IMAGE_CHECKER_JOB_STATE="not_run"
IMAGE_CHECKER_EXIT_CODE="N/A"
IMAGE_CHECKER_STDOUT=""
IMAGE_CHECKER_STDERR=""
IMAGE_CHECKER_SUMMARY_SOURCE="none"
ZI_UNIT_TEST_STATUS="not run in this invocation"
ZPPY_UNIT_TEST_STATUS="not run in this invocation"
IMAGE_HELPER_UNIT_TEST_STATUS="not run in this invocation"
STATUS_FILE_CHECK_STATUS="not run in this invocation"
declare -a INTEGRATION_TEST_RESULTS=()
declare -A CAPTURED_ENV_TASKS=()

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

# Append a line (or block) of text to the Markdown report.
report_append() {
    printf '%s\n' "$*" >> "$REPORT_FILE"
}

init_conda_base() {
    set +u
    # shellcheck disable=SC1090
    source ~/.bashrc
    $CONDA_ACTIVATION_CMD  # Machine-specific conda init (lcrc_conda / compy_conda / nersc_conda)
}

# Activate conda and (optionally) a named environment.
activate_env() {
    local env_name="${1:-}"
    init_conda_base
    if [ -n "$env_name" ]; then
        conda activate "$env_name"
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
    init_conda_base
    # shellcheck disable=SC1090
    source "${UNIFIED_ENV_CMD#source }"
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

# ----------------------------------------------------------------------------
# Environment description capture (Requirement: env_description.txt per task)
# ----------------------------------------------------------------------------
#
# Writes a description of the environment used for a given task to
# ${ENV_DESC_DIR}/<task>.txt. For dev environments, this includes the git
# commit hash of the relevant package repo plus `conda list` output. For
# unified/release environments there's no dedicated dev repo, so only the
# conda package list is captured.
#
#   capture_env_description <task_name> <pkg_dir_or_empty> <env_type> <env_name>
capture_env_description() {
    local task_name="$1"
    local pkg_dir="$2"
    local env_type="$3"
    local env_name="$4"
    local out_file="${ENV_DESC_DIR}/${task_name}.txt"

    mkdir -p "$ENV_DESC_DIR"

    {
        echo "Task: ${task_name}"
        echo "Generated: $(date +'%Y-%m-%d %H:%M:%S')"
        echo ""
        if [[ "$env_type" == "dev" && -n "$pkg_dir" && -d "$pkg_dir" ]]; then
            echo "Repository: ${pkg_dir}"
            echo "Commit: $(git -C "$pkg_dir" rev-parse HEAD 2>/dev/null || echo unknown)"
            echo "Commit (short): $(git -C "$pkg_dir" rev-parse --short HEAD 2>/dev/null || echo unknown)"
            echo "Branch: $(git -C "$pkg_dir" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
        else
            echo "Repository: N/A (uses a released package via the unified environment)"
        fi
        echo ""
        if [[ "$env_type" == "dev" ]]; then
            echo "Conda environment (dev): ${env_name}"
            echo ""
            echo "Package versions:"
            echo "-----------------"
            ( init_conda_base && conda list -n "${env_name}" ) 2>/dev/null || echo "(unable to list packages for ${env_name})"
        else
            echo "Conda environment: E3SM-Unified"
            echo ""
            echo "Package versions:"
            echo "-----------------"
            ( activate_unified_env && conda list ) 2>/dev/null || echo "(unable to list packages for the unified environment)"
        fi
    } > "$out_file"
    CAPTURED_ENV_TASKS["$task_name"]=1

    log "Wrote environment description for task '${task_name}' -> ${out_file}"
}

# Copy each task's cached env_description.txt out to the "_www" output tree
# for every cfg that was run, so it sits alongside that task's diagnostics
# (e.g. .../zppy_weekly_comprehensive_v3_www/<unique_id>/<case>/global_time_series/env_description.txt).
distribute_env_descriptions() {
    log "Distributing environment descriptions to task output directories..."
    local cfg case task desc_file target_dir www_root cfg_file
    for cfg in "${CFGS_ARRAY[@]}"; do
        cfg="${cfg// /}"
        if [[ "$cfg" == *v2* ]]; then
            case="v2.LR.historical_0201"
        else
            case="v3.LR.historical_0051"
        fi
        cfg_file="${ZPPY_DIR}/tests/integration/generated/test_${cfg}_${MACHINE_CFG_SUFFIX}.cfg"
        if [[ ! -f "$cfg_file" ]]; then
            log_warning "Config file not found while distributing env descriptions: ${cfg_file}"
            continue
        fi
        www_root=$(awk -F'=' '
            /^[[:space:]]*www[[:space:]]*=/ {
                value=$2
                gsub(/^[[:space:]]+|[[:space:]]+$/, "", value)
                gsub(/^"|"$/, "", value)
                print value
                exit
            }
        ' "$cfg_file")
        if [[ -z "$www_root" ]]; then
            log_warning "Could not determine www root from ${cfg_file}; skipping env-description copies for ${cfg}"
            continue
        fi
        for task in "${TASKS_ARRAY[@]}"; do
            task="${task// /}"
            desc_file="${ENV_DESC_DIR}/${task}.txt"
            if [[ ! -f "$desc_file" ]]; then
                continue
            fi
            # NOTE: the "www" value read from the generated cfg is already
            # the fully-resolved per-cfg/per-run root (it already bakes in
            # "zppy_<cfg>_www/<unique_id>"), so we only need to append
            # <case>/<task> here. Appending "zppy_<cfg>_www/<unique_id>"
            # again created a spurious duplicate subtree that the
            # expected-results updater script never picks up.
            target_dir="${www_root%/}/${case}/${task}"
            mkdir -p "$target_dir" 2>/dev/null || {
                log_warning "Could not create ${target_dir}; skipping env description for ${cfg}/${task}"
                continue
            }
            cp "$desc_file" "${target_dir}/env_description.txt"
        done
    done
    log_success "Environment descriptions distributed."
}

# ----------------------------------------------------------------------------
# Auto-launch the image checker (Requirement: no manual compute-node step)
# ----------------------------------------------------------------------------
#
# Submits tests/integration/test_images.py as a SLURM batch job (using the
# same partition/qos/time/account as the documented manual salloc command),
# waits for it to finish, and records the job's stdout log + generated
# test_images_summary.md for the Markdown report.
get_slurm_job_status() {
    local job_id="$1"
    sacct -X --parsable2 --noheader -j "$job_id" \
        --format=JobIDRaw,State,ExitCode 2>/dev/null \
        | awk -F'|' -v id="$job_id" '$1 == id {print $2 "|" $3; exit}'
}

is_terminal_slurm_state() {
    local state="$1"
    case "$state" in
        COMPLETED*|FAILED*|CANCELLED*|TIMEOUT*|OUT_OF_MEMORY*|NODE_FAIL*|PREEMPTED*|BOOT_FAIL*|DEADLINE*|SPECIAL_EXIT*)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

wait_for_slurm_job() {
    local job_id="$1"
    local check_interval=${2:-120}
    local max_wait=${3:-7200}
    local elapsed=0

    log "Waiting for SLURM job ${job_id} (checking every ${check_interval}s, max ${max_wait}s)..."
    while [ "$elapsed" -lt "$max_wait" ]; do
        local queue_state
        queue_state=$(squeue -h -j "$job_id" -o "%T" 2>/dev/null | head -n 1 || true)
        if [[ -n "$queue_state" ]]; then
            log "Image checker job ${job_id} state: ${queue_state} (elapsed: ${elapsed}s / max: ${max_wait}s)"
        else
            local status
            status=$(get_slurm_job_status "$job_id")
            if [[ -n "$status" ]]; then
                IMAGE_CHECKER_JOB_STATE="${status%%|*}"
                IMAGE_CHECKER_EXIT_CODE="${status#*|}"
                if is_terminal_slurm_state "$IMAGE_CHECKER_JOB_STATE"; then
                    log "Image checker job ${job_id} finished with state ${IMAGE_CHECKER_JOB_STATE} (ExitCode ${IMAGE_CHECKER_EXIT_CODE})"
                    [[ "$IMAGE_CHECKER_JOB_STATE" == COMPLETED* && "${IMAGE_CHECKER_EXIT_CODE%%:*}" == "0" ]]
                    return
                fi
            else
                log "Image checker job ${job_id} left squeue; waiting for accounting data..."
            fi
        fi

        sleep "$check_interval"
        elapsed=$((elapsed + check_interval))
    done

    IMAGE_CHECKER_JOB_STATE="TIMEOUT"
    IMAGE_CHECKER_EXIT_CODE="N/A"
    log_error "Timed out waiting for image checker job ${job_id}"
    return 1
}

get_preferred_git_remote() {
    local repo_dir="$1"
    if git -C "$repo_dir" remote get-url upstream >/dev/null 2>&1; then
        echo "upstream"
        return 0
    fi
    if git -C "$repo_dir" remote get-url origin >/dev/null 2>&1; then
        echo "origin"
        return 0
    fi
    return 1
}

run_image_checker() {
    local job_name="zppy_image_checker_${TAG}"
    local image_checker_ok=true

    log "Preparing image checker SLURM batch job..."
    rm -f "${ZPPY_DIR}/test_images_summary.md" "${ZPPY_DIR}/early_test_images_summary.md"
    cat > "$IMAGE_CHECKER_SBATCH" <<EOF
#!/bin/bash
#SBATCH --job-name=${job_name}
#SBATCH --nodes=1
#SBATCH --output=${IMAGE_CHECKER_STDOUT_PREFIX}.o%j
#SBATCH --error=${IMAGE_CHECKER_STDOUT_PREFIX}.e%j
${SBATCH_DIRECTIVES}

set -e
set +u
source ~/.bashrc
${CONDA_ACTIVATION_CMD}
conda activate ${ZPPY_ENV}
set -u
cd ${ZPPY_DIR}
pytest tests/integration/test_images.py
EOF

    log "Submitting image checker job (test_images.py)..."
    if ! IMAGE_CHECKER_JOB_ID=$(sbatch --parsable "$IMAGE_CHECKER_SBATCH"); then
        IMAGE_CHECKER_JOB_STATE="SUBMISSION_FAILED"
        IMAGE_CHECKER_EXIT_CODE="N/A"
        log_error "Failed to submit image checker job"
        return 1
    fi
    if [[ -z "$IMAGE_CHECKER_JOB_ID" ]]; then
        IMAGE_CHECKER_JOB_STATE="SUBMISSION_FAILED"
        IMAGE_CHECKER_EXIT_CODE="N/A"
        log_error "Image checker job submission returned an empty job ID"
        return 1
    fi
    log "Image checker job submitted: ${IMAGE_CHECKER_JOB_ID}"

    IMAGE_CHECKER_STDOUT="${IMAGE_CHECKER_STDOUT_PREFIX}.o${IMAGE_CHECKER_JOB_ID}"
    IMAGE_CHECKER_STDERR="${IMAGE_CHECKER_STDOUT_PREFIX}.e${IMAGE_CHECKER_JOB_ID}"

    if ! wait_for_slurm_job "$IMAGE_CHECKER_JOB_ID" 120 7200; then
        image_checker_ok=false
        log_error "Image checker job failed with state ${IMAGE_CHECKER_JOB_STATE} (ExitCode ${IMAGE_CHECKER_EXIT_CODE})"
    fi

    if [[ -f "$IMAGE_CHECKER_STDOUT" ]]; then
        if [ "$image_checker_ok" = true ]; then
            log_success "Image checker job passed. Output: ${IMAGE_CHECKER_STDOUT}"
        else
            log_error "Image checker job did not pass. Output: ${IMAGE_CHECKER_STDOUT}"
        fi
    else
        log_warning "Image checker output log not found: ${IMAGE_CHECKER_STDOUT}"
    fi

    if [[ -f "${ZPPY_DIR}/test_images_summary.md" ]]; then
        cp "${ZPPY_DIR}/test_images_summary.md" "${SCRIPT_RUN_DIR}/test_images_summary_${TAG}.md"
        IMAGE_CHECKER_SUMMARY_SOURCE="final"
        log_success "Copied test_images_summary.md -> ${SCRIPT_RUN_DIR}/test_images_summary_${TAG}.md"
    elif [[ -f "${ZPPY_DIR}/early_test_images_summary.md" ]]; then
        cp "${ZPPY_DIR}/early_test_images_summary.md" "${SCRIPT_RUN_DIR}/test_images_summary_${TAG}.md"
        IMAGE_CHECKER_SUMMARY_SOURCE="early"
        log_warning "Copied early_test_images_summary.md -> ${SCRIPT_RUN_DIR}/test_images_summary_${TAG}.md"
    else
        IMAGE_CHECKER_SUMMARY_SOURCE="missing"
        log_warning "test_images_summary.md not found in ${ZPPY_DIR}"
    fi

    [ "$image_checker_ok" = true ]
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
                setup_conda_env "conda-env" "$E3SM_TO_CMIP_ENV"
            fi
        else
            log "Using unified env for e3sm_to_cmip (skipping conda env creation)"
        fi
    )
    capture_env_description "e3sm_to_cmip" "$E3SM_TO_CMIP_DIR" "$E3SM_TO_CMIP_ENV_TYPE" "$E3SM_TO_CMIP_ENV"

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
                setup_conda_env "conda-env" "$DIAGS_ENV"
            fi
        else
            log "Using unified env for e3sm_diags (skipping conda env creation)"
        fi
    )
    capture_env_description "e3sm_diags" "$E3SM_DIAGS_DIR" "$DIAGS_ENV_TYPE" "$DIAGS_ENV"

    # ------------------------------------------------------------------
    # MPAS-Analysis
    # ------------------------------------------------------------------
    log "Setting up MPAS-Analysis..."

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
            else
                setup_conda_env "none" "$MPAS_ENV"
            fi
        else
            log "Using unified env for MPAS-Analysis (skipping conda env creation)"
        fi
    )
    capture_env_description "mpas_analysis" "$MPAS_ANALYSIS_DIR" "$MPAS_ENV_TYPE" "$MPAS_ENV"

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
                setup_conda_env "conda" "$ZI_ENV"
            fi
        else
            log "Using unified env for zppy-interfaces..."
            activate_unified_env
        fi

        log "Running zppy-interfaces unit tests..."
        pytest tests/unit/global_time_series/test_*.py
        pytest tests/unit/pcmdi_diags/test_*.py
    )
    ZI_UNIT_TEST_STATUS="passed"
    log_success "zppy-interfaces unit tests passed"
    # global_time_series and pcmdi_diags are both powered by zppy-interfaces.
    capture_env_description "global_time_series" "$ZPPY_INTERFACES_DIR" "$ZI_ENV_TYPE" "$ZI_ENV"
    capture_env_description "pcmdi_diags" "$ZPPY_INTERFACES_DIR" "$ZI_ENV_TYPE" "$ZI_ENV"

    # ------------------------------------------------------------------
    # Any configured task that has not already been associated with a
    # dedicated dev repo/env uses the unified/release environment.
    # ------------------------------------------------------------------
    local release_task
    for release_task in "${TASKS_ARRAY[@]}"; do
        release_task="${release_task// /}"
        if [[ -z "${CAPTURED_ENV_TASKS[$release_task]:-}" ]]; then
            capture_env_description "$release_task" "" "unified" ""
        fi
    done

    # ------------------------------------------------------------------
    # zppy (includes unit tests + config generation)
    # ------------------------------------------------------------------
    log "Setting up zppy..."

    (
        cd "$ZPPY_DIR"
        ensure_test_branch "test_zppy_${TAG}" "$ZPPY_BASE_BRANCH"

        log "Latest zppy commit (should match https://github.com/E3SM-Project/zppy/commits/${ZPPY_BASE_BRANCH}):"
        git log -1 --oneline

        if [[ -n "$ZPPY_EXISTING_ENV" ]]; then
            log "Reusing existing 'zppy' env: $ZPPY_EXISTING_ENV (skipping creation)"
            activate_env "$ZPPY_ENV"
        else
            setup_conda_env "conda" "$ZPPY_ENV"
        fi

        log "Running zppy unit tests..."
        pytest tests/test_*.py
    )
    ZPPY_UNIT_TEST_STATUS="passed"
    log_success "zppy unit tests passed"

    (
        cd "$ZPPY_DIR"
        ensure_test_branch "test_zppy_${TAG}" "$ZPPY_BASE_BRANCH"
        init_conda_base
        conda activate "$ZPPY_ENV"

        log "Running tests of the image checker itself..."
        pytest tests/images/test_image_checker.py
        pytest tests/images/test_image_severity.py
        pytest tests/images/test_image_summary_report.py
    )
    IMAGE_HELPER_UNIT_TEST_STATUS="passed"
    log_success "Image-checker/report unit tests passed"

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
# Phase 3: Validation (status checks + pytest integration tests + image checker)
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

    local overall_ok=true

    if [ "$all_good" = false ]; then
        overall_ok=false
        STATUS_FILE_CHECK_STATUS="failed"
        log_error "Some status checks failed!"
        checkpoint "Errors found in status files. Continue to pytest anyway?"
    else
        STATUS_FILE_CHECK_STATUS="passed"
        log_success "All status files clean!"
    fi

    # ------------------------------------------------------------------
    # Distribute per-task environment descriptions now that output
    # directories exist.
    # ------------------------------------------------------------------
    distribute_env_descriptions

    # ------------------------------------------------------------------
    # pytest integration tests
    # ------------------------------------------------------------------
    log "Running integration tests..."

    log "Running test_last_year.py (no expected results dir)..."
    if pytest tests/integration/test_last_year.py; then
        INTEGRATION_TEST_RESULTS+=("test_last_year.py: passed")
    else
        overall_ok=false
        INTEGRATION_TEST_RESULTS+=("test_last_year.py: failed")
        log_warning "test_last_year.py had failures"
    fi

    log "Running test_bash_generation.py..."
    if pytest tests/integration/test_bash_generation.py; then
        INTEGRATION_TEST_RESULTS+=("test_bash_generation.py: passed")
    else
        overall_ok=false
        INTEGRATION_TEST_RESULTS+=("test_bash_generation.py: failed")
        log_warning "test_bash_generation.py had failures"
    fi

    log "Running test_campaign.py..."
    if pytest tests/integration/test_campaign.py; then
        INTEGRATION_TEST_RESULTS+=("test_campaign.py: passed")
    else
        overall_ok=false
        INTEGRATION_TEST_RESULTS+=("test_campaign.py: failed")
        log_warning "test_campaign.py had failures"
    fi

    log "Running test_defaults.py..."
    if pytest tests/integration/test_defaults.py; then
        INTEGRATION_TEST_RESULTS+=("test_defaults.py: passed")
    else
        overall_ok=false
        INTEGRATION_TEST_RESULTS+=("test_defaults.py: failed")
        log_warning "test_defaults.py had failures"
    fi

    log "Running test_bundles.py..."
    if pytest tests/integration/test_bundles.py; then
        INTEGRATION_TEST_RESULTS+=("test_bundles.py: passed")
    else
        overall_ok=false
        INTEGRATION_TEST_RESULTS+=("test_bundles.py: failed")
        log_warning "test_bundles.py had failures"
    fi

    # ------------------------------------------------------------------
    # test_images.py -- now auto-launched via SLURM, no manual step needed.
    # ------------------------------------------------------------------
    log "Auto-launching the image checker (test_images.py) on a compute node..."
    if ! run_image_checker; then
        overall_ok=false
    fi

    if [ "$overall_ok" = true ]; then
        log_success "Phase 3 automated tests complete!"
    else
        log_error "Phase 3 automated tests completed with failures."
    fi

    # ------------------------------------------------------------------
    # Markdown report
    # ------------------------------------------------------------------
    generate_markdown_report
    log_success "Markdown report written: ${REPORT_FILE}"

    [ "$overall_ok" = true ]
}

# ============================================================================
# Markdown report generation (Requirement: write the Markdown report)
# ============================================================================
#
# Assembles ${REPORT_FILE} from: the captured integration_test log (this
# script's own stdout, if it was invoked with `| tee integration_test_runN.log`
# in the same directory), the per-task env_description.txt files, and the
# image checker's output/summary table. Sections that require human judgment
# (e.g. deciding whether image diffs are "expected") are left as TODOs.
generate_markdown_report() {
    log "Generating Markdown report..."

    {
        echo "# ${DATE_STAMP} zppy test"
        echo ""
        echo "Below, I follow the steps of the [automated testing docs page](https://docs.e3sm.org/zppy/_build/html/main/dev_guide/tests/automated_test.html)."
        echo ""
    } > "$REPORT_FILE"

    # --- Step 1: expected results directory (optional, auto-populated) ---
    report_append "## Step 1: Determine what the current expected results are"
    report_append ""
    if [[ -n "$EXPECTED_RESULTS_DIR" && -d "$EXPECTED_RESULTS_DIR" ]]; then
        report_append "Promotion date for each cfg/task under \`${EXPECTED_RESULTS_DIR}\` -- i.e. when its expected-results files were last copied into place. This is **not** necessarily when those results were actually produced (see Step 2, which uses a different, content-based date for exactly that reason)."
        report_append ""
        local cfg cfg_dirname task task_dir mtime_date
        local _found_any_cfg_dir=false
        for cfg in "${CFGS_ARRAY[@]}"; do
            cfg="${cfg// /}"
            cfg_dirname="expected_${cfg#weekly_}"
            [[ -d "${EXPECTED_RESULTS_DIR}/${cfg_dirname}" ]] || continue
            _found_any_cfg_dir=true
            report_append "\`${cfg_dirname}\`:"
            report_append ""
            report_append "| Task | Last promoted |"
            report_append "| --- | --- |"
            for task in "${TASKS_ARRAY[@]}"; do
                task="${task// /}"
                task_dir="${EXPECTED_RESULTS_DIR}/${cfg_dirname}/${task}"
                [[ -d "$task_dir" ]] || continue
                mtime_date="$(date -r "$task_dir" +%Y-%m-%d 2>/dev/null || echo unknown)"
                report_append "| ${task} | \`${mtime_date}\` |"
            done
            report_append ""
        done
        if [[ "$_found_any_cfg_dir" == false ]]; then
            report_append "_No \`expected_<cfg>\` subdirectories found under ${EXPECTED_RESULTS_DIR} for the cfgs in CFGS_TO_RUN._"
            report_append ""
        fi
        unset _found_any_cfg_dir
    else
        report_append "_TODO: set EXPECTED_RESULTS_DIR in the config to auto-populate this section._"
        report_append ""
    fi

    # --- Step 2: changes since expected results were updated ---
    report_append "## Step 2: Review changes since expected results were updated"
    report_append ""
    report_append "Commits merged on each repo's *expected-results baseline branch* (see the \"Branch tested\" column when it differs from the branch this run actually tested) since that dependency's expected results were actually **produced** (for \`e3sm_to_cmip\`/\`zppy\`, which have no per-task expected results of their own, since they were last **tested** instead -- see the \`*_LAST_TESTED_DATE\` config variables). The \"Since\" date is read from the \`Generated:\` line of the promoted \`env_description.txt\` (the earliest one found across every cfg being tested) -- deliberately not the promotion date from Step 1 above, since results normally sit under review before being promoted, so the promotion date routinely lags well behind the run that actually produced them (set the matching \`*_EXPECTED_RESULTS_DATE\`/\`*_LAST_TESTED_DATE\` in the config to override any date below when you know better, e.g. from a discussion thread). \`zppy-interfaces\` bundles two independently-refreshed tasks, so its row is split into \`global_time_series\` and \`pcmdi_diags\`, each with its own date."
    report_append ""
    report_append "| Package | Branch tested | Since | Changes since expected results were produced |"
    report_append "| --- | --- | --- | --- |"
    _report_repo_changes "e3sm_to_cmip" "$E3SM_TO_CMIP_DIR" "$E3SM_TO_CMIP_BASE_BRANCH" "$E3SM_TO_CMIP_EXPECTED_RESULTS_BRANCH" "$E3SM_TO_CMIP_LAST_TESTED_DATE" "https://github.com/E3SM-Project/e3sm_to_cmip" "E3SM_TO_CMIP_LAST_TESTED_DATE"
    _report_repo_changes "e3sm_diags" "$E3SM_DIAGS_DIR" "$DIAGS_BASE_BRANCH" "$DIAGS_EXPECTED_RESULTS_BRANCH" "$DIAGS_EXPECTED_RESULTS_DATE" "https://github.com/E3SM-Project/e3sm_diags" "DIAGS_EXPECTED_RESULTS_DATE"
    _report_repo_changes "mpas_analysis" "$MPAS_ANALYSIS_DIR" "$MPAS_BASE_BRANCH" "$MPAS_EXPECTED_RESULTS_BRANCH" "$MPAS_EXPECTED_RESULTS_DATE" "https://github.com/MPAS-Dev/MPAS-Analysis" "MPAS_EXPECTED_RESULTS_DATE"
    _report_repo_changes "zppy-interfaces (global_time_series)" "$ZPPY_INTERFACES_DIR" "$ZI_BASE_BRANCH" "$ZI_EXPECTED_RESULTS_BRANCH" "$ZI_GLOBAL_TIME_SERIES_EXPECTED_RESULTS_DATE" "https://github.com/E3SM-Project/zppy-interfaces" "ZI_GLOBAL_TIME_SERIES_EXPECTED_RESULTS_DATE"
    _report_repo_changes "zppy-interfaces (pcmdi_diags)" "$ZPPY_INTERFACES_DIR" "$ZI_BASE_BRANCH" "$ZI_EXPECTED_RESULTS_BRANCH" "$ZI_PCMDI_DIAGS_EXPECTED_RESULTS_DATE" "https://github.com/E3SM-Project/zppy-interfaces" "ZI_PCMDI_DIAGS_EXPECTED_RESULTS_DATE"
    _report_repo_changes "zppy" "$ZPPY_DIR" "$ZPPY_BASE_BRANCH" "$ZPPY_EXPECTED_RESULTS_BRANCH" "$ZPPY_LAST_TESTED_DATE" "https://github.com/E3SM-Project/zppy" "ZPPY_LAST_TESTED_DATE"
    report_append ""

    # --- Environment descriptions ---
    report_append "## Environment descriptions"
    report_append ""
    report_append "An \`env_description.txt\` (commit hash + conda package list) was written for each task alongside its diagnostic output. Locally cached copies:"
    report_append ""
    report_append "| Task | env_description.txt |"
    report_append "| --- | --- |"
    local desc_file task
    if compgen -G "${ENV_DESC_DIR}/*.txt" > /dev/null; then
        while IFS= read -r desc_file; do
            task="${desc_file##*/}"
            task="${task%.txt}"
            report_append "| ${task} | \`${desc_file}\` (also copied to each cfg's \`_www\` output dir) |"
        done < <(find "$ENV_DESC_DIR" -maxdepth 1 -type f -name '*.txt' | sort)
    else
        report_append "| _none_ | _env_description.txt files were not captured in ${ENV_DESC_DIR}_ |"
    fi
    report_append ""

    # --- Unit tests / status files / integration tests summary ---
    report_append "## Automated test script results"
    report_append ""
    report_append "* zppy-interfaces unit tests: \`${ZI_UNIT_TEST_STATUS}\`"
    report_append "* zppy unit tests: \`${ZPPY_UNIT_TEST_STATUS}\`"
    report_append "* Image-checker/report unit tests: \`${IMAGE_HELPER_UNIT_TEST_STATUS}\` (\`tests/images/test_image_checker.py\`, \`tests/images/test_image_severity.py\`, \`tests/images/test_image_summary_report.py\`)"
    report_append "* Output directory status files: \`${STATUS_FILE_CHECK_STATUS}\`"
    report_append "* Integration tests:"
    local integration_result
    for integration_result in "${INTEGRATION_TEST_RESULTS[@]}"; do
        report_append "  * \`${integration_result}\`"
    done
    report_append ""
    # The point of this script is full automation: if every line above says
    # "passed", there is nothing left to dig for in the raw log, so only
    # point at it when something didn't pass.
    local _any_failure=false
    [[ "$ZI_UNIT_TEST_STATUS" != "passed" ]] && _any_failure=true
    [[ "$ZPPY_UNIT_TEST_STATUS" != "passed" ]] && _any_failure=true
    [[ "$IMAGE_HELPER_UNIT_TEST_STATUS" != "passed" ]] && _any_failure=true
    [[ "$STATUS_FILE_CHECK_STATUS" != "passed" ]] && _any_failure=true
    for integration_result in "${INTEGRATION_TEST_RESULTS[@]}"; do
        [[ "$integration_result" == *": failed" ]] && _any_failure=true
    done
    if [[ "$_any_failure" == true ]]; then
        report_append "_TODO: one or more steps above did not pass -- review the full log captured from this script's stdout (for example, \`integration_test_runN.log\` if you used \`tee integration_test_runN.log\`) and note any unexpected failures here._"
        report_append ""
    fi
    unset _any_failure

    # --- Step 8: image checker (auto-launched) ---
    report_append "## Step 8: Run Python tests"
    report_append ""
    report_append "The image checker (\`pytest tests/integration/test_images.py\`) was launched automatically as a SLURM job and no longer requires a manual compute-node step."
    report_append ""
    report_append "* SLURM job ID: \`${IMAGE_CHECKER_JOB_ID:-unknown}\`"
    report_append "* Terminal state: \`${IMAGE_CHECKER_JOB_STATE:-unknown}\`"
    report_append "* Exit code: \`${IMAGE_CHECKER_EXIT_CODE:-unknown}\`"
    report_append "* Summary source: \`${IMAGE_CHECKER_SUMMARY_SOURCE:-unknown}\`"
    report_append ""
    # The SLURM stdout/stderr files ARE the full output already; embedding
    # an excerpt here just duplicates them (and produces an empty code
    # block when the job failed before pytest wrote a "Captured stdout
    # call" section), so just point at them directly.
    if [[ -n "${IMAGE_CHECKER_STDOUT:-}" && -f "${IMAGE_CHECKER_STDOUT:-}" ]]; then
        report_append "* Full output: \`${IMAGE_CHECKER_STDOUT}\`"
    else
        report_append "* Full output: _not found (expected at \`${IMAGE_CHECKER_STDOUT:-unknown}\`)_"
    fi
    if [[ -n "${IMAGE_CHECKER_STDERR:-}" && -f "${IMAGE_CHECKER_STDERR:-}" && -s "${IMAGE_CHECKER_STDERR:-}" ]]; then
        report_append "* Errors: \`${IMAGE_CHECKER_STDERR}\`"
    fi
    report_append ""

    local summary_file="${SCRIPT_RUN_DIR}/test_images_summary_${TAG}.md"
    report_append "### Complete summary table"
    report_append ""
    if [[ -f "$summary_file" ]]; then
        cat "$summary_file" >> "$REPORT_FILE"
    else
        echo "_test_images_summary.md not found._" >> "$REPORT_FILE"
    fi
    report_append ""

    report_append "### Summary table -- only failing image-check tests, sorted by task"
    report_append ""
    if [[ -f "$summary_file" ]]; then
        python -m tests.integration.image_summary_report \
            "$summary_file" "${TASKS_ARRAY[@]}" >> "$REPORT_FILE"
    else
        echo "_test_images_summary.md not found; skipping._" >> "$REPORT_FILE"
    fi
    report_append ""

    report_append "## Results analysis"
    report_append ""
    report_append "_TODO: fill in analysis of any failures above (expected vs. unexpected, whether expected results should be updated, etc.)._"
    report_append ""
}

# Helper for generate_markdown_report: append one repo's commit log since
# its own expected-results production date as a Markdown table row.
#
# Two branches matter here and they are frequently NOT the same branch:
#   - tested_branch: what this run actually checked out (e.g. a feature
#     branch rebased onto main).
#   - results_branch: the branch the *expected* (baseline) results were
#     actually generated from (usually a project's long-lived default
#     branch, e.g. "main"). This is what "changes since expected results
#     were updated" needs to be measured against -- looking at
#     tested_branch's own history would conflate "upstream drift on the
#     baseline branch" with "commits unique to the branch under test",
#     and always hardcoding the default branch would be wrong for setups
#     that intentionally maintain expected results off a different branch.
#
# since_date is likewise per-dependency (see _detect_expected_results_date
# above): different dependencies' expected results can have been produced
# on different dates, so there is no single script-wide date to use here.
_report_repo_changes() {
    local label="$1"
    local repo_dir="$2"
    local tested_branch="$3"
    local results_branch="$4"
    local since_date="$5"
    local repo_url="$6"
    local date_var_name="$7"

    local tested_branch_col="\`${tested_branch}\`"
    if [[ "$tested_branch" == "$results_branch" ]]; then
        tested_branch_col="\`${tested_branch}\` (same as baseline)"
    fi

    if [[ -z "$since_date" ]]; then
        report_append "| [${label}](${repo_url}/commits/${results_branch}) | ${tested_branch_col} | _unknown_ | _could not determine when this dependency was last tested; set \`${date_var_name}\` in the config_ |"
        return
    fi

    local since_col="\`${since_date}\`"

    if [[ ! -d "$repo_dir" ]]; then
        report_append "| [${label}](${repo_url}/commits/${results_branch}) | ${tested_branch_col} | ${since_col} | _repo not found at ${repo_dir}_ |"
        return
    fi

    local remote
    if ! remote=$(get_preferred_git_remote "$repo_dir"); then
        report_append "| [${label}](${repo_url}/commits/${results_branch}) | ${tested_branch_col} | ${since_col} | _unable to identify a git remote for ${repo_dir}_ |"
        return
    fi

    local log_ref=""
    if ! env GIT_TERMINAL_PROMPT=0 \
        GIT_SSH_COMMAND="ssh -oBatchMode=yes" \
        git -C "$repo_dir" fetch "$remote" "$results_branch" >/dev/null 2>&1; then
        report_append "| [${label}](${repo_url}/commits/${results_branch}) | ${tested_branch_col} | ${since_col} | _unable to fetch ${remote}/${results_branch}_ |"
        return
    elif ! log_ref=$(git -C "$repo_dir" rev-parse FETCH_HEAD 2>/dev/null); then
        report_append "| [${label}](${repo_url}/commits/${results_branch}) | ${tested_branch_col} | ${since_col} | _unable to resolve fetched ${remote}/${results_branch}_ |"
        return
    fi

    local commits
    if ! commits=$(git -C "$repo_dir" log "$log_ref" --since="${since_date}" --oneline 2>/dev/null); then
        report_append "| [${label}](${repo_url}/commits/${results_branch}) | ${tested_branch_col} | ${since_col} | _unable to inspect ${log_ref}_ |"
        return
    fi

    if [[ -z "$commits" ]]; then
        report_append "| [${label}](${repo_url}/commits/${results_branch}) | ${tested_branch_col} | ${since_col} | None |"
        return
    fi

    local links=""
    local hash msg pr
    while IFS= read -r line; do
        hash="${line%% *}"
        msg="${line#* }"
        # Extract a trailing "(#1234)" PR reference if present.
        if [[ "$msg" =~ \(#([0-9]+)\)$ ]]; then
            pr="${BASH_REMATCH[1]}"
            links+="[#${pr}](${repo_url}/pull/${pr}), "
        else
            links+="[${hash}](${repo_url}/commit/${hash}), "
        fi
    done <<< "$commits"
    links="${links%, }"

    report_append "| [${label}](${repo_url}/commits/${results_branch}) | ${tested_branch_col} | ${since_col} | ${links} |"
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
    log_success "Markdown report: ${REPORT_FILE}"
}

main
