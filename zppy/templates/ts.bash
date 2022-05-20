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

ts_fmt={{ ts_fmt }}
echo $ts_fmt

{%- if frequency != 'monthly' %}
# For non-monthly input files, need to add the last file of the previous year
year={{ yr_start - 1 }}
YYYY=`printf "%04d" ${year}`
mapfile -t files < <( ls ${input}/{{ case }}.{{ input_files }}.${YYYY}-*.nc 2> /dev/null )
{% raw -%}
if [ ${#files[@]} -ne 0 ]
then
  ln -s ${files[-1]} .
fi
{%- endraw %}
# as well as first file of next year to ensure that first and last years are complete
year={{ yr_end + 1 }}
YYYY=`printf "%04d" ${year}`
mapfile -t files < <( ls ${input}/{{ case }}.{{ input_files }}.${YYYY}-*.nc 2> /dev/null )
{% raw -%}
if [ ${#files[@]} -ne 0 ]
then
  ln -s ${files[0]} .
fi
{%- endraw %}
{%- endif %}

ls {{ case }}.{{ input_files }}.????-*.nc > input.txt
# Generate time series files
cat input.txt | ncclimo \
-c {{ case }} \
-v {{ vars }} \
--mem_mb=0 \
{%- if extra_vars != '' %}
--var_xtr={{extra_vars}} \
{%- endif %}
--yr_srt={{ yr_start }} \
--yr_end={{ yr_end }} \
--ypf={{ ypf }} \
{% if mapping_file == '' -%}
-o output \
{%- elif mapping_file == 'glb' -%}
-o output \
--glb_avg \
--area={{ area_nm }} \
{%- else -%}
--map={{ mapping_file }} \
-o trash \
-O output \
{%- endif %}
{%- if frequency != 'monthly' %}
--clm_md=hfs \
--dpf={{ dpf }} \
--tpd={{ tpd }} \
{%- endif %}
{%- if input_files.split(".")[0] == 'cam' or input_files.split(".")[0] == 'eam'%}
--prc_typ={{ input_files.split(".")[0] }}
{%- else %}
--prc_typ=sgs
{%- endif %}



if [ $? != 0 ]; then
  cd {{ scriptDir }}
  echo 'ERROR (1)' > {{ prefix }}.status
  exit 1
fi

# Move output ts files to final destination
{
  dest={{ output }}/post/{{ component }}/{{ grid }}/ts/{{ frequency }}/{{ '%dyr' % (ypf) }}
  mkdir -p ${dest}
  mv output/*.nc ${dest}
}
if [ $? != 0 ]; then
  cd {{ scriptDir }}
  echo 'ERROR (2)' > {{ prefix }}.status
  exit 2
fi

{%- if ts_fmt != 'ts_only' %}
tmp_dir=tmp_{{ prefix }}

# Generate CMIP ts
cat > default_metadata.json << EOF
{% include cmip_metadata %}
EOF
{
  export cmortables_dir=/lcrc/group/acme/public_html/diagnostics/cmip6-cmor-tables/Tables
  input_dir={{ output }}/post/{{ component }}/{{ grid }}/ts/{{ frequency }}/{{ '%dyr' % (ypf) }}
  dest_cmip={{ output }}/post/{{ component }}/{{ grid }}/cmip_ts/{{ frequency }}
  mkdir -p ${dest_cmip}
  e3sm_to_cmip \
  --output-path \
  ${dest_cmip}/${tmp_dir} \
  {% if input_files == 'elm.h0' -%}
  --var-list \
  'mrsos, mrso, mrfso, mrros, mrro, prveg, evspsblveg, evspsblsoi, tran, tsl, lai, cLitter, cProduct, cSoilFast,cSoilMedium,cSoilSlow fFire, fHarvest, cVeg, nbp, gpp, ra, rh' \
  --realm \
  lnd \
  {% endif -%}
  {% if input_files == 'eam.h0' -%}
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
    echo 'ERROR (3)' > {{ prefix }}.status
    exit 3
  fi

  # Move output ts files to final destination
  mv ${dest_cmip}/${tmp_dir}/CMIP6/CMIP/*/*/*/*/*/*/*/*/*.nc ${dest_cmip}
  if [ $? != 0 ]; then
    cd {{ scriptDir }}
    echo 'ERROR (4)' > {{ prefix }}.status
    exit 4
  fi

      rm -r ${dest_cmip}/${tmp_dir}

}
if [ $? != 0 ]; then
  cd {{ scriptDir }}
  echo 'ERROR (5)' > {{ prefix }}.status
  exit 5
fi
{%- endif %}

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
