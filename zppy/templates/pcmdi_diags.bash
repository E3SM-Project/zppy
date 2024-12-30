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
y1={{ year1 }}
y2={{ year2 }}
Y1="{{ '%04d' % (year1) }}"
Y2="{{ '%04d' % (year2) }}"
{% if run_type == "model_vs_model" %}
ref_Y1="{{ '%04d' % (ref_year1) }}"
ref_Y2="{{ '%04d' % (ref_year2) }}"
{%- endif %}
run_type="{{ run_type }}"
tag="{{ tag }}"

results_dir=${tag}_${Y1}-${Y2}

ref_name={{ ref_name }}

##################################################
#info to construct pcmdi-preferred data convension
##################################################
cmip_name='{{ cmip_name }}'
tableID='{{ cmip_tableID }}'
{% if run_type == "model_vs_obs" %}
cmip_name_ref='obs.historical.%(model).00'
tableID_ref=${tableID}
{% elif run_type == "model_vs_model" %}
cmip_name_ref='{{ cmip_name_ref }}'
tableID_ref='{{ cmip_tableID_ref }}'
{%- endif %}
case_id=v$(date '+%Y%m%d')

# Create temporary workdir
workdir=`mktemp -d tmp.${id}.XXXX`
cd ${workdir}

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
    dofm=(15 46 74 105 135 166 196 227 258 288 319 349) #middle day of month
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
    ncap2 -O -h -s 'time[time]={15.5, 45, 74.5, 105, 135.5, 166, 196.5, 227.5, 258, 288.5,319, 349.5};time_bnds[time,bnds]={0, 31, 31, 59, 59, 90, 90, 120, 120, 151, 151, 181, 181, 212, 212, 243, 243, 273, 273, 304, 304, 334, 334, 365.};time@units="days since 1850-01-01 00:00:00";time@calendar="noleap";time@bounds="time_bnds"' ${combined_name} ${combined_name}
    rm -rvf ${v}_clm_*.nc
    if [ $? != 0 ]; then
      cd {{ scriptDir }}
      echo "ERROR (${error_num})" > {{ prefix }}.status
      exit ${error_num}
    fi
  done
  cd ..
}

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
    dofm=(15 46 74 105 135 166 196 227 258 288 319 349) #middle day of month
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
    ncap2 -O -h -s 'time[time]={15.5, 45, 74.5, 105, 135.5, 166, 196.5, 227.5, 258, 288.5,319, 349.5};time@units="days since 1850-01-01 00:00:00";time@calendar="noleap";' ${combined_name} ${combined_name}
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
    YYYYS=${fname: -16:-10}
    YYYYE=${fname: -9:-3}
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

{%- if ("mean_climate" in subset) %}
{% if run_type == "model_vs_obs" %}
climo_dir_primary=climo
{% elif run_type == "model_vs_model" %}
climo_dir_primary=climo_test
{%- endif %}
# Create local links to input climo files
climo_dir_source={{ output }}/post/atm/{{ grid }}/cmip_ts/monthly
create_links_acyc_climo ${climo_dir_source} ${climo_dir_primary} ${Y1} ${Y2} ${cmip_name}.${tableID} 1
{% if run_type == "model_vs_model" %}
# Create local links to input climo files (ref model)
climo_dir_source={{ reference_data_path }}
climo_dir_ref=climo_ref
create_links_acyc_climo ${climo_dir_source} ${climo_dir_ref} ${ref_Y1} ${ref_Y2} ${cmip_name_ref}.${tableID_ref} 2
{%- endif %}
{%- endif %}

########################
#prepare the model data
########################
{%- if ("variability_mode_cpl" in subset) or ("variability_mode_atm" in subset) or ("enso" in subset) %}
#all diags will be run with ts data
{% if run_type == "model_vs_obs" %}
ts_dir_primary=ts
{% elif run_type == "model_vs_model" %}
ts_dir_primary=ts_test
{%- endif %}
# Create netcdf files for time series variables
ts_dir_source={{ output }}/post/atm/{{ grid }}/cmip_ts/monthly
create_links_ts ${ts_dir_source} ${ts_dir_primary} ${Y1} ${Y2} ${cmip_name}.${tableID} 3
{% if run_type == "model_vs_model" %}
ts_dir_source={{ reference_data_path_ts }}/{{ ts_num_years_ref }}yr
ts_dir_ref=ts_ref
create_links_ts ${ts_dir_source} ${ts_dir_ref} ${ref_Y1} ${ref_Y2} ${cmip_name_ref}.${tableID_ref} 4
{%- endif %}
{%- endif %}

#########################################################
#process the derived quantities for pcmdi diagnostics.
#this module is created as variables such as rltcre and
#rstcre were not included as default in cmip6 table
#this part can be removed when all variables converated
#during the 'e3sm_to_cmip' step
#########################################################
cat > process_derived_var.py << EOF
import os
import glob
import json
import time
import datetime
import xarray as xr
import xcdat as xc
import numpy as np
import shutil

import pcmdi_metrics
from pcmdi_metrics.io import (
        xcdat_open
)

def derive_var(path,vout,var_dic,fname):
   for i,var in enumerate(var_dic.keys()):
     fpath = sorted(glob.glob(os.path.join(path,"*."+var+".*.nc")))
     df = xcdat_open(fpath[0])
     if i == 0:
       template = fpath[0].split("/")[-1]
       #construct a copy of file for derived variable
       out = os.path.join(path,template.replace(".{}.".format(var),".{}.".format(vout)))
       shutil.copy(fpath[0],out)
       ds = xcdat_open(fpath[0])
       ds = ds.rename_vars({var:vout})
       ds[vout].data = ds[vout].data * var_dic[var]
     else:
       ds[vout].data = ds[vout].data + df[var].data * var_dic[var]
   ds.to_netcdf(out)
   return

{% if run_type == "model_vs_obs" %}
cmip_groups = ['${cmip_name}.${tableID}']
{%- if ("mean_climate" in subset) %}
run_groups=['${climo_dir_primary}']
variables = '{{ cmip_vars }}'.split(",")
{%- elif ("variability_mode_cpl" in subset) or ("variability_mode_atm" in subset) or ("enso" in subset) %}
run_groups=['${ts_dir_primary}']
variables = '{{ vars }}'.split(",")
{%- endif %}
{% elif run_type == "model_vs_model" %}
cmip_groups = ['${cmip_name}.${tableID}','${cmip_name_ref}.${tableID_ref}']
{%- if ("mean_climate" in subset) %}
run_groups=['${climo_dir_primary}','${climo_dir_ref}']
variables = '{{ cmip_vars }}'.split(",")
{%- elif ("variability_mode_cpl" in subset) or ("variability_mode_atm" in subset) or ("enso" in subset) %}
run_groups=['${ts_dir_primary}','${ts_dir_ref}']
variables = '{{ vars }}'.split(",")
{%- endif %}
{%- endif %}

###############################################################
#check and process derived quantities, these quantities are not
#included as default in e3sm_to_cmip module
###############################################################
for i,group in enumerate(run_groups):
  for j,var in enumerate(variables):
    if "_" in var or "-" in var:
      varin = var.split("_|-", varin)[0]
    else:
      varin = var
    if varin in ['rltcre','rstcre']:
      fpaths = sorted(glob.glob(os.path.join(group,"*"+var+"_*.nc")))
      if len(fpaths) < 1:
        if varin == 'rstcre':
          derive_var(group,varin,{'rsutcs':1,'rsut':-1},cmip_groups[i])
        elif varin == 'rltcre':
          derive_var(group,varin,{'rlutcs':1,'rlut':-1},cmip_groups[i])

EOF
###################
# run process jobs
###################
command="srun -N 1 python -u process_derived_var.py"
time ${command}
if [ $? != 0 ]; then
  cd {{ scriptDir }}
  echo 'ERROR (5)' > {{ prefix }}.status
  exit 5
fi

{% if run_type == "model_vs_obs" %}
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
import glob
import json
import time
import datetime
import xarray as xr
import xcdat as xc
import numpy as np
import shutil

import pcmdi_metrics
from pcmdi_metrics.io import (
        xcdat_open
)

def derive_var(path,vout,var_dic,fname):
   for i,var in enumerate(var_dic.keys()):
     fpath = sorted(glob.glob(os.path.join(path,"*."+var+".*.nc")))
     df = xcdat_open(fpath[0])
     if i == 0:
       template = fpath[0].split("/")[-1]
       #construct a copy of file for derived variable
       out = os.path.join(path,template.replace(".{}.".format(var),".{}.".format(vout)))
       shutil.copy(fpath[0],out)
       ds = xcdat_open(fpath[0])
       ds = ds.rename_vars({var:vout})
       ds[vout].data = ds[vout].data * var_dic[var]
     else:
       ds[vout].data = ds[vout].data + df[var].data * var_dic[var]
   ds.to_netcdf(out)
   return

cmip_name = '${cmip_name_ref}.${tableID_ref}'

{%- if ("mean_climate" in subset) %}
variables = '{{ cmip_vars }}'.split(",")
obs_sets = '{{ obs_sets }}'.split(",")
{%- elif ("variability_mode_cpl" in subset) or ("variability_mode_atm" in subset) or ("enso" in subset) %}
variables = '{{ vars }}'.split(",")
obs_sets = '{{ obs_sets }}'.split(",")
{%- endif %}
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

obs_dic = json.load(open('{{reference_alias}}'))

#loop each variable and process the data
for i,var in enumerate(variables):
  if "_" in var or "-" in var:
    varin = var.split("_|-", varin)[0]
  else:
    varin = var

  if len(obs_sets) > 1 and len(obs_sets) == len(variables):
    obsid = obs_sets[i]
  else:
    obsid = obs_sets[0]

  obsname = obs_dic[var][obsid]
  if "ceres_ebaf" in obsname:
    obsstr = obsname.replace("_","*").replace("-","*")
  else:
    obsstr = obsname

  fpaths = sorted(glob.glob(os.path.join(ts_dir_ref_source,obsstr,varin+"_*.nc")))
  if (len(fpaths) < 1) and (varin in altobs_dic.keys()):
    #these variables were not included as cmip type
    varin = altobs_dic[varin]
    fpaths = sorted(glob.glob(os.path.join(ts_dir_ref_source,obsstr,varin+"_*.nc")))

  if (len(fpaths) > 0) and (os.path.exists(fpaths[0])):
    template = fpaths[0].split("/")[-1]
    yms = template.split("_")[-2][0:6]
    yme = template.split("_")[-1][0:6]
    obs = obsname.replace(".","_")
    out = os.path.join('${obstmp_dir}',
                       '{}.{}.{}-{}.nc'.format(
	                cmip_name.replace('%(model)',obs),
                        var,yms,yme))
    #rename variable if needed then save file
    if varin != var:
      ds = xcdat_open(fpaths[0])
      ds = ds.rename(name_dict={varin:var})
      ds.to_netcdf(out)
    elif not os.path.exists(out):
      os.symlink(fpaths[0],out)

  #####################################################################
  #check and process derived quantities
  #note: these quantities are possibly not included as default in cmip
  if varin in ['rltcre','rstcre']:
    fpaths = sorted(glob.glob(os.path.join('${obstmp_dir}',"*"+varin+"_*.nc")))
    if len(fpaths) < 1:
      if varin == 'rstcre':
        derive_var('${obstmp_dir}',varin,{'rsutcs':1,'rsut':-1},cmip_name)
      elif varin == 'rltcre':
        derive_var('${obstmp_dir}',varin,{'rlutcs':1,'rlut':-1},cmip_name)

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
{%- if ("mean_climate" in subset) %}
climo_dir_ref=climo_ref
create_links_acyc_climo_obs ${ts_dir_ref_source} ${climo_dir_ref} ${Y1} ${Y2} 7
{%- elif ("variability_mode_cpl" in subset) or ("variability_mode_atm" in subset) or ("enso" in subset) %}
ts_dir_ref=ts_ref
create_links_ts_obs ${ts_dir_ref_source} ${ts_dir_ref} ${Y1} ${Y2} 8
{%- endif %}

{%- endif %}

##################################################
#collect data description and save in a json file
#for the convinience of later-on process
##################################################
mkdir -p ${results_dir}
cat > data_info_collect.py << EOF
import os
import glob
import json
import collections
from collections import OrderedDict

{%- if ("mean_climate" in subset) %}
test = '${climo_dir_primary}'
refr = '${climo_dir_ref}'
variables = '{{ cmip_vars }}'.split(",")
{%- elif ("variability_mode_cpl" in subset) or ("variability_mode_atm" in subset) %}
test = '${ts_dir_primary}'
refr = '${ts_dir_ref}'
variables = '{{ vars }}'.split(",")
{%- elif  ("enso" in subset) %}
test = '${ts_dir_primary}'
refr = '${ts_dir_ref}'
variables = '{{ vars }}'.split(",")
{%- endif %}

test_data_set = ['${cmip_name}'.split(".")[1]]
{% if run_type == "model_vs_obs" %}
refr_data_set = '{{ obs_sets }}'.split(",")
{% elif run_type == "model_vs_model" %}
refr_data_set = ['${cmip_name_ref}'.split(".")[1]]
{%- endif %}

#collect variables when both model and observations are available
refr_dic,test_dic = OrderedDict(),OrderedDict()
for i,var in enumerate(variables):
  if "_" in var or "-" in var:
    varin = var.split("_|-", varin)[0]
  else:
    varin = var
  test_path = sorted(glob.glob(os.path.join(test,"*.{}.*.nc".format(varin))))
  refr_path = sorted(glob.glob(os.path.join(refr,"*.{}.*.nc".format(varin))))
  if (len(test_path) > 0) and (len(refr_path) > 0):
    if (os.path.exists(test_path[0])) and (os.path.exists(refr_path[0])):
      for j,path in enumerate([test_path[0],refr_path[0]]):
        fname = path.split("/")[-1]
        model = fname.split(".")[2]
        sbdic = { "mip"         : fname.split(".")[0],
                  "exp"         : fname.split(".")[1],
                  "model"       : fname.split(".")[2],
                  "realization" : fname.split(".")[3],
                  "tableID"     : fname.split(".")[4],
                  "yymms"       : fname.split(".")[6].split("-")[0],
                  "yymme"       : fname.split(".")[6].split("-")[1],
                  "var_in_file" : varin,
                  "var_name"    : var,
                  "file_path"   : path,
                  "template"    : fname }
        if j == 0:
          if var not in test_dic.keys():
             test_dic[var] = {}
          if len(test_data_set) != len(variables):
             kset = test_data_set[0]
          else:
             kset = test_data_set[i]
          test_dic[var]['set'] = kset
          test_dic[var][kset]  = model
          test_dic[var][model] = sbdic
        else:
          if var not in refr_dic.keys():
             refr_dic[var] = {}
          if len(refr_data_set) != len(variables):
             kset = refr_data_set[0]
          else:
             kset = refr_data_set[i]
          refr_dic[var][kset]  = model
          refr_dic[var][model] = sbdic
          refr_dic[var]['set'] = kset

# Save test and obs/reference data information for next step
for i,group in enumerate([test,refr]):
  if i == 0:
    out_dic = test_dic
  else:
    out_dic = refr_dic
  out_file = os.path.join(
           '${results_dir}',
           '{}_{}_catalogue.json'.format(group,'{{subset}}')
  )
  json.dump(out_dic,
            open(out_file, "w"),
            sort_keys=False,
            indent=4,
            separators=(",", ": "))

EOF
#####################
# run process jobs
command="srun -N 1 python -u data_info_collect.py"
time ${command}
if [ $? != 0 ]; then
  cd {{ scriptDir }}
  echo 'ERROR (9)' > {{ prefix }}.status
  exit 9
fi

##############################################################################
# land/sea mask is needed in PCMDI diagnostics, check and generate it here as
# these data are not always available for model or observations
##############################################################################
fixed_dir="fixed"
mkdir -p ${fixed_dir}
cat > create_landsea_mask.py << EOF
import os
import glob
import json
import datetime
import numpy as np
import collections
from collections import OrderedDict

import pcmdi_metrics
from pcmdi_metrics.io import (
        xcdat_open
)
from pcmdi_metrics.utils import (
        create_land_sea_mask
)

###############################################
# Flag to turn on/off land/sea mask processing
#############################################
if {{ generate_sftlf }} in ['true', 'y', True]:
  generate_sftlf = True
else:
  generate_sftlf = False

if generate_sftlf:

{%- if ("mean_climate" in subset) %}
  test = '${climo_dir_primary}'
  refr = '${climo_dir_ref}'
{%- elif ("variability_mode_cpl" in subset) or ("variability_mode_atm" in subset) or ("enso" in subset) %}
  test = '${ts_dir_primary}'
  refr = '${ts_dir_ref}'
{%- endif %}

  #loop each group and process land/mask if not exist
  for group in [test,refr]:
     dic_file = os.path.join(
                '${results_dir}',
                '{}_{}_catalogue.json'.format(group,'{{subset}}')
     )
     data_dic = json.load(open(dic_file))
     for var in data_dic.keys():
       mdset = data_dic[var]['set']
       model = data_dic[var][mdset]
       mpath = data_dic[var][model]['file_path']
       mpath_lf = os.path.join(
              '${fixed_dir}',
              'sftlf.{}.nc'.format(model)
       )
       # generate land/sea mask if not exist
       if not os.path.exists(mpath_lf):
         ds = xcdat_open(mpath, decode_times=True)
         ds = ds.bounds.add_missing_bounds()
         try:
             lf_array = create_land_sea_mask(ds, method="pcmdi")
             print("land mask is estimated using pcmdi method.")
         except Exception:
             lf_array = create_land_sea_mask(ds, method="regionmask")
             print("land mask is estimated using regionmask method.")
         lf_array = lf_array * 100.0
         lf_array.attrs['long_name']= "land_area_fraction"
         lf_array.attrs['units'] = "%"
         lf_array.attrs['id'] = "sftlf"  # Rename
         ds_lf = lf_array.to_dataset().compute()
         ds_lf = ds_lf.bounds.add_missing_bounds()
         ds_lf = ds_lf.rename_vars({"lsmask": "sftlf"})
         ds_lf.fillna(1.0e20)
         ds_lf.attrs['model'] = model
         ds_lf.attrs['associated_files'] = mpath
         ds_lf.attrs['history'] = "File processed: " + datetime.datetime.now().strftime("%Y%m%d")
         comp = dict(_FillValue=1.0e20,zlib=True,complevel=5)
         encoding = {var: comp for var in list(ds_lf.data_vars)+list(ds_lf.coords)}
         ds_lf.to_netcdf(mpath_lf,encoding=encoding)
         del(ds,ds_lf,lf_array)
EOF
#####################
# run process script
command="srun -N 1 python -u create_landsea_mask.py"
time ${command}
if [ $? != 0 ]; then
  cd {{ scriptDir }}
  echo 'ERROR (10)' > {{ prefix }}.status
  exit 10
fi

########################################################
# generate basic parameter file for pcmdi metrics driver
########################################################
cat > parameterfile.py << EOF
import os
import sys
import json
import numpy as np
import collections
from collections import OrderedDict

#####################
#basic information
#####################
start_yr = int('${Y1}')
end_yr = int('${Y2}')
num_years = end_yr - start_yr + 1
period = "{:04d}{:02d}-{:04d}{:02d}".format(start_yr,1,end_yr,12)

mip = '${cmip_name}'.split(".")[0]
exp = '${cmip_name}'.split(".")[1]
product = '${cmip_name}'.split(".")[2]
realm = '${cmip_name}'.split(".")[3]

##############################################
#Configuration shared with pcmdi diagnostics
##############################################
# Record NetCDF output
nc_out_obs = {{ nc_out_obs }}
nc_out = {{ nc_out }}
if nc_out:
  ext = ".nc"
else:
  ext = ".xml"
user_notes = 'Provenance and results'
debug = {{ pmp_debug }}

# Generate plots
plot = {{ plot }}
plot_obs = {{ plot_obs }} # optional

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
    '${fixed_dir}',
    'sftlf.%(model).nc'
)

############################################
#setup specific for mean climate metrics
{%- if ("mean_climate" in subset) %}

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
test_data_set = [ product ]
test_data_path = '${climo_dir_primary}'
# Templates for model climatology files
filename_template = '.'.join([
  mip,
  exp,
  '%(model)',
  '*',
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
   '${results_dir}',
   '{}_{}_catalogue.json'.format(
    '${climo_dir_ref}',
    '{{subset}}'))

#load caclulated regions for each variable
regions = json.load(open('regions.json'))

#load predefined region information
regions_specs = json.load(open('{{regions_specs}}'))
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
    '${results_dir}',
    'metrics_results',
    'mean_climate',
     mip,
     exp,
    '%(case_id)'
)

############################################################
# DATA LOCATION: INTERPOLATED MODELS' CLIMATOLOGIES
diagnostics_output_path= os.path.join(
    '${results_dir}',
    'diagnostic_results',
    'mean_climate',
     mip,
     exp,
    '%(case_id)'
)
test_clims_interpolated_output = diagnostics_output_path

{%- endif %}

{%- if "variability_mode" in subset  %}
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
modpath = '.'.join([
  mip,
  exp,
  '%(model)',
  '*',
  '${tableID}',
  '%(variable)',
  period,
  'AC',
  '${case_id}',
  'nc'
])

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
cmec = {{ cmec }}

# Update diagnostic file if exist
update_json = {{ update_json }}

#results directory structure.
results_dir = os.path.join(
    '${results_dir}',
    '%(output_type)',
    'variability_modes',
    '%(mip)',
    '%(exp)',
    '${case_id}',
    '%(variability_mode)',
    '%(reference_data_name)',
)
{%- endif %}

{%- if "enso" in subset %}
###########################################
#parameter setup specific for enso metrics
###########################################
modnames = [ product ]
realization = realm

modpath = os.path.join(
  '${ts_dir_primary}',
  '.'.join([mip,exp,'%(model)','%(realization)',
            '${tableID}','%(variable)',period,'nc'])
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
    '${results_dir}',
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

################################################################
# Run PCMDI Diags
echo
echo ===== RUN PCMDI DIAGS =====
echo
# Prepare configuration file
cat > pcmdi.py << EOF
import os
import glob
import glob
import json
import time
import datetime
import xarray as xr
import xcdat as xc
import numpy as np

import collections
from collections import OrderedDict

import pcmdi_metrics
from pcmdi_metrics.io import (
        xcdat_open
)

import psutil
import subprocess
from itertools import chain
from subprocess import Popen, PIPE, call

def childCount():
    current_process = psutil.Process()
    children = current_process.children()
    return(len(children))

start_yr = int('${Y1}')
end_yr = int('${Y2}')
num_years = end_yr - start_yr + 1

#parallel calculation
num_workers = {{ num_workers }}
multiprocessing = {{multiprocessing}}

# DATA LOCATION: Reference
{%- if "mean_climate" in subset %}
reference_data_path = '${climo_dir_ref}'
{%- elif ("variability_mode" in subset) or ("enso" in subset) %}
reference_data_path = '${ts_dir_ref}'
{%- endif %}
observation_file = os.path.join(
   '${results_dir}',
   '{}_{}_catalogue.json'.format(
    reference_data_path,
    '{{subset}}')
)
obs_dic = json.load(open(observation_file))

{%- if "mean_climate" in subset %}
######################################
# call pcmdi mean climate diagnostics
#####################################
#customized region, otherwise default
regional = '{{ regional }}'
if regional  == "y":
  default_regions = '{{ regions }}'.split(",")
else:
  default_regions = ["global", "NHEX", "SHEX", "TROPICS"]

###################################################
# generate the command list for each reference and
# each variable (will execuate in parallel later)
lstcmd = []
regv_dic = OrderedDict()
for var in "{{vars}}".split(","):
  if var in obs_dic.keys():
    vkey = var.split("-")[0]
    refset = obs_dic[var]['set']
    regv_dic[vkey] = default_regions
    lstcmd.append(" ".join([
                  'mean_climate_driver.py',
                  '-p  parameterfile.py'  ,
                  '--vars'                , '{}'.format(var),
                  '-r'                    , '{}'.format(refset),
                  '--varname_in_test_data', '{}'.format(vkey),
                  '--case_id'             , '{}'.format('${case_id}')
                  ]))

#save region info dictionary
json.dump(regv_dic,
          open('regions.json', "w"),
          sort_keys=False,
          indent=4,
          separators=(",", ": "))

#finally process the data in parallel
print("Number of jobs starting is ", str(len(lstcmd)))
procs = []
if len(lstcmd) > 0:
  for i,p in enumerate(lstcmd):
    print('running %s' % (str(p)))
    proc = Popen(p, stdout=PIPE, shell=True)
    if multiprocessing == True:
      procs.append(proc)
      while (childCount() > num_workers):
        time.sleep(0.25)
        [pp.communicate() for pp in procs]
        procs = []
      else:
        if (i == len(lstcmd)-1):
          try:
            outs, errs = proc.communicate()
            if proc.returncode == 0:
              print("stdout = {}; stderr = {}".format(str(outs),str(errs)))
            else:
              exit("ERROR: subprocess {} failed".format(str(lstcmd[i])))
          except:
            break
    else:
      return_code = proc.communicate()
      if return_code != 0:
        exit("Failed to run {}".format(str(p)))

#set a delay to avoid delay in writing process
time.sleep(1)
print("done submitting")

{%- endif %}

{%- if "variability_mode" in subset %}
##########################################
# call pcmdi mode variability diagnostics
##########################################
print("calculate mode variability metrics")

{%- if subset == "variability_mode_atm" %}
var_modes = '{{ atm_modes }}'.split(",")
{% elif subset == "variability_mode_cpl" %}
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
for variability_mode in var_modes:
  if variability_mode in ["NPO", "NPGO", "PSA1"]:
    eofn_obs = "2"
    eofn_mod = "2"
  elif variability_mode in ["PSA2"]:
    eofn_obs = "3"
    eofn_mod = "3"
  else:
    eofn_obs = "1"
    eofn_mod = "1"
  ##############################################
  cmd = (" ".join([
            'variability_modes_driver.py',
            '-p parameterfile.py'        ,
            '--variability_mode'         , '{}'.format(variability_mode),
            '--eofn_mod'                 , '{}'.format(eofn_mod),
            '--eofn_obs'                 , '{}'.format(eofn_obs),
            '--varOBS'                   , '{}'.format(varOBS),
            '--osyear'                   , '{}'.format(reftyrs),
            '--oeyear'                   , '{}'.format(reftyre),
            '--reference_data_name'      , '{}'.format(refname),
            '--reference_data_path'      , '{}'.format(refpath),
            '--case_id'                  , '{}'.format('${case_id}')
            ]))
  lstcmd.append(cmd); del(cmd)

#finally process the data in parallel
print("Number of jobs starting is ", str(len(lstcmd)))
procs = []
for i,p in enumerate(lstcmd):
  print('running %s' % (str(p)))
  proc = Popen(p, stdout=PIPE, shell=True)
  if multiprocessing == True:
    procs.append(proc)
    while (childCount() > num_workers):
      time.sleep(0.25)
      [pp.communicate() for pp in procs] # this will get the exit code
      procs = []
    else:
      if (i == len(lstcmd)-1):
        try:
          outs, errs = proc.communicate()
          if proc.returncode == 0:
            print("stdout = {}; stderr = {}".format(str(outs),str(errs)))
          else:
            exit("ERROR: subprocess {} failed".format(str(lstcmd[i])))
        except:
          break
  else:
    return_code = proc.communicate()
    if return_code != 0:
      exit("Failed to run {}".format(str(p)))
#set a delay to avoid delay in writing process
time.sleep(1)
print("done submitting")
del(lstcmd)
{%- endif %}

{%- if "enso" in subset %}
#############################################
# call enso_driver.py to process diagnostics
#############################################
#reorgnize observation needed for enso driver
refr_dic = OrderedDict()
relf_dic = OrderedDict()
for var in list("{{vars}}".split(",")):
  vkey = var.split("-")[0]
  refset  = obs_dic[var]['set']
  refname = obs_dic[var][refset]
  #data file in model->var sequence
  if refname not in refr_dic.keys():
    refr_dic[refname] = {}
  refr_dic[refname][var] = obs_dic[var][refname]
  #land/sea mask
  if refname not in  relf_dic.keys():
    relf_dic[refname] = os.path.join(
         "${fixed_dir}",
         'sftlf.{}.nc'.format(refname))

#save data file dictionary
json.dump(refr_dic,
          open('obs_catalogue.json', "w"),
          sort_keys=False,
          indent=4,
          separators=(",", ": "))

#save land/sea mask dictionary
json.dump(relf_dic,
          open('obs_landmask.json', "w"),
          sort_keys=False,
          indent=4,
          separators=(",", ": "))

#now start enso driver
print("calculate enso metrics")
enso_groups = '{{ enso_groups }}'.split(",")
lstcmd = []
for metricsCollection in enso_groups:
  cmd = (" ".join([
            'enso_driver.py     ',
            '-p parameterfile.py',
	    '--metricsCollection', '{}'.format(metricsCollection),
            '--case_id'          , '{}'.format('${case_id}')
         ]))
  lstcmd.append(cmd); del(cmd)

print("Number of jobs starting: ", str(len(lstcmd)))

#finally process the data in parallel
procs = []
for i,p in enumerate(lstcmd):
  print('running %s' % (str(p)))
  proc = Popen(p, stdout=PIPE, shell=True)
  procs.append(proc)
  while (childCount() > {{num_workers}}):
    time.sleep(0.25)
    [pp.communicate() for pp in procs] # this will get the exit code
    procs = []
  else:
    if (i == len(lstcmd)-1):
      try:
        outs, errs = proc.communicate()
        if proc.returncode == 0:
          print("stdout = {}; stderr = {}".format(str(outs),str(errs)))
        else:
          exit("ERROR: subprocess {} failed".format(str(lstcmd[i])))
      except:
        break
#set a delay to avoid delay in writing process
time.sleep(1)
print("done submitting")
{%- endif %}
EOF
################################
# Run diagnostics
command="srun -N 1 python -u pcmdi.py"
# Run diagnostics
time ${command}
if [ $? != 0 ]; then
  cd {{ scriptDir }}
  echo 'ERROR (11)' > {{ prefix }}.status
  exit 11
fi

################################################################
# this post-processing module is to generate sythentic metrics
# for mean-climate diagnostics (compared with cmip model results)
################################################################
{%- if "mean_climate" in subset %}
echo
echo ===== RUN PCMDI POST-PROCESSING =====
echo
# Prepare configuration file
cat > post_processing.py << EOF
import os
import glob
import glob
import json
import time
import datetime
import xarray as xr
import xcdat as xc
import numpy as np
import pcmdi_metrics

# external module for plot
{%- if ("mean_climate" in subset) %}
import {{clim_plot_parser}}
import {{clim_plot_driver}}
{%- endif %}

#customized region, otherwise default
regional = '{{ regional }}'
if regional  == "y":
  default_regions = '{{ regions }}'.split(",")
else:
  default_regions = ["global", "NHEX", "SHEX", "TROPICS"]

#generate diagnostics figures
print("--- prepare for mean climate metrics plot ---")
parser = create_mean_climate_plot_parser()
parameter = parser.get_parameter(argparse_vals_only=False)
parameter.regions = default_regions
parameter.run_type = "${run_type}"
parameter.period = "{:04d}-{:04d}".format(${Y1},${Y2})
parameter.pcmdi_data_set = "{{pcmdi_data_set}}"
parameter.pcmdi_data_path = os.path.join('{{pcmdi_data_path}}',"mean_climate")
parameter.test_data_set = "{}.{}".format(${cmip_name},"${case_id}")
parameter.test_data_path = os.path.join("${results_dir}","metrics_results","mean_climate")

{% if run_type == "model_vs_obs" %}
parameter.refr_data_set = ""
parameter.refr_period = ""
parameter.refr_data_path = ""
{% elif run_type == "model_vs_model" %}
parameter.refr_data_set = "{}.{}".format(${cmip_name_ref},"${case_id}")
parameter.refr_period = "{}-{}".format(${ref_Y1},${ref_Y2})
parameter.refr_data_path = os.path.join("${results_dir}","metrics_results","mean_climate")
{%- endif %}

parameter.output_path = os.path.join("${results_dir}","graphics","mean_climate")
parameter.ftype = '{{ figure_format }}'
parameter.debug = {{ pmp_debug }}
parameter.parcord_show_markers = {{parcord_show_markers}} #False
parameter.add_vertical_line = {{portrait_vertical_line}}  #True

#generate diagnostics figures
print("--- generate mean climate metrics plot ---")
mean_climate_metrics_plot(parameter)

EOF

################################
# Run diagnostics
command="srun -N 1 python -u post_processing.py"
# Run diagnostics
time ${command}
if [ $? != 0 ]; then
  cd {{ scriptDir }}
  echo 'ERROR (12)' > {{ prefix }}.status
  exit 12
fi
{% endif %}

#################################
# Copy output to web server
echo
echo ===== COPY FILES TO WEB SERVER =====
echo

# Create top-level directory
web_dir=${www}/${case}/pcmdi_diags #/{{ sub }}
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
