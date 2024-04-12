# Run this script to update expected files for test_defaults.py
# Run from the top level of the zppy repo
# Run as `./tests/integration/generated/update_defaults_expected_files.sh`

rm -rf /lcrc/group/e3sm/public_html/zppy_test_resources/test_defaults_expected_files
mkdir -p /lcrc/group/e3sm/public_html/zppy_test_resources/test_defaults_expected_files
# Your output will now become the new expectation.
# You can just move (i.e., not copy) the output since re-running this test will re-generate the output.
mv test_defaults_output/post/scripts/*.settings /lcrc/group/e3sm/public_html/zppy_test_resources/test_defaults_expected_files
# Rerun test
python -u -m unittest tests/integration/test_defaults.py
