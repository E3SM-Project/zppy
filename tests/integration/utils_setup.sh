# Run this script to set up the zppy integration test environments.
# Run from the top level of the zppy repo

set -e # Fail immediately if a command exits with a non-zero status

# Define these for yourself
unique_id=unique_id
use_custom_e3sm_diags=false
use_custom_zi=false
use_custom_zppy=false
unified_env_cmds="source /lcrc/soft/climate/e3sm-unified/load_latest_e3sm_unified_chrysalis.sh" # Set to the command to load the latest unified environment.
conda_source_file="/gpfs/fs1/home/ac.forsyth2/miniforge3/etc/profile.d/conda.sh" # Set to the path of your conda source file


# Don't need to change anything below this line

conda clean --all --y # Clean up conda envs; also confirms conda is installed
workdir=~/zppy_test_setup_${unique_id}
rm -rf ${workdir} # Remove any old test setup
mkdir ${workdir}
cd ${workdir}

if [ "$use_custom_e3sm_diags" = "true" ]; then
    git clone git@github.com:E3SM-Project/e3sm_diags.git
    cd e3sm_diags
    e3sm_diags_env=e3sm_diags_dev_${unique_id}
    conda env create -f conda-env/dev.yml -n ${e3sm_diags_env}
    conda activate ${e3sm_diags_env} && pip install .
    cd ..
    e3sm_diags_env_cmds="source ${conda_source_file}; conda activate ${e3sm_diags_env}"

else
    e3sm_diags_env_cmds="None"
fi

if [ "$use_custom_zi" = "true" ]; then
    git clone git@github.com:E3SM-Project/zppy-interfaces.git
    cd zppy-interfaces
    zi_env=zi_dev_${unique_id}
    conda env create -f conda/dev.yml -n ${zi_env}
    conda activate ${zi_env} && pip install .
    pytest tests/unit/global_time_series/test_*.py
    cd ..
    zi_env_cmds="source ${conda_source_file}; conda activate ${zi_env}"
else
    zi_env_cmds="None"
fi

git clone git@github.com:E3SM-Project/zppy.git
cd zppy
if [ "$use_custom_zppy" = "true" ]; then
    zppy_env=zppy_dev_${unique_id}
    conda env create -f conda/dev.yml -n ${zppy_env}
    conda activate ${zppy_env} && pip install .
    pytest tests/test_*.py
    zppy_env_cmds="source ${conda_source_file}; conda activate ${zppy_env}"
else
    zppy_env_cmds="${unified_env_cmds}"
fi
python tests/integration/utils.py ${unique_id} ${e3sm_diags_env_cmds} ${zi_env_cmds} ${unified_env_cmds}
echo 'Generated diffs:'
git diff tests/integration/generated/test_weekly_comprehensive_v3_chrysalis.cfg
git diff tests/integration/generated/test_weekly_comprehensive_v2_chrysalis.cfg
git diff tests/integration/generated/test_weekly_bundles_chrysalis.cfg
echo "Run these commands from ${workdir}/zppy to create output for the integration tests:"
echo 'zppy -c tests/integration/generated/test_weekly_comprehensive_v3_chrysalis.cfg'
echo 'zppy -c tests/integration/generated/test_weekly_comprehensive_v2_chrysalis.cfg'
echo 'zppy -c tests/integration/generated/test_weekly_bundles_chrysalis.cfg # Runs 1st part of bundles cfg'
echo 'zppy -c tests/integration/generated/test_weekly_bundles_chrysalis.cfg # Runs 2nd part of bundles cfg'
