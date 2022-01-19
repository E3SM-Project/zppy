# Run this script to clear test output
# Run from the top level of the zppy repo
# Run as `./tests/clear_test_output.sh`

rm -r test_*_output

rm tests/*.cfg.txt
rm tests/*~
rm -r tests/__pycache__

rm -r tests/integration/image_check_failures
rm tests/integration/*~
rm -r tests/integration/__pycache__
