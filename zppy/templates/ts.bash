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
# https://unix.stackexchange.com/questions/237297/the-fastest-way-to-remove-a-string-in-a-variable
# https://stackoverflow.com/questions/26457052/remove-a-substring-from-a-bash-variable
# Remove U, since it is a 3D variable and thus will not work with rgn_avg
# vars=${vars//,U}
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
# Generate time series files.
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
{%- if mapping_file == '' %}
-o output \
{%- elif mapping_file == 'glb' %}
-o output \
--rgn_avg \
--area={{ area_nm }} \
{%- else %}
{%- if prc_typ in ['mpasocean', 'mpasseaice'] %}
-o trash \
{%- else %}
--map={{ mapping_file }} \
-o trash \
-O output \
{%- endif %}
{%- endif %}
{%- if frequency != 'monthly' %}
--clm_md=hfs \
--dpf={{ dpf }} \
--tpd={{ tpd }} \
{%- endif %}
--prc_typ={{ prc_typ }}

# Check ncclimo status before any optional separate regridding.
if [ $? != 0 ]; then
  cd {{ scriptDir }}
  echo 'ERROR (2)' > {{ prefix }}.status
  exit 2
fi

{%- if mapping_file != '' and mapping_file != 'glb' and prc_typ in ['mpasocean', 'mpasseaice'] %}

# Regrid MPAS-Ocean and MPAS-Seaice files separately.
#
# For MPAS components, generate native-grid time-series files first, then
# regrid them with ncremap. This lets us restore MPAS-native time metadata,
# construct a CF-style numeric time coordinate, and repair missing_value
# attributes after regridding if needed.
#
# For MPAS-Seaice, also provide valid spatial-only SGS helper variables for
# regridding. MPAS-Seaice monthly files may include time-dependent SGS
# diagnostics such as:
#
#   timeMonthly_avg_iceAreaCell(Time,nCells)
#
# This variable should remain in the final time-series output. However,
# NCO's regridder requires sgs_frc_nm and sgs_msk_nm to be spatial-only
# fields matching the horizontal source grid size, i.e., nCells. Therefore,
# create temporary spatial-only helper variables with separate names and use
# them only for regridding.
mkdir -p output

mpas_calendar="{{ mpas_calendar }}"
mpas_start_time="{{ mpas_start_time }}"
mpas_start_time="${mpas_start_time/_/ }"

for f in trash/*.nc ; do
  bname=$(basename "${f}")
  tmp_f="tmp_regrid_${bname}"
  tmp_frc="tmp_sgs_frc_${bname}"
  tmp_msk="tmp_sgs_msk_${bname}"
  out_f="output/${bname}"

  cp "${f}" "${tmp_f}"

  # Detect whether the time dimension is named Time or time.
  # MPAS native ncclimo files often have a Time dimension but no
  # coordinate variable named Time/time.
  if run_nco ncks -m "${tmp_f}" | grep -qE "^[[:space:]]*Time[[:space:]]*=|\(Time[,)]|, Time[,)]"; then
    time_dim="Time"
  elif run_nco ncks -m "${tmp_f}" | grep -qE "^[[:space:]]*time[[:space:]]*=|\(time[,)]|, time[,)]"; then
    time_dim="time"
  else
    echo "ERROR: Cannot find Time/time dimension in ${tmp_f}"
    cd {{ scriptDir }}
    echo 'ERROR (3)' > {{ prefix }}.status
    exit 3
  fi

  # Infer the main variable name from the output filename.
  # Example:
  #   timeMonthly_avg_seaSurfaceTemperature_000101_000512.nc
  # becomes:
  #   timeMonthly_avg_seaSurfaceTemperature
  main_var=$(echo "${bname}" | sed -E 's/_[0-9]{6}_[0-9]{6}\.nc$//')

  use_sgs_helpers="false"

  {%- if prc_typ == 'mpasseaice' %}

  # Construct explicit static SGS helpers for MPAS-Seaice.
  #
  # ncremap -P mpasseaice automatically tries to use
  # timeMonthly_avg_iceAreaCell as sgs_frc_nm. However, that variable is
  # time-dependent, with shape Time x nCells, while NCO requires sgs_frc_nm
  # to be spatial-only, with shape nCells.
  #
  # Therefore, whenever timeMonthly_avg_iceAreaCell is available, construct:
  #
  #   sgs_frc_static(nCells) = time mean of timeMonthly_avg_iceAreaCell
  #   sgs_msk_static(nCells) = 1 where sgs_frc_static > 0, else 0
  #
  # Do not fall back to implicit ncremap SGS handling when this helper can be
  # constructed, because the implicit path may reuse the time-dependent field.
  if run_nco ncks -m "${tmp_f}" | grep -q "timeMonthly_avg_iceAreaCell"; then

    # Construct spatial-only SGS fraction helper.
    run_nco ncwa -O -a "${time_dim}" -y avg \
      -v timeMonthly_avg_iceAreaCell \
      "${tmp_f}" "${tmp_frc}"

    run_nco ncrename -O \
      -v timeMonthly_avg_iceAreaCell,sgs_frc_static \
      "${tmp_frc}"

    # Construct a spatial-only binary SGS mask from the static fraction.
    # This avoids relying on timeMonthly_avg_icePresentIntMask, which may
    # not be present in every split file.
    run_nco ncap2 -O \
      -s 'sgs_msk_static=(sgs_frc_static > 0.0)' \
      "${tmp_frc}" "${tmp_msk}"

    run_nco ncks -O -x -v sgs_frc_static "${tmp_msk}" "${tmp_msk}.only_msk"
    mv "${tmp_msk}.only_msk" "${tmp_msk}"

    # Append helper variables to the temporary file.
    # This does not remove or overwrite the original time-dependent variables.
    run_nco ncks -A "${tmp_frc}" "${tmp_f}"
    run_nco ncks -A "${tmp_msk}" "${tmp_f}"

    use_sgs_helpers="true"
  else
    echo "ERROR: timeMonthly_avg_iceAreaCell is missing in ${tmp_f}; cannot construct static SGS helpers for MPAS-Seaice."
    cd {{ scriptDir }}
    echo 'ERROR (3)' > {{ prefix }}.status
    exit 3
  fi

  {%- endif %}

  if [ "${use_sgs_helpers}" == "true" ]; then
    run_nco ncremap \
      -P {{ prc_typ }} \
      --d2f \
      --no_stagger \
      -t 1 \
      --nco_opt='--no_tmp_fl --hdr_pad=10000' \
      --map={{ mapping_file }} \
      --sgs_frc=sgs_frc_static \
      --sgs_msk=sgs_msk_static \
      --sgs_nrm=1.0 \
      "${tmp_f}" \
      "${out_f}"
  else
    run_nco ncremap \
      -P {{ prc_typ }} \
      --d2f \
      --no_stagger \
      -t 1 \
      --nco_opt='--no_tmp_fl --hdr_pad=10000' \
      --map={{ mapping_file }} \
      "${tmp_f}" \
      "${out_f}"
  fi

  rc=$?

  # Remove temporary/helper variables from the final regridded output.
  # Keep timeMonthly_avg_iceAreaCell only when it is the requested main variable.
  if [ ${rc} == 0 ] && [ "{{ prc_typ }}" == "mpasseaice" ]; then
    vars_to_remove="sgs_frc_static,sgs_msk_static"

    if [ "${main_var}" != "timeMonthly_avg_iceAreaCell" ]; then
      vars_to_remove="${vars_to_remove},timeMonthly_avg_iceAreaCell"
    fi

    # Remove helper variables only if at least one is present in the output.
    remove_present="false"
    for rm_var in $(echo "${vars_to_remove}" | tr ',' ' '); do
      if run_nco ncks -m "${out_f}" | grep -qE "^[[:space:]]*[^:]+[[:space:]]+${rm_var}(\(|\[)"; then
        remove_present="true"
        break
      fi
    done

    if [ "${remove_present}" == "true" ]; then
      run_nco ncks -O -x -v "${vars_to_remove}" "${out_f}" "${out_f}.clean"
      mv "${out_f}.clean" "${out_f}"
      rc=$?
    fi
  fi

  # Restore MPAS-native time metadata variables if needed.
  # MPAS files often have a Time dimension and xtime_* variables, but no
  # standard numeric coordinate variable named Time/time.
  if [ ${rc} == 0 ]; then
    for tvar in xtime_startMonthly xtime_endMonthly timeMonthly_avg_daysSinceStartOfSim; do
      if run_nco ncks -m "${tmp_f}" | grep -q "${tvar}"; then
        if ! run_nco ncks -m "${out_f}" | grep -q "${tvar}"; then
          run_nco ncks -A -v "${tvar}" "${tmp_f}" "${out_f}"
          rc=$?
          if [ ${rc} != 0 ]; then
            break
          fi
        fi
      fi
    done
  fi

  # Construct a CF-style numeric time coordinate if it is missing.
  # Use MPAS days-since-start metadata:
  #
  #   timeMonthly_avg_daysSinceStartOfSim(Time)
  #
  # to create:
  #
  #   time(Time)
  #     units    = "days since ${mpas_start_time}"
  #     calendar = "${mpas_calendar}"
  #
  # This improves compatibility with downstream tools that expect a
  # standard numeric time coordinate.
  if [ ${rc} == 0 ]; then
    if ! run_nco ncks -m "${out_f}" | grep -qE "^[[:space:]]*(float|double)[[:space:]]+time(\(|\[)"; then
      if run_nco ncks -m "${tmp_f}" | grep -q "timeMonthly_avg_daysSinceStartOfSim"; then
        tmp_time="tmp_time_${bname}"

        run_nco ncks -O \
          -v timeMonthly_avg_daysSinceStartOfSim \
          "${tmp_f}" "${tmp_time}"

        run_nco ncrename -O \
          -v timeMonthly_avg_daysSinceStartOfSim,time \
          "${tmp_time}"

        run_nco ncatted -O \
          -a units,time,o,c,"days since ${mpas_start_time}" \
          -a calendar,time,o,c,"${mpas_calendar}" \
          -a long_name,time,o,c,time \
          -a standard_name,time,o,c,time \
          "${tmp_time}"

        run_nco ncks -A -v time "${tmp_time}" "${out_f}"
        rc=$?

        rm -f "${tmp_time}"
      fi
    fi
  fi

  # Add missing_value metadata only for the main floating-point data variable
  # if it is missing. Avoid modifying coordinate or integer mask variables.
  # Do not force-create _FillValue here, because some NetCDF workflows are
  # sensitive to adding _FillValue after variable creation. Existing _FillValue
  # attributes are preserved.
  if [ ${rc} == 0 ]; then
    if run_nco ncks -m "${out_f}" | grep -qE "^[[:space:]]*(float|double)[[:space:]]+${main_var}(\(|\[)"; then
      if ! run_nco ncks -m "${out_f}" | grep -A8 -E "^[[:space:]]*(float|double)[[:space:]]+${main_var}(\(|\[)" | grep -q "missing_value"; then
        run_nco ncatted -O \
          -a missing_value,"${main_var}",o,f,1.0e36 \
          "${out_f}"
        rc=$?
      fi
    fi
  fi

  rm -f "${tmp_f}" "${tmp_frc}" "${tmp_msk}" "${tmp_msk}.only_msk" "${out_f}.clean"

  if [ ${rc} != 0 ]; then
    echo "ERROR: MPAS component regridding failed for ${bname}"
    cd {{ scriptDir }}
    echo 'ERROR (4)' > {{ prefix }}.status
    exit 4
  fi

done

{%- endif %}

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
  echo 'ERROR (5)' > {{ prefix }}.status
  exit 5
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
