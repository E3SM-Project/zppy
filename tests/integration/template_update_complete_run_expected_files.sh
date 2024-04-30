# Run this script to update expected files for test_complete_run.py
# Run from the top level of the zppy repo
# Run as `./tests/integration/generated/update_complete_run_expected_files.sh`

# Remove old expected files.
rm -rf #expand expected_dir#expected_complete_run
# Your output will now become the new expectation.
# Copy output so you don't have to rerun zppy to generate the output.
cp -r #expand user_www#zppy_test_complete_run_www/#expand unique_id#/v2.LR.historical_0201 #expand expected_dir#expected_complete_run
zppy_top_level=$(pwd)
cd #expand expected_dir#expected_complete_run
# Remove the image check failures, so they don't end up in the expected files.
rm -rf image_check_failures_complete_run
# This file will list all the expected images.
find . -type f -name '*.png' > ../image_list_expected_complete_run.txt
cd ${zppy_top_level}
# Rerun test
python -u -m unittest tests/integration/test_complete_run.py
