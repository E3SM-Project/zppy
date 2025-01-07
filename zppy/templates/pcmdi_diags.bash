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
create_links_acyc_climo ${climo_dir_source} ${climo_dir_primary} ${Y1} ${Y2} ${model_name}.${tableID} 1
{% if run_type == "model_vs_model" %}
# Create local links to input climo files (ref model)
climo_dir_source={{ reference_data_path }}
climo_dir_ref=climo_ref
create_links_acyc_climo ${climo_dir_source} ${climo_dir_ref} ${ref_Y1} ${ref_Y2} ${model_name_ref}.${tableID_ref} 2
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
create_links_ts ${ts_dir_source} ${ts_dir_primary} ${Y1} ${Y2} ${model_name}.${tableID} 3
{% if run_type == "model_vs_model" %}
ts_dir_source={{ reference_data_path_ts }}/{{ ts_num_years_ref }}yr
ts_dir_ref=ts_ref
create_links_ts ${ts_dir_source} ${ts_dir_ref} ${ref_Y1} ${ref_Y2} ${model_name_ref}.${tableID_ref} 4
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

variables = '{{ vars }}'.split(",")

{%- if ("mean_climate" in subset) %}
{% if run_type == "model_vs_obs" %}
model_groups = ['${model_name}.${tableID}']
run_groups=['${climo_dir_primary}']
{% elif run_type == "model_vs_model" %}
model_groups = ['${model_name}.${tableID}','${model_name_ref}.${tableID_ref}']
run_groups=['${climo_dir_primary}','${climo_dir_ref}']
{%- endif %}
{%- elif ("variability_mode_cpl" in subset) or ("variability_mode_atm" in subset) or ("enso" in subset) %}
{% if run_type == "model_vs_obs" %}
model_groups = ['${model_name}.${tableID}']
run_groups = ['${ts_dir_primary}']
{% elif run_type == "model_vs_model" %}
model_groups = ['${model_name}.${tableID}','${model_name_ref}.${tableID_ref}']
run_groups = ['${ts_dir_primary}','${ts_dir_ref}']
{%- endif %}
{%- endif %}

###############################################################
#check and process derived quantities, these quantities are not
#included as default in e3sm_to_cmip module
###############################################################
for i,group in enumerate(run_groups):
  for j,var in enumerate(variables):
    if "_" in var or "-" in var:
      varin = re.split("_|-", var)[0]
    else:
      varin = var
    if varin in ['rltcre','rstcre']:
      fpaths = sorted(glob.glob(os.path.join(group,"*"+var+"_*.nc")))
      if len(fpaths) < 1:
        if varin == 'rstcre':
          derive_var(group,varin,{'rsutcs':1,'rsut':-1},model_groups[i])
        elif varin == 'rltcre':
          derive_var(group,varin,{'rlutcs':1,'rlut':-1},model_groups[i])

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

obs_dic = json.load(open('{{reference_alias}}'))

#loop each variable and process the data
for i,var in enumerate(variables):
  if "_" in var or "-" in var:
    varin = re.split("_|-", var)[0]
  else:
    varin = var

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
	                model_name.replace('%(model)',obs),
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
        derive_var('${obstmp_dir}',varin,{'rsutcs':1,'rsut':-1},model_name)
      elif varin == 'rltcre':
        derive_var('${obstmp_dir}',varin,{'rlutcs':1,'rlut':-1},model_name)

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
mkdir -p pcmdi_diags
cat > data_info_collect.py << EOF
import os
import re
import glob
import json
import collections
from collections import OrderedDict

{%- if ("mean_climate" in subset) %}
test = '${climo_dir_primary}'
refr = '${climo_dir_ref}'
variables = '{{ vars }}'.split(",")
{%- elif ("variability_mode_cpl" in subset) or ("variability_mode_atm" in subset) %}
test = '${ts_dir_primary}'
refr = '${ts_dir_ref}'
variables = '{{ vars }}'.split(",")
{%- elif  ("enso" in subset) %}
test = '${ts_dir_primary}'
refr = '${ts_dir_ref}'
variables = '{{ vars }}'.split(",")
{%- endif %}

test_data_set = ['${model_name}'.split(".")[1]]
{% if run_type == "model_vs_obs" %}
refr_data_set = '{{ obs_sets }}'.split(",")
{% elif run_type == "model_vs_model" %}
refr_data_set = ['${model_name_ref}'.split(".")[1]]
{%- endif %}

#collect variables when both model and observations are available
refr_dic,test_dic = OrderedDict(),OrderedDict()
for i,var in enumerate(variables):
  if "_" in var or "-" in var:
    varin = re.split("_|-", var)[0]
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
           'pcmdi_diags',
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
                'pcmdi_diags',
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
             lf_array = create_land_sea_mask(ds, method="regionmask")
             print("land mask is estimated using regionmask method.")
         except Exception:
             lf_array = create_land_sea_mask(ds, method="pcmdi")
             print("land mask is estimated using pcmdi method.")
         lf_array = lf_array * 100.0
         lf_array.attrs['long_name']= "land_area_fraction"
         lf_array.attrs['units'] = "%"
         lf_array.attrs['id'] = "sftlf"  # Rename
         ds_lf = lf_array.to_dataset(name='sftlf').compute()
         ds_lf = ds_lf.bounds.add_missing_bounds()
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

{%- if ("variability_mode" in subset)  %}
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
  '{}.{}.%(model).%(realization).{}.%(variable).{}.nc'.format(mip,exp,${tableID},period)
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

{%- if ("enso" in subset) %}
###########################################
#parameter setup specific for enso metrics
###########################################
modnames = [ product ]
realization = realm
modpath = os.path.join(
  '${ts_dir_primary}',
  '{}.{}.%(model).%(realization).{}.%(variable).{}.nc'.format(mip,exp,${tableID},period)
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

import pcmdi_metrics
from pcmdi_metrics.io import (
        xcdat_open
)

from pcmdi_metrics.graphics import (
    Metrics,
    normalize_by_median,
    parallel_coordinate_plot,
    portrait_plot,
)

import psutil
import subprocess
from itertools import chain
from subprocess import Popen, PIPE, call

def childCount():
    current_process = psutil.Process()
    children = current_process.children()
    return(len(children))

def parallel_jobs(cmds,num_workers):
    procs = []
    for i,p in enumerate(cmds):
       print('running %s' % (str(p)))
       proc = Popen(p, stdout=PIPE, shell=True)
       procs.append(proc)
       if (i == len(cmds)-1):
          outs, errs = proc.communicate()
          rcode = proc.returncode
          time.sleep(0.25); break
       else:
          njobs = childCount()
          while (njobs > num_workers):
               [pp.communicate() for pp in procs]
               time.sleep(0.25)
               procs = []
    return outs,errs,rcode

def serial_jobs(cmds,num_workers):
    for i,p in enumerate(cmds):
       print('running %s' % (str(p)))
       proc = Popen(p, stdout=PIPE, shell=True)

    return outs,errs,rcode

def variable_region(regions,variables):
    regv_dic = OrderedDict()
    for var in variables:
       vkey = var.split("-")[0]
       regv_dic[vkey] = regions

    #save region info dictionary
    json.dump(regv_dic,
              open('regions.json', "w"),
              sort_keys=False,
              indent=4,
              separators=(",", ": "))
    return

def enso_obsvar_dict(obs_dic,variables):
    #orgnize observation for enso driver
    refr_dic = OrderedDict()
    for var in variables:
       vkey = var.split("-")[0]
       refset  = obs_dic[vkey]['set']
       refname = obs_dic[vkey][refset]
       #data file in model->var sequence
       if refname not in refr_dic.keys():
          refr_dic[refname] = {}
       refr_dic[refname][vkey] = obs_dic[vkey][refname]

    #save data file dictionary
    json.dump(refr_dic,
              open('obs_catalogue.json', "w"),
              sort_keys=False,
              indent=4,
              separators=(",", ": "))

    return

def enso_obsvar_lmsk(regions,variables):
    #orgnize observation landmask for enso driver
    relf_dic = OrderedDict()
    for var in variables:
       vkey = var.split("-")[0]
       refset  = obs_dic[vkey]['set']
       refname = obs_dic[vkey][refset]
       #land/sea mask
       if refname not in  relf_dic.keys():
          relf_dic[refname] = os.path.join(
                 "${fixed_dir}",
                 'sftlf.{}.nc'.format(refname))

    #save data file dictionary
    json.dump(relf_dic,
              open('obs_landmask.json', "w"),
              sort_keys=False,
              indent=4,
              separators=(",", ": "))

    return


def shift_row_to_bottom(df, index_to_shift):
    idx = [i for i in df.index if i != index_to_shift]
    return df.loc[idx + [index_to_shift]]

def merge_data(model_lib,cmip_lib,model_name):
    model_lib,cmip_lib = check_regions(model_lib,cmip_lib)
    merge_lib = cmip_lib.merge(model_lib)
    merge_lib = check_units(merge_lib)
    for stat in merge_lib.df_dict:
        for season in merge_lib.df_dict[stat]:
            for region in merge_lib.df_dict[stat][season]:
                highlight_models = []
                df = merge_lib.df_dict[stat][season][region]
                for model in df["model"].tolist():
                    if "e3sm" in model.lower():
                        highlight_models.append(model)
                    if model in model_name:
                        idxs = df[df.iloc[:, 0] == model].index
                        df.loc[idxs, "model"] = model_name
                highlight_models.append(model_name)
                for model in highlight_models:
                    for idx in df[df.iloc[:, 0] == model].index:
                        df = shift_row_to_bottom(df, idx)
                merge_lib.df_dict[stat][season][region] = df.fillna(value=np.nan)
                del(df)
    return merge_lib

def check_regions(data_lib,ref_lib):
    regions = [x for x in data_lib.regions if x in ref_lib.regions]
    for stat in ref_lib.df_dict:
        for season in ref_lib.df_dict[stat]:
            subset_dict = dict((k, ref_lib.df_dict[stat][season][k]) for k in regions)
            ref_lib.df_dict[stat][season] = subset_dict
            del(subset_dict)
    ref_lib.regions = regions

    for stat in data_lib.df_dict:
        for season in data_lib.df_dict[stat]:
            subset_dict = dict((k, data_lib.df_dict[stat][season][k]) for k in regions)
            data_lib.df_dict[stat][season] = subset_dict
            del(subset_dict)
    data_lib.regions = regions

    return data_lib,ref_lib

def check_references(data_dict):
    reference_alias = {'CERES-EBAF-4-1': 'ceres_ebaf_v4_1',
                       'CERES-EBAF-4-0': 'ceres_ebaf_v4_0',
                       'CERES-EBAF-2-8': 'ceres_ebaf_v2_8',
                       'GPCP-2-3'      : 'GPCP_v2_3',
                       'GPCP-2-2'      : 'GPCP_v2_2',
                       'GPCP-3-2'      : 'GPCP_v3_2',
                       'NOAA_20C'      : 'NOAA-20C',
                       'ERA-INT'       : 'ERA-Interim',
                       'ERA-5'         : 'ERA5'}
    for key,values in data_dict.items():
        for i,value in enumerate(values):
            if value in reference_alias.keys():
                values[i] = reference_alias[value]
        data_dict[key] = values
    return data_dict

def check_units(data_lib):
    # we define fixed sets of variables used for final plotting.
    units_all = {
        "prw"   : "[kg m$^{-2}$]", "pr"    : "[mm d$^{-1}$]", "prsn"   : "[mm d$^{-1}$]",
        "prc"   : "[mm d$^{-1}$]", "hfls"  : "[W m$^{-2}$]",  "hfss"   : "[W m$^{-2}$]",
        "clivi" : "[kg $m^{-2}$]", "clwvi" : "[kg $m^{-2}$]", "psl"    : "[Pa]",
        "rlds"  : "[W m$^{-2}$]",  "rldscs": "[W $m^{-2}$]",  "evspsbl": "[kg m$^{-2} s^{-1}$]",
        "rtmt"  : "[W m$^{-2}$]",  "rsdt"  : "[W m$^{-2}$]",  "rlus"   : "[W m$^{-2}$]",
        "rluscs": "[W m$^{-2}$]",  "rlut"  : "[W m$^{-2}$]",  "rlutcs" : "[W m$^{-2}$]",
        "rsds"  : "[W m$^{-2}$]",  "rsdscs": "[W m$^{-2}$]",  "rstcre" : "[W m$^{-2}$]",
        "rltcre": "[W m$^{-2}$]",  "rsus"  : "[W m$^{-2}$]",  "rsuscs" : "[W m$^{-2}$]",
        "rsut"  : "[W m$^{-2}$]",  "rsutcs": "[W m$^{-2}$]",  "ts"     : "[K]",
        "tas"   : "[K]",           "tauu"  : "[Pa]",          "tauv"   : "[Pa]",
        "zg-500": "[m]",           "ta-200": "[K]",           "sfcWind": "[m s$^{-1}$]",
        "ta-850": "[K]",           "ua-200": "[m s$^{-1}$]",  "ua-850" : "[m s$^{-1}$]",
        "va-200": "[m s$^{-1}$]",  "va-850": "[m s$^{-1}$]",  "uas"    : "[m s$^{-1}$]",
        "vas"   : "[m s$^{-1}$]",  "tasmin": "[K]",           "tasmax" : "[K]",
        "clt"   : "[%]"}

    common_vars = [x for x in data_lib.var_list if x in units_all.keys()]
    #special case
    if 'rtmt' not in common_vars:
        if ('rt' in data_lib.var_list) or ('rmt' in data_lib.var_list):
            common_vars.append('rtmt')

    #collect unit list
    common_unts = [units_all[x] for x in common_vars]

    #collect reference list
    reflist = data_lib.var_ref_dict.copy()
    for var in reflist:
        if var not in common_vars:
            if var in ['rt','rmt']:
                data_lib.var_ref_dict['rtmt'] = data_lib.var_ref_dict.pop(var)
            else:
                data_lib.var_ref_dict.pop(var)
    data_lib.var_ref_dict = check_references(data_lib.var_ref_dict)
    #now clean up data to exclude vars not in common lists
    for stat in data_lib.df_dict:
        for season in data_lib.df_dict[stat]:
            for region in data_lib.df_dict[stat][season]:
                df = data_lib.df_dict[stat][season][region]
                if 'rt' in df.columns:
                    df['rtmt'] = df['rt']
                elif 'rmt' in df.columns:
                    df['rtmt'] = df['rmt']
                for var in df.columns[3:]:
                    if var not in common_vars:
                        df = df.drop(var,axis=1)
                data_lib.df_dict[stat][season][region] = df
                del(df)

    data_lib.var_list = common_vars
    data_lib.var_unit_list = common_unts

    return data_lib

def collect_metrics_data(parameter,group):
    #merge data to an exisiting cmip base
    cmip_files = glob.glob(os.path.join(
            parameter['cmip_path'],
            group,
            parameter['cmip_name'].split(".")[0],
            parameter['cmip_name'].split(".")[1],
            parameter['cmip_name'].split(".")[2],
            "*.json"))
    if len(cmip_files) > 0 and os.path.exists(cmip_files[0]):
        print('CMIP PCMDI DIAGs for Sythetic Metrics Found, Read data...')
        cmip_lib = Metrics(cmip_files)
        cmip_lib = check_units(cmip_lib)
    else:
        exit("Warning: CMIP PCMDI DIAGs for Sythetic Metrics Not Found,....")

    model_name = '.'.join([
        parameter['test_name'].split(".")[2],
        parameter['test_name'].split(".")[3]])
    model_files = glob.glob(os.path.join(
        parameter['test_path'],
        group,
        parameter['test_name'].split(".")[0],
        parameter['test_name'].split(".")[1],
        parameter['case_id'],
        "*.json"))
    if len(model_files) > 0 and os.path.exists(model_files[0]):
        print('{} PCMDI DIAGs for Sythetic Metrics Found, Read data...'.format(model_name))
        model_lib = Metrics(model_files)
        model_lib = check_units(model_lib)
    else:
        exit("Warning: Model PCMDI DIAGs for Sythetic Metrics Not Found,....")

    #merge model data with reference cmip data
    merge_lib = merge_data(model_lib,cmip_lib,model_name)

    return merge_lib

def archive_data(parameter,stat,region,season,data_dict,
                 model_name,var_names,var_units,outdir):
    outdic = pd.DataFrame(data_dict)
    outdic = outdic.drop(columns=["model_run"])
    for var in list(outdic.columns.values[3:]):
        if var not in var_names:
            outdic = outdic.drop(columns=[var])
        else:
            # replace the variable with the name + units
            outdic.columns.values[outdic.columns.values.tolist().index(var)] = (
                var_units[var_names.index(var)]
            )
    # save data to .csv file
    if not os.path.exists(outdir):
        os.makedirs(outdir)
    outfile = "{}_{}_{}_{}.csv".format(stat,region,season,model_name)
    outdic.to_csv(os.path.join(outdir,outfile))
    return

def parcord_metric_plot(parameter,group,data_lib):
    season = "ann"
    metric_dict = {"rms_xyt"     : "RMSE"}
    model_name = '.'.join([
        parameter['test_name'].split(".")[2],
        parameter['test_name'].split(".")[3]])

    # process figure
    fontsize = 20
    figsize = (40, 18)
    shrink = 0.8
    legend_box_xy = (1.08, 1.18)
    legend_box_size = 4
    legend_lw = 1.5
    legend_fontsize = fontsize * 0.8
    legend_ncol = int(7 * figsize[0] / 40.0)
    legend_posistion = (0.50, -0.14)
    # hide markers for CMIP models
    identify_all_models = False
    # colors for highlight lines
    xcolors = ["#000000","#e41a1c","#ff7f00","#4daf4a","#f781bf",
               "#a65628","#984ea3","#999999","#377eb8","#dede00"]

    for stat in metric_dict.keys():
        for region in data_lib.regions:
            var_names = data_lib.var_list.copy()
            var_units = data_lib.var_unit_list.copy()
            # data for final plot
            data_dict = data_lib.df_dict[stat][season][region].reset_index(drop=True)
            #drop data if all is NaNs
            for column in data_dict.columns[3:]:
                if np.all(np.isnan(data_dict[column].to_numpy())):
                    data_dict = data_dict.drop(column, axis=1)
                    index = var_names.index(column)
                    var_names.remove(var_names[index])
                    var_units.remove(var_units[index])

            highlight_model1 = []
            for model in data_dict['model'].to_list():
                if "e3sm" in model.lower():
                   highlight_model1.append(model)
                elif model in model_name:
                   highlight_model1.append(model_name)

            # ensemble mean for CMIP group
            irow_sub = data_dict[data_dict['model'] == highlight_model1[0]].index[0]
            data_dict.loc["CMIP MMM"] = data_dict[:irow_sub].mean(
                    numeric_only=True, skipna=True)
            data_dict.at["CMIP MMM", "model"] = "CMIP MMM"
            data_dict.loc["E3SM MMM"] = data_dict[irow_sub:].mean(
                    numeric_only=True, skipna=True)
            data_dict.at["E3SM MMM", "model"] = "E3SM MMM"

            if parameter['save_data']:
                outdir = os.path.join(parameter['out_dir'],region)
                archive_data(parameter,stat,region,season,data_dict,
                             model_name,var_names,var_units,outdir)

            model_list = data_dict['model'].to_list()
            highlight_model2 = data_dict['model'].to_list()[-3:]

	    #final plot data
            data_var = data_dict[var_names].to_numpy()

            #label information
            var_labels = []
            for i,var in enumerate(var_names):
                var_labels.append(var + "\n"  + var_units[i])

            xlabel = "Metric"
            ylabel = '{} ({})'.format(metric_dict[stat],stat.upper())
            # colors for highlight lines
            lncolors = xcolors[1 : len(highlight_model2)] + [xcolors[0]]
            fig,ax = parallel_coordinate_plot(
                data_var,
                var_labels,
                model_list,
                model_names2=highlight_model1,
                group1_name="CMIP6",
                group2_name="E3SM",
                models_to_highlight=highlight_model2,
                models_to_highlight_colors=lncolors,
                models_to_highlight_labels=highlight_model2,
                identify_all_models=identify_all_models,
                vertical_center="median",
                vertical_center_line=True,
                title="Model Performance of {} Climatology ({}, {})".format(
                      season.upper(),stat.upper(), region.upper()),
                figsize=figsize,
                colormap="tab20_r",
                show_boxplot=False,
                show_violin=True,
                violin_colors=("lightgrey", "pink"),
                legend_ncol=legend_ncol,
                legend_bbox_to_anchor=legend_posistion,
                legend_fontsize=fontsize * 0.85,
                xtick_labelsize=fontsize * 0.95,
                ytick_labelsize=fontsize * 0.95,
                logo_rect=[0, 0, 0, 0],
                logo_off=True)

            # Save figure as an image file
            outdir = os.path.join(parameter['out_dir'],region)
            if not os.path.exists(outdir):
                os.makedirs(outdir)
            outfile = "{}_{}_{}_parcord_{}.png".format(stat,region,season,model_name)
            fig.savefig(os.path.join(outdir,outfile),facecolor="w", bbox_inches="tight")


def portrait_metric_plot(parameter,group,data_lib):
    seasons = ["djf", "mam", "jja", "son"]
    metric_dict = {"cor_xy"  : "Pattern Corr.",
                   "rms_xy"  : "Normalized RMSE by Median"}
    model_name = '.'.join([
        parameter['test_name'].split(".")[2],
        parameter['test_name'].split(".")[3]])

    # process figure
    fontsize = 20
    add_vertical_line = True
    figsize = (40, 18)
    legend_box_xy = (1.08, 1.18)
    legend_box_size = 4
    legend_lw = 1.5
    shrink = 0.8
    legend_fontsize = fontsize * 0.8

    var_names = data_lib.var_list
    var_units = data_lib.var_unit_list

    for stat in metric_dict.keys():
        for region in data_lib.regions:
            data_nor = dict()
            for season in seasons:
                data_dict = data_lib.df_dict[stat][season][region].copy()
                if stat == "cor_xy":
                   data_nor[season] = data_dict[var_names].to_numpy().T
                else:
                   data_nor[season] = normalize_by_median(
		       data_dict[var_names].to_numpy().T, axis=1)
                if parameter['save_data']:
                   data_dict[var_names] = data_nor[season]
                   outdir = os.path.join(parameter['out_dir'],region)
                   archive_data(parameter,stat,region,season,data_dict,
                                model_name,var_names,var_units,outdir)
	    # data for final plot
            data_all_nor = np.stack(
	       [data_nor["djf"], data_nor["mam"], data_nor["jja"], data_nor["son"]]
	    )

            lable_colors = []
            highlight_models = []
            model_list = data_dict['model'].to_list()
            for model in model_list:
                if "e3sm" in model.lower():
                   highlight_models.append(model)
                   lable_colors.append("#5170d7")
                elif model in model_name:
                   highlight_models.append(model_name)
                   lable_colors.append("#FC5A50")
                else:
                   lable_colors.append("#000000")

            if stat == "cor_xy":
               var_range = (0, 1.0)
               cmap_color = "YlOrBr"
               cmap_bounds = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.65,
	                      0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0]
            else:
               var_range = (-0.5, 0.5)
               cmap_color = "RdYlBu_r"
               cmap_bounds = [-0.5, -0.4, -0.3, -0.2, -0.1,
	                      0, 0.1,0.2, 0.3, 0.4, 0.5]

            fig, ax, cbar = portrait_plot(
                    data_all_nor,
                    xaxis_labels=model_list,
                    yaxis_labels=var_names,
                    cbar_label=metric_dict[stat],
                    cbar_label_fontsize=fontsize * 1.0,
                    cbar_tick_fontsize=fontsize,
                    box_as_square=True,
                    vrange=var_range,
                    figsize=figsize,
                    cmap=cmap_color,
                    cmap_bounds=cmap_bounds,
                    cbar_kw={"extend": "both", "shrink": shrink},
                    missing_color="white",
                    legend_on=True,
                    legend_labels=["DJF", "MAM", "JJA", "SON"],
                    legend_box_xy=legend_box_xy,
                    legend_box_size=legend_box_size,
                    legend_lw=legend_lw,
                    legend_fontsize=legend_fontsize,
                    logo_rect=[0, 0, 0, 0],
                    logo_off=True)

            ax.axvline(x=len(x_labels)-len(highlight_models),color="k",linewidth=3)
            ax.set_xticklabels(model_list,rotation=45,va="bottom",ha="left")
            ax.set_yticklabels(y_labels,rotation=0,va="center",ha="right")
            for xtick,color in zip(ax.get_xticklabels(),lable_colors):
                xtick.set_color(color)
            ax.yaxis.label.set_color(lable_colors[0])

            # Save figure as an image file
            outdir = os.path.join(parameter['out_dir'],region)
            if not os.path.exists(outdir):
                os.makedirs(outdir)
            outfile = "{}_{}_4season_{}.png".format(stat,region,model_name)
            fig.savefig(os.path.join(outdir,outfile),facecolor="w", bbox_inches="tight")

    return

##############################
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
   'pcmdi_diags',
   '{}_{}_catalogue.json'.format(
    reference_data_path,
    '{{subset}}')
)
obs_dic = json.load(open(observation_file))

{%- if "mean_climate" in subset %}
######################################
# call pcmdi mean climate diagnostics
#####################################
compute_regions = '{{regions}}'.split(",")
compute_variables = '{{vars}}'.split(",")
#assiagn region to each variable
variable_region(
    compute_regions,
    compute_variables
)
###################################################
# generate the command list for each reference and
# each variable (will execuate in parallel later)
lstcmd = []
for var in compute_variables:
  vkey = var.split("-")[0]
  if vkey in obs_dic.keys():
    refset = obs_dic[vkey]['set']
    lstcmd.append(" ".join([
                  'mean_climate_driver.py',
                  '-p  parameterfile.py'  ,
                  '--vars'                , '{}'.format(var),
                  '-r'                    , '{}'.format(refset),
                  '--case_id'             , '{}'.format('${case_id}')
                  ]))

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
  exit("ERROR: {} jobs failed".format('{{subset}}'))
else:
  print("successfully finish all jobs....")
  #time delay to ensure process completely finished
  time.sleep(1)

{% if run_type == "model_vs_obs" %}
synthetic_plot = '{{sythentic_plots}}'
if synthetic_plot == "y":
   print("generate sythentic metrics plot ...")
   parameter = OrderedDict()
   parameter['save_data'] = True
   parameter['cmip_path'] = '{{pcmdi_data_path}}'
   parameter['cmip_name'] = '{{pcmdi_cmip_clim}}'
   parameter['test_name'] = '{{model_name}}'
   parameter['test_path'] = os.path.join('pcmdi_diags','metrics_results')
   parameter['case_id']   = '${case_id}'
   parameter['out_dir']    = os.path.join('${results_dir}','ERROR_metric')
   merge_lib = collect_metrics_data(parameter,'mean_climate')
   print("Processing Portrait  Plots (4 seasons)....")
   portrait_metric_plot(parameter,'mean_climate',merge_lib)
   print("Processing Parallel Coordinate Plots (Annual Cycle)....")
   parcord_metric_plot(parameter,'mean_climate',merge_lib)
{%- endif %}

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
  exit("ERROR: {} jobs failed".format('{{subset}}'))
else:
  print("successfully finish all jobs....")
  #time delay to ensure process completely finished
  time.sleep(1)

{%- endif %}

{%- if "enso" in subset %}
#############################################
# call enso_driver.py to process diagnostics
#############################################

#orgnize observation var list
enso_obsvar_dict(obs_dic,"{{vars}}".split(","))

#orgnize observation landmask
enso_obsvar_lmsk(obs_dic,"{{vars}}".split(","))

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
  exit("ERROR: {} jobs failed".format('{{subset}}'))
else:
  print("successfully finish all jobs....")
  #time delay to ensure process completely finished
  time.sleep(1)
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

###########################################
# reorgnize pcmdi diagnostics output
###########################################
# Prepare configuration file
cat > graphic_viewer.py << EOF
import os
import glob
import json
import time
import datetime
import collections
from collections import OrderedDict

def get_mean_climate_graphics(regions,variables,fig_format,input_dir,output_dir):
    diag_metric = "mean_climate"
    seasons = ['DJF','MAM','JJA','SON','AC']
    input_dir = input_dir.replace("%(metric_type)",diag_metric)

    fig_sets = OrderedDict()
    fig_sets['CLIM_patttern'] = ['graphics','*']

    for fset in fig_sets.keys():
      fdir = input_dir.replace('%(output_type)',fig_sets[fset][0] )
      output = output_dir.replace("%(group_type)",fset)
      for region in regions:
        for sea in seasons:
          outpath = os.path.join(output,region,sea)
          if not os.path.exists(outpath):
              os.makedirs(outpath)
          for var in variables:
             fpaths = sorted(glob.glob(os.path.join(fdir,var,
                     '{}{}_{}*.{}'.format(fig_sets[fset][1],region,sea,fig_format))))
             for fpath in fpaths:
                refname = fpath.split("/")[-2]
                filname = fpath.split("/")[-1]
                outfile = os.path.join(outpath,filname)
                os.rename(fpath,outfile)

    return

def get_variability_graphics(modes,fig_format,input_dir,output_dir):
    diag_metric = "variability_modes"
    input_dir = input_dir.replace("%(metric_type)",diag_metric)

    fig_sets = OrderedDict()
    fig_sets['MOV_eofvar']  = ['diagnostic_results','EG_Spec*']
    fig_sets['MOV_telecon'] = ['graphics','*teleconnection']
    fig_sets['MOV_pattern'] = ['graphics','*']

    for mode in modes:
      for fset in fig_sets.keys():
         fdir = input_dir.replace('%(output_type)',fig_sets[fset][0] )
         output = output_dir.replace("%(group_type)",fset)
         fpaths = sorted(glob.glob(os.path.join(fdir,mode,'*',
                         '{}.{}'.format(fig_sets[fset][1],fig_format))))
         for fpath in fpaths:
             refname = fpath.split("/")[-2]
             filname = fpath.split("/")[-1]
             outpath = os.path.join(output,'{}_model_vs_{}'.format(mode,refname))
             if not os.path.exists(outpath):
                os.makedirs(outpath)
             outfile = os.path.join(outpath,filname)
             os.rename(fpath,outfile)
    return

def get_enso_graphics(groups,fig_format,refname,input_dir,output_dir):
    diag_metric = "enso_metric"
    input_dir = input_dir.replace("%(metric_type)",diag_metric)

    fig_sets = OrderedDict()
    fig_sets['ENSO_metric'] = ['graphics','*']

    for fset in fig_sets.keys():
      for group in groups:
         fdir = input_dir.replace('%(output_type)',fig_sets[fset][0] )
         output = output_dir.replace("%(group_type)",fset)
         fpaths = sorted(glob.glob(os.path.join(fdir,group,
                         '{}.{}'.format(fig_sets[fset][1],fig_format))))
         for fpath in fpaths:
             filname = fpath.split("/")[-1]
             outpath = os.path.join(output,'{}_model_vs_{}'.format(group,refname))
             if not os.path.exists(outpath):
                os.makedirs(outpath)
             outfile = os.path.join(outpath,filname)
             os.rename(fpath,outfile)

    return

#############
fig_format = '{{ figure_format }}'
diag_types = ['metrics_results','diagnostic_result','graphics']

input_template = os.path.join(
    'pcmdi_diags',
    '%(output_type)',
    '%(metric_type)',
    '${model_name}'.split(".")[0],
    '${model_name}'.split(".")[1],
    '${case_id}',
)

out_path = os.path.join(
    '${results_dir}',
    '%(group_type)'
)

{%- if ("mean_climate" in subset) %}
compute_regions = '{{ regions }}'.split(",")
compute_variables = '{{ vars }}'.split(",")
get_mean_climate_graphics(
  compute_regions,compute_variables,
  fig_format,input_template,out_path
)
{% endif %}

{%- if ("variability_mode" in subset) %}
{%- if ("variability_mode_atm" in subset) %}
compute_modes = '{{ atm_modes }}'.split(",")
{% elif ("variability_mode_cpl" in subset) %}
compute_modes = '{{ cpl_modes }}'.split(",")
{%- endif %}
get_variability_graphics(
   compute_modes,fig_format,
   input_template,out_path
)
{%- endif %}

{%- if ("enso" in subset) %}
compute_groups = '{{ enso_groups }}'.split(",")
obs_dict = json.load(open('obs_catalogue.json'))
obs_name = list(obs_dict.keys())[0]
get_enso_graphics(
   compute_groups,fig_format,
   obs_name,input_template,out_path
)
{% endif %}

EOF
################################
# Run diagnostics
command="srun -N 1 python -u graphic_viewer.py"
# Run diagnostics
time ${command}
if [ $? != 0 ]; then
  cd {{ scriptDir }}
  echo 'ERROR (12)' > {{ prefix }}.status
  exit 12
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
