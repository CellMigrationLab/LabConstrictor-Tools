"""Hooks a tool can call while it runs: progress(), cancelled(), check_cancel(). Host-independent.

The worker installs the real sinks around each task; outside a worker they are harmless no-ops.
"""

from collections.abc import Callable
from typing import Any

from .types import Cancelled

_sinks: dict[str, Any] = {"progress": None, "cancelled": None}


def install(
    progress: Callable[[float | None, str], None] | None = None, cancelled: Callable[[], bool] | None = None
) -> None:
    """Called by the worker around each task."""
    _sinks["progress"], _sinks["cancelled"] = progress, cancelled


def progress(fraction: float | None = None, message: str = "") -> None:
    """Report progress (fraction in 0..1, or None for indeterminate) and a short status message."""
    if _sinks["progress"]:
        _sinks["progress"](fraction, message)


def cancelled() -> bool:
    """True once the host asked to cancel this task."""
    return bool(_sinks["cancelled"] and _sinks["cancelled"]())


def check_cancel() -> None:
    """Raise Cancelled if the host asked to cancel. Call this regularly inside long loops."""
    if cancelled():
        raise Cancelled()
