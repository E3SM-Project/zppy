#!/bin/bash
{% include 'inclusions/slurm_header.bash' %}
{% include 'inclusions/boilerplate.bash' %}

set -e
{{ environment_commands }}
set +e

set_pkg_manager
echo "${pkg_manager} list zppy-interfaces:"
${pkg_manager} list zppy-interfaces || true # If we can't print this, just continue on.
echo "${pkg_manager} list pcmdi_metrics:"
${pkg_manager} list pcmdi_metrics || true # If we can't print this, just continue on.

# Need this setup as otherwise can not generate diagnostics
export UCX_SHM_DEVICES=all # or not set UCX_NET_DEVICES at all

# Make sure UVCDAT doesn't prompt us about anonymous logging
export UVCDAT_ANONYMOUS_LOG=False


# Use a non-interactive Matplotlib backend for batch diagnostics.
# Safe for workflows that save figures to files and avoids GUI/Tkinter errors
# on systems without a display.
export MPLBACKEND=Agg

# Script dir
cd {{ scriptDir }}

# Get jobid
id=${SLURM_JOBID}

# Update status file
STARTTIME=$(date +%s)
echo "RUNNING ${id}" > {{ prefix }}.status

# Basic definitions
case="{{ case }}"
www="{{ www }}"
run_type="{{ run_type }}"
results_dir="{{ run_type }}"
error_key=0

{% if current_set != "synthetic_plots" %}

# Input time range
y1={{ year1 }}
y2={{ year2 }}
ref_y1={{ ref_year1 }}
ref_y2={{ ref_year2 }}
ref_start_yr={{ ref_start_yr }}
ref_final_yr={{ ref_final_yr }}

# Formatted versions (analysis window only; ref formatted after refinement below)
Y1="$(printf "%04d" ${y1})"
Y2="$(printf "%04d" ${y2})"

# Keep originals for fallback
orig_ref_y1=${ref_y1}
orig_ref_y2=${ref_y2}
if [[ ${orig_ref_y1} -lt ${ref_start_yr} ]]; then
   orig_ref_y1=${ref_start_yr}
fi
if [[ ${orig_ref_y2} -gt ${ref_final_yr} ]]; then
   orig_ref_y2=${ref_final_yr}
fi
# Refine reference range
if [[ ${ref_start_yr} -le ${y1} && ${ref_final_yr} -ge ${y2} ]]; then
   # Availability fully covers analysis: use [y1, y2]
   ref_y1=${y1}
   ref_y2=${y2}
else
   # Case 2: Prefer the user's clamped custom window; only tweak if needed
   # 2a) If clamped custom overlaps the analysis window, use the intersection
   if [[ ${orig_ref_y1} -le ${y2} && ${orig_ref_y2} -ge ${y1} ]]; then
      # minimal trimming to fit inside [y1, y2]
      ref_y1=$(( orig_ref_y1 > y1 ? orig_ref_y1 : y1 ))
      ref_y2=$(( orig_ref_y2 < y2 ? orig_ref_y2 : y2 ))
   else
      # 2b) No overlap between custom and analysis:
      #     try availability i∩ analysis (minimal change wrt both)
      ovl_start=$(( ref_start_yr > y1 ? ref_start_yr : y1 ))
      ovl_end=$(( ref_final_yr < y2 ? ref_final_yr : y2 ))
      if [[ ${ovl_start} -le ${ovl_end} ]]; then
         ref_y1=${ovl_start}
         ref_y2=${ovl_end}
      else
         # 2c) Truly no overlap possible; fall back to clamped custom window
         ref_y1=${orig_ref_y1}
         ref_y2=${orig_ref_y2}
      fi
   fi
fi

# Format reference years after refinement
ref_Y1="$(printf "%04d" ${ref_y1})"
ref_Y2="$(printf "%04d" ${ref_y2})"

{% if current_set == "mean_climate"%}
source_vars="{{ clim_vars }}"
{% elif current_set == "variability_modes_cpl"%}
source_vars="{{ movc_vars }}"
{% elif current_set == "variability_modes_atm"%}
source_vars="{{ mova_vars }}"
{% elif current_set == "enso"%}
source_vars="{{ enso_vars }}"
{% endif %}

{% endif %}

# Top-level directory
web_dir=${www}/${case}/pcmdi_diags

##################################################
# info to construct pcmdi-preferred data convention
##################################################
model_name='{{ model_name }}'
tableID='{{ model_tableID }}'
{% if run_type == "model_vs_obs" %}
# The put_model_here gets replaced is passed into Python as a string literal
# And then replaced inside the Python code.
model_name_ref='obs.historical.put_model_here.00'
tableID_ref=${tableID}
{% elif run_type == "model_vs_model" %}
model_name_ref='{{ model_name_ref }}'
tableID_ref='{{ model_tableID_ref }}'
{%- endif %}
{% if current_set == "synthetic_plots" %}
# For synthetic_plots, discover the case_id from files written by upstream jobs,
# since those jobs may have run on a different calendar date.
clim_dir_discover=${www}/${case}/pcmdi_diags/model_vs_obs/metrics_data/mean_climate/
case_id=$(find "${clim_dir_discover}" -name "*.v*.json" 2>/dev/null \
           | grep -oP '\.v\d{8}\.' | head -1 | tr -d '.')
if [[ -z "${case_id}" ]]; then
  echo "WARNING: Could not discover case_id from upstream output; falling back to today's date."
  case_id=v$(date '+%Y%m%d')
fi
{% else %}
case_id=v$(date '+%Y%m%d')
{% endif %}

# Create temporary workdir
workdir=$(mktemp -d tmp.{{ prefix }}.${id}.XXXX)
cd ${workdir}

# files for definition of regions for regional mean
cat > regions_specs.json << EOF
{% include regions_specs %}
EOF

# file for aliases of observation datasets
cat > reference_alias.json << EOF
{% include reference_alias %}
EOF

# file for list of variables for synthetic_metrics metric plots
cat > synthetic_metrics_list.json << EOF
{% include synthetic_metrics_list %}
EOF

{% if current_set == "mean_climate" %}
create_links_acyc_climo() {
  local ts_dir_source="$1"
  local ts_dir_destination="$2"
  local begin_year="$3"
  local end_year="$4"
  local name_key="$5"
  local error_num="$6" # Will use error_num +0,+1,+2

  echo "create_links_acyc_climo: linking from ${ts_dir_source} to ${ts_dir_destination}"

  mkdir -p "${ts_dir_destination}"
  cd "${ts_dir_destination}" || exit

  local variables="{{ cmip_vars }}"
  local script_dir="{{ scriptDir }}"
  local prefix="{{ prefix }}"
  local ts_step="{{ ts_num_years }}"

  for v in ${variables//,/ }; do
    > "${v}_files.txt"  # Start fresh

    shopt -s nullglob
    for year in $(seq "${begin_year}" "${ts_step}" "${end_year}"); do
      local YYYY
      YYYY=$(printf "%04d" "${year}")
      for file in ${ts_dir_source}/${v}_*_${YYYY}*.nc; do
        [[ -f "${file}" ]] && echo "${file}" >> "${v}_files.txt"
      done
    done
    shopt -u nullglob

    if [[ ! -s "${v}_files.txt" ]]; then
      echo "WARNING: No input files found for variable ${v}, skipping climatology. \
            This variable may not have been processed or output by e3sm_to_cmip."
      continue
    fi

    first_file=$(head -n 1 "${v}_files.txt")
    if ! run_nco ncks -m "${first_file}" >/dev/null 2>&1; then
      echo "WARNING: First file is not a valid NetCDF for ${v}: ${first_file}, skipping climatology. \
            This variable may not have been processed or output by e3sm_to_cmip."
      continue
    fi

    # Derive monthly climatology files
    for month in $(seq 1 12); do
      local MM
      MM=$(printf "%02d" "${month}")
      run_nco ncra -O -h -F -d time,"${month}",,12 $(< "${v}_files.txt") "${v}_clm_${MM}.nc"
      if [[ $? -ne 0 ]]; then
        cd "${script_dir}" || exit
        echo "ERROR ($((error_num + 1)))" > "${prefix}.status"
        exit "$((error_num + 1))"
      fi
    done

    # Combine to form full annual cycle file
    local combined_name="${name_key}.${v}.${begin_year}01-${end_year}12.AC.${case_id}.nc"
    run_nco ncrcat -O -h -d time,0, "${v}_clm_"*.nc "${combined_name}"
    if [[ $? -ne 0 ]]; then
      cd "${script_dir}" || exit
      echo "ERROR ($((error_num + 2)))" > "${prefix}.status"
      exit "$((error_num + 2))"
    fi

    # Add bnds dimension if missing
    if ! run_nco ncks -m "${combined_name}" | grep -q "bnds = 2"; then
      echo "Adding missing bnds dimension..."
      run_nco ncap2 -O -h -s 'defdim("bnds",2)' \
        "${combined_name}" "${combined_name}"
      if [[ $? -ne 0 ]]; then
        cd "${script_dir}" || exit
	echo "ERROR ($((error_num + 3)))" > "${prefix}.status"
        exit "$((error_num + 3))"
      fi
    fi

    # Adjust time metadata for PCMDI diagnostics
    local cmdfix1='time[time]={15.5, 45, 74.5, 105, 125.5, 166, 196.5, 227.5, 258, 288.5,319, 349.5}'
    local cmdfix2='time_bnds[time,bnds]={0,31,31,59,59,90,90,120,120,151,151,181,181,212,212,243,243,273,273,304,304,334,334,365.}'
    local cmdfix3='time@units="days since 1850-01-01 00:00:00"'
    local cmdfix4='time@calendar="noleap"'
    local cmdfix5='time@bounds="time_bnds"'
    local cmdfix6='time_bnds@units=time@units'
    local cmdfix7='time_bnds@calendar=time@calendar'
    run_nco ncap2 -O -h -s "${cmdfix1};${cmdfix2};${cmdfix3};${cmdfix4};${cmdfix5};${cmdfix6};${cmdfix7}" \
      "${combined_name}" "${combined_name}"

    if [[ $? -ne 0 ]]; then
      cd "${script_dir}" || exit
      echo "ERROR ($((error_num + 4)))" > "${prefix}.status"
      exit "$((error_num + 4))"
    fi

    rm -vf "${v}_clm_"*.nc
  done

  if [ -z "$(ls ./*.nc 2>/dev/null)" ]; then
    echo "create_links_acyc_climo: ${ts_dir_destination} was not updated!"
    cd "${script_dir}" || exit
    echo "ERROR ($((error_num + 5)))" > "${prefix}.status"
    exit "$((error_num + 5))"
  fi

  cd ..
}

{% if run_type == "model_vs_obs" %}
create_links_acyc_climo_obs() {
  local ts_dir_source="$1"
  local ts_dir_destination="$2"
  local begin_year="$3"
  local end_year="$4"
  local error_num="$5" # Will use error_num +0,+1,+2

  local script_dir="{{ scriptDir }}"
  local prefix="{{ prefix }}"

  echo "create_links_acyc_climo_obs: linking from ${ts_dir_source} to ${ts_dir_destination}"

  mkdir -p "${ts_dir_destination}"
  cd "${ts_dir_destination}" || exit

  for file in "${ts_dir_source}"/*; do
    local fname
    local YYYYS YYYYE
    local SUBSTR
    local ttag tmp_file MM combined_name

    fname=$(basename "${file}")
    if [[ ${fname} != *.nc ]]; then
      # Skip non-.nc files
      continue
    fi

    # Match two date patterns (YYYYMM or YYYYMMDD) separated by _ or -
    if [[ ${fname} =~ ([0-9]{6,8})[_-]([0-9]{6,8}) ]]; then
      YYYYS="${BASH_REMATCH[1]}"
      YYYYE="${BASH_REMATCH[2]}"
    else
      echo "Warning: Could not extract dates from ${fname}, basename of ${file}"
      continue
    fi

    # Clip to specified year range if no overlap use full range covered by file
    orig_YYYYS="${YYYYS}"
    file_start_year=${YYYYS:0:4}
    file_end_year=${YYYYE:0:4}

    if (( file_end_year < begin_year || file_start_year > end_year )); then
      echo "WARNING: ${fname} does not overlap requested range ${begin_year}-${end_year}; using file range ${file_start_year}-${file_end_year}."
      YYYYS="${file_start_year}"
      YYYYE="${file_end_year}"
    else
      # Clip to specified year range
      (( file_start_year < begin_year )) && YYYYS="${begin_year}" || YYYYS="${file_start_year}"
      (( file_end_year > end_year )) && YYYYE="${end_year}" || YYYYE="${file_end_year}"
    fi

    # Extract prefix before the date range (removes from .${YYYYS} or -${YYYYS})
    SUBSTR="${fname%%[._-]${orig_YYYYS}*}"

    ttag="$(printf "%04d" "${YYYYS}")01-$(printf "%04d" "${YYYYE}")12"
    tmp_file="tmp_combine_${ttag}.nc"

    run_nco ncrcat -O -h -d time,"${YYYYS}-01-01","${YYYYE}-12-31" "${file}" "${tmp_file}"
    if [[ $? -ne 0 ]]; then
      echo "ERROR: ncrcat failed for ${fname} (date range ${YYYYS}-${YYYYE})"
      rm -f "${tmp_file}"
      cd "${script_dir}" || exit
      echo "ERROR ($((error_num + 1)))" > "${prefix}.status"
      exit "$((error_num + 1))"
    fi

    # Derive monthly climatology
    for month in $(seq 1 12); do
      local MM
      MM=$(printf "%02d" ${month})
      run_nco ncra -O -h -F -d time,"${month}",,12 "${tmp_file}" "tmp_clm_${MM}.nc"
      if [[ $? -ne 0 ]]; then
        echo "ERROR: ncra failed for ${fname} month ${MM}."
        rm -f tmp_clm_*.nc "${tmp_file}"
        cd "${script_dir}" || exit
        echo "ERROR ($((error_num + 2)))" > "${prefix}.status"
        exit "$((error_num + 2))"
      fi
    done
    # If any month failed, the tmp_clm files were cleaned up — skip to next file
    if ! ls tmp_clm_*.nc &>/dev/null; then
      continue
    fi

    combined_name="${SUBSTR}.${ttag}.AC.${case_id}.nc"
    run_nco ncrcat -O -h tmp_clm_*.nc "${combined_name}"
    if [[ $? -ne 0 ]]; then
      cd "${script_dir}" || exit
      echo "ERROR ($((error_num + 3)))" > "${prefix}.status"
      exit "$((error_num + 3))"
    fi

    # Adjust time metadata
    local cmdfix1='time[time]={15.5, 45, 74.5, 105, 125.5, 166, 196.5, 227.5, 258, 288.5,319, 349.5}'
    local cmdfix2='time@units="days since 1850-01-01 00:00:00"'
    local cmdfix3='time@calendar="noleap"'
    run_nco ncap2 -O -h -s "${cmdfix1};${cmdfix2};${cmdfix3}" "${combined_name}" "${combined_name}"
    if [[ $? -ne 0 ]]; then
      cd "${script_dir}" || exit
      echo "ERROR ($((error_num + 4)))" > "${prefix}.status"
      exit "$((error_num + 4))"
    fi

    # Add bnds dimension if missing
    if ! run_nco ncks -m "${combined_name}" | grep -q "bnds = 2"; then
      echo "Adding missing bnds dimension..."
      run_nco ncap2 -O -h -s 'defdim("bnds",2)' \
        "${combined_name}" "${combined_name}"
      if [[ $? -ne 0 ]]; then
        cd "${script_dir}" || exit
        echo "ERROR ($((error_num + 5)))" > "${prefix}.status"
        exit "$((error_num + 5))"
      fi
    fi

    local cmdfix4='time_bnds=make_bounds(time,$bnds,"time_bnds")'
    local cmdfix5='time_bnds@units=time@units'
    local cmdfix6='time_bnds@calendar=time@calendar'
    local cmdfix7='time@bounds="time_bnds"'
    run_nco ncap2 -O -h -s "${cmdfix4};${cmdfix5};${cmdfix6};${cmdfix7}" "${combined_name}" "${combined_name}"
    if [[ $? -ne 0 ]]; then
      cd "${script_dir}" || exit
      echo "ERROR ($((error_num + 6)))" > "${prefix}.status"
      exit "$((error_num + 6))"
    fi

    rm -vf tmp_*.nc
  done

  if [ -z "$( ls . )" ]; then
    echo "create_links_acyc_climo_obs: ${ts_dir_destination} was not updated!"
    cd "${script_dir}" || exit
    echo "ERROR (${error_num})" > "${prefix}.status"
    exit "${error_num}"
  fi

  cd ..
}
{% endif %}
{% endif %}

{% if current_set in ["variability_modes_cpl", "variability_modes_atm", "enso"] %}
create_links_ts() {
  local ts_dir_source="$1"
  local ts_dir_destination="$2"
  local begin_year="$3"
  local end_year="$4"
  local subname="$5"
  local error_num="$6"

  local script_dir="{{ scriptDir }}"
  local prefix="{{ prefix }}"
  local ts_step="{{ ts_num_years }}"
  local vars="${source_vars}"

  echo "create_links_ts: linking from ${ts_dir_source} to ${ts_dir_destination}"

  mkdir -p "${ts_dir_destination}"
  cd "${ts_dir_destination}" || exit

  local v file YYYY combined_name

  # Convert comma-separated list to array
  IFS=',' read -ra var_array <<< "${vars}"
  for v in "${var_array[@]}"; do
    > "${v}_files.txt"  # Reset file list

    shopt -s nullglob
    for year in $(seq "${begin_year}" "${ts_step}" "${end_year}"); do
      YYYY=$(printf "%04d" "${year}")
      for file in ${ts_dir_source}/${v}_*_${YYYY}*.nc; do
        [[ -f "${file}" ]] && echo "${file}" >> "${v}_files.txt"
      done
    done
    shopt -u nullglob

    combined_name="${subname}.${v}.${begin_year}01-${end_year}12.nc"
    if [[ -s "${v}_files.txt" ]]; then
      # Ensure input files have time calendar before string-based subsetting
      while IFS= read -r file; do
        [[ -z "${file}" ]] && continue

        if ! run_nco ncks -m "${file}" | grep -q "time:calendar"; then
          echo "Adding missing calendar attribute to input time: ${file}"
          run_nco ncatted -O -h -a calendar,time,o,c,"standard" "${file}"
          if [[ $? -ne 0 ]]; then
            cd "${script_dir}" || exit
	    echo "ERROR ($((error_num + 1)))" > "${prefix}.status"
	    exit "$((error_num + 1))"
          fi
        fi
      done < "${v}_files.txt"

      # Extract subset of time series
      run_nco ncrcat -O -h \
        -v "${v},time" \
        -d time,"${begin_year}-01-01","${end_year}-12-31" $(< "${v}_files.txt") "${combined_name}"
      if [[ $? -ne 0 ]]; then
        cd "${script_dir}" || exit
        echo "ERROR ($((error_num + 2)))" > "${prefix}.status"
	exit "$((error_num + 2))"
      fi
      echo "ncrcat subset successful"

      # Add bnds dimension if missing
      if ! run_nco ncks -m "${combined_name}" | grep -q "bnds = 2"; then
        echo "Adding missing bnds dimension..."
        run_nco ncap2 -O -h -s 'defdim("bnds",2)' "${combined_name}" "${combined_name}"
        if [[ $? -ne 0 ]]; then
          cd "${script_dir}" || exit
          echo "ERROR ($((error_num + 3)))" > "${prefix}.status"
	  exit "$((error_num + 3))"
        fi
        echo "ncap2 defdim successful"
      fi

      # Always overwrite time bounds
      local cmdfix1='time_bnds=make_bounds(time,$bnds,"time_bnds")'
      local cmdfix2='time_bnds@units=time@units'
      local cmdfix3='time_bnds@calendar=time@calendar'
      local cmdfix4='time@bounds="time_bnds"'
      run_nco ncap2 -O -h -s "${cmdfix1};${cmdfix2};${cmdfix3};${cmdfix4}" \
        "${combined_name}" "${combined_name}"
      if [[ $? -ne 0 ]]; then
        cd "${script_dir}" || exit
        echo "ERROR ($((error_num + 4)))" > "${prefix}.status"
        exit "$((error_num + 4))"
      fi
      echo "ncap2 time_bnds successful"

      # Add CF metadata
      run_nco ncatted -O \
        -a axis,time,o,c,"T" \
        -a standard_name,time,o,c,"time" \
        "${combined_name}" "${combined_name}"
      if [[ $? -ne 0 ]]; then
        cd "${script_dir}" || exit
        echo "ERROR ($((error_num + 5)))" > "${prefix}.status"
        exit "$((error_num + 5))"
      fi
      echo "ncatted CF metadata successful"
    else
      echo "Warning: No input files found for variable ${v} in ${ts_dir_source}. Skipping."
    fi
  done

  if [ -z "$(ls ./*.nc 2>/dev/null)" ]; then
    echo "create_links_ts: ${ts_dir_destination} was not updated!"
    cd "${script_dir}" || exit
    echo "ERROR ($((error_num + 6)))" > "${prefix}.status"
    exit "$((error_num + 6))"
  fi

  cd ..
}

{% if run_type == "model_vs_obs" %}
create_links_ts_obs() {
  local ts_dir_source="$1"
  local ts_dir_destination="$2"
  local begin_year="$3"
  local end_year="$4"
  local error_num="$5" # Will use error_num +0,+1,+2

  local script_dir="{{ scriptDir }}"
  local prefix="{{ prefix }}"

  echo "create_links_ts_obs: linking from ${ts_dir_source} to ${ts_dir_destination}"

  mkdir -p "${ts_dir_destination}"
  cd "${ts_dir_destination}" || exit

  local file fname SUBSTR YYYYS YYYYE ttag combined_name

  for file in "${ts_dir_source}"/*; do
    fname=$(basename "$file")
    echo "create_links_ts_obs: checking if nc file: ${fname}"
    if [[ ${fname} != *.nc ]]; then
      # Skip non-.nc files
      continue
    fi
    echo "create_links_ts_obs: processing ${file}"

    # Match two time patterns (YYYYMM or YYYYMMDD) separated by _ or -
    if [[ $fname =~ ^(.+)\.([0-9]{4})([0-9]{2}){1,2}[-_]([0-9]{4})([0-9]{2}){1,2}\.nc$ ]]; then
      SUBSTR="${BASH_REMATCH[1]}"   # everything before the .YYYY...
      file_start_year="${BASH_REMATCH[2]}"  # file start year
      file_end_year="${BASH_REMATCH[4]}"    # file end year
    else
      echo "Warning: Could not extract dates from ${fname}, basename of ${file}"
      continue
    fi

    # Clip years to be in the selected range
    if (( file_end_year < begin_year || file_start_year > end_year )); then
      echo "WARNING: ${fname} does not overlap requested range ${begin_year}-${end_year}; using file range ${file_start_year}-${file_end_year}."
      YYYYS="${file_start_year}"
      YYYYE="${file_end_year}"
    else
      (( file_start_year < begin_year )) && YYYYS="${begin_year}" || YYYYS="${file_start_year}"
      (( file_end_year > end_year )) && YYYYE="${end_year}" || YYYYE="${file_end_year}"
    fi

    ttag="$(printf "%04d" "${YYYYS}")01-$(printf "%04d" "${YYYYE}")12"
    combined_name="${SUBSTR}.${ttag}.nc"

    # Ensure input time has calendar attribute before string-based time subsetting
    if ! run_nco ncks -m "${file}" | grep -q "time:calendar"; then
      echo "Adding missing calendar attribute to input time..."
      run_nco ncatted -O -h -a calendar,time,o,c,"standard" "${file}"
      if [[ $? -ne 0 ]]; then
        cd "${script_dir}" || exit
	echo "ERROR ($((error_num + 1)))" > "${prefix}.status"
        exit "$((error_num + 1))"
      fi
      echo "ncatted successful"
    fi

<<<<<<< HEAD
    # Extract subset of time series
    run_nco ncrcat -O -h -d time,"${YYYYS}-01-01","${YYYYE}-12-31" "${file}" "${combined_name}"
    if [[ $? -ne 0 ]]; then
      cd "${script_dir}" || exit
      echo "ERROR ($((error_num + 2)))" > "${prefix}.status"
      exit "$((error_num + 2))"
    fi
    echo "ncrcat subset successful"

    # Add bnds dimension if missing
    if ! run_nco ncks -m "${combined_name}" | grep -q "bnds = 2"; then
      echo "Adding missing bnds dimension..."
      run_nco ncap2 -O -h -s 'defdim("bnds",2)' "${combined_name}" "${combined_name}"
      if [[ $? -ne 0 ]]; then
        cd "${script_dir}" || exit
        echo "ERROR ($((error_num + 3)))" > "${prefix}.status"
        exit "$((error_num + 3))"
      fi
      echo "ncap2 defdim successful"
    fi

    # Add time bounds
    local cmdfix1='time_bnds=make_bounds(time,$bnds,"time_bnds")'
    local cmdfix2='time_bnds@units=time@units'
    local cmdfix3='time_bnds@calendar=time@calendar'
    local cmdfix4='time@bounds="time_bnds"'
    run_nco ncap2 -O -h -s "${cmdfix1};${cmdfix2};${cmdfix3};${cmdfix4}" "${combined_name}" "${combined_name}"
=======
    # Normalize time to the nearest second to prevent floating-point precision
    # artifacts (e.g., cftime decoding a value as second=60 instead of
    # second=0 of the next day) that arise from ncrcat time subsetting.
    local cmdfix_t='time=double(round(time*86400.0)/86400.0)'
    run_nco ncap2 -O -h -s "${cmdfix_t}" "${combined_name}" "${combined_name}"
    if [[ $? -ne 0 ]]; then
      cd "${script_dir}" || exit
      echo "ERROR (${error_num})" > "${prefix}.status"
      exit "${error_num}"
    fi
    echo "time normalization successful"

    # Add time bounds
    local cmdfix1='if(!exists("bnds")) defdim("bnds",2)'
    local cmdfix2='time_bnds=make_bounds(time,$bnds,"time_bnds")'
    local cmdfix3='time_bnds@units=time@units'
    local cmdfix4='time_bnds@calendar=time@calendar'
    local cmdfix5='time_bnds=double(round(time_bnds*86400.0)/86400.0)'
    run_nco ncap2 -O -h -s "${cmdfix1};${cmdfix2};${cmdfix3};${cmdfix4};${cmdfix5}" "${combined_name}" "${combined_name}"
>>>>>>> 759c924 (Claude-augument enhancement: fix time precision and bnds dimension warnings)
    if [[ $? -ne 0 ]]; then
      cd "${script_dir}" || exit
      echo "ERROR ($((error_num + 4)))" > "${prefix}.status"
      exit "$((error_num + 4))"
    fi
    echo "ncap2 successful"

    # Add CF metadata
    run_nco ncatted -O \
      -a axis,time,o,c,"T" \
      -a standard_name,time,o,c,"time" \
      "${combined_name}" "${combined_name}"
    if [[ $? -ne 0 ]]; then
      cd "${script_dir}" || exit
      echo "ERROR ($((error_num + 5)))" > "${prefix}.status"
      exit "$((error_num + 5))"
    fi
    echo "ncatted CF metadata successful"
  done

  if [ -z "$( ls . )" ]; then
    echo "create_links_ts_obs: ${ts_dir_destination} was not updated!"
    cd "${script_dir}" || exit
    echo "ERROR ($((error_num + 6)))" > "${prefix}.status"
    exit "$((error_num + 6))"
  fi

  cd ..
}
{% endif %}
{% endif %}

########################
# Prepare the model data
########################
{% if current_set == "mean_climate" %}
# Define output directory for climatology files
climo_dir_primary="climo"
# Path to model's monthly climatology files
# This cmip_ts path is created via zppy/templates/e3sm_to_cmip.bash
climo_dir_source="{{ output }}/post/atm/{{ grid }}/cmip_ts/monthly"
# Link and process primary model climo data
create_links_acyc_climo "${climo_dir_source}" "${climo_dir_primary}" "${Y1}" "${Y2}" "${model_name}.${tableID}" 10
{% if run_type == "model_vs_model" %}
# Path to reference model's climatology files
climo_dir_source_ref="{{ reference_data_path_ts }}"
climo_dir_ref="climo_ref"
# Link and process reference model climo data
create_links_acyc_climo "${climo_dir_source_ref}" "${climo_dir_ref}" "${ref_Y1}" "${ref_Y2}" "${model_name_ref}.${tableID_ref}" 20
{% endif %}
{% endif %}

{% if current_set in ["variability_modes_cpl", "variability_modes_atm", "enso"] %}
# All these diagnostics use time series (ts) data
# Define output directory for primary model time series
ts_dir_primary="ts"
ts_dir_source="{{ output }}/post/atm/{{ ts_grid }}/cmip_ts/monthly"
# Create local links and combine time series NetCDF files for the primary model
create_links_ts "${ts_dir_source}" "${ts_dir_primary}" "${Y1}" "${Y2}" "${model_name}.${tableID}" 30
{% if run_type == "model_vs_model" %}
# Define time series path for reference model (adjust for different year spans)
ts_dir_source_ref="{{ reference_data_path_ts }}"
ts_dir_ref="ts_ref"
# Create local links and combine ts files for the reference model
create_links_ts "${ts_dir_source_ref}" "${ts_dir_ref}" "${ref_Y1}" "${ref_Y2}" "${model_name_ref}.${tableID_ref}" 40
{% endif %}
{% endif %}

{% if run_type == "model_vs_obs" and current_set != "synthetic_plots" %}
###########################################################################
# Prepare the observation data
# Observation datasets vary by diagnostic, so we use an external
# Python utility to handle linking and remapping to standard names.
###########################################################################
obstmp_dir="obs_link"
mkdir -p "${obstmp_dir}"
echo "Linking observational data into ${obstmp_dir}..."

###################
# Run process job
###################
echo "Linking observational data using SLURM..."

command="zi-pcmdi-link-observation --model_name_ref ${model_name_ref} --tableID_ref ${tableID_ref} --vars=${source_vars} --obs_sets {{ obs_sets }} --obs_ts {{ obs_ts }} --obstmp_dir ${obstmp_dir} --debug ${debug,,}"
echo "Running a zi-pcmdi command: ${command}"

set -e
{{ environment_commands_secondary }}
set +e

time ${command}

if [ $? -ne 0 ]; then
  cd {{ scriptDir }}
  echo "ERROR (50)" > {{ prefix }}.status
  exit 50
fi

set -e
{{ environment_commands }}
set +e

#######################################################
# Now create obs climo and time series for PCMDI diags
# Use same period as test model when possible
#######################################################
ts_dir_ref_source="{{ scriptDir }}/${workdir}/${obstmp_dir}"

{% if current_set == "mean_climate" %}
climo_dir_ref=climo_ref
# This will use errors code 61,62,63...:
create_links_acyc_climo_obs "${ts_dir_ref_source}" "${climo_dir_ref}" ${ref_Y1} ${ref_Y2} 60
{% elif current_set in ["variability_modes_cpl", "variability_modes_atm", "enso"] %}
ts_dir_ref=ts_ref
# This will use error codes 71,72,73...:
create_links_ts_obs "${ts_dir_ref_source}" "${ts_dir_ref}" ${ref_Y1} ${ref_Y2} 70
{% endif %}

{% endif %}

{% if current_set != "synthetic_plots" %}
########################################################
# generate basic parameter file for pcmdi metrics driver
########################################################
echo "About to create parameterfile.py, which will be passed in with -p"
echo "The current directory is: $PWD" # This will be of the form .../post/scripts/tmpDir

cat > parameterfile.py << EOF
import os
import sys
import json
#####################
# Basic Information
#####################

start_yr = int('${Y1}')
end_yr = int('${Y2}')
num_years = end_yr - start_yr + 1
period = f"{start_yr:04d}01-{end_yr:04d}12"

model_parts = '${model_name}'.split('.')
mip, exp, product, realm = model_parts[:4]

##############################################
# Configuration Shared with PCMDI Diagnostics
##############################################

# Whether to generate NetCDF outputs for observations and model results
nc_out_obs = {{ mov_nc_out_obs }}
nc_out_model = {{ mov_nc_out_model }}

# Output file extension: use .nc if either output is enabled,
# otherwise default to .xml
ext = ".nc" if nc_out_model or nc_out_obs else ".xml"

# User annotation and debug flag
user_notes = 'Provenance and results'
debug = {{ pcmdi_debug }}

# Enable plot generation for model and observation
plot = {{ mov_plot_model }}
plot_obs = {{ mov_plot_obs }}  # optional

# Execution mode and output format
run_type = '{{ run_type }}'
figure_format = '{{ figure_format }}'

# Save interpolated model climatologies?
save_test_clims = {{ save_test_clims }}

# Save all metrics results in a single file?
# Set to 'n' as metrics are computed per variable
metrics_in_single_file = 'n'

# Custom values for land/sea masking
regions_values = {
    "land": 100.0,
    "ocean": 0.0
}

# Template path for land/sea mask file (fixed input)
modpath_lf = os.path.join(
    'fixed',
    'sftlf.%(model).nc'
)

{% if current_set == "mean_climate" %}

############################################
# Setup Specific for Mean Climate Metrics
############################################
modver = "${case_id}"
parallel = False
generate_sftlf = False
sftlf_filename_template = modpath_lf

# Target grid: can be '2.5x2.5' or a CDMS2 grid object string
target_grid = '{{ target_grid }}'
targetGrid = target_grid  # for backward compatibility
target_grid_string = '{{ target_grid_string }}'

# Regridding tool and method (general use)
# OPTIONS: 'regrid2' or 'esmf'
regrid_tool = '{{ regrid_tool }}'
# OPTIONS: 'linear' or 'conservative' (only for 'esmf')
regrid_method = '{{ regrid_method }}'

# Regridding tool and method for ocean diagnostics
regrid_tool_ocn = '{{ regrid_tool_ocn }}'  # 'regrid2' or 'esmf'
regrid_method_ocn = ('{{ regrid_method_ocn }}')  # 'linear' or 'conservative'

# Model realization(s) to consider
realization = "*"

# Model product name from input
test_data_set = [product]

# Path to model climatology files
test_data_path = '${climo_dir_primary}'

# Template for model climatology filenames
filename_template = '.'.join([
    mip,
    exp,
    '%(model)',
    '%(realization)',
    '${tableID}',
    '%(variable)',
    period,
    'AC',
    '${case_id}',
    'nc'
])

# Path to reference climatology files
reference_data_path = '${climo_dir_ref}'

# Observation catalogue file (dynamic by subsection)
custom_observations = os.path.join(
    'pcmdi_diags',
    '{}_{}_catalogue.json'.format(
        '${climo_dir_ref}',
        '{{subsection}}'
    )
)

# Load variable-specific region definitions
regions = json.load(open('regions.json'))

# Load predefined region specifications and normalize domain lat/lon as tuples
regions_specs = json.load(open('regions_specs.json'))
for key in regions_specs:
    domain = regions_specs[key].get('domain', {})
    if 'latitude' in domain:
        domain['latitude'] = tuple(domain['latitude'])
        regions_specs[key]['domain']['latitude'] = domain['latitude']
    if 'longitude' in domain:
        domain['longitude'] = tuple(domain['longitude'])
        regions_specs[key]['domain']['longitude'] = domain['longitude']

# METRICS OUTPUT
metrics_output_path = os.path.join(
    'pcmdi_diags',
    'metrics_results',
    'mean_climate',
    mip,
    exp,
    '%(case_id)'
)

#INTERPOLATED MODELS' CLIMATOLOGIES
diagnostics_output_path = os.path.join(
    'pcmdi_diags',
    'diagnostic_results',
    'mean_climate',
    mip,
    exp,
    '%(case_id)'
)

test_clims_interpolated_output = diagnostics_output_path

{% endif %}

{% if current_set in ["variability_modes_cpl", "variability_modes_atm"] %}
# Setup for Mode Variability Diagnostics
msyear = int(start_yr)
meyear = int(end_yr)

# Seasons to analyze (comma-separated string to list)
seasons = '{{ seasons }}'.split(",")

# Data frequency (e.g., monthly, seasonal)
frequency = '{{ frequency }}'

# Variables to analyze (comma-separated string or space-separated)
{% if current_set == "variability_modes_cpl"%}
varModel = '{{ movc_vars }}'
{% elif current_set == "variability_modes_atm"%}
varModel = '{{ mova_vars }}'
{% endif %}

# Unit conversion flags for model and observations
ModUnitsAdjust = {{ ModUnitsAdjust }}
ObsUnitsAdjust = {{ ObsUnitsAdjust }}

# Mask out land regions (consider ocean-only if True)
landmask = {{ landmask }}

# Maximum number of eof modes
eofn_mod_max = {{ eofn_mod_max }}

# If True, remove domain mean from each time step
RmDomainMean = {{ RmDomainMean }}

# If True, normalize EOFs to unit variance
EofScaling = {{ EofScaling }}

# Conduct Combined EOF/CBF analysis (if True)
CBF = {{ CBF }}

# Conduct Conventional EOF analysis (if True)
ConvEOF = {{ ConvEOF }}

# Skip CMEC output (hardcoded for now)
cmec = False

# Whether to overwrite existing diagnostic output
update_json = False

# Template for model input file paths
modnames = [product]
realization = "*"
modpath = os.path.join(
    '${ts_dir_primary}',
    '{}.{}.%(model).%(realization).{}.%(variable).{}.nc'.format(
        mip, exp, '${tableID}', period
    )
)

# Output results directory
results_dir = os.path.join(
    'pcmdi_diags',
    '%(output_type)',
    'variability_modes',
    '%(mip)',
    '%(exp)',
    '${case_id}',
    '%(variability_mode)',
    '%(reference_data_name)',
)
{% endif %}

{% if current_set == "enso" %}
# Parameter Setup for ENSO Metrics
modnames = [product]
realization = realm

modpath = os.path.join(
    '${ts_dir_primary}',
    '{}.{}.%(model).%(realization).{}.%(variable).{}.nc'.format(
        mip, exp, '${tableID}', period
    )
)

# Observation/Reference settings
obs_cmor = True
obs_cmor_path = '${ts_dir_ref}'
obs_catalogue = 'obs_catalogue.json'

# Land/Sea mask for reference data
reference_data_lf_path = json.load(open('obs_landmask.json'))

# Metrics collection type (e.g., ENSO_perf, ENSO_tel, ENSO_proc)
# Defined externally via metricsCollection

# Output directory structure
results_dir = os.path.join(
    'pcmdi_diags',
    '%(output_type)',
    'enso_metric',
    '%(mip)',
    '%(exp)',
    '${case_id}',
    '%(metricsCollection)',
)

# Output filenames for JSON and NetCDF
json_name = "%(mip)_%(exp)_%(metricsCollection)_${case_id}_%(model)_%(realization)"

netcdf_name = json_name

{% endif %}

EOF

{% endif %}

################################################################
# Run PCMDI Diags
echo
echo ===== RUN PCMDI DIAGS =====
echo
################################

echo "About to set up a zi-pcmdi command"
echo "The current directory is: $PWD" # This will be of the form .../post/scripts/tmpDir

# Run diagnostics
mkdir -p pcmdi_diags

{% if current_set != "synthetic_plots" %}
{% if current_set == "mean_climate"%}
source_dirs="--climo_ts_dir_primary ${climo_dir_primary} --climo_ts_dir_ref ${climo_dir_ref}"
{% elif current_set in ["variability_modes_cpl", "variability_modes_atm", "enso"] %}
source_dirs="--climo_ts_dir_primary ${ts_dir_primary} --climo_ts_dir_ref ${ts_dir_ref}"
{% endif %}

# -------------------------------------------------------
# Adaptive safeguard for resource-intensive diagnostics
# -------------------------------------------------------
requested_workers={{ num_workers }}
effective_workers=${requested_workers}
subsection="{{ subsection }}"

# Each zppy subset is a separate SLURM job, so num_workers spans the entire
# job allocation.  The relevant CPU budget is the total across all nodes.
# {{ nodes }} is the compile-time node count (same value as --nodes={{ nodes }}),
# so multiplying by it is simpler and more portable than relying on the
# runtime variable SLURM_JOB_NUM_NODES.
if [[ -n "${SLURM_CPUS_ON_NODE}" ]]; then
  allocated_cpus=$(( SLURM_CPUS_ON_NODE * {{ nodes }} ))
elif command -v nproc >/dev/null 2>&1; then
  allocated_cpus=$(nproc)
else
  allocated_cpus=1
fi

# Guard against zero or empty (should not happen, but be safe)
if [[ -z "${allocated_cpus}" || "${allocated_cpus}" -lt 1 ]]; then
  allocated_cpus=1
fi

# EOF / variability modes are heavy because each subprocess may call
# threaded LAPACK/BLAS routines and allocate large arrays.
if [[ "${subsection}" == "variability_modes_atm" || "${subsection}" == "variability_modes_cpl" ]]; then
  safe_cap=$(( allocated_cpus / 4 ))

  if [[ ${safe_cap} -lt 1 ]]; then
    safe_cap=1
  fi

  if [[ ${requested_workers} -gt ${safe_cap} ]]; then
    echo "WARNING: Reducing num_workers from ${requested_workers} to ${safe_cap} for ${subsection} because EOF diagnostics are resource-intensive."
    effective_workers=${safe_cap}
  fi
fi

echo "PCMDI worker policy: requested_workers=${requested_workers}, allocated_cpus=${allocated_cpus}, effective_workers=${effective_workers}, subsection=${subsection}"

# Parameter passing can encounter errors if parameters are empty.
# So, it's a good idea to make sure they can't be (or at least are unlikely to be) empty.
# run_type == "model_vs_obs" only: obs_sets (default value is NOT "")
# run_type == "model_vs_model" only: model_name_ref, tableID_ref (default values are NOT "")
core_parameters="--num_workers ${effective_workers} --multiprocessing {{ multiprocessing }} --subsection {{ subsection }} ${source_dirs} --model_name ${model_name} --model_tableID {{ model_tableID }} --figure_format {{ figure_format }} --run_type {{ run_type }} --obs_sets {{ obs_sets }} --model_name_ref ${model_name_ref} --vars ${source_vars} --tableID_ref ${tableID_ref} --generate_sftlf {{ generate_sftlf }} --case_id ${case_id} --results_dir ${results_dir} --debug ${debug,,}"
{% endif %}

{% if current_set == "mean_climate" %}
command="zi-pcmdi-mean-climate ${core_parameters} --regions {{ clim_regions }}"
{% endif %}
{% if current_set in ["variability_modes_cpl", "variability_modes_atm"] %}
{% if current_set == "variability_modes_atm" %}
var_modes={{ mova_modes }}
{% elif current_set == "variability_modes_cpl" %}
var_modes={{ movc_modes }}
{% endif %}
command="zi-pcmdi-variability-modes ${core_parameters} --var_modes ${var_modes}"
{% endif %}
{% if current_set == "enso" %}
command="zi-pcmdi-enso ${core_parameters} --enso_groups {{ enso_groups }}"
{% endif %}
{% if current_set == "synthetic_plots" %}

#add command for mean climate viewer
clim_keys="--clim_viewer {{clim_viewer}} --cmip_clim_dir {{ cmip_clim_dir }} --cmip_clim_set {{ cmip_clim_set }} --clim_vars {{clim_vars}} --clim_years {{ clim_years }} --clim_regions {{ clim_regions }}"
{% if clim_viewer %}
echo "Checking if *.${case_id}.json files exist in clim_dir:"
clim_dir=${web_dir}/model_vs_obs/metrics_data/mean_climate/
find ${clim_dir} -name "*.${case_id}*.json"
echo "Done checking. There should be a list of files above, if they exist."
{% endif %}

#add command for modes variability viewer
movs_keys="--mova_viewer {{mova_viewer}} --movc_viewer {{movc_viewer}} --cmip_movs_dir {{ cmip_movs_dir }} --cmip_movs_set {{ cmip_movs_set }} --mova_modes {{ mova_modes }} --mova_vars {{mova_vars}} --mova_years {{mova_years}} --movc_modes {{ movc_modes }} --movc_vars {{movc_vars}} --movc_years {{movc_years}}"
{% if movc_viewer or mova_viewer %}
echo "Checking if var_mode_*.json files exist in variability_modes_dir:"
variability_modes_dir=${web_dir}/model_vs_obs/metrics_data/variability_modes/
find ${variability_modes_dir} -name "var_mode_*${case_id}*.json"
echo "Done checking. There should be a list of files above, if they exist."
{% endif %}

#add command for enso viewer
enso_keys="--enso_viewer {{ enso_viewer }} --cmip_enso_dir {{ cmip_enso_dir }} --cmip_enso_set {{ cmip_enso_set }} --enso_vars {{ enso_vars }} --enso_years {{ enso_years }}"
{% if enso_viewer %}
echo "Checking if var_mode_*.json files exist in variability_modes_dir:"
enso_dir=${web_dir}/model_vs_obs/metrics_data/enso_metric/*
find ${enso_dir} -name "*.${case_id}*.json"
echo "Done checking. There should be a list of files above, if they exist."
{% endif %}

command="zi-pcmdi-synthetic-plots --synthetic_sets {{ synthetic_sets }} --figure_format {{ figure_format }} --www ${www} --results_dir ${results_dir} --case {{ case }} --model_name {{ model_name }} --model_tableID {{ model_tableID }} --web_dir=${web_dir} --pcmdi_webtitle {{ pcmdi_webtitle }} --pcmdi_version {{ pcmdi_version }} --run_type ${run_type} --pcmdi_external_prefix {{ diagnostics_base_path }} --pcmdi_viewer_template {{ pcmdi_viewer_template }} --save_all_data {{ save_all_data }} ${clim_keys} ${movs_keys} ${enso_keys} --debug ${debug,,}"

{% endif %}

# Run diagnostics
set -e
{{ environment_commands_secondary }}
set +e

echo "Running a zi-pcmdi command: ${command}"
echo "The current directory is: $PWD" # This will be of the form .../post/scripts/tmpDir
time ${command}
if [ $? != 0 ]; then
  cd {{ scriptDir }}
  echo 'ERROR (80)' > {{ prefix }}.status
  exit 80
fi

set -e
{{ environment_commands }}
set +e

#################################
# Copy output to web server
echo
echo ===== COPY FILES TO WEB SERVER =====
echo

# Create top-level directory
mkdir -p ${web_dir}
if [ $? != 0 ]; then
  cd {{ scriptDir }}
  echo 'ERROR (90)' > {{ prefix }}.status
  exit 90
fi

{% if machine in ['pm-cpu', 'pm-gpu'] %}
# For NERSC, make sure it is world readable
f=`realpath ${web_dir}`
while [[ $f != "/" ]]
do
  owner=`stat --format '%U' $f`
  if [ "${owner}" = "${USER}" ]; then
    chgrp e3sm $f
    chmod go+rx $f
  fi
  f=$(dirname $f)
done
{% endif %}

############################################
# Copy files
#rsync -a --delete ${results_dir} ${web_dir}/
{% if current_set != "synthetic_plots" %}
rsync -a ${results_dir} ${web_dir}/
if [ $? != 0 ]; then
  cd {{ scriptDir }}
  echo 'ERROR (100)' > {{ prefix }}.status
  exit 100
fi
{% endif %}

{% if machine in ['pm-cpu', 'pm-gpu'] %}
# For NERSC, change permissions of new files
pushd ${web_dir}/
chgrp -R e3sm ${results_dir}
chmod -R go+rX,go-w ${results_dir}
popd
{% endif %}

{% if machine in ['anvil', 'chrysalis'] %}
# For LCRC, change permissions of new files
pushd ${web_dir}/
chmod -R go+rX,go-w ${results_dir}
popd
{% endif %}

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
rm -f {{ prefix }}.status
echo 'OK' > {{ prefix }}.status
exit 0
