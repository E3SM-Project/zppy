#!/bin/bash
{% include 'inclusions/slurm_header.sh' %}
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
################################################################################

zppy-interfaces global-time-series --use_ocn={{ use_ocn }} --global_ts_dir={{ global_time_series_dir }} --input={{ input }} --input_subdir={{ input_subdir }}  --moc_file={{ moc_file }} --case_dir={{ output }} --experiment_name={{ experiment_name }} --figstr={{ figstr }} --color={{ color }} --ts_num_years={{ ts_num_years }} --plots_original={{ plots_original }} --atmosphere_only={{ atmosphere_only }} --plots_atm={{ plots_atm }} --plots_ice={{ plots_ice }} --plots_lnd={{ plots_lnd }} --plots_ocn={{ plots_ocn }} --regions={{ regions }} --start_yr={{ year1 }} --end_yr={{ year2 }}

echo 'Copy images to directory'
results_dir={{ prefix }}_results
results_dir_absolute_path={{ scriptDir }}/${results_dir}
mkdir -p ${results_dir_absolute_path}
cp *.pdf ${results_dir_absolute_path}
cp *.png ${results_dir_absolute_path}

################################################################################
case={{ case }}
www={{ www }}

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
