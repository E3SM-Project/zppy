#!/bin/bash

# Running on compy

#SBATCH  --job-name=mpas_analysis_ts_1985-1986_climo_1985-1986
#SBATCH  --account=e3sm
#SBATCH  --nodes=1
#SBATCH  --output=/zppy_snapshot/output/post/scripts/mpas_analysis_ts_1985-1986_climo_1985-1986.o%j
#SBATCH  --exclusive
#SBATCH  --time=00:30:00


#SBATCH  --qos=regular
#SBATCH  --partition=slurm


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
echo "RUNNING ${id}" > mpas_analysis_ts_1985-1986_climo_1985-1986.status

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
  if echo "source /share/apps/E3SM/conda_envs/load_latest_e3sm_unified_compy.sh" | grep -Eq 'test_e3sm_unified|load_latest_e3sm_unified'; then
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
source /share/apps/E3SM/conda_envs/load_latest_e3sm_unified_compy.sh
set +e

set_pkg_manager
echo "${pkg_manager} list mpas-analysis:"
${pkg_manager} list mpas-analysis || true # If we can't print this, just continue on.

# Additional settings for MPAS-Analysis
export OMP_NUM_THREADS=1
export HDF5_USE_FILE_LOCKING=FALSE
ulimit -s unlimited 2>/dev/null || true



# Basic definitions
case="v3.LR.historical_0051"
www="/zppy_snapshot/www"
tsY1="1985"
tsY2="1986"
ensoY1="1985"
ensoY2="1986"
climY1="1985"
climY2="1986"

# Job identifier
identifier=ts_${tsY1}-${tsY2}_climo_${climY1}-${climY2}
output_dir_name="ts_1985-1986_climo_1985-1986"

# Set-up work directory structure
echo
echo ===== SET UP MPAS-ANALYSIS DIRECTORY STRUCTURE =====
echo

workdir="../analysis/mpas_analysis/mvo"
mkdir -p ${workdir}
cd ${workdir}



mkdir -p ${output_dir_name}
mkdir -p cfg


# Restore cached copies of pre-computed files
cached=( "timeseries/moc" "timeseries/OceanBasins" "timeseries/transport" )
cache_dir="/zppy_snapshot/output/post/scripts/../analysis/mpas_analysis/cache"
mkdir -p ${cache_dir}
for subdir in "${cached[@]}"
do
  mkdir -p ${cache_dir}/${subdir} ${output_dir_name}/${subdir}
  rsync -av ${cache_dir}/${subdir}/ ${output_dir_name}/${subdir}/
done
files=( "mpasIndexOcean.nc" "mpasTimeSeriesOcean.nc" "seaIceAreaVolNH.nc" "seaIceAreaVolSH.nc")
for file in "${files[@]}"
do
  cp ${cache_dir}/timeseries/${file} ${output_dir_name}/timeseries/${file}
done


# Run MPAS-Analysis
echo
echo ===== RUN MPAS-ANALYSIS =====
echo

# Prepare configuration file
cat > cfg/mpas_analysis_${identifier}.cfg << EOF

## This file contains the most common config options that a user might want
## to customize.  The values are the same as in mpas_analysis/config.default,
## the default config file, which has all possible configuration options.
## Usage:
##  1. Copy this file to a new name for a specific run (say config.myrun).
##  2. Modify any config options you want to change in your new config file.
##     At a minimum, you need to specify:
##       * [runs]/mainRunName -- A name for the run to be included plot titles
##                               and legends
##       * [input]/baseDirectory -- The directory for the simulation results
##                                  to analyze
##       * [input]/mpasMeshName -- The name of the MPAS ocean/sea ice mesh
##       * [output]/baseDirectory -- The directory for the analysis results
##       * [oceanObservations]/baseDirectory -- The directory for the analysis
##                                              ocean observations
##       * [seaIceObservations]/baseDirectory -- The directory for the analysis
##                                               sea ice observations
##       * [regions]/regionMaskDirectory -- a directory containing MOC and
##                                          ice shelf region masks
##  3. run: mpas_analysis config.myrun.  This will read the configuraiton
##     first from config.default and then replace that configuraiton with any
##     changes from from config.myrun
##  4. If you want to run a subset of the analysis, you can either set the
##     generate option under [output] in your config file or use the
##     --generate flag on the command line.  See the comments for 'generate'
##     in the '[output]' section below for more details on this option.


[runs]
## options related to the run to be analyzed and control runs to be
## compared against

# mainRunName is a name that identifies the simulation being analyzed.
mainRunName = v3.LR.historical_0051




[execute]
## options related to executing parallel tasks

# the number of parallel tasks (1 means tasks run in serial, the default)
parallelTaskCount = 12

# the parallelism mode in ncclimo ("serial" or "bck")
# Set this to "bck" (background parallelism) if running on a machine that can
# handle 12 simultaneous processes, one for each monthly climatology.
ncclimoParallelMode = bck

# the number of total threads to use when ncclimo runs in "bck" or "mpi" mode.
# Reduce this number if ncclimo is crashing (maybe because it is out of memory).
# The number of threads must be a factor of 12 (1, 2, 3, 4, 6 or 12).
ncclimoThreads = 12

# the number of MPI tasks to use in creating mapping files (1 means tasks run in
# serial, the default)
mapMpiTasks = 6

# "None" if ESMF should perform remapping in serial without a command, or one of
# "srun" or "mpirun" if it should be run in parallel  (or in serial but with a
# command)

mapParallelExec = srun --mpi=pmi2


# "None" if ncremap should perform remapping without a command, or "srun"
# possibly with some flags if it should be run with that command

ncremapParallelExec = srun --mpi=pmi2 -n 1



[diagnostics]
## config options related to observations, mapping files and region files used
## by MPAS-Analysis in diagnostics computations.

# The base path to the diagnostics directory.  Typically, this will be a shared
# directory on each E3SM supported machine (see the example config files for
# its location).  For other machines, this would be the directory pointed to
# when running "download_analysis_data.py" to get the public observations,
# mapping files and region files.

baseDirectory = /compyfs/diagnostics


[input]
## options related to reading in the results to be analyzed

# directory containing model results
baseDirectory = /zppy_snapshot/input/v3.LR.historical_0051

# Note: an absolute path can be supplied for any of these subdirectories.
# A relative path is assumed to be relative to baseDirectory.
# By default, results are assumed to be directly in baseDirectory,
# i.e. <baseDirecory>/./

# subdirectory containing restart files
runSubdirectory = /zppy_snapshot/input/v3.LR.historical_0051/run
# subdirectory for ocean history files
oceanHistorySubdirectory = /zppy_snapshot/input/v3.LR.historical_0051//archive/ocn/hist
seaIceHistorySubdirectory = /zppy_snapshot/input/v3.LR.historical_0051//archive/ice/hist

# names of namelist and streams files, either a path relative to baseDirectory
# or an absolute path.
oceanNamelistFileName = /zppy_snapshot/input/v3.LR.historical_0051/run/mpaso_in
oceanStreamsFileName = /zppy_snapshot/input/v3.LR.historical_0051/run/streams.ocean
seaIceNamelistFileName = /zppy_snapshot/input/v3.LR.historical_0051/run/mpassi_in
seaIceStreamsFileName = /zppy_snapshot/input/v3.LR.historical_0051/run/streams.seaice

# names of ocean and sea ice meshes (e.g. oEC60to30, oQU240, oRRS30to10, etc.)
mpasMeshName = IcoswISC30E3r5


[output]
## options related to writing out plots, intermediate cached data sets, logs,
## etc.

# directory where analysis should be written
# NOTE: This directory path must be specific to each test case.
baseDirectory = /zppy_snapshot/output/post/scripts/${workdir}/${output_dir_name}

# provide an absolute path to put HTML in an alternative location (e.g. a web
# portal)
htmlSubdirectory = html

# a list of analyses to generate.  Valid names can be seen by running:
#   mpas_analysis --list
# This command also lists tags for each analysis.
# Shortcuts exist to generate (or not generate) several types of analysis.
# These include:
#   'all' -- all analyses will be run
#   'all_publicObs' -- all analyses for which observations are availabe on the
#                      public server (the default)
#   'all_<tag>' -- all analysis with a particular tag will be run
#   'all_<component>' -- all analyses from a given component (either 'ocean'
#                        or 'seaIce') will be run
#   'only_<component>', 'only_<tag>' -- all analysis from this component or
#                                       with this tag will be run, and all
#                                       analysis for other components or
#                                       without the tag will be skipped
#   'no_<task_name>' -- skip the given task
#   'no_<component>', 'no_<tag>' -- in analogy to 'all_*', skip all analysis
#                                   tasks from the given compoonent or with
#                                   the given tag.  Do
#                                      mpas_analysis --list
#                                   to list all task names and their tags
# an equivalent syntax can be used on the command line to override this
# option:
#    mpas_analysis config.analysis --generate \
#         only_ocean,no_timeSeries,timeSeriesSST
generate = ['all', 'no_landIceCavities', 'no_BGC', 'no_icebergs', 'no_min', 'no_max', 'no_sose', 'no_waves', 'no_eke', 'no_climatologyMapAntarcticMelt', 'no_regionalTSDiagrams', 'no_timeSeriesAntarcticMelt', 'no_timeSeriesOceanRegions', 'no_climatologyMapSose', 'no_woceTransects', 'no_soseTransects', 'no_geojsonTransects', 'no_oceanRegionalProfiles', 'no_hovmollerOceanRegions', 'no_oceanConservation']

[climatology]
## options related to producing climatologies, typically to compare against
## observations and previous runs

# reference year for anomaly
anomalyRefYear = 1

# the first year over which to average climatalogies
startYear = ${climY1}
# the last year over which to average climatalogies
endYear = ${climY2}

[timeSeries]
## options related to producing time series plots, often to compare against
## observations and previous runs

# reference year for anomaly
anomalyRefYear = 1

# start and end years for timeseries analysis. Using out-of-bounds values
#   like start_year = 1 and end_year = 9999 will be clipped to the valid range
#   of years, and is a good way of insuring that all values are used.
startYear = ${tsY1}
endYear = ${tsY2}

[index]
## options related to producing nino index.

# start and end years for the nino 3.4 analysis.  Using out-of-bounds values
#   like start_year = 1 and end_year = 9999 will be clipped to the valid range
#   of years, and is a good way of insuring that all values are used.
# For valid statistics, index times should include at least 30 years
startYear = ${ensoY1}
endYear = ${ensoY2}

[streamfunctionMOC]
## options related to plotting the streamfunction of the meridional overturning
## circulation (MOC)
# Use postprocessing script to compute the MOC? You want this to be True
# for low-resolution simulations that use GM to parameterize eddies, because
# the online MOC analysis member currently does not include the bolus velocity
# in its calculation, whereas the postprocessing script does.
# NOTE: this is a temporary option that will be removed once the online
# MOC takes into account the bolus velocity when GM is on.
usePostprocessingScript = False

EOF

# Run diagnostics

purge=""



extra_config=""


# MPAS-Analysis appends to taskProgress.log rather than overwriting it, so
# ERROR lines from a previous (failed) run would make a successful rerun fail
# the check below. Set the old log aside so the check only sees this run.
task_progress_log=${output_dir_name}/logs/taskProgress.log
if [ -f ${task_progress_log} ]; then
  mv ${task_progress_log} ${task_progress_log}.$(date +%Y%m%d_%H%M%S)
fi

mpas_analysis ${purge} --verbose ${extra_config} cfg/mpas_analysis_${identifier}.cfg
if [ $? != 0 ]; then
  echo 'ERROR (1)' > /zppy_snapshot/output/post/scripts/mpas_analysis_ts_1985-1986_climo_1985-1986.status
  exit 1
fi

# Check master log for obvious errors
size=`wc -c ${task_progress_log} | awk '{print $1}'`
error=`grep ERROR ${task_progress_log} | wc -l`
if [ "${size}" = "" ] || [ "${size}" = "0" ] || [ "${error}" != "0" ];then
  echo 'ERROR (2)' > /zppy_snapshot/output/post/scripts/mpas_analysis_ts_1985-1986_climo_1985-1986.status
  exit 2
fi


# Cache copies of selected files
echo
echo ===== CACHE OUTPUT FILES =====
echo
for file in "${files[@]}"
do
  cp ${output_dir_name}/timeseries/${file} ${cache_dir}/timeseries/${file}
done
for subdir in "${cached[@]}"
do
  rsync -av ${output_dir_name}/${subdir}/ ${cache_dir}/${subdir}/
done
# Remove one particularly large file which does not need to be cached
rm ${output_dir_name}/timeseries/mpasTimeSeriesSeaIce.nc


# Copy output to web server
echo
echo ===== COPY FILES TO WEB SERVER =====
echo

# Create top-level directory
f=${www}/${case}/mpas_analysis/mvo/${output_dir_name}/
mkdir -p ${f}
if [ $? != 0 ]; then
  echo 'ERROR (3)' > /zppy_snapshot/output/post/scripts/mpas_analysis_ts_1985-1986_climo_1985-1986.status
  exit 3
fi



# Copy files
rsync -a --delete ${output_dir_name}/html/ ${www}/${case}/mpas_analysis/mvo/${output_dir_name}/
if [ $? != 0 ]; then
  echo 'ERROR (4)' > /zppy_snapshot/output/post/scripts/mpas_analysis_ts_1985-1986_climo_1985-1986.status
  exit 4
fi





# Update status file and exit

ENDTIME=$(date +%s)
ELAPSEDTIME=$(($ENDTIME - $STARTTIME))

echo ==============================================
echo "Elapsed time: $ELAPSEDTIME seconds"
echo ==============================================
cd /zppy_snapshot/output/post/scripts
rm -f mpas_analysis_ts_1985-1986_climo_1985-1986.status
echo 'OK' > mpas_analysis_ts_1985-1986_climo_1985-1986.status
exit 0