.. _getting-started:

***************
Getting started
***************

Activate e3sm_unified environment
=================================

If you have an account on one of the E3SM supported machines, you can access ``zppy`` by activating ``e3sm_unified``, which is
a conda environment that pulls together Python and other E3SM tools such as
``e3sm_diags`` and ``zstash``.

The paths to ``e3sm_unified`` activation scripts are machine dependent. As of E3SM Unified 1.13.0, the supported machines and their corresponding activation scripts are:

**Andes**
    ::

     source /ccs/proj/cli115/software/e3sm-unified/load_latest_e3sm_unified_andes.sh

**Aurora**
    ::

     source /lus/flare/projects/E3SMinput/soft/e3sm-unified/load_latest_e3sm_unified_aurora.sh

**Chrysalis**
    ::

     source /lcrc/soft/climate/e3sm-unified/load_latest_e3sm_unified_chrysalis.sh

**Compy**
    ::

     source /share/apps/E3SM/conda_envs/load_latest_e3sm_unified_compy.sh

**Dane**
    ::

     source /usr/workspace/e3sm/apps/e3sm-unified/load_latest_e3sm_unified_dane.sh

**Frontier**
    ::

     source /ccs/proj/cli115/software/e3sm-unified/load_latest_e3sm_unified_frontier.sh

**Perlmutter (login or CPU nodes)**
    ::

     source /global/common/software/e3sm/anaconda_envs/load_latest_e3sm_unified_pm-cpu.sh

**ALCF Polaris**
    ::

     source /lus/grand/projects/E3SMinput/soft/e3sm-unified/load_latest_e3sm_unified_polaris.sh


Change ``.sh`` to ``.csh`` for ``csh`` shells.

E3SM Unified and zppy versions
==============================

``zppy`` development is largely synced with ``e3sm_unified``. The last several releases have been:

* E3SM Unified 1.13.0: ``zppy 3.2.0``, ``zppy-interfaces 0.2.1``
* E3SM Unified 1.12.0: ``zppy 3.1.0``, ``zppy-interfaces 0.2.0``
* E3SM Unified 1.11.1: ``zppy 3.1.0``, ``zppy-interfaces 0.1.2``
* E3SM Unified 1.11.0: ``zppy 3.0.0``, ``zppy-interfaces 0.1.1`` (new auxillary package)
* E3SM Unified 1.10.0: ``zppy 2.5.0``

To use ``zppy`` features/fixes not yet in a production release, you can use a development environment.

Note that ``e3sm_unified``'s development cycle is not in phase with ``zppy``.
Therefore the version of ``zppy`` included may not be the latest.
To install the latest stable release, refer to the following:

Setting up a development environment
====================================

.. code-block:: bash

        # Get the code ########################################################################

        # Set up your fork:
        # Go to https://github.com/E3SM-Project/zppy
        # Click the green "Code" button
        # Choose the SSH option and paste it here:
        git clone git@github.com:E3SM-Project/zppy.git
        cd zppy_dev
        git remote -v # You should see the main repo listed as `origin`

        # A couple optional steps:
        git remote add upstream git@github.com:E3SM-Project/zppy.git # Use the name "upstream" instead of origin
        git remote add your-fork-name git@github.com:your-fork-name/zppy.git # Use your fork, if you have one

        # To use the latest code:
        git checkout upstream main
        # To use code from a specific branch:
        git checkout upstream that-branch-name

        # Set up the environment ##############################################################
        # First, make sure you have conda activated. Then:
        rm -rf build # Sometimes an existing `build` directory can cause problems.
        conda clean --all --y # This makes sure conda will pick up the latest information.
        conda env create -f conda/dev.yml -n env-name
        conda activate env-name
        pre-commit run --all-files # This is only necessary if you've made changes
        python -m pip install . # Install the code into your development environment (env-name)

Note: if you'd like to contribute to ``zppy`` rather than just using the latest code, please refer to the Developer Guide instead.


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
For the most part, ``zppy`` can be invoked safely multiple times -- it will simply check the status of previously
submitted tasks, only submitting new or previously failed tasks.

.. warning::
    Some tasks cannot be safely rerun. Notably, ``mpas_analysis`` has historically needed to be rerun from scratch if a job failed. This is documented in https://github.com/E3SM-Project/zppy/issues/764. 
