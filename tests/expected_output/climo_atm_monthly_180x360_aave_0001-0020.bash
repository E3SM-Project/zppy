#!/bin/bash


# Running on chrysalis

#SBATCH  --job-name=climo_atm_monthly_180x360_aave_0001-0020
#SBATCH  --nodes=4
#SBATCH  --output=test_output/post/scripts/climo_atm_monthly_180x360_aave_0001-0020.o%j
#SBATCH  --exclusive
#SBATCH  --time=02:00:00
#SBATCH  --partition=compute


# Load E3SM unified environment for LCRC (selectable)
source /lcrc/soft/climate/e3sm-unified/load_latest_e3sm_unified.sh

# Turn on debug output if needed
debug=False
if [[ "${debug,,}" == "true" ]]; then
  set -x
fi

# Script dir
cd test_output/post/scripts

# Get jobid
id=${SLURM_JOBID}

# Update status file
STARTTIME=$(date +%s)
echo "RUNNING ${id}" > climo_atm_monthly_180x360_aave_0001-0020.status

# Create temporary workdir
workdir=`mktemp -d tmp.${id}.XXXX`
cd ${workdir}


# --- Monthly climatologies ---
ncclimo \
--case=case_name \
--no_amwg_link \
--parallel=mpi \
--december_mode=sdd \
--yr_srt=1 \
--yr_end=20 \
--input=./archive/atm/hist \
--map=/home/ac.zender/data/maps/map_ne30pg2_to_cmip6_180x360_aave.20200201.nc \
--output=trash \
--regrid=output \
--model=eam



if [ $? != 0 ]; then
  cd ..
  echo 'ERROR (2)' > climo_atm_monthly_180x360_aave_0001-0020.status
  exit 2
fi

# Move regridded climo files to final destination
{
  dest=test_output/post/atm/180x360_aave/clim/20yr
  mkdir -p ${dest}
  mv output/*.nc ${dest}
}
if [ $? != 0 ]; then
  cd ..
  echo 'ERROR (3)' > climo_atm_monthly_180x360_aave_0001-0020.status
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
echo 'OK' > climo_atm_monthly_180x360_aave_0001-0020.status
exit 0
