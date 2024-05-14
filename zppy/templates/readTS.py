from typing import Optional, Tuple

import xarray


class TS(object):
    def __init__(self, directory):

        self.directory: str = directory

        # directory will be of the form `{case_dir}/post/<componen>/glb/ts/monthly/{ts_num_years}yr`
        self.f: xarray.core.dataset.Dataset = xarray.open_mfdataset(f"{directory}/*.nc")
        # Refactor note: `self.f = cdms2.open(filename)` gave `cdms2.dataset.Dataset`

    def __del__(self):

        self.f.close()

    def globalAnnual(
        self, var: str
    ) -> Tuple[xarray.core.dataarray.DataArray, Optional[str]]:

        units: Optional[str] = None

        # Constants, from AMWG diagnostics
        Lv = 2.501e6
        Lf = 3.337e5

        v: xarray.core.dataarray.DataArray

        # Is this a derived variable?
        if var == "RESTOM":

            FSNT, _ = self.globalAnnual("FSNT")
            FLNT, _ = self.globalAnnual("FLNT")
            v = FSNT - FLNT

        elif var == "RESTOA":

            print("NOT READY")
            FSNTOA, _ = self.globalAnnual("FSNTOA")
            FLUT, _ = self.globalAnnual("FLUT")
            v = FSNTOA - FLUT

        elif var == "LHFLX":

            QFLX, _ = self.globalAnnual("QFLX")
            PRECC, _ = self.globalAnnual("PRECC")
            PRECL, _ = self.globalAnnual("PRECL")
            PRECSC, _ = self.globalAnnual("PRECSC")
            PRECSL, _ = self.globalAnnual("PRECSL")
            v = (Lv + Lf) * QFLX - Lf * 1.0e3 * (PRECC + PRECL - PRECSC - PRECSL)

        elif var == "RESSURF":

            FSNS, _ = self.globalAnnual("FSNS")
            FLNS, _ = self.globalAnnual("FLNS")
            SHFLX, _ = self.globalAnnual("SHFLX")
            LHFLX, _ = self.globalAnnual("LHFLX")
            v = FSNS - FLNS - SHFLX - LHFLX

        elif var == "PREC":

            PRECC, _ = self.globalAnnual("PRECC")
            PRECL, _ = self.globalAnnual("PRECL")
            v = 1.0e3 * (PRECC + PRECL)

        else:
            # Non-derived variables

            # Read variable
            v = self.f.data_vars[var]
            # Refactor note: `v = self.f(var)` gave `cdms2.tvariable.TransientVariable`
            units = v.units

            # Annual average

            # Refactor note: `AttributeError: 'Dataset' object has no attribute 'temporal'` seems to always occur
            # Regardless if using CDAT or not, if using as object or class method.
            # v = self.f.temporal.group_average(v, "year")
            v = xarray.Dataset.temporal.group_average(v, "year")

        return v, units
