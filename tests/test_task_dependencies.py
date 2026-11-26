"""Check the dependencies of the jobs that zppy generates."""

import re
from typing import List, Optional, Tuple

import pytest

from tests.rendering.scenarios import (
    SCENARIOS,
    SCENARIOS_BY_NAME,
    Scenario,
    read_dependencies,
    render_scenario,
)

# Tasks whose jobs process one year set each and depend only on inputs for
# those years. (MPAS-Analysis jobs also depend on earlier MPAS-Analysis jobs,
# so they are not included.)
PER_YEAR_SET_TASKS = [
    "e3sm_diags_",
    "e3sm_to_cmip_",
    "ilamb_",
    "livvkit_",
    "pcmdi_diags_",
]
YEARS = re.compile(r"(\d{4})-(\d{4})")


def _first_years(name: str) -> Optional[Tuple[int, int]]:
    match = YEARS.search(name)
    if match is None:
        return None
    return int(match.group(1)), int(match.group(2))


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.name)
def test_jobs_depend_only_on_their_own_years(scenario: Scenario) -> None:
    dependencies = read_dependencies(render_scenario(scenario))
    failures: List[str] = []
    for job, job_dependencies in dependencies.items():
        if not any(job.startswith(task) for task in PER_YEAR_SET_TASKS):
            continue
        job_years = _first_years(job)
        if job_years is None:
            continue
        for dependency in job_dependencies:
            years = _first_years(dependency)
            if years is None:
                continue
            if not (job_years[0] <= years[0] and years[1] <= job_years[1]):
                failures.append(f"{job} depends on {dependency}")
    assert not failures, "\n".join(failures)


def test_comprehensive_scenario_has_several_year_sets_per_task() -> None:
    # The check above only means something for tasks with more than one
    # year set.
    jobs = read_dependencies(
        render_scenario(SCENARIOS_BY_NAME["comprehensive_chrysalis"])
    )
    for task in PER_YEAR_SET_TASKS:
        later = [job for job in jobs if job.startswith(task) and "_1987-1988" in job]
        assert later, f"no {task} job for a second year set"
