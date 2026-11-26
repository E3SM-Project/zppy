#!/bin/bash

# Running on dane

#SBATCH  --job-name=climo_atm_monthly_180x360_aave_1985-1986
#SBATCH  --account=e3sm
#SBATCH  --nodes=4
#SBATCH  --output=/zppy_snapshot/output/post/scripts/climo_atm_monthly_180x360_aave_1985-1986.o%j
#SBATCH  --exclusive
#SBATCH  --time=00:30:00


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
echo "RUNNING ${id}" > climo_atm_monthly_180x360_aave_1985-1986.status

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
  if echo "source /usr/workspace/e3sm/apps/e3sm-unified/load_latest_e3sm_unified_dane.sh" | grep -Eq 'test_e3sm_unified|load_latest_e3sm_unified'; then
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
source /usr/workspace/e3sm/apps/e3sm-unified/load_latest_e3sm_unified_dane.sh
set +e

set_pkg_manager
echo "${pkg_manager} list nco:"
${pkg_manager} list nco || true # If we can't print this, just continue on.

# Create temporary workdir
hash=`mktemp --dry-run -d XXXX`
workdir=tmp.climo_atm_monthly_180x360_aave_1985-1986.${id}.${hash}
mkdir ${workdir}
cd ${workdir}


# --- Monthly climatologies ---
run_nco ncclimo \
--case=v3.LR.historical_0051 \
--jobs=${SLURM_NNODES} \
--thr=1 \
--parallel=mpi \
--yr_srt=1985 \
--yr_end=1986 \
--input=/zppy_snapshot/input/v3.LR.historical_0051/archive/atm/hist \
--map=/usr/workspace/e3sm/data/diagnostics/maps/map_ne30pg2_to_cmip6_180x360_aave.20200201.nc \
--output=trash \
--regrid=output \
--prc_typ=eam



if [ $? != 0 ]; then
  cd /zppy_snapshot/output/post/scripts
  echo 'ERROR (3)' > climo_atm_monthly_180x360_aave_1985-1986.status
  exit 3
fi

# Move regridded climo files to final destination
subdir=""

{
 subdir=clim
}

dest=/zppy_snapshot/output/post/atm/180x360_aave/${subdir}/2yr
mkdir -p ${dest}
mv output/*.nc ${dest}

if [ $? != 0 ]; then
  cd /zppy_snapshot/output/post/scripts
  echo 'ERROR (4)' > climo_atm_monthly_180x360_aave_1985-1986.status
  exit 4
fi

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
rm -f climo_atm_monthly_180x360_aave_1985-1986.status
echo 'OK' > climo_atm_monthly_180x360_aave_1985-1986.status
exit 0