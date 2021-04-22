set -e # Don't continue on error

# Generate global time series plots
# Be sure to set these variables accordingly.

# Paths
unified_script=/lcrc/soft/climate/e3sm-unified/load_latest_e3sm_unified.sh # LCRC
#unified_script=/share/apps/E3SM/conda_envs/load_latest_e3sm_unified.sh # Compy
e3sm_simulations_dir=/lcrc/group/e3sm/ac.forsyth2/E3SM_simulations
case_dir=${e3sm_simulations_dir}/20210122.v2_test01.piControl.ne30pg2_EC30to60E2r2-1900_ICG.chrysalis
web_dir=/lcrc/group/e3sm/public_html/diagnostic_output/ac.forsyth2/E3SM/v2/beta/20210122.v2_test01.piControl.ne30pg2_EC30to60E2r2-1900_ICG.chrysalis
zppy_dir=/home/ac.forsyth2/E3SM/utils/post_v2/zppy/

# Names
moc_file=mocTimeSeries_0001-0100.nc
experiment_name=20210122.v2_test01.piControl.chrysalis
figstr=coupled_v2_test01

# Years
start_yr=1
end_yr=100

################################################################################

echo 'Load unified environment'
source ${unified_script}

echo 'Create xml files for atm'
cd ${case_dir}/post/atm/glb/ts/monthly/10yr
cdscan -x glb.xml *.nc

echo 'Create ocean time series'
mkdir -p ${case_dir}/post/ocn/glb/ts/monthly/10yr
cd ${zppy_dir}/global_time_series
python ocean_month.py ${case_dir} ${start_yr} ${end_yr}

echo 'Create xml for for ocn'
cd ${case_dir}/post/ocn/glb/ts/monthly/10yr
cdscan -x glb.xml *.nc

echo 'Copy moc file'
cd ${case_dir}/post/analysis/mpas_analysis/cache/timeseries/moc
cp ${moc_file} ../../../../../ocn/glb/ts/monthly/10yr/

echo 'Update time series figures'
cd ${zppy_dir}/global_time_series
python coupled_global.py ${case_dir} ${experiment_name} ${figstr}

echo 'Copy image to web'
cp ${figstr}.png ${web_dir}/${figstr}.png
