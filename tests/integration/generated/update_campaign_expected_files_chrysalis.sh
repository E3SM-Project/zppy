# Run this script to update expected files for test_campaign.py
# Run from the top level of the zppy repo
# Run as `./tests/integration/generated/update_campaign_expected_files.sh`

for campaign in "cryosphere" "cryosphere_override" "high_res_v1" "none" "water_cycle" "water_cycle_override"
do
    echo ${campaign}
    rm -rf /lcrc/group/e3sm/public_html/zppy_test_resources/test_campaign_${campaign}_expected_files
    mkdir -p /lcrc/group/e3sm/public_html/zppy_test_resources/test_campaign_${campaign}_expected_files
    # Your output will now become the new expectation.
    # You can just move (i.e., not copy) the output since re-running this test will re-generate the output.
    mv test_campaign_${campaign}_output/post/scripts/*.settings /lcrc/group/e3sm/public_html/zppy_test_resources/test_campaign_${campaign}_expected_files
done

# Rerun test
pytest tests/integration/test_campaign.py
