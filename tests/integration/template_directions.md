# Testing directions for #expand machine#

## Commands to run before running integration tests

Replace `<UNIQUE ID>` with a short description of what you're testing.
Usually, this will be an issue number (e.g., "issue-123").
This allows you to simultaneously run jobs
launched from `zppy` on different branches,
without worrying about overwriting results.

NOTE: Actually running the tests (e.g., `python -u -m unittest tests/integration/test_*.py`)
can not be done from two different branches simultaneously
(since files in the `zppy` directory rather than an external directory get changed).

### Debug your code with test_debug

Follow the directions in the cfg to modify it for your testing needs.

```
rm -rf #expand user_www#zppy_test_debug_www/<UNIQUE ID>/v2.LR.historical_0201
rm -rf #expand user_output#zppy_test_debug_output/<UNIQUE ID>/v2.LR.historical_0201/post
# Generate cfg
python tests/integration/utils.py

# Run jobs:
zppy -c tests/integration/generated/test_debug_#expand machine#.cfg
# After they finish, check the results:
cd #expand user_output#zppy_test_debug_output/<UNIQUE ID>/v2.LR.historical_0201/post/scripts
grep -v "OK" *status
# Nothing should print
cd -
```

### test_bundles

```
rm -rf #expand user_www#zppy_test_bundles_www/<UNIQUE ID>/v2.LR.historical_0201
rm -rf #expand user_output#zppy_test_bundles_output/<UNIQUE ID>/v2.LR.historical_0201/post
# Generate cfg
python tests/integration/utils.py

# Run first set of jobs:
zppy -c tests/integration/generated/test_bundles_#expand machine#.cfg
# bundle1 and bundle2 should run. After they finish, check the results:
cd #expand user_output#zppy_test_bundles_output/<UNIQUE ID>/v2.LR.historical_0201/post/scripts
grep -v "OK" *status
# Nothing should print
cd -

# Now, invoke zppy again to run jobs that needed to wait for dependencies:
zppy -c tests/integration/generated/test_bundles_#expand machine#.cfg
# bundle3 and ilamb should run. After they finish, check the results:
cd #expand user_output#zppy_test_bundles_output/<UNIQUE ID>/v2.LR.historical_0201/post/scripts
grep -v "OK" *status
# Nothing should print
cd -

# If a final release has just been made,
# run the following to move the previous expected results elsewhere.
cp #expand expected_dir#expected_bundles expected_bundles_v<version>
```

### test_complete_run

```
rm -rf #expand user_www#zppy_test_complete_run_www/<UNIQUE ID>/v2.LR.historical_0201
rm -rf #expand user_output#zppy_test_complete_run_output/<UNIQUE ID>/v2.LR.historical_0201/post
# Generate cfg
python tests/integration/utils.py

# Run jobs:
zppy -c tests/integration/generated/test_complete_run_#expand machine#.cfg
# After they finish, check the results:
cd #expand user_output#zppy_test_complete_run_output/<UNIQUE ID>/v2.LR.historical_0201/post/scripts
grep -v "OK" *status
# Nothing should print
cd -

# If a final release has just been made,
# run the following to move the previous expected results elsewhere.
cp #expand expected_dir#expected_complete_run expected_complete_run_v<version>
```

## Commands to run to replace outdated expected files

### test_bash_generation

```
cd <top level of zppy repo>
chmod u+x tests/integration/generated/update_bash_generation_expected_files_#expand machine#.sh
./tests/integration/generated/update_bash_generation_expected_files_#expand machine#.sh
```

### test_bundles

```
cd <top level of zppy repo>
chmod u+x tests/integration/generated/update_bundles_expected_files_#expand machine#.sh
./tests/integration/generated/update_bundles_expected_files_#expand machine#.sh
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
cd <top level of zppy repo>
chmod u+x tests/integration/generated/update_complete_run_expected_files_#expand machine#.sh
./tests/integration/generated/update_complete_run_expected_files_#expand machine#.sh
```

### test_defaults

```
cd <top level of zppy repo>
chmod u+x tests/integration/generated/update_defaults_expected_files_#expand machine#.sh
./tests/integration/generated/update_defaults_expected_files_#expand machine#.sh
```

## Commands to generate official expected results for a release

### test_bundles

```
cp -r #expand user_www#zppy_test_bundles_www/<UNIQUE ID>/v2.LR.historical_0201 #expand expected_dir#expected_bundles_unified_<#>
mkdir -p #expand expected_dir#expected_bundles_unified_<#>/bundle_files
cp -r #expand user_output#zppy_test_bundles_output/<UNIQUE ID>/v2.LR.historical_0201/post/scripts/bundle*.bash #expand expected_dir#expected_bundles_unified_<#>/bundle_files
```

### test_complete_run

```
cp -r #expand user_www#zppy_test_complete_run_www/<UNIQUE ID>/v2.LR.historical_0201 #expand expected_dir#expected_complete_run_unified_<#>
```
