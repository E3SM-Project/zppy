#!/bin/bash
{% include 'inclusions/slurm_header.bash' %}

{# For SLURM, match CPU allocation to E3SM Diags multiprocessing. #}
{% set cpus_per_task = (num_workers if multiprocessing else 1) %}

{# Dane enforces step-level CPU/memory limits unless explicitly requested. #}
{% if machine == 'dane' %}
#SBATCH  --ntasks=1
#SBATCH  --cpus-per-task={{ cpus_per_task }}
#SBATCH  --mem=0
{% endif %}

{% include 'inclusions/boilerplate.bash' %}
set -e
{{ environment_commands }}
set +e

set_pkg_manager
echo "${pkg_manager} list e3sm_diags:"
${pkg_manager} list e3sm_diags || true # If we can't print this, just continue on.

# Make sure UVCDAT doesn't prompt us about anonymous logging
export UVCDAT_ANONYMOUS_LOG=False

# Basic definitions
case="{{ case }}"
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

results_dir={{ results_dir }}

# Create temporary workdir
hash=`mktemp --dry-run -d XXXX`
workdir=tmp.{{ prefix }}.${id}.${hash}
mkdir ${workdir}
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
  # Glob covers both EAM monthly (${case}_VAR_*) and EAMxx monthly (${case}.{stream}_VAR_*).
  cp -s ${climo_dir_source}/${nc_prefix}*_${begin_year}??_${end_year}??_climo.nc .
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
  cp -s ${climo_diurnal_dir_source}/${nc_prefix}.*_*_${begin_year}??_${end_year}??_climo.nc .
  if [ $? != 0 ]; then
    cd {{ scriptDir }}
    echo "ERROR (${error_num})" > {{ prefix }}.status
    exit ${error_num}
  fi
  cd ..
}

{%- if ("lat_lon_land" in sets) %}
climo_dir_primary_land={{ climo_dir_primary_land }}
# Create local links to input climo files
climo_dir_source={{ output }}/post/lnd/{{ grid }}/clim/{{ '%dyr' % (year2-year1+1) }}
create_links_climo ${climo_dir_source} ${climo_dir_primary_land} ${case} ${Y1} ${Y2} 1
{% if run_type == "model_vs_model" %}
# Create local links to input climo files (ref model)
climo_dir_source={{ reference_data_path }}/{{ '%dyr' % (ref_year2-ref_year1+1) }}
climo_dir_ref_land={{ climo_dir_ref_land }}
create_links_climo ${climo_dir_source} ${climo_dir_ref_land} {{ ref_name }} ${ref_Y1} ${ref_Y2} 2
{%- endif %}
{%- endif %}

{%- if ("lat_lon" in sets) or ("zonal_mean_xy" in sets) or ("zonal_mean_2d" in sets) or ("polar" in sets) or ("cosp_histogram" in sets) or ("meridional_mean_2d" in sets) or ("annual_cycle_zonal_mean" in sets) or ("zonal_mean_2d_stratosphere" in sets) %}
climo_dir_primary={{ climo_dir_primary }}
# Create local links to input climo files
climo_dir_source={{ output }}/post/atm/{{ grid }}/clim/{{ '%dyr' % (year2-year1+1) }}
create_links_climo ${climo_dir_source} ${climo_dir_primary} ${case} ${Y1} ${Y2} 3
{% if run_type == "model_vs_model" %}
# Create local links to input climo files (ref model)
climo_dir_source={{ reference_data_path }}/{{ '%dyr' % (ref_year2-ref_year1+1) }}
climo_dir_ref={{ climo_dir_ref }}
create_links_climo ${climo_dir_source} ${climo_dir_ref} {{ ref_name }} ${ref_Y1} ${ref_Y2} 4
{%- endif %}
{%- endif %}


{%- if "diurnal_cycle" in sets %}
climo_diurnal_dir_primary={{ climo_diurnal_dir_primary }}
# Create local links to input diurnal cycle climo files
climo_diurnal_dir_source={{ output }}/post/atm/{{ grid }}/clim_{{ climo_diurnal_frequency }}/{{ '%dyr' % (year2-year1+1) }}
create_links_climo_diurnal ${climo_diurnal_dir_source} ${climo_diurnal_dir_primary} ${case} ${Y1} ${Y2} 5
{% if run_type == "model_vs_model" %}
# Create local links to input climo files (ref model)
climo_diurnal_dir_source={{ reference_data_path_climo_diurnal }}/{{ '%dyr' % (ref_year2-ref_year1+1) }}
climo_diurnal_dir_ref={{ climo_diurnal_dir_ref }}
create_links_climo_diurnal ${climo_diurnal_dir_source} ${climo_diurnal_dir_ref} {{ ref_name }} ${ref_Y1} ${ref_Y2} 6
{%- endif %}
{%- endif %}

# Run E3SM Diags
echo
echo ===== RUN E3SM DIAGS =====
echo

# Copy the run script that zppy rendered next to this job script
cp {{ scriptDir }}/{{ prefix }}.py e3sm.py

# Handle cases when cfg file is explicitly provided
{% if cfg != "" %}
cat > e3sm_diags.cfg << EOF
{% include cfg %}
EOF
{% if machine == 'dane' %}
command="srun --ntasks=1 --cpus-per-task={{ cpus_per_task }} --cpu-bind=cores python -u e3sm.py -d e3sm_diags.cfg"
{% else %}
command="srun -n 1 python -u e3sm.py -d e3sm_diags.cfg"
{% endif %}
{% else %}
{% if machine == 'dane' %}
command="srun --ntasks=1 --cpus-per-task={{ cpus_per_task }} --cpu-bind=cores python -u e3sm.py"
{% else %}
command="srun -n 1 python -u e3sm.py"
{% endif %}
{% endif %}


# Run diagnostics
time ${command}
if [ $? != 0 ]; then
  cd {{ scriptDir }}
  echo 'ERROR (7)' > {{ prefix }}.status
  exit 7
fi

# Copy output to web server
echo
echo ===== COPY FILES TO WEB SERVER =====
echo

# Create top-level directory
web_dir=${www}/{{ default_case }}/e3sm_diags/{{ sub }}
mkdir -p ${web_dir}
if [ $? != 0 ]; then
  cd {{ scriptDir }}
  echo 'ERROR (8)' > {{ prefix }}.status
  exit 8
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
  echo 'ERROR (9)' > {{ prefix }}.status
  exit 9
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
