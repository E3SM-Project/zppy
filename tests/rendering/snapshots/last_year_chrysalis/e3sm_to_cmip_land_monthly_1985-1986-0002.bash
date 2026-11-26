#!/bin/bash

# Running on chrysalis

#SBATCH  --job-name=e3sm_to_cmip_land_monthly_1985-1986-0002
#SBATCH  --account=e3sm
#SBATCH  --nodes=1
#SBATCH  --output=/zppy_snapshot/output/post/scripts/e3sm_to_cmip_land_monthly_1985-1986-0002.o%j
#SBATCH  --exclusive
#SBATCH  --time=00:30:00


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
echo "RUNNING ${id}" > e3sm_to_cmip_land_monthly_1985-1986-0002.status

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
echo "${pkg_manager} list e3sm_to_cmip:"
${pkg_manager} list e3sm_to_cmip || true # If we can't print this, just continue on.

# Create temporary workdir
hash=`mktemp --dry-run -d XXXX`
workdir=tmp.e3sm_to_cmip_land_monthly_1985-1986-0002.${id}.${hash}
mkdir ${workdir}
cd ${workdir}

# From the ts task
dest=/zppy_snapshot/output/post/lnd/180x360_aave/ts/monthly/2yr

tmp_dir=tmp_e3sm_to_cmip_land_monthly_1985-1986-0002

# Generate CMIP ts
cat > default_metadata.json << EOF
{
  "#note_source_type": "explanation of what source_type is goes here",

  "source_type": "AOGCM AER",

  "#note_experiment_id": "CMIP6 valid experiment_ids are found in CMIP6_CV.json",

  "experiment_id": "piControl",

  "activity_id": "CMIP",

  "sub_experiment_id": "none",

  "realization_index": "1",

  "initialization_index": "1",

  "physics_index": "1",

  "forcing_index": "1",

  "#note_run_variant": "Text stored in attribute variant_info (recommended, not required description of run variant)",

  "run_variant": "",

  "parent_experiment_id": "piControl-spinup",

  "parent_activity_id": "CMIP",

  "parent_source_id": "E3SM-1-0",

  "parent_variant_label": "r1i1p1f1",

  "parent_time_units": "days since 0001-01-01",

  "branch_method": "standard",

  "branch_time_in_child": 0.0,

  "branch_time_in_parent": 0.0,

  "#note_institution_id": "institution_id must be registered at https://github.com/WCRP-CMIP/CMIP6_CVs/issues/new ",

  "institution_id": "E3SM-Project",

  "#note_source_id": "source_id (model name) must be registered at https://github.com/WCRP-CMIP/CMIP6_CVs/issues/new ",

  "source_id": "E3SM-1-0",

  "calendar": "noleap",

  "grid": "data regridded to a CMIP6 standard 1x1 degree lonxlat grid from the native grid using an area-average preserving method.",

  "grid_label": "gr",

  "nominal_resolution": "100 km",

  "license": "CMIP6 model data produced by E3SM is licensed under a Creative Commons Attribution ShareAlike 4.0 International License (https://creativecommons.org/licenses). Consult https://pcmdi.llnl.gov/CMIP6/TermsOfUse for terms of use governing CMIP6 output, including citation requirements and proper acknowledgment. Further information about this data, including some limitations, can be found via the further_info_url (recorded as a global attribute in this file) and at https:///pcmdi.llnl.gov/. The data producers and data providers make no warranty, either express or implied, including, but not limited to, warranties of merchantability and fitness for a particular purpose. All liabilities arising from the supply of the information (including any liability arising in negligence) are excluded to the fullest extent permitted by law.",

  "#output": "Root directory for output (can be either a relative or full path)",

  "outpath": "CMIP6",

  "#note_optional": " **** The following descriptors are optional and may be set to an empty string ",

  "project PI": "Dave Bader (bader2@llnl.gov)",

  "data contact": "E3SM-DATA-SUPPORT@LISTSERV.LLNL.GOV",

  "history": "Output from 20180129.DECKv1b_piControl.ne30_oEC.edison. compset = A_WCYCL1850S_CMIP6",

  "comment": "This is the default metadata file, any data  should only be used for testing purposes",

  "references": "Golaz, J.-C., P. M. Caldwell, L. P. Van Roekel and co-authors, 2019: The DOE E3SM coupled model version 1: Overview and evaluation at standard resolution. JAMES, doi: 10.1029/2018MS001603; http://e3sm.org'",

  "#note_CV": " **** The following will be obtained from the CV and do not need to be defined here",

  "sub_experiment": "none",

  "institution": "E3SM-Project",

  "source": "E3SM 1.0 (2018)",

  "#note_CMIP6": " **** The following are set correctly for CMIP6 and should not normally need editing",

  "_control_vocabulary_file": "CMIP6_CV.json",

  "_AXIS_ENTRY_FILE": "CMIP6_coordinate.json",

  "_FORMULA_VAR_FILE": "CMIP6_formula_terms.json",

  "_cmip6_option": "CMIP6",

  "mip_era": "CMIP6",

  "parent_mip_era": "CMIP6",

  "tracking_prefix": "hdl:21.14100",

  "_history_template": "%s ;rewrote data to be consistent with <activity_id> for variable <variable_id> found in table <table_id>.",

  "#output_path_template": "Template for output path directory using tables keys or global attributes, these should follow the relevant data reference syntax",

  "output_path_template": "<mip_era><activity_id><institution_id><source_id><experiment_id><_member_id><table><variable_id><grid_label><version>",

  "output_file_template": "<variable_id><table><source_id><experiment_id><_member_id><grid_label>"
}
EOF
{
  export cmortables_dir=/lcrc/group/e3sm/diagnostics/cmip6-cmor-tables/Tables
  input_dir=${dest}/1985_1986
  mkdir -p $input_dir

  cp -s $dest/*_1985??_1986??.nc $input_dir
  dest_cmip=/zppy_snapshot/output/post/lnd/180x360_aave/cmip_ts/monthly
  mkdir -p ${dest_cmip}

  # If the [ts] task vert-remapped some vars (sibling directory ts_vrt_remap/),
  # replace the corresponding ts/ symlinks with ts_vrt_remap/ ones. The inline
  # regrid loop below will detect these (via readlink) and skip them.
  dest_plev=/zppy_snapshot/output/post/lnd/180x360_aave/ts_vrt_remap/monthly/2yr
  if [ -d "${dest_plev}" ]; then
    cp -sf ${dest_plev}/*_1985??_1986??.nc $input_dir 2>/dev/null || true
  fi

  # Gate on prc_typ (atm processing type) rather than fragile input_files
  # prefix parsing — fixes #820 where input_component="eamxx" with non-eamxx
  # input_files (e.g., "AVERAGE.nmonths_x1") caused this block to be skipped.
  #call e3sm_to_cmip
  srun -N 1 e3sm_to_cmip \
  --output-path \
  ${dest_cmip}/${tmp_dir} \
  --var-list \
  'snd, mrsos, mrso, mrfso, mrros, mrro, prveg, evspsblveg, evspsblsoi, tran, tsl, lai, cLitter, cProduct, cSoilFast, cSoilMedium, cSoilSlow, fFire, fHarvest, cVeg, nbp, gpp, ra, rh' \
  --realm \
  lnd \
  --input-path \
  ${input_dir} \
  --user-metadata \
  /zppy_snapshot/output/post/scripts/${workdir}/default_metadata.json \
  --num-proc \
  12 \
  --tables-path \
  ${cmortables_dir}

  if [ $? != 0 ]; then
    cd /zppy_snapshot/output/post/scripts
    echo 'ERROR (2)' > e3sm_to_cmip_land_monthly_1985-1986-0002.status
    exit 2
  fi

  # Move output ts files to final destination
  mv ${dest_cmip}/${tmp_dir}/CMIP6/CMIP/*/*/*/*/*/*/*/*/*.nc ${dest_cmip}
  if [ $? != 0 ]; then
    cd /zppy_snapshot/output/post/scripts
    echo 'ERROR (3)' > e3sm_to_cmip_land_monthly_1985-1986-0002.status
    exit 3
  fi

  rm -r ${dest_cmip}/${tmp_dir}

}
if [ $? != 0 ]; then
  cd /zppy_snapshot/output/post/scripts
  echo 'ERROR (4)' > e3sm_to_cmip_land_monthly_1985-1986-0002.status
  exit 4
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
rm -f e3sm_to_cmip_land_monthly_1985-1986-0002.status
echo 'OK' > e3sm_to_cmip_land_monthly_1985-1986-0002.status
exit 0