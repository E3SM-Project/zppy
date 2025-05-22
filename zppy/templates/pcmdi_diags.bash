#!/bin/bash
{% include 'inclusions/slurm_header.sh' %}

{{ environment_commands }}

# Turn on debug output if needed
debug={{ debug }}
if [[ "${debug,,}" == "true" ]]; then
  set -x
fi

# Need this setup as otherwise can not generate diagnostics
export UCX_SHM_DEVICES=all # or not set UCX_NET_DEVICES at all

# Make sure UVCDAT doesn't prompt us about anonymous logging
export UVCDAT_ANONYMOUS_LOG=False

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
ref_name={{ ref_name }}
{% if "synthetic_plots" not in subsection %}

# Input variables
y1={{ year1 }}
y2={{ year2 }}
ref_y1={{ ref_year1 }}
ref_y2={{ ref_year2 }}
ref_start_yr={{ ref_start_yr }}
ref_final_yr={{ ref_final_yr }}

# Formatted versions
Y1="$(printf "%04d" ${y1})"
Y2="$(printf "%04d" ${y2})"
ref_Y1="$(printf "%04d" ${ref_y1})"
ref_Y2="$(printf "%04d" ${ref_y2})"

# Refine reference range
if [[ ${ref_y1} -lt ${ref_start_yr} ]]; then
    ref_y1=${ref_start_yr}
    ref_Y1="$(printf "%04d" ${ref_y1})"
fi

num_years=$((y2 - y1 + 1))
ref_end_yr=$((ref_y1 + num_years - 1))

if [[ ${ref_y2} -gt ${ref_end_yr} ]]; then
    ref_y2=${ref_end_yr}
    ref_Y2="$(printf "%04d" ${ref_y2})"
fi

if [[ ${ref_y2} -gt ${ref_final_yr} ]]; then
    ref_y2=${ref_final_yr}
    ref_Y2="$(printf "%04d" ${ref_y2})"
fi

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
case_id=v$(date '+%Y%m%d')

# Create temporary workdir
workdir=`mktemp -d tmp.${id}.XXXX`
cd ${workdir}


# TODO: Move anything in {{pcmdi_external_prefix}} == /lcrc/group/e3sm/diagnostics/ to the inclusions subdir
# or to zppy-interfaces

# utility file for pcmdi-zppy workflow
cp -r '{{pcmdi_external_prefix}}/{{pcmdi_zppy_util}}'   .

# files for definition of regions for regional mean
cp -r '{{pcmdi_external_prefix}}/{{regions_specs}}'     .

# file for aliases of observation datasets
cp -r '{{pcmdi_external_prefix}}/{{reference_alias}}'   .

# file for list of variables for synthetic_metrics metric plots
cp -r '{{pcmdi_external_prefix}}/{{synthetic_metrics}}' .

# utility file for pcmdi-zppy viewer
cp -r '{{pcmdi_external_prefix}}/{{pcmdi_viewer_util}}' .

{% if "mean_climate" in subsection %}
create_links_acyc_climo() {
  local ts_dir_source="$1"
  local ts_dir_destination="$2"
  local begin_year="$3"
  local end_year="$4"
  local name_key="$5"
  local error_num="$6"

  echo "create_links_acyc_climo: linking from ${ts_dir_source} to ${ts_dir_destination}"

  mkdir -p "${ts_dir_destination}"
  cd "${ts_dir_destination}" || exit

  local variables="{{ cmip_vars }}"
  local script_dir="{{ scriptDir }}"
  local prefix="{{ prefix }}"
  local ts_step="{{ ts_num_years }}"
  local dofm=(15.5 45 74.5 105 125.5 166 196.5 227.5 258 288.5 319 349.5)

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

    # Derive monthly climatology files
    for month in $(seq 1 12); do
      local MM
      MM=$(printf "%02d" "${month}")
      ncra -O -h -F -d time,"${month}",,12 $(< "${v}_files.txt") "${v}_clm_${MM}.nc"
    done

    # Combine to form full annual cycle file
    local combined_name="${name_key}.${v}.${begin_year}01-${end_year}12.AC.${case_id}.nc"
    ncrcat -O -d time,0, "${v}_clm_"*.nc "${combined_name}"

    # Adjust time metadata for PCMDI diagnostics
    local cmdfix1='time[time]={15.5, 45, 74.5, 105, 125.5, 166, 196.5, 227.5, 258, 288.5,319, 349.5}'
    local cmdfix2='time_bnds[time,bnds]={0,31,31,59,59,90,90,120,120,151,151,181,181,212,212,243,243,273,273,304,304,334,334,365.}'
    local cmdfix3='time@units="days since 1850-01-01 00:00:00"'
    local cmdfix4='time@calendar="noleap"'
    local cmdfix5='time@bounds="time_bnds"'
    ncap2 -O -h -s "${cmdfix1};${cmdfix2};${cmdfix3};${cmdfix4};${cmdfix5}" "${combined_name}" "${combined_name}"

    rm -vf "${v}_clm_"*.nc

    if [[ $? -ne 0 ]]; then
      cd "${script_dir}" || exit
      echo "ERROR (${error_num})" > "${prefix}.status"
      exit "${error_num}"
    fi
  done

  if [ -z "$( ls . )" ]; then
    echo "create_links_acyc_climo: ${ts_dir_destination} was not updated!"
  fi

  cd ..
}

{% if run_type == "model_vs_obs" %}
create_links_acyc_climo_obs() {
  local ts_dir_source="$1"
  local ts_dir_destination="$2"
  local begin_year="$3"
  local end_year="$4"
  local error_num="$5"

  local script_dir="{{ scriptDir }}"
  local prefix="{{ prefix }}"
  local dofm=(15.5 45 74.5 105 125.5 166 196.5 227.5 258 288.5 319 349.5)

  echo "create_links_acyc_climo_obs: linking from ${ts_dir_source} to ${ts_dir_destination}"

  mkdir -p "${ts_dir_destination}"
  cd "${ts_dir_destination}" || exit

  for file in ${ts_dir_source}/*; do
    local fname
    local YYYYS YYYYE
    local PREFIX
    local ttag tmp_file MM combined_name

    fname=$(basename "${file}")
    if [[ ! ${fname} =~ ".nc" ]]; then
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

    # Clip to specified year range
    if [[ ${YYYYS} -lt ${begin_year} ]]; then YYYYS=${begin_year}; fi
    if [[ ${YYYYE} -gt ${end_year} ]]; then YYYYE=${end_year}; fi

    # Extract prefix before the date range (removes from .${YYYYS} or -${YYYYS})
    PREFIX="${fname%%[._-]${YYYYS}*}"

    ttag="$(printf "%04d" "${YYYYS}")01-$(printf "%04d" "${YYYYE}")12"
    tmp_file="tmp_combine_${ttag}.nc"

    ncrcat -O -d time,"${YYYYS}-01-01","${YYYYE}-12-31" "${file}" "${tmp_file}"

    # Derive monthly climatology
    for month in $(seq 1 12); do
      MM=$(printf "%02d" ${month})
      ncra -O -h -F -d time,"${month}",,12 "${tmp_file}" "tmp_clm_${MM}.nc"
    done

    combined_name="${PREFIX}.${ttag}.AC.${case_id}.nc"
    ncrcat -O tmp_clm_*.nc "${combined_name}"

    # Adjust time metadata
    local cmdfix1='time[time]={15.5, 45, 74.5, 105, 125.5, 166, 196.5, 227.5, 258, 288.5,319, 349.5}'
    local cmdfix2='time@units="days since 1850-01-01 00:00:00"'
    local cmdfix3='time@calendar="noleap"'
    ncap2 -O -h -s "${cmdfix1};${cmdfix2};${cmdfix3}" "${combined_name}" "${combined_name}"

    local cmdfix4='defdim("bnds",2)'
    local cmdfix5='time_bnds=make_bounds(time,$bnds,"time_bnds")'
    local cmdfix6='time_bnds@units=time@units'
    local cmdfix7='time_bnds@calendar=time@calendar'
    ncap2 -O -h -s "${cmdfix4};${cmdfix5};${cmdfix6};${cmdfix7}" "${combined_name}" "${combined_name}"

    rm -vf tmp_*.nc

    if [[ $? -ne 0 ]]; then
      cd "${script_dir}" || exit
      echo "ERROR (${error_num})" > "${prefix}.status"
      exit "${error_num}"
    fi
  done

  if [ -z "$( ls . )" ]; then
    echo "create_links_acyc_climo_obs: ${ts_dir_destination} was not updated!"
  fi

  cd ..
}
{% endif %}
{% endif %}

{% if "variability_modes_cpl" in subsection
   or "variability_modes_atm" in subsection
   or "enso" in subsection %}
create_links_ts() {
  local ts_dir_source="$1"
  local ts_dir_destination="$2"
  local begin_year="$3"
  local end_year="$4"
  local subname="$5"
  local error_num="$6"

  local script_dir="{{ scriptDir }}"
  local prefix="{{ prefix }}"
  local vars="{{ vars }}"
  local ts_step="{{ ts_num_years }}"

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
      ncrcat -O -v "${v}" -d time,"${begin_year}-01-01","${end_year}-12-31" $(< "${v}_files.txt") "${combined_name}"

      # Add calendar attribute if missing
      if ! ncks -m "${combined_name}" | grep -q "calendar"; then
        echo "Adding missing calendar attribute to time..."
        ncatted -a calendar,time,o,c,"standard" "${combined_name}"
      fi

      # Add time bounds
      local cmdfix1='defdim("bnds",2)'
      local cmdfix2='time_bnds=make_bounds(time,$bnds,"time_bnds")'
      local cmdfix3='time_bnds@units=time@units'
      local cmdfix4='time_bnds@calendar=time@calendar'
      ncap2 -O -h -s "${cmdfix1};${cmdfix2};${cmdfix3};${cmdfix4}" "${combined_name}" "${combined_name}"

      if [[ $? -ne 0 ]]; then
        cd "${script_dir}" || exit
        echo "ERROR (${error_num})" > "${prefix}.status"
        exit "${error_num}"
      fi
    else
      echo "Warning: No input files found for variable ${v} in ${ts_dir_source}. Skipping."
    fi
  done

  if [ -z "$( ls . )" ]; then
    echo "create_links_ts: ${ts_dir_destination} was not updated!"
  fi

  cd ..
}

{% if run_type == "model_vs_obs" %}
create_links_ts_obs() {
  local ts_dir_source="$1"
  local ts_dir_destination="$2"
  local begin_year="$3"
  local end_year="$4"
  local error_num="$5"

  local script_dir="{{ scriptDir }}"
  local prefix="{{ prefix }}"

  echo "create_links_ts_obs: linking from ${ts_dir_source} to ${ts_dir_destination}"

  mkdir -p "${ts_dir_destination}"
  cd "${ts_dir_destination}" || exit

  local file fname PREFIX YYYYS YYYYE ttag combined_name

  for file in ${ts_dir_source}/*; do
    fname=$(basename "$file")
    echo "create_links_ts_obs: checking if nc file: ${fname}"
    if [[ ! ${fname} =~ ".nc" ]]; then
      # Skip non-.nc files
      continue
    fi
    echo "create_links_ts_obs: processing ${file}"
    # Match two time patterns (YYYYMM or YYYYMMDD) separated by _ or -
    if [[ ${fname} =~ ([0-9]{6,8})[_-]([0-9]{6,8}) ]]; then
      YYYYS="${BASH_REMATCH[1]}"
      YYYYE="${BASH_REMATCH[2]}"
    else
      echo "Warning: Could not extract dates from ${fname}, basename of ${file}"
      continue
    fi

    # Optional: clip years if needed
    if [[ ${YYYYS} -lt ${begin_year} ]]; then
      YYYYS="${begin_year}"
    fi

    if [[ ${YYYYE} -gt ${end_year} ]]; then
      YYYYE="${end_year}"
    fi

    # Extract prefix (before the date range, ignoring separator)
    PREFIX="${fname%%[._-]${YYYYS}*}"

    ttag="$(printf "%04d" "${YYYYS}")01-$(printf "%04d" "${YYYYE}")12"
    combined_name="${PREFIX}.${ttag}.nc"

    # Extract subset of time series
    ncrcat -O -d time,"${YYYYS}-01-01","${YYYYE}-12-31" "${file}" "${combined_name}"
    if [[ $? -ne 0 ]]; then
      cd "${script_dir}" || exit
      echo "ERROR (${error_num})" > "${prefix}.status"
      exit "${error_num}"
    fi
    echo "ncrcat successful"

    # Ensure time has calendar attribute
    if ! ncks -m "${combined_name}" | grep -q "calendar"; then
      echo "Adding missing calendar attribute to time..."
      ncatted -a calendar,time,o,c,"standard" "${combined_name}"
      if [[ $? -ne 0 ]]; then
        cd "${script_dir}" || exit
        echo "ERROR (${error_num})" > "${prefix}.status"
        exit "${error_num}"
      fi
      echo "ncatted successful"
    fi

    # Add time bounds
    local cmdfix1='defdim("bnds",2)'
    local cmdfix2='time_bnds=make_bounds(time,$bnds,"time_bnds")'
    local cmdfix3='time_bnds@units=time@units'
    local cmdfix4='time_bnds@calendar=time@calendar'
    ncap2 -O -h -s "${cmdfix1};${cmdfix2};${cmdfix3};${cmdfix4}" "${combined_name}" "${combined_name}"
    if [[ $? -ne 0 ]]; then
      cd "${script_dir}" || exit
      echo "ERROR (${error_num})" > "${prefix}.status"
      exit "${error_num}"
    fi
    echo "ncap2 successful"
  done

  if [ -z "$( ls . )" ]; then
    echo "create_links_ts_obs: ${ts_dir_destination} was not updated!"
    cd "${script_dir}" || exit
    echo "ERROR (${error_num})" > "${prefix}.status"
    exit "${error_num}"
  fi

  cd ..
}
{% endif %}
{% endif %}

########################
# Prepare the model data
########################
{% if "mean_climate" in subsection %}
# Define output directory for climatology files
climo_dir_primary="climo"
# Path to model's monthly climatology files
# TODO: how do we have cmip_ts under climo??
climo_dir_source="{{ output }}/post/atm/{{ grid }}/cmip_ts/monthly"
# Link and process primary model climo data
create_links_acyc_climo "${climo_dir_source}" "${climo_dir_primary}" "${Y1}" "${Y2}" "${model_name}.${tableID}" 1
{% if run_type == "model_vs_model" %}
# Path to reference model's climatology files
climo_dir_source_ref="{{ reference_data_path_ts }}"
climo_dir_ref="climo_ref"
# Link and process reference model climo data
create_links_acyc_climo "${climo_dir_source_ref}" "${climo_dir_ref}" "${ref_Y1}" "${ref_Y2}" "${model_name_ref}.${tableID_ref}" 2
{% endif %}
{% endif %}

{% if "variability_modes_cpl" in subsection or "variability_modes_atm" in subsection or "enso" in subsection %}
# All diagnostics in this subsection use time series (ts) data
# Define output directory for primary model time series
ts_dir_primary="ts"
ts_dir_source="{{ output }}/post/atm/{{ ts_grid }}/cmip_ts/monthly"
# Create local links and combine time series NetCDF files for the primary model
create_links_ts "${ts_dir_source}" "${ts_dir_primary}" "${Y1}" "${Y2}" "${model_name}.${tableID}" 3
{% if run_type == "model_vs_model" %}
# Define time series path for reference model (adjust for different year spans)
ts_dir_source_ref="{{ reference_data_path_ts }}"
ts_dir_ref="ts_ref"
# Create local links and combine ts files for the reference model
create_links_ts "${ts_dir_source_ref}" "${ts_dir_ref}" "${ref_Y1}" "${ref_Y2}" "${model_name_ref}.${tableID_ref}" 4
{% endif %}
{% endif %}

{% if run_type == "model_vs_obs" and "synthetic_plots" not in subsection %}
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

command="zi-pcmdi-link-observation --model_name_ref ${model_name_ref} --tableID_ref ${tableID_ref} --vars={{ vars }} --obs_sets {{ obs_sets }} --obs_ts {{ obs_ts }} --obstmp_dir ${obstmp_dir}"
echo "Running: ${command}"

source /gpfs/fs1/home/ac.forsyth2/miniforge3/etc/profile.d/conda.sh; conda activate zi-pcmdi-20250529
time eval "${command}"
source /lcrc/soft/climate/e3sm-unified/load_latest_e3sm_unified_chrysalis.sh

if [ $? -ne 0 ]; then
  cd {{ scriptDir }}
  echo "ERROR (6)" > {{ prefix }}.status
  exit 6
fi

#######################################################
# Now create obs climo and time series for PCMDI diags
# Use same period as test model when possible
#######################################################
ts_dir_ref_source="{{ scriptDir }}/${workdir}/${obstmp_dir}"

{% if "mean_climate" in subsection %}
climo_dir_ref=climo_ref
create_links_acyc_climo_obs "${ts_dir_ref_source}" "${climo_dir_ref}" ${ref_Y1} ${ref_Y2} 7
{% elif "variability_modes_cpl" in subsection or "variability_modes_atm" in subsection or "enso" in subsection %}
ts_dir_ref=ts_ref
create_links_ts_obs "${ts_dir_ref_source}" "${ts_dir_ref}" ${ref_Y1} ${ref_Y2} 8
{% endif %}

{% endif %}

{% if "synthetic_plots" not in subsection %}
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
plot_model = {{ mov_plot_model }}
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
    'sftlf.put_model_here.nc'
)

{% if "mean_climate" in subsection %}

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
    'put_model_here',
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

{% if "variability_modes" in subsection %}
# Setup for Mode Variability Diagnostics
msyear = int(start_yr)
meyear = int(end_yr)

# Seasons to analyze (comma-separated string to list)
seasons = '{{ seasons }}'.split(",")

# Data frequency (e.g., monthly, seasonal)
frequency = '{{ frequency }}'

# Variables to analyze (comma-separated string or space-separated)
varModel = '{{ vars }}'

# Unit conversion flags for model and observations
ModUnitsAdjust = {{ ModUnitsAdjust }}
ObsUnitsAdjust = {{ ObsUnitsAdjust }}

# Mask out land regions (consider ocean-only if True)
landmask = {{ landmask }}

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
    '{}.{}.put_model_here.%(realization).{}.%(variable).{}.nc'.format(
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

{% if "enso" in subsection %}
# Parameter Setup for ENSO Metrics
modnames = [product]
realization = realm

modpath = os.path.join(
    '${ts_dir_primary}',
    '{}.{}.put_model_here.%(realization).{}.%(variable).{}.nc'.format(
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
json_name = "%(mip)_%(exp)_%(metricsCollection)_${case_id}_put_model_here_%(realization)"

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

{% if "synthetic_plots" not in subsection %}
{% if "mean_climate" in subsection %}
source_dirs="--climo_ts_dir_primary ${climo_dir_primary} --climo_ts_dir_ref ${climo_dir_ref}"
{% elif "variability_modes" in subsection or "enso" in subsection %}
source_dirs="--climo_ts_dir_primary ${ts_dir_primary} --climo_ts_dir_ref ${ts_dir_ref}"
{% endif %}
# Parameter passing can encounter errors if parameters are empty.
# So, it's a good idea to make sure they can't be (or at least are unlikely to be) empty.
# run_type == "model_vs_obs" only: obs_sets (default value is NOT "")
# run_type == "model_vs_model" only: model_name_ref, tableID_ref (default values are NOT "")
core_parameters="--num_workers {{ num_workers }} --multiprocessing {{ multiprocessing }} --subsection {{ subsection }} ${source_dirs} --model_name ${model_name} --model_tableID {{model_tableID }} --figure_format {{ figure_format }}  --run_type {{ run_type }} --obs_sets {{ obs_sets }} --model_name_ref ${model_name_ref} --vars {{ vars }} --tableID_ref ${tableID_ref} --generate_sftlf {{ generate_sftlf }} --case_id ${case_id} --results_dir ${results_dir}"
{% endif %}

{% if "mean_climate" in subsection %}
command="zi-pcmdi-mean-climate ${core_parameters} --regions {{ regions }}"
{% endif %}
{% if "variability_modes" in subsection %}
{% if subsection == "variability_modes_atm" %}
var_modes={{ atm_modes }}
{% elif subsection == "variability_modes_cpl" %}
var_modes={{ cpl_modes }}
{% endif %}
command="zi-pcmdi-variability-modes ${core_parameters} --var_modes ${var_modes}"
{% endif %}
{% if "enso" in subsection %}
command="zi-pcmdi-enso ${core_parameters}  --enso_groups {{ enso_groups }}"
{% endif %}
{% if "synthetic_plots" in subsection %}
# Note: ts_years may be List[str]
command="zi-pcmdi-synthetic-plots --synthetic_sets {{ synthetic_sets }} --figure_format {{ figure_format }} --www ${www} --results_dir ${results_dir} --case {{ case }} --model_name {{ model_name }} --model_tableID {{model_tableID }} --web_dir=${web_dir} --cmip_clim_dir {{ cmip_clim_dir }} --cmip_clim_set {{ cmip_clim_set }} --cmip_movs_dir {{ cmip_movs_dir }} --cmip_movs_set {{ cmip_movs_set }} --atm_modes {{ atm_modes }} --cpl_modes {{ cpl_modes }} --cmip_enso_dir {{ cmip_enso_dir }} --cmip_enso_set {{ cmip_enso_set }} --sub_sets {{ sub_sets }} --pcmdi_webtitle {{ pcmdi_webtitle }} --pcmdi_version {{ pcmdi_version }} --run_type ${run_type} --ts_years {{ ts_years }} --pcmdi_external_prefix {{ pcmdi_external_prefix }} --pcmdi_viewer_template {{ pcmdi_viewer_template }}"
{% endif %}

# Run diagnostics
source /gpfs/fs1/home/ac.forsyth2/miniforge3/etc/profile.d/conda.sh; conda activate zi-pcmdi-20250529
echo "About to run a zi-pcmdi command"
echo "The current directory is: $PWD" # This will be of the form .../post/scripts/tmpDir
time ${command}
if [ $? != 0 ]; then
  cd {{ scriptDir }}
  echo 'ERROR (11)' > {{ prefix }}.status
  exit 11
fi
source /lcrc/soft/climate/e3sm-unified/load_latest_e3sm_unified_chrysalis.sh

#################################
# Copy output to web server
echo
echo ===== COPY FILES TO WEB SERVER =====
echo

# Create top-level directory
mkdir -p ${web_dir}
if [ $? != 0 ]; then
  cd {{ scriptDir }}
  echo 'ERROR (13)' > {{ prefix }}.status
  exit 13
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
{% if "synthetic_plots" not in subsection %}
rsync -a ${results_dir} ${web_dir}/
if [ $? != 0 ]; then
  cd {{ scriptDir }}
  echo 'ERROR (14)' > {{ prefix }}.status
  exit 14
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
