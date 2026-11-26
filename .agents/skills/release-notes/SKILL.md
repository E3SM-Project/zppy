---
name: release-notes
description: Write or revise the notes for a zppy GitHub release. Use when preparing a release or rewriting an existing release's description.
---

# Release notes

The reader uses `zppy` and wants to know what is new and what will break when they upgrade. Every pull request since the previous release appears once.

## Structure

The [release process](https://docs.e3sm.org/zppy/_build/html/main/dev_guide/releases/production_releases.html) asks for two sections:

```
## Summary of changes

<1 to 3 sentences: what this release is about, and the zppy-interfaces version it is designed for>

## Full list of changes

Incompatible API changes (user-facing)
- #N: <what changed>

Features (user-facing)
Small Improvements (user-facing)
Bug Fixes (user-facing)
Documentation/examples only (user-facing)
Tests only
DevOps
Version Updating
```

Write `- None` under Incompatible API changes when there are none. Drop any other empty category.

## Gathering

- Take the list of pull requests from GitHub, not from merge commits: `gh api repos/E3SM-Project/zppy/releases/generate-notes -f tag_name=<tag> -f previous_tag_name=<prev> -q .body`.
- Read each pull request's title, labels and description with `gh pr view`.
- Find renamed, removed or re-defaulted parameters with `git diff <prev> <tag> -- zppy/defaults`.
- Take dependency versions from `conda/dev.yml` and `pyproject.toml` at the two tags, not from titles.

## Sorting

- Incompatible API changes: renamed or removed cfg parameters, changed defaults, changed paths under `output` or `www`, anything a user's cfg or scripts will trip over. A pull request can appear both here and in another category.
- Bug fixes say what was wrong, not how it was fixed. Flag a fix that changes output.
- Release candidates and the final version bump go under Version Updating.

## Writing

- One line per bullet and per paragraph; GitHub release notes are not hard-wrapped.
- Rewrite titles as what changed for the user, not what the pull request did: "Add ENSO diagnostics to `pcmdi_diags`", not "Zppy pcmdi enhancement".
- End with the signature from `AGENTS.md`.

## Checking

Every number from the generated notes must appear in the draft:

```
gh api repos/E3SM-Project/zppy/releases/generate-notes \
    -f tag_name=<tag> -f previous_tag_name=<prev> -q .body \
  | grep -o 'pull/[0-9]*' | cut -d/ -f2 | sort -nu \
  | while read n; do grep -q "#$n\b" notes.md || echo "missing #$n"; done
```

Show the draft to the developer before posting it with `gh release edit <tag> --notes-file notes.md`.

## Example

From the 3.3.0 notes:

> `zppy v3.3.0` is designed for use with `zppy-interfaces v0.3.0`. It introduces several important upgrades including integrating `zppy` with SimBoard, adding ENSO support to `pcmdi_diags`, and enabling EAMxx support across several tasks.

> Bug Fixes (user-facing)
> - #898: Fix missing last ts dependency when ts_num_years = 1
> - #901: Derive the EAMxx source vertical grid from whichever coefficients exist
> - #903: mpas_analysis: ignore stale taskProgress.log entries on rerun
