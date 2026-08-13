# Run this script to update expected files used by both test_bundles.py & test_images.py.
# Run from the top level of the zppy repo
# Run as `./tests/integration/generated/update_weekly_expected_files_#expand machine#.sh`


# NOTE: in `tests` below, do *not* include the `zppy_weekly_` prefix, as that is added later.

# Update all
tests=("comprehensive_v2" "comprehensive_v3" "bundles" "legacy_3.1.0_comprehensive_v2" "legacy_3.1.0_comprehensive_v3" "legacy_3.1.0_bundles" "legacy_3.0.0_comprehensive_v2" "legacy_3.0.0_comprehensive_v3" "legacy_3.0.0_bundles")

# Update regular only
#tests=("comprehensive_v2" "comprehensive_v3" "bundles")

# Update legacy 3.1.0 only
#tests=("legacy_3.1.0_comprehensive_v2" "legacy_3.1.0_comprehensive_v3" "legacy_3.1.0_bundles")

# Update legacy 3.0.0 only
#tests=("legacy_3.0.0_comprehensive_v2" "legacy_3.0.0_comprehensive_v3" "legacy_3.0.0_bundles")

# ------------------------------------------------------------------------------
# NEW: restrict updates to specific diagnostic subdirectories, e.g. e3sm_diags,
# mpas_analysis, global_time_series, ilamb, livvkit, pcmdi_diags.
# Leave empty (diags=()) to update every diag subdirectory (old/full behavior).
# Example -- only refresh e3sm_diags:
# diags=("e3sm_diags")
# This applies uniformly across every entry in `tests` above.
# "bundle_files" (the bundle*.bash files, only relevant when "bundles" is in
# `tests`) is treated as its own selectable name -- include it in `diags` if you
# want it refreshed during a partial update; it's always refreshed on a full one.
diags=()
# ------------------------------------------------------------------------------

for test_name in "${tests[@]}"
do
    # Example for Chrysalis:
    #
    # expected_dir = /lcrc/group/e3sm/public_html/zppy_test_resources/
    #
    # There are 9 subdirectories relevant to image checking:
    # 1-3. expected_bundles, expected_comprehensive_v2, expected_comprehensive_v3
    # 4-6. expected_legacy_3.1.0_bundles, expected_legacy_3.1.0_comprehensive_v2, expected_legacy_3.1.0_comprehensive_v3
    # 7-9. expected_legacy_3.0.0_bundles, expected_legacy_3.0.0_comprehensive_v2, expected_legacy_3.0.0_comprehensive_v3
    # Notice the subdirectories do *not* include the `zppy_weekly` prefix.
    #
    # Each of those subdirectories has a corresponding image list of the form:
    # `image_list_<subdir_name>.txt`
    #
    # Each of those subdirectories in turn contains diagnostic subdirectories,
    # e.g.: e3sm_diags, global_time_series, ilamb, livvkit, mpas_analysis, pcmdi_diags

    expected_dir=#expand expected_dir#expected_${test_name}

    if [[ "${test_name,,}" =~ "v2" ]]; then
      # We need the v2 case name
      output_case_dir=#expand user_www#zppy_weekly_${test_name}_www/#expand unique_id#/#expand case_name_v2#
    else
      # We need the v3 case name
      output_case_dir=#expand user_www#zppy_weekly_${test_name}_www/#expand unique_id#/#expand case_name#
    fi

    if [[ ${#diags[@]} -eq 0 ]]; then
      # Full update: remove old expected files, copy the entire output over.
      rm -rf ${expected_dir}
      # Your output will now become the new expectation.
      # Copy output so you don't have to rerun zppy to generate the output.
      cp -r ${output_case_dir} ${expected_dir}
    else
      # Partial update: only refresh the named diag subdirectories, leaving the
      # rest of expected_${test_name} untouched.
      mkdir -p ${expected_dir}
      for diag_name in "${diags[@]}"
      do
        if [[ "${diag_name}" == "bundle_files" ]]; then
          continue # handled below, alongside the "bundles" test_name check
        fi
        if [[ -d ${output_case_dir}/${diag_name} ]]; then
          rm -rf ${expected_dir}/${diag_name}
          cp -r ${output_case_dir}/${diag_name} ${expected_dir}/${diag_name}
        else
          echo "WARNING: ${output_case_dir}/${diag_name} does not exist -- skipping (test_name=${test_name})."
        fi
      done
    fi

    # test_bundles.py also needs the bash files transferred.
    # Note that for legacy cfgs, we're only testing test_images.py
    if [[ "${test_name,,}" == "bundles" ]]; then
      if [[ ${#diags[@]} -eq 0 ]] || [[ " ${diags[*]} " =~ " bundle_files " ]]; then
        mkdir -p ${expected_dir}/bundle_files
        cp -r #expand user_output#zppy_weekly_bundles_output/#expand unique_id#/#expand case_name#/post/scripts/bundle*.bash ${expected_dir}/bundle_files
      fi
    fi

    zppy_top_level=$(pwd)
    cd ${expected_dir}
    # Remove the image check failures, so they don't end up in the expected files.
    rm -rf image_check_failures_${test_name}
    # This file will list all the expected images -- a mix of freshly-updated
    # and previously-existing diag subdirectories, if `diags` restricted scope.
    find . -type f -name '*.png' > ../image_list_expected_${test_name}.txt
    cd ${zppy_top_level}
done

# To rerun tests:
# pytest tests/integration/test_bundles.py
# pytest tests/integration/test_images.py
