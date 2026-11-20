.. _component-land:

Land — ELM
===========

**ELM** (E3SM Land Model) is E3SM's land component, based on CLM5. It
simulates vegetation, soil, hydrology, and carbon/nitrogen cycles.

Relevant zppy tasks
-------------------

- :doc:`../tasks/ts` — generate land time-series files
- :doc:`../tasks/e3sm_to_cmip` — convert land output to CMIP6 format
- :doc:`../tasks/e3sm_diags` — land diagnostics (e.g., ``lat_lon`` set with land variables)
- :doc:`../tasks/ilamb` — land benchmarking against observational datasets
- :doc:`../tasks/livvkit` — ice sheet validation (for cryosphere configurations)
- :doc:`../tasks/global_time_series` — land global time series (via ``plots_lnd``)

ELM time-series configuration
------------------------------

ELM output is typically in monthly ``elm.h0`` files. A typical ``[ts]``
configuration for land:

.. code-block:: cfg

   [ts]
   active = True

     [[land_monthly]]
     input_files = elm.h0
     input_subdir = archive/lnd/hist
     input_component = elm
     mapping_file = /path/to/map_r05_to_cmip6_180x360_aave.nc
     grid = 180x360_aave
     years = 1:100:10

The ``input_component = elm`` setting tells ``zppy`` that this is ELM
output. This is required for correct processing by ``e3sm_to_cmip`` and
``ilamb``.

CMIP conversion for ILAMB
--------------------------

ILAMB requires CMIP6-format data. The ``e3sm_to_cmip`` task must be run
first. Typical configuration:

.. code-block:: cfg

   [e3sm_to_cmip]
   active = True

     [[land_monthly]]
     input_component = elm
     ts_land_subsection = land_monthly

   [ilamb]
   active = True
   land_only = False
   e3sm_to_cmip_land_subsection = land_monthly

The ``ilamb`` task will depend on both the land and atmosphere
``e3sm_to_cmip`` subtasks (unless ``land_only = True``). With
``infer_section_parameters = True`` (default), subsection names for land
tasks default to ``land_monthly`` and atmosphere tasks default to
``atm_monthly_180x360_aave``.

Ice sheet validation with LIVVkit
----------------------------------

For cryosphere-enabled simulations, the ``livvkit`` task validates the ice
sheet component against reanalysis datasets. LIVVkit requires grid-native
and regridded climatology files from the ``[climo]`` task:

.. code-block:: cfg

   [climo]
     [[land_monthly_climo_native]]
     input_files = elm.h0
     input_subdir = archive/lnd/hist
     input_component = elm
     years = 1:100:20

     [[land_monthly_climo_era5]]
     input_files = elm.h0
     input_subdir = archive/lnd/hist
     input_component = elm
     mapping_file = /path/to/map_r05_to_era5.nc
     grid = era5
     years = 1:100:20

   [livvkit]
   active = True
   climo_subsections = land_monthly_climo_native, land_monthly_climo_era5
   icesheets = gis,ais
   sets = cmb,smb,energy_era5

Notes for ELM developers
--------------------------

- The ``input_component = elm`` parameter is used internally by ``zppy``
  to set the correct processing type (``prc_typ``) for ``ncclimo``.
- ELM variables to process can be set via the ``vars`` parameter. Leaving
  ``vars = ""`` processes all variables, which can be slow. Consider
  specifying only the variables needed for your diagnostics.
- The land component mapping file maps from ELM's finite-volume grid (e.g.,
  ``r05``, ``ne30pg2``) to a regular lat-lon grid.
