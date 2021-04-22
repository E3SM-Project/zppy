#!/bin/bash


# Running on chrysalis

#SBATCH  --job-name=e3sm_diags_atm_monthly_180x360_aave_model_vs_obs_0001-0020
#SBATCH  --nodes=1
#SBATCH  --output=test_output/post/scripts/e3sm_diags_atm_monthly_180x360_aave_model_vs_obs_0001-0020.o%j
#SBATCH  --exclusive
#SBATCH  --time=02:00:00
#SBATCH  --partition=compute

source /home/ac.forsyth2/miniconda3/etc/profile.d/conda.sh; conda activate e3sm_diags_env_dev

# Turn on debug output if needed
debug=False
if [[ "${debug,,}" == "true" ]]; then
  set -x
fi

# Make sure UVCDAT doesn't prompt us about anonymous logging
export UVCDAT_ANONYMOUS_LOG=False

# Script dir
cd test_output/post/scripts

# Get jobid
id=${SLURM_JOBID}

# Update status file
STARTTIME=$(date +%s)
echo "RUNNING ${id}" > e3sm_diags_atm_monthly_180x360_aave_model_vs_obs_0001-0020.status

# Basic definitions
case="case_name"
short="20210122.v2_test01.piControl.chrysalis"
www="www/path"
y1=1
y2=20
Y1="0001"
Y2="0020"
run_type="model_vs_obs"
tag="model_vs_obs"

results_dir=${tag}_${Y1}-${Y2}

# Create temporary workdir
workdir=`mktemp -d tmp.${id}.XXXX`
cd ${workdir}

# Create local links to input climo files
climoDir=test_output/post/atm/180x360_aave/clim/20yr
mkdir -p climo
cd climo
cp -s ${climoDir}/${case}_*_${Y1}??_${Y2}??_climo.nc .
cd ..
# Create xml files for time series variables
ts_dir=test_output/post/atm/180x360_aave/ts/monthly/10yr
mkdir -p ts_links
cd ts_links
# https://stackoverflow.com/questions/27702452/loop-through-a-comma-separated-shell-variable
variables="FSNTOA,FLUT,FSNT,FLNT,FSNS,FLNS,SHFLX,QFLX,TAUX,TAUY,PRECC,PRECL,PRECSC,PRECSL,TS,TREFHT,CLDTOT,CLDHGH,CLDMED,CLDLOW,U"
for v in ${variables//,/ }
do
  # Go through the time series files for between year1 and year2, using a step size equal to the number of years per time series file
  for (( year=${y1}; year<=${y2}; year+=10 ))
  do
    YYYY=`printf "%04d" ${year}`
    for file in ${ts_dir}/${v}_${YYYY}*.nc
    do
      # Add this time series file to the list of files for cdscan to use
      echo ${file} >> ${v}_files.txt
    done
  done
  # xml file will cover the whole period from year1 to year2
  xml_name=${v}_${Y1}01_${Y2}12.xml
  cdscan -x ${xml_name} -f ${v}_files.txt
  if [ $? != 0 ]; then
      cd ../..
      echo 'ERROR (4)' > e3sm_diags_atm_monthly_180x360_aave_model_vs_obs_0001-0020.status
      exit 1
  fi
done
cd ..

# Run E3SM Diags
echo
echo ===== RUN E3SM DIAGS model_vs_obs =====
echo

# Prepare configuration file
cat > e3sm.py << EOF
import os
import numpy
from acme_diags.parameter.area_mean_time_series_parameter import AreaMeanTimeSeriesParameter
from acme_diags.parameter.core_parameter import CoreParameter
from acme_diags.parameter.enso_diags_parameter import EnsoDiagsParameter
from acme_diags.parameter.qbo_parameter import QboParameter
from acme_diags.run import runner

short_name = '${short}'
test_ts = 'ts_links'
start_yr = int('${Y1}')
end_yr = int('${Y2}')
num_years = end_yr - start_yr + 1
ref_start_yr = 1979

param = CoreParameter()

# Model
param.test_data_path = 'climo'
param.test_name = '${case}'
param.short_test_name = short_name

# Obs
param.reference_data_path = 'ref_data_path'

# Output dir
param.results_dir = '${results_dir}'

# Additional settings
param.run_type = 'model_vs_obs'
param.diff_title = 'Model - Observations'
param.output_format = ['png']
param.output_format_subplot = ['']
param.multiprocessing = True
param.num_workers = 24
#param.fail_on_incomplete = True
params = [param]
enso_param = EnsoDiagsParameter()
enso_param.reference_data_path = 'obs_ts_path'
enso_param.test_data_path = test_ts
enso_param.test_name = short_name
enso_param.test_start_yr = start_yr
enso_param.test_end_yr = end_yr
enso_param.ref_start_yr = ref_start_yr
enso_param.ref_end_yr = ref_start_yr + 10
params.append(enso_param)
qbo_param = QboParameter()
qbo_param.reference_data_path = 'obs_ts_path'
qbo_param.test_data_path = test_ts
qbo_param.test_name = short_name
qbo_param.test_start_yr = start_yr
qbo_param.test_end_yr = end_yr
qbo_param.ref_start_yr = ref_start_yr
ref_end_yr = ref_start_yr + num_years - 1
if (ref_end_yr <= 2016):
  qbo_param.ref_end_yr = ref_end_yr
else:
  qbo_param.ref_end_yr = 2016
params.append(qbo_param)
ts_param = AreaMeanTimeSeriesParameter()
ts_param.reference_data_path = 'obs_ts_path'
ts_param.test_data_path = test_ts
ts_param.test_name = short_name
ts_param.start_yr = start_yr
ts_param.end_yr = end_yr
params.append(ts_param)

# Run
runner.sets_to_run = ['lat_lon', 'zonal_mean_xy', 'zonal_mean_2d', 'polar', 'cosp_histogram', 'meridional_mean_2d', 'enso_diags', 'qbo', 'area_mean_time_series']
runner.run_diags(params)

EOF

# Handle cases when cfg file is explicitly provided

command="python -u e3sm.py"


# Run diagnostics
time ${command}
if [ $? != 0 ]; then
  cd ..
  echo 'ERROR (1)' > e3sm_diags_atm_monthly_180x360_aave_model_vs_obs_0001-0020.status
  exit 1
fi

# Copy output to web server
echo
echo ===== COPY FILES TO WEB SERVER =====
echo

# Create top-level directory
f=${www}/${case}/e3sm_diags/180x360_aave
mkdir -p ${f}
if [ $? != 0 ]; then
  cd ..
  echo 'ERROR (2)' > e3sm_diags_atm_monthly_180x360_aave_model_vs_obs_0001-0020.status
  exit 1
fi



# Copy files
rsync -a --delete ${results_dir} ${www}/${case}/e3sm_diags/180x360_aave/
if [ $? != 0 ]; then
  cd ..
  echo 'ERROR (3)' > e3sm_diags_atm_monthly_180x360_aave_model_vs_obs_0001-0020.status
  exit 1
fi




# For LCRC, change permissions of new files
pushd ${www}/${case}/e3sm_diags/180x360_aave/
chmod -R go+rX,go-w ${results_dir}
popd


# Delete temporary workdir
cd ..
if [[ "${debug,,}" != "true" ]]; then
  rm -rf ${workdir}
fi

# Update status file and exit

ENDTIME=$(date +%s)
ELAPSEDTIME=$(($ENDTIME - $STARTTIME))

echo ==============================================
echo "Elapsed time: $ELAPSEDTIME seconds"
echo ==============================================
echo 'OK' > e3sm_diags_atm_monthly_180x360_aave_model_vs_obs_0001-0020.status
exit 0
