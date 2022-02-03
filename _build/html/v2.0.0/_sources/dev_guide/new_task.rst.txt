*****************
Adding a new task
*****************

The task's bash file
=====================

Create ``zppy/templates/<task-name>.bash``.
This is where the bulk of the work required for a task will be.
Most of the file is task-specific, so it is difficult to describe precise steps.
Some key parts, however, are displayed below:

    .. code::

        #!/bin/bash
        {% include 'slurm_header.sh' %}

        {{ environment_commands }}

        # Turn on debug output if needed
        debug={{ debug }}
        if [[ "${debug,,}" == "true" ]]; then
          set -x
        fi

        # Script dir
        cd {{ scriptDir }}

        # Get jobid
        id=${SLURM_JOBID}

        # Update status file
        STARTTIME=$(date +%s)
        echo "RUNNING ${id}" > {{ prefix }}.status

    .. code::

        # Update status file and exit
        {% raw %}
        ENDTIME=$(date +%s)
        ELAPSEDTIME=$(($ENDTIME - $STARTTIME))
        {% endraw %}
        echo ==============================================
        echo "Elapsed time: $ELAPSEDTIME seconds"
        echo ==============================================
        echo 'OK' > {{ prefix }}.status
        exit 0


Variables of the form ``{{ <variable-name> }}`` can come from a number of sources:

1. ``zppy/templates/default.ini`` (in the form of ``<variable-name> = <variable-type>(default=<default-value>)``)
2. ``zppy/templates/<campaign>.cfg`` (in the form of ``<variable-name> = <value>``); overrides values from #1
3. The user's configuration file (in the form of ``<variable-name> = <value>``); overrides values from #1, #2

Another possible source is ``zppy/<task-name>.py``
(in the form of ``c["<variable-name>"]`` where ``c`` is defined in ``for c in tasks``).






The task's Python file
======================

Create ``zppy/<task-name>.py``. The basic outline of the file should be similar to the
below example, adapted from ``zppy/e3sm_diags.py``.

    .. code::

        import os
        import pprint

        import jinja2

        from zppy.utils import checkStatus, getTasks, getYears, submitScript


        # -----------------------------------------------------------------------------
        def <task-name>(config, scriptDir):

            # Initialize jinja2 template engine
            templateLoader = jinja2.FileSystemLoader(
                searchpath=config["default"]["templateDir"]
            )
            templateEnv = jinja2.Environment(loader=templateLoader)
            template = templateEnv.get_template("<task-name>.bash")

            # --- List of <task-name> tasks ---
            tasks = getTasks(config, "<task-name>")
            if len(tasks) == 0:
                return

            # --- Generate and submit <task-name> scripts ---
            for c in tasks:

                # Loop over year sets
                year_sets = getYears(c["years"])
                for s in year_sets:
                    c["year1"] = s[0]
                    c["year2"] = s[1]
                    c["scriptDir"] = scriptDir
                    if c["subsection"]:
                        sub = c["subsection"]
                    else:
                        sub = c["grid"]
                    prefix = "<task-name>_%s_%s_%04d-%04d" % (
                        sub,
                        c["tag"],
                        c["year1"],
                        c["year2"],
                    )
                    print(prefix)
                    c["prefix"] = prefix
                    scriptFile = os.path.join(scriptDir, "%s.bash" % (prefix))
                    statusFile = os.path.join(scriptDir, "%s.status" % (prefix))
                    settingsFile = os.path.join(scriptDir, "%s.settings" % (prefix))
                    skip = checkStatus(statusFile)
                    if skip:
                        continue

                    # Create script
                    with open(scriptFile, "w") as f:
                        f.write(template.render(**c))

                    # List of dependencies
                    dependencies = []

                    with open(settingsFile, "w") as sf:
                        p = pprint.PrettyPrinter(indent=2, stream=sf)
                        p.pprint(c)
                        p.pprint(s)

                    if not c["dry_run"]:
                        # Submit job
                        jobid = submitScript(
                            scriptFile, dependFiles=dependencies, export="NONE"
                        )

                        if jobid != -1:
                            # Update status file
                            with open(statusFile, "w") as f:
                                f.write("WAITING %d\n" % (jobid))


The main file
=============

Add the task to ``zppy/__main__.py``:

    .. code::

        from <task_name> import <task_name>

    .. code::

        # <task-name> tasks
        <task-name>(config, scriptDir)

Update defaults
===============
Add default values for parameters in ``zppy/templates/default.ini``.

    .. code::

        [<task-name>]
        ...

            [[__many__]] # Only if the task supports sub-tasks
            ... # List the same parameters but with `default=None`

Update the tutorial
===================
Add example values for parameters in ``docs/source/post.mysimulation.cfg``.

    .. code::

        [ <task-name> ]
        ... # Specify parameters that would likely apply to all sub-tasks

            [[ <subtask-name> ]] # Only if the task supports sub-tasks
            ... # Specify parameters that make more sense defined in the sub-tasks

Explain new parameters
======================
In ``docs/source/parameters.rst``

Copy defaults from ``zppy/templates/default.ini`` and add a comment line
above each explaining the parameter.


Update the tests
================
In ``tests/integration/test_*.cfg``

Copy example values from ``docs/source/post.mysimulation.cfg``.
The expected files will have to be updated as well.
