#!/bin/bash
{% include 'slurm_header.sh' %}
{% include 'e3sm_unified' %}sh

# Turn on debug output if needed
debug={{ debug }}
if [[ "${debug,,}" == "true" ]]; then
  set -x
fi

# Script dir
cd {{ scriptDir }}

# Get jobid
id=${SLURM_JOBID}

# Update status file
STARTTIME=$(date +%s)
echo "RUNNING ${id}" > {{ prefix }}.status

# Create temporary workdir
workdir=`mktemp -d tmp.${id}.XXXX`
cd ${workdir}

# Input dir
input={{ input }}/{{ input_subdir }}

# Compute global averages
{
  for (( year={{ year1 }}; year<={{ year2 }}; year++ ))
  do
    YYYY=`printf "%04d" ${year}`
    for file in ${input}/*.{{ model_name }}.h0.${YYYY}-??.nc
    do
      echo $file
      # Extract file name
      tmp1=${file##*/}
      # Extract only last 10 characters: YYYY-MM.nc
      tmp2=${tmp1: -10:10}
      ncwa -v {{ vars }} -a ncol -w {{ weights }} ${file} ${tmp2}
    done
  done
}
if [ $? != 0 ]; then
  cd ..
  echo 'ERROR (1)' > {{ prefix }}.status
  exit 2
fi

# Concatenate into a single time series file
{
  Y1=`printf "%04d" {{ year1 }}`
  Y2=`printf "%04d" {{ year2 }}`
  ncrcat ????-??.nc {{ model_name }}.h0.glb.${Y1}01-${Y2}12.nc
  rm -f ????-??.nc
}
if [ $? != 0 ]; then
  cd ..
  echo 'ERROR (2)' > {{ prefix }}.status
  exit 2
fi

# Move to destination directory
{
  dest={{ output }}/post/atm/{{ grid }}/ts/monthly/{{ '%dyr' % (year2-year1+1) }}
  mkdir -p ${dest}
  mv {{ model_name }}.h0.glb.${Y1}01-${Y2}12.nc ${dest}
}
if [ $? != 0 ]; then
  cd ..
  echo 'ERROR (3)' > {{ prefix }}.status
  exit 2
fi

# Delete temporary workdir
cd ..
if [[ "${debug,,}" != "true" ]]; then
  rm -rf ${workdir}
fi

# Update status file and exit
{% raw %}
ENDTIME=$(date +%s)
ELAPSEDTIME=$(($ENDTIME - $STARTTIME))
{% endraw %}
echo ==============================================
echo "Elapsed time: $ELAPSEDTIME seconds"
echo ==============================================
echo 'OK' > {{ prefix }}.status
exit 0

