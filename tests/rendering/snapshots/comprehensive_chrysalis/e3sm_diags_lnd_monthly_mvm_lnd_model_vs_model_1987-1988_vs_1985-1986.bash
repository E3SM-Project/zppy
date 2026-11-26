#!/bin/bash

# Running on chrysalis

#SBATCH  --job-name=e3sm_diags_lnd_monthly_mvm_lnd_model_vs_model_1987-1988_vs_1985-1986
#SBATCH  --account=e3sm
#SBATCH  --nodes=1
#SBATCH  --output=/zppy_snapshot/output/post/scripts/e3sm_diags_lnd_monthly_mvm_lnd_model_vs_model_1987-1988_vs_1985-1986.o%j
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
echo "RUNNING ${id}" > e3sm_diags_lnd_monthly_mvm_lnd_model_vs_model_1987-1988_vs_1985-1986.status

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
y1=1987
y2=1988
Y1="1987"
Y2="1988"

ref_Y1="1985"
ref_Y2="1986"
run_type="model_vs_model"
tag="model_vs_model"

results_dir=${tag}_${Y1}-${Y2}

# Create temporary workdir
hash=`mktemp --dry-run -d XXXX`
workdir=tmp.e3sm_diags_lnd_monthly_mvm_lnd_model_vs_model_1987-1988_vs_1985-1986.${id}.${hash}
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
    echo "ERROR (${error_num})" > e3sm_diags_lnd_monthly_mvm_lnd_model_vs_model_1987-1988_vs_1985-1986.status
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
    echo "ERROR (${error_num})" > e3sm_diags_lnd_monthly_mvm_lnd_model_vs_model_1987-1988_vs_1985-1986.status
    exit ${error_num}
  fi
  cd ..
}

climo_dir_primary_land=climo_test_land
# Create local links to input climo files
climo_dir_source=/zppy_snapshot/output/post/lnd/180x360_aave/clim/2yr
create_links_climo ${climo_dir_source} ${climo_dir_primary_land} ${case} ${Y1} ${Y2} 1

# Create local links to input climo files (ref model)
climo_dir_source=/zppy_snapshot/output/post/lnd/180x360_aave/clim/2yr
climo_dir_ref_land=climo_ref_land
create_links_climo ${climo_dir_source} ${climo_dir_ref_land} v3.LR.historical_0051 ${ref_Y1} ${ref_Y2} 2


ref_name=v3.LR.historical_0051


# Run E3SM Diags
echo
echo ===== RUN E3SM DIAGS =====
echo

# Prepare configuration file
cat > e3sm.py << EOF
import os
import numpy
from e3sm_diags.parameter.core_parameter import CoreParameter
from e3sm_diags.parameter.lat_lon_land_parameter import LatLonLandParameter


from e3sm_diags.run import runner

short_name = '${short}'
test_ts = '${ts_dir_primary}'
start_yr = int('${Y1}')
end_yr = int('${Y2}')
num_years = end_yr - start_yr + 1

param = CoreParameter()

# Model
param.test_name = '${case}'
param.short_test_name = short_name

# Ref

# Output dir
param.results_dir = '${results_dir}'

# Additional settings
param.run_type = 'model_vs_model'
param.diff_title = 'Difference'
param.output_format = ['png']
param.output_format_subplot = []
param.multiprocessing = True
param.num_workers = 8
#param.fail_on_incomplete = True
params = [param]

# Model land
land_param = LatLonLandParameter()
land_param.test_data_path = '${climo_dir_primary_land}'

# Reference
land_param.reference_data_path = '${climo_dir_ref_land}'
land_param.ref_name = '${ref_name}'
land_param.short_ref_name = 'same simulation'
# Optionally, swap test and reference model
if True:
   land_param.test_data_path, land_param.reference_data_path = land_param.reference_data_path, land_param.test_data_path
   land_param.test_name, land_param.ref_name = land_param.ref_name, land_param.test_name
   land_param.short_test_name, land_param.short_ref_name = land_param.short_ref_name, land_param.short_test_name
params.append(land_param)

# Run
runner.sets_to_run = ['lat_lon_land']
runner.run_diags(params)

EOF

# Handle cases when cfg file is explicitly provided


command="srun -n 1 python -u e3sm.py"




# Run diagnostics
time ${command}
if [ $? != 0 ]; then
  cd /zppy_snapshot/output/post/scripts
  echo 'ERROR (7)' > e3sm_diags_lnd_monthly_mvm_lnd_model_vs_model_1987-1988_vs_1985-1986.status
  exit 7
fi

# Copy output to web server
echo
echo ===== COPY FILES TO WEB SERVER =====
echo

# Create top-level directory
web_dir=${www}/v3.LR.historical_0051/e3sm_diags/lnd_monthly_mvm_lnd
mkdir -p ${web_dir}
if [ $? != 0 ]; then
  cd /zppy_snapshot/output/post/scripts
  echo 'ERROR (8)' > e3sm_diags_lnd_monthly_mvm_lnd_model_vs_model_1987-1988_vs_1985-1986.status
  exit 8
fi



# Copy files
rsync -a --delete ${results_dir} ${web_dir}/
if [ $? != 0 ]; then
  cd /zppy_snapshot/output/post/scripts
  echo 'ERROR (9)' > e3sm_diags_lnd_monthly_mvm_lnd_model_vs_model_1987-1988_vs_1985-1986.status
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
rm -f e3sm_diags_lnd_monthly_mvm_lnd_model_vs_model_1987-1988_vs_1985-1986.status
echo 'OK' > e3sm_diags_lnd_monthly_mvm_lnd_model_vs_model_1987-1988_vs_1985-1986.status
exit 0