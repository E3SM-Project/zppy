#!/bin/bash

# Running on dane

#SBATCH  --job-name=pcmdi_diags_mean_climate_model_vs_obs_1985-1986
#SBATCH  --account=e3sm
#SBATCH  --nodes=1
#SBATCH  --output=/zppy_snapshot/output/post/scripts/pcmdi_diags_mean_climate_model_vs_obs_1985-1986.o%j
#SBATCH  --exclusive
#SBATCH  --time=2:00:00


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
echo "RUNNING ${id}" > pcmdi_diags_mean_climate_model_vs_obs_1985-1986.status

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
echo "${pkg_manager} list zppy-interfaces:"
${pkg_manager} list zppy-interfaces || true # If we can't print this, just continue on.
echo "${pkg_manager} list pcmdi_metrics:"
${pkg_manager} list pcmdi_metrics || true # If we can't print this, just continue on.

# Need this setup as otherwise can not generate diagnostics
export UCX_SHM_DEVICES=all # or not set UCX_NET_DEVICES at all

# Make sure UVCDAT doesn't prompt us about anonymous logging
export UVCDAT_ANONYMOUS_LOG=False

# Basic definitions
case="v3.LR.historical_0051"
www="/zppy_snapshot/www"
run_type="model_vs_obs"
results_dir="model_vs_obs"



# Input time range
y1=1985
y2=1986
ref_y1=1985
ref_y2=1986
ref_start_yr=1985
ref_final_yr=1986

# Formatted versions
Y1="$(printf "%04d" ${y1})"
Y2="$(printf "%04d" ${y2})"
ref_Y1="$(printf "%04d" ${ref_y1})"
ref_Y2="$(printf "%04d" ${ref_y2})"

num_years=$((y2 - y1 + 1))
ref_end_yr=$((ref_y1 + num_years - 1))

# Keep originals for fallback
orig_ref_y1=${ref_y1}
orig_ref_y2=${ref_y2}
if [[ ${orig_ref_y1} -lt ${ref_start_yr} ]]; then
   orig_ref_y1=${ref_start_yr}
fi
if [[ ${orig_ref_y2} -gt ${ref_final_yr} ]]; then
   orig_ref_y2=${ref_final_yr}
fi
# Refine reference range
if [[ ${ref_start_yr} -le ${y1} && ${ref_final_yr} -ge ${y2} ]]; then
   # Availability fully covers analysis: use [y1, y2]
   ref_y1=${y1}
   ref_y2=${y2}
else
   # Case 2: Prefer the user's clamped custom window; only tweak if needed
   # 2a) If clamped custom overlaps the analysis window, use the intersection
   if [[ ${orig_ref_y1} -le ${y2} && ${orig_ref_y2} -ge ${y1} ]]; then
      # minimal trimming to fit inside [y1, y2]
      ref_y1=$(( orig_ref_y1 > y1 ? orig_ref_y1 : y1 ))
      ref_y2=$(( orig_ref_y2 < y2 ? orig_ref_y2 : y2 ))
   else
      # 2b) No overlap between custom and analysis:
      #     try availability i∩ analysis (minimal change wrt both)
      ovl_start=$(( ref_start_yr > y1 ? ref_start_yr : y1 ))
      ovl_end=$(( ref_final_yr < y2 ? ref_final_yr : y2 ))
      if [[ ${ovl_start} -le ${ovl_end} ]]; then
         ref_y1=${ovl_start}
         ref_y2=${ovl_end}
      else
         # 2c) Truly no overlap possible; fall back to clamped custom window
         ref_y1=${orig_ref_y1}
         ref_y2=${orig_ref_y2}
      fi
   fi
fi


source_vars="pr,tas"




# Top-level directory
web_dir=${www}/${case}/pcmdi_diags

##################################################
# info to construct pcmdi-preferred data convention
##################################################
model_name='e3sm.historical.v3-LR.0051'
tableID='Amon'

# The put_model_here gets replaced is passed into Python as a string literal
# And then replaced inside the Python code.
model_name_ref='obs.historical.put_model_here.00'
tableID_ref=${tableID}


case_id=v$(date '+%Y%m%d')


# Create temporary workdir
workdir=`mktemp -d tmp.pcmdi_diags_mean_climate_model_vs_obs_1985-1986.${id}.XXXX`
cd ${workdir}

# files for definition of regions for regional mean
cat > regions_specs.json << EOF
{
    "global": {
        "domain": { "latitude":[-90.0, 90.0]}
    },
    "NH": {
        "domain": { "latitude":[0.0, 90.0]}
    },
    "SH": {
        "domain": { "latitude":[-90.0, 0]}
    },
    "NHEX": {
        "domain": { "latitude":[30.0, 90.0]}
    },
    "SHEX": {
        "domain": { "latitude":[-90.0, -30.0]}
    },
    "TROPICS": {
        "domain": { "latitude":[-30.0, 30.0]}
    },
    "90S50S": {
        "domain": { "latitude":[-90.0, -50.0]}
    },
    "50S20S": {
        "domain": { "latitude":[-50.0, -20.0]}
    },
    "20S20N": {
        "domain": { "latitude":[-20.0, 20.0]}
    },
    "20N50N": {
        "domain": { "latitude":[20.0, 50.0]}
    },
    "50N90N": {
        "domain": { "latitude":[50.0, 90.0]}
    },
    "ocean_NH": {
        "value":  0.0,
        "domain": { "latitude":[0.0, 90.0]}
    },
    "ocean_SH": {
        "value":  0.0,
        "domain": { "latitude":[-90.0, 0.0]}
    },
    "land_NH": {
        "value":   100,
        "domain": { "latitude":[0.0, 90.0]}
    },
    "land_SH": {
        "value":   100,
        "domain": { "latitude":[-90.0, 0.0]}
    },
    "land_NHEX": {
        "value": 100,
        "domain": { "latitude":[30.0, 90.0]}
    },
    "land_SHEX": {
        "value": 100,
        "domain": { "latitude":[-90.0, -30.0]}
    },
    "land_TROPICS": {
        "value": 100,
        "domain": { "latitude":[-30.0, 30.0]}
    },
    "land": {
        "value": 100
    },
    "ocean_NHEX": {
        "value": 0,
        "domain": { "latitude":[30.0, 90.0]}
    },
    "ocean_SHEX": {
        "value": 0,
        "domain": { "latitude":[-90.0, -30.0]}
    },
    "ocean_TROPICS": {
        "value": 0,
        "domain": { "latitude":[30.0, 30.0]}
    },
    "ocean": {
        "value": 0
    },
    "ocean_50S50N": {
        "value": 0.0,
        "domain": { "latitude":[-50.0, 50.0]}
    },
    "ocean_50S20S": {
        "value": 0.0,
        "domain": { "latitude":[-50.0, -20.0]}
    },
    "ocean_20S20N": {
        "value": 0.0,
        "domain": { "latitude":[-20.0, 20.0]}
    },
    "ocean_20N50N": {
        "value": 0.0,
        "domain": { "latitude":[20.0, 50.0]}
    },
    "ocean_50N90N": {
        "value": 0.0,
        "domain": { "latitude":[50.0, 90.0]}
    },
    "ocean_90S50S": {
        "value": 0.0,
        "domain": { "latitude":[-90.0, -50.0]}
    },
    "NAM": {
        "domain": { "latitude":[20.0, 90],
		    "longitude":[-180, 180]}
    },
    "NAO": {
        "domain": { "latitude":[20.0, 80],
		    "longitude":[-90, 40]}
    },
    "SAM": {
        "domain": { "latitude":[-20.0, -90],
		    "longitude":[0, 360]}
    },
    "PSA1": {
        "domain": { "latitude":[-20.0, -90],
		    "longitude":[0, 360]}
    },
    "PSA2": {
        "domain": { "latitude":[-20.0, -90],
		    "longitude":[0, 360]}
    },
    "PNA": {
        "domain": { "latitude":[20.0, 85],
		    "longitude":[120, 240]}
    },
    "PDO": {
        "domain": { "latitude":[20.0, 70],
		    "longitude":[110, 260]}
    },
    "AMO": {
	"domain": { "latitude":[0.0, 70],
		    "longitude":[-80, 0]}
    },
    "AllMW": {
        "domain": { "latitude":[-40.0, 45.0],
		    "longitude":[0.0, 360.0]}
    },
    "AllM": {
        "domain": { "latitude":[-45.0, 45.0],
		    "longitude":[0.0, 360.0]}
    },
    "NAMM": {
        "domain": { "latitude":[0.0, 45.0],
		    "longitude":[210.0, 310.0]}
    },
    "SAMM": {
        "domain": { "latitude":[-45.0, 0.0],
		    "longitude":[240.0, 330.0]}
    },
    "NAFM": {
        "domain": { "latitude":[0.0, 45.0],
		    "longitude":[310.0, 60.0]}
    },
    "SAFM": {
        "domain": { "latitude":[-45.0, 0.0],
		    "longitude":[0.0, 90.0]}
    },
    "ASM": {
        "domain": { "latitude":[0.0, 45.0],
		    "longitude":[60.0, 180.0]}
    },
    "AUSM": {
        "domain": { "latitude":[-45.0, 0.0],
		    "longitude":[90.0, 160.0]}
    },
    "AIR": {
        "domain": { "latitude":[7.0, 25.0],
		    "longitude":[65.0, 85.0]}
    },
    "AUS": {
        "domain": { "latitude":[-20.0, -10.0],
		    "longitude":[120.0, 150.0]}
    },
    "Sahel": {
        "domain": { "latitude":[13.0, 18.0],
		    "longitude":[-10.0, 10.0]}
    },
    "GoG": {
        "domain": { "latitude":[0.0, 5.0],
		    "longitude":[-10.0, 10.0]}
    },
    "NAmo": {
        "domain": { "latitude":[20.0, 37.0],
		    "longitude":[-112.0, -103.0]}
    },
    "SAmo": {
        "domain": { "latitude":[-20.0, 2.5],
		    "longitude":[-65.0, -40.0]}
    },
    "Nino34": {
        "value": 0.0,
        "domain": { "latitude":[-5.0, 5.0],
		    "longitude":[190.0, 240.0]}
    },
    "Nino3": {
        "value": 0.0,
        "domain": { "latitude":[-5.0, 5.0],
		    "longitude":[210.0, 270.0]}
    },
    "Nino4": {
        "value": 0.0,
        "domain": { "latitude":[-5.0, 5.0],
		    "longitude":[160.0, 210.0]}
    },
    "ONI": {
        "value": 0.0,
        "domain": { "latitude":[-5.0, 5.0],
		    "longitude":[190.0, 240.0]}
    },
    "Nino12": {
        "value": 0.0,
        "domain": { "latitude":[-10.0, 0.0],
		    "longitude":[270.0, 280.0]}
    },
    "AMMS": {
        "value": 0.0,
        "domain": { "latitude":[-15.0, -5.0],
		    "longitude":[-20.0, 10.0]}
    },
    "AMMN": {
        "value": 0.0,
        "domain": { "latitude":[5.0, 15.0],
		    "longitude":[-50.0, -20.0]}
    },
    "ATL3": {
        "value": 0.0,
        "domain": { "latitude":[-3.0, 3.0],
		    "longitude":[-20.0, 0.0]}
    },
    "TSA": {
        "value": 0.0,
        "domain": { "latitude":[-20.0, 0.0],
		    "longitude":[-30.0, 10.0]}
    },
    "TNA": {
        "value": 0.0,
        "domain": { "latitude":[5.5, 23.5],
		    "longitude":[302.5, 345.0]}
    },
    "TIO": {
        "value": 0.0,
        "domain": { "latitude":[-15.0, 15.0],
		    "longitude":[40.0, 115.0]}
    },
    "IODE": {
        "value": 0.0,
        "domain": { "latitude":[-10.0, 10.0],
		    "longitude":[50.0, 70.0]}
    },
    "IODW": {
        "value": 0.0,
        "domain": { "latitude":[-10.0, 0.0],
		    "longitude":[90.0, 110.0]}
    },
    "SOCN": {
        "value": 0.0,
        "domain": { "latitude":[-70.0, -50.0],
		    "longitude":[0.0, 360.0]}
    },
    "CONUS_RRM": {
        "domain": { "latitude":[20.0, 50.0],
                    "longitude":[-125.0, -65.0]}
    },
    "EastAsia_RRM": {
        "domain": { "latitude":[8.0, 50.0],
                    "longitude":[70.0, 142.5]}
    },
    "Amazon_RRM": {
        "domain": { "latitude":[-28.5, 14.0],
                    "longitude":[-88.5, -31.0]}
    }
}
EOF

# file for aliases of observation datasets
cat > reference_alias.json << EOF
{
  "rlds" : {
           "defaultpi"  : "NOAA-20C",
           "default"    : "ceres_ebaf_v4.1",
           "alternatc1" : "ceres_ebaf_v4.0",
           "alternatc2" : "ceres_ebaf_v2.8",
           "alternatd1" : "Tropflux",
           "alternatd2" : "COREv2-Flux",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "rldscs" : {
           "defaultpi"  : "NOAA-20C",
           "default"    : "ceres_ebaf_v4.1",
           "alternatc1" : "ceres_ebaf_v4.0",
           "alternatc2" : "ceres_ebaf_v2.8",
           "alternatd1" : "Tropflux",
           "alternatd2" : "COREv2-Flux",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "rlus" : {
           "defaultpi"  : "NOAA-20C",
           "default"    : "ceres_ebaf_v4.1",
           "alternatc1" : "ceres_ebaf_v4.0",
           "alternatc2" : "ceres_ebaf_v2.8",
           "alternatd1" : "Tropflux",
           "alternatd2" : "COREv2-Flux",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "rsds" : {
           "defaultpi"  : "NOAA-20C",
           "default"    : "ceres_ebaf_v4.1",
           "alternatc1" : "ceres_ebaf_v4.0",
           "alternatc2" : "ceres_ebaf_v2.8",
           "alternatd1" : "Tropflux",
           "alternatd2" : "COREv2-Flux",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "rsdscs" : {
           "defaultpi"  : "NOAA-20C",
           "default"    : "ceres_ebaf_v4.1",
           "alternatc1" : "ceres_ebaf_v4.0",
           "alternatc2" : "ceres_ebaf_v2.8",
           "alternatd1" : "Tropflux",
           "alternatd2" : "COREv2-Flux",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },

  "rsus" : {
           "defaultpi"  : "NOAA-20C",
           "default"    : "ceres_ebaf_v4.1",
           "alternatc1" : "ceres_ebaf_v4.0",
           "alternatc2" : "ceres_ebaf_v2.8",
           "alternatd1" : "Tropflux",
           "alternatd2" : "COREv2-Flux",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "rsuscs": {
           "defaultpi"  : "NOAA-20C",
           "default"    : "ceres_ebaf_v4.1",
           "alternatc1" : "ceres_ebaf_v4.0",
           "alternatc2" : "ceres_ebaf_v2.8",
           "alternatd1" : "Tropflux",
           "alternatd2" : "COREv2-Flux",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "rstcre" : {
           "defaultpi"  : "NOAA-20C",
           "default"    : "ceres_ebaf_v4.1",
           "alternatc1" : "ceres_ebaf_v4.0",
           "alternatc2" : "ceres_ebaf_v2.8",
           "alternatd1" : "Tropflux",
           "alternatd2" : "COREv2-Flux",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "rltcre" : {
           "defaultpi"  : "NOAA-20C",
           "default"    : "ceres_ebaf_v4.1",
           "alternatc1" : "ceres_ebaf_v4.0",
           "alternatc2" : "ceres_ebaf_v2.8",
           "alternatd1" : "Tropflux",
           "alternatd2" : "COREv2-Flux",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "rlut" : {
           "defaultpi"  : "NOAA-20C",
           "default"    : "ceres_ebaf_v4.1",
           "alternatc1" : "ceres_ebaf_v4.0",
           "alternatc2" : "ceres_ebaf_v2.8",
           "alternatd1" : "Tropflux",
           "alternatd2" : "COREv2-Flux",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "rlutcs" : {
           "defaultpi"  : "NOAA-20C",
           "default"    : "ceres_ebaf_v4.1",
           "alternatc1" : "ceres_ebaf_v4.0",
           "alternatc2" : "ceres_ebaf_v2.8",
           "alternatd1" : "Tropflux",
           "alternatd2" : "COREv2-Flux",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "rsdt" : {
           "defaultpi"  : "NOAA-20C",
           "default"    : "ceres_ebaf_v4.1",
           "alternatc1" : "ceres_ebaf_v4.0",
           "alternatc2" : "ceres_ebaf_v2.8",
           "alternatd1" : "Tropflux",
           "alternatd2" : "COREv2-Flux",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "rsut" : {
           "defaultpi"  : "NOAA-20C",
           "default"    : "ceres_ebaf_v4.1",
           "alternatc1" : "ceres_ebaf_v4.0",
           "alternatc2" : "ceres_ebaf_v2.8",
           "alternatd1" : "Tropflux",
           "alternatd2" : "COREv2-Flux",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "rsutcs" : {
           "defaultpi"  : "NOAA-20C",
           "default"    : "ceres_ebaf_v4.1",
           "alternatc1" : "ceres_ebaf_v4.0",
           "alternatc2" : "ceres_ebaf_v2.8",
           "alternatd1" : "Tropflux",
           "alternatd2" : "COREv2-Flux",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "rtmt" : {
           "defaultpi"  : "NOAA-20C",
           "default"    : "ceres_ebaf_v4.1",
           "alternatc1" : "ceres_ebaf_v4.0",
           "alternatc2" : "ceres_ebaf_v2.8",
           "alternatd1" : "Tropflux",
           "alternatd2" : "COREv2-Flux",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "pr" : {
           "defaultpi"  : "NOAA-20C",
           "default"    : "GPCP_v2.3",
           "alternatc6" : "GPCP_v2.2",
           "alternatc7" : "GPCP_1DD",
           "alternatc3" : "GPCP_v3.2",
           "alternatc4" : "CMAP_v1902",
           "alternatc5" : "TRMM-3B43v-7",
           "alternatd1" : "Tropflux",
           "alternatd2" : "COREv2-Flux",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "prc" : {
           "defaultpi"  : "NOAA-20C",
           "default"    : "ERA5",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "prsn" : {
           "defaultpi"  : "NOAA-20C",
           "default"    : "ERA5",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "prw" : {
           "defaultpi"  : "NOAA-20C",
           "default"    : "ERA5",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "psl" : {
           "defaultpi"  : "NOAA-20C",
           "default"    : "ERA5",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "ps" : {
           "defaultpi"  : "NOAA-20C",
           "default"    : "ERA5",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "huss" : {
           "defaultpi"  : "NOAA-20C",
           "default"    : "MERRA2",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "ta" : {
           "defaultpi"  : "NOAA-20C",
           "default"    : "ERA5",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "ua" : {
           "defaultpi"  : "NOAA-20C",
           "default"    : "ERA5",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "va" : {
           "defaultpi"  : "NOAA-20C",
           "default"    : "ERA5",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "hur" : {
           "defaultpi"  : "NOAA-20C",
           "default"    : "ERA5",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "wap" : {
           "defaultpi"  : "NOAA-20C",
           "default"    : "ERA5",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "zg" : {
           "defaultpi"  : "NOAA-20C",
           "default"    : "ERA5",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "o3" : {
           "defaultpi"  : "NOAA-20C",
           "default"    : "ERA5",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "hus" : {
           "defaultpi"  : "NOAA-20C",
           "default"    : "ERA5",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "uas" : {
           "defaultpi"  : "NOAA-20C",
           "default"    : "ERA5",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "vas" : {
           "defaultpi"  : "NOAA-20C",
           "default"    : "ERA5",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "tauu" : {
           "defaultpi"  : "NOAA-20C",
           "default"    : "ERA5",
           "alternatd1" : "Tropflux",
           "alternatd2" : "COREv2-Flux",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "taux" : {
           "defaultpi"  : "NOAA-20C",
           "default"    : "ERA5",
	   "alternatd1" : "Tropflux",
           "alternatd2" : "COREv2-Flux",
           "alternatd3" : "OAFlux",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "tauv" : {
           "defaultpi"  : "NOAA-20C",
           "default"    : "ERA5",
           "alternatd1" : "Tropflux",
           "alternatd2" : "COREv2-Flux",
           "alternatd3" : "OAFlux",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "tauy" : {
           "defaultpi"  : "NOAA-20C",
           "default"    : "ERA5",
           "alternatd1" : "Tropflux",
           "alternatd2" : "COREv2-Flux",
           "alternatd3" : "OAFlux",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "tas" : {
           "defaultpi"  : "NOAA-20C",
           "default"    : "ERA5",
           "alternatd1" : "Tropflux",
           "alternatd2" : "COREv2-Flux",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "ts" : {
           "defaultpi"  : "NOAA-20C",
           "default"    : "ERA5",
           "alternatd1" : "Tropflux",
           "alternatd2" : "COREv2-Flux",
           "alternatc8" : "HadISST",
           "alternatd4" : "HadISST2",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "sst" : {
           "defaultpi"  : "HadISST",
           "default"    : "HadISST",
           "alternatd1" : "Tropflux",
           "alternatd2" : "COREv2-Flux",
           "alternatc8" : "HadISST",
           "alternatd4" : "HadISST2",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "sfcWind" : {
           "defaultpi"  : "NOAA-20C",
           "default"    : "NOAA-20C",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "hfls" : {
           "defaultpi"  : "NOAA-20C",
           "default"    : "ERA5",
           "alternatd1" : "Tropflux",
           "alternatd2" : "COREv2-Flux",
           "alternatd3" : "OAFlux",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "hfss" : {
           "defaultpi"  : "NOAA-20C",
           "default"    : "ERA5",
           "alternatd1" : "Tropflux",
           "alternatd2" : "COREv2-Flux",
           "alternatd3" : "OAFlux",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "thf" : {
           "defaultpi"  : "NOAA-20C",
           "default"    : "ERA5",
           "alternatd1" : "Tropflux",
           "alternatd2" : "COREv2-Flux",
           "alternatd3" : "OAFlux",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "evspsbl" : {
           "defaultpi"  : "NOAA-20C",
           "default"    : "ERA5",
           "alternatd1" : "Tropflux",
           "alternatd2" : "COREv2-Flux",
           "alternatd3" : "OAFlux",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "clt" : {
           "defaultpi"  : "NOAA-20C",
           "default"    : "ERA5",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "clwvi" : {
           "defaultpi"  : "NOAA-20C",
           "default"    : "ERA5",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "clivi" : {
           "defaultpi"  : "NOAA-20C",
           "default"    : "ERA5",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "tasmin" : {
           "defaultpi"  : "NOAA-20C",
           "default"    : "MERRA2",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "tasmax" : {
           "defaultpi"  : "NOAA-20C",
           "default"    : "MERRA2",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "sic" : {
           "defaultpi"  : "HadISST2",
           "default"    : "HadISST2",
           "alternatc8" : "HadISST",
           "alternatd1" : "Tropflux",
           "alternatd2" : "COREv2-Flux",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "tos" : {
           "defaultpi"  : "HadISST2",
           "default"    : "HadISST2",
           "alternatc8" : "HadISST",
           "alternatd1" : "Tropflux",
           "alternatd2" : "COREv2-Flux",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "ssh" : {
           "defaultpi"  : "AVISO",
           "default"    : "AVISO",
           "alternatd1" : "Tropflux",
           "alternatd2" : "COREv2-Flux",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "zos" : {
           "defaultpi"  : "AVISO",
           "default"    : "AVISO",
           "alternatd1" : "Tropflux",
           "alternatd2" : "COREv2-Flux",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           },
  "sos" : {
           "defaultpi"  : "Aquarius",
           "default"    : "Aquarius",
           "alternatd1" : "Tropflux",
           "alternatd2" : "COREv2-Flux",
           "alternate1" : "ERA5",
           "alternate2" : "MERRA2",
           "alternate3" : "ERA-Interim",
           "alternate4" : "NOAA-20C",
           "alternate5" : "FAKE-FUTURE1",
           "alternate6" : "FAKE-FUTURE2"
           }
}
EOF

# file for list of variables for synthetic_metrics metric plots
cat > synthetic_metrics_list.json << EOF
{
    "mean_climate" : {
            "mae_xy" : {
                    "name"   : "Mean Absolute Error Normalized by Median",
                    "type"   : ["portrait"],
                    "region" : ["global","ocean","land","NHEX","SHEX","TROPICS"],
                    "season" : ["djf", "mam", "jja", "son"]
            },
	    "cor_xy"  : {
		    "name"   : "Pattern Corr.",
		    "type"   : ["portrait"],
		    "region" : ["global","ocean","land","NHEX","SHEX","TROPICS"],
		    "season" : ["djf", "mam", "jja", "son"]
	    },
	    "rms_xy"  : {
		    "name"   : "RMSE Normalized by Median",
		    "type"   : ["portrait"],
                    "region" : ["global","ocean","land","NHEX","SHEX","TROPICS"],
		    "season" : ["djf", "mam", "jja", "son"]
	    },
            "bias_xy" : {
                    "name"   : "Annual Mean Bias",
                    "type"   : ["parcoord"],
                    "region" : ["global","ocean","land","NHEX","SHEX","TROPICS"],
                    "season" : ["ann"]
            },
	    "rms_xyt" : {
		    "name"   : "Spatiotemporal RMSE",
		    "type"   : ["parcoord"],
                    "region" : ["global","ocean","land","NHEX","SHEX","TROPICS"],
		    "season" : ["ann"]
	    }
    },
    "variability_modes" : {
	    "rms"  : {
                    "name"   : "RMSE Normalized by Median",
                    "type"   : ["portrait","parcoord"],
                    "season" : []
	    },
	    "rmsc" : {
                    "name"   : "CenteredRMSE Normalized by Median",
                    "type"   : ["portrait","parcoord"],
                    "season" : []
	    },
	    "stdv_pc_ratio_to_obs" : {
		    "name"   : "Amplitude Ratio to Reference",
		    "type"   : ["portrait","parcoord"],
		    "season" : []
	    }
    },
    "enso_metric" : {
           "skill" : {
	           "collection" : ["ENSO_perf", "ENSO_tel", "ENSO_proc"],
                   "type"       : ["portrait"],
                   "season"     : []
            }
    }
}
EOF


create_links_acyc_climo() {
  local ts_dir_source="$1"
  local ts_dir_destination="$2"
  local begin_year="$3"
  local end_year="$4"
  local name_key="$5"
  local error_num="$6"

  echo "create_links_acyc_climo: linking from ${ts_dir_source} to ${ts_dir_destination}"

  mkdir -p "${ts_dir_destination}"
  cd "${ts_dir_destination}" || exit

  local variables="pr,tas"
  local script_dir="/zppy_snapshot/output/post/scripts"
  local prefix="pcmdi_diags_mean_climate_model_vs_obs_1985-1986"
  local ts_step="2"
  local dofm=(15.5 45 74.5 105 125.5 166 196.5 227.5 258 288.5 319 349.5)

  for v in ${variables//,/ }; do
    > "${v}_files.txt"  # Start fresh

    shopt -s nullglob
    for year in $(seq "${begin_year}" "${ts_step}" "${end_year}"); do
      local YYYY
      YYYY=$(printf "%04d" "${year}")
      for file in ${ts_dir_source}/${v}_*_${YYYY}*.nc; do
        [[ -f "${file}" ]] && echo "${file}" >> "${v}_files.txt"
      done
    done
    shopt -u nullglob

    if [[ -s "${v}_files.txt" ]]; then
      local ncra_failed=0
      # Derive monthly climatology files
      for month in $(seq 1 12); do
        local MM
        MM=$(printf "%02d" "${month}")
        run_nco ncra -O -h -F -d time,"${month}",,12 $(< "${v}_files.txt") "${v}_clm_${MM}.nc"
        if [[ $? -ne 0 ]]; then
          ncra_failed=1
          break
        fi
      done

      if [[ ${ncra_failed} -ne 0 ]]; then
        rm -f "${v}_clm_"*.nc "${v}_files.txt"
        cd "${script_dir}" || exit
        echo "ERROR (${error_num})" > "${prefix}.status"
        exit "${error_num}"
      fi

      # Combine to form full annual cycle file
      local combined_name="${name_key}.${v}.${begin_year}01-${end_year}12.AC.${case_id}.nc"
      run_nco ncrcat -O -d time,0, "${v}_clm_"*.nc "${combined_name}"
      if [[ $? -ne 0 ]]; then
        rm -f "${v}_clm_"*.nc "${v}_files.txt"
        cd "${script_dir}" || exit
        echo "ERROR (${error_num})" > "${prefix}.status"
        exit "${error_num}"
      fi

      # Adjust time metadata for PCMDI diagnostics
      local cmdfix1='time[time]={15.5, 45, 74.5, 105, 125.5, 166, 196.5, 227.5, 258, 288.5,319, 349.5}'
      local cmdfix2='time_bnds[time,bnds]={0,31,31,59,59,90,90,120,120,151,151,181,181,212,212,243,243,273,273,304,304,334,334,365.}'
      local cmdfix3='time@units="days since 1850-01-01 00:00:00"'
      local cmdfix4='time@calendar="noleap"'
      local cmdfix5='time@bounds="time_bnds"'
      run_nco ncap2 -O -h -s "${cmdfix1};${cmdfix2};${cmdfix3};${cmdfix4};${cmdfix5}" "${combined_name}" "${combined_name}"
      if [[ $? -ne 0 ]]; then
        rm -f "${v}_clm_"*.nc "${v}_files.txt"
        cd "${script_dir}" || exit
        echo "ERROR (${error_num})" > "${prefix}.status"
        exit "${error_num}"
      fi

      rm -vf "${v}_clm_"*.nc
      rm -f "${v}_files.txt"
    else
      echo "Warning: No input files found for variable ${v} in ${ts_dir_source}. Skipping."
      rm -f "${v}_files.txt"
    fi
  done

  if [ -z "$( ls . )" ]; then
    echo "create_links_acyc_climo: ${ts_dir_destination} was not updated!"
  fi

  cd ..
}


create_links_acyc_climo_obs() {
  local ts_dir_source="$1"
  local ts_dir_destination="$2"
  local begin_year="$3"
  local end_year="$4"
  local error_num="$5" # Will use error_num +0,+1,+2

  local script_dir="/zppy_snapshot/output/post/scripts"
  local prefix="pcmdi_diags_mean_climate_model_vs_obs_1985-1986"
  local dofm=(15.5 45 74.5 105 125.5 166 196.5 227.5 258 288.5 319 349.5)

  echo "create_links_acyc_climo_obs: linking from ${ts_dir_source} to ${ts_dir_destination}"

  mkdir -p "${ts_dir_destination}"
  cd "${ts_dir_destination}" || exit

  for file in ${ts_dir_source}/*; do
    local fname
    local YYYYS YYYYE
    local SUBSTR
    local ttag tmp_file MM combined_name

    fname=$(basename "${file}")
    if [[ ! ${fname} =~ ".nc" ]]; then
      # Skip non-.nc files
      continue
    fi

    # Match two time patterns (YYYYMM or YYYYMMDD) separated by _ or -
    if [[ $fname =~ ^(.+)\.([0-9]{4})([0-9]{2}){1,2}[-_]([0-9]{4})([0-9]{2}){1,2}\.nc$ ]]; then
      SUBSTR="${BASH_REMATCH[1]}"   # everything before the .YYYY...
      YYYYS="${BASH_REMATCH[2]}"    # start year (4 digits)
      YYYYE="${BASH_REMATCH[4]}"    # end year (4 digits)
    else
      echo "Warning: Could not extract dates from ${fname}, basename of ${file}"
      continue
    fi

    # Check if observation record overlaps the requested period
    if [[ ${YYYYS} -gt ${end_year} || ${YYYYE} -lt ${begin_year} ]]; then
      echo "create_links_acyc_climo_obs: ${fname} (years ${YYYYS}-${YYYYE}) does not overlap requested range ${begin_year}-${end_year}; using available range ${YYYYS}-${YYYYE}."
    else
      # Clip to specified year range
      if [[ ${YYYYS} -lt ${begin_year} ]]; then
        YYYYS="${begin_year}"
      fi
      if [[ ${YYYYE} -gt ${end_year} ]]; then
        YYYYE="${end_year}"
      fi
    fi

    ttag="$(printf "%04d" "${YYYYS}")01-$(printf "%04d" "${YYYYE}")12"
    tmp_file="tmp_combine_${ttag}.nc"

    run_nco ncrcat -O -d time,"${YYYYS}-01-01","${YYYYE}-12-31" "${file}" "${tmp_file}"
    if [[ $? -ne 0 ]]; then
      echo "WARNING: ncrcat failed for ${fname} (date range ${YYYYS}-${YYYYE}), skipping."
      rm -f "${tmp_file}"
      continue
    fi

    # Derive monthly climatology
    for month in $(seq 1 12); do
      MM=$(printf "%02d" ${month})
      run_nco ncra -O -h -F -d time,"${month}",,12 "${tmp_file}" "tmp_clm_${MM}.nc"
      if [[ $? -ne 0 ]]; then
        echo "WARNING: ncra failed for ${fname} month ${MM}, skipping file."
        rm -f tmp_clm_*.nc "${tmp_file}"
        break  # exit the month loop
      fi
    done
    # If any month failed, the tmp_clm files were cleaned up — skip to next file
    if ! ls tmp_clm_*.nc &>/dev/null; then
      continue
    fi

    combined_name="${SUBSTR}.${ttag}.AC.${case_id}.nc"
    run_nco ncrcat -O tmp_clm_*.nc "${combined_name}"
    if [[ $? -ne 0 ]]; then
      cd "${script_dir}" || exit
      echo "ERROR (${error_num})" > "${prefix}.status"
      exit "${error_num}"
    fi

    # Adjust time metadata
    local cmdfix1='time[time]={15.5, 45, 74.5, 105, 125.5, 166, 196.5, 227.5, 258, 288.5,319, 349.5}'
    local cmdfix2='time@units="days since 1850-01-01 00:00:00"'
    local cmdfix3='time@calendar="noleap"'
    run_nco ncap2 -O -h -s "${cmdfix1};${cmdfix2};${cmdfix3}" "${combined_name}" "${combined_name}"
    if [[ $? -ne 0 ]]; then
      cd "${script_dir}" || exit
      echo "ERROR (${error_num})" > "${prefix}.status"
      exit "$((error_num + 1))"
    fi

    local cmdfix4='defdim("bnds",2)'
    local cmdfix5='time_bnds=make_bounds(time,$bnds,"time_bnds")'
    local cmdfix6='time_bnds@units=time@units'
    local cmdfix7='time_bnds@calendar=time@calendar'
    run_nco ncap2 -O -h -s "${cmdfix4};${cmdfix5};${cmdfix6};${cmdfix7}" "${combined_name}" "${combined_name}"
    if [[ $? -ne 0 ]]; then
      cd "${script_dir}" || exit
      echo "ERROR (${error_num})" > "${prefix}.status"
      exit "$((error_num + 2))"
    fi

    rm -vf tmp_*.nc
  done

  if [ -z "$( ls . )" ]; then
    echo "create_links_acyc_climo_obs: ${ts_dir_destination} was not updated!"
  fi

  cd ..
}





########################
# Prepare the model data
########################

# Define output directory for climatology files
climo_dir_primary="climo"
# Path to model's monthly climatology files
# This cmip_ts path is created via zppy/templates/e3sm_to_cmip.bash
climo_dir_source="/zppy_snapshot/output/post/atm/180x360_aave/cmip_ts/monthly"
# Link and process primary model climo data
create_links_acyc_climo "${climo_dir_source}" "${climo_dir_primary}" "${Y1}" "${Y2}" "${model_name}.${tableID}" 1






###########################################################################
# Prepare the observation data
# Observation datasets vary by diagnostic, so we use an external
# Python utility to handle linking and remapping to standard names.
###########################################################################
obstmp_dir="obs_link"
mkdir -p "${obstmp_dir}"
echo "Linking observational data into ${obstmp_dir}..."

###################
# Run process job
###################
echo "Linking observational data using SLURM..."

command="zi-pcmdi-link-observation --model_name_ref ${model_name_ref} --tableID_ref ${tableID_ref} --vars=${source_vars} --obs_sets default --obs_ts /usr/workspace/e3sm/data/diagnostics/observations/Atm/time-series/ --obstmp_dir ${obstmp_dir} --debug ${debug,,}"
echo "Running a zi-pcmdi command: ${command}"

set -e

set +e

time eval "${command}"

if [ $? -ne 0 ]; then
  cd /zppy_snapshot/output/post/scripts
  echo "ERROR (5)" > pcmdi_diags_mean_climate_model_vs_obs_1985-1986.status
  exit 5
fi

set -e
source /usr/workspace/e3sm/apps/e3sm-unified/load_latest_e3sm_unified_dane.sh
set +e

#######################################################
# Now create obs climo and time series for PCMDI diags
# Use same period as test model when possible
#######################################################
ts_dir_ref_source="/zppy_snapshot/output/post/scripts/${workdir}/${obstmp_dir}"


climo_dir_ref=climo_ref
# This will use errors code 6,7,8:
create_links_acyc_climo_obs "${ts_dir_ref_source}" "${climo_dir_ref}" ${ref_Y1} ${ref_Y2} 6





########################################################
# generate basic parameter file for pcmdi metrics driver
########################################################
echo "About to create parameterfile.py, which will be passed in with -p"
echo "The current directory is: $PWD" # This will be of the form .../post/scripts/tmpDir

cat > parameterfile.py << EOF
import os
import sys
import json
#####################
# Basic Information
#####################

start_yr = int('${Y1}')
end_yr = int('${Y2}')
num_years = end_yr - start_yr + 1
period = f"{start_yr:04d}01-{end_yr:04d}12"

model_parts = '${model_name}'.split('.')
mip, exp, product, realm = model_parts[:4]

##############################################
# Configuration Shared with PCMDI Diagnostics
##############################################

# Whether to generate NetCDF outputs for observations and model results
nc_out_obs = True
nc_out_model = True

# Output file extension: use .nc if either output is enabled,
# otherwise default to .xml
ext = ".nc" if nc_out_model or nc_out_obs else ".xml"

# User annotation and debug flag
user_notes = 'Provenance and results'
debug = False

# Enable plot generation for model and observation
plot = True
plot_obs = True  # optional

# Execution mode and output format
run_type = 'model_vs_obs'
figure_format = 'png'

# Save interpolated model climatologies?
save_test_clims = True

# Save all metrics results in a single file?
# Set to 'n' as metrics are computed per variable
metrics_in_single_file = 'n'

# Custom values for land/sea masking
regions_values = {
    "land": 100.0,
    "ocean": 0.0
}

# Template path for land/sea mask file (fixed input)
modpath_lf = os.path.join(
    'fixed',
    'sftlf.%(model).nc'
)



############################################
# Setup Specific for Mean Climate Metrics
############################################
modver = "${case_id}"
parallel = False
generate_sftlf = False
sftlf_filename_template = modpath_lf

# Target grid: can be '2.5x2.5' or a CDMS2 grid object string
target_grid = '1x1'
targetGrid = target_grid  # for backward compatibility
target_grid_string = '1px1p'

# Regridding tool and method (general use)
# OPTIONS: 'regrid2' or 'esmf'
regrid_tool = 'esmf'
# OPTIONS: 'linear' or 'conservative' (only for 'esmf')
regrid_method = 'regrid2'

# Regridding tool and method for ocean diagnostics
regrid_tool_ocn = 'esmf'  # 'regrid2' or 'esmf'
regrid_method_ocn = ('conservative')  # 'linear' or 'conservative'

# Model realization(s) to consider
realization = "*"

# Model product name from input
test_data_set = [product]

# Path to model climatology files
test_data_path = '${climo_dir_primary}'

# Template for model climatology filenames
filename_template = '.'.join([
    mip,
    exp,
    '%(model)',
    '%(realization)',
    '${tableID}',
    '%(variable)',
    period,
    'AC',
    '${case_id}',
    'nc'
])

# Path to reference climatology files
reference_data_path = '${climo_dir_ref}'

# Observation catalogue file (dynamic by subsection)
custom_observations = os.path.join(
    'pcmdi_diags',
    '{}_{}_catalogue.json'.format(
        '${climo_dir_ref}',
        'mean_climate'
    )
)

# Load variable-specific region definitions
regions = json.load(open('regions.json'))

# Load predefined region specifications and normalize domain lat/lon as tuples
regions_specs = json.load(open('regions_specs.json'))
for key in regions_specs:
    domain = regions_specs[key].get('domain', {})
    if 'latitude' in domain:
        domain['latitude'] = tuple(domain['latitude'])
        regions_specs[key]['domain']['latitude'] = domain['latitude']
    if 'longitude' in domain:
        domain['longitude'] = tuple(domain['longitude'])
        regions_specs[key]['domain']['longitude'] = domain['longitude']

# METRICS OUTPUT
metrics_output_path = os.path.join(
    'pcmdi_diags',
    'metrics_results',
    'mean_climate',
    mip,
    exp,
    '%(case_id)'
)

#INTERPOLATED MODELS' CLIMATOLOGIES
diagnostics_output_path = os.path.join(
    'pcmdi_diags',
    'diagnostic_results',
    'mean_climate',
    mip,
    exp,
    '%(case_id)'
)

test_clims_interpolated_output = diagnostics_output_path







EOF



################################################################
# Run PCMDI Diags
echo
echo ===== RUN PCMDI DIAGS =====
echo
################################

echo "About to set up a zi-pcmdi command"
echo "The current directory is: $PWD" # This will be of the form .../post/scripts/tmpDir

# Run diagnostics
mkdir -p pcmdi_diags



source_dirs="--climo_ts_dir_primary ${climo_dir_primary} --climo_ts_dir_ref ${climo_dir_ref}"

# Parameter passing can encounter errors if parameters are empty.
# So, it's a good idea to make sure they can't be (or at least are unlikely to be) empty.
# run_type == "model_vs_obs" only: obs_sets (default value is NOT "")
# run_type == "model_vs_model" only: model_name_ref, tableID_ref (default values are NOT "")
core_parameters="--num_workers 24 --multiprocessing True --subsection mean_climate ${source_dirs} --model_name ${model_name} --model_tableID Amon --figure_format png  --run_type model_vs_obs --obs_sets default --model_name_ref ${model_name_ref} --vars ${source_vars} --tableID_ref ${tableID_ref} --generate_sftlf True --case_id ${case_id} --results_dir ${results_dir} --debug ${debug,,}"



command="zi-pcmdi-mean-climate ${core_parameters} --regions global"





# Run diagnostics
set -e

set +e

echo "Running a zi-pcmdi command: ${command}"
echo "The current directory is: $PWD" # This will be of the form .../post/scripts/tmpDir
time ${command}
if [ $? != 0 ]; then
  cd /zppy_snapshot/output/post/scripts
  echo 'ERROR (12)' > pcmdi_diags_mean_climate_model_vs_obs_1985-1986.status
  exit 12
fi

set -e
source /usr/workspace/e3sm/apps/e3sm-unified/load_latest_e3sm_unified_dane.sh
set +e

#################################
# Copy output to web server
echo
echo ===== COPY FILES TO WEB SERVER =====
echo

# Create top-level directory
mkdir -p ${web_dir}
if [ $? != 0 ]; then
  cd /zppy_snapshot/output/post/scripts
  echo 'ERROR (13)' > pcmdi_diags_mean_climate_model_vs_obs_1985-1986.status
  exit 13
fi



############################################
# Copy files
#rsync -a --delete ${results_dir} ${web_dir}/

rsync -a ${results_dir} ${web_dir}/
if [ $? != 0 ]; then
  cd /zppy_snapshot/output/post/scripts
  echo 'ERROR (14)' > pcmdi_diags_mean_climate_model_vs_obs_1985-1986.status
  exit 14
fi






# Delete temporary workdir
cd ..
if [[ "${debug,,}" != "true" ]]; then
  rm -rf ${workdir}
fi

# Update status file and exit

ENDTIME=$(date +%s)
ELAPSEDTIME=$(($ENDTIME - $STARTTIME))

echo ==============================================
echo "Elapsed time: $ELAPSEDTIME seconds"
echo ==============================================
rm -f pcmdi_diags_mean_climate_model_vs_obs_1985-1986.status
echo 'OK' > pcmdi_diags_mean_climate_model_vs_obs_1985-1986.status
exit 0