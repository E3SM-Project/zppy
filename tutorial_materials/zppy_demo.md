# zppy demo

# Load the E3SM Unified environment
This environment has all the important post-processing packages,
including zppy and the packages it calls.
```
# This will load E3SM Unified 1.10.0
$ source /global/common/software/e3sm/anaconda_envs/load_latest_e3sm_unified_pm-cpu.sh
```

# Short term archiving
zppy works best when using a short-term achived simulation.
To short-term archive a simulation, you can run:
```
$ cd <simulations_dir>/<case_name>/case_scripts
$ ./case.st_archive --last-date yyyy-mm-dd --force-move --no-incomplete-logs
$ ls <e3sm_simulations_dir>/<case_name>/archive # Archives will be here
```
We'll use a simulation that has been short-term archived already.

Our short-term archived simulation output can be found in:
```
/global/cfs/cdirs/e3sm/www/Tutorials/2024/simulations/extendedOutput.v3.LR.historical_0101/archive
```

In addition to the content in `archive`, there are a few files we need in `run`:
```
extendedOutput.v3.LR.historical_0101.mpaso.rst.2000-01-01_00000.nc
extendedOutput.v3.LR.historical_0101.mpassi.rst.2000-01-01_00000.nc
mpaso_in
mpassi_in
streams.ocean
streams.seaice
```

# The zppy cfg
The zppy `cfg` file defines everything `zppy` needs to know to operate.
Let's examine this file.
```
cat extendedOutput.v3.LR.historical_0101.cfg
```

# Running zppy
Now all we have to do is run this one line!
```
zppy -c extendedOutput.v3.LR.historical_0101.cfg
```

<details>
<summary>Example output</summary>

The initial lines of the output tell us where to go for help and that the configuration file is able to be interpreted.
```
For help, please see https://e3sm-project.github.io/zppy. Ask questions at https://github.com/E3SM-Project/zppy/discussions/categories/q-a.
Configuration file validation passed.
```

- The climo jobs run fist. We see that indeed 6 climo jobs launch. 
- The `environment_commands` tells us what environment we're operating we're in. Knowing the environment your job is running in is _very_ important. You don't want to have a failure just because you're using the wrong version of a package.
- The number after "batch job" is the job ID.

```
climo_atm_monthly_180x360_aave_2000-2001
...Submitted batch job 25198124
   environment_commands=source /global/common/software/e3sm/anaconda_envs/load_latest_e3sm_unified_pm-cpu.sh
climo_atm_monthly_180x360_aave_2002-2003
...Submitted batch job 25198125
   environment_commands=source /global/common/software/e3sm/anaconda_envs/load_latest_e3sm_unified_pm-cpu.sh
climo_atm_monthly_diurnal_8xdaily_180x360_aave_2000-2001
...Submitted batch job 25198126
   environment_commands=source /global/common/software/e3sm/anaconda_envs/load_latest_e3sm_unified_pm-cpu.sh
climo_atm_monthly_diurnal_8xdaily_180x360_aave_2002-2003
...Submitted batch job 25198128
   environment_commands=source /global/common/software/e3sm/anaconda_envs/load_latest_e3sm_unified_pm-cpu.sh
climo_land_monthly_climo_2000-2001
...Submitted batch job 25198129
   environment_commands=source /global/common/software/e3sm/anaconda_envs/load_latest_e3sm_unified_pm-cpu.sh
climo_land_monthly_climo_2002-2003
...Submitted batch job 25198130
   environment_commands=source /global/common/software/e3sm/anaconda_envs/load_latest_e3sm_unified_pm-cpu.sh
```

- 12 time series jobs launch.
- `ts` tasks also print `e3sm_to_cmip_environment_commands`. If this is empty, then the `e3sm_to_cmip` call will use the same environment that NCO was using to produce the time series. This is the usual case.

```
ts_atm_monthly_180x360_aave_2000-2001-0002
...Submitted batch job 25198131
   environment_commands=source /global/common/software/e3sm/anaconda_envs/load_latest_e3sm_unified_pm-cpu.sh
   e3sm_to_cmip_environment_commands=
ts_atm_monthly_180x360_aave_2002-2003-0002
...Submitted batch job 25198133
   environment_commands=source /global/common/software/e3sm/anaconda_envs/load_latest_e3sm_unified_pm-cpu.sh
   e3sm_to_cmip_environment_commands=
ts_atm_daily_180x360_aave_2000-2001-0002
...Submitted batch job 25198134
   environment_commands=source /global/common/software/e3sm/anaconda_envs/load_latest_e3sm_unified_pm-cpu.sh
   e3sm_to_cmip_environment_commands=
ts_atm_daily_180x360_aave_2002-2003-0002
...Submitted batch job 25198135
   environment_commands=source /global/common/software/e3sm/anaconda_envs/load_latest_e3sm_unified_pm-cpu.sh
   e3sm_to_cmip_environment_commands=
ts_atm_monthly_glb_2000-2004-0005
...Submitted batch job 25198136
   environment_commands=source /global/common/software/e3sm/anaconda_envs/load_latest_e3sm_unified_pm-cpu.sh
   e3sm_to_cmip_environment_commands=
ts_atm_monthly_glb_2005-2009-0005
...Submitted batch job 25198138
   environment_commands=source /global/common/software/e3sm/anaconda_envs/load_latest_e3sm_unified_pm-cpu.sh
   e3sm_to_cmip_environment_commands=
ts_land_monthly_2000-2001-0002
...Submitted batch job 25198139
   environment_commands=source /global/common/software/e3sm/anaconda_envs/load_latest_e3sm_unified_pm-cpu.sh
   e3sm_to_cmip_environment_commands=
ts_land_monthly_2002-2003-0002
...Submitted batch job 25198140
   environment_commands=source /global/common/software/e3sm/anaconda_envs/load_latest_e3sm_unified_pm-cpu.sh
   e3sm_to_cmip_environment_commands=
ts_land_monthly_glb_2000-2004-0005
...Submitted batch job 25198142
   environment_commands=source /global/common/software/e3sm/anaconda_envs/load_latest_e3sm_unified_pm-cpu.sh
   e3sm_to_cmip_environment_commands=
ts_land_monthly_glb_2005-2009-0005
...Submitted batch job 25198143
   environment_commands=source /global/common/software/e3sm/anaconda_envs/load_latest_e3sm_unified_pm-cpu.sh
   e3sm_to_cmip_environment_commands=
```

- For tasks that produce visual output, we display the URL where that output can be found

```
e3sm_diags_atm_monthly_180x360_aave_model_vs_obs_2000-2001
...Submitted batch job 25198144
   environment_commands=source /global/common/software/e3sm/anaconda_envs/load_latest_e3sm_unified_pm-cpu.sh
URL: https://portal.nersc.gov/cfs/e3sm/forsyth/E3SM-tutorial/extendedOutput.v3.LR.historical_0101/e3sm_diags
e3sm_diags_atm_monthly_180x360_aave_model_vs_obs_2002-2003
...Submitted batch job 25198145
   environment_commands=source /global/common/software/e3sm/anaconda_envs/load_latest_e3sm_unified_pm-cpu.sh
URL: https://portal.nersc.gov/cfs/e3sm/forsyth/E3SM-tutorial/extendedOutput.v3.LR.historical_0101/e3sm_diags
```

```
mpas_analysis_ts_2000-2004_climo_2000-2004
...Submitted batch job 25198147
   environment_commands=source /global/common/software/e3sm/anaconda_envs/load_latest_e3sm_unified_pm-cpu.sh
URL: https://portal.nersc.gov/cfs/e3sm/forsyth/E3SM-tutorial/extendedOutput.v3.LR.historical_0101/mpas_analysis
```

```
global_time_series_2000-2004
...Submitted batch job 25198148
   environment_commands=source /global/common/software/e3sm/anaconda_envs/load_latest_e3sm_unified_pm-cpu.sh
URL: https://portal.nersc.gov/cfs/e3sm/forsyth/E3SM-tutorial/extendedOutput.v3.LR.historical_0101/global_time_series
```

```
ilamb_2000-2001
...Submitted batch job 25198149
   environment_commands=source /global/common/software/e3sm/anaconda_envs/load_latest_e3sm_unified_pm-cpu.sh
URL: https://portal.nersc.gov/cfs/e3sm/forsyth/E3SM-tutorial/extendedOutput.v3.LR.historical_0101/ilamb
ilamb_2002-2003
...Submitted batch job 25198151
   environment_commands=source /global/common/software/e3sm/anaconda_envs/load_latest_e3sm_unified_pm-cpu.sh
URL: https://portal.nersc.gov/cfs/e3sm/forsyth/E3SM-tutorial/extendedOutput.v3.LR.historical_0101/ilamb
```

</details>

Now, many batch jobs will launch.
To keep track of what's still running, we can define some helpful aliases.
To check on all batch jobs:
```
alias sqa='squeue -o "%8u %.7a %.4D %.10P %8i %.2t %.10r %.10M %.10l %.8Q %j" --sort=P,-t,-p'
```
To check on your batch jobs specifically:
```
alias sq='sqa -u $USER'
```
The output of sq uses several abbreviations: ST = Status (with R = running, PD = pending, CG = completing).
There are also reasons why a job isn't running yet: Dependency -- job is waiting for another job to finish first,
Resources or Priority -- job will run relatively soon.

It can take a while for jobs to run. Notably `e3sm_diags` and `mpas_analysis` can take an hour or more.

<details>
<summary>Example output</summary>

Note that this output will look slightly different for you, because you will have set
`account = "ntrain6"` and `reservation = "e3sm_day3"`. Those will show up as
`ntrain6` under `ACCOUNT` and `resv` under `PARTITION`.

```
$ sq
USER     ACCOUNT NODE PARTITION JOBID    ST     REASON       TIME TIME_LIMIT NAME
forsyth     e3sm    8 regular_m 25198151 PD Dependency       0:00      30:00 ilamb_2002-2003
forsyth     e3sm    8 regular_m 25198149 PD Dependency       0:00      30:00 ilamb_2000-2001
forsyth     e3sm    1 regular_m 25198148 PD Dependency       0:00      30:00 global_time_series_2000-2004
forsyth     e3sm    1 regular_m 25198147 PD   Priority       0:00    2:00:00 mpas_analysis_ts_2000-2004_climo_2000-2004
forsyth     e3sm    1 regular_m 25198145 PD Dependency       0:00    2:00:00 e3sm_diags_atm_monthly_180x360_aave_model_vs_obs_2002-2003
forsyth     e3sm    1 regular_m 25198144 PD Dependency       0:00    2:00:00 e3sm_diags_atm_monthly_180x360_aave_model_vs_obs_2000-2001
forsyth     e3sm    1 regular_m 25198143 PD   Priority       0:00      30:00 ts_land_monthly_glb_2005-2009-0005
forsyth     e3sm    1 regular_m 25198142 PD   Priority       0:00      30:00 ts_land_monthly_glb_2000-2004-0005
forsyth     e3sm    1 regular_m 25198140 PD   Priority       0:00      30:00 ts_land_monthly_2002-2003-0002
forsyth     e3sm    1 regular_m 25198139 PD   Priority       0:00      30:00 ts_land_monthly_2000-2001-0002
forsyth     e3sm    1 regular_m 25198138 PD   Priority       0:00      30:00 ts_atm_monthly_glb_2005-2009-0005
forsyth     e3sm    1 regular_m 25198136 PD   Priority       0:00      30:00 ts_atm_monthly_glb_2000-2004-0005
forsyth     e3sm    1 regular_m 25198135 PD   Priority       0:00      30:00 ts_atm_daily_180x360_aave_2002-2003-0002
forsyth     e3sm    1 regular_m 25198134 PD   Priority       0:00      30:00 ts_atm_daily_180x360_aave_2000-2001-0002
forsyth     e3sm    1 regular_m 25198133 PD   Priority       0:00      30:00 ts_atm_monthly_180x360_aave_2002-2003-0002
forsyth     e3sm    1 regular_m 25198131 PD   Priority       0:00      30:00 ts_atm_monthly_180x360_aave_2000-2001-0002
forsyth     e3sm    4 regular_m 25198130 PD   Priority       0:00      30:00 climo_land_monthly_climo_2002-2003
forsyth     e3sm    4 regular_m 25198129 PD   Priority       0:00      30:00 climo_land_monthly_climo_2000-2001
forsyth     e3sm    4 regular_m 25198128 PD   Priority       0:00      30:00 climo_atm_monthly_diurnal_8xdaily_180x360_aave_2002-2003
forsyth     e3sm    4 regular_m 25198126 PD   Priority       0:00      30:00 climo_atm_monthly_diurnal_8xdaily_180x360_aave_2000-2001
forsyth     e3sm    4 regular_m 25198125 PD   Priority       0:00      30:00 climo_atm_monthly_180x360_aave_2002-2003
forsyth     e3sm    4 regular_m 25198124 PD   Priority       0:00      30:00 climo_atm_monthly_180x360_aave_2000-2001
```

</details>

zppy is technically finished once it submits all the jobs to the scheduler.
But usually we refer to zppy being done when all those jobs finish.
Once they're finished, we can examine the output.

# Reviewing zppy's output
```
# `cd` into the output directory from the cfg
$ cd /global/cfs/cdirs/e3sm/forsyth/E3SM-tutorial-v3/extendedOutput.v3.LR.historical_0101

# zppy puts output in the `post` directory
$ cd post
$ ls
# This directory has analysis, atm, lnd, ocn subdirectories.
# There is also the scripts directory, which is where most of the zppy-generated files live.

$ cd scripts
$ ls
# There are primarily four types of files here.
# 1) .status -- they tell you the status of a zppy job.
# OK -- successful
# WAITING -- waiting to run. This could be because of a dependency or simply waiting for queue time.
# RUNNING -- currently running
# ERROR -- the batch job errored out
# 2) .o -- they log the output from the batch jobs submitted by zppy
# These are where to look when debugging.
# 3) .settings -- they list how every single zppy parameter was defined for the corresponding job.
# These can be extremely useful if something doesn't seem right in the .o file.
# Perhaps you simply set a parameter wrong!
# 4) .bash -- these are the actual scripts zppy ran
# You can modify these files manually and rerun them with `sbatch <file-name>.bash`.

# You can look for status files that didn't finish successfully by running:
$ grep -v "OK" *status
# Running that here gives no output, so it looks like all our jobs finished successfully!
```

We can also review visual output on the web server.
The `www` from our `cfg` was: `/global/cfs/cdirs/e3sm/www/forsyth/E3SM-tutorial`
That corresponds to this web address: https://portal.nersc.gov/cfs/e3sm/forsyth/E3SM-tutorial. So,
https://portal.nersc.gov/cfs/e3sm/forsyth/E3SM-tutorial/extendedOutput.v3.LR.historical_0101 brings us to our output.
We have visual output for `e3sm_diags`, `mpas_analysis`, `global_time_series`, `ilamb`:

- https://portal.nersc.gov/cfs/e3sm/forsyth/E3SM-tutorial/extendedOutput.v3.LR.historical_0101/e3sm_diags/atm_monthly_180x360_aave/model_vs_obs_2000-2001/viewer/
- https://portal.nersc.gov/cfs/e3sm/forsyth/E3SM-tutorial/extendedOutput.v3.LR.historical_0101/e3sm_diags/atm_monthly_180x360_aave/model_vs_obs_2002-2003/viewer/
- https://portal.nersc.gov/cfs/e3sm/forsyth/E3SM-tutorial/extendedOutput.v3.LR.historical_0101/mpas_analysis/ts_2000-2004_climo_2000-2004/
- https://portal.nersc.gov/cfs/e3sm/forsyth/E3SM-tutorial/extendedOutput.v3.LR.historical_0101/global_time_series/global_time_series_2000-2004_results/v3.LR.historical_0101_glb_original.pdf
- https://portal.nersc.gov/cfs/e3sm/forsyth/E3SM-tutorial/extendedOutput.v3.LR.historical_0101/ilamb/180x360_aave_2000-2001/
- https://portal.nersc.gov/cfs/e3sm/forsyth/E3SM-tutorial/extendedOutput.v3.LR.historical_0101/ilamb/180x360_aave_2002-2003/
