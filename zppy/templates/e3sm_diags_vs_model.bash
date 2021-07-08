#!/bin/bash
{% include 'slurm_header.sh' %}
{{ environment_commands }}

# To load custom E3SM Diags environment, comment out line above using {# ... #}
# and uncomment lines below

#module load anaconda3/2019.03
#source /share/apps/anaconda3/2019.03/etc/profile.d/conda.sh
#conda activate e3sm_diags_env_dev

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
Y1="{{ '%04d' % (year1) }}"
Y2="{{ '%04d' % (year2) }}"
ref_Y1="{{ '%04d' % (ref_year1) }}"
ref_Y2="{{ '%04d' % (ref_year2) }}"
run_type="{{ run_type }}"
tag="{{ tag }}"

results_dir=${tag}_${Y1}-${Y2}

# Create temporary workdir
workdir=`mktemp -d tmp.${id}.XXXX`
cd ${workdir}

# Create local links to input climo files (test model)
climoDir={{ output }}/post/atm/{{ grid }}/clim/{{ '%dyr' % (year2-year1+1) }}
mkdir -p climo_test
cd climo_test
cp -s ${climoDir}/${case}_*_${Y1}??_${Y2}??_climo.nc .
cd ..

# Create local links to input climo files (ref model)
climoDir={{ reference_data_path }}/{{ '%dyr' % (ref_year2-ref_year1+1) }}
mkdir -p climo_ref
cd climo_ref
cp -s ${climoDir}/{{ ref_name }}_*_${ref_Y1}??_${ref_Y2}??_climo.nc .
cd ..

# Run E3SM Diags
echo
echo ===== RUN E3SM DIAGS model_vs_model =====
echo

# Prepare configuration file
cat > e3sm.py << EOF
import os
import numpy
from acme_diags.parameter.core_parameter import CoreParameter
from acme_diags.run import runner

param = CoreParameter()

# Model
param.test_data_path = 'climo_test'
param.test_name = '${case}'
param.short_test_name = '${short}'

# Reference
param.reference_data_path = 'climo_ref'
param.ref_name = ''
param.short_ref_name = '{{ short_ref_name }}'

# Output dir
param.results_dir = '${results_dir}'

# Additional settings
param.run_type = '{{ run_type }}'
param.diff_title = '{{ diff_title }}'
param.output_format = {{ output_format }}
param.output_format_subplot = {{ output_format_subplot }}
param.multiprocessing = {{ multiprocessing }}
param.num_workers = {{ num_workers }}

# Optionally, swap test and reference model
if {{ swap_test_ref }}:
    param.test_data_path, param.reference_data_path = param.reference_data_path, param.test_data_path
    param.test_name, param.ref_name = param.ref_name, param.test_name
    param.short_test_name, param.short_ref_name = param.short_ref_name, param.short_test_name

# Run
runner.sets_to_run = {{ sets }}
runner.run_diags([param])

EOF

# Run diagnostics
time python e3sm.py
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
f=${www}/${case}/e3sm_diags/{{ grid }}
mkdir -p ${f}
if [ $? != 0 ]; then
  cd {{ scriptDir }}
  echo 'ERROR (2)' > {{ prefix }}.status
  exit 1
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
  echo 'ERROR (3)' > {{ prefix }}.status
  exit 1
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
