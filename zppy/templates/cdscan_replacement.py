import sys

import pandas
import xcdat


def cdscan_replacement_xarray(output_file, input_files):
    dataset = xcdat.open_mfdataset(input_files)
    # TODO: write to xml, not netCDF
    dataset.to_netcdf(output_file)


def cdscan_replacement(output_file, input_files):
    if len(input_files) == 1:
        files = []
        # Convert text file of files to a list of files.
        with open(input_files) as f:
            for line in f:
                files.append(line.strip())
        input_files = files
    dataframe = pandas.read_table(input_files)
    dataframe.to_xml(output_file)


if __name__ == "__main__":
    output_file = sys.argv[1]
    input_files = sys.argv[2:]
    cdscan_replacement(output_file, input_files)
