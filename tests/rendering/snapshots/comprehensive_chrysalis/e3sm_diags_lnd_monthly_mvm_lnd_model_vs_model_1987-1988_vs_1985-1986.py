import os
import numpy
from e3sm_diags.parameter.core_parameter import CoreParameter
from e3sm_diags.parameter.lat_lon_land_parameter import LatLonLandParameter


from e3sm_diags.run import runner

short_name = 'v3.LR.historical_0051'
test_ts = ''
start_yr = int('1987')
end_yr = int('1988')
num_years = end_yr - start_yr + 1

param = CoreParameter()

# Model
param.test_name = 'v3.LR.historical_0051'
param.short_test_name = short_name

# Ref

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
land_param = LatLonLandParameter()
land_param.test_data_path = 'climo_test_land'

# Reference
land_param.reference_data_path = 'climo_ref_land'
land_param.ref_name = 'v3.LR.historical_0051'
land_param.short_ref_name = 'same simulation'
# Optionally, swap test and reference model
if True:
   land_param.test_data_path, land_param.reference_data_path = land_param.reference_data_path, land_param.test_data_path
   land_param.test_name, land_param.ref_name = land_param.ref_name, land_param.test_name
   land_param.short_test_name, land_param.short_ref_name = land_param.short_ref_name, land_param.short_test_name
params.append(land_param)

# Run
runner.sets_to_run = ['lat_lon_land']
runner.run_diags(params)
