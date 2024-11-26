#!/usr/bin/env python
import copy
import glob
import json
import os

from pcmdi_metrics.utils import StringConstructor
from pcmdi_metrics.variability_mode.lib import dict_merge


def main():
    mip = "e3sm"
    exp = "amip"
    case_id = "v20241030"
    period = "1985-2014"
    metric_collection = "mean_climate"
    run_type = "model_vs_obs"
    data_path = "/lcrc/group/e3sm/public_html/diagnostic_output/ac.szhang/e3sm-pcmdi"
    obs_selection = "default"

    # target here is to merge all product models at all realizations to one-big file
    # product = ['v3.LR']
    # realm = ["0101", "0151", "0201"]

    # template for diagnostic directory tree
    # construct the directory for specific mpi, exp and case
    pmprdir_template = StringConstructor(
        "%(product).%(exp)_%(realization)/pcmdi_diags/%(run_type)_%(period)"
    )
    pmprdir = os.path.join(
        data_path,
        pmprdir_template(
            mip=mip,
            exp=exp,
            case_id=case_id,
            product="*",
            realization="*",
            run_type=run_type,
            period=period,
        ),
    )
    print("pmprdir:", pmprdir)

    # template for metrics directory tree
    json_file_dir_template = StringConstructor(
        "metrics_results/%(metric_collection)/%(mip)/%(exp)/%(case_id)"
    )
    json_file_dir = os.path.join(
        pmprdir,
        json_file_dir_template(
            metric_collection=metric_collection,
            mip=mip,
            exp=exp,
            case_id=case_id,
        ),
    )
    print("json_file_dir:", json_file_dir)

    # template for output directory tree
    out_file_dir_template = StringConstructor(
        "%(run_type)_%(period)/%(metric_collection)/%(mip)/%(exp)/%(case_id)"
    )
    out_file_dir = os.path.join(
        data_path,
        "merged_data",
        out_file_dir_template(
            metric_collection=metric_collection,
            mip=mip,
            exp=exp,
            case_id=case_id,
            run_type=run_type,
            period=period,
        ),
    )
    print("out_file_dir:", out_file_dir)
    variables = [
        s.split("/")[-1]
        for s in glob.glob(
            os.path.join(
                json_file_dir,
                "*",
            )
        )
        if os.path.isdir(s)
    ]
    variables = list(set(variables))
    print("variables:", variables)

    for var in variables:
        # json merge
        # try:
        if 1:
            merge_json(
                mip, exp, case_id, var, obs_selection, json_file_dir, out_file_dir
            )
        """
        except Exception as err:
            print("ERROR: ", mip, exp, var, err)
            pass
        """


def merge_json(mip, exp, case_id, var, obs, json_file_dir, out_file_dir):
    print("json_file_dir:", json_file_dir)
    json_file_template = StringConstructor(
        "%(var)_%(model)_%(realization)_*_%(obs)_%(case_id).json"
    )
    # Search for individual JSONs
    json_files = sorted(
        glob.glob(
            os.path.join(
                json_file_dir,
                var,
                json_file_template(
                    var=var,
                    model="*",
                    realization="*",
                    obs=obs,
                    case_id=case_id,
                ),
            )
        )
    )

    print("json_files:", json_files)

    # Remove diveDown JSONs and previously generated merged JSONs if included
    json_files_revised = copy.copy(json_files)
    for j, json_file in enumerate(json_files):
        filename_component = json_file.split("/")[-1].split(".")[0].split("_")
        if "allModels" in filename_component:
            json_files_revised.remove(json_file)
        elif "allRuns" in filename_component:
            json_files_revised.remove(json_file)

    # Load individual JSON and merge to one big dictionary
    for j, json_file in enumerate(json_files_revised):
        print(j, json_file)
        f = open(json_file)
        dict_tmp = json.loads(f.read())
        if j == 0:
            dict_final = dict_tmp.copy()
        else:
            dict_merge(dict_final, dict_tmp)
        f.close()

    # Dump final dictionary to JSON
    if not os.path.exists(out_file_dir):
        os.makedirs(out_file_dir)

    final_json_filename = StringConstructor("%(var)_%(mip)_%(exp)_%(case_id).json")(
        var=var, mip=mip, exp=exp, case_id=case_id
    )
    final_json_file = os.path.join(out_file_dir, final_json_filename)
    if os.path.exists(final_json_file):
        # previously generated merged JSONs if included
        os.remove(final_json_file)

    with open(final_json_file, "w") as fp:
        json.dump(dict_final, fp, sort_keys=True, indent=4)


if __name__ == "__main__":
    main()
