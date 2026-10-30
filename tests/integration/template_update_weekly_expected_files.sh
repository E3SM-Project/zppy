# Run this script to update expected files used by both test_bundles.py & test_images.py.
# Run from the top level of the zppy repo
# Run as `./tests/integration/generated/update_weekly_expected_files_#expand machine#.sh`


# NOTE: in `tests` below, do *not* include the `zppy_weekly_` prefix, as that is added later.

# Current legacy zppy version. Bump this when a new legacy version replaces the old one;
# expected files for every other legacy version are pruned below.
legacy_version="3.2.0"

# Update all
tests=("comprehensive_v2" "comprehensive_v3" "bundles" "legacy_${legacy_version}_comprehensive_v3")

# Update regular only
#tests=("comprehensive_v2" "comprehensive_v3" "bundles")

# Update legacy only
#tests=("legacy_${legacy_version}_comprehensive_v3")

# ------------------------------------------------------------------------------
# Restrict updates to specific diagnostic subdirectories, e.g. e3sm_diags,
# mpas_analysis, global_time_series, ilamb, livvkit, pcmdi_diags.
# Leave empty (tasks=()) to update every task subdirectory (old/full behavior).
# Example -- only refresh e3sm_diags:
# tasks=("e3sm_diags")
# This applies uniformly across every entry in `tests` above.
# "bundle_files" (the bundle*.bash files, only relevant when "bundles" is in
# `tests`) is treated as its own selectable name -- include it in `tasks` if you
# want it refreshed during a partial update; it's always refreshed on a full one.
tasks=()
# ------------------------------------------------------------------------------

# Prune expected files for legacy versions other than ${legacy_version}.
# Only the current legacy version is tested, and older ones are never overwritten,
# so without this they linger. Safe in every mode (full or partial),
# since it never touches the current version.
resources_dir=#expand expected_dir#
if [[ -d "${resources_dir}" ]]; then
    # Make globs that match nothing expand to nothing (instead of the literal pattern),
    # so the loop below is skipped when there are no legacy files to prune.
    shopt -s nullglob
    for possibly_stale in ${resources_dir}expected_legacy_* ${resources_dir}image_list_expected_legacy_*
    do
        case "$(basename ${possibly_stale})" in
            *legacy_${legacy_version}_*) ;;
            *)
                echo "Removing stale legacy expected file(s): ${possibly_stale}"
                rm -rf ${possibly_stale}
                ;;
        esac
    done
    shopt -u nullglob
fi

for test_name in "${tests[@]}"
do
    # Example for Chrysalis:
    #
    # expected_dir = /lcrc/group/e3sm/public_html/zppy_test_resources/
    #
    # There are 4 subdirectories relevant to image checking:
    # 1-3. expected_bundles, expected_comprehensive_v2, expected_comprehensive_v3
    # 4. expected_legacy_3.2.0_comprehensive_v3
    # Notice the subdirectories do *not* include the `zppy_weekly` prefix.
    #
    # Each of those subdirectories has a corresponding image list of the form:
    # `image_list_<subdir_name>.txt`
    #
    # Each of those subdirectories in turn contains task subdirectories,
    # e.g.: e3sm_diags, global_time_series, ilamb, livvkit, mpas_analysis, pcmdi_diags

    expected_dir=#expand expected_dir#expected_${test_name}

    if [[ "${test_name,,}" =~ "v2" ]]; then
      # We need the v2 case name
      output_case_dir=#expand user_www#zppy_weekly_${test_name}_www/#expand unique_id#/#expand case_name_v2#
    else
      # We need the v3 case name
      output_case_dir=#expand user_www#zppy_weekly_${test_name}_www/#expand unique_id#/#expand case_name#
    fi

    if [[ ${#tasks[@]} -eq 0 ]]; then
      # Full update: remove old expected files, copy the entire output over.
      rm -rf ${expected_dir}
      # Your output will now become the new expectation.
      # Copy output so you don't have to rerun zppy to generate the output.
      cp -r ${output_case_dir} ${expected_dir}
    else
      # Partial update: only refresh the named task subdirectories, leaving the
      # rest of expected_${test_name} untouched.
      mkdir -p ${expected_dir}
      for task_name in "${tasks[@]}"
      do
        if [[ "${task_name}" == "bundle_files" ]]; then
          continue # handled below, alongside the "bundles" test_name check
        fi
        if [[ -d ${output_case_dir}/${task_name} ]]; then
          rm -rf ${expected_dir}/${task_name}
          cp -r ${output_case_dir}/${task_name} ${expected_dir}/${task_name}
        else
          echo "WARNING: ${output_case_dir}/${task_name} does not exist -- skipping (test_name=${test_name})."
        fi
      done
    fi

    # test_bundles.py also needs the bash files transferred.
    # Note that for legacy cfgs, we're only testing test_images.py
    if [[ "${test_name,,}" == "bundles" ]]; then
      if [[ ${#tasks[@]} -eq 0 ]] || [[ " ${tasks[*]} " =~ " bundle_files " ]]; then
        mkdir -p ${expected_dir}/bundle_files
        cp -r #expand user_output#zppy_weekly_bundles_output/#expand unique_id#/#expand case_name#/post/scripts/bundle*.bash ${expected_dir}/bundle_files
      fi
    fi

    zppy_top_level=$(pwd)
    cd ${expected_dir}
    # Remove the image check failures, so they don't end up in the expected files.
    # The directory name can carry a suffix after the test name (e.g.
    # image_check_failures_comprehensive_v3_try2), so match any suffix.
    rm -rf image_check_failures_*
    # This file will list all the expected images -- a mix of freshly-updated
    # and previously-existing task subdirectories, if `tasks` restricted scope.
    find . -type f -name '*.png' -not -path './image_check_failures_*' > ../image_list_expected_${test_name}.txt
    cd ${zppy_top_level}
done

# To rerun tests:
# pytest tests/integration/test_bundles.py
# pytest tests/integration/test_images.py
