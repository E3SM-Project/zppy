#!/bin/bash
# Scheduled controller for zppy's complete run test.
#
# Invoked from cron on a login node. Its configuration file is maintained
# outside Git, since it names machine accounts and filesystem locations that
# differ per operator.
#
#   complete-run-controller.sh /absolute/path/to/config.env
set -euo pipefail

if [[ $# -ne 1 ]]; then
    printf '%s\n' 'Usage: complete-run-controller.sh /absolute/path/to/config.env' >&2
    exit 2
fi

# shellcheck source=/dev/null
source "$1"
: "${MACHINE:?}"
: "${REPO_ROOT:?}"
: "${CONDA_BASE:?}"
: "${CONTROLLER_ENV:?}"
: "${CONDA_PROFILE:?}"
: "${SLURM_ACCOUNT:?}"

# Standard cron cannot express "every second Monday" across month boundaries,
# so the schedule fires weekly and the controller gates it here.
WEEK_PARITY="${WEEK_PARITY:-any}"
if [[ "$WEEK_PARITY" != "any" ]]; then
    # 10# forces base 10; ISO weeks like "08" are not octal.
    ISO_WEEK=$((10#$(date +%V)))
    if [[ "$WEEK_PARITY" == "even" && $((ISO_WEEK % 2)) -ne 0 ]]; then
        printf '%s\n' 'Skipping odd ISO week.'
        exit 0
    fi
    if [[ "$WEEK_PARITY" == "odd" && $((ISO_WEEK % 2)) -eq 0 ]]; then
        printf '%s\n' 'Skipping even ISO week.'
        exit 0
    fi
fi

# A complete run submits hundreds of jobs and waits for the operator's queue to
# drain. Two overlapping runs would see each other's jobs and each conclude the
# other's failures were its own. The lock is per operator, because the queue
# being drained is per operator; the shared root is group-owned.
LOCK_FILE="${LOCK_FILE:-$HOME/.zppy_complete_run.lock}"
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    printf '%s\n' 'A complete run controller is already active; exiting.'
    exit 0
fi

# Inherited SLURM_* settings would be applied to the jobs this controller
# submits. Clear them before submitting anything.
unset SLURM_MEM_PER_CPU SLURM_OPEN_MODE
for variable in "${!SLURM_@}"; do
    unset "$variable"
done

# cron does not run a login shell, so conda must be initialized explicitly.
# shellcheck source=/dev/null
source "$CONDA_BASE/etc/profile.d/conda.sh"
conda activate "$CONTROLLER_ENV"

cd "$REPO_ROOT/zppy"

# Empty means the machine's default shared root.
SHARED_ROOT_ARGS=()
if [[ -n "${SHARED_ROOT:-}" ]]; then
    SHARED_ROOT_ARGS=(--shared-root "$SHARED_ROOT")
fi

AUTOMATION_EXIT=0
# shellcheck disable=SC2086 # EXTRA_AUTOMATION_ARGS is deliberately word-split.
python -m tests.complete_run.automation \
    --machine "$MACHINE" \
    --account "$SLURM_ACCOUNT" \
    --repo-root "$REPO_ROOT" \
    --conda-profile "$CONDA_PROFILE" \
    "${SHARED_ROOT_ARGS[@]}" \
    ${EXTRA_AUTOMATION_ARGS:-} || AUTOMATION_EXIT=$?

if [[ "$AUTOMATION_EXIT" -ne 0 ]]; then
    printf '%s\n' "Complete run finished with exit code ${AUTOMATION_EXIT}." >&2
    printf '%s\n' "Its report, and its worktrees for review, were retained." >&2
fi

exit "$AUTOMATION_EXIT"
