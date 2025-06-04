# Run this script to update expected files used by both test_bundles.py & test_images.py.
# Run from the top level of the zppy repo
# Run as `./tests/integration/generated/update_weekly_expected_files_#expand machine#.sh`

# Update all
tests=("comprehensive_v2" "comprehensive_v3" "bundles" "legacy_3.0.0_comprehensive_v2" "legacy_3.0.0_comprehensive_v3" "legacy_3.0.0_bundles")

# Update regular only
#tests=("comprehensive_v2" "comprehensive_v3" "bundles")

# Update legacy only
#tests=("legacy_3.0.0_comprehensive_v2" "legacy_3.0.0_comprehensive_v3" "legacy_3.0.0_bundles")

for test_name in "${tests[@]}"
do
    # Remove old expected files.
    rm -rf #expand expected_dir#expected_${test_name}

    # Your output will now become the new expectation.
    # Copy output so you don't have to rerun zppy to generate the output.
    if [[ "${test_name,,}" =~ "v2" ]]; then
      # We need the v2 case name
      cp -r #expand user_www#zppy_weekly_${test_name}_www/#expand unique_id#/#expand case_name_v2# #expand expected_dir#expected_${test_name}
    else
      # We need the v3 case name
      cp -r #expand user_www#zppy_weekly_${test_name}_www/#expand unique_id#/#expand case_name# #expand expected_dir#expected_${test_name}
    fi

    # test_bundles.py also needs the bash files transferred.
    # Note that for legacy cfgs, we're only testing test_images.py
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

# To rerun tests:
# pytest tests/integration/test_bundles.py
# pytest tests/integration/test_images.py
