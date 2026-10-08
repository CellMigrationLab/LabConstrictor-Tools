"""One log file for every front-end: <LC_HOME>/logs/labconstrictor.log (rotating, 5 x 1 MB).

Napari, the command line and (through the same line format) Fiji append to it, so a bug report needs one file:
    labconstrictor-tools logs            # print the tail          labconstrictor-tools support-bundle   # zip for a bug report
Logging never raises: an unwritable log folder must not break a run.
"""

import logging
import logging.handlers
import platform
import sys
from collections.abc import Sequence
from pathlib import Path

from . import registry

LOG_NAME = "labconstrictor.log"
_FORMAT = "%(asctime)s.%(msecs)03d %(levelname)-7s pid=%(process)d %(message)s"
_logger = None
_version_fallback_logged = False


def log_dir() -> Path:
    return registry.home() / "logs"


def log_path() -> Path:
    return log_dir() / LOG_NAME


def logger() -> logging.Logger:
    global _logger
    if _logger is not None:
        return _logger
    _logger = logging.getLogger("labconstrictor")
    _logger.setLevel(logging.DEBUG)
    _logger.propagate = False
    try:
        log_dir().mkdir(parents=True, exist_ok=True)
        handler = logging.handlers.RotatingFileHandler(
            log_path(), maxBytes=1_000_000, backupCount=5, encoding="utf-8"
        )
        handler.setFormatter(logging.Formatter(_FORMAT, "%Y-%m-%d %H:%M:%S"))
        _logger.addHandler(handler)
        _logger.info("---- session start: %s", environment_summary())
    except OSError as error:
        _logger.addHandler(logging.NullHandler())
        print(  # once per process: the run goes on, but nobody should believe a log is being written
            "LabConstrictor: cannot write the log file %s (%s: %s); diagnostics will not be saved"
            % (log_path(), type(error).__name__, error),
            file=sys.stderr,
        )
    return _logger


def environment_summary() -> str:
    return "labconstrictor_tools=%s python=%s (%s) platform=%s LC_HOME=%s" % (
        version(),
        platform.python_version(),
        sys.executable,
        platform.platform(),
        registry.home(),
    )


def version() -> str:
    try:
        from importlib.metadata import PackageNotFoundError
        from importlib.metadata import version as package_version

        return package_version("labconstrictor-tools")
    except PackageNotFoundError:  # intended fallback: running from a checkout
        global _version_fallback_logged
        if not _version_fallback_logged:
            _version_fallback_logged = True
            logging.getLogger("labconstrictor").info(
                "labconstrictor-tools is not installed as a package: version shown as 'unknown (checkout)'"
            )
        return "unknown (checkout)"


def info(message: str, *args: object) -> None:
    logger().info(message, *args)


def warning(message: str, *args: object) -> None:
    logger().warning(message, *args)


def error(message: str, *args: object, exc_info: bool = False) -> None:
    logger().error(message, *args, exc_info=exc_info)


def tail(lines: int = 60) -> str:
    """Last `lines` lines of the log, newest last (for 'Details' windows and `labconstrictor-tools logs`)."""
    try:
        return "".join(log_path().read_text(encoding="utf-8", errors="replace").splitlines(True)[-lines:])
    except OSError as error:  # no log yet, or unreadable: an empty tail, and the reason in the debug log
        logging.getLogger("labconstrictor").debug(
            "cannot read the log file %s: %s: %s", log_path(), type(error).__name__, error
        )
        return ""


def explain_spawn_error(error_: OSError, command: Sequence[str]) -> str:
    """Turn an OSError from starting a worker into a sentence that says what to check."""
    path = command[0]
    if isinstance(error_, FileNotFoundError):
        return (
            "the app's Python was not found at %s (was the app moved, uninstalled or is the drive not mounted?)"
            % path
        )
    if isinstance(error_, PermissionError):
        return (
            "no permission to run %s (check execute rights, antivirus quarantine, or a read-only/noexec mount)"
            % path
        )
    return "could not start %s: %s" % (path, error_)


def hint_for_exit(returncode: int | None, stderr_tail: str | None) -> str:
    """A one-line likely cause for a worker that died on its own."""
    text = stderr_tail or ""
    if "ModuleNotFoundError" in text or "ImportError" in text:
        return "a Python package is missing or broken in the app's environment (see the traceback above)"
    if returncode in (-9, 137):
        return "the worker was killed (out of memory? the OS OOM killer ends big image jobs this way)"
    if returncode in (-11, 139, 3221225477):
        return "the worker crashed natively (segmentation fault in a compiled library)"
    if returncode == 3:
        return "the app's tool module failed to import (see the traceback above)"
    return ""
