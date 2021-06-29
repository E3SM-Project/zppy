import cdms2
import cdutil


class TS(object):
    def __init__(self, filename):

        self.filename = filename

        self.f = cdms2.open(filename)

    def __del__(self):

        self.f.close()

    def globalAnnual(self, var):

        # Constants, from AMWG diagnostics
        Lv = 2.501e6
        Lf = 3.337e5

        # Is this a derived variable?
        if var == "RESTOM":

            FSNT = self.globalAnnual("FSNT")
            FLNT = self.globalAnnual("FLNT")
            v = FSNT - FLNT

        elif var == "RESTOA":

            print("NOT READY")
            FSNTOA = self.globalAnnual("FSNTOA")
            FLUT = self.globalAnnual("FLUT")
            v = FSNTOA - FLUT

        elif var == "LHFLX":

            QFLX = self.globalAnnual("QFLX")
            PRECC = self.globalAnnual("PRECC")
            PRECL = self.globalAnnual("PRECL")
            PRECSC = self.globalAnnual("PRECSC")
            PRECSL = self.globalAnnual("PRECSL")
            v = (Lv + Lf) * QFLX - Lf * 1.0e3 * (PRECC + PRECL - PRECSC - PRECSL)

        elif var == "RESSURF":

            FSNS = self.globalAnnual("FSNS")
            FLNS = self.globalAnnual("FLNS")
            SHFLX = self.globalAnnual("SHFLX")
            LHFLX = self.globalAnnual("LHFLX")
            v = FSNS - FLNS - SHFLX - LHFLX

        elif var == "PREC":

            PRECC = self.globalAnnual("PRECC")
            PRECL = self.globalAnnual("PRECL")
            v = 1.0e3 * (PRECC + PRECL)

        else:

            # Read variable
            v = self.f(var)

            # Annual average
            v = cdutil.YEAR(v)

        return v
