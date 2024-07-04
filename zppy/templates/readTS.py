from typing import Optional, Tuple

import xarray
import xcdat  # noqa: F401


class TS(object):
    def __init__(self, directory):

        self.directory: str = directory

        # `directory` will be of the form `{case_dir}/post/<componen>/glb/ts/monthly/{ts_num_years}yr/`
        self.f: xarray.core.dataset.Dataset = xcdat.open_mfdataset(
            f"{directory}*.nc", center_times=True
        )

    def __del__(self):

        self.f.close()

    def globalAnnual(
        self, var: str
    ) -> Tuple[xarray.core.dataarray.DataArray, Optional[str]]:

        v: xarray.core.dataarray.DataArray
        units: Optional[str] = None

        # Constants, from AMWG diagnostics
        Lv = 2.501e6
        Lf = 3.337e5

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

            annual_average_dataset_for_var: xarray.core.dataset.Dataset = (
                self.f.temporal.group_average(var, "year")
            )
            v = annual_average_dataset_for_var.data_vars[var]
            units = v.units

        return v, units
