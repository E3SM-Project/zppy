"""The single subprocess seam used by the complete run test.

Every external command the complete run issues goes through :func:`run_command`,
so tests can replace one function rather than patching :mod:`subprocess` in each
module that shells out.
"""

from __future__ import annotations

import logging
import subprocess
from typing import List, Sequence

logger: logging.Logger = logging.getLogger(__name__)


class CommandError(RuntimeError):
    """A command exited nonzero, or could not be run at all."""

    def __init__(self, args: Sequence[str], returncode: int, stderr: str) -> None:
        self.args_run: List[str] = list(args)
        self.returncode: int = returncode
        self.stderr: str = stderr
        super().__init__(
            f"Command failed with exit code {returncode}: "
            f"{' '.join(self.args_run)}\n{stderr}"
        )


def run_command(
    args: Sequence[str],
    *,
    cwd: str | None = None,
    check: bool = True,
    timeout: int | None = None,
) -> str:
    """Run a command and return its stripped standard output.

    Parameters
    ----------
    args : Sequence[str]
        The command and its arguments. Never a shell string; the complete run
        builds argument lists so paths with spaces cannot be re-split.
    cwd : str | None
        Directory to run in.
    check : bool
        Raise :class:`CommandError` on a nonzero exit. When False, the command's
        output is returned regardless and the caller inspects it.
    timeout : int | None
        Seconds to wait before giving up.

    Raises
    ------
    CommandError
        If the command exits nonzero and ``check`` is True, or if it could not
        be started or timed out.
    """
    try:
        completed = _run(args, cwd, timeout)
    except (OSError, subprocess.SubprocessError) as error:
        raise CommandError(args, -1, str(error)) from error

    if check and completed.returncode != 0:
        raise CommandError(args, completed.returncode, completed.stderr)

    return completed.stdout.strip()


def run_command_status(
    args: Sequence[str], *, cwd: str | None = None, timeout: int | None = None
) -> tuple[int, str]:
    """Run a command and return its exit code alongside combined output.

    Used where a nonzero exit is a result to record rather than an error to
    raise -- a failing pytest file, for example.
    """
    try:
        completed = _run(args, cwd, timeout)
    except (OSError, subprocess.SubprocessError) as error:
        return -1, str(error)

    return completed.returncode, completed.stdout + completed.stderr


def _run(
    args: Sequence[str], cwd: str | None, timeout: int | None
) -> "subprocess.CompletedProcess[str]":
    logger.debug("Running: %s", " ".join(args))
    return subprocess.run(
        list(args), cwd=cwd, capture_output=True, text=True, timeout=timeout
    )
