import jinja2
import os

from utils import getTasks, getYears, submitScript, checkStatus

# -----------------------------------------------------------------------------
def glb(config, scriptDir):

    # --- Initialize jinja2 template engine ---
    templateLoader = jinja2.FileSystemLoader(searchpath=config['default']['templateDir'])
    templateEnv = jinja2.Environment( loader=templateLoader )
    template = templateEnv.get_template( 'glb.bash' )

    # --- List of tasks ---
    tasks = getTasks(config, 'glb')
    if (len(tasks) == 0):
        return

    # --- Generate and submit scripts ---
    for c in tasks:

        c['grid'] = "glb"

        # Loop over year sets
        year_sets = getYears(c['years'])
        for s in year_sets:

            c['year1'] = s[0]
            c['year2'] = s[1]
            c['scriptDir'] = scriptDir
            if c['subsection']:
                prefix = 'glb_%s_%04d-%04d' % (c['subsection'],c['year1'],c['year2'])
            else:
                prefix = 'glb_%04d-%04d' % (c['year1'],c['year2'])
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

            if not c['dry_run']:
                # Submit job
                jobid = submitScript(scriptFile)
                
                # Update status file
                with open(statusFile, 'w') as f:
                    f.write('WAITING %d\n' % (jobid))
