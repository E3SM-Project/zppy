#!/bin/bash

# Running on chrysalis

#SBATCH  --job-name=ts_atm_daily_180x360_aave_1985-1986-0002
#SBATCH  --account=e3sm
#SBATCH  --nodes=1
#SBATCH  --output=/zppy_snapshot/output/post/scripts/ts_atm_daily_180x360_aave_1985-1986-0002.o%j
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
echo "RUNNING ${id}" > ts_atm_daily_180x360_aave_1985-1986-0002.status

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
echo "${pkg_manager} list nco:"
${pkg_manager} list nco || true # If we can't print this, just continue on.

# Create temporary workdir
hash=`mktemp --dry-run -d XXXX`
workdir=tmp.ts_atm_daily_180x360_aave_1985-1986-0002.${id}.${hash}
mkdir ${workdir}
cd ${workdir}

# Create symbolic links to input files
input=/zppy_snapshot/input/v3.LR.historical_0051/archive/atm/hist
for (( year=1985; year<=1986; year++ ))
do
  YYYY=`printf "%04d" ${year}`
  for file in ${input}/v3.LR.historical_0051.eam.h1.${YYYY}-*.nc
  do
    ln -s ${file} .
  done
done
# For non-monthly input files, need to add the last file of the previous year
year=1984
YYYY=`printf "%04d" ${year}`
mapfile -t files < <( ls ${input}/v3.LR.historical_0051.eam.h1.${YYYY}-*.nc 2> /dev/null )
if [ ${#files[@]} -ne 0 ]
then
  ln -s ${files[-1]} .
fi
# as well as first file of next year to ensure that first and last years are complete
year=1987
YYYY=`printf "%04d" ${year}`
mapfile -t files < <( ls ${input}/v3.LR.historical_0051.eam.h1.${YYYY}-*.nc 2> /dev/null )
if [ ${#files[@]} -ne 0 ]
then
  ln -s ${files[0]} .
fi


vars=PRECT

ls v3.LR.historical_0051.eam.h1.????-*.nc > input.txt
if grep -q "*" input.txt; then
  cd /zppy_snapshot/output/post/scripts
  echo 'Missing input files'
  echo 'ERROR (1)' > ts_atm_daily_180x360_aave_1985-1986-0002.status
  exit 1
fi
# Generate time series files
# If the user-defined parameter "vars" is "", then ${vars}, defined above, will be too.
cat input.txt | run_nco ncclimo \
-c v3.LR.historical_0051 \
-v ${vars} \
--split \
--yr_srt=1985 \
--yr_end=1986 \
--ypf=2 \
--map=/lcrc/group/e3sm/diagnostics/maps/map_ne30pg2_to_cmip6_180x360_aave.20200201.nc \
-o trash \
-O output \
--clm_md=hfs \
--dpf=30 \
--tpd=1 \
--prc_typ=eam



if [ $? != 0 ]; then
  cd /zppy_snapshot/output/post/scripts
  echo 'ERROR (2)' > ts_atm_daily_180x360_aave_1985-1986-0002.status
  exit 2
fi

# Move output ts files to final destination
{
  dest=/zppy_snapshot/output/post/atm/180x360_aave/ts/daily/2yr
  mkdir -p ${dest}
  mv output/*.nc ${dest}
}
if [ $? != 0 ]; then
  cd /zppy_snapshot/output/post/scripts
  echo 'ERROR (3)' > ts_atm_daily_180x360_aave_1985-1986-0002.status
  exit 3
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
rm -f ts_atm_daily_180x360_aave_1985-1986-0002.status
echo 'OK' > ts_atm_daily_180x360_aave_1985-1986-0002.status
exit 0