# Compute time series of ocean heat content (ohc) using MPAS-O output

import glob
import sys
from datetime import datetime

import numpy as np
from netCDF4 import Dataset, chartostring, date2num

# Run directories
input_dir = sys.argv[1]
case_dir = sys.argv[2]
path_in = "{}/archive/ocn/hist".format(input_dir)
path_out = "{}/post/ocn/glb/ts/monthly/10yr".format(case_dir)

# Years to process
start_yr = int(sys.argv[3])
end_yr = int(sys.argv[4])

# Ocean constants
# specific heat [J/(kg*degC)]
cp = 3.996e3
# [kg/m3]
rho = 1026.0
fac = rho * cp

# Time units, calendar
tcalendar = "noleap"
tunits = "days since 0001-01-01 00:00:00"

# Loop over year sets
for y in range(start_yr, end_yr, 10):

    year1 = y
    year2 = y + 10 - 1
    files = []
    for year in range(year1, year2 + 1):
        print("year=", year)
        inFiles = "%s/*mpaso.hist.am.timeSeriesStatsMonthly.%04d-??-??.nc" % (
            path_in,
            year,
        )
        files.extend(sorted(glob.glob(inFiles)))
    out = "%s/mpaso.glb.%04d01-%04d12.nc" % (path_out, year1, year2)

    # Create output file
    fout = Dataset(out, "w", format="NETCDF4_CLASSIC")
    fout.createDimension("time", None)
    fout.createDimension("nbnd", 2)

    time = fout.createVariable("time", "f8", ("time",))
    time.long_name = "time"
    time.units = tunits
    time.calendar = tcalendar
    time.bounds = "time_bnds"

    time_bnds = fout.createVariable("time_bnds", "f8", ("time", "nbnd"))
    time_bnds.long_name = "time interval endpoints"

    ohc = fout.createVariable("ohc", "f8", ("time",))
    ohc.long_name = "total ocean heat content"
    ohc.units = "J"

    volume = fout.createVariable("volume", "f8", ("time",))
    volume.long_name = "sum of the volumeCell variable over the full domain, used to normalize global statistics"
    volume.units = "m^3"

    # OHC from monthly time series
    itime = 0
    for file in files:

        # Open current input file
        print(file)
        f = Dataset(file, "r")

        # Time variables
        xtime_startMonthly = chartostring(f.variables["xtime_startMonthly"][:])
        xtime_endMonthly = chartostring(f.variables["xtime_endMonthly"][:])

        # Convert to datetime objects (assuming 0 UTC boundary)
        date_start = np.array(
            [datetime.strptime(x[0:10], "%Y-%m-%d") for x in xtime_startMonthly]
        )
        date_end = np.array(
            [datetime.strptime(x[0:10], "%Y-%m-%d") for x in xtime_endMonthly]
        )

        # Convert to netCDF4 time
        tstart = date2num(date_start, tunits, tcalendar)
        tend = date2num(date_end, tunits, tcalendar)
        t = 0.5 * (tstart + tend)

        # Variables needed to compute global OHC
        iregion = 6  # global average region
        sumLayerMaskValue = f.variables[
            "timeMonthly_avg_avgValueWithinOceanLayerRegion_sumLayerMaskValue"
        ][:, iregion, :]
        avgLayerArea = f.variables[
            "timeMonthly_avg_avgValueWithinOceanLayerRegion_avgLayerArea"
        ][:, iregion, :]
        avgLayerThickness = f.variables[
            "timeMonthly_avg_avgValueWithinOceanLayerRegion_avgLayerThickness"
        ][:, iregion, :]
        avgLayerTemperature = f.variables[
            "timeMonthly_avg_avgValueWithinOceanLayerRegion_avgLayerTemperature"
        ][:, iregion, :]

        # volumeCellGlobal
        volumeCell = f.variables["timeMonthly_avg_volumeCellGlobal"][:]

        # Close current input file
        f.close()

        # Compute OHC
        layerArea = sumLayerMaskValue * avgLayerArea
        layerVolume = layerArea * avgLayerThickness
        tmp = layerVolume * avgLayerTemperature
        ohc_tot = fac * np.sum(tmp, axis=1)

        # Diagnostics printout
        for i in range(len(date_start)):
            print(
                "Start, End, OHC = %s (%s), %s (%s), %e"
                % (date_start[i], tstart[i], date_end[i], tend[i], ohc_tot[i])
            )

        # Write data
        time[itime:] = t
        time_bnds[itime:, 0] = tstart
        time_bnds[itime:, 1] = tend
        ohc[itime:] = ohc_tot
        volume[itime:] = volumeCell

        itime = itime + len(t)

    # Close output file
    fout.close()
