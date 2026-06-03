.. _archive:

*******
Archive
*******

This page collects documentation that is obsolete or refers to older
versions of ``zppy`` or the E3SM Unified environment. It is retained for
historical reference.

.. toctree::
   :maxdepth: 1

   initial_docs

Old testing tutorial (E3SM Unified 1.5.0)
==========================================

The :doc:`tutorial_testing_e3sm_unified` page contains a tutorial written
for testing against E3SM Unified v1.5.0. For current testing directions,
see :ref:`release-testing`.

Old documentation setup (initial Sphinx configuration)
=======================================================

The section "Initial setup (obsolete/for reference only)" in
:doc:`contributing` describes the original one-time Sphinx configuration
steps. Those steps do not need to be repeated.

Deprecated parameters
=====================

The following ``zppy`` parameters no longer perform any function:

.. code-block:: text

   e3sm_to_cmip_environment_commands
   ts_fmt
   scratch
   atmosphere_only
   plot_names
   ncclimo_cmd (still accepted but ignored)
   nrows (in global_time_series; specifying has no effect)
   ncols (in global_time_series; specifying has no effect)
   vars_exclude (deprecated; use vars = "" and filter in post-processing)
