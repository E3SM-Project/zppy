#!/bin/bash

# Before running this script ########################################################

# Make sure you're on the branch you want to test!

# If you want to test `main`, do the following:
# git fetch upstream main
# git checkout -b test_pre_zppy_rc<#>_<machine_name> upstream/main
# git log # check the commits match https://github.com/E3SM-Project/zppy/commits/main

# Set these parameters
DIAGS_DIR=/home/ac.forsyth2/e3sm_diags/
DIAGS_DEV=diags_dev_2023_10_05
ZPPY_DIR=/home/ac.forsyth2/zppy/
DIAGS_ENV_CMD="source /home/ac.forsyth2/miniconda3/etc/profile.d/conda.sh; conda activate ${DIAGS_DEV}"
ZPPY_DEV=zppy_dev_n516

# Make sure you do not have important changes on the `main` branch in your
# E3SM_DIAGS_DIRECTORY. This script will reset that branch to match `upstream`!

#####################################################################################

echo "Update E3SM Diags"
# `cd` to e3sm_diags directory
cd ${DIAGS_DIR}
git checkout main
git fetch upstream
git reset --hard upstream/main
git log # Should match https://github.com/E3SM-Project/e3sm_diags/commits/main # TODO: Requires user review
mamba clean --all # TODO: Requires user input to advance
conda remove -n ${DIAGS_DEV} --all
mamba env create -f conda-env/dev.yml -n ${DIAGS_DEV}
conda activate ${DIAGS_DEV} # TODO: errors with ./tests/scripts/test_dev.bash: line 34: {DIAGS_DEV}: command not found
pip install .
cd ${ZPPY_DIR}

echo "Make sure we're using the latest packages"
UNIFIED_TESTING=False
python tests/integration/utils.py ${UNIFIED_TESTING} ${DIAGS_ENV_CMD}

echo "Set up our environment"
mamba clean --all # TODO: Requires user input to advance
mamba env create -f conda/dev.yml -n ${ZPPY_DEV}
conda activate ${ZPPY_DEV} # TODO: errors with CommandNotFoundError: Your shell has not been properly configured to use 'conda activate'.
pip install .

echo "Run unit tests"
python -u -m unittest tests/test_*.py
if [ $? != 0 ]; then
  echo 'ERROR (1): unit tests failed'
  exit 1
fi

exit 7

echo "Set up integration tests"
# TODO: somehow use Mache (a Python package) to get machine-independent paths in this bash script!
# test_complete_run
rm -rf /lcrc/group/e3sm/public_html/diagnostic_output/ac.forsyth2/zppy_test_complete_run_www/v2.LR.historical_0201
rm -rf /lcrc/group/e3sm/ac.forsyth2/zppy_test_complete_run_output/v2.LR.historical_0201/post
# Run jobs:
zppy -c tests/integration/generated/test_complete_run_chrysalis.cfg
# TODO: how can we possibly tell, automatically, when this is finished?
# After they finish, check the results:
cd /lcrc/group/e3sm/ac.forsyth2/zppy_test_complete_run_output/v2.LR.historical_0201/post/scripts
grep -v "OK" *status
if [ $? == 0 ]; then
  # The above command succeeds only if there are reported failures.
  echo 'ERROR (2): zppy complete run failed.'
  exit 2
fi
cd ${ZPPY_DIR}
# test_bundles
rm -rf /lcrc/group/e3sm/public_html/diagnostic_output/ac.forsyth2/zppy_test_bundles_www/v2.LR.historical_0201
rm -rf /lcrc/group/e3sm/ac.forsyth2/zppy_test_bundles_output/v2.LR.historical_0201/post
# Run first set of jobs:
zppy -c tests/integration/generated/test_bundles_chrysalis.cfg
# TODO: how can we possibly tell, automatically, when this is finished?
# bundle1 and bundle2 should run. After they finish, check the results:
cd /lcrc/group/e3sm/ac.forsyth2/zppy_test_bundles_output/v2.LR.historical_0201/post/scripts
grep -v "OK" *status
if [ $? == 0 ]; then
  # The above command succeeds only if there are reported failures.
  echo 'ERROR (3): zppy bundles 1st run failed.'
  exit 3
fi
cd ${ZPPY_DIR}
# Now, invoke zppy again to run jobs that needed to wait for dependencies:
zppy -c tests/integration/generated/test_bundles_chrysalis.cfg
# TODO: how can we possibly tell, automatically, when this is finished?
# bundle3 and ilamb should run. After they finish, check the results:
cd /lcrc/group/e3sm/ac.forsyth2/zppy_test_bundles_output/v2.LR.historical_0201/post/scripts
grep -v "OK" *status
if [ $? == 0 ]; then
  # The above command succeeds only if there are reported failures.
  echo 'ERROR (4): zppy bundles 2nd run failed.'
  exit 4
fi
cd ${ZPPY_DIR}

echo "Run the integration tests"
python -u -m unittest tests/integration/test_*.py
if [ $? != 0 ]; then
  echo 'ERROR (5): integration tests failed'
  exit 5
fi

echo "All tests passed!"
