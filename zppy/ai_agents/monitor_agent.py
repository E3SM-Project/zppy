"""
Job monitor for zppy SLURM jobs.

Reads .status files written by zppy into the scripts directory and
displays a live or one-shot status table.

zppy writes status tokens: OK | RUNNING | WAITING | ERROR (N)
"""

import time
from pathlib import Path
from typing import Dict

_SYMBOLS = {
    "OK": "✓",
    "RUNNING": "⟳",
    "WAITING": "⏸",
    "ERROR": "✗",
    "UNKNOWN": "?",
}

_COLORS = {
    "OK": "\033[32m",
    "RUNNING": "\033[36m",
    "WAITING": "\033[33m",
    "ERROR": "\033[31m",
}
_RESET = "\033[0m"


class JobMonitor:
    """
    Monitor zppy job statuses by reading .status files.

    Usage:
        monitor = JobMonitor("/path/to/scripts")
        monitor.display(monitor.get_statuses())   # one-shot
        monitor.watch(interval=30)                # live loop
    """

    def __init__(self, scripts_dir: str, color: bool = True):
        self.scripts_dir = Path(scripts_dir)
        self.color = color

    def get_statuses(self) -> Dict[str, str]:
        """Read all .status files; return {job_name: status_token}."""
        statuses = {}
        for f in sorted(self.scripts_dir.glob("*.status")):
            try:
                token = f.read_text().strip().split()[0]
            except Exception:
                token = "UNKNOWN"
            statuses[f.stem] = token
        return statuses

    def _fmt(self, text: str, status: str) -> str:
        if not self.color:
            return text
        return f"{_COLORS.get(status, '')}{text}{_RESET}"

    def display(self, statuses: Dict[str, str]) -> None:
        if not statuses:
            print("No .status files found.")
            return
        width = max(len(n) for n in statuses)
        print(f"\n{'Job':<{width + 2}}Status")
        print("─" * (width + 14))
        for name, status in statuses.items():
            symbol = _SYMBOLS.get(status, "?")
            print(f"{name:<{width + 2}}{self._fmt(symbol + ' ' + status, status)}")
        print()

    def summary(self, statuses: Dict[str, str]) -> str:
        counts: Dict[str, int] = {}
        for s in statuses.values():
            counts[s] = counts.get(s, 0) + 1
        return "  ".join(f"{v} {k}" for k, v in sorted(counts.items()))

    def watch(self, interval: int = 30) -> None:
        """Refresh the status table every `interval` seconds until all jobs finish."""
        try:
            while True:
                statuses = self.get_statuses()
                print("\033[2J\033[H", end="")  # clear screen
                print(f"zppy Monitor — {self.scripts_dir}")
                print(f"Refresh every {interval}s  |  Ctrl+C to quit\n")
                self.display(statuses)
                if statuses:
                    print(f"Summary: {self.summary(statuses)}")
                    if all(s in ("OK", "ERROR") for s in statuses.values()):
                        print("\nAll jobs finished.")
                        break
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\nMonitor stopped.")
