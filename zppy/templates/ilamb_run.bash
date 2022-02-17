#!/bin/bash
{% include 'slurm_header.sh' %}

{{ environment_commands }}

# Turn on debug output if needed
debug={{ debug }}
if [[ "${debug,,}" == "true" ]]; then
  set -x
fi

# Point to obsersvation data
# TODO: need to use a shared directory
export ILAMB_ROOT=/lcrc/group/e3sm/ac.zhang40/ilamb_data

# Script dir
cd {{ scriptDir }}

# Get jobid
id=${SLURM_JOBID}

# Update status file
STARTTIME=$(date +%s)
echo "RUNNING ${id}" > {{ prefix }}.status

# Basic definitions
case="{{ case }}"
www="{{ www }}"
y1={{ year1 }}
y2={{ year2 }}
Y1="{{ '%04d' % (year1) }}"
Y2="{{ '%04d' % (year2) }}"

# Create temporary workdir
workdir=`mktemp -d tmp.${id}.XXXX`
cd ${workdir}

# Create output directory
outdir=${www}/${case}/ilamb_results_${Y1}_${Y2}
mkdir -p ${outdir}


# Create local links to input cmip time-series files
lnd_ts_for_ilamb={{ output }}/post/lnd/180x360_aave/cmip_ts/monthly/
atm_ts_for_ilamb={{ output }}/post/atm/180x360_aave/cmip_ts/monthly/
mkdir -p ts_tmp
cd ts_tmp
#cp -s ${ts_for_ilamb}/${case}_*_${Y1}??_${Y2}??_climo.nc .
# TODO: renaming time-series files
cp -s ${lnd_ts_for_ilamb}/*_*_*_*_*_*_${Y1}??-${Y2}??.nc .
cp -s ${atm_ts_for_ilamb}/*_*_*_*_*_*_${Y1}??-${Y2}??.nc .

echo
echo ===== RUN ILAMB =====
echo
cd ${outdir}

# Run diagnostics
# Note --export=All is needed to make sure the executable is copied and executed  on the nodes.
# TODO: figure out how to best use cmip.cfg file
# TODO: find the mpi run format for different platforms
srun --export=ALL -N 1 ilamb-run --config /home/ac.zhang40/ILAMB/src/ILAMB/data/cmip.cfg --model_root ${workdir}/ts_tmp  --regions global
#srun --export=ALL -N 1 ilamb-run --config /home/ac.zhang40/ILAMB/src/ILAMB/data/cmip.cfg --model_root /lcrc/group/e3sm/ac.zhang40/ilamb_test_data --regions global

if [ $? != 0 ]; then
  cd {{ scriptDir }}
  echo 'ERROR (2)' > {{ prefix }}.status
  exit 2
fi

## Copy output to web server
#echo
#echo ===== COPY FILES TO WEB SERVER =====
#echo
#
## Create top-level directory
#f=${www}/${case}/e3sm_diags/{{ grid }}
#mkdir -p ${f}
#if [ $? != 0 ]; then
#  cd {{ scriptDir }}
#  echo 'ERROR (3)' > {{ prefix }}.status
#  exit 3
#fi

# Delete temporary workdir
cd ${workdir}
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
