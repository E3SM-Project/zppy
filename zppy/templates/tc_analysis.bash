#!/bin/bash
{% include 'inclusions/slurm_header.bash' %}
{% include 'inclusions/boilerplate.bash' %}
set -e
{{ environment_commands }}
set +e

set_pkg_manager

# A Bash script to post-process E3SM 6 hourly (h2) instantaneous output to generate a text file storing Tropical Cyclone tracks
# tempestremap and tempestextremes are built in e3sm-unified from version 1.5.0.

#For typical EAM v2 ne gp2 grids.
start="{{ '%04d' % (year1) }}"
end="{{ '%04d' % (year2) }}"
caseid="{{ case }}"
default_caseid="{{ default_case }}"
drc_in={{ input }}/{{ input_subdir }}
y1={{ year1 }}
y2={{ year2 }}
Y1="{{ '%04d' % (year1) }}"
Y2="{{ '%04d' % (year2) }}"
result_dir={{ output }}/post/atm/tc-analysis_${Y1}_${Y2}/

rm -rf ${result_dir}

atm_name={{ atm_name }}
input_files={{ input_files }}

# Determine grid resolution (res) and whether grid uses pg2.
# Preferred path (EAM + EAMxx): set input_grid in [tc_analysis], e.g. "ne30pg2".
# Legacy path (EAM-only):       set res, or rely on topography-file inference.
input_grid="{{ input_grid }}"
res="{{ res }}"
pg2=false

if [[ -n "${input_grid}" ]]; then
    if [[ "${input_grid}" =~ ^ne([0-9]+)(pg2|np4)$ ]]; then
        res="${BASH_REMATCH[1]}"
        [[ "${BASH_REMATCH[2]}" == "pg2" ]] && pg2=true
    else
        echo "ERROR: unsupported input_grid='${input_grid}'. Expected ne30pg2, ne30np4, ne120pg2, or ne120np4."
        cd {{ scriptDir }}
        echo 'ERROR (1)' > {{ prefix }}.status
        exit 1
    fi
else
    # Legacy: infer pg2 (and possibly res) from the topography_file global
    # attribute of a sample input file. EAM only; EAMxx sets topography_file="NONE".
    first_file=$(ls ${drc_in}/${caseid}.{{ input_files }}.*.nc 2>/dev/null | head -n 1)
    if [[ -n "${first_file}" ]]; then
        topography_file=$(run_nco ncks --trd -M -m "${first_file}" \
            | grep -E -i "^global attribute [0-9]+: topography_file" \
            | cut -f 11- -d ' ' | sort)
        filename="${topography_file##*/}"
        echo "topography_file=${topography_file}"
        if [[ "${filename}" =~ ne([0-9]+)np4pg2 ]]; then
            [[ -z "${res}" ]] && res="${BASH_REMATCH[1]}"
            pg2=true
        elif [[ "${filename}" =~ ne([0-9]+)np4 ]]; then
            [[ -z "${res}" ]] && res="${BASH_REMATCH[1]}"
        fi
    fi
    if [[ -z "${res}" ]]; then
        echo "ERROR: could not determine grid. Set input_grid (e.g. \"ne30pg2\") in [tc_analysis]."
        cd {{ scriptDir }}
        echo 'ERROR (2)' > {{ prefix }}.status
        exit 2
    fi
fi

echo "res=${res}"
echo "pg2=${pg2}"

# Determine variable names from the fixed TC variable sequence.
# Required order:
#   SLP,T@200hPa,T@500hPa,U@model_bottom,V@model_bottom,U@850hPa,V@850hPa
tc_vars="{{ tc_vars }}"
IFS=',' read -ra var_array <<< "${tc_vars}"
{% raw %}
if [ "${#var_array[@]}" -ne 7 ]; then
{% endraw %}
    echo "ERROR: tc_vars must contain exactly seven comma-separated variables in this order:"
    echo "       SLP,T@200hPa,T@500hPa,U@model_bottom,V@model_bottom,U@850hPa,V@850hPa"
    echo "Example for EAM:"
    echo "       tc_vars=\"PSL,T200,T500,UBOT,VBOT,U850,V850\""
    echo "Example for EAMxx:"
    echo "       tc_vars=\"SeaLevelPressure,T_mid_at_200hPa,T_mid_at_500hPa,U_at_model_bot,V_at_model_bot,U_at_850hPa,V_at_850hPa\""
    cd {{ scriptDir }}
    echo 'ERROR (3)' > {{ prefix }}.status
    exit 3
fi

var_psl="${var_array[0]}"
var_t200="${var_array[1]}"
var_t500="${var_array[2]}"
var_ubot="${var_array[3]}"
var_vbot="${var_array[4]}"
var_u850="${var_array[5]}"
var_v850="${var_array[6]}"

echo "TC variable mapping:"
echo "  SLP          = ${var_psl}"
echo "  T@200hPa     = ${var_t200}"
echo "  T@500hPa     = ${var_t500}"
echo "  U@bottom     = ${var_ubot}"
echo "  V@bottom     = ${var_vbot}"
echo "  U@850hPa     = ${var_u850}"
echo "  V@850hPa     = ${var_v850}"


mkdir -p "${result_dir}"
file_name=${default_caseid}_${start}_${end}

# ------------------------------------------------------------
# Generate mesh files (.g)
# ------------------------------------------------------------
if ${pg2}; then
    # For v2 and v3 production simulations with pg2 grids:
    GenerateCSMesh \
        --res "${res}" \
        --alt \
        --file "${result_dir}outCSMeshne${res}.g"

    if [ $? != 0 ]; then
        echo "ERROR: GenerateCSMesh failed."
        cd {{ scriptDir }}
        echo 'ERROR (4)' > {{ prefix }}.status
        exit 4
    fi
    echo "Completed GenerateCSMesh"

    GenerateVolumetricMesh \
        --in "${result_dir}outCSMeshne${res}.g" \
        --out "${result_dir}outCSne${res}.g" \
        --np 2 \
        --uniform

    if [ $? != 0 ]; then
        echo "ERROR: GenerateVolumetricMesh failed."
        cd {{ scriptDir }}
        echo 'ERROR (5)' > {{ prefix }}.status
        exit 5
    fi
    echo "Completed GenerateVolumetricMesh"

    out_type="FV"
else
    # For v1 production simulations with np4 grids:
    GenerateCSMesh \
        --res "${res}" \
        --alt \
        --file "${result_dir}outCSne${res}.g"

    if [ $? != 0 ]; then
        echo "ERROR: GenerateCSMesh failed."
        cd {{ scriptDir }}
        echo 'ERROR (6)' > {{ prefix }}.status
        exit 6
    fi
    echo "Completed GenerateCSMesh"

    out_type="CGLL"
fi

echo "${out_type}"

mesh_file="${result_dir}outCSne${res}.g"
connect_file="${result_dir}connect_CSne${res}_v2.dat"

if [ ! -s "${mesh_file}" ]; then
    echo "ERROR: mesh file '${mesh_file}' does not exist or is empty."
    cd {{ scriptDir }}
    echo 'ERROR (7)' > {{ prefix }}.status
    exit 7
fi

GenerateConnectivityFile \
    --in_mesh "${mesh_file}" \
    --out_type "${out_type}" \
    --out_connect "${connect_file}"

if [ $? != 0 ]; then
    echo "ERROR: GenerateConnectivityFile failed."
    cd {{ scriptDir }}
    echo 'ERROR (8)' > {{ prefix }}.status
    exit 8
fi

echo "Completed GenerateConnectivityFile"

# ------------------------------------------------------------
# Get the list of files
# ------------------------------------------------------------
cd "${drc_in}" || {
    echo "ERROR: cannot cd to input directory '${drc_in}'."
    cd {{ scriptDir }}
    echo 'ERROR (9)' > {{ prefix }}.status
    exit 9
}

eval ls ${drc_in}/${caseid}.${input_files}.*{${start}..${end}}*.nc > "${result_dir}inputfile_${file_name}.txt"
if [ $? != 0 ] || [ ! -s "${result_dir}inputfile_${file_name}.txt" ]; then
    echo "ERROR: no input files found for ${caseid}.${input_files} between ${start} and ${end}."
    cd {{ scriptDir }}
    echo 'ERROR (10)' > {{ prefix }}.status
    exit 10
fi

eval ls ${caseid}.${input_files}.*{${start}..${end}}*.nc > "${result_dir}outputfile_${file_name}.txt"
if [ $? != 0 ] || [ ! -s "${result_dir}outputfile_${file_name}.txt" ]; then
    echo "ERROR: no output file names generated for ${caseid}.${input_files} between ${start} and ${end}."
    cd {{ scriptDir }}
    echo 'ERROR (11)' > {{ prefix }}.status
    exit 11
fi

cd "${result_dir}" || {
    echo "ERROR: cannot cd to result directory '${result_dir}'."
    cd {{ scriptDir }}
    echo 'ERROR (12)' > {{ prefix }}.status
    exit 12
}

# ------------------------------------------------------------
# TC candidate detection. Detection threshold including:
# 1. The sea-level pressure (SLP) must be a local minimum;
# 2. SLP must have a sufficient decrease (300 Pa) compared to surrounding nodes within 4 degree radius;
# 3. The average of the 200 hPa and 500 hPa level temperature decreases by 0.6 K in all directions
#    within a 4 degree radius from the location to fSLP minima
# ------------------------------------------------------------
if [ "${res}" == 120 ]; then
    echo "${res}"
    temp_threshold_radius=0.30
elif [ "${res}" == 30 ]; then
    echo "${res}"
    temp_threshold_radius=1.0
else
    echo "ERROR: ${res} value not supported"
    cd {{ scriptDir }}
    echo 'ERROR (13)' > {{ prefix }}.status
    exit 13
fi

DetectNodes \
    --verbosity 0 \
    --in_connect "${connect_file}" \
    --closedcontourcmd "${var_psl},300.0,4.0,0;_AVG(${var_t200},${var_t500}),-0.6,4,${temp_threshold_radius}" \
    --mergedist 6.0 \
    --searchbymin "${var_psl}" \
    --outputcmd "${var_psl},min,0;_VECMAG(${var_ubot},${var_vbot}),max,2" \
    --timestride 1 \
    --in_data_list "${result_dir}inputfile_${file_name}.txt" \
    --out "${result_dir}out.dat"

if [ $? != 0 ]; then
    echo "ERROR: TC DetectNodes failed."
    cd {{ scriptDir }}
    echo 'ERROR (14)' > {{ prefix }}.status
    exit 14
fi

cat "${result_dir}"out.dat0* > "${result_dir}cyclones_${file_name}.txt" 2>/dev/null
echo "Completed DetectNodes"

# Stitch all candidate nodes in time to form tracks.
# Criteria:
#   - maximum distance between candidates: 6.0 degrees
#   - minimum track duration: 6 time steps
#   - maximum gap size: 1 time step
#   - wind speed threshold: >= 17.5 m/s for at least 6 time steps
#   - latitude range: 40S–40N for at least 6 time steps
StitchNodes \
    --in_fmt "lon,lat,slp,wind" \
    --in_connect "${connect_file}" \
    --range 6.0 \
    --mintime 6 \
    --maxgap 1 \
    --in "${result_dir}cyclones_${file_name}.txt" \
    --out "${result_dir}cyclones_stitch_${file_name}.dat" \
    --threshold "wind,>=,17.5,6;lat,<=,40.0,6;lat,>=,-40.0,6"
echo "Completed StitchNodes"

# ------------------------------------------------------------
# TC histogram
# ------------------------------------------------------------
HistogramNodes \
    --in "${result_dir}cyclones_stitch_${file_name}.dat" \
    --iloncol 2 \
    --ilatcol 3 \
    --out "${result_dir}cyclones_hist_${file_name}.nc"

if [ $? != 0 ]; then
    echo "ERROR: Cyclone HistogramNodes failed."
    cd {{ scriptDir }}
    echo 'ERROR (15)' > {{ prefix }}.status
    exit 15
fi

echo "Completed HistogramNodes"

rm -f "${result_dir}cyclones_${file_name}.txt"


# ------------------------------------------------------------
# AEW: calculate relative vorticity using 850-hPa winds
# The 850-hPa wind variable names are inferred from the fixed vars sequence:
#   vars[5] = U@850hPa
#   vars[6] = V@850hPa
# ------------------------------------------------------------
sed -i 's/\.nc/_vorticity.nc/' "${result_dir}outputfile_${file_name}.txt"

VariableProcessor \
    --in_data_list "${result_dir}inputfile_${file_name}.txt" \
    --out_data_list "${result_dir}outputfile_${file_name}.txt" \
    --var "_CURL{4,0.5}(${var_u850},${var_v850})" \
    --varout "VORT" \
    --in_connect "${connect_file}"

if [ $? != 0 ]; then
    echo "ERROR: VariableProcessor failed while computing VORT from ${var_u850},${var_v850}."
    echo "       Check that these variables exist in the input files."
    cd {{ scriptDir }}
    echo 'ERROR (16)' > {{ prefix }}.status
    exit 16
fi

echo "Completed VariableProcessor"

# ------------------------------------------------------------
# AEW candidate detection
# ------------------------------------------------------------
DetectNodes \
    --verbosity 0 \
    --in_connect "${connect_file}" \
    --closedcontourcmd "VORT,-5.e-6,4,0" \
    --mergedist 2.0 \
    --searchbymax VORT \
    --outputcmd "VORT,max,0" \
    --in_data_list "${result_dir}outputfile_${file_name}.txt" \
    --out "${result_dir}aew_out.dat" \
    --minlat -35.0 \
    --maxlat 35.0

if [ $? != 0 ]; then
    echo "ERROR: AEW DetectNodes failed."
    cd {{ scriptDir }}
    echo 'ERROR (17)' > {{ prefix }}.status
    exit 17
fi


cat "${result_dir}"aew_out.dat0* > "${result_dir}aew_${file_name}.txt" 2>/dev/null
echo "Completed DetectNodes"

# ------------------------------------------------------------
# AEW stitching
# ------------------------------------------------------------

StitchNodes \
    --in_fmt "lon,lat,VORT" \
    --in_connect "${connect_file}" \
    --range 3.0 \
    --mintime 8 \
    --maxgap 0 \
    --min_endpoint_dist 10.0 \
    --in "${result_dir}aew_${file_name}.txt" \
    --out "${result_dir}aew_stitch_5e-6_${file_name}.dat" \
    --threshold "lat,<=,25.0,8;lat,>=,0.0,8"
echo "Completed StitchNodes"

# ------------------------------------------------------------
# AEW histogram
# ------------------------------------------------------------

HistogramNodes \
    --in "${result_dir}aew_stitch_5e-6_${file_name}.dat" \
    --iloncol 2 \
    --ilatcol 3 \
    --nlat 256 \
    --nlon 512 \
    --out "${result_dir}aew_hist_${file_name}.nc"

if [ $? != 0 ]; then
    echo "ERROR: AEW HistogramNodes failed."
    cd {{ scriptDir }}
    echo 'ERROR (18)' > {{ prefix }}.status
    exit 18
fi

echo "Completed HistogramNodes"

rm -f "${result_dir}aew_${file_name}.txt"


# ------------------------------------------------------------
# Cleanup
# ------------------------------------------------------------
rm -f "${result_dir}"*out.dat00*.dat
rm -f "${result_dir}${caseid}"*.nc
rm -f "${result_dir}"*.txt

# Update status file and exit
cd {{ scriptDir }}
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
