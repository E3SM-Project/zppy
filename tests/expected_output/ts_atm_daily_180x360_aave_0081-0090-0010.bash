#!/bin/bash


# Running on chrysalis

#SBATCH  --job-name=ts_atm_daily_180x360_aave_0081-0090-0010
#SBATCH  --nodes=1
#SBATCH  --output=test_output/post/scripts/ts_atm_daily_180x360_aave_0081-0090-0010.o%j
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
echo "RUNNING ${id}" > ts_atm_daily_180x360_aave_0081-0090-0010.status

# Create temporary workdir
workdir=`mktemp -d tmp.${id}.XXXX`
cd ${workdir}

# Create symbolic links to input files
input=./archive/atm/hist
for (( year=81; year<=90; year++ ))
do
  YYYY=`printf "%04d" ${year}`
  for file in ${input}/case_name.eam.h1.${YYYY}-*.nc
  do
    ln -s ${file} .
  done
done
# For non-monthly input files, need to add the last file of the previous year
year=80
YYYY=`printf "%04d" ${year}`
mapfile -t files < <( ls ${input}/case_name.eam.h1.${YYYY}-*.nc 2> /dev/null )
if [ ${#files[@]} -ne 0 ]
then
  ln -s ${files[-1]} .
fi
# as well as first file of next year to ensure that first and last years are complete
year=91
YYYY=`printf "%04d" ${year}`
mapfile -t files < <( ls ${input}/case_name.eam.h1.${YYYY}-*.nc 2> /dev/null )
if [ ${#files[@]} -ne 0 ]
then
  ln -s ${files[0]} .
fi

# Generate time series files
ncclimo \
-c case_name \
-v PRECT \
--yr_srt=81 \
--yr_end=90 \
--ypf=10 \
--map=/home/ac.zender/data/maps/map_ne30pg2_to_cmip6_180x360_aave.20200201.nc \
-o trash \
-O output \
--clm_md=hfs \
--dpf=30 \
--tpd=1 \
case_name.eam.h1.????-*.nc

if [ $? != 0 ]; then
  cd ..
  echo 'ERROR (1)' > ts_atm_daily_180x360_aave_0081-0090-0010.status
  exit 1
fi

# Move output ts files to final destination
{
  dest=test_output/post/atm/180x360_aave/ts/daily/10yr
  mkdir -p ${dest}
  mv output/*.nc ${dest}
}
if [ $? != 0 ]; then
  cd ..
  echo 'ERROR (2)' > ts_atm_daily_180x360_aave_0081-0090-0010.status
  exit 2
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
echo 'OK' > ts_atm_daily_180x360_aave_0081-0090-0010.status
exit 0
