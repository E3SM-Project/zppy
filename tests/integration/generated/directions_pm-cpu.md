# Testing directions for pm-cpu

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
rm -rf /global/cfs/cdirs/e3sm/www/forsyth/zppy_test_debug_www/<UNIQUE ID>/v2.LR.historical_0201
rm -rf /global/cfs/cdirs/e3sm/forsyth/zppy_test_debug_output/<UNIQUE ID>/v2.LR.historical_0201/post
# Generate cfg
python tests/integration/utils.py

# Run jobs:
zppy -c tests/integration/generated/test_debug_pm-cpu.cfg
# After they finish, check the results:
cd /global/cfs/cdirs/e3sm/forsyth/zppy_test_debug_output/<UNIQUE ID>/v2.LR.historical_0201/post/scripts
grep -v "OK" *status
# Nothing should print
cd -
```

### test_bundles

```
rm -rf /global/cfs/cdirs/e3sm/www/forsyth/zppy_test_bundles_www/<UNIQUE ID>/v2.LR.historical_0201
rm -rf /global/cfs/cdirs/e3sm/forsyth/zppy_test_bundles_output/<UNIQUE ID>/v2.LR.historical_0201/post
# Generate cfg
python tests/integration/utils.py

# Run first set of jobs:
zppy -c tests/integration/generated/test_bundles_pm-cpu.cfg
# bundle1 and bundle2 should run. After they finish, check the results:
cd /global/cfs/cdirs/e3sm/forsyth/zppy_test_bundles_output/<UNIQUE ID>/v2.LR.historical_0201/post/scripts
grep -v "OK" *status
# Nothing should print
cd -

# Now, invoke zppy again to run jobs that needed to wait for dependencies:
zppy -c tests/integration/generated/test_bundles_pm-cpu.cfg
# bundle3 and ilamb should run. After they finish, check the results:
cd /global/cfs/cdirs/e3sm/forsyth/zppy_test_bundles_output/<UNIQUE ID>/v2.LR.historical_0201/post/scripts
grep -v "OK" *status
# Nothing should print
cd -

# If a final release has just been made,
# run the following to move the previous expected results elsewhere.
cp /global/cfs/cdirs/e3sm/www/zppy_test_resources/expected_bundles expected_bundles_v<version>
```

### test_complete_run

```
rm -rf /global/cfs/cdirs/e3sm/www/forsyth/zppy_test_complete_run_www/<UNIQUE ID>/v2.LR.historical_0201
rm -rf /global/cfs/cdirs/e3sm/forsyth/zppy_test_complete_run_output/<UNIQUE ID>/v2.LR.historical_0201/post
# Generate cfg
python tests/integration/utils.py

# Run jobs:
zppy -c tests/integration/generated/test_complete_run_pm-cpu.cfg
# After they finish, check the results:
cd /global/cfs/cdirs/e3sm/forsyth/zppy_test_complete_run_output/<UNIQUE ID>/v2.LR.historical_0201/post/scripts
grep -v "OK" *status
# Nothing should print
cd -

# If a final release has just been made,
# run the following to move the previous expected results elsewhere.
cp /global/cfs/cdirs/e3sm/www/zppy_test_resources/expected_complete_run expected_complete_run_v<version>
```

## Commands to run to replace outdated expected files

### test_bash_generation

```
cd <top level of zppy repo>
chmod u+x tests/integration/generated/update_bash_generation_expected_files_pm-cpu.sh
./tests/integration/generated/update_bash_generation_expected_files_pm-cpu.sh
```

### test_bundles

```
cd <top level of zppy repo>
chmod u+x tests/integration/generated/update_bundles_expected_files_pm-cpu.sh
./tests/integration/generated/update_bundles_expected_files_pm-cpu.sh
```

### test_campaign

```
cd <top level of zppy repo>
chmod u+x tests/integration/generated/update_campaign_expected_files_pm-cpu.sh
./tests/integration/generated/update_campaign_expected_files_pm-cpu.sh
```
This command also runs the test again.
If the test fails on `test_campaign_high_res_v1`, try running the lines of the loop manually:
```
rm -rf /global/cfs/cdirs/e3sm/www/zppy_test_resources/test_campaign_high_res_v1_expected_files
mkdir -p /global/cfs/cdirs/e3sm/www/zppy_test_resources/test_campaign_high_res_v1_expected_files
mv test_campaign_high_res_v1_output/post/scripts/*.settings /global/cfs/cdirs/e3sm/www/zppy_test_resources/test_campaign_high_res_v1_expected_files
```

### test_complete_run

```
cd <top level of zppy repo>
chmod u+x tests/integration/generated/update_complete_run_expected_files_pm-cpu.sh
./tests/integration/generated/update_complete_run_expected_files_pm-cpu.sh
```

### test_defaults

```
cd <top level of zppy repo>
chmod u+x tests/integration/generated/update_defaults_expected_files_pm-cpu.sh
./tests/integration/generated/update_defaults_expected_files_pm-cpu.sh
```

## Commands to generate official expected results for a release

### test_bundles

```
cp -r /global/cfs/cdirs/e3sm/www/forsyth/zppy_test_bundles_www/<UNIQUE ID>/v2.LR.historical_0201 /global/cfs/cdirs/e3sm/www/zppy_test_resources/expected_bundles_unified_<#>
mkdir -p /global/cfs/cdirs/e3sm/www/zppy_test_resources/expected_bundles_unified_<#>/bundle_files
cp -r /global/cfs/cdirs/e3sm/forsyth/zppy_test_bundles_output/<UNIQUE ID>/v2.LR.historical_0201/post/scripts/bundle*.bash /global/cfs/cdirs/e3sm/www/zppy_test_resources/expected_bundles_unified_<#>/bundle_files
```

### test_complete_run

```
cp -r /global/cfs/cdirs/e3sm/www/forsyth/zppy_test_complete_run_www/<UNIQUE ID>/v2.LR.historical_0201 /global/cfs/cdirs/e3sm/www/zppy_test_resources/expected_complete_run_unified_<#>
```
