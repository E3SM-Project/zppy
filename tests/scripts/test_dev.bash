#!/bin/bash

# Before running this script ########################################################

# Set up branch
# If you want to test `main`, do the following:
# git fetch upstream main
# git checkout -b test_main_<date> upstream/main
# git log # check the commits match https://github.com/E3SM-Project/zppy/commits/main

# Set these parameters:

# Make sure you do not have important changes in any of these directories. This script will reset them!
ZPPY_DIR=/home/ac.forsyth2/zppy/
DIAGS_DIR=/home/ac.forsyth2/e3sm_diags/
ZI_DIR=/home/ac.forsyth2/zppy-interfaces/

ZPPY_DEV=zppy_dev_n516
DIAGS_DEV=diags_dev_2024_12_13
ZI_DEV=zi_dev_2024_12_13

DIAGS_ENV_CMD="source /home/ac.forsyth2/miniconda3/etc/profile.d/conda.sh; conda activate ${DIAGS_DEV}"
ZI_ENV_CMD="source /home/ac.forsyth2/miniconda3/etc/profile.d/conda.sh; conda activate ${ZI_DEV}"

UNIQUE_ID="unique_id"

#####################################################################################

# Set up zppy-interfaces env
cd ${ZI_DIR}
git fetch upstream main
git checkout main upstream/main
if [ $? != 0 ]; then
  echo 'ERROR (1): Could not check out zppy-interfaces main branch'
  exit 1
fi
git reset --hard upstream/main
conda clean --all --y
# TODO: previous iterations of this script had issues with activating conda environments
conda env create -f conda/dev.yml -n ${ZI_DEV}
conda activate ${ZI_DEV}
pip install .
pytest tests/global_time_series/test_*.py
if [ $? != 0 ]; then
  echo 'ERROR (2): zppy-interfaces unit tests failed'
  exit 2
fi

# Set up e3sm_diags env
cd ${DIAGS_DIR}
git fetch upstream
git checkout main
if [ $? != 0 ]; then
  echo 'ERROR (3): Could not check out e3sm_diags main branch'
  exit 3
fi
git reset --hard upstream/main
conda clean --all --y
conda env create -f conda-env/dev.yml -n ${DIAGS_DEV}
conda activate ${DIAGS_DEV}
pip install .

# Set up zppy env
cd ${ZPPY_DIR}
# We should already be on the branch we want to test!
conda clean --all --y
conda env create -f conda/dev.yml -n ${ZPPY_DEV}
conda activate ${ZPPY_DEV}
pip install .
pytest tests/test_*.py
if [ $? != 0 ]; then
  echo 'ERROR (4): zppy unit tests failed'
  exit 4
fi

# Integration testing for zppy
python tests/integration/utils.py False ${DIAGS_DEV} ${ZI_DEV}


zppy -c tests/integration/generated/test_weekly_comprehensive_v3_chrysalis.cfg
zppy -c tests/integration/generated/test_weekly_comprehensive_v2_chrysalis.cfg
zppy -c tests/integration/generated/test_weekly_bundles_chrysalis.cfg # Runs 1st part of bundles cfg

# TODO: figure out how to wait for all those jobs to finish

zppy -c tests/integration/generated/test_weekly_bundles_chrysalis.cfg

# TODO: figure out how to wait for all those jobs to finish

# Check output
cd /lcrc/group/e3sm/${USER}/zppy_weekly_comprehensive_v3_output/${UNIQUE_ID}/v3.LR.historical_0051/post/scripts/
grep -v "OK" *status
if [ $? == 0 ]; then
  echo 'ERROR (5): weekly_comprehensive_v3 failed'
  exit 5
fi

cd /lcrc/group/e3sm/${USER}/zppy_weekly_comprehensive_v2_output/${UNIQUE_ID}/v2.LR.historical_0201/post/scripts
grep -v "OK" *status
if [ $? == 0 ]; then
  echo 'ERROR (6): weekly_comprehensive_v2 failed'
  exit 6
fi

cd /lcrc/group/e3sm/${USER}/zppy_weekly_bundles_output/${UNIQUE_ID}/v3.LR.historical_0051/post/scripts
grep -v "OK" *status
if [ $? == 0 ]; then
  echo 'ERROR (7): weekly_bundles failed'
  exit 7
fi

# Run integration tests
cd ~/ez/zppy
pytest tests/integration/test_*.py
if [ $? != 0 ]; then
  echo 'ERROR (8): zppy integration tests failed'
  exit 8
fi
