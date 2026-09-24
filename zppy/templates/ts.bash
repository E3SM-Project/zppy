#!/bin/bash
{% include 'inclusions/slurm_header.bash' %}
{% include 'inclusions/boilerplate.bash' %}
set -e
{{ environment_commands }}
set +e

set_pkg_manager
echo "${pkg_manager} list nco:"
${pkg_manager} list nco || true # If we can't print this, just continue on.

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
# Remove 3D variables (U, U10, V) since they will not work with rgn_avg
# Use sed to match complete variable names (not partial matches)
# Pattern explanation: \(^\|,\) matches start of string or comma
#                      \(,\|$\) matches comma or end of string
vars=$(echo "$vars" | sed 's/\(^\|,\)U10\(,\|$\)/\1/g; s/\(^\|,\)U\(,\|$\)/\1/g; s/\(^\|,\)V\(,\|$\)/\1/g; s/,,*/,/g; s/^,//; s/,$//')
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
cat input.txt | run_nco ncclimo \
-c {{ case }} \
{%- if vars != '' %}
-v ${vars} \
{%- endif %}
{%- if job_nbr > 0 %}
--jobs={{ job_nbr }} \
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

{%- if vrt_remap_vars != '' %}

# Vertical regrid (model levels → pressure levels)
# When vrt_remap_vars is set, regrid the listed vars and write to a sibling
# directory ts_vrt_remap/ alongside the standard ts/ output.
mkdir output_plev
IFS=',' read -ra vremap_vars <<< "{{ vrt_remap_vars }}"
for var in "${vremap_vars[@]}"
do
  for file in output/${var}_{{ '%04d' % (yr_start) }}??_{{ '%04d' % (yr_end) }}??.nc
  do
    if [ ! -f "${file}" ]; then continue; fi
    out_file=output_plev/$(basename "${file}")
    run_nco ncremap \
      {%- if machine == 'dane' %}
      --mpi_pfx='srun -n {{ nodes }}' \
      {%- else %}
      -p mpi \
      {%- endif %}
      --vrt_ntp=log \
      --vrt_xtr=mss_val \
      --vrt_out='{{ vrt_remap_file }}' \
      {%- if prc_typ == 'eamxx' %}
      --ps_nm=${file}/ps \
      --vrt_in='{{ vrt_in_file }}' \
      {%- endif %}
      ${file} ${out_file}
    if [ $? != 0 ]; then
      cd {{ scriptDir }}
      echo 'ERROR (6)' > {{ prefix }}.status
      exit 6
    fi
  done
done
{%- endif %}

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

{%- if vrt_remap_vars != '' %}
# Move vertically regridded ts files to sibling destination
{
  dest_plev={{ output }}/post/{{ component }}/{{ grid }}/ts_vrt_remap/{{ frequency }}/{{ '%dyr' % (ypf) }}
  mkdir -p ${dest_plev}
  mv output_plev/*.nc ${dest_plev}
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
