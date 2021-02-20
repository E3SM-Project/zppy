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

# Generate climo files
ncclimo -n '-x' -v ANRAIN,ANSNOW,AQRAIN,AQSNOW \
--no_amwg_link -p mpi -a sdd \
-c {{ case }} \
-s {{ year1 }} -e {{ year2 }} \
-i {{ input }}/{{ input_subdir }} \
-r {{ mapping_file }} \
-o clim \
-O clim_rgr \
-m {{ model_name }}

if [ $? != 0 ]; then
  cd ..
  echo 'ERROR (1)' > {{ prefix }}.status
  exit 1
fi

# Move regridded climo files to final destination
{
  dest={{ output }}/post/atm/{{ grid }}/clim/{{ '%dyr' % (year2-year1+1) }}
  mkdir -p ${dest}
  mv clim_rgr/*.nc ${dest}
}
if [ $? != 0 ]; then
  cd ..
  echo 'ERROR (2)' > {{ prefix }}.status
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

