---
name: pr-descriptions
description: Write or update a pull request description. Use when opening a pull request or editing its body.
---

# Pull request descriptions

The reader is deciding whether to review.

- What changed and why, in a few sentences. Not how.
- Anything needing a reviewer decision goes in its own short list near the top, never mid-paragraph.
- A list of changed behaviours is fine. A trace of the mechanism is not.
- No commit list. No testing; that goes in a separate `Testing` comment.
- Link the issue or upstream pull request that gives context.
- Several fixes usually means several pull requests.
- Write in the template's Summary section, and leave its checklists for the developer to tick.

## Length

Aim for what colleagues wrote before agents did. Not counting the template, `zppy` descriptions run 7 words at the median, 14 at the seventy-fifth percentile, 40 at the ninetieth, and 213 at the longest. Past the ninetieth percentile, cut. The first draft of a recent agent-written description ran 408 words, nearly twice the longest a colleague has written.

These figures come from `zppy` pull requests merged in 2023 and 2024. Use them as they are; there is no need to measure again.

## Enough

A fix, stated and done (#547):

> Typical E3SMv3 WCYCL and CRYO configurations will not have the output necessary to run waves and eddy kinetic energy (EKE) analysis. It should be turned off to prevent confusing (though not fatal) errors in the setup stage of an MPAS-Analysis run.

A follow-up, linking what it follows (#460):

> Follow up to #459 -- if a plot only uses `glb` data, with no option for hemispheric plotting, then it should not be plotted on the hemispheric time series.

## Too much

That 408-word draft walked through what its tests compare and check, listed five bugs for later pull requests to fix, and added notes for reviewers like this one:

> The snapshots are excluded from the pre-commit whitespace and end-of-file hooks, because Jinja drops each script's final newline and the snapshots must match the rendered scripts exactly.

None of it helps someone decide whether to review, and the reason was already in the commit message, where it belongs. The rewrite runs about 100 words.
