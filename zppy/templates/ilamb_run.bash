#!/bin/bash
{% include 'slurm_header.sh' %}

{{ environment_commands }}

# Turn on debug output if needed
debug={{ debug }}
if [[ "${debug,,}" == "true" ]]; then
  set -x
fi

# Point to obsersvation data
# TODO: need to update these data to other supported machines
export ILAMB_ROOT=/lcrc/group/acme/public_html/diagnostics/ilamb_data

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
lnd_ts_for_ilamb={{ output }}/post/lnd/180x360_aave/cmip_ts/monthly/
atm_ts_for_ilamb={{ output }}/post/atm/180x360_aave/cmip_ts/monthly/
cp -s ${lnd_ts_for_ilamb}/*_*_*_*_*_*_${Y1}??-${Y2}??.nc .
cp -s ${atm_ts_for_ilamb}/*_*_*_*_*_*_${Y1}??-${Y2}??.nc .
cd ../..

echo
echo ===== RUN ILAMB =====
echo

# Run diagnostics
# Note --export=All is needed to make sure the executable is copied and executed  on the nodes.
# TODO: find the mpi run format for different platforms

# include cfg file
cat > ilamb_run.cfg << EOF
{% include cfg %}
EOF

echo ${workdir}
echo {{ scriptDir }}

srun --export=ALL -N 1 ilamb-run --config ilamb_run.cfg --model_root $model_root  --regions global --model_year ${Y1} 2000

if [ $? != 0 ]; then
  cd {{ scriptDir }}
  echo 'ERROR (2)' > {{ prefix }}.status
  exit 2
fi

# Copy output to web server
echo
echo ===== COPY FILES TO WEB SERVER =====
echo

# TODO copy _build from $workdir to web server

## Create top-level directory
#f=${www}/${case}/ilamb/{{ grid }}
#mkdir -p ${f}
#if [ $? != 0 ]; then
#  cd {{ scriptDir }}
#  echo 'ERROR (3)' > {{ prefix }}.status
#  exit 3
#fi
#
## Delete temporary workdir
#cd ${workdir}
#cd ..
#if [[ "${debug,,}" != "true" ]]; then
#  rm -rf ${workdir}
#fi

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
