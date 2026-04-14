#!/bin/bash
{% include 'inclusions/slurm_header.bash' %}
{% include 'inclusions/boilerplate.bash' %}
echo
echo ===== ACTIVATE ENVIRONMENT =====
echo
set -e
{{ environment_commands }}
set +e

# Detect whether to use pixi or conda based on environment_commands
if echo {{ environment_commands }} | grep -q "conda"; then
    pkg_manager="conda"
else
    pkg_manager="pixi"
fi

echo "${pkg_manager} list python:"
${pkg_manager} list python || true # If we can't print this, just continue on.
echo "${pkg_manager} list livvkit:"
${pkg_manager} list livvkit || true # If we can't print this, just continue on.

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
mkdir -p ${workdir}/${case}
cd ${workdir}/${case}

echo
echo ===== RUN LIVVKIT =====
echo

# include cfg file
cat > livvkit_template.yml << EOF
{% include cfg %}
EOF

climo_dir_source={{ output }}/post/lnd/DATA_GRID/clim/{{ '%dyr' % (year2-year1+1) }}

# Generate config file
lex-cfg \
  --template livvkit_template.yml \
  --casedir ${climo_dir_source} \
  --case ${case} \
  --icesheets {{ icesheets }} \
  --sets {{ sets }} \
  -z

echo ${workdir}
echo {{ scriptDir }}
livv --validate livvkit.yml --out-dir ./${case}.web

if [ $? != 0 ]; then
  cd {{ scriptDir }}
  echo 'ERROR (1)' > {{ prefix }}.status
  exit 1
fi
mv livv_log_${case}.web.log ./${case}.web/logs

# Copy output to web server
echo
echo ===== COPY FILES TO WEB SERVER =====
echo

# Create top-level directory
web_dir=${www}/${case}/livvkit/${Y1}-${Y2}
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
results_dir=./${case}.web/
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
cd {{ scriptDir }}
rm -f {{ prefix }}.status
echo 'OK' > {{ prefix }}.status
exit 0
