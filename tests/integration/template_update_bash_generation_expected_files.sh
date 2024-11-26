# Run this script to update expected files for test_bash_generation.py
# Run from the top level of the zppy repo
# Run as `./tests/integration/generated/update_bash_generation_expected_files.sh`

rm -rf #expand expected_dir#expected_bash_files
# Your output will now become the new expectation.
# You can just move (i.e., not copy) the output since re-running this test will re-generate the output.
mv test_bash_generation_output/post/scripts #expand expected_dir#expected_bash_files
# Rerun test
pytest tests/integration/test_bash_generation.py
