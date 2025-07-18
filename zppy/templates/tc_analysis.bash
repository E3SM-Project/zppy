#!/bin/bash
{% include 'inclusions/slurm_header.bash' %}
{% include 'inclusions/boilerplate.bash' %}
{{ environment_commands }}

set -e # Stop running script on error

# A Bash script to post-process E3SM 6 hourly (h2) instantaneous output to generate a text file storing Tropical Cyclone tracks
# tempestremap and tempestextremes are built in e3sm-unified from version 1.5.0.

#For typical EAM v2 ne gp2 grids.
start="{{ '%04d' % (year1) }}"
end="{{ '%04d' % (year2) }}"
caseid="{{ case }}"
drc_in={{ input }}/{{ input_subdir }}
y1={{ year1 }}
y2={{ year2 }}
Y1="{{ '%04d' % (year1) }}"
Y2="{{ '%04d' % (year2) }}"
result_dir={{ output }}/post/atm/tc-analysis_${Y1}_${Y2}/

rm -rf ${result_dir}

atm_name={{ atm_name }}
input_files={{ input_files }}

# Determine res and pg2
first_file=`echo $(ls ${drc_in}/${caseid}.{{ input_files }}.*.nc | head -n 1)`
echo "first_file=${first_file}"
topography_file=`echo $(ncks --trd -M -m ${first_file} | grep -E -i "^global attribute [0-9]+: topography_file" | cut -f 11- -d ' ' | sort)`
echo "topography_file=${topography_file}"
res={{ res }}
pg2=false
filename="${topography_file##*/}"
echo "filename=${filename}"
if [[ $filename =~ ne[0-9]+np4pg2+ ]]; then
    grid="${BASH_REMATCH[0]}"
    echo "grid=${grid}"
    if [[ -z "${res}" ]]; then
        echo "Inferring res from grid"
        if [[ $grid =~ ne([0-9]*) ]]; then
            res=${BASH_REMATCH[1]}
        fi
    fi
    pg2=true
else
    echo "Pattern not found in filename: $filename"
fi
echo "res=${res}"
echo "pg2=${pg2}"

mkdir -p $result_dir
file_name=${caseid}_${start}_${end}

# Generate mesh files (.g).
if $pg2; then
    # For v2 and v3 production simulation with pg2 grids:
    GenerateCSMesh --res $res --alt --file ${result_dir}outCSMeshne$res.g
    GenerateVolumetricMesh --in ${result_dir}outCSMeshne$res.g  --out ${result_dir}outCSne$res.g --np 2 --uniform
    out_type="FV"
else
    # For v1 production simulation with np4 grids:
    GenerateCSMesh --res $res --alt --file ${result_dir}outCSne$res.g
    out_type="CGLL"
fi
echo $out_type
# Generate connectivity files (.dat)
GenerateConnectivityFile --in_mesh ${result_dir}outCSne$res.g --out_type $out_type --out_connect ${result_dir}connect_CSne${res}_v2.dat

# Get the list of files
cd ${drc_in};eval ls ${drc_in}/${caseid}.$input_files.*{${start}..${end}}*.nc >${result_dir}inputfile_${file_name}.txt
cd ${drc_in};eval ls ${caseid}.$input_files.*{${start}..${end}}*.nc >${result_dir}outputfile_${file_name}.txt

cd ${result_dir}
# Detection threshold including:
# The sea-level pressure (SLP) must be a local minimum; SLP must have a sufficient decrease (300 Pa) compared to surrounding nodes within 4 degree radius; The average of the 200 hPa and 500 hPa level temperature decreases by 0.6 K in all directions within a 4 degree radius from the location to fSLP minima
if [ $res == 120 ]; then
    echo $res
    DetectNodes --verbosity 0 --in_connect ${result_dir}connect_CSne${res}_v2.dat --closedcontourcmd "PSL,300.0,4.0,0;_AVG(T200,T500),-0.6,4,0.30" --mergedist 6.0 --searchbymin PSL --outputcmd "PSL,min,0;_VECMAG(UBOT,VBOT),max,2" --timestride 1 --in_data_list ${result_dir}inputfile_${file_name}.txt --out ${result_dir}out.dat
elif [ $res == 30 ]; then
    echo $res
    DetectNodes --verbosity 0 --in_connect ${result_dir}connect_CSne${res}_v2.dat --closedcontourcmd "PSL,300.0,4.0,0;_AVG(T200,T500),-0.6,4,1.0" --mergedist 6.0 --searchbymin PSL --outputcmd "PSL,min,0;_VECMAG(UBOT,VBOT),max,2" --timestride 1 --in_data_list ${result_dir}inputfile_${file_name}.txt --out ${result_dir}out.dat
else
    echo “$res value not supported”
fi


cat ${result_dir}out.dat0* > ${result_dir}cyclones_${file_name}.txt

# Stitch all candidate nodes in time to form tracks, with a maximum distance between candidates of 6.0, minimum time steps of 6, and with a maximum gap size of one (most consecutive time steps with no associated candidate). And there is threshold for wind speed, lat and lon.
StitchNodes --in_fmt "lon,lat,slp,wind" --in_connect ${result_dir}connect_CSne${res}_v2.dat --range 6.0 --mintime 6 --maxgap 1 --in ${result_dir}cyclones_${file_name}.txt --out ${result_dir}cyclones_stitch_${file_name}.dat --threshold "wind,>=,17.5,6;lat,<=,40.0,6;lat,>=,-40.0,6"
rm ${result_dir}cyclones_${file_name}.txt

# Generate histogram of detections
HistogramNodes --in ${result_dir}cyclones_stitch_${file_name}.dat --iloncol 2 --ilatcol 3 --out ${result_dir}cyclones_hist_${file_name}.nc

# Calculate relative vorticity
sed -i 's/\.nc/_vorticity.nc/' ${result_dir}outputfile_${file_name}.txt
VariableProcessor --in_data_list ${result_dir}inputfile_${file_name}.txt --out_data_list ${result_dir}outputfile_${file_name}.txt --var "_CURL{4,0.5}(U850,V850)" --varout "VORT" --in_connect ${result_dir}connect_CSne${res}_v2.dat

DetectNodes --verbosity 0 --in_connect ${result_dir}connect_CSne${res}_v2.dat --closedcontourcmd "VORT,-5.e-6,4,0" --mergedist 2.0 --searchbymax VORT --outputcmd "VORT,max,0" --in_data_list ${result_dir}outputfile_${file_name}.txt --out ${result_dir}aew_out.dat --minlat -35.0 --maxlat 35.0
cat ${result_dir}aew_out.dat0* > ${result_dir}aew_${file_name}.txt

StitchNodes --in_fmt "lon,lat,VORT" --in_connect ${result_dir}connect_CSne${res}_v2.dat --range 3.0 --minlength 8 --maxgap 0 --min_endpoint_dist 10.0 --in ${result_dir}aew_${file_name}.txt --out ${result_dir}aew_stitch_5e-6_${file_name}.dat --threshold "lat,<=,25.0,8;lat,>=,0.0,8"
rm ${result_dir}aew_${file_name}.txt

HistogramNodes --in ${result_dir}aew_stitch_5e-6_${file_name}.dat --iloncol 2 --ilatcol 3 --nlat 256 --nlon 512 --out ${result_dir}aew_hist_${file_name}.nc

rm ${result_dir}*out.dat00*.dat
rm ${result_dir}${caseid}*.nc
rm ${result_dir}*.txt

# Update status file and exit
cd {{ scriptDir }}
{% raw %}
ENDTIME=$(date +%s)
ELAPSEDTIME=$(($ENDTIME - $STARTTIME))
{% endraw %}
echo ==============================================
echo "Elapsed time: $ELAPSEDTIME seconds"
echo ==============================================
rm -f {{ prefix }}.status
echo 'OK' > {{ prefix }}.status
exit 0
