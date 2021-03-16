#!/bin/bash
{% include 'slurm_header.sh' %}
{% include 'e3sm_unified' %}sh

# Additional settings for MPAS-Analysis
export OMP_NUM_THREADS=1
export HDF5_USE_FILE_LOCKING=FALSE

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
echo "RUNNING ${id}" > {{ scriptDir }}/{{ prefix }}.status

# Basic definitions
case="{{ case }}"
www="{{ www }}"
tsY1="{{ '%04d' % (ts_year1) }}"
tsY2="{{ '%04d' % (ts_year2) }}"
ensoY1="{{ '%04d' % (enso_year1) }}"
ensoY2="{{ '%04d' % (enso_year2) }}"
climY1="{{ '%04d' % (climo_year1) }}"
climY2="{{ '%04d' % (climo_year2) }}"

# Job identifier
identifier=ts_${tsY1}-${tsY2}_climo_${climY1}-${climY2}

# Set-up work directory structure
echo
echo ===== SET UP MPAS-ANALYSIS DIRECTORY STRUCTURE =====
echo

workdir='../analysis/mpas_analysis'
mkdir -p ${workdir}
cd ${workdir}

{% if purge == true %}
# If purge is on, delete previous directory
  rm -rf ${identifier}
{% endif %}

mkdir -p ${identifier}
mkdir -p cfg

{% if cache == true %}
# Restore cached copies of pre-computed files
cached=( "timeseries/moc" "timeseries/OceanBasins" "timeseries/transport" )
mkdir -p cache
for subdir in "${cached[@]}"
do
  mkdir -p cache/${subdir} ${identifier}/${subdir}
  rsync -av cache/${subdir}/ ${identifier}/${subdir}/
done
{% endif %}

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
mainRunName = {{ case }}

# preprocessedReferenceRunName is the name of a reference run that has been
# preprocessed to compare against (or None to turn off comparison).  Reference
# runs of this type would have preprocessed results because they were not
# performed with MPAS components (so they cannot be easily ingested by
# MPAS-Analysis)
preprocessedReferenceRunName = None

# config file for a control run to which this run will be compared.  The
# analysis should have already been run to completion once with this config
# file, so that the relevant MPAS climatologies already exist and have been
# remapped to the comparison grid.  Leave this option commented out if no
# control run is desired.
# controlRunConfigFile = /path/to/config/file

# config file for a main run on which the analysis was already run to
# completion.  The relevant MPAS climatologies already exist and have been
# remapped to the comparison grid and time series have been extracted.
# Leave this option commented out if the analysis for the main run should be
# performed.
# mainRunConfigFile = /path/to/config/file


[execute]
## options related to executing parallel tasks

# the number of parallel tasks (1 means tasks run in serial, the default)
parallelTaskCount = {{ parallelTaskCount }}

# the parallelism mode in ncclimo ("serial" or "bck")
# Set this to "bck" (background parallelism) if running on a machine that can
# handle 12 simultaneous processes, one for each monthly climatology.
ncclimoParallelMode = bck


[diagnostics]
## config options related to observations, mapping files and region files used
## by MPAS-Analysis in diagnostics computations.

# The base path to the diagnostics directory.  Typically, this will be a shared
# directory on each E3SM supported machine (see the example config files for
# its location).  For other machines, this would be the directory pointed to
# when running "download_analysis_data.py" to get the public observations,
# mapping files and region files.
{% if machine == 'compy' %}
baseDirectory = /compyfs/diagnostics
{% elif machine == 'cori' %}
baseDirectory = /global/cfs/cdirs/e3sm/diagnostics
{% elif machine in ['anvil', 'chrysalis'] %}
baseDirectory = /lcrc/group/acme/diagnostics
{% endif %}

# Directory for mapping files (if they have been generated already). If mapping
# files needed by the analysis are not found here, they will be generated and
# placed in the output mappingSubdirectory.  The user can supply an absolute
# path here to point to a path that is not within the baseDirectory above.
mappingSubdirectory = mpas_analysis/maps

# Directory for region mask files. The user can supply an absolute path here to
# point to a path that is not within the baseDirectory above.
regionMaskSubdirectory = mpas_analysis/region_masks


[input]
## options related to reading in the results to be analyzed

# directory containing model results
baseDirectory = {{ input }}

# Note: an absolute path can be supplied for any of these subdirectories.
# A relative path is assumed to be relative to baseDirectory.
# By default, results are assumed to be directly in baseDirectory,
# i.e. <baseDirecory>/./

# subdirectory containing restart files
runSubdirectory = {{ input }}/run
# subdirectory for ocean history files
oceanHistorySubdirectory = {{ input }}/{{ subdir_ocean }}
seaIceHistorySubdirectory = {{ input }}/{{ subdir_ice }}

# names of namelist and streams files, either a path relative to baseDirectory
# or an absolute path.
oceanNamelistFileName = {{ input }}/run/{{ mpaso_nml }}
oceanStreamsFileName = {{ input }}/run/{{ stream_ocn }}
seaIceNamelistFileName = {{ input }}/run/{{ mpassi_nml }}
seaIceStreamsFileName = {{ input }}/run/{{ stream_ice }}

# names of ocean and sea ice meshes (e.g. oEC60to30, oQU240, oRRS30to10, etc.)
mpasMeshName = {{ mesh }}


[output]
## options related to writing out plots, intermediate cached data sets, logs,
## etc.

# directory where analysis should be written
# NOTE: This directory path must be specific to each test case.
baseDirectory = {{ scriptDir }}/${workdir}/${identifier}

# subdirectories within baseDirectory for analysis output
scratchSubdirectory = scratch
plotsSubdirectory = plots
logsSubdirectory = logs
mpasClimatologySubdirectory = clim/mpas
mappingSubdirectory = mapping
timeSeriesSubdirectory = timeseries
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
generate = {{ generate }}

[climatology]
## options related to producing climatologies, typically to compare against
## observations and previous runs

# the first year over which to average climatalogies
startYear = ${climY1}
# the last year over which to average climatalogies
endYear = ${climY2}

[timeSeries]
## options related to producing time series plots, often to compare against
## observations and previous runs

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
usePostprocessingScript = {{ PostMOC }}

[oceanObservations]
## options related to ocean observations with which the results will be
## compared

# subdirectory within [diagnostics]/baseDirectory where ocean observations are
# stored.  The user can supply an absolute path here to point to a path that is
# not within [diagnostics]/baseDirectory.
obsSubdirectory = observations/Ocean

[oceanPreprocessedReference]
## options related to preprocessed ocean reference run with which the results
## will be compared (e.g. a POP, CESM or ACME v0 run)

# directory where ocean reference simulation results are stored
baseDirectory = /dir/to/ocean/reference

[seaIceObservations]
## options related to sea ice observations with which the results will be
## compared

# subdirectory within [diagnostics]/baseDirectory where sea ice observations
# are stored.  The user can supply an absolute path here to point to a path
# that is not within [diagnostics]/baseDirectory.
obsSubdirectory = observations/SeaIce

[seaIcePreprocessedReference]
## options related to preprocessed sea ice reference run with which the results
## will be compared (e.g. a CICE, CESM or ACME v0 run)

# directory where ocean reference simulation results are stored
baseDirectory = /dir/to/seaice/reference

[icebergObservations]
## options related to iceberg observations with which the results will be
## compared

# subdirectory within [diagnostics]/baseDirectory where iceberg observations
# are stored.  The user can supply an absolute path here to point to a path
# that is not within [diagnostics]/baseDirectory.
obsSubdirectory = observations/Icebergs

EOF

# Run diagnostics
{% if purge == true %}
purge="--purge"
{% else %}
purge=""
{% endif %}
srun -N 1 -n 1 mpas_analysis ${purge} --verbose cfg/mpas_analysis_${identifier}.cfg
if [ $? != 0 ]; then
  echo 'ERROR (1)' > {{ scriptDir }}/{{ prefix }}.status
  exit 1
fi

# Check master log for obvious errors
size=`wc -c ${identifier}/logs/taskProgress.log | awk '{print $1}'`
error=`grep ERROR ${identifier}/logs/taskProgress.log | wc -l`
if [ "${size}" = "" ] || [ "${size}" = "0" ] || [ "${error}" != "0" ];then
  echo 'ERROR (2)' > {{ scriptDir }}/{{ prefix }}.status
  exit 1
fi

{% if cache == true %}
# Cache copies of selected files
echo
echo ===== CACHE OUTPUT FILES =====
echo
for subdir in "${cached[@]}"
do
  rsync -av ${identifier}/${subdir}/ cache/${subdir}/
done
{% endif %}

# Copy output to web server
echo
echo ===== COPY FILES TO WEB SERVER =====
echo

# Create top-level directory
f=${www}/${case}/mpas_analysis/${identifier}/
mkdir -p ${f}
if [ $? != 0 ]; then
  echo 'ERROR (3)' > {{ scriptDir }}/{{ prefix }}.status
  exit 1
fi

{% if machine == 'cori' %}
# For NERSC cori, make sure it is world readable
f=`realpath ${f}`
while [[ $f != "/" ]]
do
  owner=`stat --format '%U' $f`
  if [ "${owner}" = "${USER}" ]; then
    chgrp e3sm $f
    chmod go+rx $f
  fi
  f=$(dirname $f)
done
{% endif %}

# Copy files
rsync -a --delete ${identifier}/html/ ${www}/${case}/mpas_analysis/${identifier}/
if [ $? != 0 ]; then
  echo 'ERROR (4)' > {{ scriptDir }}/{{ prefix }}.status
  exit 1
fi

{% if machine == 'cori' %}
# For NERSC cori, change permissions of new files
pushd ${www}/${case}/mpas_analysis/
chgrp -R e3sm ${identifier}
chmod -R go+rX,go-w ${identifier}
popd
{% endif %}

{% if machine in ['anvil', 'chrysalis'] %}
# For LCRC, change permissions of new files
pushd ${www}/${case}/mpas_analysis/
chgrp -R e3sm ${identifier}
chmod -R go+rX,go-w ${identifier}
popd
{% endif %}

# Update status file and exit
{% raw %}
ENDTIME=$(date +%s)
ELAPSEDTIME=$(($ENDTIME - $STARTTIME))
{% endraw %}
echo ==============================================
echo "Elapsed time: $ELAPSEDTIME seconds"
echo ==============================================
echo 'OK' > {{ scriptDir }}/{{ prefix }}.status
exit 0

