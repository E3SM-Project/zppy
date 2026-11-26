---
name: design-documents
description: Write or revise a design document. Use when proposing a new capability or a reorganization, not when fixing a bug.
---

# Design documents

Long is fine. A design document is scanned and returned to, not read straight through. What must be scannable is the specification.

- Normative statements come first in a section and stand alone. Rationale goes in a marked block below, which a reader can skip.
- Rejected alternatives and superseded drafts go in one `Decisions` section, cited from the places they affect. Never re-argued in place.
- A principle is stated once. Later sections cite it by name.
- Do not pre-empt objections. Drop "worth noting", "not an accident", "deliberately", "this is not a stylistic preference". State the decision and let it stand.
- Open questions go at the top or in their own section, never mid-paragraph.
- Requirements describe what `zppy` must do for its users, not technical software issues.

## Calibration

`zppy` has no design documents yet; ask the developer where a new one should go. Aim for twenty words per sentence and none of the hedging phrases above.

## Enough

From the shared-steps design document in `E3SM-Project/polaris`. The heading states the requirement, the body is one normative sentence, and some requirements need no body at all.

> ### Requirement: Shared steps are run once.
>
> Shared steps should be run once per invocation of `polaris serial` or `polaris run`.
>
> ### Requirement: Shared steps are run before steps that depend on their output.
>
> ### Requirement: The output of shared steps may be used by multiple tasks.
>
> A step may only be shared across multiple tasks if its output would be identical for each task.

Seven requirements in that document take about 150 words between them.
