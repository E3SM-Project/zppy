.. _component-atmosphere:

Atmosphere — EAM and EAMxx
===========================

E3SM has two atmosphere models:

- **EAM** (E3SM Atmosphere Model) — the standard atmosphere model used in
  most E3SM configurations.
- **EAMxx** (E3SM Atmosphere Model, next generation) — uses a different
  vertical grid (L128) and a different file format.

Relevant zppy tasks
-------------------

The following ``zppy`` tasks are commonly used for atmosphere post-processing:

- :doc:`../tasks/climo` — generate atmosphere climatology files
- :doc:`../tasks/ts` — generate atmosphere time-series files
- :doc:`../tasks/e3sm_to_cmip` — convert to CMIP6 format
- :doc:`../tasks/e3sm_diags` — atmospheric diagnostics (most sets)
- :doc:`../tasks/tc_analysis` — tropical cyclone analysis
- :doc:`../tasks/global_time_series` — global atmospheric time series plots
- :doc:`../tasks/pcmdi_diags` — atmospheric performance metrics

EAM configuration
-----------------

For EAM (standard resolution), typical history streams are:

- ``eam.h0`` — monthly averages (most common for diagnostics)
- ``eam.h1`` — daily averages
- ``eam.h2`` — high-frequency output (used for TC analysis)

Typical ``[climo]`` and ``[ts]`` subsection configuration for EAM:

.. code-block:: cfg

   [climo]
   active = True

     [[atm_monthly_180x360_aave]]
     input_files = eam.h0
     input_subdir = archive/atm/hist
     mapping_file = /path/to/map_ne30pg2_to_cmip6_180x360_aave.20200201.nc
     grid = 180x360_aave
     years = 1:100:20

   [ts]
   active = True

     [[atm_monthly_180x360_aave]]
     input_files = eam.h0
     input_subdir = archive/atm/hist
     mapping_file = /path/to/map_ne30pg2_to_cmip6_180x360_aave.20200201.nc
     grid = 180x360_aave
     years = 1:100:10

     [[atm_daily_180x360_aave]]
     input_files = eam.h1
     input_subdir = archive/atm/hist
     mapping_file = /path/to/map_ne30pg2_to_cmip6_180x360_aave.20200201.nc
     grid = 180x360_aave
     frequency = daily
     years = 1:100:10

     [[atm_monthly_glb]]
     input_files = eam.h0
     input_subdir = archive/atm/hist
     years = 1:100:10

EAMxx configuration
-------------------

EAMxx uses a 128-level vertical grid (L128) and stores output differently
from EAM. Key differences when configuring ``zppy`` for EAMxx:

- Set ``input_component = eamxx`` in ``[climo]`` and ``[ts]`` sections.
- The ``vrt_in_file`` parameter may be needed for vertical remapping.
  When ``input_component = eamxx``, ``zppy`` defaults to a
  ``vert_L128.nc`` file under ``diagnostics_base_path``.
- Vertical remapping (``vrt_remap_vars``) is often needed to produce
  pressure-level data for diagnostics.

Example EAMxx configuration:

.. code-block:: cfg

   [ts]
   active = True

     [[eamxx_monthly_180x360_aave]]
     input_component = eamxx
     input_files = eamxx.h0
     input_subdir = archive/atm/hist
     mapping_file = /path/to/map_ne30pg2_to_cmip6_180x360_aave.nc
     grid = 180x360_aave
     vrt_remap_vars = T,Q,U,V,Z3,OMEGA
     years = 1:50:10

Mapping files
-------------

Mapping files remap EAM/EAMxx output from the native spectral-element
grid (e.g., ``ne30pg2``) to a regular latitude-longitude grid
(e.g., ``180x360_aave``). These files are typically pre-computed and
available on supported machines under the ``diagnostics_base_path``.

Machine-specific mapping file locations:

- **Chrysalis/Anvil (LCRC)**: typically under
  ``/home/ac.zender/data/maps/``
- **Perlmutter (NERSC)**: typically under
  ``/global/homes/z/zender/data/maps/``
- **Compy**: typically under ``/compyfs/zender/maps/``

Diurnal cycle
-------------

For diurnal cycle diagnostics in ``e3sm_diags``, high-frequency
(8× daily) climatologies are needed. Configure an additional ``[climo]``
subsection:

.. code-block:: cfg

   [climo]
     [[atm_monthly_diurnal_8xdaily_180x360_aave]]
     input_files = eam.h3
     input_subdir = archive/atm/hist
     frequency = diurnal_8xdaily
     mapping_file = /path/to/map_ne30pg2_to_cmip6_180x360_aave.nc
     grid = 180x360_aave
     years = 1:100:20

   [e3sm_diags]
     [[atm_monthly_180x360_aave]]
     sets = diurnal_cycle,...
     climo_diurnal_subsection = atm_monthly_diurnal_8xdaily_180x360_aave
     climo_diurnal_frequency = diurnal_8xdaily
     dc_obs_climo = /path/to/obs/climatology
