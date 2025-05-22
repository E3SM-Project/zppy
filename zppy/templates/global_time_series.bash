#!/bin/bash
{% include 'inclusions/slurm_header.bash' %}
{% include 'inclusions/boilerplate.bash' %}
{{ environment_commands }}

# Generate global time series plots
################################################################################
results_dir={{ prefix }}_results

zi-global-time-series --use_ocn {{ use_ocn }} --input {{ input }} --input_subdir {{ input_subdir }} --moc_file {{ moc_file }} --case_dir {{ output }} --experiment_name {{ experiment_name }} --figstr {{ figstr }} --color {{ color }} --ts_num_years {{ ts_num_years }} --plots_original {{ plots_original }} --plots_atm {{ plots_atm }} --plots_ice {{ plots_ice }} --plots_lnd {{ plots_lnd }} --plots_ocn {{ plots_ocn }} --nrows {{ nrows }} --ncols {{ ncols }} --results_dir ${results_dir} --regions {{ regions }} --make_viewer {{ make_viewer }} --start_yr {{ year1 }} --end_yr {{ year2 }}

results_dir_absolute_path={{ scriptDir }}/${results_dir}
# We are already in scriptDir so we don't have to copy files over to results_dir_absolute_path

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
