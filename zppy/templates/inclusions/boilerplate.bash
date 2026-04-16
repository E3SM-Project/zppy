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

run_nco() {
  # Example:
  # environment_path=/global/cfs/cdirs/e3sm/zender/bin/ (set with jinja2 substitution from config file)
  # nco_cmd=ncclimo (passed in directly)
  # Runs `/global/cfs/cdirs/e3sm/zender/bin/ncclimo --npo` on the original arguments

  # Full list of NCO commands: https://nco.sourceforge.net/nco.html#Reference-Manual

  local environment_path="{{ nco_path }}"
  local nco_cmd=$1
  shift # Remove nco_cmd from the argument list

  if [[ -z "$environment_path" ]]; then
    # nco_path is empty, so use just the nco_cmd itself:
    "$nco_cmd" "$@"
  else
    # nco_path is non-empty, so use the full development setup:
    "${environment_path%/}/$nco_cmd" --npo "$@"
  fi
}
