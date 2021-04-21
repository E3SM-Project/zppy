import argparse
from configobj import ConfigObj
from validate import Validator
import errno
import os
import re

from climo import climo
from ts import ts
from glb import glb
from e3sm_diags import e3sm_diags
from e3sm_diags_vs_model import e3sm_diags_vs_model
from amwg import amwg
from mpas_analysis import mpas_analysis

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

# global average time series tasks
glb(config, scriptDir)

# e3sm_diags tasks
e3sm_diags(config, scriptDir)

# e3sm_diags_vs_model tasks
e3sm_diags_vs_model(config, scriptDir)

# amwg tasks
amwg(config, scriptDir)

# mpas_analysis tasks
mpas_analysis(config, scriptDir)

# Create page for the simulation
analysis_dir = os.path.join(config['default']['www'], config['default']['case'])
analysis_html = os.path.join(config['default']['html_path'], config['default']['case'])
if config['e3sm_diags']['active'] and config['e3sm_diags']['atm_monthly_180x360_aave']:
  viewer_dir = dict()
  time_periods_dir = os.path.join('e3sm_diags', config['e3sm_diags']['atm_monthly_180x360_aave']['grid'])
  time_periods = os.listdir(os.path.join(analysis_dir, time_periods_dir))
  # model_vs_obs_0001-0020
  for time_period in time_periods:
    m = re.search('model_vs_obs_(\d\d\d\d)-(\d\d\d\d)', time_period)
    start_yr = int(m.group(1))
    end_yr = int(m.group(2))
    num_years = end_yr - start_yr + 1
    viewer = "{}/viewer".format(os.path.join(analysis_html, time_periods_dir, time_period))
    if num_years in viewer_dir.keys():
      viewer_dir[num_years].append(viewer)
    else:
      viewer_dir[num_years] = [viewer]
  for num_years in viewer_dir.keys():
    viewers = sorted(viewer_dir[num_years])
    for viewer in viewers:
      print(viewer)
if config['mpas_analysis']['active']:
  mpas_dir = os.path.join(analysis_dir, 'mpas_analysis')
  pages = os.listdir(mpas_dir)
  pages = ["{}".format(os.path.join(analysis_html, 'mpas_analysis', page)) for page in pages]
  for page in pages:
    print(page)

# TODO: create a nice webpage (using Pandoc?) rather than just printing links
