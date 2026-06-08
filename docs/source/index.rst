.. zppy documentation master file

.. _index-label:

******************
Zppy documentation
******************

What is zppy?
=============

``zppy`` (pronounced as "zippy", or in IPA: /ˈzɪpi/) is a **workflow manager** for post-processing
E3SM simulations, written in Python. The goal of ``zppy`` is to speed up
post-processing by automating commonly performed tasks.

``zppy`` is built around a set of tasks that perform specific actions,
such as generating (regridded) **time series** or **climatology** files
using NCO's ``ncclimo``, or generating analysis figures with **E3SM Diags**
or **MPAS-Analysis**. ``zppy`` provides a framework to simplify the use of
these tools, especially for long simulations.

``zppy`` is controlled entirely from a single user-provided configuration file
(e.g., ``mysimulation.cfg``). This configuration file specifies input and
output directories, as well as the list of tasks to run. Each task operates
over a specified number of years—for
example, generating atmosphere climatology files every 20 and 50 years.

``zppy`` parses the configuration file and generates batch jobs that are
submitted for execution by SLURM. Dependencies between tasks are handled and
passed to SLURM. Internally, each batch job is created by instantiating
Jinja2 template scripts (usually
written in bash, but other languages are supported as well).

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   user_guide/index

.. toctree::
   :maxdepth: 2
   :caption: Developer Guide

   dev_guide/index
