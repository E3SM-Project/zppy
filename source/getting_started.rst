.. _getting-started:
  
***************
Getting started
***************

Installation
============

Install zppy by cloning its repository: ::

    cd E3SM/code
    git clone https://github.com/E3SM-Project/zppy.git

All the necessary dependencies for running zppy are available
in the E3SM Unified conda environment. Activate it using: ::


    # for bash shell
    source <activate_path>/load_latest_e3sm_unified.sh
    # or for csh shell
    source <activate_path>/load_latest_e3sm_unified.csh

where <activate_path> is machine dependent:

===================== =============================================
Machine                <activate_path>
===================== =============================================
Anvil/chrysalis (ANL) /lcrc/soft/climate/e3sm-unified
Compy (PNNL)          /share/apps/E3SM/conda_envs/
Cori (NERSC)          /global/cfs/cdirs/e3sm/software/anaconda_envs
===================== =============================================


Configuration file
==================

As a first example, let's say we want to post-process 100 years
of an existing simulation. In particular, we'd like to generate
the following:

* Regridded atmosphere climatologies every 20 and 50 years
* Regridded atmosphere monthly time series files in 10 year chunks
* E3SM Diags every 20 and 50 years
* MPAS-Analysis

First, create a configuration file in your favorite editor: ::

  cd E3SM/script
  gvim post.mysimulation.cfg

Copy and paste the following:

.. literalinclude:: post.mysimulation.cfg
   :language: cfg
   :linenos:

The configuration files consists of sections ([...]) and subsections ([[...]]). There is
a default section at the top ([default]) to define some common settings, followed
by a separate section for each available tasks. Within each task section, you can optionally
include an arbitrary number of subsections for multiple renditions of a given
tasks. The name of the subsections are arbitrary. They are used to name the batch
jobs and resolve dependencies.

Please note that the configuration file follows an inheritance model: [[ subsections ]] inherit settings
from their parent [section], which itself inherits settings from the [default] section.
Settings can be defined at arbitrary levels, with the lower level definition taking precedence:
[[ subsection ]] settings can overwrite [section] settings which can overwrite [default] settings.
Many settings also take on sensible default values if they are or set.

A detailed description of all available settings is provided in a next section
of the documentation. Here, we only
provide a brief overview:

Running
=======

To start the post-processing: ::

  python ~/E3SM/code/zppy/post.py -c post.mysimulation.cfg

Zppy will parse the configuration file, generate and submit all batch jobs.
Zppy can be invoked safely multiple times. Zppy will check status of previously
submitted tasks and will only submit new or previously incomplete tasks.

