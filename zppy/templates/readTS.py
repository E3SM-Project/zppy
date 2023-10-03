import xcdat


class TS(object):
    def __init__(self, filename):

        self.filename = filename

        self.f = xcdat.open_dataset(filename)

    def __del__(self):

        self.f.close()

    def globalAnnual(self, var):

        units = None

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

            # Read variable
            v = self.f(var)
            units = v.units

            # Annual average
            v = self.f.temporal.group_average(v, "year")

        return v, units
