#!/bin/bash

# Running on chrysalis

#SBATCH  --job-name=e3sm_diags_atm_monthly_180x360_aave_mvm_model_vs_model_1985-1986_vs_1985-1986
#SBATCH  --account=e3sm
#SBATCH  --nodes=1
#SBATCH  --output=/zppy_snapshot/output/post/scripts/e3sm_diags_atm_monthly_180x360_aave_mvm_model_vs_model_1985-1986_vs_1985-1986.o%j
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
echo "RUNNING ${id}" > e3sm_diags_atm_monthly_180x360_aave_mvm_model_vs_model_1985-1986_vs_1985-1986.status

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
www="/zppy_snapshot/www"
y1=1985
y2=1986
Y1="1985"
Y2="1986"

ref_Y1="1985"
ref_Y2="1986"
run_type="model_vs_model"
tag="model_vs_model"

results_dir=model_vs_model_1985-1986

# Create temporary workdir
hash=`mktemp --dry-run -d XXXX`
workdir=tmp.e3sm_diags_atm_monthly_180x360_aave_mvm_model_vs_model_1985-1986_vs_1985-1986.${id}.${hash}
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
    echo "ERROR (${error_num})" > e3sm_diags_atm_monthly_180x360_aave_mvm_model_vs_model_1985-1986_vs_1985-1986.status
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
    echo "ERROR (${error_num})" > e3sm_diags_atm_monthly_180x360_aave_mvm_model_vs_model_1985-1986_vs_1985-1986.status
    exit ${error_num}
  fi
  cd ..
}
climo_dir_primary=climo_test
# Create local links to input climo files
climo_dir_source=/zppy_snapshot/output/post/atm/180x360_aave/clim/2yr
create_links_climo ${climo_dir_source} ${climo_dir_primary} ${case} ${Y1} ${Y2} 3

# Create local links to input climo files (ref model)
climo_dir_source=/zppy_snapshot/output/post/atm/180x360_aave/clim/2yr
climo_dir_ref=climo_ref
create_links_climo ${climo_dir_source} ${climo_dir_ref} v3.LR.historical_0051 ${ref_Y1} ${ref_Y2} 4
climo_diurnal_dir_primary=climo_diurnal_8xdaily_test
# Create local links to input diurnal cycle climo files
climo_diurnal_dir_source=/zppy_snapshot/output/post/atm/180x360_aave/clim_diurnal_8xdaily/2yr
create_links_climo_diurnal ${climo_diurnal_dir_source} ${climo_diurnal_dir_primary} ${case} ${Y1} ${Y2} 5

# Create local links to input climo files (ref model)
climo_diurnal_dir_source=/zppy_snapshot/output/post/atm/180x360_aave/clim_diurnal_8xdaily/2yr
climo_diurnal_dir_ref=climo_diurnal_ref
create_links_climo_diurnal ${climo_diurnal_dir_source} ${climo_diurnal_dir_ref} v3.LR.historical_0051 ${ref_Y1} ${ref_Y2} 6

# Run E3SM Diags
echo
echo ===== RUN E3SM DIAGS =====
echo

# Copy the run script that zppy rendered next to this job script
cp /zppy_snapshot/output/post/scripts/e3sm_diags_atm_monthly_180x360_aave_mvm_model_vs_model_1985-1986_vs_1985-1986.py e3sm.py

# Handle cases when cfg file is explicitly provided


command="srun -n 1 python -u e3sm.py"




# Run diagnostics
time ${command}
if [ $? != 0 ]; then
  cd /zppy_snapshot/output/post/scripts
  echo 'ERROR (7)' > e3sm_diags_atm_monthly_180x360_aave_mvm_model_vs_model_1985-1986_vs_1985-1986.status
  exit 7
fi

# Copy output to web server
echo
echo ===== COPY FILES TO WEB SERVER =====
echo

# Create top-level directory
web_dir=${www}/v3.LR.historical_0051/e3sm_diags/atm_monthly_180x360_aave_mvm
mkdir -p ${web_dir}
if [ $? != 0 ]; then
  cd /zppy_snapshot/output/post/scripts
  echo 'ERROR (8)' > e3sm_diags_atm_monthly_180x360_aave_mvm_model_vs_model_1985-1986_vs_1985-1986.status
  exit 8
fi



# Copy files
rsync -a --delete ${results_dir} ${web_dir}/
if [ $? != 0 ]; then
  cd /zppy_snapshot/output/post/scripts
  echo 'ERROR (9)' > e3sm_diags_atm_monthly_180x360_aave_mvm_model_vs_model_1985-1986_vs_1985-1986.status
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
rm -f e3sm_diags_atm_monthly_180x360_aave_mvm_model_vs_model_1985-1986_vs_1985-1986.status
echo 'OK' > e3sm_diags_atm_monthly_180x360_aave_mvm_model_vs_model_1985-1986_vs_1985-1986.status
exit 0