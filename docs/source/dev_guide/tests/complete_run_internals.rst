.. _complete-run-internals:

***************************************
Inside the complete run test
***************************************

:ref:`automated-testing-zppy` covers how to run and configure the complete run
test. This page covers the other side: how ``tests/complete_run/`` and
``tests/integration/weekly_cfgs.py`` are built, and why, for anyone changing
that code rather than just invoking it.

It assumes you have read :ref:`automated-testing-zppy` and
:ref:`manually-testing-zppy` already -- this page explains the machinery, not
the workflow the machinery replaced.

One subprocess seam
====================

Every external command the complete run issues -- ``git``, ``conda``,
``sbatch``, ``squeue``, ``zppy`` itself -- goes through a single function,
``commands.run_command`` (``run_command_status`` is a variant that returns the
exit code instead of raising). No other module in the package calls
:mod:`subprocess` directly.

That is a testing decision, not a style preference. It means a unit test for,
say, ``worktrees.create_checkout`` can monkeypatch ``run_command`` and assert
on the argument lists it was called with, instead of mocking
:mod:`subprocess` inside every module that shells out. Every
``test_complete_run_*.py`` file does exactly this: replace ``run_command``
with a recording stub, call the function under test, and assert on the
command lines it produced. ``CommandError`` carries the command, its exit
code, and its output, so a failure deep in a solve or a submission does not
need to be reproduced to be diagnosed -- it is printed and raised at the one
place that invoked the subprocess.

The pipeline: stages and ``status.json``
=========================================

``automation.py`` is the entry point. It does not run the test as one long
function; it runs it as an explicit state machine over six stages --
``prepare``, ``generate``, ``submit``, ``bundles``, ``validate``, ``report``
-- defined as the ``STAGES`` tuple, plus a set of terminal failure states
(``FAILURE_STAGES``: ``prepare_failed``, ``submission_failed``,
``dependency_never_satisfied``, ``timed_out``, ``validation_failed``) that a
run can land in instead of progressing.

After every stage, the run's current stage and accumulated state are written
to ``status.json`` under the run directory (see :mod:`tests.complete_run.layout`
for where that is). This buys two things:

* ``--start-stage`` can resume a run from any stage without repeating the
  ones before it, reading back whatever ``prepare`` or ``submit`` recorded
  (resolved SHAs, environment paths, job IDs) rather than resolving them
  again.
* A run that crashes, times out, or is killed still has a ``status.json`` on
  disk, so ``report.py`` can always render *something* -- see
  `Reports that cannot fail`_ below.

Each stage is a plain function taking and returning the accumulated run
state; ``automation.py`` is mostly the loop that calls them in order, catches
the exception a stage can raise, maps it onto the right failure stage, and
calls ``report`` regardless of whether the loop ended in a pass, a failure,
or an exception.

Everything that actually exercises zppy -- cfg generation, ``zppy -c``, and
every test that runs against it -- executes inside the environment built from
the commit under test (via ``conda run``), never in whatever environment
launched ``automation.py``. The launching environment only ever needs Python
and enough to drive the orchestration itself (``mache``, ``pytest`` for the
package's own unit tests). This is why ``prepare`` builds environments before
anything else runs.

Why worktrees, not clones
==========================

:mod:`tests.complete_run.worktrees` exists because of two constraints that
come directly from this being an automated, unattended test:

* It must never modify a developer's checkout -- no branch switches, no
  commits, nothing left on a different revision than the developer left it
  on.
* It must test one *immutable* revision, even if a branch moves while jobs
  are still queued on SLURM. A run that resolves ``main`` to a SHA at
  ``prepare`` and tests that SHA is not exposed to a merge landing an hour
  later.

Both follow from the same mechanism: ``resolve_sha`` turns a branch name into
a commit hash once, and ``add_worktree`` checks that hash out, detached, into
a throwaway directory under scratch (``create_checkout`` combines the two and
also records the remote and short SHA for the manifest). ``add_worktree``
refuses to reuse an existing path rather than silently overwriting it --
see ``test_add_worktree_refuses_to_reuse_an_existing_path`` -- because a
leftover directory from an earlier failed run is a sign something is wrong,
not something to paper over.

``resolve_sha`` tries ``fetch`` against the named remote first and only falls
back to resolving the ref locally if the fetch fails (for example, an
unpushed local branch someone is testing before opening a PR); either way it
returns which path was taken, which ends up in the manifest as the
repository's ``remote`` field.

``remove_worktree`` is deliberately built to never raise: cleanup failing
(a dirty worktree, a filesystem hiccup) must never mask the run's actual
pass/fail outcome, which is why it is called from a context where its result
is discarded rather than propagated.

Worktrees for a run that did not pass are kept, not removed, so there is
always something on disk to inspect afterward -- see `If a run does not
pass`_ in :ref:`automated-testing-zppy`.

Three kinds of environment
============================

:mod:`tests.complete_run.environments` builds one conda environment per
repository under test, and the choice of *how* to build it is per-repository,
not global. ``ENV_TYPES`` names three modes (``ENV_TYPE_DEV``,
``ENV_TYPE_BASELINE``, ``ENV_TYPE_UNIFIED``):

``dev``
    Solve fresh from that repository's own ``dev.yml``, from the worktree
    created in `Why worktrees, not clones`_. This is the default, and it is
    the only mode that exercises the floating version constraints a
    ``dev.yml`` carries -- a pin that moved is a dependency regression this
    mode is built to catch.

``baseline``
    Reconstruct the exact environment a previous (baseline) run used, from
    the YAML export that run wrote. This is what lets a comparison hold
    dependencies fixed while a code branch changes, so an image difference
    can be attributed to the branch rather than to a new dependency solve.
    It only works if the baseline itself exported that YAML; a baseline
    produced before exports existed cannot be reconstructed, and
    ``resolve_solver`` says so explicitly rather than quietly solving fresh
    instead and silently invalidating the comparison.

``unified``
    Skip building a dev environment at all and use the released
    E3SM-Unified environment. Several tasks (``livvkit``, ``climo``, ``ts``,
    ``tc_analysis``, ``ilamb``) always run this way; it is also the fast
    path for a repository you are not actively testing.

``environments_by_task`` maps each zppy task to the ``Environment`` that
should run it, and ``environment_from_status`` reconstructs an
``Environment`` from a resumed run's recorded state rather than rebuilding
it -- part of why ``--start-stage`` can skip straight past ``prepare``.
Every environment this module builds, in any mode, is exported to
``environments/<repo>.yml`` in the run's results -- that export is what makes
``baseline`` mode possible for a later run.

Machine and repository parameters
====================================

:mod:`tests.complete_run.params` holds the things that differ by machine
(``MachineProfile``: SLURM partition/qos/constraint, module commands) and by
repository (``REPO_SPECS`` / ``REPO_SPECS_BY_NAME``: the five repositories'
default branches, remotes, and conda environment files), plus the defaults
for which cfgs and tasks run when nothing is passed on the command line.

It re-exports ``WEEKLY_CFGS`` and ``case_name_for_cfg`` from
``tests.integration.weekly_cfgs`` (see the next section) rather than
defining its own notion of which cfgs exist, so there is exactly one table
anywhere in the codebase that says that.

The weekly cfg table
=======================

``tests/integration/weekly_cfgs.py`` is new infrastructure, not just new
data. Before it, which weekly cfgs existed, which case each ran against, and
which tasks' plots the image checker compared were three separate things
that had to be kept in sync by hand across cfg generation, the test driver,
and ``test_images.py``. A task a cfg ran but nobody added to an image-check
list was silently never compared -- which is exactly how ``livvkit``'s
``weekly_comprehensive_v3`` plots and ``pcmdi_diags``'s legacy 3.1.0 plots
went unchecked before this change (see the note in
:ref:`automated-testing-zppy`).

The module defines one frozen dataclass, ``WeeklyCfg`` (name, case,
image-checked tasks), and one tuple of them, ``WEEKLY_CFGS``. Cfg generation,
``tests.complete_run.params``, and ``test_images.py`` all read this same
tuple. ``tests/test_weekly_cfgs.py`` is what actually keeps it honest: it
asserts that the cfg templates on disk and the table agree in both
directions -- no template without a table entry, and no table entry naming a
plotting task the template doesn't produce (``test_every_plotting_task_a_cfg_runs_is_image_checked``)
-- so an engineer adding a cfg without updating the table gets a failing
unit test instead of a silent gap discovered weeks later in a diff viewer.

Where results live, and why nothing is ever copied
=====================================================

:mod:`tests.complete_run.layout` defines the directory structure (see the
tree in :ref:`automated-testing-zppy`) and, more importantly, the rule
behind it: every run gets its own directory under a shared root, and that
directory is never modified again once the run finishes. Promotion (see
`Promotion is a pointer, not a copy`_) and comparison both follow from that
one invariant -- there is nothing to accidentally overwrite, and a baseline
*is* a specific run directory, not a snapshot someone made of one.

Large, disposable data -- zppy's post-processing output, the worktrees --
deliberately lives outside this tree, on scratch, because it is large and
worthless once a run is validated. ``layout.py`` is also what
``validate.py`` calls to copy the handful of small artifacts a baseline
actually needs (bash and settings baselines, bundle scripts) out of scratch
and into the permanent run directory before scratch can purge them.

Submitting and waiting on SLURM
==================================

:mod:`tests.complete_run.slurm` is intentionally small: submit, then poll.
``queued_job_ids`` and ``wait_for_user_jobs`` poll ``squeue`` until every job
of interest has left the set of non-terminal states
(``TERMINAL_STATE_PREFIXES`` covers ``COMPLETED``, ``FAILED``,
``CANCELLED``, ``TIMEOUT``, and their prefixes, since SLURM reports states
like ``CANCELLED by <uid>``). It does not interpret *why* a job ended in a
given state -- that is left entirely to `Validation: three checks, in order`_,
which reads the job's own status files. ``slurm.py``'s only job is knowing
when the queue has drained.

Validation: three checks, in order
=====================================

:mod:`tests.complete_run.validate` is where "the jobs ran" becomes "the run
passed." It performs exactly three checks, in this order, because each one
only means something once the one before it has passed:

1. Every job's own status files report ``OK``. If a job never finished
   cleanly, nothing downstream of it is trustworthy, so this check runs
   first.
2. The integration test suite (``INTEGRATION_TEST_FILES`` from ``params.py``,
   in the documented order) passes.
3. The image checker -- submitted as its own batch job, since it needs a
   compute node that the orchestration process itself does not hold --
   finds no differences that need review.

A failure at any step produces one of the ``FAILURE_STAGES`` named earlier,
and validation stops there rather than continuing to check things whose
results would not mean anything yet.

Attributing image differences to the environment
====================================================

:mod:`tests.complete_run.envdiff` answers a single question: *did the
environment change between this run and the baseline it is being compared
against?* That question has to be answered before an image difference can be
interpreted at all, because the same pixel difference means two different
things depending on the answer:

* If the environment is identical, a difference is attributable to the code
  under test.
* If the environment changed on purpose (a fresh ``dev`` solve, see `Three
  kinds of environment`_), the difference may simply be a dependency that
  moved -- here the *package list* is the finding, not the plot.
* If the run asked to reproduce the baseline's environment and it still
  came out different, the reproduction did not take, and no conclusion about
  the code can be drawn from the images until that is fixed.

It works by parsing ``conda env export`` output into package lists and
diffing them, deliberately ignoring the ``name:`` and ``prefix:`` fields --
every run's environment has a unique name and path by construction, so
comparing those would bury every real package difference under noise that is
never meaningful. For a baseline that ran under E3SM-Unified (no per-run
export to diff against), it falls back to the ``conda list`` captured in that
baseline's ``env_descriptions/<task>.txt`` and compares by version only.

This diff is not just a validation detail -- it is surfaced to a human
reviewer twice: once per task in the diff viewer (see `A self-contained
viewer for image diffs`_) and once in the Markdown report's own
``## Environment`` section, both ahead of the actual results, because it
changes how everything below should be read.

Provenance: what a baseline is allowed to assume about itself
=================================================================

:mod:`tests.complete_run.provenance` writes two things:

``env_description.txt``, one per task
    This is copied alongside that task's output and, when a run is
    promoted, becomes part of the expected-results directory future runs
    compare against. A later run's ``envdiff`` reads its ``Generated:`` line
    back out to know how old a baseline's environment is. That makes this
    file's line format a **contract with every already-promoted baseline on
    disk**: reordering or renaming lines in it breaks ``envdiff`` for every
    existing baseline, not just future ones, which is why the module's
    docstring calls this out explicitly.

``manifest.json``, one per run
    The machine-readable record of exactly what a run tested: resolved SHAs,
    which environment mode each repository used, which cfgs and tasks were
    selected. ``promote.py`` reads this back to decide whether a run is even
    eligible to become a baseline (see below) -- a promotion is a judgment
    about a specific manifest, not about whatever is currently on a branch.

Reports that cannot fail
===========================

:mod:`tests.complete_run.report` renders ``complete-run-report.json`` (for
other tooling) and ``complete-run-report.md`` (pasted into the weekly
testing log) from whatever is in ``status.json``, ``manifest.json``, and the
validation results at the point the run stopped. Its guiding rule is in its
own docstring: rendering must never raise because an input is missing,
because the run that died before producing some artifact is exactly the run
whose report a maintainer most needs to read. Every lookup into the
accumulated state is written to degrade to "not available" rather than
propagate a ``KeyError`` up through ``automation.py``'s final step.

A self-contained viewer for image diffs
==========================================

The image checker already writes ``<n>_actual.png``, ``<n>_expected.png``,
``<n>_diff.png``, and ``image_scores.json`` into a web-served directory --
that part is not new. What :mod:`tests.complete_run.viewer` adds is an
``index.html`` rendered beside them that turns that into something a
reviewer can actually use: each changed plot next to its baseline and diff,
worst severity first, filterable.

It is written to be fully self-contained -- no external stylesheet or
script tag -- because the portal that serves the run directory serves static
files only; anything the page needed from elsewhere simply would not load.
This is also why the page leads with the environment-diff panel described in
`Attributing image differences to the environment`_, opened by default when
a reproduction did not take: that is the one piece of context that changes
how a reviewer should read every image below it.

Promotion is a pointer, not a copy
=====================================

A run directory, once it exists, already *is* valid baseline material -- its
``www/`` tree holds the plots, its ``image_lists`` and ``settings``
directories describe what it produced. :mod:`tests.complete_run.promote`
therefore never copies anything: promoting a run means pointing
``baselines/latest-<channel>`` at that run's directory. That makes promotion
atomic and instant regardless of how many images a run produced, and it
means the previous baseline is simply the run it used to point at --
rolling back is promoting that run again, not restoring anything from a
backup.

Because nothing is copied, ``promote.py`` has to be strict about what it
will point a channel at: it reads the candidate run's own report (did it
pass?) and manifest (did it come from ``main``, not a feature branch?)
rather than trusting a flag on the command line, so a promotion cannot claim
something the run itself does not support. ``--allow-failed`` exists for the
legitimate case where a dependency improved a plot on purpose, but it is a
deliberate override of that check, not a different code path around it --
and it is meant to follow reading the diff viewer, not replace it.

Release snapshots (``--channel unified_1.13.0``) are handled the same way:
another named pointer, not another copy of the run.

Pruning (``promote.py prune``) deletes run directories that no channel
currently points at, oldest first, and reports what it would delete before
``--delete`` makes it permanent -- consistent with every run directory being
immutable right up until it is removed entirely.

Running unattended: the scheduled controller
===============================================

``complete-run-controller.sh`` is deliberately thin: it sources an
operator-specific config file (``complete-run.config.env.template``, which
is meant to be copied outside the repository, since it names machine
accounts and filesystem paths), takes a lock for the duration of the run so a
second cron firing exits immediately instead of overlapping a still-running
one, and then calls ``tests.complete_run.automation`` with that
configuration. All of the actual orchestration logic stays in the Python
package described above; the shell script's only job is to make the Python
entry point safe to invoke unattended from cron.

``complete-run.crontab.template`` installs a weekly Monday firing. The
``WEEK_PARITY`` setting (``any`` / ``even`` / ``odd``) exists because plain
cron cannot express "every second Monday" across month boundaries on its
own -- gating down to biweekly is done in the controller's own logic, not by
trying to encode it in the crontab syntax. ``tests/test_complete_run_schedule.py``
checks both files statically (for example, that the controller actually
requires each configuration variable it depends on) rather than by running
cron, since the whole point of this layer is code that runs unattended where
a mistake is otherwise discovered a week later by a run that silently never
happened.

How the generated cfgs stay out of hand edits
================================================

Before this change, generating a test cfg meant editing
``TEST_SPECIFICS`` in ``tests/integration/utils.py`` by hand, or rewriting
it with regex from a driver script. ``tests.integration.utils.build_specifics``
replaces both: it takes keyword overrides and returns a settings dict with
``TEST_SPECIFICS``'s defaults filled in underneath whatever was passed,
instead of mutating the module-level dict in place.
``tests/test_complete_run_cfg_generation.py`` checks both ends of that: that
calling it with nothing reproduces ``TEST_SPECIFICS`` exactly, and that
passing one field overrides only that field. ``automation.py`` calls this
directly; a one-off manual run can still call the same function, or still
edit ``TEST_SPECIFICS`` by hand and run the module directly, since
``build_specifics`` is additive rather than a replacement for that older
path.

Testing this package
=======================

Every module above has a matching ``tests/test_complete_run_<module>.py``,
built around the subprocess seam described in `One subprocess seam`_:
replace ``run_command`` with a stub that records its arguments (and, where
needed, returns canned output or raises ``CommandError``), call the function
under test, and assert on what it would have run or what it returned. None
of these tests touch a real git repository, conda installation, or SLURM
queue.

``tests/test_weekly_cfgs.py`` is the exception -- it is a consistency check
on data (the cfg table against the template files on disk) rather than a
test of a function's behavior, for the reasons covered in `The weekly cfg
table`_.

The CI change in ``.github/workflows/build_workflow.yml`` that runs
``tests/images`` alongside the existing ``tests/test_*.py`` is part of the
same picture: the complete run's ``validate`` stage relies on the image
checker to produce a trustworthy verdict, so the image checker's own unit
tests have to pass on every pull request, not just get exercised incidentally
during a weekly run.
