#!/bin/bash
{% include 'slurm_header.sh' %}

{{ environment_commands }}

# Turn on debug output if needed
debug={{ debug }}
if [[ "${debug,,}" == "true" ]]; then
  set -x
fi

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
short="{{ short_name }}"
www="{{ www }}"
y1={{ year1 }}
y2={{ year2 }}
Y1="{{ '%04d' % (year1) }}"
Y2="{{ '%04d' % (year2) }}"
{% if run_type == "model_vs_model" %}
ref_Y1="{{ '%04d' % (ref_year1) }}"
ref_Y2="{{ '%04d' % (ref_year2) }}"
{%- endif %}
run_type="{{ run_type }}"
tag="{{ tag }}"

results_dir=${tag}_${Y1}-${Y2}

# Create temporary workdir
workdir=`mktemp -d tmp.${id}.XXXX`
cd ${workdir}

create_links_climo()
{
  climo_dir_source=$1
  climo_dir_destination=$2
  nc_prefix=$3
  begin_year=$4
  end_year=$5
  error_num=$6
  mkdir -p ${climo_dir_destination}
  cd ${climo_dir_destination}
  cp -s ${climo_dir_source}/${nc_prefix}_*_${begin_year}??_${end_year}??_climo.nc .
  if [ $? != 0 ]; then
    cd {{ scriptDir }}
    echo "ERROR (${error_num})" > {{ prefix }}.status
    exit ${error_num}
  fi
  cd ..
}

create_links_climo_diurnal()
{
  climo_diurnal_dir_source=$1
  climo_diurnal_dir_destination=$2
  nc_prefix=$3
  begin_year=$4
  end_year=$5
  error_num=$6
  mkdir -p ${climo_diurnal_dir_destination}
  cd ${climo_diurnal_dir_destination}
  cp -s ${climo_diurnal_dir_source}/${nc_prefix}.{{ climo_diurnal_input_files }}_*_${begin_year}??_${end_year}??_climo.nc .
  if [ $? != 0 ]; then
    cd {{ scriptDir }}
    echo "ERROR (${error_num})" > {{ prefix }}.status
    exit ${error_num}
  fi
  cd ..
}

create_links_ts()
{
  ts_dir_source=$1
  ts_dir_destination=$2
  begin_year=$3
  end_year=$4
  error_num=$5
  # Create xml files for time series variables
  mkdir -p ${ts_dir_destination}
  cd ${ts_dir_destination}
  # https://stackoverflow.com/questions/27702452/loop-through-a-comma-separated-shell-variable
  variables="{{ vars }}"
  for v in ${variables//,/ }
  do
    # Go through the time series files for between year1 and year2, using a step size equal to the number of years per time series file
    for year in `seq ${begin_year} {{ ts_num_years }} ${end_year}`;
    do
      YYYY=`printf "%04d" ${year}`
      for file in ${ts_dir_source}/${v}_${YYYY}*.nc
      do
        # Add this time series file to the list of files for cdscan to use
        echo ${file} >> ${v}_files.txt
      done
    done
    # xml file will cover the whole period from year1 to year2
    xml_name=${v}_${begin_year}01_${end_year}12.xml
    export CDMS_NO_MPI=true
    cdscan -x ${xml_name} -f ${v}_files.txt
    if [ $? != 0 ]; then
      cd {{ scriptDir }}
      echo "ERROR (${error_num})" > {{ prefix }}.status
      exit ${error_num}
    fi
  done
  cd ..
}

create_links_ts_rof()
{
  ts_rof_dir_source=$1
  ts_rof_dir_destination=$2
  begin_year=$3
  end_year=$4
  error_num=$5
  mkdir -p ${ts_rof_dir_destination}
  cd ${ts_rof_dir_destination}
  v="RIVER_DISCHARGE_OVER_LAND_LIQ"
  xml_name=${v}_${begin_year}01_${end_year}12.xml
  cdscan -x ${xml_name} ${ts_rof_dir_source}/${v}_*.nc
  if [ $? != 0 ]; then
    cd {{ scriptDir }}
    echo "ERROR (${error_num})" > {{ prefix }}.status
    exit ${error_num}
  fi
  cd ..
}

{%- if ("lat_lon" in sets) or ("zonal_mean_xy" in sets) or ("zonal_mean_2d" in sets) or ("polar" in sets) or ("cosp_histogram" in sets) or ("meridional_mean_2d" in sets) or ("annual_cycle_zonal_mean" in sets) or ("zonal_mean_2d_stratosphere" in sets) %}
{% if run_type == "model_vs_obs" %}
climo_dir_primary=climo
{% elif run_type == "model_vs_model" %}
climo_dir_primary=climo_test
{%- endif %}
# Create local links to input climo files
climo_dir_source={{ output }}/post/atm/{{ grid }}/clim/{{ '%dyr' % (year2-year1+1) }}
create_links_climo ${climo_dir_source} ${climo_dir_primary} ${case} ${Y1} ${Y2} 1
{% if run_type == "model_vs_model" %}
# Create local links to input climo files (ref model)
climo_dir_source={{ reference_data_path }}/{{ '%dyr' % (ref_year2-ref_year1+1) }}
climo_dir_ref=climo_ref
create_links_climo ${climo_dir_source} ${climo_dir_ref} {{ ref_name }} ${ref_Y1} ${ref_Y2} 2
{%- endif %}
{%- endif %}

{%- if "diurnal_cycle" in sets %}
{% if run_type == "model_vs_obs" %}
climo_diurnal_dir_primary=climo_{{ climo_diurnal_frequency }}
{% elif run_type == "model_vs_model" %}
climo_diurnal_dir_primary=climo_{{ climo_diurnal_frequency }}_test
{%- endif %}
# Create local links to input diurnal cycle climo files
climo_diurnal_dir_source={{ output }}/post/atm/{{ grid }}/clim_{{ climo_diurnal_frequency }}/{{ '%dyr' % (year2-year1+1) }}
create_links_climo_diurnal ${climo_diurnal_dir_source} ${climo_diurnal_dir_primary} ${case} ${Y1} ${Y2} 3
{% if run_type == "model_vs_model" %}
# Create local links to input climo files (ref model)
climo_diurnal_dir_source={{ reference_data_path_climo_diurnal }}/{{ '%dyr' % (ref_year2-ref_year1+1) }}
climo_diurnal_dir_ref=climo_diurnal_ref
create_links_climo_diurnal ${climo_diurnal_dir_source} ${climo_diurnal_dir_ref} {{ ref_name }} ${ref_Y1} ${ref_Y2} 4
{%- endif %}
{%- endif %}

{%- if ("enso_diags" in sets) or ("qbo" in sets) or ("area_mean_time_series" in sets) %}
{% if run_type == "model_vs_obs" %}
ts_dir_primary=ts
{% elif run_type == "model_vs_model" %}
ts_dir_primary=ts_test
{%- endif %}
# Create xml files for time series variables
ts_dir_source={{ output }}/post/atm/{{ grid }}/ts/monthly/{{ '%dyr' % (ts_num_years) }}
create_links_ts ${ts_dir_source} ${ts_dir_primary} ${Y1} ${Y2} 5
{% if run_type == "model_vs_model" %}
ts_dir_source={{ reference_data_path_ts }}/{{ ts_num_years_ref }}yr
ts_dir_ref=ts_ref
create_links_ts ${ts_dir_source} ${ts_dir_ref} ${ref_Y1} ${ref_Y2} 6
{%- endif %}
{%- endif %}

{%- if "streamflow" in sets %}
{% if run_type == "model_vs_obs" %}
ts_rof_dir_primary=rof
{% elif run_type == "model_vs_model" %}
ts_rof_dir_primary=rof_test
{%- endif %}
ts_rof_dir_source="{{ output }}/post/rof/native/ts/monthly/{{ ts_num_years }}yr"
create_links_ts_rof ${ts_rof_dir_source} ${ts_rof_dir_primary} ${Y1} ${Y2} 7
{% if run_type == "model_vs_model" %}
ts_rof_dir_source={{ reference_data_path_ts_rof }}/{{ ts_num_years_ref }}yr
ts_rof_dir_ref=ts_rof_ref
create_links_ts_rof ${ts_rof_dir_source} ${ts_rof_dir_ref} ${ref_Y1} ${ref_Y2} 8
{%- endif %}
{%- endif %}

{% if run_type == "model_vs_obs" %}
ref_name={{ ref_name }}
{%- endif %}
{% if (run_type == "model_vs_model") and keep_mvm_case_name_in_fig %}
ref_name={{ ref_name }}
{%- endif %}
{% if (run_type == "model_vs_model") and not keep_mvm_case_name_in_fig %}
ref_name=""
{%- endif %}

# Run E3SM Diags
echo
echo ===== RUN E3SM DIAGS =====
echo

# Prepare configuration file
cat > e3sm.py << EOF
import os
import numpy
{%- if "area_mean_time_series" in sets %}
from e3sm_diags.parameter.area_mean_time_series_parameter import AreaMeanTimeSeriesParameter
{%- endif %}
from e3sm_diags.parameter.core_parameter import CoreParameter
{%- if "diurnal_cycle" in sets %}
from e3sm_diags.parameter.diurnal_cycle_parameter import DiurnalCycleParameter
{%- endif %}
{%- if "enso_diags" in sets %}
from e3sm_diags.parameter.enso_diags_parameter import EnsoDiagsParameter
{%- endif %}
{%- if "qbo" in sets %}
from e3sm_diags.parameter.qbo_parameter import QboParameter
{%- endif %}
{%- if "streamflow" in sets %}
from e3sm_diags.parameter.streamflow_parameter import StreamflowParameter
{%- endif %}
{%- if "tc_analysis" in sets %}
from e3sm_diags.parameter.tc_analysis_parameter import TCAnalysisParameter
{%- endif %}


from e3sm_diags.run import runner

short_name = '${short}'
test_ts = '${ts_dir_primary}'
start_yr = int('${Y1}')
end_yr = int('${Y2}')
num_years = end_yr - start_yr + 1
{%- if ("enso_diags" in sets) or ("qbo" in sets) %}
ref_start_yr = {{ ref_start_yr }}
{%- endif %}

param = CoreParameter()

# Model
{%- if ("lat_lon" in sets) or ("zonal_mean_xy" in sets) or ("zonal_mean_2d" in sets) or ("polar" in sets) or ("cosp_histogram" in sets) or ("meridional_mean_2d" in sets) or ("annual_cycle_zonal_mean" in sets) or ("zonal_mean_2d_stratosphere" in sets) %}
param.test_data_path = '${climo_dir_primary}'
{%- endif %}
param.test_name = '${case}'
param.short_test_name = short_name

{%- if ("lat_lon" in sets) or ("zonal_mean_xy" in sets) or ("zonal_mean_2d" in sets) or ("polar" in sets) or ("cosp_histogram" in sets) or ("meridional_mean_2d" in sets) or ("annual_cycle_zonal_mean" in sets) or ("zonal_mean_2d_stratosphere" in sets) %}
{% if run_type == "model_vs_obs" %}
# Obs
param.reference_data_path = '{{ reference_data_path }}'
{% elif run_type == "model_vs_model" %}
# Reference
param.reference_data_path = '${climo_dir_ref}'
param.ref_name = '${ref_name}'
param.short_ref_name = '{{ short_ref_name }}'
# Optionally, swap test and reference model
if {{ swap_test_ref }}:
   param.test_data_path, param.reference_data_path = param.reference_data_path, param.test_data_path
   param.test_name, param.ref_name = param.ref_name, param.test_name
   param.short_test_name, param.short_ref_name = param.short_ref_name, param.short_test_name
{%- endif %}
{%- endif %}

# Output dir
param.results_dir = '${results_dir}'

# Additional settings
param.run_type = '{{ run_type }}'
param.diff_title = '{{ diff_title }}'
param.output_format = {{ output_format }}
param.output_format_subplot = {{ output_format_subplot }}
param.multiprocessing = {{ multiprocessing }}
param.num_workers = {{ num_workers }}
#param.fail_on_incomplete = True
params = [param]

{%- if "enso_diags" in sets %}
enso_param = EnsoDiagsParameter()
enso_param.test_data_path = test_ts
enso_param.test_name = short_name
enso_param.test_start_yr = start_yr
enso_param.test_end_yr = end_yr
{% if run_type == "model_vs_obs" %}
# Obs
enso_param.reference_data_path = '{{ obs_ts }}'
enso_param.ref_start_yr = ref_start_yr
enso_param.ref_end_yr = ref_start_yr + 10
{% elif run_type == "model_vs_model" %}
# Reference
enso_param.reference_data_path = '${ts_dir_ref}'
enso_param.ref_name = '${ref_name}'
enso_param.short_ref_name = '{{ short_ref_name }}'
enso_param.ref_start_yr = '{{ ref_start_yr }}'
enso_param.ref_end_yr = '{{ ref_final_yr }}'
# Optionally, swap test and reference model
if {{ swap_test_ref }}:
   enso_param.test_data_path, enso_param.reference_data_path = enso_param.reference_data_path, enso_param.test_data_path
   enso_param.test_name, enso_param.ref_name = enso_param.ref_name, enso_param.test_name
   enso_param.short_test_name, enso_param.short_ref_name = enso_param.short_ref_name, enso_param.short_test_name
{%- endif %}
params.append(enso_param)
{%- endif %}


{%- if "qbo" in sets %}
qbo_param = QboParameter()
qbo_param.test_data_path = test_ts
qbo_param.test_name = short_name
qbo_param.test_start_yr = start_yr
qbo_param.test_end_yr = end_yr
qbo_param.ref_start_yr = ref_start_yr
ref_end_yr = ref_start_yr + num_years - 1
if (ref_end_yr <= {{ ref_final_yr }}):
  qbo_param.ref_end_yr = ref_end_yr
else:
  qbo_param.ref_end_yr = {{ ref_final_yr }}
{% if run_type == "model_vs_obs" %}
# Obs
qbo_param.reference_data_path = '{{ obs_ts }}'
{% elif run_type == "model_vs_model" %}
# Reference
qbo_param.reference_data_path = '${ts_dir_ref}'
qbo_param.ref_name = '${ref_name}'
qbo_param.short_ref_name = '{{ short_ref_name }}'
# Optionally, swap test and reference model
if {{ swap_test_ref }}:
   qbo_param.test_data_path, qbo_param.reference_data_path = qbo_param.reference_data_path, qbo_param.test_data_path
   qbo_param.test_name, qbo_param.ref_name = qbo_param.ref_name, qbo_param.test_name
   qbo_param.short_test_name, qbo_param.short_ref_name = qbo_param.short_ref_name, qbo_param.short_test_name
{%- endif %}
params.append(qbo_param)
{%- endif %}


{%- if "area_mean_time_series" in sets %}
ts_param = AreaMeanTimeSeriesParameter()
ts_param.test_data_path = test_ts
ts_param.test_name = short_name
ts_param.start_yr = start_yr
ts_param.end_yr = end_yr
{% if run_type == "model_vs_obs" %}
# Obs
ts_param.reference_data_path = '{{ obs_ts }}'
{% elif run_type == "model_vs_model" %}
# Reference
ts_param.reference_data_path = '${ts_dir_ref}'
ts_param.ref_name = '${ref_name}'
ts_param.short_ref_name = '{{ short_ref_name }}'
# Optionally, swap test and reference model
if {{ swap_test_ref }}:
   ts_param.test_data_path, ts_param.reference_data_path = ts_param.reference_data_path, ts_param.test_data_path
   ts_param.test_name, ts_param.ref_name = ts_param.ref_name, ts_param.test_name
   ts_param.short_test_name, ts_param.short_ref_name = ts_param.short_ref_name, ts_param.short_test_name
{%- endif %}
params.append(ts_param)
{%- endif %}

{%- if "diurnal_cycle" in sets %}
dc_param = DiurnalCycleParameter()
dc_param.test_data_path = '${climo_diurnal_dir_primary}'
dc_param.short_test_name = short_name
# Plotting diurnal cycle amplitude on different scales. Default is True
dc_param.normalize_test_amp = False
{% if run_type == "model_vs_obs" %}
# Obs
dc_param.reference_data_path = '{{ dc_obs_climo }}'
{% elif run_type == "model_vs_model" %}
# Reference
dc_param.reference_data_path = '${climo_diurnal_dir_ref}'
dc_param.ref_name = '${ref_name}'
dc_param.short_ref_name = '{{ short_ref_name }}'
# Optionally, swap test and reference model
if {{ swap_test_ref }}:
   dc_param.test_data_path, dc_param.reference_data_path = dc_param.reference_data_path, dc_param.test_data_path
   dc_param.test_name, dc_param.ref_name = dc_param.ref_name, dc_param.test_name
   dc_param.short_test_name, dc_param.short_ref_name = dc_param.short_ref_name, dc_param.short_test_name
{%- endif %}
params.append(dc_param)
{%- endif %}

{%- if "streamflow" in sets %}
streamflow_param = StreamflowParameter()
streamflow_param.reference_data_path = '{{ streamflow_obs_ts }}'
streamflow_param.test_data_path = '${ts_rof_dir_primary}'
streamflow_param.test_name = short_name
streamflow_param.test_start_yr = start_yr
streamflow_param.test_end_yr = end_yr
{% if run_type == "model_vs_obs" %}
# Obs
streamflow_param.reference_data_path = '{{ streamflow_obs_ts }}'
streamflow_param.ref_start_yr = "1986" # Streamflow gauge station data range from year 1986 to 1995
streamflow_param.ref_end_yr = "1995"
{% elif run_type == "model_vs_model" %}
# Reference
streamflow_param.reference_data_path = '${ts_rof_dir_ref}'
streamflow_param.ref_name = '${ref_name}'
streamflow_param.short_ref_name = '{{ short_ref_name }}'
streamflow_param.ref_start_yr = '{{ ref_start_yr }}'
streamflow_param.ref_end_yr = '{{ ref_final_yr }}'
streamflow_param.gauges_path = '{{ gauges_path }}'
# Optionally, swap test and reference model
if {{ swap_test_ref }}:
   streamflow_param.test_data_path, streamflow_param.reference_data_path = streamflow_param.reference_data_path, streamflow_param.test_data_path
   streamflow_param.test_name, streamflow_param.ref_name = streamflow_param.ref_name, streamflow_param.test_name
   streamflow_param.short_test_name, streamflow_param.short_ref_name = streamflow_param.short_ref_name, streamflow_param.short_test_name
{%- endif %}
params.append(streamflow_param)
{%- endif %}

{%- if "tc_analysis" in sets %}
tc_param = TCAnalysisParameter()
tc_param.test_data_path = "{{ output }}/post/atm/tc-analysis_${Y1}_${Y2}"
tc_param.short_test_name = short_name
tc_param.test_start_yr = "${Y1}"
tc_param.test_end_yr = "${Y2}"
{% if run_type == "model_vs_obs" %}
# Obs
tc_param.reference_data_path = '{{ tc_obs }}'
# For model vs obs, the ref start and end year can be any four digit strings
# For now, use all available years from obs by default
tc_param.ref_start_yr = "1979"
tc_param.ref_end_yr = "2018"
{% elif run_type == "model_vs_model" %}
# Reference
tc_param.reference_data_path = '{{ reference_data_path_tc }}'
tc_param.ref_name = '${ref_name}'
tc_param.short_ref_name = '{{ short_ref_name }}'
tc_param.ref_start_yr = '{{ ref_start_yr }}'
tc_param.ref_end_yr = '{{ ref_final_yr }}'
# Optionally, swap test and reference model
if {{ swap_test_ref }}:
   tc_param.test_data_path, tc_param.reference_data_path = tc_param.reference_data_path, tc_param.test_data_path
   tc_param.test_name, tc_param.ref_name = tc_param.ref_name, tc_param.test_name
   tc_param.short_test_name, tc_param.short_ref_name = tc_param.short_ref_name, tc_param.short_test_name
{%- endif %}
params.append(tc_param)
{%- endif %}

# Run
runner.sets_to_run = {{ sets }}
runner.run_diags(params)

EOF

# Handle cases when cfg file is explicitly provided
{% if cfg != "" %}
cat > e3sm_diags.cfg << EOF
{% include cfg %}
EOF
command="srun -n 1 python -u e3sm.py -d e3sm_diags.cfg"
{% else %}
command="srun -n 1 python -u e3sm.py"
{% endif %}

# Run diagnostics
time ${command}
if [ $? != 0 ]; then
  cd {{ scriptDir }}
  echo 'ERROR (9)' > {{ prefix }}.status
  exit 9
fi

# Copy output to web server
echo
echo ===== COPY FILES TO WEB SERVER =====
echo

# Create top-level directory
web_dir=${www}/${case}/e3sm_diags/{{ sub }}
mkdir -p ${web_dir}
if [ $? != 0 ]; then
  cd {{ scriptDir }}
  echo 'ERROR (10)' > {{ prefix }}.status
  exit 10
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

# Copy files
rsync -a --delete ${results_dir} ${web_dir}/
if [ $? != 0 ]; then
  cd {{ scriptDir }}
  echo 'ERROR (11)' > {{ prefix }}.status
  exit 11
fi

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
