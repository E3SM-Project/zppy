#!/bin/bash

# Running on compy

#SBATCH  --job-name=ts_atm_monthly_180x360_aave_1985-1986-0002
#SBATCH  --account=e3sm
#SBATCH  --nodes=1
#SBATCH  --output=/zppy_snapshot/output/post/scripts/ts_atm_monthly_180x360_aave_1985-1986-0002.o%j
#SBATCH  --exclusive
#SBATCH  --time=00:30:00


#SBATCH  --qos=regular
#SBATCH  --partition=slurm


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
echo "RUNNING ${id}" > ts_atm_monthly_180x360_aave_1985-1986-0002.status

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
  if echo "source /share/apps/E3SM/conda_envs/load_latest_e3sm_unified_compy.sh" | grep -Eq 'test_e3sm_unified|load_latest_e3sm_unified'; then
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
source /share/apps/E3SM/conda_envs/load_latest_e3sm_unified_compy.sh
set +e

set_pkg_manager
echo "${pkg_manager} list nco:"
${pkg_manager} list nco || true # If we can't print this, just continue on.

# Create temporary workdir
hash=`mktemp --dry-run -d XXXX`
workdir=tmp.ts_atm_monthly_180x360_aave_1985-1986-0002.${id}.${hash}
mkdir ${workdir}
cd ${workdir}

# Create symbolic links to input files
input=/zppy_snapshot/input/v3.LR.historical_0051/archive/atm/hist
for (( year=1985; year<=1986; year++ ))
do
  YYYY=`printf "%04d" ${year}`
  for file in ${input}/v3.LR.historical_0051.eam.h0.${YYYY}-*.nc
  do
    ln -s ${file} .
  done
done


vars=FSNTOA,FLUT,FSNT,FLNT,FSNS,FLNS,SHFLX,QFLX,TAUX,TAUY,PRECC,PRECL,PRECSC,PRECSL,TS,TREFHT,CLDTOT,CLDHGH,CLDMED,CLDLOW,U,PSL

ls v3.LR.historical_0051.eam.h0.????-*.nc > input.txt
if grep -q "*" input.txt; then
  cd /zppy_snapshot/output/post/scripts
  echo 'Missing input files'
  echo 'ERROR (1)' > ts_atm_monthly_180x360_aave_1985-1986-0002.status
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
--map=/compyfs/diagnostics/maps/map_ne30pg2_to_cmip6_180x360_aave.20200201.nc \
-o trash \
-O output \
--prc_typ=eam



if [ $? != 0 ]; then
  cd /zppy_snapshot/output/post/scripts
  echo 'ERROR (2)' > ts_atm_monthly_180x360_aave_1985-1986-0002.status
  exit 2
fi

# Vertical regrid (model levels → pressure levels)
# When vrt_remap_vars is set, regrid the listed vars and write to a sibling
# directory ts_vrt_remap/ alongside the standard ts/ output.
mkdir output_plev
IFS=',' read -ra vremap_vars <<< "T"
for var in "${vremap_vars[@]}"
do
  for file in output/${var}_1985??_1986??.nc
  do
    if [ ! -f "${file}" ]; then continue; fi
    out_file=output_plev/$(basename "${file}")
    run_nco ncremap \
      -p mpi \
      --vrt_ntp=log \
      --vrt_xtr=mss_val \
      --vrt_out='/compyfs/diagnostics/e3sm_to_cmip_data/maps/vrt_remap_plev19.nc' \
      ${file} ${out_file}
    if [ $? != 0 ]; then
      cd /zppy_snapshot/output/post/scripts
      echo 'ERROR (6)' > ts_atm_monthly_180x360_aave_1985-1986-0002.status
      exit 6
    fi
  done
done

# Move output ts files to final destination
{
  dest=/zppy_snapshot/output/post/atm/180x360_aave/ts/monthly/2yr
  mkdir -p ${dest}
  mv output/*.nc ${dest}
}
if [ $? != 0 ]; then
  cd /zppy_snapshot/output/post/scripts
  echo 'ERROR (3)' > ts_atm_monthly_180x360_aave_1985-1986-0002.status
  exit 3
fi
# Move vertically regridded ts files to sibling destination
{
  dest_plev=/zppy_snapshot/output/post/atm/180x360_aave/ts_vrt_remap/monthly/2yr
  mkdir -p ${dest_plev}
  mv output_plev/*.nc ${dest_plev}
}
if [ $? != 0 ]; then
  cd /zppy_snapshot/output/post/scripts
  echo 'ERROR (5)' > ts_atm_monthly_180x360_aave_1985-1986-0002.status
  exit 5
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
rm -f ts_atm_monthly_180x360_aave_1985-1986-0002.status
echo 'OK' > ts_atm_monthly_180x360_aave_1985-1986-0002.status
exit 0