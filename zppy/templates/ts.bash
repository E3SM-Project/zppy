#!/bin/bash
{% include 'inclusions/slurm_header.bash' %}
{% include 'inclusions/boilerplate.bash' %}
{{ environment_commands }}

# Create temporary workdir
hash=`mktemp --dry-run -d XXXX`
workdir=tmp.{{ prefix }}.${id}.${hash}
mkdir ${workdir}
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

{% if mapping_file == 'glb' -%}
vars={{ vars }}
# https://unix.stackexchange.com/questions/237297/the-fastest-way-to-remove-a-string-in-a-variable
# https://stackoverflow.com/questions/26457052/remove-a-substring-from-a-bash-variable
# Remove U, since it is a 3D variable and thus will not work with rgn_avg
vars=${vars//,U}
{%- else %}
vars={{ vars }}
{%- endif %}

ls {{ case }}.{{ input_files }}.????-*.nc > input.txt
if grep -q "*" input.txt; then
  cd {{ scriptDir }}
  echo 'Missing input files'
  echo 'ERROR (1)' > {{ prefix }}.status
  exit 1
fi
# Generate time series files
# If the user-defined parameter "vars" is "", then ${vars}, defined above, will be too.
cat input.txt | ncclimo \
-c {{ case }} \
{%- if vars != '' %}
-v ${vars} \
{%- elif 'elm' in input_files %}
--xcl_var -v {{ vars_exclude }} \
{%- endif %}
--split \
{%- if extra_vars != '' %}
--var_xtr={{extra_vars}} \
{%- endif %}
{%- if parallel != '' %}
--parallel={{ parallel }} \
{%- endif %}
--yr_srt={{ yr_start }} \
--yr_end={{ yr_end }} \
--ypf={{ ypf }} \
{% if mapping_file == '' -%}
-o output \
{%- elif mapping_file == 'glb' -%}
-o output \
--rgn_avg \
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
--prc_typ={{ prc_typ }}



if [ $? != 0 ]; then
  cd {{ scriptDir }}
  echo 'ERROR (2)' > {{ prefix }}.status
  exit 2
fi

# Move output ts files to final destination
{
  dest={{ output }}/post/{{ component }}/{{ grid }}/ts/{{ frequency }}/{{ '%dyr' % (ypf) }}
  mkdir -p ${dest}
  mv output/*.nc ${dest}
}
if [ $? != 0 ]; then
  cd {{ scriptDir }}
  echo 'ERROR (3)' > {{ prefix }}.status
  exit 3
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
