# Run this script to update expected files for test_weekly.py
# Run from the top level of the zppy repo
# Run as `./tests/integration/generated/update_weekly_expected_files_chrysalis.sh`

for test_name in "comprehensive_v2" "comprehensive_v3" "bundles"
do
    # Remove old expected files.
    rm -rf /lcrc/group/e3sm/public_html/zppy_test_resources/expected_${test_name}
    # Your output will now become the new expectation.
    # Copy output so you don't have to rerun zppy to generate the output.
    if [[ "${test_name,,}" == "comprehensive_v2" ]]; then
      cp -r /lcrc/group/e3sm/public_html/diagnostic_output/ac.forsyth2/zppy_weekly_${test_name}_www/test-642-working-env-20241121/v2.LR.historical_0201 /lcrc/group/e3sm/public_html/zppy_test_resources/expected_${test_name}
    else
      cp -r /lcrc/group/e3sm/public_html/diagnostic_output/ac.forsyth2/zppy_weekly_${test_name}_www/test-642-working-env-20241121/v3.LR.historical_0051 /lcrc/group/e3sm/public_html/zppy_test_resources/expected_${test_name}
    fi
    if [[ "${test_name,,}" == "bundles" ]]; then
      mkdir -p /lcrc/group/e3sm/public_html/zppy_test_resources/expected_bundles/bundle_files
      cp -r /lcrc/group/e3sm/ac.forsyth2/zppy_weekly_bundles_output/test-642-working-env-20241121/v3.LR.historical_0051/post/scripts/bundle*.bash /lcrc/group/e3sm/public_html/zppy_test_resources/expected_bundles/bundle_files
    fi
    zppy_top_level=$(pwd)
    cd /lcrc/group/e3sm/public_html/zppy_test_resources/expected_${test_name}
    # Remove the image check failures, so they don't end up in the expected files.
    rm -rf image_check_failures_${test_name}
    # This file will list all the expected images.
    find . -type f -name '*.png' > ../image_list_expected_${test_name}.txt
    cd ${zppy_top_level}
done

# Rerun test
python -u -m unittest tests/integration/test_weekly.py
