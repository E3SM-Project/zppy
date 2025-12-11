#!/bin/bash
{% include 'inclusions/slurm_header.bash' %}
{% include 'inclusions/boilerplate.bash' %}
set -e
{{ environment_commands }}
set +e

# Point to observation data
export ILAMB_ROOT={{ ilamb_obs }}

# Basic definitions
case="{{ case }}"
short="{{ short_name }}"
www="{{ www }}"
y1={{ year1 }}
y2={{ year2 }}
Y1="{{ '%04d' % (year1) }}"
Y2="{{ '%04d' % (year2) }}"
scriptDir="{{ scriptDir }}"

# Create temporary workdir
hash=`mktemp --dry-run -d XXXX`
workdir=tmp.{{ prefix }}.${id}.${hash}
workdir=${scriptDir}/${workdir}
mkdir ${workdir}
model_root=${workdir}/model_data

if [ $short != "" ]; then
    case=${short}
fi

mkdir -p ${model_root}/${case}
cd ${model_root}/${case}

echo
echo ===== Copy nc files =====
echo

# Create output directory
# Create local links to input cmip time-series files
lnd_ts_for_ilamb={{ output }}/post/lnd/{{ ts_land_grid }}/cmip_ts/monthly/
{% if not land_only %}
atm_ts_for_ilamb={{ output }}/post/atm/{{ ts_atm_grid }}/cmip_ts/monthly/
{% endif %}
# Go through the time series files for between year1 and year2,
# using a step size equal to the number of years per time series file
start_year=$(echo $Y1 | sed 's/^0*//')
end_year=$(echo $Y2 | sed 's/^0*//')
for year in `seq $start_year {{ ts_num_years }} $end_year`;
do
  end_year_int=$((${year} + {{ ts_num_years }} - 1))
  start_year=`printf "%04d" ${year}`
  end_year=`printf "%04d" ${end_year_int}`
  echo "Copying files for ${start_year} to ${end_year}"
  cp -s ${lnd_ts_for_ilamb}/*_*_*_*_*_*_${start_year}??-${end_year}??.nc .
  if [ $? != 0 ]; then
    cd {{ scriptDir }}
    echo 'ERROR (1)' > {{ prefix }}.status
    exit 1
  fi
{% if not land_only %}
  cp -s ${atm_ts_for_ilamb}/*_*_*_*_*_*_${start_year}??-${end_year}??.nc .
  if [ $? != 0 ]; then
    cd {{ scriptDir }}
    echo 'ERROR (2)' > {{ prefix }}.status
    exit 2
  fi
{% endif %}
done
cd ../..

echo
echo ===== RUN ILAMB =====
echo

# Run diagnostics
# Not required TODO?
# TODO: find the mpi run format for different platforms

# include cfg file
cat > ilamb.cfg << EOF
{% include cfg %}
EOF

echo ${workdir}
echo {{ scriptDir }}

srun -N 1 ilamb-run --config ilamb.cfg --model_root $model_root  --regions global --model_year ${Y1} 2000

if [ $? != 0 ]; then
  cd {{ scriptDir }}
  echo 'ERROR (3)' > {{ prefix }}.status
  exit 3
fi

# Copy output to web server
echo
echo ===== COPY FILES TO WEB SERVER =====
echo

# Create top-level directory
web_dir=${www}/${case}/ilamb/{{ sub }}_${Y1}-${Y2}
mkdir -p ${web_dir}
if [ $? != 0 ]; then
  cd {{ scriptDir }}
  echo 'ERROR (4)' > {{ prefix }}.status
  exit 4
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
results_dir=_build/
rsync -a --delete ${results_dir} ${web_dir}/
if [ $? != 0 ]; then
  cd {{ scriptDir }}
  echo 'ERROR (5)' > {{ prefix }}.status
  exit 5
fi

{% if machine in ['pm-cpu', 'pm-gpu'] %}
# For NERSC, change permissions of new files
pushd ${web_dir}/
chgrp -R e3sm .
chmod -R go+rX,go-w .
popd
{% endif %}

{% if machine in ['anvil', 'chrysalis'] %}
# For LCRC, change permissions of new files
pushd ${web_dir}/
chmod -R go+rX,go-w .
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
