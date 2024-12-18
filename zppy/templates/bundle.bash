#!/bin/bash
{% include 'inclusions/slurm_header.bash' %}
{% include 'inclusions/boilerplate.bash' %}

# Loop over all tasks
error=false
{% for task in tasks %}
echo === {{ task }}  ===
task={{ task }}
taskStatusFile="${task%.*}.status"
if [ ! -f ${taskStatusFile} ] || [ "`cat ${taskStatusFile}`" != "OK" ] ; then
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
  rm -f {{ prefix }}.status
  echo 'OK' > {{ prefix }}.status
  exit 0
fi
