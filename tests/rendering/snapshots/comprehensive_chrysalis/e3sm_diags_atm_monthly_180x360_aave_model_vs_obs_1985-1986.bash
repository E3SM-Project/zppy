#!/bin/bash

# Running on chrysalis

#SBATCH  --job-name=e3sm_diags_atm_monthly_180x360_aave_model_vs_obs_1985-1986
#SBATCH  --account=e3sm
#SBATCH  --nodes=1
#SBATCH  --output=/zppy_snapshot/output/post/scripts/e3sm_diags_atm_monthly_180x360_aave_model_vs_obs_1985-1986.o%j
#SBATCH  --exclusive
#SBATCH  --time=02:00:00


#SBATCH  --partition=compute









# Turn on debug output if needed
debug=False
if [[ "${debug,,}" == "true" ]]; then
  set -x
fi

# Script dir
cd /zppy_snapshot/output/post/scripts

# Get jobid
id=${SLURM_JOBID}

# Update status file
STARTTIME=$(date +%s)
echo "RUNNING ${id}" > e3sm_diags_atm_monthly_180x360_aave_model_vs_obs_1985-1986.status

set_pkg_manager() {
  # Detect whether to use pixi or conda based on environment_commands
  # Example environment commands:

  # These would indicate pixi is the package manager:
  # source /share/apps/E3SM/conda_envs/test_e3sm_unified_1.13.0rc7_compy.sh
  # source /share/apps/E3SM/conda_envs/load_latest_e3sm_unified_compy.sh

  # This would indicate conda is the package manager:
  # source /qfs/people/fors729/miniforge3/etc/profile.d/conda.sh; conda activate e3sm_to_cmip_20260415

  # Important: we need the quotes since environment_commands might
  # include multiple commands, separated by semi-colon.
  if echo "source /lcrc/soft/climate/e3sm-unified/load_latest_e3sm_unified_chrysalis.sh" | grep -Eq 'test_e3sm_unified|load_latest_e3sm_unified'; then
    pkg_manager="pixi"
  else
    pkg_manager="conda"
  fi

  # We always want to know what the python version is.
  echo "${pkg_manager} list python:"
  ${pkg_manager} list python || true # If we can't print this, just continue on.
}

run_nco() {
  # Example:
  # environment_path=/global/cfs/cdirs/e3sm/zender/bin_perlmutter/ (set with jinja2 substitution from config file)
  # nco_cmd=ncclimo (passed in directly)
  # Runs `/global/cfs/cdirs/e3sm/zender/bin_perlmutter/ncclimo --npo` on the original arguments

  # Full list of NCO commands: https://nco.sourceforge.net/nco.html#Reference-Manual

  local environment_path=""
  local nco_cmd=$1
  shift # Remove nco_cmd from the argument list

  if [[ -n "$environment_path" && ( "$nco_cmd" == "ncclimo" || "$nco_cmd" == "ncremap" ) ]]; then
    # nco_path is non-empty AND nco_cmd is a script (either ncclimo or ncremap),
    # so use the full development setup:
    "${environment_path%/}/$nco_cmd" --npo "$@"
  else
    # nco_path is empty OR nco_cmd is a binary executable (not a script),
    # so use just the nco_cmd itself:
    "$nco_cmd" "$@"
  fi
}
set -e
source /lcrc/soft/climate/e3sm-unified/load_latest_e3sm_unified_chrysalis.sh
set +e

set_pkg_manager
echo "${pkg_manager} list e3sm_diags:"
${pkg_manager} list e3sm_diags || true # If we can't print this, just continue on.

# Make sure UVCDAT doesn't prompt us about anonymous logging
export UVCDAT_ANONYMOUS_LOG=False

# Basic definitions
case="v3.LR.historical_0051"
short="v3.LR.historical_0051"
www="/zppy_snapshot/www"
y1=1985
y2=1986
Y1="1985"
Y2="1986"

run_type="model_vs_obs"
tag="model_vs_obs"

results_dir=${tag}_${Y1}-${Y2}

# Create temporary workdir
hash=`mktemp --dry-run -d XXXX`
workdir=tmp.e3sm_diags_atm_monthly_180x360_aave_model_vs_obs_1985-1986.${id}.${hash}
mkdir ${workdir}
cd ${workdir}

create_links_climo()
{
  climo_dir_source=$1
  climo_dir_destination=$2
  nc_prefix=$3
  begin_year=$4
  end_year=$5
  error_num=$6
  mkdir -p ${climo_dir_destination}
  cd ${climo_dir_destination}
  # Glob covers both EAM monthly (${case}_VAR_*) and EAMxx monthly (${case}.{stream}_VAR_*).
  cp -s ${climo_dir_source}/${nc_prefix}*_${begin_year}??_${end_year}??_climo.nc .
  if [ $? != 0 ]; then
    cd /zppy_snapshot/output/post/scripts
    echo "ERROR (${error_num})" > e3sm_diags_atm_monthly_180x360_aave_model_vs_obs_1985-1986.status
    exit ${error_num}
  fi
  cd ..
}

create_links_climo_diurnal()
{
  climo_diurnal_dir_source=$1
  climo_diurnal_dir_destination=$2
  nc_prefix=$3
  begin_year=$4
  end_year=$5
  error_num=$6
  mkdir -p ${climo_diurnal_dir_destination}
  cd ${climo_diurnal_dir_destination}
  cp -s ${climo_diurnal_dir_source}/${nc_prefix}.*_*_${begin_year}??_${end_year}??_climo.nc .
  if [ $? != 0 ]; then
    cd /zppy_snapshot/output/post/scripts
    echo "ERROR (${error_num})" > e3sm_diags_atm_monthly_180x360_aave_model_vs_obs_1985-1986.status
    exit ${error_num}
  fi
  cd ..
}

climo_dir_primary=climo

# Create local links to input climo files
climo_dir_source=/zppy_snapshot/output/post/atm/180x360_aave/clim/2yr
create_links_climo ${climo_dir_source} ${climo_dir_primary} ${case} ${Y1} ${Y2} 3


climo_diurnal_dir_primary=climo_diurnal_8xdaily

# Create local links to input diurnal cycle climo files
climo_diurnal_dir_source=/zppy_snapshot/output/post/atm/180x360_aave/clim_diurnal_8xdaily/2yr
create_links_climo_diurnal ${climo_diurnal_dir_source} ${climo_diurnal_dir_primary} ${case} ${Y1} ${Y2} 5

# Create xml files for time series variables
ts_dir_primary=/zppy_snapshot/output/post/atm/180x360_aave/ts/monthly/2yr

ts_daily_dir=/zppy_snapshot/output/post/atm/180x360_aave/ts/daily/2yr

ts_rof_dir_primary="/zppy_snapshot/output/post/rof/native/ts/monthly/2yr"





# Run E3SM Diags
echo
echo ===== RUN E3SM DIAGS =====
echo

# Prepare configuration file
cat > e3sm.py << EOF
import os
import numpy
from e3sm_diags.parameter.area_mean_time_series_parameter import AreaMeanTimeSeriesParameter
from e3sm_diags.parameter.core_parameter import CoreParameter
from e3sm_diags.parameter.diurnal_cycle_parameter import DiurnalCycleParameter
from e3sm_diags.parameter.enso_diags_parameter import EnsoDiagsParameter
from e3sm_diags.parameter.qbo_parameter import QboParameter
from e3sm_diags.parameter.streamflow_parameter import StreamflowParameter
from e3sm_diags.parameter.mp_partition_parameter import MPpartitionParameter
from e3sm_diags.parameter.precip_pdf_parameter import PrecipPDFParameter
from e3sm_diags.parameter.tc_analysis_parameter import TCAnalysisParameter
from e3sm_diags.parameter.tropical_subseasonal_parameter import TropicalSubseasonalParameter


from e3sm_diags.run import runner

short_name = '${short}'
test_ts = '${ts_dir_primary}'
start_yr = int('${Y1}')
end_yr = int('${Y2}')
num_years = end_yr - start_yr + 1
ref_start_yr = 1985

param = CoreParameter()

# Model
param.test_data_path = '${climo_dir_primary}'
param.test_name = '${case}'
param.short_test_name = short_name

# Ref

# Obs
param.reference_data_path = '/lcrc/group/e3sm/diagnostics/observations/Atm/climatology/'


# Output dir
param.results_dir = '${results_dir}'

# Additional settings
param.run_type = 'model_vs_obs'
param.diff_title = 'Model - Observations'
param.output_format = ['png']
param.output_format_subplot = []
param.multiprocessing = True
param.num_workers = 8
#param.fail_on_incomplete = True
params = [param]

# Model land
enso_param = EnsoDiagsParameter()
enso_param.test_data_path = test_ts
enso_param.test_name = short_name
enso_param.test_start_yr = start_yr
enso_param.test_end_yr = end_yr

# Obs
enso_param.reference_data_path = '/lcrc/group/e3sm/diagnostics/observations/Atm/time-series/'
enso_param.ref_start_yr = ref_start_yr
enso_param.ref_end_yr = ref_start_yr + 10

params.append(enso_param)
trop_param = TropicalSubseasonalParameter()
trop_param.test_data_path = '${ts_daily_dir}'
trop_param.test_name = short_name
trop_param.test_start_yr = start_yr
trop_param.test_end_yr = end_yr

# Obs
trop_param.reference_data_path = '/lcrc/group/e3sm/diagnostics/observations/Atm/time-series/'
trop_param.ref_start_yr = 2001
trop_param.ref_end_yr = 2010

params.append(trop_param)
qbo_param = QboParameter()
qbo_param.test_data_path = test_ts
qbo_param.test_name = short_name
qbo_param.test_start_yr = start_yr
qbo_param.test_end_yr = end_yr
qbo_param.ref_start_yr = ref_start_yr
ref_end_yr = ref_start_yr + num_years - 1
if (ref_end_yr <= 1986):
  qbo_param.ref_end_yr = ref_end_yr
else:
  qbo_param.ref_end_yr = 1986

# Obs
qbo_param.reference_data_path = '/lcrc/group/e3sm/diagnostics/observations/Atm/time-series/'

params.append(qbo_param)
ts_param = AreaMeanTimeSeriesParameter()
ts_param.test_data_path = test_ts
ts_param.test_name = short_name
ts_param.start_yr = start_yr
ts_param.end_yr = end_yr

# Obs
ts_param.reference_data_path = '/lcrc/group/e3sm/diagnostics/observations/Atm/time-series/'

params.append(ts_param)
mp_param = MPpartitionParameter()
mp_param.test_data_path = test_ts
mp_param.test_name = short_name
mp_param.short_test_name = short_name
mp_param.test_start_yr = start_yr
mp_param.test_end_yr = end_yr

params.append(mp_param)
precip_pdf_param = PrecipPDFParameter()
precip_pdf_param.test_data_path = '${ts_daily_dir}'
precip_pdf_param.test_name = short_name
precip_pdf_param.short_test_name = short_name
precip_pdf_param.test_start_yr = start_yr
precip_pdf_param.test_end_yr = end_yr

# Obs
precip_pdf_param.reference_data_path = '/lcrc/group/e3sm/diagnostics/observations/Atm/time-series/'
precip_pdf_param.ref_start_yr = 2001
precip_pdf_param.ref_end_yr = 2010

params.append(precip_pdf_param)
dc_param = DiurnalCycleParameter()
dc_param.test_data_path = '${climo_diurnal_dir_primary}'
dc_param.short_test_name = short_name
# Plotting diurnal cycle amplitude on different scales. Default is True
dc_param.normalize_test_amp = False

# Obs
dc_param.reference_data_path = '/lcrc/group/e3sm/diagnostics/observations/Atm/climatology/'

params.append(dc_param)
streamflow_param = StreamflowParameter()
streamflow_param.test_data_path = '${ts_rof_dir_primary}'
streamflow_param.test_name = short_name
streamflow_param.test_start_yr = start_yr
streamflow_param.test_end_yr = end_yr

# Obs
streamflow_param.reference_data_path = '/lcrc/group/e3sm/diagnostics/observations/Atm/time-series/'
streamflow_param.ref_start_yr = "1986" # Streamflow gauge station data range from year 1986 to 1995
streamflow_param.ref_end_yr = "1995"

params.append(streamflow_param)
tc_param = TCAnalysisParameter()
tc_param.test_data_path = "/zppy_snapshot/output/post/atm/tc-analysis_${Y1}_${Y2}"
tc_param.short_test_name = short_name
tc_param.test_start_yr = "${Y1}"
tc_param.test_end_yr = "${Y2}"

# Obs
tc_param.reference_data_path = '/lcrc/group/e3sm/diagnostics/observations/Atm/tc-analysis/'
# For model vs obs, the ref start and end year can be any four digit strings
# For now, use all available years from obs by default
tc_param.ref_start_yr = "1979"
tc_param.ref_end_yr = "2018"

params.append(tc_param)

# Run
runner.sets_to_run = ['lat_lon', 'zonal_mean_xy', 'zonal_mean_2d', 'polar', 'cosp_histogram', 'meridional_mean_2d', 'annual_cycle_zonal_mean', 'zonal_mean_2d_stratosphere', 'enso_diags', 'qbo', 'area_mean_time_series', 'diurnal_cycle', 'streamflow', 'mp_partition', 'tropical_subseasonal', 'precip_pdf', 'tc_analysis', 'aerosol_aeronet']
runner.run_diags(params)

EOF

# Handle cases when cfg file is explicitly provided


command="srun -n 1 python -u e3sm.py"




# Run diagnostics
time ${command}
if [ $? != 0 ]; then
  cd /zppy_snapshot/output/post/scripts
  echo 'ERROR (7)' > e3sm_diags_atm_monthly_180x360_aave_model_vs_obs_1985-1986.status
  exit 7
fi

# Copy output to web server
echo
echo ===== COPY FILES TO WEB SERVER =====
echo

# Create top-level directory
web_dir=${www}/v3.LR.historical_0051/e3sm_diags/atm_monthly_180x360_aave
mkdir -p ${web_dir}
if [ $? != 0 ]; then
  cd /zppy_snapshot/output/post/scripts
  echo 'ERROR (8)' > e3sm_diags_atm_monthly_180x360_aave_model_vs_obs_1985-1986.status
  exit 8
fi



# Copy files
rsync -a --delete ${results_dir} ${web_dir}/
if [ $? != 0 ]; then
  cd /zppy_snapshot/output/post/scripts
  echo 'ERROR (9)' > e3sm_diags_atm_monthly_180x360_aave_model_vs_obs_1985-1986.status
  exit 9
fi




# For LCRC, change permissions of new files
pushd ${web_dir}/
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
rm -f e3sm_diags_atm_monthly_180x360_aave_model_vs_obs_1985-1986.status
echo 'OK' > e3sm_diags_atm_monthly_180x360_aave_model_vs_obs_1985-1986.status
exit 0