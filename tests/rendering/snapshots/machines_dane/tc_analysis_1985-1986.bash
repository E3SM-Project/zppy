#!/bin/bash

# Running on dane

#SBATCH  --job-name=tc_analysis_1985-1986
#SBATCH  --account=e3sm
#SBATCH  --nodes=1
#SBATCH  --output=/zppy_snapshot/output/post/scripts/tc_analysis_1985-1986.o%j
#SBATCH  --exclusive
#SBATCH  --time=00:30:00


# Turn on debug output if needed
debug=False
if [[ "${debug,,}" == "true" ]]; then
  set -x
fi

# Script dir
cd /zppy_snapshot/output/post/scripts

# Get jobid
id=${SLURM_JOBID}

# Update status file
STARTTIME=$(date +%s)
echo "RUNNING ${id}" > tc_analysis_1985-1986.status

set_pkg_manager() {
  # Detect whether to use pixi or conda based on environment_commands
  # Example environment commands:

  # These would indicate pixi is the package manager:
  # source /share/apps/E3SM/conda_envs/test_e3sm_unified_1.13.0rc7_compy.sh
  # source /share/apps/E3SM/conda_envs/load_latest_e3sm_unified_compy.sh

  # This would indicate conda is the package manager:
  # source /qfs/people/fors729/miniforge3/etc/profile.d/conda.sh; conda activate e3sm_to_cmip_20260415

  # Important: we need the quotes since environment_commands might
  # include multiple commands, separated by semi-colon.
  if echo "source /usr/workspace/e3sm/apps/e3sm-unified/load_latest_e3sm_unified_dane.sh" | grep -Eq 'test_e3sm_unified|load_latest_e3sm_unified'; then
    pkg_manager="pixi"
  else
    pkg_manager="conda"
  fi

  # We always want to know what the python version is.
  echo "${pkg_manager} list python:"
  ${pkg_manager} list python || true # If we can't print this, just continue on.
}

run_nco() {
  # Example:
  # environment_path=/global/cfs/cdirs/e3sm/zender/bin_perlmutter/ (set with jinja2 substitution from config file)
  # nco_cmd=ncclimo (passed in directly)
  # Runs `/global/cfs/cdirs/e3sm/zender/bin_perlmutter/ncclimo --npo` on the original arguments

  # Full list of NCO commands: https://nco.sourceforge.net/nco.html#Reference-Manual

  local environment_path=""
  local nco_cmd=$1
  shift # Remove nco_cmd from the argument list

  if [[ -n "$environment_path" && ( "$nco_cmd" == "ncclimo" || "$nco_cmd" == "ncremap" ) ]]; then
    # nco_path is non-empty AND nco_cmd is a script (either ncclimo or ncremap),
    # so use the full development setup:
    "${environment_path%/}/$nco_cmd" --npo "$@"
  else
    # nco_path is empty OR nco_cmd is a binary executable (not a script),
    # so use just the nco_cmd itself:
    "$nco_cmd" "$@"
  fi
}
set -e
source /usr/workspace/e3sm/apps/e3sm-unified/load_latest_e3sm_unified_dane.sh
set +e

set_pkg_manager

# A Bash script to post-process E3SM 6 hourly (h2) instantaneous output to generate a text file storing Tropical Cyclone tracks
# Only time steps at 00, 06, 12, and 18Z are used (TempestExtremes --timefilter "6hr"), since the tracking criteria count time steps.
# tempestremap and tempestextremes are built in e3sm-unified from version 1.5.0.

#For typical EAM v2 ne gp2 grids.
start="1985"
end="1986"
caseid="v3.LR.historical_0051"
default_caseid="v3.LR.historical_0051"
drc_in=/zppy_snapshot/input/v3.LR.historical_0051/archive/atm/hist
y1=1985
y2=1986
Y1="1985"
Y2="1986"
result_dir=/zppy_snapshot/output/post/atm/tc-analysis_${Y1}_${Y2}/

rm -rf ${result_dir}

atm_name=eam
input_files=eam.h2

# Determine grid resolution (res) and whether grid uses pg2.
# Preferred path (EAM + EAMxx): set input_grid in [tc_analysis], e.g. "ne30pg2".
# Legacy path (EAM-only):       set res, or rely on topography-file inference.
input_grid="ne30pg2"
res=""
pg2=false

if [[ -n "${input_grid}" ]]; then
    if [[ "${input_grid}" =~ ^ne([0-9]+)(pg2|np4)$ ]]; then
        res="${BASH_REMATCH[1]}"
        [[ "${BASH_REMATCH[2]}" == "pg2" ]] && pg2=true
    else
        echo "ERROR: unsupported input_grid='${input_grid}'. Expected neXpg2 or neXnp4 (e.g. ne30pg2, ne120np4, ne256pg2)."
        cd /zppy_snapshot/output/post/scripts
        echo 'ERROR (1)' > tc_analysis_1985-1986.status
        exit 1
    fi
else
    # Legacy: infer pg2 (and possibly res) from the topography_file global
    # attribute of a sample input file. EAM only; EAMxx sets topography_file="NONE".
    first_file=$(ls ${drc_in}/${caseid}.eam.h2.*.nc 2>/dev/null | head -n 1)
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
        cd /zppy_snapshot/output/post/scripts
        echo 'ERROR (2)' > tc_analysis_1985-1986.status
        exit 2
    fi
fi

echo "res=${res}"
echo "pg2=${pg2}"

# Determine variable names from the fixed TC variable sequence.
# Required order:
#   SLP,T@200hPa,T@500hPa,U@model_bottom,V@model_bottom,U@850hPa,V@850hPa
tc_vars="PSL,T200,T500,UBOT,VBOT,U850,V850"
IFS=',' read -ra var_array <<< "${tc_vars}"

if [ "${#var_array[@]}" -ne 7 ]; then

    echo "ERROR: tc_vars must contain exactly seven comma-separated variables in this order:"
    echo "       SLP,T@200hPa,T@500hPa,U@model_bottom,V@model_bottom,U@850hPa,V@850hPa"
    echo "Example for EAM:"
    echo "       tc_vars=\"PSL,T200,T500,UBOT,VBOT,U850,V850\""
    echo "Example for EAMxx:"
    echo "       tc_vars=\"SeaLevelPressure,T_mid_at_200hPa,T_mid_at_500hPa,U_at_model_bot,V_at_model_bot,U_at_850hPa,V_at_850hPa\""
    cd /zppy_snapshot/output/post/scripts
    echo 'ERROR (3)' > tc_analysis_1985-1986.status
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
        cd /zppy_snapshot/output/post/scripts
        echo 'ERROR (4)' > tc_analysis_1985-1986.status
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
        cd /zppy_snapshot/output/post/scripts
        echo 'ERROR (5)' > tc_analysis_1985-1986.status
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
        cd /zppy_snapshot/output/post/scripts
        echo 'ERROR (6)' > tc_analysis_1985-1986.status
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
    cd /zppy_snapshot/output/post/scripts
    echo 'ERROR (7)' > tc_analysis_1985-1986.status
    exit 7
fi

GenerateConnectivityFile \
    --in_mesh "${mesh_file}" \
    --out_type "${out_type}" \
    --out_connect "${connect_file}"

if [ $? != 0 ]; then
    echo "ERROR: GenerateConnectivityFile failed."
    cd /zppy_snapshot/output/post/scripts
    echo 'ERROR (8)' > tc_analysis_1985-1986.status
    exit 8
fi

echo "Completed GenerateConnectivityFile"

# ------------------------------------------------------------
# Get the list of files
# ------------------------------------------------------------
cd "${drc_in}" || {
    echo "ERROR: cannot cd to input directory '${drc_in}'."
    cd /zppy_snapshot/output/post/scripts
    echo 'ERROR (9)' > tc_analysis_1985-1986.status
    exit 9
}

eval ls ${drc_in}/${caseid}.${input_files}.*{${start}..${end}}*.nc > "${result_dir}inputfile_${file_name}.txt"
if [ $? != 0 ] || [ ! -s "${result_dir}inputfile_${file_name}.txt" ]; then
    echo "ERROR: no input files found for ${caseid}.${input_files} between ${start} and ${end}."
    cd /zppy_snapshot/output/post/scripts
    echo 'ERROR (10)' > tc_analysis_1985-1986.status
    exit 10
fi

eval ls ${caseid}.${input_files}.*{${start}..${end}}*.nc > "${result_dir}outputfile_${file_name}.txt"
if [ $? != 0 ] || [ ! -s "${result_dir}outputfile_${file_name}.txt" ]; then
    echo "ERROR: no output file names generated for ${caseid}.${input_files} between ${start} and ${end}."
    cd /zppy_snapshot/output/post/scripts
    echo 'ERROR (11)' > tc_analysis_1985-1986.status
    exit 11
fi

cd "${result_dir}" || {
    echo "ERROR: cannot cd to result directory '${result_dir}'."
    cd /zppy_snapshot/output/post/scripts
    echo 'ERROR (12)' > tc_analysis_1985-1986.status
    exit 12
}

# ------------------------------------------------------------
# TC candidate detection. Detection threshold including:
# 1. The sea-level pressure (SLP) must be a local minimum;
# 2. SLP must have a sufficient decrease (300 Pa) compared to surrounding nodes within 4 degree radius;
# 3. Warm core: the maximum of the 200/500 hPa average temperature is searched for within
#    temp_threshold_radius degrees of the SLP minimum (about one grid spacing, so it depends
#    on resolution), and from that maximum the field must decrease by 0.6 K in all directions
#    within a 4 degree radius.
# ------------------------------------------------------------
if [ "${res}" == 120 ]; then
    echo "${res}"
    temp_threshold_radius=0.30
elif [ "${res}" == 30 ]; then
    echo "${res}"
    temp_threshold_radius=1.0
elif [ "${res}" == 256 ]; then
    echo "${res}"
    temp_threshold_radius=0.15
else
    echo "ERROR: ${res} value not supported. Supported resolutions: 30, 120, 256."
    cd /zppy_snapshot/output/post/scripts
    echo 'ERROR (13)' > tc_analysis_1985-1986.status
    exit 13
fi

DetectNodes \
    --verbosity 0 \
    --in_connect "${connect_file}" \
    --closedcontourcmd "${var_psl},300.0,4.0,0;_AVG(${var_t200},${var_t500}),-0.6,4,${temp_threshold_radius}" \
    --mergedist 6.0 \
    --searchbymin "${var_psl}" \
    --outputcmd "${var_psl},min,0;_VECMAG(${var_ubot},${var_vbot}),max,2" \
    --timefilter "6hr" \
    --in_data_list "${result_dir}inputfile_${file_name}.txt" \
    --out "${result_dir}out.dat"

if [ $? != 0 ]; then
    echo "ERROR: TC DetectNodes failed."
    cd /zppy_snapshot/output/post/scripts
    echo 'ERROR (14)' > tc_analysis_1985-1986.status
    exit 14
fi

cat "${result_dir}"out.dat0* > "${result_dir}cyclones_${file_name}.txt" 2>/dev/null
if ! grep -q "^[0-9]" "${result_dir}cyclones_${file_name}.txt"; then
    echo "ERROR: no input time steps are at 00:00, 06:00, 12:00, or 18:00 UTC."
    echo "       tc_analysis uses only these time steps (TempestExtremes --timefilter \"6hr\")."
    cd /zppy_snapshot/output/post/scripts
    echo 'ERROR (19)' > tc_analysis_1985-1986.status
    exit 19
fi
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
    cd /zppy_snapshot/output/post/scripts
    echo 'ERROR (15)' > tc_analysis_1985-1986.status
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
    --in_connect "${connect_file}" \
    --timefilter "6hr"

if [ $? != 0 ]; then
    echo "ERROR: VariableProcessor failed while computing VORT from ${var_u850},${var_v850}."
    echo "       Check that these variables exist in the input files."
    cd /zppy_snapshot/output/post/scripts
    echo 'ERROR (16)' > tc_analysis_1985-1986.status
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
    cd /zppy_snapshot/output/post/scripts
    echo 'ERROR (17)' > tc_analysis_1985-1986.status
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
    cd /zppy_snapshot/output/post/scripts
    echo 'ERROR (18)' > tc_analysis_1985-1986.status
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
cd /zppy_snapshot/output/post/scripts

ENDTIME=$(date +%s)
ELAPSEDTIME=$(($ENDTIME - $STARTTIME))

echo ==============================================
echo "Elapsed time: $ELAPSEDTIME seconds"
echo ==============================================
rm -f tc_analysis_1985-1986.status
echo 'OK' > tc_analysis_1985-1986.status
exit 0