# Testing directions for #expand machine#

## Commands to run before running integration tests

### test_bundles

```
rm -rf #expand user_www#zppy_test_bundles_www/v2.LR.historical_0201
rm -rf #expand user_output#zppy_test_bundles_output/v2.LR.historical_0201/post
# Generate cfg
python tests/integration/utils.py
zppy -c tests/integration/generated/test_bundles.cfg
# bundle1 and bundle2 should run. After they finish, invoke zppy again to resolve remaining dependencies:
zppy -c tests/integration/generated/test_bundles.cfg
# bundle3 and ilamb should run
```

### test_complete_run

```
rm -rf #expand user_www#zppy_test_complete_run_www/v2.LR.historical_0201
rm -rf #expand user_output#zppy_test_complete_run_output/v2.LR.historical_0201/post
# Generate cfg
python tests/integration/utils.py
zppy -c tests/integration/generated/test_complete_run.cfg
```

## Commands to run to replace outdated expected files

### test_bash_generation

```
rm -rf #expand expected_dir#expected_bash_files
cd <top level of zppy repo>
# Your output will now become the new expectation.
# You can just move (i.e., not copy) the output since re-running this test will re-generate the output.
mv test_bash_generation_output/post/scripts #expand expected_dir#expected_bash_files
# Rerun test
python -u -m unittest tests/integration/test_bash_generation.py
```

#### test_bundles

```
rm -rf #expand expected_dir#expected_bundles
# Your output will now become the new expectation.
# Copy output so you don't have to rerun zppy to generate the output.
cp -r #expand user_www#zppy_test_bundles_www/v2.LR.historical_0201 #expand expected_dir#expected_bundles
mkdir -p #expand expected_dir#expected_bundles/bundle_files
cp -r #expand user_output#zppy_test_bundles_output/v2.LR.historical_0201/post/scripts/bundle*.bash #expand expected_dir#expected_bundles/bundle_files
cd #expand expected_dir#expected_bundles
# This file will list all the expected images.
find . -type f -name '*.png' > ../image_list_expected_bundles.txt
cd <top level of zppy repo>
# Rerun test
python -u -m unittest tests/integration/test_bundles.py
```

### test_campaign

```
cd <top level of zppy repo>
chmod u+x tests/integration/generated/update_campaign_expected_files_#expand machine#.sh
./tests/integration/generated/update_campaign_expected_files_#expand machine#.sh
```
This command also runs the test again.
If the test fails on `test_campaign_high_res_v1`, try running the lines of the loop manually:
```
rm -rf #expand expected_dir#test_campaign_high_res_v1_expected_files
mkdir -p #expand expected_dir#test_campaign_high_res_v1_expected_files
mv test_campaign_high_res_v1_output/post/scripts/*.settings #expand expected_dir#test_campaign_high_res_v1_expected_files
```

### test_complete_run

```
rm -rf #expand expected_dir#expected_complete_run
# Your output will now become the new expectation.
# Copy output so you don't have to rerun zppy to generate the output.
cp -r #expand user_www#zppy_test_complete_run_www/v2.LR.historical_0201 #expand expected_dir#expected_complete_run
cd #expand expected_dir#expected_complete_run
# This file will list all the expected images.
find . -type f -name '*.png' > ../image_list_expected_complete_run.txt
cd <top level of zppy repo>
# Rerun test
python -u -m unittest tests/integration/test_complete_run.py
```

### test_defaults

```
rm -rf #expand expected_dir#test_defaults_expected_files
mkdir -p #expand expected_dir#test_defaults_expected_files
# Your output will now become the new expectation.
# You can just move (i.e., not copy) the output since re-running this test will re-generate the output.
mv test_defaults_output/post/scripts/*.settings #expand expected_dir#test_defaults_expected_files
# Rerun test
python -u -m unittest tests/integration/test_defaults.py
```
