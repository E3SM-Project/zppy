# Run this script to update expected files for test_bundles.py
# Run from the top level of the zppy repo
# Run as `./tests/integration/generated/update_bundles_expected_files.sh`

# Remove old expected files.
rm -rf /compyfs/www/zppy_test_resources/expected_bundles
# Your output will now become the new expectation.
# Copy output so you don't have to rerun zppy to generate the output.
cp -r /compyfs/www/fors729/zppy_test_bundles_www/unique_id/v2.LR.historical_0201 /compyfs/www/zppy_test_resources/expected_bundles
mkdir -p /compyfs/www/zppy_test_resources/expected_bundles/bundle_files
cp -r /compyfs/fors729/zppy_test_bundles_output/unique_id/v2.LR.historical_0201/post/scripts/bundle*.bash /compyfs/www/zppy_test_resources/expected_bundles/bundle_files
zppy_top_level=$(pwd)
cd /compyfs/www/zppy_test_resources/expected_bundles
# Remove the image check failures, so they don't end up in the expected files.
rm -rf image_check_failures
# This file will list all the expected images.
find . -type f -name '*.png' > ../image_list_expected_bundles.txt
cd ${zppy_top_level}
# Rerun test
python -u -m unittest tests/integration/test_bundles.py
