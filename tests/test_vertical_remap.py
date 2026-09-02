import os
from typing import Any, Dict

import jinja2

# Test the templates in this working tree, not those of an installed zppy.
TEMPLATE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "zppy", "templates"
)

BASE_PARAMETERS: Dict[str, Any] = {
    "account": "",
    "case": "case_name",
    "cmip_metadata": "inclusions/e3sm_to_cmip/default_metadata.json",
    "cmip_plevdata": "/path/to/vrt_remap_plev19.nc",
    "cmip_vars": "ta",
    "cmor_tables_prefix": "/path/to/tables",
    "component": "atm",
    "dpf": 30,
    "environment_commands": "",
    "extra_vars": "ps",
    "frequency": "monthly",
    "grid": "180x360_aave",
    "input": "/path/to/input",
    "input_files": "AVERAGE.nmonths_x1",
    "input_subdir": "run",
    "interp_vars": "T_mid",
    "job_nbr": 1,
    "machine": "pm-cpu",
    "mapping_file": "map.nc",
    "nco_path": "",
    "nodes": 1,
    "output": "/path/to/output",
    "parallel": "",
    "partition": "",
    "prc_typ": "eamxx",
    "prefix": "ts_atm_1850-1851-0002",
    "qos": "",
    "scriptDir": "/path/to/scripts",
    "tpd": 1,
    "ts_grid": "180x360_aave",
    "vars": "T_mid",
    "vrt_in_file": "",
    "vrt_remap_file": "/path/to/vrt_remap_plev19.nc",
    "vrt_remap_vars": "T_mid",
    "walltime": "01:00:00",
    "yr_end": 1851,
    "yr_start": 1850,
    "ypf": 2,
}

DERIVATION = "ncks -O -v hyai,hybi,hyam,hybm"


def render(template_name: str, **overrides: Any) -> str:
    parameters = dict(BASE_PARAMETERS, **overrides)
    template_env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(searchpath=TEMPLATE_DIR)
    )
    return template_env.get_template(template_name).render(**parameters)


def test_eamxx_derives_the_source_vertical_grid():
    # No staged, grid-version-specific file should be injected; the source
    # vertical grid is derived from the run's own output instead.
    for template_name in ["ts.bash", "e3sm_to_cmip.bash"]:
        script = render(template_name)
        assert "vert_L128" not in script
        assert DERIVATION in script
        assert "P0=100000.0" in script
        assert '--vrt_in="${vrt_in_file}"' in script


def test_user_supplied_vrt_in_file_takes_precedence():
    for template_name in ["ts.bash", "e3sm_to_cmip.bash"]:
        script = render(template_name, vrt_in_file="/path/to/my_vert_grid.nc")
        assert "vrt_in_file='/path/to/my_vert_grid.nc'" in script
        assert DERIVATION not in script
        assert '--vrt_in="${vrt_in_file}"' in script


def test_non_eamxx_has_no_vertical_grid_file():
    # EAM/CAM carry vertical coordinate info in the files themselves.
    for template_name in ["ts.bash", "e3sm_to_cmip.bash"]:
        script = render(template_name, prc_typ="eam", vars="T", interp_vars="T")
        assert DERIVATION not in script
        assert "--vrt_in" not in script
        assert "--ps_nm" not in script
