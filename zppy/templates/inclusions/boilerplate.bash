# Turn on debug output if needed
debug={{ debug }}
if [[ "${debug,,}" == "true" ]]; then
  set -x
fi

# Script dir
cd {{ scriptDir }}

# Get jobid
{% if scheduler == "slurm" %}
id=${SLURM_JOBID}
{% elif scheduler == "pbs" %}
id=${PBS_JOBID}
{% endif %}

# Update status file
STARTTIME=$(date +%s)
echo "RUNNING ${id}" > {{ prefix }}.status
