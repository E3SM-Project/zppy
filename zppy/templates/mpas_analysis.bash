#!/bin/bash
{% include 'inclusions/slurm_header.bash' %}
{% include 'inclusions/boilerplate.bash' %}
set -e
{{ environment_commands }}
set +e

set_pkg_manager
echo "${pkg_manager} list mpas-analysis:"
${pkg_manager} list mpas-analysis || true # If we can't print this, just continue on.

# Additional settings for MPAS-Analysis
export OMP_NUM_THREADS=1
export HDF5_USE_FILE_LOCKING=FALSE
ulimit -s unlimited 2>/dev/null || true

{% if machine == 'dane' %}
# MPAS-Analysis workaround on dane: avoid "Too many open files" failures by
# increasing the per-process open file descriptor limit (within the job's hard limit).
ulimit -n 65536 2>/dev/null || true
{% endif %}

# Basic definitions
case="{{ case }}"
www="{{ www }}"

# Job identifier
identifier={{ identifier }}
output_dir_name="{{ output_dir_name }}"

# Set-up work directory structure
echo
echo ===== SET UP MPAS-ANALYSIS DIRECTORY STRUCTURE =====
echo

workdir="{{ analysis_dir }}"
mkdir -p ${workdir}
cd ${workdir}

{% if purge == true %}
# If purge is on, delete previous directory
  rm -rf ${output_dir_name}
{% endif %}

mkdir -p ${output_dir_name}
mkdir -p cfg

{% if cache == true %}
# Restore cached copies of pre-computed files
cached=( "timeseries/moc" "timeseries/OceanBasins" "timeseries/transport" )
cache_dir="{{ scriptDir }}/../analysis/mpas_analysis/cache"
mkdir -p ${cache_dir}
for subdir in "${cached[@]}"
do
  mkdir -p ${cache_dir}/${subdir} ${output_dir_name}/${subdir}
  rsync -av ${cache_dir}/${subdir}/ ${output_dir_name}/${subdir}/
done
files=( "mpasIndexOcean.nc" "mpasTimeSeriesOcean.nc" "seaIceAreaVolNH.nc" "seaIceAreaVolSH.nc")
for file in "${files[@]}"
do
  cp ${cache_dir}/timeseries/${file} ${output_dir_name}/timeseries/${file}
done
{% endif %}

# Run MPAS-Analysis
echo
echo ===== RUN MPAS-ANALYSIS =====
echo

# Copy the config file that zppy rendered next to this job script
cp {{ scriptDir }}/{{ prefix }}.cfg cfg/mpas_analysis_${identifier}.cfg

# Run diagnostics
{% if purge == true %}
purge="--purge"
{% else %}
purge=""
{% endif %}

{% if campaign == 'cryosphere' %}
extra_config="--polar_regions"
{% else %}
extra_config=""
{% endif %}

# MPAS-Analysis appends to taskProgress.log rather than overwriting it, so
# ERROR lines from a previous (failed) run would make a successful rerun fail
# the check below. Set the old log aside so the check only sees this run.
task_progress_log=${output_dir_name}/logs/taskProgress.log
if [ -f ${task_progress_log} ]; then
  mv ${task_progress_log} ${task_progress_log}.$(date +%Y%m%d_%H%M%S)
fi

mpas_analysis ${purge} --verbose ${extra_config} cfg/mpas_analysis_${identifier}.cfg
if [ $? != 0 ]; then
  echo 'ERROR (1)' > {{ scriptDir }}/{{ prefix }}.status
  exit 1
fi

# Check master log for obvious errors
size=`wc -c ${task_progress_log} | awk '{print $1}'`
error=`grep ERROR ${task_progress_log} | wc -l`
if [ "${size}" = "" ] || [ "${size}" = "0" ] || [ "${error}" != "0" ];then
  echo 'ERROR (2)' > {{ scriptDir }}/{{ prefix }}.status
  exit 2
fi

{% if cache == true %}
# Cache copies of selected files
echo
echo ===== CACHE OUTPUT FILES =====
echo
for file in "${files[@]}"
do
  cp ${output_dir_name}/timeseries/${file} ${cache_dir}/timeseries/${file}
done
for subdir in "${cached[@]}"
do
  rsync -av ${output_dir_name}/${subdir}/ ${cache_dir}/${subdir}/
done
# Remove one particularly large file which does not need to be cached
rm ${output_dir_name}/timeseries/mpasTimeSeriesSeaIce.nc
{% endif %}

# Copy output to web server
echo
echo ===== COPY FILES TO WEB SERVER =====
echo

# Create top-level directory
f=${www}/${case}/{{ analysis_subdir }}/{{ comparison_type }}/${output_dir_name}/
mkdir -p ${f}
if [ $? != 0 ]; then
  echo 'ERROR (3)' > {{ scriptDir }}/{{ prefix }}.status
  exit 3
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
rsync -a --delete ${output_dir_name}/html/ ${www}/${case}/{{ analysis_subdir }}/{{ comparison_type }}/${output_dir_name}/
if [ $? != 0 ]; then
  echo 'ERROR (4)' > {{ scriptDir }}/{{ prefix }}.status
  exit 4
fi

{% if machine in ['pm-cpu', 'pm-gpu'] %}
# For NERSC, change permissions of new files
pushd ${www}/${case}/{{ analysis_subdir }}/{{ comparison_type }}/
chgrp -R e3sm ${output_dir_name}
chmod -R go+rX,go-w ${output_dir_name}
popd
{% endif %}

{% if machine in ['anvil', 'chrysalis'] %}
# For LCRC, change permissions of new files
pushd ${www}/${case}/{{ analysis_subdir }}/{{ comparison_type }}/
chmod -R go+rX,go-w ${output_dir_name}
popd
{% endif %}

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
