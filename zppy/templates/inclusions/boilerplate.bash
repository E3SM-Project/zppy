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

set_pkg_manager() {
  # Detect whether to use pixi or conda based on environment_commands
  # Important: we need the quotes since environment_commands might
  # include multiple commands, separated by semi-colon.
  if echo "{{ environment_commands }}" | grep -q "conda"; then
      pkg_manager="conda"
  else
      pkg_manager="pixi"
  fi

  # We always want to know what the python version is.
  echo "${pkg_manager} list python:"
  ${pkg_manager} list python || true # If we can't print this, just continue on.
}
