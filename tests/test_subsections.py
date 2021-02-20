import argparse
from configobj import ConfigObj
from pprint import pprint
from validate import Validator
import os

import sys
sys.path.append("..")
from utils import getTasks

# Command line parser
parser = argparse.ArgumentParser(description='Launch E3SM post-processing tasks')
parser.add_argument(
    '-c', '--config', type=str, help='configuration file',required=True)
args = parser.parse_args()

# Subdirectory where templates are located
templateDir = os.path.join( '..', 'templates' )

# Read configuration file and validate it
config = ConfigObj(args.config, configspec=os.path.join(templateDir, 'default.ini'))
validator = Validator()

result = config.validate(validator)
if result != True:
  print('Configuration file validation failed')
  #raise Exception
else:
  print('Configuration file validation passed')

# Add templateDir to config
config['default']['templateDir'] = templateDir

# List of tasks
for section in ('ts', 'climo'):
  print("---------- %s ----------" % (section))
  print("-- %s --" % ('default'))
  print(config['default'])
  print("-- %s --" % (section))
  print(config[section])
  tasks = getTasks(config, section)
  pprint(tasks)

