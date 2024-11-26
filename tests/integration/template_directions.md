# Testing directions for #expand machine#

## How to run a cfg

```
# Change UNIQUE_ID in tests/integration/utils.py
#
$ pip install . && python tests/integration/utils.py
```

Now, if you're running the e3sm_diags task,
it's a good idea to test on the latest diags code.
(If you're not, then skip to the next code block).
```
# `cd` to e3sm_diags directory
$ git checkout main
$ git fetch upstream
$ git reset --hard upstream/main
$ git log # Should match https://github.com/E3SM-Project/e3sm_diags/commits/main
$ mamba clean --all
$ mamba env create -f conda-env/dev.yml -n e3sm_diags_<date>
$ conda activate e3sm_diags_<date>
$ pip install .
$ `cd` back to zppy directory
# Then edit tests/integration/utils.py `diags_environment_commands` to use that environment.
```

```
$ zppy -c tests/integration/generated/test_<cfg-name>_#expand machine#.cfg
# Some cfg files should be run twice (bundles)
# Some cfg files are meant to be run after another (run mvm_2 after mvm_1 completes)
$ cd #expand user_output#zppy_test_<cfg-name>_output/<UNIQUE_ID>/#expand case_name#/post/scripts
$ grep -v "OK" *status
# If this has no output, that means there are no errors.
```

Changing `UNIQUE_ID` allows you to simultaneously run jobs
launched from `zppy` on different branches,
without worrying about overwriting results.

NOTE: Actually running the tests (e.g., `pytest tests/integration/test_*.py`)
can not be done from two different branches simultaneously
(since files in the `zppy` directory rather than an external directory get changed).

## Minimal cases

Some tests specifically check minimal zppy cfgs:
i.e., cfgs with as few parameters as possible to test a specific case.
If your code changes could interact with these minimal cases,
then you should run the relevant ones to make sure they still work.

These do not have automatic Python testing.
The comprehensive and bundles tests do have this, however.
These tests are ideally run weekly on the `main` branch.

## Commands to run to replace outdated expected files


Basic tests:
```
cd <top level of zppy repo>

chmod u+x tests/integration/generated/update_bash_generation_expected_files_#expand machine#.sh
./tests/integration/generated/update_bash_generation_expected_files_#expand machine#.sh

chmod u+x tests/integration/generated/update_campaign_expected_files_#expand machine#.sh
./tests/integration/generated/update_campaign_expected_files_#expand machine#.sh
# This command also runs the test again.
# If the test fails on `test_campaign_high_res_v1`, try running the lines of the loop manually:
rm -rf #expand expected_dir#test_campaign_high_res_v1_expected_files
mkdir -p #expand expected_dir#test_campaign_high_res_v1_expected_files
mv test_campaign_high_res_v1_output/post/scripts/*.settings #expand expected_dir#test_campaign_high_res_v1_expected_files

chmod u+x tests/integration/generated/update_defaults_expected_files_#expand machine#.sh
./tests/integration/generated/update_defaults_expected_files_#expand machine#.sh
```

Weekly tests require running zppy beforehand:
```
cd <top level of zppy repo>
chmod u+x tests/integration/generated/update_weekly_expected_files_#expand machine#.sh
./tests/integration/generated/update_weekly_expected_files_#expand machine#.sh
```

## Commands to generate official expected results for a zppy/Unified release

Edit `release_name` in
`tests/integration/generated/update_archive_expected_files_#expand machine#.sh`.
Then, run:
```
chmod u+x tests/integration/generated/update_archive_expected_files_#expand machine#.sh
./tests/integration/generated/update_archive_expected_files_#expand machine#.sh
```
