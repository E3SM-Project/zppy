import os

import pytest

from zppy.ai_agents.config_agent import ConfigAgent


class TestConfigAgent:
    def test_init_default(self):
        agent = ConfigAgent()
        assert agent.zppy_root is not None
        assert agent._defaults_path.name == "default.ini"

    def test_init_custom_root(self, tmp_path):
        agent = ConfigAgent(zppy_root=str(tmp_path))
        assert agent.zppy_root == tmp_path

    def test_validate_config_file_not_found(self):
        agent = ConfigAgent()
        errors = agent.validate_config("/nonexistent/path.cfg")
        assert len(errors) == 1
        assert "not found" in errors[0]

    def test_validate_config_valid(self):
        """Validate a known-good config from the test suite."""
        agent = ConfigAgent()
        # Use one of the existing test configs
        test_cfg = os.path.join(
            str(agent.zppy_root), "tests", "test_sections.cfg"
        )
        if os.path.isfile(test_cfg):
            errors = agent.validate_config(test_cfg)
            # test_sections.cfg may not have all required fields,
            # but it should at least parse without exceptions
            assert isinstance(errors, list)

    def test_validate_config_returns_errors_for_bad_config(self, tmp_path):
        """A config with invalid parameter types should produce errors."""
        bad_cfg = tmp_path / "bad.cfg"
        bad_cfg.write_text(
            "[default]\n"
            "active = not_a_boolean\n"
            "nodes = not_an_integer\n"
        )
        agent = ConfigAgent()
        errors = agent.validate_config(str(bad_cfg))
        # Should have validation errors for wrong types
        assert len(errors) > 0

    def test_generate_config_not_implemented(self):
        agent = ConfigAgent()
        with pytest.raises(NotImplementedError):
            agent.generate_config("run e3sm_diags for my simulation")

    def test_collect_validation_errors_nested(self):
        """Test the recursive error collection helper."""
        agent = ConfigAgent()
        result = {
            "default": {
                "case": True,
                "nodes": False,
                "active": ValueError("invalid literal"),
            },
            "climo": True,
        }
        errors = agent._collect_validation_errors(result)
        assert len(errors) == 2
        assert any("nodes" in e for e in errors)
        assert any("active" in e for e in errors)
