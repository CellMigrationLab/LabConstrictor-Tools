"""Hooks a tool can call while it runs: progress(), cancelled(), check_cancel(). Host-independent.

The worker installs the real sinks around each task; outside a worker they are harmless no-ops.
"""

from .types import Cancelled

_sinks = {"progress": None, "cancelled": None}


def install(progress=None, cancelled=None):
    """Called by the worker around each task."""
    _sinks["progress"], _sinks["cancelled"] = progress, cancelled


def progress(fraction=None, message=""):
    """Report progress (fraction in 0..1, or None for indeterminate) and a short status message."""
    if _sinks["progress"]:
        _sinks["progress"](fraction, message)


def cancelled():
    """True once the host asked to cancel this task."""
    return bool(_sinks["cancelled"] and _sinks["cancelled"]())


def check_cancel():
    """Raise Cancelled if the host asked to cancel. Call this regularly inside long loops."""
    if cancelled():
        raise Cancelled()
