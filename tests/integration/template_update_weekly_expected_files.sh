# Run this script to update expected files used by both test_bundles.py & test_images.py.
# Run from the top level of the zppy repo
# Run as `./tests/integration/generated/update_weekly_expected_files_#expand machine#.sh`

for test_name in "comprehensive_v2" "comprehensive_v3" "bundles"
do
    # Remove old expected files.
    rm -rf #expand expected_dir#expected_${test_name}
    # Your output will now become the new expectation.
    # Copy output so you don't have to rerun zppy to generate the output.
    if [[ "${test_name,,}" == "comprehensive_v2" ]]; then
      cp -r #expand user_www#zppy_weekly_${test_name}_www/#expand unique_id#/#expand case_name_v2# #expand expected_dir#expected_${test_name}
    else
      cp -r #expand user_www#zppy_weekly_${test_name}_www/#expand unique_id#/#expand case_name# #expand expected_dir#expected_${test_name}
    fi
    if [[ "${test_name,,}" == "bundles" ]]; then
      mkdir -p #expand expected_dir#expected_bundles/bundle_files
      cp -r #expand user_output#zppy_weekly_bundles_output/#expand unique_id#/#expand case_name#/post/scripts/bundle*.bash #expand expected_dir#expected_bundles/bundle_files
    fi
    zppy_top_level=$(pwd)
    cd #expand expected_dir#expected_${test_name}
    # Remove the image check failures, so they don't end up in the expected files.
    rm -rf image_check_failures_${test_name}
    # This file will list all the expected images.
    find . -type f -name '*.png' > ../image_list_expected_${test_name}.txt
    cd ${zppy_top_level}
done

# Rerun test
pytest tests/integration/test_bundles.py
pytest tests/integration/test_images.py
