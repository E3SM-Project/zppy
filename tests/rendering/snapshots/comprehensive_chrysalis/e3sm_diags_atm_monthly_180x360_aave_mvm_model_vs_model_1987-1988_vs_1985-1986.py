import os
import numpy
from e3sm_diags.parameter.core_parameter import CoreParameter
from e3sm_diags.parameter.diurnal_cycle_parameter import DiurnalCycleParameter
from e3sm_diags.parameter.enso_diags_parameter import EnsoDiagsParameter
from e3sm_diags.parameter.qbo_parameter import QboParameter
from e3sm_diags.parameter.streamflow_parameter import StreamflowParameter
from e3sm_diags.parameter.tc_analysis_parameter import TCAnalysisParameter
from e3sm_diags.parameter.tropical_subseasonal_parameter import TropicalSubseasonalParameter


from e3sm_diags.run import runner

short_name = 'v3.LR.historical_0051'
test_ts = '/zppy_snapshot/output/post/atm/180x360_aave/ts/monthly/2yr'
start_yr = int('1987')
end_yr = int('1988')
num_years = end_yr - start_yr + 1
ref_start_yr = 1985

param = CoreParameter()

# Model
param.test_data_path = 'climo_test'
param.test_name = 'v3.LR.historical_0051'
param.short_test_name = short_name

# Ref

# Reference
param.reference_data_path = 'climo_ref'
param.ref_name = 'v3.LR.historical_0051'
param.short_ref_name = 'same simulation'
# Optionally, swap test and reference model
if False:
   param.test_data_path, param.reference_data_path = param.reference_data_path, param.test_data_path
   param.test_name, param.ref_name = param.ref_name, param.test_name
   param.short_test_name, param.short_ref_name = param.short_ref_name, param.short_test_name

# Output dir
param.results_dir = 'model_vs_model_1987-1988'

# Additional settings
param.run_type = 'model_vs_model'
param.diff_title = 'Difference'
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

# Reference
enso_param.reference_data_path = '/zppy_snapshot/output/post/atm/180x360_aave/ts/monthly/2yr'
enso_param.ref_name = 'v3.LR.historical_0051'
enso_param.short_ref_name = 'same simulation'
enso_param.ref_start_yr = '1985'
enso_param.ref_end_yr = '1986'
# Optionally, swap test and reference model
if False:
   enso_param.test_data_path, enso_param.reference_data_path = enso_param.reference_data_path, enso_param.test_data_path
   enso_param.test_name, enso_param.ref_name = enso_param.ref_name, enso_param.test_name
   enso_param.short_test_name, enso_param.short_ref_name = enso_param.short_ref_name, enso_param.short_test_name
params.append(enso_param)
trop_param = TropicalSubseasonalParameter()
trop_param.test_data_path = '/zppy_snapshot/output/post/atm/180x360_aave/ts/daily/2yr'
trop_param.test_name = short_name
trop_param.test_start_yr = start_yr
trop_param.test_end_yr = end_yr

trop_param.reference_data_path = '/zppy_snapshot/output/post/atm/180x360_aave/ts/daily/2yr'
trop_param.ref_name = 'v3.LR.historical_0051'
trop_param.short_ref_name = 'same simulation'
trop_param.ref_start_yr = '1985'
trop_param.ref_end_yr = '1986'
# Optionally, swap test and reference model
if False:
   trop_param.test_data_path, trop_param.reference_data_path = trop_param.reference_data_path, trop_param.test_data_path
   trop_param.test_name, trop_param.ref_name = trop_param.ref_name, trop_param.test_name
   trop_param.short_test_name, trop_param.short_ref_name = trop_param.short_ref_name, trop_param.short_test_name
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

# Reference
qbo_param.reference_data_path = '/zppy_snapshot/output/post/atm/180x360_aave/ts/monthly/2yr'
qbo_param.ref_name = 'v3.LR.historical_0051'
qbo_param.short_ref_name = 'same simulation'
# Optionally, swap test and reference model
if False:
   qbo_param.test_data_path, qbo_param.reference_data_path = qbo_param.reference_data_path, qbo_param.test_data_path
   qbo_param.test_name, qbo_param.ref_name = qbo_param.ref_name, qbo_param.test_name
   qbo_param.short_test_name, qbo_param.short_ref_name = qbo_param.short_ref_name, qbo_param.short_test_name
params.append(qbo_param)
dc_param = DiurnalCycleParameter()
dc_param.test_data_path = 'climo_diurnal_8xdaily_test'
dc_param.short_test_name = short_name
# Plotting diurnal cycle amplitude on different scales. Default is True
dc_param.normalize_test_amp = False

# Reference
dc_param.reference_data_path = 'climo_diurnal_ref'
dc_param.ref_name = 'v3.LR.historical_0051'
dc_param.short_ref_name = 'same simulation'
# Optionally, swap test and reference model
if False:
   dc_param.test_data_path, dc_param.reference_data_path = dc_param.reference_data_path, dc_param.test_data_path
   dc_param.test_name, dc_param.ref_name = dc_param.ref_name, dc_param.test_name
   dc_param.short_test_name, dc_param.short_ref_name = dc_param.short_ref_name, dc_param.short_test_name
params.append(dc_param)
streamflow_param = StreamflowParameter()
streamflow_param.test_data_path = '/zppy_snapshot/output/post/rof/native/ts/monthly/2yr'
streamflow_param.test_name = short_name
streamflow_param.test_start_yr = start_yr
streamflow_param.test_end_yr = end_yr

# Reference
streamflow_param.reference_data_path = '/zppy_snapshot/output/post/rof/native/ts/monthly/2yr'
streamflow_param.ref_name = 'v3.LR.historical_0051'
streamflow_param.short_ref_name = 'same simulation'
streamflow_param.ref_start_yr = '1985'
streamflow_param.ref_end_yr = '1986'
streamflow_param.gauges_path = '/lcrc/group/e3sm/diagnostics/observations/Atm/time-series/GSIM/GSIM_catchment_characteristics_all_1km2.csv'
# Optionally, swap test and reference model
if False:
   streamflow_param.test_data_path, streamflow_param.reference_data_path = streamflow_param.reference_data_path, streamflow_param.test_data_path
   streamflow_param.test_name, streamflow_param.ref_name = streamflow_param.ref_name, streamflow_param.test_name
   streamflow_param.short_test_name, streamflow_param.short_ref_name = streamflow_param.short_ref_name, streamflow_param.short_test_name
params.append(streamflow_param)
tc_param = TCAnalysisParameter()
tc_param.test_data_path = "/zppy_snapshot/output/post/atm/tc-analysis_1987_1988"
tc_param.short_test_name = short_name
tc_param.test_start_yr = "1987"
tc_param.test_end_yr = "1988"

# Reference
tc_param.reference_data_path = '/zppy_snapshot/output/post/atm/tc-analysis_1985_1986'
tc_param.ref_name = 'v3.LR.historical_0051'
tc_param.short_ref_name = 'same simulation'
tc_param.ref_start_yr = '1985'
tc_param.ref_end_yr = '1986'
# Optionally, swap test and reference model
if False:
   tc_param.test_data_path, tc_param.reference_data_path = tc_param.reference_data_path, tc_param.test_data_path
   tc_param.test_name, tc_param.ref_name = tc_param.ref_name, tc_param.test_name
   tc_param.short_test_name, tc_param.short_ref_name = tc_param.short_ref_name, tc_param.short_test_name
params.append(tc_param)

# Run
runner.sets_to_run = ['lat_lon', 'zonal_mean_xy', 'enso_diags', 'qbo', 'diurnal_cycle', 'streamflow', 'tropical_subseasonal', 'tc_analysis']
runner.run_diags(params)
