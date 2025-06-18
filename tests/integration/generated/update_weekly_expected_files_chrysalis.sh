# Run this script to update expected files used by both test_bundles.py & test_images.py.
# Run from the top level of the zppy repo
# Run as `./tests/integration/generated/update_weekly_expected_files_chrysalis.sh`


# NOTE: in `tests` below, do *not* include the `zppy_weekly_` prefix, as that is added later.

# Update all
tests=("comprehensive_v2" "comprehensive_v3" "bundles" "legacy_3.0.0_comprehensive_v2" "legacy_3.0.0_comprehensive_v3" "legacy_3.0.0_bundles")

# Update regular only
#tests=("comprehensive_v2" "comprehensive_v3" "bundles")

# Update legacy only
#tests=("legacy_3.0.0_comprehensive_v2" "legacy_3.0.0_comprehensive_v3" "legacy_3.0.0_bundles")

for test_name in "${tests[@]}"
do
    # Example for Chrysalis:
    #
    # expected_dir = /lcrc/group/e3sm/public_html/zppy_test_resources/
    #
    # There are 6 subdirectories relevant to image checking:
    # 1-3. expected_bundles, expected_comprehensive_v2, expected_comprehensive_v3
    # 4-6. expected_legacy_3.0.0_bundles, expected_legacy_3.0.0_comprehensive_v2, expected_legacy_3.0.0_comprehensive_v3
    # Notice the subdirectories do *not* include the `zppy_weekly` prefix.
    #
    # Each of those subdirectories has a corresponding image list of the form:
    # `image_list_<subdir_name>.txt`

    # Remove old expected files.
    rm -rf /lcrc/group/e3sm/public_html/zppy_test_resources/expected_${test_name}

    # Your output will now become the new expectation.
    # Copy output so you don't have to rerun zppy to generate the output.
    if [[ "${test_name,,}" =~ "v2" ]]; then
      # We need the v2 case name
      cp -r /lcrc/group/e3sm/public_html/diagnostic_output/ac.forsyth2/zppy_weekly_${test_name}_www/unique_id/v2.LR.historical_0201 /lcrc/group/e3sm/public_html/zppy_test_resources/expected_${test_name}
    else
      # We need the v3 case name
      cp -r /lcrc/group/e3sm/public_html/diagnostic_output/ac.forsyth2/zppy_weekly_${test_name}_www/unique_id/v3.LR.historical_0051 /lcrc/group/e3sm/public_html/zppy_test_resources/expected_${test_name}
    fi

    # test_bundles.py also needs the bash files transferred.
    # Note that for legacy cfgs, we're only testing test_images.py
    if [[ "${test_name,,}" == "bundles" ]]; then
      mkdir -p /lcrc/group/e3sm/public_html/zppy_test_resources/expected_bundles/bundle_files
      cp -r /lcrc/group/e3sm/ac.forsyth2/zppy_weekly_bundles_output/unique_id/v3.LR.historical_0051/post/scripts/bundle*.bash /lcrc/group/e3sm/public_html/zppy_test_resources/expected_bundles/bundle_files
    fi

    zppy_top_level=$(pwd)
    cd /lcrc/group/e3sm/public_html/zppy_test_resources/expected_${test_name}
    # Remove the image check failures, so they don't end up in the expected files.
    rm -rf image_check_failures_${test_name}
    # This file will list all the expected images.
    find . -type f -name '*.png' > ../image_list_expected_${test_name}.txt
    cd ${zppy_top_level}
done

# To rerun tests:
# pytest tests/integration/test_bundles.py
# pytest tests/integration/test_images.py
