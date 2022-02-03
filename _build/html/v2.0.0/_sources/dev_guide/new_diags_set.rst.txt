*********************************************
Adding a new set to the E3SM Diagnostics task
*********************************************

This guide gives a general list of things to consider when adding a new
E3SM Diagnostics set. The exact code changes required will differ amongst sets.

Example pull requests
=====================

Code snippets are from the following two pull requests:

- `Diurnal Cycle <https://github.com/E3SM-Project/zppy/pull/34>`_
- `Streamflow <https://github.com/E3SM-Project/zppy/pull/126/files>`_

.. warning ::

    Code blocks in this guide are taken from these pull requests.
    They may be outdated because of more recent changes.

Handle dependencies
===================

Sometimes a new set may require first editing the ``climo`` or ``ts`` functionality.

Add dependencies in the Python file
-----------------------------------

In ``zppy/e3sm_diags.py``

Diurnal Cycle: ``e3sm_diags`` had to be set up to depend on a new climatology subtask:

    .. code::

        if "diurnal_cycle" in c['sets']:
            dependencies.append(os.path.join(scriptDir, 'climo_%s_%04d-%04d.status' % (
                c['climo_diurnal_subsection'], c['year1'],c['year2'])))

Streamflow: ``e3sm_diags`` had to be set up to depend on a new time series subtask:

    .. code::

        if "streamflow" in c["sets"]:
            dependencies.append(
                os.path.join(
                    scriptDir,
                    "ts_rof_monthly_%04d-%04d-%04d.status"
                    % (start_yr, end_yr, c["ts_num_years"]),
                )
            )

Update the ``climo`` or ``ts`` bash files
-----------------------------------------

In ``zppy/templates/climo.bash`` or ``zppy/templates/ts.bash``

Diurnal Cycle: ``climo.bash`` needed some changes:

    .. code::

        {% elif frequency.startswith('monthly_diurnal') %}
        {
          dest={{ output }}/post/{{ component }}/{{ grid }}/clim_{{ subsection }}/{{ '%dyr' % (yr_end-yr_start+1) }}
          mkdir -p ${dest}
          mv output/*.nc ${dest}
        }
        {%- endif %}

Add any required pre-processing steps to the bash file
------------------------------------------------------

In ``zppy/templates/e3sm_diags.bash``

Diurnal Cycle:

    .. code::

        {%- if "diurnal_cycle" in sets %}
        # Create local links to input diurnal cycle climo files
        climoDir={{ output }}/post/atm/{{ grid }}/clim_{{ climo_diurnal_subsection }}/{{ '%dyr' % (year2-year1+1) }}
        climoDirCopy=climo_{{ climo_diurnal_subsection }}
        mkdir -p ${climoDirCopy}
        cd ${climoDirCopy}
        cp -s ${climoDir}/${case}.eam.h4_*_${Y1}??_${Y2}??_climo.nc .
        cd ..
        {%- endif %}

Streamflow:

    .. code::

        {%- if "streamflow" in sets %}
        rofDir="{{ output }}/post/rof/native/ts/monthly/{{ ts_num_years }}yr"
        mkdir -p rof_links
        cd rof_links
        v="RIVER_DISCHARGE_OVER_LAND_LIQ"
        xml_name=${v}_${Y1}01_${Y2}12.xml
        cdscan -x ${xml_name} ${rofDir}/${v}_*.nc
        cd ..
        {%- endif %}

Update the tutorial
-------------------

In ``docs/source/post.mysimulation.cfg``

Streamflow: Since the ``rof_monthly`` subtask of ``ts`` is required, it was added
to the tutorial documentation:

    .. code::

        [[ rof_monthly ]]
        input_subdir = "archive/rof/hist"
        input_files = "mosart.h0"
        frequency = "monthly"
        mapping_file = ""
        vars = "RIVER_DISCHARGE_OVER_LAND_LIQ"
        extra_vars = 'areatotal2'

Update the tests
----------------

In ``tests/integration/test_*.cfg``.

Streamflow: the ``rof_monthly`` subtask of ``ts`` had to be included:

    .. code::

          [[ rof_monthly ]]
          input_subdir = "archive/rof/hist"
          input_files = "mosart.h0"
          frequency = "monthly"
          mapping_file = ""
          vars = "RIVER_DISCHARGE_OVER_LAND_LIQ"
          extra_vars = 'areatotal2'

The expected files will have to be updated as well.
	  
Add the new set
===============

Add new set to defaults
-----------------------

In ``zppy/templates/default.ini``

Diurnal Cycle: ``diurnal_cycle`` was added:

    .. code::

        sets = string_list(default=list("lat_lon","zonal_mean_xy","zonal_mean_2d","polar","cosp_histogram","meridional_mean_2d","enso_diags","qbo","area_mean_time_series","diurnal_cycle"))

Streamflow: ``streamflow`` was added:

    .. code::

        sets = string_list(default=list("lat_lon","zonal_mean_xy","zonal_mean_2d","polar","cosp_histogram","meridional_mean_2d","enso_diags","qbo","diurnal_cycle","annual_cycle_zonal_mean","streamflow"))

Add the Python parameter import/setup to the bash file
------------------------------------------------------

In ``zppy/templates/e3sm_diags.bash``

Diurnal Cycle:

    .. code::

        {%- if "diurnal_cycle" in sets %}
        from acme_diags.parameter.diurnal_cycle_parameter import DiurnalCycleParameter
        {%- endif %}

    .. code::

        {%- if "diurnal_cycle" in sets %}
        dc_param = DiurnalCycleParameter()
        dc_param.reference_data_path = '{{ dc_obs_climo }}'
        dc_param.test_data_path = 'climo_{{ climo_diurnal_subsection }}'
        dc_param.test_name = short_name
        dc_param.short_test_name = short_name
        # Plotting diurnal cycle amplitude on different scales. Default is True
        dc_param.normalize_test_amp = False
        params.append(dc_param)
        {%- endif %}

Streamflow:

    .. code::

        {%- if "streamflow" in sets %}
        from e3sm_diags.parameter.streamflow_parameter import StreamflowParameter
        {%- endif %}

    .. code::

        {%- if "streamflow" in sets %}
        streamflow_param = StreamflowParameter()
        streamflow_param.reference_data_path = '{{ streamflow_obs_ts }}'
        streamflow_param.test_data_path = 'rof_links'
        streamflow_param.test_name = short_name
        streamflow_param.test_start_yr = start_yr
        streamflow_param.test_end_yr = end_yr # Streamflow gauge station data range from year 1986 to 1995
        streamflow_param.ref_start_yr = "1986"
        streamflow_param.ref_end_yr = "1995"
        params.append(streamflow_param)
        {%- endif %}

Explain new parameters
----------------------

In ``docs/source/parameters.rst``

Streamflow:

    .. code::

            # Path to observation data for streamflow diagnostics
            streamflow_obs_ts = string

Update the tutorial
-------------------

In ``docs/source/post.mysimulation.cfg``

Streamflow: The new parameter had to be included:

    .. code::

        # This needs to be set for streamflow diags
        streamflow_obs_ts = '/lcrc/group/e3sm/public_html/e3sm_diags_test_data/unit_test_complete_run/obs/time-series/'

Update the tests
----------------

In ``tests/integration/test_*.cfg``.

Streamflow: The new parameter had to be included:

    .. code::

          streamflow_obs_ts = '/lcrc/group/e3sm/public_html/e3sm_diags_test_data/unit_test_complete_run/obs/time-series/'

The expected files will have to be updated as well.
