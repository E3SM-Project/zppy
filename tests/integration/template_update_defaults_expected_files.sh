# Run this script to update expected files for test_defaults.py
# Run from the top level of the zppy repo
# Run as `./tests/integration/generated/update_defaults_expected_files.sh`

src=test_defaults_output/post/scripts

# If the output is missing, run the test to generate it.
# (The test may fail against the old expected files; that's fine,
# we only need the output to be produced.)
if ! ls ${src}/*.settings >/dev/null 2>&1; then
    echo "No .settings files in ${src}; running the test to generate them..."
    pytest tests/integration/test_defaults.py || true
fi

# Re-check after (possibly) running the test
if ! ls ${src}/*.settings >/dev/null 2>&1; then
    echo "Still no .settings files in ${src} after running the test. Exiting without changes."
    exit 1
fi

rm -rf #expand expected_dir#test_defaults_expected_files
mkdir -p #expand expected_dir#test_defaults_expected_files
# Your output will now become the new expectation.
# You can just move (i.e., not copy) the output since re-running this test will re-generate the output.
mv ${src}/*.settings #expand expected_dir#test_defaults_expected_files
# Rerun test
pytest tests/integration/test_defaults.py
