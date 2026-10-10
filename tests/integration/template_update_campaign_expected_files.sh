# Run this script to update expected files for test_campaign.py
# Run from the top level of the zppy repo
# Run as `./tests/integration/generated/update_campaign_expected_files.sh`

# Update all campaigns
campaigns=("cryosphere" "cryosphere_override" "high_res_v1" "none" "water_cycle" "water_cycle_override")

# To update only a subset, comment out the line above and use e.g.:
# campaigns=("cryosphere")

# Track whether we've already run the test to generate missing output
test_has_run=false

for campaign in "${campaigns[@]}"
do
    echo ${campaign}
    src=test_campaign_${campaign}_output/post/scripts

    # If the output is missing, run the test once to generate it.
    # (The test may fail against the old expected files; that's fine,
    # we only need the output to be produced.)
    if ! ls ${src}/*.settings >/dev/null 2>&1 && [ "${test_has_run}" = false ]; then
        echo "No .settings files in ${src}; running the test to generate output..."
        pytest tests/integration/test_campaign.py || true
        test_has_run=true
    fi

    # Re-check after (possibly) running the test
    if ! ls ${src}/*.settings >/dev/null 2>&1; then
        echo "Still no .settings files in ${src} after running the test. Skipping ${campaign}."
        continue
    fi

    rm -rf #expand expected_dir#test_campaign_${campaign}_expected_files
    mkdir -p #expand expected_dir#test_campaign_${campaign}_expected_files
    # Your output will now become the new expectation.
    # You can just move (i.e., not copy) the output since re-running this test will re-generate the output.
    mv test_campaign_${campaign}_output/post/scripts/*.settings #expand expected_dir#test_campaign_${campaign}_expected_files
done

# Rerun test
pytest tests/integration/test_campaign.py
