#!/bin/bash

# Running on chrysalis

#SBATCH  --job-name=bundle_glb
#SBATCH  --account=e3sm
#SBATCH  --nodes=1
#SBATCH  --output=/zppy_snapshot/output/post/scripts/bundle_glb.o%j
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
echo "RUNNING ${id}" > bundle_glb.status

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

# Loop over all tasks
error=false

echo === ts_atm_monthly_glb_1985-1986-0002.bash  ===
task=ts_atm_monthly_glb_1985-1986-0002.bash
taskStatusFile="${task%.*}.status"
if [ ! -f ${taskStatusFile} ] || [ "`cat ${taskStatusFile}`" != "OK" ] ; then
  ./ts_atm_monthly_glb_1985-1986-0002.bash
  if [ $? -ne 0 ]; then
    error=true
  fi
fi

echo === ts_atm_monthly_glb_1987-1988-0002.bash  ===
task=ts_atm_monthly_glb_1987-1988-0002.bash
taskStatusFile="${task%.*}.status"
if [ ! -f ${taskStatusFile} ] || [ "`cat ${taskStatusFile}`" != "OK" ] ; then
  ./ts_atm_monthly_glb_1987-1988-0002.bash
  if [ $? -ne 0 ]; then
    error=true
  fi
fi

echo === ts_lnd_monthly_glb_1985-1986-0002.bash  ===
task=ts_lnd_monthly_glb_1985-1986-0002.bash
taskStatusFile="${task%.*}.status"
if [ ! -f ${taskStatusFile} ] || [ "`cat ${taskStatusFile}`" != "OK" ] ; then
  ./ts_lnd_monthly_glb_1985-1986-0002.bash
  if [ $? -ne 0 ]; then
    error=true
  fi
fi

echo === ts_lnd_monthly_glb_1987-1988-0002.bash  ===
task=ts_lnd_monthly_glb_1987-1988-0002.bash
taskStatusFile="${task%.*}.status"
if [ ! -f ${taskStatusFile} ] || [ "`cat ${taskStatusFile}`" != "OK" ] ; then
  ./ts_lnd_monthly_glb_1987-1988-0002.bash
  if [ $? -ne 0 ]; then
    error=true
  fi
fi


# Update status file and exit

ENDTIME=$(date +%s)
ELAPSEDTIME=$(($ENDTIME - $STARTTIME))

echo ==============================================
echo "Elapsed time: $ELAPSEDTIME seconds"
echo ==============================================
if [ ${error} = true ]; then
  echo 'ERROR (1)' > bundle_glb.status
  exit 1
else
  rm -f bundle_glb.status
  echo 'OK' > bundle_glb.status
  exit 0
fi