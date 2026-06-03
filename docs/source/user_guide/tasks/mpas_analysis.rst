.. _task-mpas-analysis:

mpas_analysis — Ocean and Sea-Ice Analysis
==========================================

The ``mpas_analysis`` task runs `MPAS-Analysis
<https://mpas-dev.github.io/MPAS-Analysis/>`_ to produce ocean and sea-ice
diagnostics. It supports both model-vs-observations (``mvo``) and
model-vs-model (``mvm``) comparison modes. The comparison type is inferred
automatically: if ``reference_data_path`` is set, the run is treated as MVM;
otherwise it is treated as MVO.

.. note::
   ``environment_commands`` should be the same for all related
   ``[mpas_analysis]`` runs. Mixing environments across year ranges can cause
   MPAS-Analysis to fail.

Parameters
----------

.. list-table::
   :header-rows: 1
   :widths: 28 10 18 44

   * - Parameter
     - Required
     - Default
     - Description
   * - ``active``
     - No
     - ``False``
     - Set to ``True`` to enable this task.
   * - ``generate``
     - No
     - ``"all,no_landIceCavities,..."``
     - List of MPAS-Analysis analyses to generate.
   * - ``ts_years``
     - No
     - ``[""]``
     - Year ranges for time-series sub-runs.
   * - ``climo_years``
     - No
     - ``[""]``
     - Year ranges for climatology sub-runs.
   * - ``enso_years``
     - No
     - ``[""]``
     - Year ranges for ENSO sub-runs.
   * - ``reference_data_path``
     - No
     - ``""``
     - For MVM runs: path to a prior zppy output directory (the one
       containing ``post/``) to use as the reference run. Setting this
       triggers MVM mode.
   * - ``test_data_path``
     - No
     - ``""``
     - For MVM runs: path to the test run's prior zppy output directory (if
       different from the current run).
   * - ``reference_comparison_type``
     - No
     - ``"auto"``
     - Comparison type for the referenced prior run: ``"auto"``, ``"mvo"``,
       or ``"mvm"``.
   * - ``test_comparison_type``
     - No
     - ``"auto"``
     - Comparison type for the test run's referenced prior run.
   * - ``reference_case``
     - No*
     - ``""``
     - Case name of the reference run. Required when
       ``reference_data_path`` points to a non-subsection path.
   * - ``ref_ts_years``
     - No
     - ``[""]``
     - Year ranges for reference time-series sub-runs. Defaults to
       ``ts_years`` if empty.
   * - ``ref_climo_years``
     - No
     - ``[""]``
     - Year ranges for reference climatology sub-runs.
   * - ``ref_enso_years``
     - No
     - ``[""]``
     - Year ranges for reference ENSO sub-runs.
   * - ``anomalyRefYear``
     - No
     - ``1``
     - Reference year for anomaly calculations.
   * - ``cache``
     - No
     - ``True``
     - Whether to cache MPAS-Analysis intermediate results.
   * - ``mapMpiTasks``
     - No
     - ``6``
     - Number of MPI tasks for mapping.
   * - ``mpaso_nml``
     - No
     - ``"mpaso_in"``
     - Name of the MPAS-Ocean namelist file.
   * - ``mpassi_nml``
     - No
     - ``"mpassi_in"``
     - Name of the MPAS sea-ice namelist file.
   * - ``ncclimoThreads``
     - No
     - ``12``
     - Number of threads for ``ncclimo`` in MPAS-Analysis.
   * - ``ncclimoParallelMode``
     - No
     - ``"bck"``
     - Parallel mode for ``ncclimo`` in MPAS-Analysis.
   * - ``parallelTaskCount``
     - No
     - ``12``
     - Number of parallel analysis tasks in MPAS-Analysis.
   * - ``PostMOC``
     - No
     - ``False``
     - Whether to post-process MOC data.
   * - ``purge``
     - No
     - ``False``
     - Whether to purge previous MPAS-Analysis output before running.
   * - ``shortTermArchive``
     - No
     - ``True``
     - Whether the input uses the short-term archive directory structure.
   * - ``stream_ice``
     - No
     - ``"streams.seaice"``
     - Name of the MPAS sea-ice streams file.
   * - ``stream_ocn``
     - No
     - ``"streams.ocean"``
     - Name of the MPAS ocean streams file.
   * - ``walltime``
     - No
     - ``"06:00:00"``
     - Maximum wall time. Overrides the ``[default]`` value (``02:00:00``).

Year range behavior for MVM runs
---------------------------------

For model-vs-model comparisons, ``zppy`` supports separate year ranges for
the test and reference runs:

- ``ts_years``, ``climo_years``, ``enso_years``: define the **test** run
  year ranges.
- ``ref_ts_years``, ``ref_climo_years``, ``ref_enso_years``: optionally
  override the **reference** run year ranges (defaults to test year ranges
  if not set).
- If ``reference_data_path`` points to a prior ``[[subsection]]`` in the
  same cfg, the reference year ranges default to that subsection's values.
- If a single reference year range is provided and multiple test ranges are
  requested, the single reference range is used for each test range.
