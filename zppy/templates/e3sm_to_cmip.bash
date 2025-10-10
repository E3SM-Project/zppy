#!/bin/bash
{% include 'inclusions/slurm_header.bash' %}
{% include 'inclusions/boilerplate.bash' %}
{{ environment_commands }}

# Create temporary workdir
hash=`mktemp --dry-run -d XXXX`
workdir=tmp.{{ prefix }}.${id}.${hash}
mkdir ${workdir}
cd ${workdir}

# From the ts task
dest={{ output }}/post/{{ component }}/{{ ts_grid }}/ts/{{ frequency }}/{{ '%dyr' % (ypf) }}

tmp_dir=tmp_{{ prefix }}

# Generate CMIP ts
cat > default_metadata.json << EOF
{% include cmip_metadata %}
EOF
{
  export cmortables_dir={{ cmor_tables_prefix }}/cmip6-cmor-tables/Tables
  input_dir=${dest}/{{ '%04d' % (yr_start) }}_{{ '%04d' % (yr_end) }}
  mkdir -p $input_dir

  cp -s $dest/*_{{ '%04d' % (yr_start) }}??_{{ '%04d' % (yr_end) }}??.nc $input_dir
  dest_cmip={{ output }}/post/{{ component }}/{{ ts_grid }}/cmip_ts/{{ frequency }}
  mkdir -p ${dest_cmip}

  {% if input_files.split(".")[0] == 'cam' or input_files.split(".")[0] == 'eam' -%}
  #add code to do vertical interpolation variables at model levels before e3sm_to_cmip
  IFS=',' read -ra mlvars <<< "{{ interp_vars }}"
  for var in "${mlvars[@]}"
  do
    for file in ${input_dir}/${var}_{{ '%04d' % (yr_start) }}??_{{ '%04d' % (yr_end) }}??.nc
    do
      if [ -f ${file} ]; then
        #ncks --rgr xtr_mth=mss_val --vrt_fl='{{cmip_plevdata}}' ${file} ${file}.plev
        ncremap -p mpi --vrt_ntp=log --vrt_xtr=mss_val --vrt_out='{{cmip_plevdata}}' ${file} ${file}.plev
        if [ $? != 0 ]; then
          cd {{ scriptDir }}
          echo 'ERROR (1)' > {{ prefix }}.status
          exit 1
        fi
        #overwrite the model level data
	      mv ${file}.plev ${file}
      fi
    done
  done
  {% endif -%}

  #call e3sm_to_cmip
  srun -N 1 e3sm_to_cmip \
  --output-path \
  ${dest_cmip}/${tmp_dir} \
  --var-list \
  '{{ cmip_vars }}' \
  --realm \
  {{ component }} \
  --input-path \
  ${input_dir} \
  --user-metadata \
  {{ scriptDir }}/${workdir}/default_metadata.json \
  --num-proc \
  12 \
  --tables-path \
  ${cmortables_dir}

  if [ $? != 0 ]; then
    cd {{ scriptDir }}
    echo 'ERROR (2)' > {{ prefix }}.status
    exit 2
  fi

  # Move output ts files to final destination
  mv ${dest_cmip}/${tmp_dir}/CMIP6/CMIP/*/*/*/*/*/*/*/*/*.nc ${dest_cmip}
  if [ $? != 0 ]; then
    cd {{ scriptDir }}
    echo 'ERROR (3)' > {{ prefix }}.status
    exit 3
  fi

  rm -r ${dest_cmip}/${tmp_dir}

}
if [ $? != 0 ]; then
  cd {{ scriptDir }}
  echo 'ERROR (4)' > {{ prefix }}.status
  exit 4
fi

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
