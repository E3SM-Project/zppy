#! /usr/bin/env python
import glob
import json
import os
import shutil
import subprocess

# command = shlex.split("bash -c 'source init_env && env'")
# proc = subprocess.Popen(command, stdout = subprocess.PIPE)

srcdir = "/lcrc/group/e3sm/ac.szhang/acme_scratch/e3sm_project/test_zppy_pmp/zppy"
cmip_var = json.load(
    open(os.path.join(srcdir, "zppy/templates/pcmdi_diags", "cmip_var.json"))
)
ref_dic = json.load(
    open(os.path.join(srcdir, "zppy/templates/pcmdi_diags", "reference_data.json"))
)

output_path = (
    "/lcrc/soft/climate/e3sm_diags_data/obs_for_e3sm_diags/time-series/NOAA_20C"
)


default_metadata = os.path.join(
    srcdir, "zppy/templates/pcmdi_diags/default_metadata.json"
)
tables_path = "/lcrc/group/e3sm/diagnostics/cmip6-cmor-tables/Tables"

input_path = os.path.join(output_path, "input_data")
if not os.path.exists(input_path):
    os.makedirs(input_path)

raw_data_path = "/lcrc/group/acme/ac.szhang/acme_scratch/data/CVDP_RGD/NOAA_20C"
fpaths = sorted(glob.glob(os.path.join(raw_data_path, "{}*.nc".format("NOAA_20C"))))
for fpath in fpaths:
    fname = fpath.split("/")[-1]
    fname = fname.replace("-", ".")
    fout = "_".join(fname.split(".")[2:])
    fout = os.path.join(input_path, fout.replace("_nc", ".nc"))
    print("input: ", fpath)
    print("output: ", fout)
    if os.path.islink(fout):
        os.remove(fout)
        os.symlink(fpath, fout)
    else:
        os.symlink(fpath, fout)
    del (fname, fout)
del (fpaths, raw_data_path)

for key in cmip_var.keys():
    cmip_var_list = ", ".join(cmip_var[key])
    print(cmip_var_list)
    subprocess.call(
        [
            "e3sm_to_cmip",
            "--output-path",
            output_path,
            "--var-list",
            cmip_var_list,
            "--input-path",
            input_path,
            "--user-metadata",
            default_metadata,
            "--tables-path",
            tables_path,
        ]
    )

# move data to target location
opaths = sorted(glob.glob(os.path.join(output_path, "CMIP6/CMIP/*/*/*/*/*/*/*/*/*.nc")))
for opath in opaths:
    outfile = opath.split("/")[-1]
    outname = outfile.replace("-", "_").split("_")
    fout = "_".join([outname[0], outname[-2], outname[-1]])
    fout = os.path.join(output_path, fout.replace("_nc", ".nc"))
    if os.path.exists(opath):
        os.rename(opath, fout)
    del (outfile, outname, fout)

# clean up directory
if os.path.exists(os.path.join(output_path, "CMIP6")):
    shutil.rmtree(os.path.join(output_path, "CMIP6"))

if os.path.exists(input_path):
    shutil.rmtree(input_path)
