---
name: review-comments
description: Write a review comment, review findings, or a reply to review feedback on a GitHub pull request. Use when reviewing code, reporting what testing someone else's branch turned up, or answering a reviewer's question.
---

# Review comments

The reader is deciding what to change. The reader also wants justification for code changes that are conceptually substantive, either in the pull request, in docstrings near the changes, or in the documentation.

- Put each finding as an inline comment on the line it concerns, one point each. That is where colleagues put them, and it is why their review bodies are short.
- The review body summarizes: what you ran, and the verdict. Two or three sentences.
- Use a list in the body only for requests that span files.
- No section on what already works. One line for all of it, if any.
- Say what you could not check.

## Length

Aim for what colleagues wrote before agents did. Review bodies run 26 words at the median, 110 at the ninetieth percentile, and 114 at the longest. Inline comments run 21 words at the median and 71 at the ninetieth percentile. Past 110 words for a body, or 70 for an inline comment, cut.

These figures come from `zppy` pull requests merged in 2023 and 2024. Use them as they are; there is no need to measure again.

## Enough

Inline, one point and a suggestion (#381):

> A call like `mache sync diags from chrysalis` should take care of copying the files. But better yet ping me to do it when you're ready.

Inline, answering a question with where to look (#400):

> `climo` specifically you do need to reset the var list (notice `# NOTE: always overrides value in [default]` in `default.ini`), but I don't think that's the case with `ts`.

In the body, a request that spans files (#400):

> One more thing, this PR should add `nco >=5.2.3` as an explicit dependency to `dev.yml` and `meta.yaml`. Right now, zppy is making explicit calls to `ncclimo` but it's only getting `nco` because other tools depend on it, which isn't the "right" way to handle dependencies.

In the body, what was run and the verdict (#497):

> The `complete_run` test passes on Perlmutter and Compy still, so I think this ready to merge.

## Too much

A real agent-written review on `E3SM-Project/polaris` spent its first 444 words on "How this was reviewed", "What the previous review asked for" and four paragraphs of "What works", then traced each finding's mechanism:

> It is static: computed once in the `MOC` constructor from `NumBins`, `MinLat` and `MaxLat`, and never updated. But it is attached to the output streams with `addField()` like any other field, so every reduction in every file carries a copy of the same 61 numbers.
