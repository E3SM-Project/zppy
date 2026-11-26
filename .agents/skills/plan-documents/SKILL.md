---
name: plan-documents
description: Write a plan for work not yet started, for a colleague or the user to approve before implementation begins.
---

# Plan documents

The reader is deciding whether to let you proceed.

- Open questions and anything needing a decision go at the top.
- The steps, in order, one line each.
- Do not justify each step. Do not list the files you will touch. Do not restate the codebase back.
- If a step needs a paragraph to explain, it belongs in a design document.

## Enough

Plans are approved in conversation rather than committed, so there is no human example in this repository to copy. The following is constructed.

> **Open:** should the hard-coded MPAS-Analysis `baseDirectory` be removed now or as part of the template reorganization?
>
> 1. Add snapshot tests of the scripts `zppy` renders.
> 2. Fix the bugs they expose, one pull request each.
> 3. Move the E3SM Diags and MPAS-Analysis config files into their own templates.
> 4. Share one job loop across the task modules.
