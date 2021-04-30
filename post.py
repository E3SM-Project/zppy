import argparse
from configobj import ConfigObj
from validate import Validator
import errno
import os

from climo import climo
from ts import ts
from e3sm_diags import e3sm_diags
from e3sm_diags_vs_model import e3sm_diags_vs_model
from amwg import amwg
from mpas_analysis import mpas_analysis
from global_time_series import global_time_series

# Command line parser
parser = argparse.ArgumentParser(description='Launch E3SM post-processing tasks')
parser.add_argument(
    '-c', '--config', type=str, help='configuration file',required=True)
args = parser.parse_args()

# Subdirectory where templates are located
templateDir = os.path.join( os.path.dirname(__file__), 'templates' )

# Read configuration file and validate it
config = ConfigObj(args.config, configspec=os.path.join(templateDir, 'default.ini'))
validator = Validator()

result = config.validate(validator)
if result != True:
  print('Validation results={}'.format(result))
  raise Exception('Configuration file validation failed')
else:
  print('Configuration file validation passed')

# Add templateDir to config
config['default']['templateDir'] = templateDir

# Output script directory
output = config['default']['output']
scriptDir = os.path.join(output, 'post/scripts')
try:
    os.makedirs(scriptDir)
except OSError as exc:
    if exc.errno != errno.EEXIST:
        print('Cannot create script directory')
        raise Exception
    pass

# Determine machine to decide which header files to use
tmp = os.getenv('HOSTNAME')
if tmp.startswith('compy'):
    machine = "compy" 
elif tmp.startswith('cori'):
    machine = "cori" 
elif tmp.startswith('blues'):
    machine = "anvil"
elif tmp.startswith('chr'):
    machine = "chrysalis"
config['default']['machine'] = machine

# climo tasks
climo(config, scriptDir)

# time series tasks
ts(config, scriptDir)

# e3sm_diags tasks
e3sm_diags(config, scriptDir)

# e3sm_diags_vs_model tasks
e3sm_diags_vs_model(config, scriptDir)

# amwg tasks
amwg(config, scriptDir)

# mpas_analysis tasks
mpas_analysis(config, scriptDir)

# global time series tasks
global_time_series(config, scriptDir)
