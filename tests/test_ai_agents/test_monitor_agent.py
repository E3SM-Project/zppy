import pytest

from zppy.ai_agents.monitor_agent import JobMonitor


@pytest.fixture
def scripts_dir(tmp_path):
    """Populate a temp dir with sample .status files."""
    (tmp_path / "climo_atm_monthly_1985-1989.status").write_text("OK\n")
    (tmp_path / "e3sm_diags_lat_lon_1985-1989.status").write_text("RUNNING\n")
    (tmp_path / "ts_atm_monthly_1985-1989.status").write_text("WAITING\n")
    return tmp_path


class TestJobMonitor:
    def test_get_statuses(self, scripts_dir):
        monitor = JobMonitor(str(scripts_dir))
        statuses = monitor.get_statuses()
        assert statuses["climo_atm_monthly_1985-1989"] == "OK"
        assert statuses["e3sm_diags_lat_lon_1985-1989"] == "RUNNING"
        assert statuses["ts_atm_monthly_1985-1989"] == "WAITING"

    def test_get_statuses_empty_dir(self, tmp_path):
        monitor = JobMonitor(str(tmp_path))
        assert monitor.get_statuses() == {}

    def test_get_statuses_unreadable_file(self, tmp_path):
        (tmp_path / "bad.status").write_text("")
        monitor = JobMonitor(str(tmp_path))
        statuses = monitor.get_statuses()
        assert statuses["bad"] == "UNKNOWN"

    def test_summary(self, scripts_dir):
        monitor = JobMonitor(str(scripts_dir))
        statuses = monitor.get_statuses()
        summary = monitor.summary(statuses)
        assert "OK" in summary
        assert "RUNNING" in summary
        assert "WAITING" in summary

    def test_display_no_files(self, tmp_path, capsys):
        monitor = JobMonitor(str(tmp_path))
        monitor.display({})
        out = capsys.readouterr().out
        assert "No .status files" in out

    def test_display_with_files(self, scripts_dir, capsys):
        monitor = JobMonitor(str(scripts_dir), color=False)
        statuses = monitor.get_statuses()
        monitor.display(statuses)
        out = capsys.readouterr().out
        assert "OK" in out
        assert "RUNNING" in out
        assert "climo_atm_monthly_1985-1989" in out

    def test_error_status_parsed(self, tmp_path):
        (tmp_path / "job.status").write_text("ERROR (3)\n")
        monitor = JobMonitor(str(tmp_path))
        statuses = monitor.get_statuses()
        assert statuses["job"] == "ERROR"
