#!/bin/bash
{% include 'slurm_header.sh' %}
{{ environment_commands }}

# Turn on debug output if needed
debug={{ debug }}
if [[ "${debug,,}" == "true" ]]; then
  set -x
fi

# Script dir
cd {{ scriptDir }}

# Get jobid
id=${SLURM_JOBID}

# Update status file
STARTTIME=$(date +%s)
echo "RUNNING ${id}" > {{ prefix }}.status

# Create temporary workdir
workdir=`mktemp -d tmp.${id}.XXXX`
cd ${workdir}

# Create symbolic links to input files
input={{ input }}/{{ input_subdir }}
for (( year={{ yr_start }}; year<={{ yr_end }}; year++ ))
do
  YYYY=`printf "%04d" ${year}`
  for file in ${input}/{{ case }}.{{ input_files }}.${YYYY}-*.nc
  do
    ln -s ${file} .
  done
done





tmp_dir=tmp_{{ prefix }}

# Generate CMIP ts
cat > default_metadata.json << EOF
{% include cmip_metadata %}
EOF
{
  export cmortables_dir={{ cmor_tables_prefix }}/cmip6-cmor-tables/Tables
  input_dir={{ output }}/post/{{ component }}/{{ grid }}/ts/{{ frequency }}/{{ '%dyr' % (ypf) }}
  dest_cmip={{ output }}/post/{{ component }}/{{ grid }}/cmip_ts/{{ frequency }}
  mkdir -p ${dest_cmip}
  srun -N 1 e3sm_to_cmip \
  --output-path \
  ${dest_cmip}/${tmp_dir} \
  {% if input_files.split(".")[0] == 'clm2' or input_files.split(".")[0] == 'elm' -%}
  --var-list \
  'mrsos, mrso, mrfso, mrros, mrro, prveg, evspsblveg, evspsblsoi, tran, tsl, lai, cLitter, cProduct, cSoilFast, cSoilMedium, cSoilSlow, fFire, fHarvest, cVeg, nbp, gpp, ra, rh' \
  --realm \
  lnd \
  {% endif -%}
  {% if input_files.split(".")[0] == 'cam' or input_files.split(".")[0] == 'eam' -%}
  --var-list \
  'pr, tas, rsds, rlds, rsus' \
  --realm \
  atm \
  {% endif -%}
  --input-path \
  ${input_dir}\
  --user-metadata \
  {{ scriptDir }}/${workdir}/default_metadata.json \
  --num-proc \
  12 \
  --tables-path \
  ${cmortables_dir}

  if [ $? != 0 ]; then
    cd {{ scriptDir }}
    echo 'ERROR (1)' > {{ prefix }}.status
    exit 1
  fi

  # Move output ts files to final destination
  mv ${dest_cmip}/${tmp_dir}/CMIP6/CMIP/*/*/*/*/*/*/*/*/*.nc ${dest_cmip}
  if [ $? != 0 ]; then
    cd {{ scriptDir }}
    echo 'ERROR (2)' > {{ prefix }}.status
    exit 2
  fi

      rm -r ${dest_cmip}/${tmp_dir}

}
if [ $? != 0 ]; then
  cd {{ scriptDir }}
  echo 'ERROR (3)' > {{ prefix }}.status
  exit 3
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
