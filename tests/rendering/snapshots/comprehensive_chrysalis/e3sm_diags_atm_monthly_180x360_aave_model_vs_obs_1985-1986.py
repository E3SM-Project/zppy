import os
import numpy
from e3sm_diags.parameter.area_mean_time_series_parameter import AreaMeanTimeSeriesParameter
from e3sm_diags.parameter.core_parameter import CoreParameter
from e3sm_diags.parameter.diurnal_cycle_parameter import DiurnalCycleParameter
from e3sm_diags.parameter.enso_diags_parameter import EnsoDiagsParameter
from e3sm_diags.parameter.qbo_parameter import QboParameter
from e3sm_diags.parameter.streamflow_parameter import StreamflowParameter
from e3sm_diags.parameter.mp_partition_parameter import MPpartitionParameter
from e3sm_diags.parameter.precip_pdf_parameter import PrecipPDFParameter
from e3sm_diags.parameter.tc_analysis_parameter import TCAnalysisParameter
from e3sm_diags.parameter.tropical_subseasonal_parameter import TropicalSubseasonalParameter


from e3sm_diags.run import runner

short_name = 'v3.LR.historical_0051'
test_ts = '/zppy_snapshot/output/post/atm/180x360_aave/ts/monthly/2yr'
start_yr = int('1985')
end_yr = int('1986')
num_years = end_yr - start_yr + 1
ref_start_yr = 1985

param = CoreParameter()

# Model
param.test_data_path = 'climo'
param.test_name = 'v3.LR.historical_0051'
param.short_test_name = short_name

# Ref

# Obs
param.reference_data_path = '/lcrc/group/e3sm/diagnostics/observations/Atm/climatology/'


# Output dir
param.results_dir = 'model_vs_obs_1985-1986'

# Additional settings
param.run_type = 'model_vs_obs'
param.diff_title = 'Model - Observations'
param.output_format = ['png']
param.output_format_subplot = []
param.multiprocessing = True
param.num_workers = 8
#param.fail_on_incomplete = True
params = [param]

# Model land
enso_param = EnsoDiagsParameter()
enso_param.test_data_path = test_ts
enso_param.test_name = short_name
enso_param.test_start_yr = start_yr
enso_param.test_end_yr = end_yr

# Obs
enso_param.reference_data_path = '/lcrc/group/e3sm/diagnostics/observations/Atm/time-series/'
enso_param.ref_start_yr = ref_start_yr
enso_param.ref_end_yr = ref_start_yr + 10

params.append(enso_param)
trop_param = TropicalSubseasonalParameter()
trop_param.test_data_path = '/zppy_snapshot/output/post/atm/180x360_aave/ts/daily/2yr'
trop_param.test_name = short_name
trop_param.test_start_yr = start_yr
trop_param.test_end_yr = end_yr

# Obs
trop_param.reference_data_path = '/lcrc/group/e3sm/diagnostics/observations/Atm/time-series/'
trop_param.ref_start_yr = 2001
trop_param.ref_end_yr = 2010

params.append(trop_param)
qbo_param = QboParameter()
qbo_param.test_data_path = test_ts
qbo_param.test_name = short_name
qbo_param.test_start_yr = start_yr
qbo_param.test_end_yr = end_yr
qbo_param.ref_start_yr = ref_start_yr
ref_end_yr = ref_start_yr + num_years - 1
if (ref_end_yr <= 1986):
  qbo_param.ref_end_yr = ref_end_yr
else:
  qbo_param.ref_end_yr = 1986

# Obs
qbo_param.reference_data_path = '/lcrc/group/e3sm/diagnostics/observations/Atm/time-series/'

params.append(qbo_param)
ts_param = AreaMeanTimeSeriesParameter()
ts_param.test_data_path = test_ts
ts_param.test_name = short_name
ts_param.start_yr = start_yr
ts_param.end_yr = end_yr

# Obs
ts_param.reference_data_path = '/lcrc/group/e3sm/diagnostics/observations/Atm/time-series/'

params.append(ts_param)
mp_param = MPpartitionParameter()
mp_param.test_data_path = test_ts
mp_param.test_name = short_name
mp_param.short_test_name = short_name
mp_param.test_start_yr = start_yr
mp_param.test_end_yr = end_yr

params.append(mp_param)
precip_pdf_param = PrecipPDFParameter()
precip_pdf_param.test_data_path = '/zppy_snapshot/output/post/atm/180x360_aave/ts/daily/2yr'
precip_pdf_param.test_name = short_name
precip_pdf_param.short_test_name = short_name
precip_pdf_param.test_start_yr = start_yr
precip_pdf_param.test_end_yr = end_yr

# Obs
precip_pdf_param.reference_data_path = '/lcrc/group/e3sm/diagnostics/observations/Atm/time-series/'
precip_pdf_param.ref_start_yr = 2001
precip_pdf_param.ref_end_yr = 2010

params.append(precip_pdf_param)
dc_param = DiurnalCycleParameter()
dc_param.test_data_path = 'climo_diurnal_8xdaily'
dc_param.short_test_name = short_name
# Plotting diurnal cycle amplitude on different scales. Default is True
dc_param.normalize_test_amp = False

# Obs
dc_param.reference_data_path = '/lcrc/group/e3sm/diagnostics/observations/Atm/climatology/'

params.append(dc_param)
streamflow_param = StreamflowParameter()
streamflow_param.test_data_path = '/zppy_snapshot/output/post/rof/native/ts/monthly/2yr'
streamflow_param.test_name = short_name
streamflow_param.test_start_yr = start_yr
streamflow_param.test_end_yr = end_yr

# Obs
streamflow_param.reference_data_path = '/lcrc/group/e3sm/diagnostics/observations/Atm/time-series/'
streamflow_param.ref_start_yr = "1986" # Streamflow gauge station data range from year 1986 to 1995
streamflow_param.ref_end_yr = "1995"

params.append(streamflow_param)
tc_param = TCAnalysisParameter()
tc_param.test_data_path = "/zppy_snapshot/output/post/atm/tc-analysis_1985_1986"
tc_param.short_test_name = short_name
tc_param.test_start_yr = "1985"
tc_param.test_end_yr = "1986"

# Obs
tc_param.reference_data_path = '/lcrc/group/e3sm/diagnostics/observations/Atm/tc-analysis/'
# For model vs obs, the ref start and end year can be any four digit strings
# For now, use all available years from obs by default
tc_param.ref_start_yr = "1979"
tc_param.ref_end_yr = "2018"

params.append(tc_param)

# Run
runner.sets_to_run = ['lat_lon', 'zonal_mean_xy', 'zonal_mean_2d', 'polar', 'cosp_histogram', 'meridional_mean_2d', 'annual_cycle_zonal_mean', 'zonal_mean_2d_stratosphere', 'enso_diags', 'qbo', 'area_mean_time_series', 'diurnal_cycle', 'streamflow', 'mp_partition', 'tropical_subseasonal', 'precip_pdf', 'tc_analysis', 'aerosol_aeronet']
runner.run_diags(params)
