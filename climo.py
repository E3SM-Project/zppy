import jinja2
import os
import re

from utils import getTasks, getYears, submitScript, checkStatus

# -----------------------------------------------------------------------------
def climo(config, scriptDir):

    # --- Initialize jinja2 template engine ---
    templateLoader = jinja2.FileSystemLoader(searchpath=config['default']['templateDir'])
    templateEnv = jinja2.Environment( loader=templateLoader )
    template = templateEnv.get_template( 'climo.bash' )

    # --- List of climo tasks ---
    tasks = getTasks(config, 'climo')
    if (len(tasks) == 0):
        return

    # --- Generate and submit climo scripts ---
    for c in tasks:
        if c['grid'] == "":
            tmp = os.path.basename(c['mapping_file'])
            tmp = re.sub('\.[^.]*\.nc$', '', tmp)
            tmp = tmp.split('_')
            if tmp[0] == "map":
                c['grid'] = ('%s_%s' % (tmp[-2],tmp[-1]))
            else:
                raise Exception('Cannot extract traget grid name from mapping file %s' % (c['mapping_file']))

        # Loop over year sets
        year_sets = getYears(c['years'])
        for s in year_sets:

            c['year1'] = s[0]
            c['year2'] = s[1]
            c['scriptDir'] = scriptDir
            if c['subsection']:
                sub = c['subsection']
            else:
                sub = c['grid']
            prefix = 'climo_%s_%04d-%04d' % (sub,c['year1'],c['year2'])
            print(prefix)
            c['prefix'] = prefix
            scriptFile = os.path.join(scriptDir, '%s.bash' % (prefix))
            statusFile = os.path.join(scriptDir, '%s.status' % (prefix))
            skip = checkStatus(statusFile)
            if skip:
                continue

            # Create script
            with open(scriptFile, 'w') as f:
                f.write(template.render( **c ))

            # Submit job
            jobid = submitScript(scriptFile)

            # Update status file
            with open(statusFile, 'w') as f:
                f.write('WAITING %d\n' % (jobid))

