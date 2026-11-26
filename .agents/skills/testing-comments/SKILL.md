---
name: testing-comments
description: Write a Testing comment on a pull request, recording what was run and what the results were. Use after running zppy, its integration tests or image checks for a pull request.
---

# Testing comments

What you ran, where, and whether it passed.

- Leave out anything CI already shows, such as the unit tests or pre-commit passing. If you ran nothing that CI does not, post no Testing comment.
- Name the test or cfg, the machine and the environment, for example the E3SM-Unified version or a dev environment. One sentence.
- Give the output directory or the expected results you compared against.
- Say the result: which `.status` files were not `OK`, whether the images matched.
- Say whether expected results, for example those of `test_bash_generation.py`, need updating once this merges.
- Use a table only when there are several runs to compare. A planned run that could not run stays in, saying why.
- Name the job that failed or differed. Say what caused it only if you checked; otherwise say the cause is not known.
- Long output, logs and paths beyond the one that matters go in a `<details>` fold, not above it.
- Do not restate in prose what a table or a pasted result already shows.
- Failures unrelated to the branch go under their own heading at the end.

## Length

Aim for what colleagues wrote before agents did. Comments reporting test results run 54 words at the median and 112 at the seventy-fifth percentile, not counting code blocks and folded details. Past that, cut.

These figures come from `zppy` pull requests merged in 2023 and 2024. Use them as they are; there is no need to measure again.

## Enough

The result, pasted, and stop (#512):

> I tested this on a mpas-analysis run that ended up here:
> https://web.lcrc.anl.gov/public/e3sm/diagnostic_output/ac.xylar/zppy/20230905.G-test.SOwISC12to60E3r1.anvil/mpas_analysis/ts_0001-0030_climo_0021-0030/
> The URL printed at submission with this fix is:
> ```
> URL: https://web.lcrc.anl.gov/public/e3sm/diagnostic_output/ac.xylar/zppy/20230905.G-test.SOwISC12to60E3r1.anvil/mpas_analysis
> ```
> so I think things are working as expected now.

A pass, with a cause that is not known (#615):

> The simultaneous tests pass when different subdirectories are used. I'm still not sure about the `NetCDF: HDF error` error specifically but if it comes up again, I'll re-open #613.

## Too much

A recent agent-written Testing comment said only what CI had already shown:

> I ran `pytest tests/test_*.py` locally in a zppy dev environment with Python 3.14: 169 passed, including the 21 new tests. Regenerating the snapshots reproduces them exactly.

It was deleted. The ones kept on the pull requests that followed say only what CI cannot: that the new regression test fails without the fix, and whether expected results on Chrysalis need updating.
