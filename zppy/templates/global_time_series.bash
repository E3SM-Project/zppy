#!/bin/bash
{% include 'slurm_header.sh' %}
{{ environment_commands }}

# Turn on debug output if needed
debug={{ debug }}
if [[ "${debug,,}" == "true" ]]; then
  set -x
fi

# Get jobid
id=${SLURM_JOBID}

# Update status file
STARTTIME=$(date +%s)
cd {{ scriptDir }}
echo "RUNNING ${id}" > {{ prefix }}.status

# Generate global time series plots

# Names
moc_file={{ moc_file }}
experiment_name={{ experiment_name }}
figstr={{ figstr }}
case={{ case }}

# Years
start_yr={{ year1 }}
end_yr={{ year2 }}
ts_num_years={{ ts_num_years }}

# Paths
www={{ www }}
case_dir={{ output }}
global_ts_dir={{ global_time_series_dir }}

################################################################################

export CDMS_NO_MPI=true

use_atm={{ use_atm }}
use_lnd={{ use_lnd }}

use_ocn={{ use_ocn }}
if [[ ${use_ocn,,} == "true" ]]; then
    echo 'Create ocean time series'
    cd ${global_ts_dir}
    mkdir -p ${case_dir}/post/ocn/glb/ts/monthly/${ts_num_years}yr
    input={{ input }}/{{ input_subdir }}
    python ocean_month.py ${input} ${case_dir} ${start_yr} ${end_yr} ${ts_num_years}
    if [ $? != 0 ]; then
      cd {{ scriptDir }}
      echo 'ERROR (3)' > {{ prefix }}.status
      exit 3
    fi

    echo 'Copy moc file'
    cd ${case_dir}/post/analysis/mpas_analysis/cache/timeseries/moc
    cp ${moc_file} ../../../../../ocn/glb/ts/monthly/${ts_num_years}yr/
    if [ $? != 0 ]; then
      cd {{ scriptDir }}
      echo 'ERROR (5)' > {{ prefix }}.status
      exit 5
    fi

fi

echo 'Update time series figures'
cd ${global_ts_dir}
atmosphere_only={{ atmosphere_only }}
python coupled_global.py ${case_dir} ${experiment_name} ${figstr} ${start_yr} ${end_yr} {{ color }} ${ts_num_years} {{ plots_original }} ${atmosphere_only,,} {{ plots_atm }} {{ plots_ice }} {{ plots_lnd }} {{ plots_ocn }} {{ nrows }} {{ ncols }} {{ regions }}
if [ $? != 0 ]; then
  cd {{ scriptDir }}
  echo 'ERROR (6)' > {{ prefix }}.status
  exit 6
fi


echo 'Copy images to directory'
results_dir={{ prefix }}_results
results_dir_absolute_path={{ scriptDir }}/${results_dir}
mkdir -p ${results_dir_absolute_path}
cp *.pdf ${results_dir_absolute_path}
cp *.png ${results_dir_absolute_path}
cp -r viewer ${results_dir_absolute_path}

################################################################################
# Copy output to web server
echo
echo ===== COPY FILES TO WEB SERVER =====
echo

# Create top-level directory
f=${www}/${case}/global_time_series
mkdir -p ${f}
if [ $? != 0 ]; then
  cd {{ scriptDir }}
  echo 'ERROR (7)' > {{ prefix }}.status
  exit 7
fi

{% if machine in ['pm-cpu', 'pm-gpu'] %}
# For NERSC, make sure it is world readable
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
rsync -a --delete ${results_dir_absolute_path} ${www}/${case}/global_time_series
if [ $? != 0 ]; then
  cd {{ scriptDir }}
  echo 'ERROR (8)' > {{ prefix }}.status
  exit 8
fi

{% if machine in ['pm-cpu', 'pm-gpu'] %}
# For NERSC, change permissions of new files
pushd ${www}/${case}/global_time_series
chgrp -R e3sm ${results_dir}
chmod -R go+rX,go-w ${results_dir}
popd
{% endif %}

{% if machine in ['anvil', 'chrysalis'] %}
# For LCRC, change permissions of new files
pushd ${www}/${case}/global_time_series
chmod -R go+rX,go-w ${results_dir}
popd
{% endif %}

################################################################################
# Update status file and exit
{% raw %}
ENDTIME=$(date +%s)
ELAPSEDTIME=$(($ENDTIME - $STARTTIME))
{% endraw %}
echo ==============================================
echo "Elapsed time: $ELAPSEDTIME seconds"
echo ==============================================
cd {{ scriptDir }}
rm -f {{ prefix }}.status
echo 'OK' > {{ prefix }}.status
exit 0
