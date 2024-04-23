# zppy problem set

This problem set will help you learn more about zppy.
Try to solve the problem by looking through the
[documentation](https://docs.e3sm.org/zppy) and/or [discussion pages](https://github.com/E3SM-Project/zppy/discussions).

The problems are divided into use cases (try to write the abridged `cfg` to solve the problem) and
debugging (try to determine what's wrong with the given abrdiged `cfg`).

## Use cases

### Problem 1
Compare the simulation's diurnal precipitation from its first 5 years and its last 5 years.

<details>
<summary>Hints</summary>
What set do we need to run from E3SM Diags to do this? What variable do we need to process?

Figuring out how to do this problem will help if you want to compare output from two different models one day.
What feature of e3sm_diags would be useful for that?

What parameters does the "diurnal_cycle" set need? Look for it in comments in the [parameter list](https://docs.e3sm.org/zppy/_build/html/main/parameters.html)

What should the `run_type` parameter be set to?

What parameters does the "model_vs_model" need? Look for it in comments in the [parameter list](https://docs.e3sm.org/zppy/_build/html/main/parameters.html)
</details>

<details>
<summary>Solution</summary>

See `zppy_use_case1.cfg_abridged`.

</details>

### Problem 2
Check that zppy will generate 2-year PRECT climatologies for the 2000-2013 period,
and 5-year PRECT climatologies for the 2000-2014 period.
That is, check that zppy will launch 10 jobs total (7 2-year and 3 5-year climatologies) --
without actually launching the jobs.

<details>
<summary>Hints</summary>

Is there a [parameter](https://docs.e3sm.org/zppy/_build/html/main/parameters.html) that could help with this?

</details>

<details>
<summary>Solution</summary>

Set `dry_run` to True if you want to see what zppy will do, without actually launching batch jobs.

See `zppy_use_case2.cfg_abridged`.

</details>

### Problem 3
Let's say a new feature has just been merged in `e3sm_diags`,
but we really need this feature before it can be released as part of E3SM Unified.
What can we do?

<details>
<summary>Hints</summary>

Is there a [parameter](https://docs.e3sm.org/zppy/_build/html/main/parameters.html) that could help with this?

Could we create a [custom environment](https://docs.e3sm.org/e3sm_diags/_build/html/master/install.html#b-development-environment) for `e3sm_diags`?

</details>

<details>
<summary>Solutions</summary>

When `environment_commands` is left blank, the latest E3SM Unified environment will be used.
Alternatively, you can set this to be a different value.
This is very useful if you need to use a version of a package that hasn't been integrated into E3SM Unified yet.
To use a custom conda environment, you can set:
```
environment_commands="source <path to conda.sh>; conda activate <custom environment>"
```

See the [discussions page](https://github.com/E3SM-Project/zppy/discussions/570) for more information.

</details>

### Problem 4
Say the simulation data has been long-term archived on HPSS and exists no where else. 
Can we still post-process that data with zppy?

<details>
<summary>Hints</summary>

If a simulation has been long-term archived to HPSS, it must be case that it can be re-extracted from there.

What other tool in the E3SM Unified environment might be helpful here?

</details>

<details>
<summary>Solution</summary>

We can run `zstash extract` -- see the [zstash demo](https://github.com/E3SM-Project/zstash/blob/add-tutorial-materials/tutorial_materials/ztash_demo.md). Now, with the data locally, in our `cfg` we can simply set:
```
input = <path to extracted simulation output>
```
</details>

## Debugging

Note there is a [debugging guide](https://github.com/E3SM-Project/zppy/discussions/573) available.
While it is primarily for developers, users may also find it useful.

### Problem 1
See `zppy_debug1.cfg_abridged`.

The user's global time series task won't run.
Running `zppy` gives this message:
```
global_time_series_2000-2010
...skipping because of dependency status file missing
```
Why is this happening?

<details>
<summary>Hints</summary>

What parameter in the [parameter list](https://docs.e3sm.org/zppy/_build/html/main/parameters.html)
tells us the increments of the time series?

Does that value need to match up with something? Checking the [discussions page](https://github.com/E3SM-Project/zppy/discussions/366) might be helpful.

</details>

<details>
<summary>Solution</summary>

Change `ts_num_years = 5` to match the `atm_monthly_glb` overriding of `years`: we actually want `ts_num_years = 10`.

</details>

### Problem 2

See `zppy_debug2.cfg_abridged`.

After running `zppy`, the user runs `sq` (see aliases defined in the demo)
"NODE" lists 4, yet they clearly requested 2 nodes. Why?


<details>
<summary>Hints</summary>

Did we actually request 2 nodes? Can the [parameter list](https://docs.e3sm.org/zppy/_build/html/main/parameters.html) offer some insights to what's going on?

Search for the comment "NOTE: always overrides value in [default]" in the parameter list.

</details>

<details>
<summary>Solution</Summary>

In general, parameters don't have to be defined twice in a zppy cfg.
However, there are a few important exceptions.
These are noted with the "NOTE: always overrides value in [default]" comment in `default.ini`.
These are parameters defined multiple places throughout default.ini
Some tasks have typical default values, so in most use cases, the value overriding makes sense.

For example, in a typical use case, a user will probably have `nodes = 1` (as is the default in `default.ini`).
But often they'll want `nodes = 4` for the `[climo]` task.
Thus, it was decided that `[climo]`'s default would be 4 nodes.
This has the unfortunate side effect of `[climo]`'s default of 4 nodes overriding a `nodes` value in the user's own `cfg`.

See [this pull request](https://github.com/E3SM-Project/zppy/pull/204) for more discussion on this topic.

We just need to move `nodes = 2` to under `[[ atm_monthly_180x360_aave ]]` or under `[climo]`.

</details>
