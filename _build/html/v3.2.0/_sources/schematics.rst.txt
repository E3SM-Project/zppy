************************
A schematic view of zppy
************************

The following example provides a schematic view of how ``zppy`` functions.
For this example, assume a researcher has 200 years of simulation data.
Figure 1 displays some of the tasks they might configure zppy to run:

- 20-year atmosphere monthly and seasonal climatologies, optionally regridded
- 20-year atmosphere monthly and seasonal climatologies resolving the diurnal cycle (eight times per day in this example, meaning eight data points per day with each point representing a three-hour time block of monthly or seasonally averaged values), optionally regridded
- 10-year atmosphere monthly time-series, optionally regridded
- 10-year atmosphere daily time-series, optionally regridded
- 10-year atmosphere monthly time-series, globally averaged
- 10-year land monthly time-series, optionally regridded

The scientist can also configure zppy to generate helpful plots such as:

- E3SM Diags for 20-year periods, (E3SM Diags includes many diagnostic sets – this example assumes the researcher would like to run them all)
- MPAS-Analysis for 50-year periods
- Global time series plots for 50-year periods

The figures illustrate schematically how zppy would function in this example.
Figure 1 shows how zppy uses sections of the configuration file and
bash/Jinja2 templates to launch jobs.
Figure 2 shows two possible job dependency graphs.

The top graph in Figure 2 shows the dependencies for the years 1-20 E3SM Diags task.
This task requires the monthly climatology for years 1-20.
Because the researcher wants to run the diurnal cycle diagnostic set,
the diurnal climatology for years 1-20 is also required.
Since the scientist wants to run the area mean time series, ENSO, and QBO diagnostic
sets, the monthly time-series for years 1-10 and years 11-20 are required.

The bottom graph in Figure 2 shows the dependencies for the global time series plots.
The plots for years 1-50 require the the monthly time-series for years 1-10, 11-20,
21-30, 31-40, and 41-50 in addition to MPAS-Analysis for years 1-50.
The plots for years 51-100 have similar requirements – however the graph calls
attention to the fact that MPAS-Analysis for years 51-100 itself depends on
MPAS-Analysis for years 1-50.

.. image:: figures/zppy_jobs.png
   :scale: 80%

Figure 1.  Illustration of how zppy uses sections of the configuration file and
bash/Jinja2 templates to launch various jobs.
climo stands for climatology and ts stands for time series.
Note that the configuration file is abridged – see the :ref:`zppy tutorial <tutorial>`
for more complete examples.

.. image:: figures/zppy_dependencies.png
   :scale: 80%

Figure 2. Two possible job dependency graphs.
climo stands for climatology and ts stands for time series.