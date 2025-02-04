#!/bin/bash
{% include 'inclusions/slurm_header.sh' %}

{{ environment_commands }}

# Turn on debug output if needed
debug={{ debug }}
if [[ "${debug,,}" == "true" ]]; then
  set -x
fi

# Need this setup as otherwise can not generate diagnostics
export UCX_SHM_DEVICES=all # or not set UCX_NET_DEVICES at all

# Make sure UVCDAT doesn't prompt us about anonymous logging
export UVCDAT_ANONYMOUS_LOG=False

# Script dir
cd {{ scriptDir }}

# Get jobid
id=${SLURM_JOBID}

# Update status file
STARTTIME=$(date +%s)
echo "RUNNING ${id}" > {{ prefix }}.status

# Basic definitions
case="{{ case }}"
www="{{ www }}"
{% if "synthetic_plots" not in subsection %}
y1={{ year1 }}
y2={{ year2 }}
Y1="{{ '%04d' % (year1) }}"
Y2="{{ '%04d' % (year2) }}"
{% if run_type == "model_vs_model" %}
ref_Y1="{{ '%04d' % (ref_year1) }}"
ref_Y2="{{ '%04d' % (ref_year2) }}"
{%- endif %}
{%- endif %}
run_type="{{ run_type }}"
tag="{{ tag }}"

results_dir=${tag} #_${Y1}-${Y2}

ref_name={{ ref_name }}

##################################################
#info to construct pcmdi-preferred data convension
##################################################
model_name='{{ model_name }}'
tableID='{{ model_tableID }}'
{% if run_type == "model_vs_obs" %}
model_name_ref='obs.historical.%(model).00'
tableID_ref=${tableID}
{% elif run_type == "model_vs_model" %}
model_name_ref='{{ model_name_ref }}'
tableID_ref='{{ model_tableID_ref }}'
{%- endif %}
case_id=v$(date '+%Y%m%d')

# Create temporary workdir
workdir=`mktemp -d tmp.${id}.XXXX`
cd ${workdir}

# utility file for pcmdi-zppy workflow
cp -r '{{pcmdi_external_prefix}}/{{pcmdi_zppy_util}}'   .

# files for definition of regions for regional mean
cp -r '{{pcmdi_external_prefix}}/{{regions_specs}}'     .

# file for aliases of observation datasets
cp -r '{{pcmdi_external_prefix}}/{{reference_alias}}'   .

# file for list of variables for synthetic_metrics metric plots
cp -r '{{pcmdi_external_prefix}}/{{synthetic_metrics}}' .

{%- if ("mean_climate" in subsection) %}
#further simplification could be done in future
create_links_acyc_climo()
{
  ts_dir_source=$1
  ts_dir_destination=$2
  begin_year=$3
  end_year=$4
  name_key=$5
  error_num=$6
  # Create netcdf files for time series variables
  mkdir -p ${ts_dir_destination}
  cd ${ts_dir_destination}
  # https://stackoverflow.com/questions/27702452/loop-through-a-comma-separated-shell-variable
  variables="{{ cmip_vars }}"
  for v in ${variables//,/ }
  do
    # Go through the time series files for between year1 and year2, using a step size equal to the number of years per time series file
    for year in `seq ${begin_year} {{ ts_num_years }} ${end_year}`;
    do
      YYYY=`printf "%04d" ${year}`
      for file in ${ts_dir_source}/${v}_*_${YYYY}*.nc
      do
        # Add this time series file to the list of files for cdscan to use
        echo ${file} >> ${v}_files.txt
      done
    done
    #derive annual cycle climate mean
    dofm=(15 46 74 105 125 166 196 227 258 288 319 349) #middle day of month
    for month in `seq 1 1 12`;
    do
      MM=`printf "%02d" ${month}`
      MDAY=dofm[${month}-1]
      cat ${v}_files.txt | ncra -O -h -F -d "time,${month},,12" ${v}_clm_${MM}.nc
    done
    #Concatenate files to form the annual cycle monthly climatology file
    combined_name="${name_key}.${v}.${begin_year}01-${end_year}12.AC.${case_id}.nc"
    ncrcat -O -d time,0, ${v}_clm_*.nc ${combined_name}
    #modify time to avoid issues in pcmdi calculation
    ncap2 -O -h -s 'time[time]={15.5, 45, 74.5, 105, 125.5, 166, 196.5, 227.5, 258, 288.5,319, 349.5};time_bnds[time,bnds]={0, 31, 31, 59, 59, 90, 90, 120, 120, 151, 151, 181, 181, 212, 212, 243, 243, 273, 273, 304, 304, 334, 334, 365.};time@units="days since 1850-01-01 00:00:00";time@calendar="noleap";time@bounds="time_bnds"' ${combined_name} ${combined_name}
    rm -rvf ${v}_clm_*.nc
    if [ $? != 0 ]; then
      cd {{ scriptDir }}
      echo "ERROR (${error_num})" > {{ prefix }}.status
      exit ${error_num}
    fi
  done
  cd ..
}

{% if run_type == "model_vs_obs" %}
create_links_acyc_climo_obs()
{
  ts_dir_source=$1
  ts_dir_destination=$2
  begin_year=$3
  end_year=$4
  error_num=$5
  # Create netcdf files for time series variables
  mkdir -p ${ts_dir_destination}
  cd ${ts_dir_destination}
  for file in ${ts_dir_source}/*.nc
  do
    fname=`basename $file`
    PREFIX=${fname: :-17}
    YYYYS=${fname: -16:-10}
    YYYYE=${fname: -9:-3}
    if [[ ${YYYYS} < ${begin_year} ]];then
      YYYYS=${begin_year}
    fi
    if [[ ${YYYYE} > ${end_year} ]];then
      YYYYE=${end_year}
    fi
    ttag=`printf "%04d" ${YYYYS}`01-`printf "%04d" ${YYYYE}`12
    # select the interest period
    tmp_file="tmp_combine_${ttag}.nc"
    ncrcat -d time,"${YYYYS}-01-01,${YYYYE}-12-31" ${file} ${tmp_file}
    # Go through the time serie file, and derive annual cycle climate mean
    dofm=(15 46 74 105 125 166 196 227 258 288 319 349) #middle day of month
    for month in `seq 1 1 12`;
    do
      MM=`printf "%02d" ${month}`
      MDAY=dofm[${month}-1]
      ncra -O -h -F -d "time,${month},,12"  ${tmp_file} tmp_clm_${MM}.nc
    done
    #Concatenate files to form the annual cycle monthly climatology file
    combined_name="${PREFIX}.${ttag}.AC.${case_id}.nc"
    ncrcat -O -d time,0, tmp_clm_*.nc ${combined_name}
    #modify time to avoid issues in pcmdi calculation
    ncap2 -O -h -s 'time[time]={15.5, 45, 74.5, 105, 125.5, 166, 196.5, 227.5, 258, 288.5,319, 349.5};time@units="days since 1850-01-01 00:00:00";time@calendar="noleap";' ${combined_name} ${combined_name}
    ncap2 -O -h -s 'defdim("bnds",2);time_bnds=make_bounds(time,$bnds,"time_bnds");time_bnds@units=time@units;time_bnds@calendar=time@calendar' ${combined_name} ${combined_name}
    rm -rvf tmp_*.nc
    if [ $? != 0 ]; then
      cd {{ scriptDir }}
      echo "ERROR (${error_num})" > {{ prefix }}.status
      exit ${error_num}
    fi
  done
  cd ..
}
{%- endif %}
{%- endif %}

{%- if ("variability_modes_cpl" in subsection) or ("variability_modes_atm" in subsection) or ("enso" in subsection) %}
create_links_ts()
{
  ts_dir_source=$1
  ts_dir_destination=$2
  begin_year=$3
  end_year=$4
  subname=$5
  error_num=$6
  # Create netcdf files for time series variables
  mkdir -p ${ts_dir_destination}
  cd ${ts_dir_destination}
  # https://stackoverflow.com/questions/27702452/loop-through-a-comma-separated-shell-variable
  variables="{{ vars }}"
  for v in ${variables//,/ }
  do
    # Go through the time series files for between year1 and year2, using a step size equal to the number of years per time series file
    for year in `seq ${begin_year} {{ ts_num_years }} ${end_year}`;
    do
      YYYY=`printf "%04d" ${year}`
      for file in ${ts_dir_source}/${v}_*_${YYYY}*.nc
      do
        # Add this time series file to the list of files for cdscan to use
        echo ${file} >> ${v}_files.txt
      done
done
    # netcdf file will be combined to cover the whole period from year1 to year2
    combined_name="${subname}.${v}.${begin_year}01-${end_year}12.nc"
    cat ${v}_files.txt | ncrcat -v ${v} -d "time,${begin_year}-01-01,${end_year}-12-31" ${combined_name}
    #modify time to avoid issues in pcmdi calculation
    ncap2 -O -h -s 'defdim("bnds",2);time_bnds=make_bounds(time,$bnds,"time_bnds");time_bnds@units=time@units;time_bnds@calendar=time@calendar' ${combined_name} ${combined_name}
    if [ $? != 0 ]; then
      cd {{ scriptDir }}
      echo "ERROR (${error_num})" > {{ prefix }}.status
      exit ${error_num}
    fi
  done
  cd ..
}

{% if run_type == "model_vs_obs" %}
create_links_ts_obs()
{
  ts_dir_source=$1
  ts_dir_destination=$2
  begin_year=$3
  end_year=$4
  error_num=$5
  # Create netcdf files for time series variables
  mkdir -p ${ts_dir_destination}
  cd ${ts_dir_destination}
  for file in ${ts_dir_source}/*.nc
  do
    fname=`basename $file`
    PREFIX=${fname: :-17}
    YYYYS=${fname: -16:-12}
    YYYYE=${fname: -9:-5}
    if [[ ${YYYYS} < ${begin_year} ]];then
      YYYYS=${begin_year}
    fi
    if [[ ${YYYYE} > ${end_year} ]];then
      YYYYE=${end_year}
    fi
    ttag=`printf "%04d" ${YYYYS}`01-`printf "%04d" ${YYYYE}`12
    # Go through the time series files and extract analysis period
    combined_name=${PREFIX}.${ttag}.nc
    ncrcat -d time,${YYYYS}-01-01,${YYYYE}-12-31 ${file} ${combined_name}
    #modify time to avoid issues in pcmdi calculation
    ncap2 -O -h -s 'defdim("bnds",2);time_bnds=make_bounds(time,$bnds,"time_bnds");time_bnds@units=time@units;time_bnds@calendar=time@calendar' ${combined_name} ${combined_name}
    if [ $? != 0 ]; then
      cd {{ scriptDir }}
      echo "ERROR (${error_num})" > {{ prefix }}.status
      exit ${error_num}
    fi
  done
  cd ..
}
{%- endif %}
{%- endif %}

########################
#prepare the model data
########################
{%- if ("mean_climate" in subsection) %}
climo_dir_primary=climo
# Create local links to input climo files
climo_dir_source={{ output }}/post/atm/{{ grid }}/cmip_ts/monthly
create_links_acyc_climo ${climo_dir_source} ${climo_dir_primary} ${Y1} ${Y2} ${model_name}.${tableID} 1
{% if run_type == "model_vs_model" %}
# Create local links to input climo files (ref model)
climo_dir_source_ref={{ reference_data_path }}
climo_dir_ref=climo_ref
create_links_acyc_climo ${climo_dir_source_ref} ${climo_dir_ref} ${ref_Y1} ${ref_Y2} ${model_name_ref}.${tableID_ref} 2
{%- endif %}
{%- endif %}

{%- if ("variability_modes_cpl" in subsection) or ("variability_modes_atm" in subsection) or ("enso" in subsection) %}
#all diags will be run with ts data
ts_dir_primary=ts
# Create netcdf files for time series variables
ts_dir_source={{ output }}/post/atm/{{ grid }}/cmip_ts/monthly
create_links_ts ${ts_dir_source} ${ts_dir_primary} ${Y1} ${Y2} ${model_name}.${tableID} 3
{% if run_type == "model_vs_model" %}
ts_dir_source_ref={{ reference_data_path_ts }}/{{ ts_num_years_ref }}yr
ts_dir_ref=ts_ref
create_links_ts ${ts_dir_source_ref} ${ts_dir_ref} ${ref_Y1} ${ref_Y2} ${model_name_ref}.${tableID_ref} 4
{%- endif %}
{%- endif %}

{% if (run_type == "model_vs_obs") and ("synthetic_plots" not in subsection) %}
#########################################################
#prepare the observation data. As observation are often
#depends on the source available for analysis, therefore,
#we use external files to help collect the information
#for pcmdi diagnostics.
#########################################################
# Create netcdf files for time series variables
obstmp_dir="obs_link"
mkdir -p ${obstmp_dir}
#create a python module to link observation data
cat > link_observation.py << EOF
import os
import re
import glob
import json
import time
import datetime
import xcdat as xc
import numpy as np
import shutil

import pcmdi_metrics
from pcmdi_metrics.io import (
        xcdat_open
)

from pcmdi_zppy_util import(
    derive_var,
)

model_name = '${model_name_ref}.${tableID_ref}'
variables = '{{ vars }}'.split(",")
obs_sets = '{{ obs_sets }}'.split(",")
ts_dir_ref_source = '{{ obs_ts }}'

# variable map from observation to cmip
altobs_dic = { "pr"      : "PRECT",
               "sst"     : "ts",
               "sfcWind" : "si10",
               "taux"    : "tauu",
               "tauy"    : "tauv",
               "rltcre"  : "toa_cre_lw_mon",
               "rstcre"  : "toa_cre_sw_mon",
               "rtmt"    : "toa_net_all_mon"}

obs_dic = json.load(open('reference_alias.json'))

########################################
#first loop: link data to work directory
########################################
for i,vv in enumerate(variables):
  if "_" in vv or "-" in vv:
    varin = re.split("_|-", vv)[0]
  else:
    varin = vv
  if len(obs_sets) > 1 and len(obs_sets) == len(variables):
    obsid = obs_sets[i]
  else:
    obsid = obs_sets[0]

  obsname = obs_dic[varin][obsid]
  if "ceres_ebaf" in obsname:
    obsstr = obsname.replace("_","*").replace("-","*")
  else:
    obsstr = obsname

  fpaths = sorted(glob.glob(os.path.join(ts_dir_ref_source,obsstr,varin+"_*.nc")))
  if (len(fpaths) > 0) and (os.path.exists(fpaths[0])):
     template = fpaths[0].split("/")[-1]
     yms = template.split("_")[-2][0:6]
     yme = template.split("_")[-1][0:6]
     obs = obsname.replace(".","_")
     out = os.path.join(
          '${obstmp_dir}',
          '{}.{}.{}-{}.nc'.format(
           model_name.replace('%(model)',obs),
           varin,yms,yme)
     )
     if not os.path.exists(out):
        os.symlink(fpaths[0],out)
  elif varin in altobs_dic.keys():
    varin1 = altobs_dic[varin]
    fpaths = sorted(glob.glob(
        os.path.join(ts_dir_ref_source,obsstr,varin1+"_*.nc"))
    )
    if (len(fpaths) > 0) and (os.path.exists(fpaths[0])):
       template = fpaths[0].split("/")[-1]
       yms = template.split("_")[-2][0:6]
       yme = template.split("_")[-1][0:6]
       obs = obsname.replace(".","_")
       out = os.path.join(
          '${obstmp_dir}',
          '{}.{}.{}-{}.nc'.format(
           model_name.replace('%(model)',obs),
           varin,yms,yme)
       )
       ds = xcdat_open(fpaths[0])
       ds = ds.rename(name_dict={varin1:varin})
       ds.to_netcdf(out)

#####################################################################
#second loop: check and process derived quantities
#note: these quantities are possibly not included as default in cmip
#####################################################################
for vv in enumerate(variables):
    if vv in ['rltcre','rstcre']:
       fpaths = sorted(glob.glob(
          os.path.join('${obstmp_dir}',"*"+vv+"_*.nc"))
       )
       if (len(fpaths) < 1) and (vv == 'rstcre'):
          derive_var('${obstmp_dir}',vv,{'rsutcs':1,'rsut':-1},model_name)
       elif (len(fpaths) < 1) and (vv == 'rltcre'):
          derive_var('${obstmp_dir}',vv,{'rlutcs':1,'rlut':-1},model_name)

EOF
###################
# run process jobs
###################
command="srun -N 1 python -u link_observation.py"
time ${command}
if [ $? != 0 ]; then
  cd {{ scriptDir }}
  echo 'ERROR (6)' > {{ prefix }}.status
  exit 6
fi
#######################################################
#now create obs climo and timeseries for pcmdi diags
#use same period as test model when possible
#######################################################
ts_dir_ref_source="{{ scriptDir }}/${workdir}/${obstmp_dir}"
{%- if ("mean_climate" in subsection) %}
climo_dir_ref=climo_ref
create_links_acyc_climo_obs ${ts_dir_ref_source} ${climo_dir_ref} ${Y1} ${Y2} 7
{%- elif ("variability_modes_cpl" in subsection) or ("variability_modes_atm" in subsection) or ("enso" in subsection) %}
ts_dir_ref=ts_ref
create_links_ts_obs ${ts_dir_ref_source} ${ts_dir_ref} ${Y1} ${Y2} 8
{%- endif %}
{%- endif %}

{% if "synthetic_plots" not in subsection %}
########################################################
# generate basic parameter file for pcmdi metrics driver
########################################################
cat > parameterfile.py << EOF
import os
import sys
import json

#####################
#basic information
#####################
start_yr = int('${Y1}')
end_yr = int('${Y2}')
num_years = end_yr - start_yr + 1
period = "{:04d}{:02d}-{:04d}{:02d}".format(start_yr,1,end_yr,12)

mip = '${model_name}'.split(".")[0]
exp = '${model_name}'.split(".")[1]
product = '${model_name}'.split(".")[2]
realm = '${model_name}'.split(".")[3]

##############################################
#Configuration shared with pcmdi diagnostics
##############################################
# Record NetCDF output
nc_out_obs = {{ mov_nc_out_obs }}
nc_out_model = {{ mov_nc_out_model }}
if nc_out_model or nc_out_obs:
  ext = ".nc"
else:
  ext = ".xml"
user_notes = 'Provenance and results'
debug = {{ pcmdi_debug }}

# Generate plots
plot_model = {{ mov_plot_model }}
plot_obs = {{ mov_plot_obs }} # optional

# Additional settings
run_type = '{{ run_type }}'
figure_format = '{{ figure_format }}'

# Save interpolated model climatology ?
save_test_clims = {{ save_test_clims }}

# Save Metrics Results in Single File ?
# option: 'y' or 'n', set to 'n' as we
# run pcmdi for each variable separately
metrics_in_single_file = 'n'

# customize land/sea mask values
regions_values = {"land":100.,"ocean":0.}

#setup template for land/sea mask (fixed)
modpath_lf = os.path.join(
    'fixed',
    'sftlf.%(model).nc'
)

############################################
#setup specific for mean climate metrics
{%- if ("mean_climate" in subsection) %}

#case id
modver = "${case_id}"

#always turn off
parallel = False

#land/sea mask file (already generated)
generate_sftlf = False
sftlf_filename_template = modpath_lf

# INTERPOLATION OPTIONS
# OPTIONS: '2.5x2.5' or an actual cdms2 grid object
target_grid = '{{ target_grid }}'
targetGrid = target_grid
target_grid_string = '{{ target_grid_string }}'
# OPTIONS: 'regrid2','esmf'
regrid_tool = '{{ regrid_tool }}'
# OPTIONS: 'linear','conservative', only if tool is esmf
regrid_method = '{{ regrid_method }}'
# OPTIONS: "regrid2","esmf"
regrid_tool_ocn = '{{ regrid_tool_ocn }}'
# OPTIONS: 'linear','conservative', only if tool is esmf
regrid_method_ocn = ( '{{ regrid_method_ocn }}' )

#######################################
# DATA LOCATION: MODELS
# ---------------------------------------------
realization = "*"
test_data_set = [ product ]
test_data_path = '${climo_dir_primary}'
# Templates for model climatology files
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

#observation info
reference_data_path = '${climo_dir_ref}'
custom_observations = os.path.join(
   'pcmdi_diags',
   '{}_{}_catalogue.json'.format(
   '${climo_dir_ref}',
   '{{subsection}}'))

#load caclulated regions for each variable
regions = json.load(open('regions.json'))

#load predefined region information
regions_specs = json.load(open('regions_specs.json'))
for key in regions_specs.keys():
  if "domain" in regions_specs[key].keys():
    if "latitude" in regions_specs[key]['domain'].keys():
      regions_specs[key]['domain']['latitude'] = tuple(
             regions_specs[key]['domain']['latitude']
      )
    if "longitude" in regions_specs[key]['domain'].keys():
      regions_specs[key]['domain']['longitude'] = tuple(
             regions_specs[key]['domain']['longitude']
      )

#######################################
# DATA LOCATION: METRICS OUTPUT
metrics_output_path = os.path.join(
    'pcmdi_diags',
    'metrics_results',
    'mean_climate',
     mip,
     exp,
    '%(case_id)'
)

############################################################
# DATA LOCATION: INTERPOLATED MODELS' CLIMATOLOGIES
diagnostics_output_path= os.path.join(
    'pcmdi_diags',
    'diagnostic_results',
    'mean_climate',
     mip,
     exp,
    '%(case_id)'
)
test_clims_interpolated_output = diagnostics_output_path

{%- endif %}

{%- if ("variability_modes" in subsection)  %}
########################################
#setup for mode variability diagnostics
########################################
seasons   = '{{ seasons }}'.split(",")
frequency = '{{ frequency }}'

#from configuration file
varModel = '{{vars}}'

#unit conversion (namelist)
ModUnitsAdjust = {{ ModUnitsAdjust }}
ObsUnitsAdjust = {{ ObsUnitsAdjust }}

# If True, maskout land region thus consider only over ocean
landmask = {{ landmask }}

#template for model file
modnames = [ product ]
realization = "*"
modpath = os.path.join(
  '${ts_dir_primary}',
  '{}.{}.%(model).%(realization).{}.%(variable).{}.nc'.format(mip,exp,'${tableID}',period)
)

#start and end year for analysis
msyear = int(start_yr)
meyear = int(end_yr)

# If True, remove Domain Mean of each time step
RmDomainMean = {{ RmDomainMean }}

# If True, consider EOF with unit variance
EofScaling = {{ EofScaling }}

# Conduct CBF analysis
CBF = {{ CBF }}

# Conduct conventional EOF analysis
ConvEOF = {{ ConvEOF }}

# Generate CMEC compliant json
cmec = False

# Update diagnostic file if exist
update_json = False

#results directory structure.
results_dir = os.path.join(
    'pcmdi_diags',
    '%(output_type)',
    'variability_modes',
    '%(mip)',
    '%(exp)',
    '${case_id}',
    '%(variability_mode)',
    '%(reference_data_name)',
)
{%- endif %}

{%- if ("enso" in subsection) %}
###########################################
#parameter setup specific for enso metrics
###########################################
modnames = [ product ]
realization = realm
modpath = os.path.join(
  '${ts_dir_primary}',
  '{}.{}.%(model).%(realization).{}.%(variable).{}.nc'.format(mip,exp,'${tableID}',period)
)

#observation/reference file catalogue
obs_cmor = True
obs_cmor_path = '${ts_dir_ref}'
obs_catalogue = 'obs_catalogue.json'

#land/sea mask for obs/reference model
reference_data_lf_path = json.load(open('obs_landmask.json'))

# METRICS COLLECTION (set in namelist, and main driver)
# metricsCollection = ENSO_perf  # ENSO_perf, ENSO_tel, ENSO_proc

# OUTPUT
results_dir = os.path.join(
    'pcmdi_diags',
    '%(output_type)',
    'enso_metric',
    '%(mip)',
    '%(exp)',
    '${case_id}',
    '%(metricsCollection)',
)

json_name = "%(mip)_%(exp)_%(metricsCollection)_${case_id}_%(model)_%(realization)"

netcdf_name = json_name

{%- endif %}

EOF
{%- endif %}

################################################################
# Run PCMDI Diags
echo
echo ===== RUN PCMDI DIAGS =====
echo
# Prepare configuration file
cat > pcmdi.py << EOF
import os
import glob
import re
import json
import time
import datetime
import xcdat as xc
import numpy as np
import pandas as pd

import collections
from collections import OrderedDict

import psutil
import subprocess
from itertools import chain
from subprocess import Popen, PIPE, call

import pcmdi_metrics

from pcmdi_metrics.graphics import (
    normalize_by_median,
)

from pcmdi_zppy_util import(
    archive_data,
    check_regions,
    check_references,
    check_units,
    childCount,
    collect_data_info,
    collect_clim_diags,
    collect_movs_diags,
    collect_enso_diags,
    collect_clim_metrics,
    collect_movs_metrics,
    create_data_lmask,
    derive_var,
    enso_obsvar_dict,
    enso_obsvar_lmsk,
    shift_row_to_bottom,
    merge_data,
    parallel_jobs,
    parcoord_metric_plot,
    portrait_metric_plot,
    serial_jobs,
    variable_region,
    mean_climate_plot_driver,
    variability_modes_plot_driver,
)

#parallel calculation
num_workers = {{ num_workers }}
if num_workers < 2:
  multiprocessing = False
else:
  multiprocessing = {{multiprocessing}}

{%- if "synthetic_plots" not in subsection %}
##############################
start_yr = int('${Y1}')
end_yr = int('${Y2}')
num_years = end_yr - start_yr + 1

# DATA LOCATION: Reference
{%- if "mean_climate" in subsection %}
test_data_path = '${climo_dir_primary}'
reference_data_path = '${climo_dir_ref}'
{%- elif ("variability_modes" in subsection) or ("enso" in subsection) %}
test_data_path = '${ts_dir_primary}'
reference_data_path = '${ts_dir_ref}'
{%- endif %}

test_data_set = ['${model_name}'.split(".")[1]]
{% if run_type == "model_vs_obs" %}
reference_data_set = '{{ obs_sets }}'.split(",")
{% elif run_type == "model_vs_model" %}
reference_data_set = ['${model_name_ref}'.split(".")[1]]
{%- endif %}

variables = '{{ vars }}'.split(",")
###############################################################
#check and process derived quantities, these quantities are
#likely not included as default in e3sm_to_cmip module
###############################################################
for i,var in enumerate(variables):
  if "_" in var or "-" in var:
    varin = re.split("_|-", var)[0]
  else:
    varin = var
  fpaths = sorted(glob.glob(os.path.join(test_data_path,"*."+var+".*.nc")))
  if len(fpaths) < 1 and varin == 'rstcre':
     derive_var(test_data_path,
                varin,{'rsutcs':1,'rsut':-1},
                '${model_name}.${tableID}')
{% if run_type == "model_vs_model" %}
     derive_var(reference_data_path,
                varin,{'rsutcs':1,'rsut':-1},
                '${model_name_ref}.${tableID_ref}')
{%- endif %}
  elif len(fpaths) < 1 and varin == 'rltcre':
     derive_var(test_data_path,
                varin,{'rlutcs':1,'rlut':-1},
                '${model_name}.${tableID}')
{% if run_type == "model_vs_model" %}
     derive_var(reference_data_path,
                varin,{'rlutcs':1,'rlut':-1},
                '${model_name_ref}.${tableID_ref}')
{%- endif %}

#######################################################
#collect and document data info in a dictionary
# for convenience of pcmdi processing
#######################################################
test_dic, obs_dic = collect_data_info(
              test_data_path,test_data_set,
              reference_data_path,reference_data_set,
              variables,'{{subsection}}','pcmdi_diags')

##########################################################
# land/sea mask is needed in PCMDI diagnostics, check and
# generate it here as these data are not always available
# for model or observations
##########################################################
if {{ generate_sftlf }} in ['true', 'y', True]:
  generate_sftlf = True
else:
  generate_sftlf = False

if generate_sftlf:
   create_data_lmask(
     test_data_path,
     reference_data_path,
     '{{subsection}}',
     'fixed')

#info to collect diagnostic output
input_template = os.path.join(
    'pcmdi_diags',
    '%(output_type)',
    '%(metric_type)',
    '${model_name}'.split(".")[0],
    '${model_name}'.split(".")[1],
    '${case_id}'
)

out_path = os.path.join(
    '${results_dir}',
    '%(group_type)'
)

{%- endif %}

{%- if "mean_climate" in subsection %}
regions = '{{regions}}'.split(",")

#assiagn region to each variable
variable_region(regions,variables)

###################################################
# generate the command list for each reference and
# each variable (will execuate in parallel later)
lstcmd = []
for var in variables:
   if "_" in var or "-" in var:
      varin = re.split("_|-", var)[0]
   else:
      varin = var
   if varin in obs_dic.keys():
      refset = obs_dic[varin]['set']
      lstcmd.append(
          " ".join(['mean_climate_driver.py', ' -p  parameterfile.py',
                    '--vars'                , '{}'.format(var),
                    '-r'                    , '{}'.format(refset),
                    '--case_id'             , '{}'.format('${case_id}')
                   ])
      )

####################################################
# call pcmdi mean climate diagnostics
####################################################
if (len(lstcmd) > 0 ) and multiprocessing:
   print("Parallel computing with {} jobs".format(str(len(lstcmd))))
   stdout,stderr,return_code = parallel_jobs(lstcmd,num_workers)
elif (len(lstcmd) > 0 ):
   print("Serial computing with {} jobs".format(str(len(lstcmd))))
   stdout,stderr,return_code = serial_jobs(lstcmd,num_workers)
else:
   print("no jobs to run...")
   return_code = 0

if return_code != 0:
   exit("ERROR: {} jobs failed".format('{{subsection}}'))
else:
   print("successfully finish all jobs....")
   #time delay to ensure process completely finished
   time.sleep(5)

#orgnize diagnostic output
collect_clim_diags(
   regions,variables,
   '{{figure_format}}',
   '${model_name}',
   '${case_id}',
   input_template,
   out_path
)

{%- endif %}

{%- if "variability_modes" in subsection %}
##########################################
# call pcmdi mode variability diagnostics
##########################################
print("calculate mode variability metrics")

{%- if subsection == "variability_modes_atm" %}
var_modes = '{{ atm_modes }}'.split(",")
{% elif subsection == "variability_modes_cpl" %}
var_modes = '{{ cpl_modes }}'.split(",")
{%- endif %}

#from configuration file
varOBS  = '{{vars}}'
refset  = obs_dic[varOBS]['set']
refname = obs_dic[varOBS][refset]
refpath = obs_dic[varOBS][refname]['file_path']
reftyrs = int(str(obs_dic[varOBS][refname]['yymms'])[0:4])
reftyre = int(str(obs_dic[varOBS][refname]['yymme'])[0:4])

lstcmd = []
for var_mode in var_modes:
    if var_mode in ["NPO", "NPGO", "PSA1"]:
      eofn_obs = "2"
      eofn_mod = "2"
    elif var_mode in ["PSA2"]:
      eofn_obs = "3"
      eofn_mod = "3"
    else:
      eofn_obs = "1"
      eofn_mod = "1"
    ##############################################
    lstcmd.append(
        " ".join([
           'variability_modes_driver.py', ' -p parameterfile.py',
           '--variability_mode'         , '{}'.format(var_mode),
           '--eofn_mod'                 , '{}'.format(eofn_mod),
           '--eofn_obs'                 , '{}'.format(eofn_obs),
           '--varOBS'                   , '{}'.format(varOBS),
           '--osyear'                   , '{}'.format(reftyrs),
           '--oeyear'                   , '{}'.format(reftyre),
           '--reference_data_name'      , '{}'.format(refname),
           '--reference_data_path'      , '{}'.format(refpath),
           '--case_id'                  , '{}'.format('${case_id}')
        ])
    )

if (len(lstcmd) > 0 ) and multiprocessing:
   print("Parallel computing with {} jobs".format(str(len(lstcmd))))
   stdout,stderr,return_code = parallel_jobs(lstcmd,num_workers)
elif (len(lstcmd) > 0 ):
   print("Serial computing with {} jobs".format(str(len(lstcmd))))
   stdout,stderr,return_code = serial_jobs(lstcmd,num_workers)
else:
   print("no jobs to run...")
   return_code = 0

if return_code != 0:
   exit("ERROR: {} jobs failed".format('{{subsection}}'))
else:
   print("successfully finish all jobs....")
   #time delay to ensure process completely finished
   time.sleep(5)

#orgnize diagnostic output
collect_movs_diags(
   var_modes,
   '{{figure_format}}',
   '${model_name}',
   '${case_id}',
   input_template,
   out_path
)

{%- endif %}

{%- if "enso" in subsection %}
#############################################
# call enso_driver.py to process diagnostics
#############################################

#orgnize observation var list
enso_obsvar_dict(obs_dic,variables)

#orgnize observation landmask
enso_obsvar_lmsk(obs_dic,variables)

#now start enso driver
print("calculate enso metrics")
enso_groups = '{{ enso_groups }}'.split(",")
lstcmd = []
for metricsCollection in enso_groups:
    lstcmd.append(
        " ".join([
           'enso_driver.py     ', ' -p parameterfile.py',
           '--metricsCollection', '{}'.format(metricsCollection),
           '--case_id'          , '{}'.format('${case_id}')
        ])
    )

if (len(lstcmd) > 0 ) and multiprocessing:
   print("Parallel computing with {} jobs".format(str(len(lstcmd))))
   stdout,stderr,return_code = parallel_jobs(lstcmd,num_workers)
elif (len(lstcmd) > 0 ):
   print("Serial computing with {} jobs".format(str(len(lstcmd))))
   stdout,stderr,return_code = serial_jobs(lstcmd,num_workers)
else:
   print("no jobs to run...")
   return_code = 0

if return_code != 0:
   exit("ERROR: {} jobs failed".format('{{subsection}}'))
else:
   print("successfully finish all jobs....")
   #time delay to ensure process completely finished
   time.sleep(5)

#organize diagnostic output
obs_dict = json.load(open('obs_catalogue.json'))
obs_name = list(obs_dict.keys())[0]
collect_enso_diags(
     enso_groups,
     '{{figure_format}}',
     obs_name,
     '${model_name}',
     '${case_id}',
     input_template,
     out_path
)

{%- endif %}

{%- if "synthetic_plots" in subsection %}
#########################################
#plot synthetic figures for pcmdi metrics
#########################################
print("generate synthetic metrics plot ...")
metric_sets = '{{sub_sets}}'.split(",")
figure_sets = '{{synthetic_sets}}'.split(",")
figure_format = '{{figure_format}}'
test_input_path = os.path.join(
    '${www}','${case}','pcmdi_diags','${results_dir}',
    'metrics_data','%(group_type)'
)

metric_dict = json.load(open('synthetic_metrics_list.json'))

parameter = OrderedDict()
parameter['save_data'] = True
parameter['case_id'] = '${case_id}'
parameter['out_dir'] = os.path.join('${results_dir}','ERROR_metric')
parameter['test_name'] = '{{model_name}}'
parameter['tableID'] = '{{model_tableID}}'
parameter['model_name'] = '-'.join('{{model_name}}'.split(".")[2:])

for metric in metric_sets:
    parameter['test_path'] = test_input_path.replace('%(group_type)',metric)
    parameter['diag_vars'] = metric_dict[metric]
    if metric == "mean_climate":
       parameter['cmip_path'] = '{{cmip_clim_dir}}'
       parameter['cmip_name'] = '{{cmip_clim_set}}'
       merge_lib = collect_clim_metrics(parameter)
    elif metric == "variability_modes":
       parameter['cmip_path'] = '{{cmip_movs_dir}}'
       parameter['cmip_name'] = '{{cmip_movs_set}}'
       parameter['movs_mode'] = '{{ atm_modes }}'.split(",") + '{{ cpl_modes }}'.split(",")
       merge_lib,mode_season_list = collect_movs_metrics(parameter)
    elif metric == 'enso':
       parameter['cmip_path'] = '{{cmip_enso_dir}}'
       parameter['cmip_name'] = '{{cmip_enso_set}}'
       merge_lib = collect_enso_metrics(parameter)

    for stat in metric_dict[metric].keys():
        if metric == "mean_climate":
           mean_climate_plot_driver(
                     metric, stat,
                     merge_lib.regions,
                     parameter['model_name'],
                     parameter['diag_vars'][stat],
                     merge_lib.df_dict[stat],
                     merge_lib.var_list,
                     merge_lib.var_unit_list,
                     parameter['save_data'],
                     parameter['out_dir'])
        elif metric == "variability_modes":
           variability_modes_plot_driver(
                     metric, stat,
                     parameter['model_name'],
                     parameter['diag_vars'][stat],
                     merge_lib[stat],
                     mode_season_list,
                     parameter['save_data'],
                     parameter['out_dir'])

{%- endif %}

EOF
################################
# Run diagnostics
mkdir -p pcmdi_diags
command="srun -N 1 python -u pcmdi.py"
# Run diagnostics
time ${command}
if [ $? != 0 ]; then
  cd {{ scriptDir }}
  echo 'ERROR (11)' > {{ prefix }}.status
  exit 11
fi

#################################
# Copy output to web server
echo
echo ===== COPY FILES TO WEB SERVER =====
echo

# Create top-level directory
web_dir=${www}/${case}/pcmdi_diags
mkdir -p ${web_dir}
if [ $? != 0 ]; then
  cd {{ scriptDir }}
  echo 'ERROR (13)' > {{ prefix }}.status
  exit 13
fi

{% if machine in ['pm-cpu', 'pm-gpu'] %}
# For NERSC, make sure it is world readable
f=`realpath ${web_dir}`
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

############################################
# Copy files
#rsync -a --delete ${results_dir} ${web_dir}/
rsync -a ${results_dir} ${web_dir}/
if [ $? != 0 ]; then
  cd {{ scriptDir }}
  echo 'ERROR (14)' > {{ prefix }}.status
  exit 14
fi

{% if machine in ['pm-cpu', 'pm-gpu'] %}
# For NERSC, change permissions of new files
pushd ${web_dir}/
chgrp -R e3sm ${results_dir}
chmod -R go+rX,go-w ${results_dir}
popd
{% endif %}

{% if machine in ['anvil', 'chrysalis'] %}
# For LCRC, change permissions of new files
pushd ${web_dir}/
chmod -R go+rX,go-w ${results_dir}
popd
{% endif %}

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
