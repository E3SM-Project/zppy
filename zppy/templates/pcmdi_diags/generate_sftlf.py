#!/bin/env python
##################################################################
# This script attemts to generate land/sea mask for a given input
##################################################################
import datetime
import os
import sys

import cdms2 as cdm
import cdutil
import numpy as np

if len(sys.argv) > 4:
    modvar = sys.argv[1]
    modname = sys.argv[2]
    modpath = sys.argv[3]
    modpath_lf = sys.argv[4]
else:
    print("ERROR: must specify {modname},{modpath},{outpath} info")
    exit()

# Set netcdf file criterion - turned on from default 0s
cdm.setCompressionWarnings(0)  # Suppress warnings
cdm.setNetcdfShuffleFlag(0)
cdm.setNetcdfDeflateFlag(1)
cdm.setNetcdfDeflateLevelFlag(9)
cdm.setAutoBounds(1)

cdm.setNetcdfDeflateLevelFlag(9)
cdm.setAutoBounds(1)
f_h = cdm.open(modpath)
var = f_h(modvar)[0, ...]
if var.ndim == 2:
    landMask = cdutil.generateLandSeaMask(var)
    # Deal with land values
    landMask[np.greater(landMask, 1e-15)] = 100
    # Rename
    landMask = cdm.createVariable(
        landMask, id="sftlf", axes=var.getAxisList(), typecode="float32"
    )
    landMask.associated_files = modpath
    landMask.long_name = "Land Area Fraction"
    landMask.standard_name = "land_area_fraction"
    landMask.units = "%"
    landMask.setMissing(1.0e20)
    landMask.id = "sftlf"  # Rename

    # Write variables to file
    print("output sftlf:", modpath_lf)
    if os.path.isfile(modpath_lf):
        os.remove(modpath_lf)
    fOut = cdm.open(modpath_lf, "w")
    # Use function to write standard global atts
    fOut.Conventions = "CF-1.0"
    fOut.history = "File processed: " + datetime.datetime.now().strftime("%Y%m%d")
    fOut.pcmdi_metrics_version = "0.1-alpha"
    fOut.pcmdi_metrics_comment = "PCMDI metrics package"
    fOut.write(landMask.astype("float32"))
    fOut.close()
    f_h.close()
    del (f_h, landMask, fOut, var)
