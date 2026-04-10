# Take the latest expected files and archive them as "official"
# I.e., the expected results for a zppy release or Unified release

release_name=""

for test_name in "comprehensive_v2" "comprehensive_v3" "bundles"
do
  cp -r /global/cfs/cdirs/e3sm/www/zppy_test_resources/expected_${test_name} /global/cfs/cdirs/e3sm/www/zppy_test_resources/${test_name}_${release_name}
done
