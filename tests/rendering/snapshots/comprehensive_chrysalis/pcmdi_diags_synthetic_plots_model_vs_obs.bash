#!/bin/bash

# Running on chrysalis

#SBATCH  --job-name=pcmdi_diags_synthetic_plots_model_vs_obs
#SBATCH  --account=e3sm
#SBATCH  --nodes=1
#SBATCH  --output=/zppy_snapshot/output/post/scripts/pcmdi_diags_synthetic_plots_model_vs_obs.o%j
#SBATCH  --exclusive
#SBATCH  --time=2:00:00


#SBATCH  --partition=compute


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
echo "RUNNING ${id}" > pcmdi_diags_synthetic_plots_model_vs_obs.status

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
  if echo "source /lcrc/soft/climate/e3sm-unified/load_latest_e3sm_unified_chrysalis.sh" | grep -Eq 'test_e3sm_unified|load_latest_e3sm_unified'; then
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
source /lcrc/soft/climate/e3sm-unified/load_latest_e3sm_unified_chrysalis.sh
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


# For synthetic_plots, discover the case_id from files written by upstream jobs,
# since those jobs may have run on a different calendar date.
clim_dir_discover=${www}/${case}/pcmdi_diags/model_vs_obs/metrics_data/mean_climate/
case_id=$(find "${clim_dir_discover}" -name "*.v*.json" 2>/dev/null \
           | grep -oP '\.v\d{8}\.' | head -1 | tr -d '.')
if [[ -z "${case_id}" ]]; then
  echo "WARNING: Could not discover case_id from upstream output; falling back to today's date."
  case_id=v$(date '+%Y%m%d')
fi


# Create temporary workdir
workdir=`mktemp -d tmp.pcmdi_diags_synthetic_plots_model_vs_obs.${id}.XXXX`
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





########################
# Prepare the model data
########################








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








#add command for mean climate viewer
clim_keys="--clim_viewer True --cmip_clim_dir /lcrc/group/e3sm/diagnostics/pcmdi_data/metrics_data/mean_climate --cmip_clim_set cmip6.historical.v20250927 --clim_vars pr,psl,rlut,rsut,tas,ts,ta-200,ta-850,ua-200,ua-850,va-200,va-850 --clim_years 1985-1988 --clim_regions global"

echo "Checking if *.${case_id}.json files exist in clim_dir:"
clim_dir=${web_dir}/model_vs_obs/metrics_data/mean_climate/
find ${clim_dir} -name "*.${case_id}*.json"
echo "Done checking. There should be a list of files above, if they exist."


#add command for modes variability viewer
movs_keys="--mova_viewer True --movc_viewer True --cmip_movs_dir /lcrc/group/e3sm/diagnostics/pcmdi_data/metrics_data/variability_modes --cmip_movs_set cmip6.historical.v20220825 --mova_modes NAM,NAO,PNA,NPO,SAM --mova_vars psl --mova_years 1985-1988 --movc_modes PDO,NPGO --movc_vars ts --movc_years 1985-1988"

echo "Checking if var_mode_*.json files exist in variability_modes_dir:"
variability_modes_dir=${web_dir}/model_vs_obs/metrics_data/variability_modes/
find ${variability_modes_dir} -name "var_mode_*${case_id}*.json"
echo "Done checking. There should be a list of files above, if they exist."


#add command for enso viewer
enso_keys="--enso_viewer True --cmip_enso_dir /lcrc/group/e3sm/diagnostics/pcmdi_data/metrics_data/enso_metric --cmip_enso_set cmip6.historical.v20210620 --enso_vars psl,pr,ts,tas,tauu,tauv,hfls,hfss,rlds,rsds,rlus,rlut,rsdt --enso_years 1985-1988"

echo "Checking if var_mode_*.json files exist in variability_modes_dir:"
enso_dir=${web_dir}/model_vs_obs/metrics_data/enso_metric/*
find ${enso_dir} -name "*.${case_id}*.json"
echo "Done checking. There should be a list of files above, if they exist."


command="zi-pcmdi-synthetic-plots --synthetic_sets portrait,parcoord --figure_format png --www ${www} --results_dir ${results_dir} --case v3.LR.historical_0051 --model_name e3sm.historical.v3-LR.0051 --model_tableID Amon --web_dir=${web_dir} --pcmdi_webtitle E3SM-PMP-Diagnostics --pcmdi_version v3.8.2 --run_type ${run_type} --pcmdi_external_prefix /lcrc/group/e3sm/diagnostics --pcmdi_viewer_template pcmdi_data/viewer --save_all_data True ${clim_keys} ${movs_keys} ${enso_keys} --debug ${debug,,}"



# Run diagnostics
set -e

set +e

echo "Running a zi-pcmdi command: ${command}"
echo "The current directory is: $PWD" # This will be of the form .../post/scripts/tmpDir
time ${command}
if [ $? != 0 ]; then
  cd /zppy_snapshot/output/post/scripts
  echo 'ERROR (12)' > pcmdi_diags_synthetic_plots_model_vs_obs.status
  exit 12
fi

set -e
source /lcrc/soft/climate/e3sm-unified/load_latest_e3sm_unified_chrysalis.sh
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
  echo 'ERROR (13)' > pcmdi_diags_synthetic_plots_model_vs_obs.status
  exit 13
fi



############################################
# Copy files
#rsync -a --delete ${results_dir} ${web_dir}/





# For LCRC, change permissions of new files
pushd ${web_dir}/
chmod -R go+rX,go-w ${results_dir}
popd


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
rm -f pcmdi_diags_synthetic_plots_model_vs_obs.status
echo 'OK' > pcmdi_diags_synthetic_plots_model_vs_obs.status
exit 0