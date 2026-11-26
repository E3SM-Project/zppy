import os
import numpy
from e3sm_diags.parameter.core_parameter import CoreParameter


from e3sm_diags.run import runner

short_name = 'v3.LR.historical_0051'
test_ts = ''
start_yr = int('1985')
end_yr = int('1986')
num_years = end_yr - start_yr + 1

param = CoreParameter()

# Model
param.test_data_path = 'climo'
param.test_name = 'v3.LR.historical_0051'
param.short_test_name = short_name

# Ref

# Obs
param.reference_data_path = '/global/cfs/cdirs/e3sm/diagnostics/observations/Atm/climatology/'


# Output dir
param.results_dir = 'model_vs_obs_1985-1986'

# Additional settings
param.run_type = 'model_vs_obs'
param.diff_title = 'Model - Observations'
param.output_format = ['png']
param.output_format_subplot = []
param.multiprocessing = True
param.num_workers = 24
#param.fail_on_incomplete = True
params = [param]

# Model land

# Run
runner.sets_to_run = ['lat_lon']
runner.run_diags(params)
