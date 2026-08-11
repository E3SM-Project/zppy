# Run from zppy/tests/main_branch_testing/frozen_env_setup

#!/usr/bin/env bash
set -euo pipefail

# --- Config -----------------------------------------------------------
UNIFIED_SCRIPT=/lcrc/soft/climate/e3sm-unified/load_latest_e3sm_unified_chrysalis.sh
REPO_DIR=/lcrc/group/e3sm/ac.forsyth2/zppy_main_branch_test_dirs
CONDA_PROFILE="$HOME/miniforge3/etc/profile.d/conda.sh"

# name -> path (relative to the repo dir) of that component's dev-env file.
declare -A DEVYML_PATHS=(
  ["e3sm_to_cmip"]="conda-env/dev.yml"
  ["e3sm_diags"]="conda-env/dev.yml"
  ["MPAS-Analysis"]="dev-spec.txt"
  ["zppy-interfaces"]="conda/dev.yml"
  ["zppy"]="conda/dev.yml"
)

# name -> the lowercase/underscore form zppy_test.cfg expects in
# BASE_ENV_LOCK_FILE_<COMPONENT> (frozen-base-<this>.txt). Doesn't always
# match the repo directory name (e.g. zppy-interfaces -> zppy_interfaces,
# MPAS-Analysis -> mpas_analysis).
declare -A CFG_NAMES=(
  ["e3sm_to_cmip"]="e3sm_to_cmip"
  ["e3sm_diags"]="e3sm_diags"
  ["MPAS-Analysis"]="mpas_analysis"
  ["zppy-interfaces"]="zppy_interfaces"
  ["zppy"]="zppy"
)

# Fixed order, since associative-array iteration order isn't guaranteed.
names_ordered=(e3sm_to_cmip e3sm_diags MPAS-Analysis zppy-interfaces zppy)

# --- Step 1: capture Unified's resolved versions (once) ---------------
./get_unified_versions.sh "${UNIFIED_SCRIPT}" "${REPO_DIR}/unified_versions.json"
echo "Done creating unified_versions.json"

# --- Step 2: pin each component's dev-env file, then build its frozen base
source "$CONDA_PROFILE"

for name in "${names_ordered[@]}"; do
    devyml_rel="${DEVYML_PATHS[$name]}"
    ext="${devyml_rel##*.}"   # "yml" for dev.yml, "txt" for dev-spec.txt
    cfg_name="${CFG_NAMES[$name]}"
    pinned_devyml="pinned-dev-${name}.${ext}"

    python pin_dev_env_to_unified.py \
        --unified "${REPO_DIR}/unified_versions.json" \
        --devyml "${REPO_DIR}/${name}/${devyml_rel}" \
        --out-devyml "${pinned_devyml}" \
        --out-report "pin-report-${name}.md" \
        --component "${name}"
    echo "Done pinning dev env for ${name}"

    if [ "$ext" = "yml" ]; then
        conda env create -f "${pinned_devyml}" -n tmp-lock-gen
    else
        conda create --name tmp-lock-gen --file "${pinned_devyml}" --yes
    fi
    conda activate tmp-lock-gen
    conda list --explicit > "${REPO_DIR}/frozen-base-${cfg_name}.txt"
    conda deactivate
    conda remove --yes --all --name tmp-lock-gen

    echo "Done creating frozen env for ${name}"
done
