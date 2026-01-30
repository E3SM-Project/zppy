#!/bin/bash
{% include 'inclusions/slurm_header.bash' %}
{% include 'inclusions/boilerplate.bash' %}
set -e
{{ environment_commands }}
set +e

# Generate water and energy budget analysis plots
################################################################################

# Create temporary workdir
hash=`mktemp --dry-run -d XXXX`
workdir=tmp.{{ prefix }}.${id}.${hash}
mkdir ${workdir}
cd ${workdir}
echo "Working in temporary directory: ${workdir}"

# Execute budget analysis using external CLI tool
echo "Running budget analysis for years {{ year1 }} to {{ year2 }}..."

# Construct log path from zppy parameters
LOG_PATH="{{ input }}/{{ case }}/archive/logs"

zi-budget-analysis \
  --log_path "${LOG_PATH}" \
  --start_year {{ year1 }} \
  --end_year {{ year2 }} \
  --budget_types {{ budget_types }} \
{%- if output_html %}
  --output_html \
{%- endif %}
{%- if output_ascii %}
  --output_ascii \
{%- endif %}
  --output_dir .

if [ $? != 0 ]; then
  cd {{ scriptDir }}
  echo 'ERROR (1)' > {{ prefix }}.status
  exit 1
fi

# Copy results to case directory
echo
echo "===== COPY RESULTS TO CASE DIRECTORY ====="
echo

case_dir={{ output }}
dest_dir=${case_dir}/post/budget/{{ year1 }}-{{ year2 }}
mkdir -p ${dest_dir}
if [ $? != 0 ]; then
  cd {{ scriptDir }}
  echo 'ERROR (2)' > {{ prefix }}.status
  exit 2
fi

# Copy all generated files
cp *.html ${dest_dir}/ 2>/dev/null || true
cp *.txt ${dest_dir}/ 2>/dev/null || true
cp *.png ${dest_dir}/ 2>/dev/null || true

echo "Results copied to ${dest_dir}/"

# Copy output to web server
echo
echo "===== COPY FILES TO WEB SERVER ====="
echo

# Create web directory
www={{ www }}
case={{ case }}
web_dir=${www}/${case}/budget/{{ year1 }}-{{ year2 }}
mkdir -p ${web_dir}
if [ $? != 0 ]; then
  cd {{ scriptDir }}
  echo 'ERROR (3)' > {{ prefix }}.status
  exit 3
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

# Copy HTML files for web viewing
cp *.html ${web_dir}/ 2>/dev/null || true
if [ $? != 0 ]; then
  cd {{ scriptDir }}
  echo 'ERROR (4)' > {{ prefix }}.status
  exit 4
fi

{% if machine in ['pm-cpu', 'pm-gpu'] %}
# For NERSC, change permissions of new files
pushd ${web_dir}
chgrp -R e3sm *.html 2>/dev/null || true
chmod -R go+rX,go-w *.html 2>/dev/null || true
popd
{% endif %}

{% if machine in ['anvil', 'chrysalis'] %}
# For LCRC, change permissions of new files
pushd ${web_dir}
chmod -R go+rX,go-w *.html 2>/dev/null || true
popd
{% endif %}

echo "Web files copied to ${web_dir}/"

# Clean up temporary workdir
echo
echo "===== CLEANUP TEMPORARY DIRECTORY ====="
echo

cd {{ scriptDir }}
if [[ "${debug,,}" != "true" ]]; then
  rm -rf ${workdir}
  if [ $? = 0 ]; then
    echo "Successfully cleaned up ${workdir}"
  else
    echo "Warning: Failed to clean up ${workdir}"
  fi
else
  echo "Debug mode: keeping temporary directory ${workdir}"
fi

################################################################################
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
