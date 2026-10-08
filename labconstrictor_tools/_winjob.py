"""Windows: make the worker's child processes die with the worker.

POSIX gets this from the worker's own process group. Windows has no process groups; a *job object* with
"kill on close" does the same: every process the worker starts joins the job, and when the worker ends (for any reason,
including being killed) Windows closes the job's last handle and ends them all.
"""

from __future__ import annotations

import ctypes
import logging
import os
from ctypes import wintypes

log = logging.getLogger("labconstrictor")

_JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
_KILL_ON_JOB_CLOSE = 0x2000
_keep_alive = None  # the job handle must stay open for as long as the worker runs


class _BasicLimits(ctypes.Structure):
    """Win32 JOBOBJECT_BASIC_LIMIT_INFORMATION: field order and sizes must match the C struct exactly."""

    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_int64),
        ("PerJobUserTimeLimit", ctypes.c_int64),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class _IoCounters(ctypes.Structure):
    """Win32 IO_COUNTERS: six counters we never read, present only so the struct below has the right size."""

    _fields_ = [(name, ctypes.c_uint64) for name in ("a", "b", "c", "d", "e", "f")]


class _ExtendedLimits(ctypes.Structure):
    """Win32 JOBOBJECT_EXTENDED_LIMIT_INFORMATION: the one SetInformationJobObject accepts for kill-on-close."""

    _fields_ = [
        ("BasicLimitInformation", _BasicLimits),
        ("IoInfo", _IoCounters),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


def kill_children_with_me() -> bool:
    """Put this process in a kill-on-close job. Returns False (and logs why) when Windows refuses; nothing else changes."""
    global _keep_alive
    if os.name != "nt":
        return False
    kernel32 = ctypes.WinDLL(  # type: ignore[attr-defined]  # Windows-only: the stubs of other platforms lack it
        "kernel32", use_last_error=True
    )
    # explicit signatures: without them ctypes passes handles as C ints and the pseudo-handle -1 of this process overflows
    kernel32.CreateJobObjectW.argtypes = [wintypes.LPVOID, wintypes.LPCWSTR]
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.GetCurrentProcess.argtypes = []
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.SetInformationJobObject.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        wintypes.LPVOID,
        wintypes.DWORD,
    ]
    kernel32.SetInformationJobObject.restype = wintypes.BOOL
    kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    job = kernel32.CreateJobObjectW(None, None)
    limits = _ExtendedLimits()
    limits.BasicLimitInformation.LimitFlags = _KILL_ON_JOB_CLOSE
    ok = bool(job) and kernel32.SetInformationJobObject(
        job, _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION, ctypes.byref(limits), ctypes.sizeof(limits)
    )
    ok = ok and kernel32.AssignProcessToJobObject(job, kernel32.GetCurrentProcess())
    if not ok:
        log.warning(
            "worker: could not join a kill-on-close job object (Windows error %s); processes a tool starts may "
            "outlive the worker",
            ctypes.get_last_error(),  # type: ignore[attr-defined]  # Windows-only: absent from other platforms' stubs
        )
        return False
    _keep_alive = job
    return True
