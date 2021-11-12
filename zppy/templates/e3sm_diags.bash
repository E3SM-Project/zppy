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
run_type="{{ run_type }}"
tag="{{ tag }}"

results_dir=${tag}_${Y1}-${Y2}

# Create temporary workdir
workdir=`mktemp -d tmp.${id}.XXXX`
cd ${workdir}

# Create local links to input climo files
climoDir={{ output }}/post/atm/{{ grid }}/clim/{{ '%dyr' % (year2-year1+1) }}
mkdir -p climo
cd climo
cp -s ${climoDir}/${case}_*_${Y1}??_${Y2}??_climo.nc .
cd ..

{%- if "diurnal_cycle" in sets %}
# Create local links to input diurnal cycle climo files
climoDir={{ output }}/post/atm/{{ grid }}/clim_{{ climo_diurnal_frequency }}/{{ '%dyr' % (year2-year1+1) }}
climoDirCopy=climo_{{ climo_diurnal_frequency }}
mkdir -p ${climoDirCopy}
cd ${climoDirCopy}
cp -s ${climoDir}/${case}.eam.h4_*_${Y1}??_${Y2}??_climo.nc .
cd ..
{%- endif %}

{%- if ("enso_diags" in sets) or ("qbo" in sets) or ("area_mean_time_series" in sets) %}
# Create xml files for time series variables
ts_dir={{ output }}/post/atm/{{ grid }}/ts/monthly/{{ '%dyr' % (ts_num_years) }}
mkdir -p ts_links
cd ts_links
# https://stackoverflow.com/questions/27702452/loop-through-a-comma-separated-shell-variable
variables="{{ vars }}"
for v in ${variables//,/ }
do
  # Go through the time series files for between year1 and year2, using a step size equal to the number of years per time series file
  for (( year=${y1}; year<=${y2}; year+={{ ts_num_years }} ))
  do
    YYYY=`printf "%04d" ${year}`
    for file in ${ts_dir}/${v}_${YYYY}*.nc
    do
      # Add this time series file to the list of files for cdscan to use
      echo ${file} >> ${v}_files.txt
    done
  done
  # xml file will cover the whole period from year1 to year2
  xml_name=${v}_${Y1}01_${Y2}12.xml
  export CDMS_NO_MPI=true
  cdscan -x ${xml_name} -f ${v}_files.txt
  if [ $? != 0 ]; then
      cd {{ scriptDir }}
      echo 'ERROR (1)' > {{ prefix }}.status
      exit 1
  fi
done
cd ..
{%- endif %}

{%- if "streamflow" in sets %}
rofDir="{{ output }}/post/rof/native/ts/monthly/{{ ts_num_years }}yr"
mkdir -p rof_links
cd rof_links
v="RIVER_DISCHARGE_OVER_LAND_LIQ"
xml_name=${v}_${Y1}01_${Y2}12.xml
cdscan -x ${xml_name} ${rofDir}/${v}_*.nc
cd ..
{%- endif %}

# Run E3SM Diags
echo
echo ===== RUN E3SM DIAGS model_vs_obs =====
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
test_ts = 'ts_links'
start_yr = int('${Y1}')
end_yr = int('${Y2}')
num_years = end_yr - start_yr + 1
{%- if ("enso_diags" in sets) or ("qbo" in sets) %}
ref_start_yr = {{ ref_start_yr }}
{%- endif %}

param = CoreParameter()

# Model
param.test_data_path = 'climo'
param.test_name = '${case}'
param.short_test_name = short_name

# Obs
param.reference_data_path = '{{ reference_data_path }}'

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
enso_param.reference_data_path = '{{ obs_ts }}'
enso_param.test_data_path = test_ts
enso_param.test_name = short_name
enso_param.test_start_yr = start_yr
enso_param.test_end_yr = end_yr
enso_param.ref_start_yr = ref_start_yr
enso_param.ref_end_yr = ref_start_yr + 10
params.append(enso_param)
{%- endif %}


{%- if "qbo" in sets %}
qbo_param = QboParameter()
qbo_param.reference_data_path = '{{ obs_ts }}'
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
params.append(qbo_param)
{%- endif %}


{%- if "area_mean_time_series" in sets %}
ts_param = AreaMeanTimeSeriesParameter()
ts_param.reference_data_path = '{{ obs_ts }}'
ts_param.test_data_path = test_ts
ts_param.test_name = short_name
ts_param.start_yr = start_yr
ts_param.end_yr = end_yr
params.append(ts_param)
{%- endif %}

{%- if "diurnal_cycle" in sets %}
dc_param = DiurnalCycleParameter()
dc_param.reference_data_path = '{{ dc_obs_climo }}'
dc_param.test_data_path = 'climo_{{ climo_diurnal_frequency }}'
dc_param.short_test_name = short_name
# Plotting diurnal cycle amplitude on different scales. Default is True
dc_param.normalize_test_amp = False
params.append(dc_param)
{%- endif %}

{%- if "streamflow" in sets %}
streamflow_param = StreamflowParameter()
streamflow_param.reference_data_path = '{{ streamflow_obs_ts }}'
streamflow_param.test_data_path = 'rof_links'
streamflow_param.test_name = short_name
streamflow_param.test_start_yr = start_yr
streamflow_param.test_end_yr = end_yr
streamflow_param.ref_start_yr = "1986" # Streamflow gauge station data range from year 1986 to 1995
streamflow_param.ref_end_yr = "1995"
params.append(streamflow_param)
{%- endif %}

{%- if "tc_analysis" in sets %}
tc_param = TCAnalysisParameter()
tc_param.reference_data_path = '{{ tc_obs }}'
tc_param.test_data_path = "{{ output }}/post/atm/tc/tc-analysis"
tc_param.short_test_name = "e3sm_v2"
tc_param.test_start_yr = start_yr
tc_param.test_end_yr = end_yr
# For model vs obs, the ref start and end year can be any four digit strings
# For now, use all available years from obs by default
tc_param.ref_start_yr = "1979"
tc_param.ref_end_yr = "2018"
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
command="python -u e3sm.py -d e3sm_diags.cfg"
{% else %}
command="python -u e3sm.py"
{% endif %}

# Run diagnostics
time ${command}
if [ $? != 0 ]; then
  cd {{ scriptDir }}
  echo 'ERROR (2)' > {{ prefix }}.status
  exit 2
fi

# Copy output to web server
echo
echo ===== COPY FILES TO WEB SERVER =====
echo

# Create top-level directory
f=${www}/${case}/e3sm_diags/{{ grid }}
mkdir -p ${f}
if [ $? != 0 ]; then
  cd {{ scriptDir }}
  echo 'ERROR (3)' > {{ prefix }}.status
  exit 3
fi

{% if machine == 'cori' %}
# For NERSC cori, make sure it is world readable
f=`realpath ${f}`
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
rsync -a --delete ${results_dir} ${www}/${case}/e3sm_diags/{{ grid }}/
if [ $? != 0 ]; then
  cd {{ scriptDir }}
  echo 'ERROR (4)' > {{ prefix }}.status
  exit 4
fi

{% if machine == 'cori' %}
# For NERSC cori, change permissions of new files
pushd ${www}/${case}/e3sm_diags/{{ grid }}/
chgrp -R e3sm ${results_dir}
chmod -R go+rX,go-w ${results_dir}
popd
{% endif %}

{% if machine in ['anvil', 'chrysalis'] %}
# For LCRC, change permissions of new files
pushd ${www}/${case}/e3sm_diags/{{ grid }}/
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
echo 'OK' > {{ prefix }}.status
exit 0
