import os
import re

import jinja2

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
