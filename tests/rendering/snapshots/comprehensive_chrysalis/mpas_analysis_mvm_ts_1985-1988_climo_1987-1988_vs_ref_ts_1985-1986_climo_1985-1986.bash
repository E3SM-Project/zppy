#!/bin/bash

# Running on chrysalis

#SBATCH  --job-name=mpas_analysis_mvm_ts_1985-1988_climo_1987-1988_vs_ref_ts_1985-1986_climo_1985-1986
#SBATCH  --account=e3sm
#SBATCH  --nodes=1
#SBATCH  --output=/zppy_snapshot/output/post/scripts/mpas_analysis_mvm_ts_1985-1988_climo_1987-1988_vs_ref_ts_1985-1986_climo_1985-1986.o%j
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
echo "RUNNING ${id}" > mpas_analysis_mvm_ts_1985-1988_climo_1987-1988_vs_ref_ts_1985-1986_climo_1985-1986.status

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
echo "${pkg_manager} list mpas-analysis:"
${pkg_manager} list mpas-analysis || true # If we can't print this, just continue on.

# Additional settings for MPAS-Analysis
export OMP_NUM_THREADS=1
export HDF5_USE_FILE_LOCKING=FALSE
ulimit -s unlimited 2>/dev/null || true



# Basic definitions
case="v3.LR.historical_0051"
www="/zppy_snapshot/www"

# Job identifier
identifier=ts_1985-1988_climo_1987-1988
output_dir_name="ts_1985-1988_climo_1987-1988_vs_ts_1985-1986_climo_1985-1986"

# Set-up work directory structure
echo
echo ===== SET UP MPAS-ANALYSIS DIRECTORY STRUCTURE =====
echo

workdir="../analysis/mpas_analysis/mvm"
mkdir -p ${workdir}
cd ${workdir}



mkdir -p ${output_dir_name}
mkdir -p cfg


# Restore cached copies of pre-computed files
cached=( "timeseries/moc" "timeseries/OceanBasins" "timeseries/transport" )
cache_dir="/zppy_snapshot/output/post/scripts/../analysis/mpas_analysis/cache"
mkdir -p ${cache_dir}
for subdir in "${cached[@]}"
do
  mkdir -p ${cache_dir}/${subdir} ${output_dir_name}/${subdir}
  rsync -av ${cache_dir}/${subdir}/ ${output_dir_name}/${subdir}/
done
files=( "mpasIndexOcean.nc" "mpasTimeSeriesOcean.nc" "seaIceAreaVolNH.nc" "seaIceAreaVolSH.nc")
for file in "${files[@]}"
do
  cp ${cache_dir}/timeseries/${file} ${output_dir_name}/timeseries/${file}
done


# Run MPAS-Analysis
echo
echo ===== RUN MPAS-ANALYSIS =====
echo

# Copy the config file that zppy rendered next to this job script
cp /zppy_snapshot/output/post/scripts/mpas_analysis_mvm_ts_1985-1988_climo_1987-1988_vs_ref_ts_1985-1986_climo_1985-1986.cfg cfg/mpas_analysis_${identifier}.cfg

# Run diagnostics

purge=""



extra_config=""


# MPAS-Analysis appends to taskProgress.log rather than overwriting it, so
# ERROR lines from a previous (failed) run would make a successful rerun fail
# the check below. Set the old log aside so the check only sees this run.
task_progress_log=${output_dir_name}/logs/taskProgress.log
if [ -f ${task_progress_log} ]; then
  mv ${task_progress_log} ${task_progress_log}.$(date +%Y%m%d_%H%M%S)
fi

mpas_analysis ${purge} --verbose ${extra_config} cfg/mpas_analysis_${identifier}.cfg
if [ $? != 0 ]; then
  echo 'ERROR (1)' > /zppy_snapshot/output/post/scripts/mpas_analysis_mvm_ts_1985-1988_climo_1987-1988_vs_ref_ts_1985-1986_climo_1985-1986.status
  exit 1
fi

# Check master log for obvious errors
size=`wc -c ${task_progress_log} | awk '{print $1}'`
error=`grep ERROR ${task_progress_log} | wc -l`
if [ "${size}" = "" ] || [ "${size}" = "0" ] || [ "${error}" != "0" ];then
  echo 'ERROR (2)' > /zppy_snapshot/output/post/scripts/mpas_analysis_mvm_ts_1985-1988_climo_1987-1988_vs_ref_ts_1985-1986_climo_1985-1986.status
  exit 2
fi


# Cache copies of selected files
echo
echo ===== CACHE OUTPUT FILES =====
echo
for file in "${files[@]}"
do
  cp ${output_dir_name}/timeseries/${file} ${cache_dir}/timeseries/${file}
done
for subdir in "${cached[@]}"
do
  rsync -av ${output_dir_name}/${subdir}/ ${cache_dir}/${subdir}/
done
# Remove one particularly large file which does not need to be cached
rm ${output_dir_name}/timeseries/mpasTimeSeriesSeaIce.nc


# Copy output to web server
echo
echo ===== COPY FILES TO WEB SERVER =====
echo

# Create top-level directory
f=${www}/${case}/mpas_analysis/mvm/${output_dir_name}/
mkdir -p ${f}
if [ $? != 0 ]; then
  echo 'ERROR (3)' > /zppy_snapshot/output/post/scripts/mpas_analysis_mvm_ts_1985-1988_climo_1987-1988_vs_ref_ts_1985-1986_climo_1985-1986.status
  exit 3
fi



# Copy files
rsync -a --delete ${output_dir_name}/html/ ${www}/${case}/mpas_analysis/mvm/${output_dir_name}/
if [ $? != 0 ]; then
  echo 'ERROR (4)' > /zppy_snapshot/output/post/scripts/mpas_analysis_mvm_ts_1985-1988_climo_1987-1988_vs_ref_ts_1985-1986_climo_1985-1986.status
  exit 4
fi




# For LCRC, change permissions of new files
pushd ${www}/${case}/mpas_analysis/mvm/
chmod -R go+rX,go-w ${output_dir_name}
popd


# Update status file and exit

ENDTIME=$(date +%s)
ELAPSEDTIME=$(($ENDTIME - $STARTTIME))

echo ==============================================
echo "Elapsed time: $ELAPSEDTIME seconds"
echo ==============================================
cd /zppy_snapshot/output/post/scripts
rm -f mpas_analysis_mvm_ts_1985-1988_climo_1987-1988_vs_ref_ts_1985-1986_climo_1985-1986.status
echo 'OK' > mpas_analysis_mvm_ts_1985-1988_climo_1987-1988_vs_ref_ts_1985-1986_climo_1985-1986.status
exit 0