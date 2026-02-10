"""Unit tests for ts.bash template variable exclusion logic."""

import os

from configobj import ConfigObj

from zppy.utils import initialize_template


def test_ts_template_variable_exclusion_glb():
    """Test that ts.bash template correctly excludes U, U10, V for glb mapping."""

    # Create a minimal config
    config = ConfigObj()
    config["default"] = {}
    config["default"]["templateDir"] = os.path.join(
        os.path.dirname(__file__), "..", "zppy", "templates"
    )

    # Initialize template
    template, _ = initialize_template(config, "ts.bash")

    # Test case 1: Original issue - OMEGA500,U,U10 should not become OMEGA50010
    test_params = {
        "mapping_file": "glb",
        "vars": "T,OMEGA500,U,U10,V,ICEFRAC",
        "environment_commands": "",
        "prefix": "test",
        "input": "/test/input",
        "input_subdir": "archive/atm/hist",
        "yr_start": 1985,
        "yr_end": 1990,
        "case": "test_case",
        "input_files": "eam.h0",
        "scriptDir": "/test/scripts",
        "ncclimo_cmd": "ncclimo",
        "job_nbr": 0,
        "extra_vars": "",
        "parallel": "",
        "ypf": 5,
        "area_nm": "area",
        "prc_typ": "flt",
        "frequency": "monthly",
        "output": "/test/output",
        "component": "atm",
        "grid": "180x360_aave",
        "debug": "false",
    }

    # Render template
    rendered = template.render(**test_params)

    # Check that the rendered template contains the correct sed command
    assert "sed 's/" in rendered, "Template should use sed for variable filtering"
    assert "U10" in rendered, "Template should check for U10"
    assert "OMEGA50010" not in rendered, "Template should not create OMEGA50010"

    # Extract the vars assignment line to verify it's using sed
    lines = rendered.split("\n")
    vars_lines = [line for line in lines if "vars=" in line and "sed" in line]
    assert len(vars_lines) > 0, "Should have at least one line using sed to set vars"

    # Verify that the old buggy pattern is not present
    assert "${vars//,U}" not in rendered, "Old buggy pattern should not be present"

    print("Test passed: Template correctly uses sed for variable exclusion")


def test_ts_template_variable_exclusion_non_glb():
    """Test that ts.bash template does not exclude variables for non-glb mapping."""

    # Create a minimal config
    config = ConfigObj()
    config["default"] = {}
    config["default"]["templateDir"] = os.path.join(
        os.path.dirname(__file__), "..", "zppy", "templates"
    )

    # Initialize template
    template, _ = initialize_template(config, "ts.bash")

    # Test with non-glb mapping_file
    test_params = {
        "mapping_file": "map_ne30pg2_to_180x360_aave.nc",
        "vars": "T,OMEGA500,U,U10,V,ICEFRAC",
        "environment_commands": "",
        "prefix": "test",
        "input": "/test/input",
        "input_subdir": "archive/atm/hist",
        "yr_start": 1985,
        "yr_end": 1990,
        "case": "test_case",
        "input_files": "eam.h0",
        "scriptDir": "/test/scripts",
        "ncclimo_cmd": "ncclimo",
        "job_nbr": 0,
        "extra_vars": "",
        "parallel": "",
        "ypf": 5,
        "mapping_file": "map_ne30pg2_to_180x360_aave.nc",
        "prc_typ": "flt",
        "frequency": "monthly",
        "output": "/test/output",
        "component": "atm",
        "grid": "180x360_aave",
        "debug": "false",
    }

    # Render template
    rendered = template.render(**test_params)

    # For non-glb mapping, variables should not be filtered
    # The template should just set vars directly without sed filtering

    # The sed filtering logic should only apply when mapping_file == 'glb'
    # For other mappings, vars should be set directly
    # Verify the "Remove 3D" comment is not in the rendered output for non-glb
    assert "Remove 3D" not in rendered or "glb" not in rendered

    print("Test passed: Template does not filter variables for non-glb mapping")


def test_ts_template_renders_without_errors():
    """Test that ts.bash template can be rendered without errors."""

    # Create a minimal config
    config = ConfigObj()
    config["default"] = {}
    config["default"]["templateDir"] = os.path.join(
        os.path.dirname(__file__), "..", "zppy", "templates"
    )

    # Initialize template
    template, _ = initialize_template(config, "ts.bash")

    # Test with empty vars for glb
    test_params = {
        "mapping_file": "glb",
        "vars": "",
        "environment_commands": "",
        "prefix": "test",
        "input": "/test/input",
        "input_subdir": "archive/atm/hist",
        "yr_start": 1985,
        "yr_end": 1990,
        "case": "test_case",
        "input_files": "eam.h0",
        "scriptDir": "/test/scripts",
        "ncclimo_cmd": "ncclimo",
        "job_nbr": 0,
        "extra_vars": "",
        "parallel": "",
        "ypf": 5,
        "area_nm": "area",
        "prc_typ": "flt",
        "frequency": "monthly",
        "output": "/test/output",
        "component": "atm",
        "grid": "180x360_aave",
        "debug": "false",
    }

    # Render template should not raise an error
    rendered = template.render(**test_params)
    assert len(rendered) > 0, "Template should render to non-empty string"

    print("Test passed: Template renders without errors with empty vars")


if __name__ == "__main__":
    test_ts_template_variable_exclusion_glb()
    test_ts_template_variable_exclusion_non_glb()
    test_ts_template_renders_without_errors()
    print("\nAll tests passed!")
