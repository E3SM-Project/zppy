"""Check that no task generates jobs for years after `last_year`."""

import re

from tests.rendering.scenarios import (
    SCENARIOS_BY_NAME,
    bash_scripts,
    read_dependencies,
    render_scenario,
)

YEARS = re.compile(r"(\d{4})-(\d{4})")


def test_no_jobs_after_last_year() -> None:
    scenario = SCENARIOS_BY_NAME["last_year_chrysalis"]
    assert scenario.last_year is not None
    files = render_scenario(scenario)
    too_late = [
        name
        for name in bash_scripts(files)
        if any(int(end) > scenario.last_year for _, end in YEARS.findall(name))
    ]
    assert too_late == []
    # Every task in the scenario should still run for the years it can.
    jobs = read_dependencies(files)
    for task in ["climo_", "ts_", "e3sm_to_cmip_", "ilamb_", "livvkit_"]:
        assert any(job.startswith(task) for job in jobs), f"no {task} job"
