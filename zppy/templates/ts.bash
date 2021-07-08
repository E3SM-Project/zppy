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

# Generate time series files
ncclimo \
-c {{ case }} \
-v {{ vars }} \
--yr_srt={{ yr_start }} \
--yr_end={{ yr_end }} \
--ypf={{ ypf }} \
{% if mapping_file == '' -%}
-o output \
{%- elif mapping_file == 'glb' -%}
-o output \
--glb_avg \
--area_nm={{ area_nm }} \
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
{{ case }}.{{ input_files }}.????-*.nc

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
