import os
import re
import subprocess

import jinja2
import pytest

# Test the template in this working tree, not that of an installed zppy.
TEMPLATE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "zppy", "templates"
)

CONTEXT = {
    "machine": "pm-cpu",
    "prefix": "tc_analysis_0001-0002",
    "scriptDir": "/path/to/scripts",
    "year1": 1,
    "year2": 2,
}


def resolution_block() -> str:
    template_env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(searchpath=TEMPLATE_DIR)
    )
    script = template_env.get_template("tc_analysis.bash").render(**CONTEXT)
    # The block that picks the warm-core search radius, up to DetectNodes.
    match = re.search(r'^if \[ "\$\{res\}" == .*?^fi$', script, re.M | re.S)
    assert match is not None
    return match.group(0)


def run_block(res: str, tmp_path) -> subprocess.CompletedProcess:
    # Stand in for scriptDir so the error branch can write its status file.
    block = resolution_block().replace("/path/to/scripts", str(tmp_path))
    script = f'res="{res}"\n{block}\necho "radius=${{temp_threshold_radius}}"\n'
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True)


@pytest.mark.parametrize(
    "res, radius", [("30", "1.0"), ("120", "0.30"), ("256", "0.15")]
)
def test_warm_core_search_radius_depends_on_resolution(res, radius, tmp_path):
    result = run_block(res, tmp_path)
    assert result.returncode == 0
    assert f"radius={radius}" in result.stdout


def test_unsupported_resolution_fails(tmp_path):
    result = run_block("60", tmp_path)
    assert result.returncode == 13
    assert "Supported resolutions: 30, 120, 256." in result.stdout
    status = tmp_path / "tc_analysis_0001-0002.status"
    assert status.read_text().strip() == "ERROR (13)"


def test_input_is_subsampled_to_6_hourly():
    template_env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(searchpath=TEMPLATE_DIR)
    )
    script = template_env.get_template("tc_analysis.bash").render(**CONTEXT)
    assert "--timestride" not in script
    # TC detection and the AEW vorticity both use 00, 06, 12, and 18Z only.
    tc_detect = re.search(r"^DetectNodes .*?^$", script, re.M | re.S)
    vorticity = re.search(r"^VariableProcessor .*?^$", script, re.M | re.S)
    assert tc_detect is not None and '--timefilter "6hr"' in tc_detect.group(0)
    assert vorticity is not None and '--timefilter "6hr"' in vorticity.group(0)


@pytest.mark.parametrize(
    "candidates, returncode",
    [("", 19), ("1850\t1\t1\t0\t0\n1850\t1\t1\t0\t6\n", 0)],
)
def test_no_6_hourly_time_step_fails(candidates, returncode, tmp_path):
    template_env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(searchpath=TEMPLATE_DIR)
    )
    script = template_env.get_template("tc_analysis.bash").render(**CONTEXT)
    match = re.search(r'^if ! grep -q "\^\[0-9\]".*?^fi$', script, re.M | re.S)
    assert match is not None
    block = match.group(0).replace("/path/to/scripts", str(tmp_path))
    (tmp_path / "cyclones_case_0001_0002.txt").write_text(candidates)
    setup = f'result_dir="{tmp_path}/"\nfile_name="case_0001_0002"\n'
    result = subprocess.run(
        ["bash", "-c", setup + block], capture_output=True, text=True
    )
    assert result.returncode == returncode
    if returncode:
        status = tmp_path / "tc_analysis_0001-0002.status"
        assert status.read_text().strip() == "ERROR (19)"
