# Run this script to update expected files for test_bash_generation.py
# Run from the top level of the zppy repo
# Run as `./tests/integration/generated/update_bash_generation_expected_files.sh`

src=test_bash_generation_output/post/scripts

# If the output is missing, run the test to generate it.
# (The test may fail against the old expected files; that's fine,
# we only need the output to be produced.)
if [ ! -d "${src}" ]; then
    echo "No output in ${src}; running the test to generate it..."
    pytest tests/integration/test_bash_generation.py || true
fi

# Re-check after (possibly) running the test
if [ ! -d "${src}" ]; then
    echo "Still no output in ${src} after running the test. Exiting without changes."
    exit 1
fi

rm -rf #expand expected_dir#expected_bash_files
# Your output will now become the new expectation.
# You can just move (i.e., not copy) the output since re-running this test will re-generate the output.
rm -rf ${src}/provenance*
mv ${src} #expand expected_dir#expected_bash_files
# Rerun test
pytest tests/integration/test_bash_generation.py
