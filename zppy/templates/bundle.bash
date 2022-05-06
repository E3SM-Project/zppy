#!/bin/bash
{% include 'slurm_header.sh' %}

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

# Loop over all tasks
error=false
{% for task in tasks %}
echo === {{ task }}  ===
task={{ task }}
taskStatusFile="${task%.*}.status"
if [ ! -f ${taskStatusFile} ] || [ `cat ${taskStatusFile}` != "OK" ] ; then
  ./{{ task }}
  if [ $? -ne 0 ]; then
    error=true
  fi
fi
{% endfor %}

# Update status file and exit
{% raw %}
ENDTIME=$(date +%s)
ELAPSEDTIME=$(($ENDTIME - $STARTTIME))
{% endraw %}
echo ==============================================
echo "Elapsed time: $ELAPSEDTIME seconds"
echo ==============================================
if [ ${error} = true ]; then
  echo 'ERROR' > {{ prefix }}.status
  exit 1
else
  echo 'OK' > {{ prefix }}.status
  exit 0
fi

