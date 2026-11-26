#!/bin/bash

# Running on chrysalis

#SBATCH  --job-name=ts_atm_monthly_eamxx_180x360_aave_1985-1986-0002
#SBATCH  --account=e3sm
#SBATCH  --nodes=1
#SBATCH  --output=/zppy_snapshot/output/post/scripts/ts_atm_monthly_eamxx_180x360_aave_1985-1986-0002.o%j
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
echo "RUNNING ${id}" > ts_atm_monthly_eamxx_180x360_aave_1985-1986-0002.status

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
workdir=tmp.ts_atm_monthly_eamxx_180x360_aave_1985-1986-0002.${id}.${hash}
mkdir ${workdir}
cd ${workdir}

# Create symbolic links to input files
input=/zppy_snapshot/input/v3.LR.historical_0051/run/
for (( year=1985; year<=1986; year++ ))
do
  YYYY=`printf "%04d" ${year}`
  for file in ${input}/1ma_ne30pg2.AVERAGE.nmonths_x1.${YYYY}-*.nc
  do
    ln -s ${file} .
  done
done


vars=ps,T_2m,SeaLevelPressure,U,V,T_mid

ls 1ma_ne30pg2.AVERAGE.nmonths_x1.????-*.nc > input.txt
if grep -q "*" input.txt; then
  cd /zppy_snapshot/output/post/scripts
  echo 'Missing input files'
  echo 'ERROR (1)' > ts_atm_monthly_eamxx_180x360_aave_1985-1986-0002.status
  exit 1
fi
# Generate time series files
# If the user-defined parameter "vars" is "", then ${vars}, defined above, will be too.
cat input.txt | run_nco ncclimo \
-c 1ma_ne30pg2 \
-v ${vars} \
--split \
--var_xtr=ps,hyai,hyam,hybi,hybm,area,landfrac,ocnfrac \
--yr_srt=1985 \
--yr_end=1986 \
--ypf=2 \
--map=/lcrc/group/e3sm/diagnostics/maps/map_ne30pg2_to_cmip6_180x360_aave.20200201.nc \
-o trash \
-O output \
--prc_typ=eamxx



if [ $? != 0 ]; then
  cd /zppy_snapshot/output/post/scripts
  echo 'ERROR (2)' > ts_atm_monthly_eamxx_180x360_aave_1985-1986-0002.status
  exit 2
fi

# Vertical regrid (model levels → pressure levels)
# When vrt_remap_vars is set, regrid the listed vars and write to a sibling
# directory ts_vrt_remap/ alongside the standard ts/ output.
mkdir output_plev
# ncremap reads the source vertical grid from the input file only when the
# vertical variables carry it with CF formula_terms. Older EAMxx output does
# not, so derive an explicit --vrt_in file from this run's own output (any
# vertical grid works). Newer EAMxx output may carry only the interface
# (hyai,hybi) or only the midpoint (hyam,hybm) coefficients, so keep whichever
# are present. Use the output's P0 if present, else the reference pressure.
raw_file=`head -n 1 input.txt`
vrt_vars=''
run_nco ncks -m -v hyai,hybi ${raw_file} > /dev/null 2>&1 && vrt_vars=hyai,hybi
run_nco ncks -m -v hyam,hybm ${raw_file} > /dev/null 2>&1 && vrt_vars=${vrt_vars:+${vrt_vars},}hyam,hybm
if [[ -n "${vrt_vars}" && "${vrt_vars}" != 'hyai,hybi,hyam,hybm' ]]; then
  echo 'WARNING: '${raw_file}' has only '${vrt_vars}' for the source vertical grid.'
  echo 'Vertical remapping then needs NCO >= 5.4.2; otherwise set vrt_in_file.'
fi
[[ -n "${vrt_vars}" ]] && \
  { run_nco ncks -O -v ${vrt_vars},P0 ${raw_file} vrt_in.nc 2> /dev/null || \
    { run_nco ncks -O -v ${vrt_vars} ${raw_file} vrt_in.nc && \
      run_nco ncap2 -A -s 'P0=100000.0' vrt_in.nc ; } ; }
if [ $? != 0 ]; then
  cd /zppy_snapshot/output/post/scripts
  echo 'Failed to derive source vertical grid file from '${raw_file}
  echo 'It needs hyai,hybi and/or hyam,hybm. Set vrt_in_file explicitly to work around this.'
  echo 'ERROR (7)' > ts_atm_monthly_eamxx_180x360_aave_1985-1986-0002.status
  exit 7
fi
vrt_in_file=vrt_in.nc
IFS=',' read -ra vremap_vars <<< "U,V,T_mid"
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
      --vrt_out='/lcrc/group/e3sm/diagnostics/e3sm_to_cmip_data/maps/vrt_remap_plev19.nc' \
      --ps_nm=${file}/ps \
      --vrt_in="${vrt_in_file}" \
      ${file} ${out_file}
    if [ $? != 0 ]; then
      cd /zppy_snapshot/output/post/scripts
      echo 'ERROR (6)' > ts_atm_monthly_eamxx_180x360_aave_1985-1986-0002.status
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
  echo 'ERROR (3)' > ts_atm_monthly_eamxx_180x360_aave_1985-1986-0002.status
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
  echo 'ERROR (5)' > ts_atm_monthly_eamxx_180x360_aave_1985-1986-0002.status
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
rm -f ts_atm_monthly_eamxx_180x360_aave_1985-1986-0002.status
echo 'OK' > ts_atm_monthly_eamxx_180x360_aave_1985-1986-0002.status
exit 0