# Testing directions for #expand machine#

## How to run a cfg

```
$ pip install .
# Either pass the settings explicitly:
$ python -m tests.integration.utils --unique-id <UNIQUE_ID>
# or edit TEST_SPECIFICS in tests/integration/utils.py and run:
$ python tests/integration/utils.py
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
# Then point the e3sm_diags task at that environment:
#   python -m tests.integration.utils --unique-id <UNIQUE_ID> \
#       --env-cmd "e3sm_diags=source <conda.sh>; conda activate e3sm_diags_<date>"
# (or edit `diags_environment_commands` in tests/integration/utils.py).
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
These tests are ideally run weekly on the `main` branch, via
`python -m tests.complete_run.automation` -- see
`docs/source/dev_guide/tests/automated_test.rst`.

## Commands to promote a baseline

Expected results are no longer produced by copying a run over the previous
baseline. Each complete run writes into its own immutable directory, and
promotion points `latest-main` at one:

```
$ python -m tests.complete_run.promote --machine #expand machine# show
$ python -m tests.complete_run.promote --machine #expand machine# run <tag>
# Add --allow-failed once you have reviewed the differences and decided the
# new results are correct.
```

Rolling back is promoting the previous run again. See
`docs/source/dev_guide/tests/update_expected_results.rst`.
