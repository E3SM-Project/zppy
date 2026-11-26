#!/bin/bash

# Running on chrysalis

#SBATCH  --job-name=global_time_series_classic_original_8_no_ocn_1985-1988
#SBATCH  --account=e3sm
#SBATCH  --nodes=1
#SBATCH  --output=/zppy_snapshot/output/post/scripts/global_time_series_classic_original_8_no_ocn_1985-1988.o%j
#SBATCH  --exclusive
#SBATCH  --time=00:30:00


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
echo "RUNNING ${id}" > global_time_series_classic_original_8_no_ocn_1985-1988.status

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
echo "${pkg_manager} list zppy-interfaces:"
${pkg_manager} list zppy-interfaces || true # If we can't print this, just continue on.

# Generate global time series plots
################################################################################

results_dir=global_time_series_classic_original_8_no_ocn_1985-1988_results
zi-global-time-series --use_ocn False --input /zppy_snapshot/input/v3.LR.historical_0051 --input_subdir archive/ocn/hist --moc_file None --case_dir /zppy_snapshot/output --experiment_name v3.LR.historical_0051 --figstr v3.LR.historical_0051 --color Blue --ts_num_years 2 --plots_original net_toa_flux_restom,global_surface_air_temperature,toa_radiation,net_atm_energy_imbalance,net_atm_water_imbalance --plots_atm None --plots_ice None --plots_lnd None --plots_ocn None --nrows 4 --ncols 2 --results_dir ${results_dir} --regions glb,n,s --make_viewer False --start_yr 1985 --end_yr 1988
if [ $? != 0 ]; then
    cd /zppy_snapshot/output/post/scripts
    echo 'ERROR (1)' > global_time_series_classic_original_8_no_ocn_1985-1988.status
    exit 1
fi


results_dir_absolute_path=/zppy_snapshot/output/post/scripts/${results_dir}
# We are already in scriptDir so we don't have to copy files over to results_dir_absolute_path

################################################################################
case=v3.LR.historical_0051
www=/zppy_snapshot/www
case_dir=/zppy_snapshot/output

# Copy ocean results to case directory
echo
echo ===== COPY OCEAN RESULTS TO CASE DIRECTORY =====
echo

if [ -d "${results_dir_absolute_path}/ocn" ]; then
    mkdir -p ${case_dir}/post/ocn
    rsync -av ${results_dir_absolute_path}/ocn/ ${case_dir}/post/ocn/
    if [ $? != 0 ]; then
        cd /zppy_snapshot/output/post/scripts
        echo 'ERROR (2)' > global_time_series_classic_original_8_no_ocn_1985-1988.status
        exit 2
    fi
    echo "Ocean results copied to ${case_dir}/post/ocn/"
else
    echo "No ocean results directory found at ${results_dir_absolute_path}/ocn"
fi

# Copy output to web server
echo
echo ===== COPY FILES TO WEB SERVER =====
echo

# Create top-level directory
top_level=${www}/${case}/global_time_series/
results_level=${top_level}/${results_dir}
mkdir -p ${results_level}
if [ $? != 0 ]; then
  cd /zppy_snapshot/output/post/scripts
  echo 'ERROR (3)' > global_time_series_classic_original_8_no_ocn_1985-1988.status
  exit 3
fi



# Copy files (excluding ocn directory)
rsync -a --delete --exclude='ocn' ${results_dir_absolute_path} ${top_level}
if [ $? != 0 ]; then
  cd /zppy_snapshot/output/post/scripts
  echo 'ERROR (4)' > global_time_series_classic_original_8_no_ocn_1985-1988.status
  exit 4
fi




# For LCRC, change permissions of new files
pushd ${top_level}
chmod -R go+rX,go-w ${results_dir}
popd


# Clean up temporary results directory
echo
echo ===== CLEANUP TEMPORARY RESULTS DIRECTORY =====
echo
rm -rf ${results_dir_absolute_path}
if [ $? = 0 ]; then
    echo "Successfully cleaned up ${results_dir_absolute_path}"
else
    echo "Warning: Failed to clean up ${results_dir_absolute_path}"
fi

################################################################################
# Update status file and exit

ENDTIME=$(date +%s)
ELAPSEDTIME=$(($ENDTIME - $STARTTIME))

echo ==============================================
echo "Elapsed time: $ELAPSEDTIME seconds"
echo ==============================================
cd /zppy_snapshot/output/post/scripts
rm -f global_time_series_classic_original_8_no_ocn_1985-1988.status
echo 'OK' > global_time_series_classic_original_8_no_ocn_1985-1988.status
exit 0