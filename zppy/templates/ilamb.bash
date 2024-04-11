#!/bin/bash
{% include 'slurm_header.sh' %}

{{ environment_commands }}

# Turn on debug output if needed
debug={{ debug }}
if [[ "${debug,,}" == "true" ]]; then
  set -x
fi

# Point to observation data
export ILAMB_ROOT={{ ilamb_obs }}

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
scriptDir="{{ scriptDir }}"

# Create temporary workdir
workdir=`mktemp -d tmp.${id}.XXXX`
workdir=${scriptDir}/${workdir}
model_root=${workdir}/model_data

if [ $short != "" ]; then
    case=${short}
fi

mkdir -p ${model_root}/${case}
cd ${model_root}/${case}

# Create output directory
# Create local links to input cmip time-series files
lnd_ts_for_ilamb={{ output }}/post/lnd/{{ ts_land_grid }}/cmip_ts/monthly/
atm_ts_for_ilamb={{ output }}/post/atm/{{ ts_atm_grid }}/cmip_ts/monthly/
cp -s ${lnd_ts_for_ilamb}/*_*_*_*_*_*_${Y1}??-${Y2}??.nc .
cp -s ${atm_ts_for_ilamb}/*_*_*_*_*_*_${Y1}??-${Y2}??.nc .
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
  echo 'ERROR (1)' > {{ prefix }}.status
  exit 1
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
  echo 'ERROR (2)' > {{ prefix }}.status
  exit 2
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
  echo 'ERROR (3)' > {{ prefix }}.status
  exit 3
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
