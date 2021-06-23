.. _getting-started:
  
***************
Getting started
***************

Activate e3sm_unified environment
=================================

If you have an account on one of the E3SM supported machines (NERSC, Compy, Acme1,
LCRC, Cooley, Rhea), you can access ``zppy`` by activating ``e3sm_unified``, which is
a conda environment that pulls together Python and other E3SM tools such as
``e3sm_diags`` and ``zstash``.

The paths to ``e3sm_unified`` activation scripts are machine dependent:

**Compy**
    ::

     source /share/apps/E3SM/conda_envs/load_latest_e3sm_unified.sh


**NERSC**
    ::

     source /global/cfs/cdirs/e3sm/software/anaconda_envs/load_latest_e3sm_unified.sh


**LCRC**
    ::

     source /lcrc/soft/climate/e3sm-unified/load_latest_e3sm_unified.sh


**Cooley**
    ::

     source /lus/theta-fs0/projects/ccsm/acme/tools/e3sm-unified/load_latest_e3sm_unified.sh


**acme1**
    ::

     source /usr/local/e3sm_unified/envs/load_latest_e3sm_unified.sh


**Rhea**
    ::

     source /ccs/proj/cli900/sw/rhea/e3sm-unified/load_latest_e3sm_unified.sh


Change ``.sh`` to ``.csh`` for ``csh`` shells.

Note that ``e3sm_unified``'s development cycle is not in phase with ``zppy``.
Therefore the version of ``zppy`` included may not be the latest.
To install the latest stable release, refer to the following:

.. _conda_environment:

Installation in a Conda Environment
===================================

If the E3SM Unified environment doesn't serve your needs, you can alternatively
install the latest version in your own custom conda environment.

First, activate conda or install it if it's not available. Details vary amongst machines.

Compy
-----
    ::

     module load anaconda3/2019.03
     source /share/apps/anaconda3/2019.03/etc/profile.d/conda.sh


NERSC
-----
    ::

     module load python/3.7-anaconda-2019.10
     source /global/common/cori_cle7/software/python/3.7-anaconda-2019.10/etc/profile.d/conda.sh


.. _conda_environment_others:

Others/Local
------------

If the system doesn't come with conda pre-installed, follow these instructions:

1. Download Conda

    Linux
        ::

            wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh

    MacOS (note that ``zppy`` is not supported on MacOS, but it may be useful to contribute to the documentation on MacOS)
        ::

            wget https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh

2. Install Conda

    Linux
        ::

            bash ./Miniconda3-latest-Linux-x86_64.sh


    MacOS
        ::

            bash ./Miniconda3-latest-MacOSX-x86_64.sh

    - ``Do you wish the installer to initialize Miniconda3 by running conda init? [yes|no] yes``

3. If you are working on a machine/network that intercepts SSL communications (such as
acme1), you will get an SSL error unless you disable the SSL verification:

    ::

        conda config --set ssl_verify false
        binstar config --set ssl_verify False

4. Set the following:

    ::

        conda config --add channels conda-forge
        conda config --set channel_priority strict

5. Once conda is properly working, you can install the **(a) Latest Stable Release** or
create a **(b) Development Environment**.

(a) Latest Stable Release
=========================

Installation using conda
------------------------

First, make sure that you're using ``bash``. ::

   $ bash

You must have Anaconda installed as well.
See :ref:`"Installation in a Conda Environment" <conda_environment>` section above for
installing conda.
Create a new Anaconda environment with ``zppy`` installed and activate it: ::

   $ conda create -n zppy_env -c e3sm -c conda-forge zppy
   $ source activate zppy_env

Or you can install ``zppy`` in an existing environment. ::

   $ conda install zppy -c e3sm -c conda-forge

Updating
--------

If you **installed via Anaconda** (e.g., not through the unified environment),
you can update ``zppy`` by doing the following:  ::

    conda update zppy -c e3sm -c conda-forge

.. _dev-env:

(b) Development Environment
===========================

Unlike the latest stable release (i.e., the user environment), the development
environment does not include ``zppy``.
Instead, the developer will ``python -m pip install .`` to build ``zppy`` with changes
(see step 6 below).

..
    # TODO: Add the QA tools
    #Furthermore, the dev environment includes quality assurance (QA) tools such as code formatters, linters, and ``pre-commit``.
    #**NOTE**: These QA tools are enforced using ``pre-commit`` checks in the continuous integration/continuous delivery (CI/CD) build, so you must use the dev environment for all contributions.

1. Follow :ref:`"Others/Local" <conda_environment_others>` section for installing conda.

2. Clone your fork and keep it in sync with the main repo's ``main``

    ::

        # Go to https://github.com/E3SM-Project/zppy
        # Click "Fork" in the upper right hand corner. This will fork the main repo.
        # Click the green "Code" button
        # Choose the HTTPS or SSH option.
        # (To use the SSH option, you need to have a SSH connection to GitHub set up).
        # Click the clipboard icon to copy the path.
        # On your command line:
        git clone <path>
        git remote -v
        # You should see your fork listed as `origin`


   or if you already have a clone of your fork, rebase your fork on the main repo's ``main`` to keep it in sync:

    ::

        # Add the main repo as a remote.
        # You can call it anything but "upstream" is recommended.
        # We'll use `<upstream-origin>` here.
        git remote add <upstream-origin> <path from the green "Code" button mentioned above>

        # Fetch all the branches of that remote into remote-tracking branches
        git fetch <upstream-origin>

        # Make sure that you're on your ``main`` branch:
        git checkout main

        # Rewrite your `main` branch so that any of your commits that
        # aren't already in <upstream-origin>/main are replayed on top of that branch:
        git rebase <upstream-origin>/main

        # Push your main branch to your GitHub fork:
        # Note that <fork-origin> should be `origin` if you cloned your fork as above.
        git push -f <fork-origin> main


   Checkout a new branch from ``main``:

    ::

        git checkout -b <branch-name> <remote-origin>/main

3. Remove any cached conda packages. This will ensure that you always get the latest packages.

    ::

        conda clean --all

4. Enter the fork's clone.

    ::

        cd zppy

5. Use conda to create a new dev environment.
(``zppy`` **is not included in this environment**).

    - Tip: Add the flag ``-n <name_of_env>`` to customize the name of the environment

    ::

        conda env create -f conda/dev.yml
        conda activate zppy_dev

..
    6. Install ``pre-commit``.

        ::

            pre-commit install

6. Make the desired changes to ``zppy``, then rebuild and install with:

    ::

        pip install .

..
    8. Commit changes and make sure ``pre-commit`` checks pass

8. Commit changes

    ::

        git commit -m "commit-message"

..
        .. figure:: _static/pre-commit-passing.png
           :alt: pre-commit Output

           ``pre-commit`` Output


Configuration file
==================

The configuration files consists of sections (``[...]``) and subsections (``[[...]]``). There is
a default section at the top (``[default]``) to define some common settings, followed
by a separate section for each available task. Within each task section, you can optionally
include an arbitrary number of subsections for multiple renditions of a given
task. The name of the subsections are arbitrary. They are used to name the batch
jobs and resolve dependencies.

Please note that the configuration file follows an inheritance model: ``[[ subsections ]]`` inherit settings
from their parent ``[section]``, which itself inherits settings from the ``[default]`` section.
Settings can be defined at arbitrary levels, with the lower level definition taking precedence:
``[[ subsection ]]`` settings can overwrite ``[section]`` settings which can overwrite ``[default]`` settings.
Many settings also take on sensible default values if they are not set.

Running
=======

To start the post-processing: ::

  zppy -c <configuration file>

``zppy`` will parse the configuration file and then generate and submit all batch jobs.
``zppy`` can be invoked safely multiple times -- it will simply check the status of previously
submitted tasks, only submitting new or previously failed tasks.
