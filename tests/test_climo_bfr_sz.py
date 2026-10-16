import os
from typing import Any, Dict

import jinja2
import pytest

# Test the template in this working tree, not that of an installed zppy.
TEMPLATE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "zppy", "templates"
)

BASE_PARAMETERS: Dict[str, Any] = {
    "case": "case_name",
    "climo_jobs": 0,
    "exclude": False,
    "fml_nm": "eamxx",
    "input": "/path/to/input",
    "input_files": "3ha_ne30pg2.AVERAGE.nhours_x3",
    "input_subdir": "run",
    "mapping_file": "map.nc",
    "parallel": "mpi",
    "prc_typ": "eamxx",
    "prefix": "climo_atm_1850-1851",
    "scriptDir": "/path/to/scripts",
    "vars": "precip_liq_surf_mass_flux,precip_ice_surf_mass_flux",
    "yr_end": 1851,
    "yr_start": 1850,
}


def render(machine: str, frequency: str, prc_typ: str = "eamxx") -> str:
    parameters = dict(
        BASE_PARAMETERS, machine=machine, frequency=frequency, prc_typ=prc_typ
    )
    template_env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(searchpath=TEMPLATE_DIR)
    )
    # Only the ncclimo call for the given frequency is rendered.
    return template_env.get_template("climo.bash").render(**parameters)


@pytest.mark.parametrize("machine", ["pm-cpu", "pm-gpu"])
def test_eamxx_diurnal_climo_uses_small_buffer_on_perlmutter(machine):
    assert "--bfr_sz=262144" in render(machine, "diurnal_8xdaily")


@pytest.mark.parametrize("machine", ["chrysalis", "compy", "anvil", "dane"])
def test_diurnal_climo_keeps_ncclimo_default_elsewhere(machine):
    assert "--bfr_sz" not in render(machine, "diurnal_8xdaily")


@pytest.mark.parametrize("machine", ["pm-cpu", "pm-gpu"])
def test_monthly_climo_keeps_ncclimo_default(machine):
    assert "--bfr_sz" not in render(machine, "monthly")


@pytest.mark.parametrize("machine", ["pm-cpu", "pm-gpu"])
def test_eam_diurnal_climo_keeps_ncclimo_default(machine):
    assert "--bfr_sz" not in render(machine, "diurnal_8xdaily", prc_typ="eam")
