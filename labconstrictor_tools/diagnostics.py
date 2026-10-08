"""Checks of an installation: the machine, the worker and the GPU libraries. Standard library only; every probe is optional.

    from labconstrictor_tools import diagnostics
    checks = diagnostics.run_checks()           # a list of Check; one failing probe never stops the others
    print(diagnostics.summary(checks))          # a short text: a tick, a warning or a cross per layer, with the fix beside each cross
    diagnostics.rows(checks)                    # a list of dicts, ready for a table
    diagnostics.as_json(checks)                 # a JSON text to attach to an issue

An app adds its own "Check this installation" tool in a few lines (see examples/interactions.py for the pattern). Probes look at a library
only when it is already installed in the app's environment: they never import something heavy just to find it missing, and they never install.
To add a probe, write a function returning a list of `Check` and give it to `run_checks(extra=[...])`.
"""

from __future__ import annotations

import json
import logging
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

# Standard library only: no dependency on the host's log file. Inside a host the "labconstrictor" logger writes to the shared
# log; in a worker (no handler) warnings and errors reach stderr, which the host copies into that log.
log = logging.getLogger("labconstrictor.diagnostics")

TOOL_PROBE_TIMEOUT_S = 10.0  # a GPU tool query (nvidia-smi, ...) that takes longer is reported as timed out
NETWORK_TIMEOUT_S = 5  # per host in the network probe
HTTPS_PORT = 443
BENCHMARK_SIZE = 512  # side of the matrix / image of the GPU benchmark
BENCHMARK_REPEATS = 5  # timed repetitions per device
BENCHMARK_AGREEMENT = 1e-3  # relative difference to the CPU result above which a device is said to disagree
ASCII_MAX = 127  # characters above this in a path are reported (some tools cannot open such paths)
# exit codes `_run` reports, following the shell convention
EXIT_TIMED_OUT, EXIT_NOT_EXECUTABLE, EXIT_NOT_FOUND = 124, 126, 127
OK, WARN, FAIL, INFO = "ok", "warn", "fail", "info"
_SYMBOL = {OK: "\u2714", WARN: "\u26a0", FAIL: "\u2716", INFO: "\u2022"}


@dataclass
class Check:
    """One line of the `doctor` report: what was looked at, how it went, and what to do about it."""

    layer: str  # "machine", "worker", "gpu tools", "gpu libraries", "benchmark", "network", ...
    name: str
    status: str  # ok | warn | fail | info
    detail: str = ""
    fix: str = ""  # what to do when status is warn or fail


Probe = Callable[[], "list[Check]"]


# ---------------------------------------------------------------------------------------------------- machine
def _ram_gb() -> float | None:
    try:
        if hasattr(os, "sysconf") and "SC_PHYS_PAGES" in os.sysconf_names:
            return os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE") / 1024**3
    except (ValueError, OSError) as error:  # no sysconf value on this platform: try the next method
        log.debug("memory: os.sysconf failed (%s: %s)", type(error).__name__, error)
    if sys.platform == "win32":
        try:
            import ctypes

            class Status(ctypes.Structure):
                """Windows MEMORYSTATUSEX: the layout GlobalMemoryStatusEx fills in."""

                _fields_ = (
                    [("length", ctypes.c_ulong), ("load", ctypes.c_ulong), ("total", ctypes.c_ulonglong)]
                    + [(n, ctypes.c_ulonglong) for n in ("avail", "ptotal", "pavail", "vtotal", "vavail")]
                    + [("ext", ctypes.c_ulonglong)]
                )

            status = Status()
            status.length = ctypes.sizeof(Status)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))  # type: ignore[attr-defined]
            return status.total / 1024**3
        except (
            OSError,
            AttributeError,
            ValueError,
        ) as error:  # no ctypes.windll / call refused: memory is then not reported
            log.warning(
                "memory: GlobalMemoryStatusEx failed (%s: %s); the memory check is skipped",
                type(error).__name__,
                error,
            )
            return None
    return None


def probe_machine() -> list[Check]:
    out = [
        Check(
            "machine",
            "system",
            INFO,
            "%s %s, %s, Python %s"
            % (platform.system(), platform.release(), platform.machine(), platform.python_version()),
        )
    ]
    out.append(Check("machine", "cpu", INFO, "%s logical cores" % (os.cpu_count() or "?")))
    ram = _ram_gb()
    if ram is not None:
        out.append(
            Check(
                "machine",
                "memory",
                OK if ram >= 8 else WARN,
                "%.1f GB" % ram,
                "" if ram >= 8 else "Less than 8 GB: large images and models may not fit.",
            )
        )
    for label, path in (("temporary folder", tempfile.gettempdir()), ("home folder", str(Path.home()))):
        try:
            free = shutil.disk_usage(path).free / 1024**3
            out.append(
                Check(
                    "machine",
                    "free disk (%s)" % label,
                    OK if free >= 5 else WARN,
                    "%.1f GB free in %s" % (free, path),
                    "" if free >= 5 else "Free some space: results and model downloads need several GB.",
                )
            )
        except OSError as error:
            out.append(Check("machine", "free disk (%s)" % label, WARN, "cannot read: %s" % error))
    try:
        with tempfile.TemporaryDirectory(prefix="lc_check_") as folder:
            probe = Path(folder, "t\u00e9st.txt")
            probe.write_text("x", encoding="utf-8")
            out.append(
                Check(
                    "machine",
                    "writing files",
                    OK,
                    "wrote and read a file with a non-ASCII name in %s" % folder,
                )
            )
    except Exception as error:  # probe boundary: any failure here IS the finding (returned below, and logged)
        log.error("probe 'writing files' failed: %s: %s", type(error).__name__, error, exc_info=True)
        out.append(
            Check(
                "machine",
                "writing files",
                FAIL,
                str(error),
                "The temporary folder is not writable or the file name is refused: set TMP or TEMP to a folder you can write.",
            )
        )
    path = tempfile.gettempdir()
    if any(ord(c) > ASCII_MAX for c in path):
        out.append(
            Check(
                "machine",
                "path characters",
                WARN,
                "the temporary folder has non-ASCII characters: %s" % path,
                "Some tools cannot open such paths: set TMP or TEMP to a plain folder.",
            )
        )
    if sys.platform == "win32" and len(path) > 60:
        out.append(
            Check(
                "machine",
                "path length",
                WARN,
                "the temporary folder path is long (%d characters)" % len(path),
                "Windows limits whole paths to 260 characters: set TMP or TEMP to a short folder such as C:\\tmp.",
            )
        )
    return out


# ---------------------------------------------------------------------------------------------------- worker
def probe_worker() -> list[Check]:
    out = [Check("worker", "python", INFO, "%s (%s)" % (sys.executable, platform.python_version()))]
    from importlib import metadata

    try:
        out.append(Check("worker", "labconstrictor-tools", INFO, metadata.version("labconstrictor-tools")))
    except metadata.PackageNotFoundError:  # intended fallback: run from a source tree
        log.info(
            "labconstrictor-tools is not installed as a package: reporting 'running from a source folder'"
        )
        out.append(Check("worker", "labconstrictor-tools", INFO, "running from a source folder"))
    for module in ("numpy", "pandas", "scipy", "tifffile", "matplotlib"):
        try:
            out.append(Check("worker", module, INFO, metadata.version(module)))
        except metadata.PackageNotFoundError:  # optional: only the libraries that are installed are listed
            log.debug("worker: %s is not installed, not listed", module)
    return out


# ---------------------------------------------------------------------------------------------------- GPU tools
def _run(command: list[str], timeout: float = TOOL_PROBE_TIMEOUT_S) -> tuple[int, str]:
    try:
        done = subprocess.run(  # noqa: S603 - fixed argument lists only, never a shell
            command, capture_output=True, text=True, timeout=timeout
        )
        return done.returncode, (done.stdout or "") + (done.stderr or "")
    except FileNotFoundError:
        return EXIT_NOT_FOUND, ""
    except subprocess.TimeoutExpired:
        return EXIT_TIMED_OUT, "timed out after %.0f s" % timeout
    except OSError as error:
        return EXIT_NOT_EXECUTABLE, str(error)


def parse_nvidia_smi(text: str) -> list[dict]:
    """The lines of `nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader,nounits`."""
    gpus = []
    for line in text.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 3 and parts[2].replace(".", "", 1).isdigit():
            gpus.append({"name": parts[0], "driver": parts[1], "memory_mb": float(parts[2])})
    return gpus


def probe_gpu_tools() -> list[Check]:
    out = []
    code, text = _run(
        ["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader,nounits"]
    )
    if code == EXIT_NOT_FOUND:
        out.append(
            Check(
                "gpu tools",
                "nvidia-smi",
                INFO,
                "not found (no NVIDIA driver on this machine, or it is not on the path)",
            )
        )
    elif code != 0:
        out.append(
            Check(
                "gpu tools",
                "nvidia-smi",
                FAIL,
                text.strip()[:200] or "exit code %d" % code,
                "The NVIDIA driver does not answer: reinstall or update it, then restart.",
            )
        )
    else:
        for index, gpu in enumerate(parse_nvidia_smi(text)):
            out.append(
                Check(
                    "gpu tools",
                    "NVIDIA GPU %d" % index,
                    OK,
                    "%s, driver %s, %.1f GB" % (gpu["name"], gpu["driver"], gpu["memory_mb"] / 1024),
                )
            )
    if sys.platform == "darwin" and platform.machine() == "arm64":
        out.append(
            Check("gpu tools", "Apple chip", OK, "Apple Silicon (Metal is available to PyTorch as 'mps')")
        )
    elif sys.platform == "darwin":
        out.append(Check("gpu tools", "Apple chip", WARN, "an Intel Mac", "Intel Macs are not supported."))
    if shutil.which("rocm-smi"):
        out.append(
            Check(
                "gpu tools",
                "ROCm",
                INFO,
                "rocm-smi found (AMD GPUs are used through the ROCm build of PyTorch, Linux only)",
            )
        )
    return out


# ---------------------------------------------------------------------------------------------------- GPU libraries
def _torch_module() -> Any:
    """PyTorch only if the app already has it: a probe must not import something heavy that is not installed."""
    import importlib.util

    if importlib.util.find_spec("torch") is None:
        return None
    import torch

    return torch


def probe_torch() -> list[Check]:
    try:
        torch = _torch_module()
    except (
        Exception
    ) as error:  # a broken install is a finding: importing can raise anything (returned below, and logged)
        log.error("probe PyTorch: import failed: %s: %s", type(error).__name__, error, exc_info=True)
        return [
            Check(
                "gpu libraries",
                "PyTorch",
                FAIL,
                "installed but cannot be imported: %s" % error,
                "Reinstall PyTorch in this application.",
            )
        ]
    if torch is None:
        return [Check("gpu libraries", "PyTorch", INFO, "not installed in this application")]
    out = [Check("gpu libraries", "PyTorch", OK, "version %s" % getattr(torch, "__version__", "?"))]
    has_nvidia = any(
        c.layer == "gpu tools" and c.name.startswith("NVIDIA GPU") and c.status == OK
        for c in probe_gpu_tools()
    )
    cuda_build = getattr(getattr(torch, "version", None), "cuda", None)
    try:
        cuda_ok = bool(torch.cuda.is_available())
    except Exception as error:  # driver calls can raise anything: reported as the CUDA finding below
        log.error(
            "probe PyTorch: torch.cuda.is_available() failed: %s: %s",
            type(error).__name__,
            error,
            exc_info=True,
        )
        cuda_ok = False
        out.append(Check("gpu libraries", "CUDA", FAIL, str(error), "Update the NVIDIA driver."))
    if cuda_ok:
        for index in range(torch.cuda.device_count()):
            props = torch.cuda.get_device_properties(index)
            out.append(
                Check(
                    "gpu libraries",
                    "CUDA device %d" % index,
                    OK,
                    "%s, %.1f GB, CUDA %s" % (props.name, props.total_memory / 1024**3, cuda_build),
                )
            )
    elif has_nvidia:
        if cuda_build is None:
            out.append(
                Check(
                    "gpu libraries",
                    "CUDA",
                    FAIL,
                    "an NVIDIA GPU is present but this PyTorch was built without CUDA",
                    "Reinstall the CUDA build of PyTorch (the installer picks it when it finds nvidia-smi; the install log says what it chose).",
                )
            )
        else:
            out.append(
                Check(
                    "gpu libraries",
                    "CUDA",
                    FAIL,
                    "an NVIDIA GPU is present and PyTorch has CUDA %s, but cannot use it" % cuda_build,
                    "The driver is probably too old for this CUDA build: update the NVIDIA driver.",
                )
            )
    else:
        out.append(Check("gpu libraries", "CUDA", INFO, "no CUDA device"))
    mps = getattr(getattr(torch, "backends", None), "mps", None)
    if mps is not None:
        try:
            if mps.is_available():
                out.append(Check("gpu libraries", "MPS (Apple Metal)", OK, "available"))
            elif sys.platform == "darwin" and platform.machine() == "arm64":
                out.append(
                    Check(
                        "gpu libraries",
                        "MPS (Apple Metal)",
                        WARN,
                        "built=%s, not available" % mps.is_built(),
                        "Update macOS (12.3 or newer) and use a PyTorch built for Apple Silicon.",
                    )
                )
        except Exception as error:  # driver calls can raise anything: reported as the MPS finding
            log.error("probe PyTorch: MPS query failed: %s: %s", type(error).__name__, error, exc_info=True)
            out.append(Check("gpu libraries", "MPS (Apple Metal)", WARN, str(error)))
    hip = getattr(getattr(torch, "version", None), "hip", None)
    if hip:
        out.append(
            Check(
                "gpu libraries",
                "ROCm",
                OK if cuda_ok else WARN,
                "PyTorch built for ROCm %s" % hip,
                "" if cuda_ok else "No AMD GPU is usable: check the ROCm driver.",
            )
        )
    return out


def torch_devices() -> list[str]:
    """Device names a PyTorch tool can use here: 'cpu', 'cuda:0', ..., 'mps'. [] when PyTorch is not installed."""
    try:
        torch = _torch_module()
    except (
        Exception
    ):  # a broken PyTorch import: probe_torch reports it as a finding; here we only list devices
        log.error("torch_devices: PyTorch cannot be imported, no devices listed", exc_info=True)
        return []
    if torch is None:
        return []
    names = ["cpu"]
    try:
        if torch.cuda.is_available():
            names += ["cuda:%d" % i for i in range(torch.cuda.device_count())]
    except Exception:  # driver query can raise anything; probe_torch reports CUDA problems as findings
        log.error("torch_devices: the CUDA query failed, no CUDA device listed", exc_info=True)
    try:
        if getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
            names.append("mps")
    except Exception:  # driver query can raise anything; probe_torch reports MPS problems as findings
        log.error("torch_devices: the MPS query failed, no MPS device listed", exc_info=True)
    return names


# ---------------------------------------------------------------------------------------------------- real work
def probe_benchmark(size: int = BENCHMARK_SIZE, repeats: int = BENCHMARK_REPEATS) -> list[Check]:
    """The same small convolution and matrix product on every device: the results must agree (a broken driver does not), and the timings show the real speed-up."""
    try:
        torch = _torch_module()
    except (
        Exception
    ):  # a broken PyTorch import: probe_torch reports it as a finding; there is nothing to benchmark
        log.error("probe benchmark: PyTorch cannot be imported, nothing benchmarked", exc_info=True)
        return []
    if torch is None:
        return []
    out = []
    reference = None
    for name in torch_devices():
        try:
            generator = torch.Generator().manual_seed(0)
            image = torch.rand(1, 1, size, size, generator=generator)
            kernel = torch.rand(8, 1, 5, 5, generator=generator)
            matrix = torch.rand(size, size, generator=generator)
            device = torch.device(name)
            image, kernel, matrix = image.to(device), kernel.to(device), matrix.to(device)

            def work(
                image: Any = image, kernel: Any = kernel, matrix: Any = matrix
            ) -> Any:  # bound now: the loop moves on to the next device
                return torch.nn.functional.conv2d(image, kernel, padding=2).sum() + (matrix @ matrix).sum()

            work()  # warm-up (kernels are compiled on first use)
            if name.startswith("cuda"):
                torch.cuda.synchronize()
            started = time.perf_counter()
            for _ in range(repeats):
                value = work()
            if name.startswith("cuda"):
                torch.cuda.synchronize()
            elif name == "mps":
                torch.mps.synchronize()
            seconds = (time.perf_counter() - started) / repeats
            result = float(value.cpu())
            if reference is None:
                reference = result
            agrees = abs(result - reference) <= BENCHMARK_AGREEMENT * max(1.0, abs(reference))
            out.append(
                Check(
                    "benchmark",
                    name,
                    OK if agrees else FAIL,
                    "%.1f ms per run (conv + matmul, %dx%d)%s"
                    % (seconds * 1000, size, size, "" if agrees else "; the result differs from the CPU's"),
                    (
                        ""
                        if agrees
                        else "This device gives a different result than the CPU: do not use it; update or reinstall its driver."
                    ),
                )
            )
        except (
            Exception
        ) as error:  # a device test can fail in any way: that is the finding (returned, and logged)
            log.error(
                "probe benchmark: device %s failed: %s: %s", name, type(error).__name__, error, exc_info=True
            )
            out.append(
                Check(
                    "benchmark",
                    name,
                    FAIL,
                    "%s: %s" % (type(error).__name__, error),
                    "This device could not run a small test: check its driver, or use the CPU.",
                )
            )
    return out


def benchmark_timings(checks: Iterable[Check]) -> dict[str, float]:
    """{device: milliseconds} from the benchmark checks (for a figure)."""
    times = {}
    for check in checks:
        match = re.match(r"([\d.]+) ms per run", check.detail) if check.layer == "benchmark" else None
        if match:
            times[check.name] = float(match.group(1))
    return times


# ---------------------------------------------------------------------------------------------------- network (only on request)
def probe_network(hosts: Iterable[str] = ("pypi.org", "huggingface.co", "github.com")) -> list[Check]:
    out = []
    for host in hosts:
        started = time.perf_counter()
        try:
            with socket.create_connection((host, HTTPS_PORT), timeout=NETWORK_TIMEOUT_S):
                pass
            out.append(
                Check("network", host, OK, "reachable in %.0f ms" % ((time.perf_counter() - started) * 1000))
            )
        except OSError as error:
            out.append(
                Check(
                    "network",
                    host,
                    WARN,
                    "not reachable (%s)" % error,
                    "Models and packages cannot be downloaded from here: check the proxy or firewall, or install from a local copy.",
                )
            )
    return out


# ---------------------------------------------------------------------------------------------------- put together
DEFAULT_PROBES: list[Probe] = [probe_machine, probe_worker, probe_gpu_tools, probe_torch]


def run_checks(*, benchmark: bool = True, network: bool = False, extra: Iterable[Probe] = ()) -> list[Check]:
    """Every probe, each isolated: a probe that raises becomes one failed Check and the others still run."""
    probes: list[Probe] = list(DEFAULT_PROBES)
    if benchmark:
        probes.append(probe_benchmark)
    if network:
        probes.append(probe_network)
    probes.extend(extra)
    checks: list[Check] = []
    for probe in probes:
        try:
            checks.extend(probe())
        except (
            Exception
        ) as error:  # isolation boundary: one broken probe must not stop the others (returned, and logged)
            log.error(
                "probe %s raised: %s: %s",
                getattr(probe, "__name__", "probe"),
                type(error).__name__,
                error,
                exc_info=True,
            )
            checks.append(
                Check(
                    "probe",
                    getattr(probe, "__name__", "probe"),
                    FAIL,
                    "%s: %s" % (type(error).__name__, error),
                    "This is a bug in the check itself: please report it.",
                )
            )
    return checks


def summary(checks: list[Check]) -> str:
    """A short text: per layer a tick, a warning or a cross, then the fixes. Markdown-friendly (`**bold**`, bullet lines)."""
    layers: dict[str, list[Check]] = {}
    for check in checks:
        layers.setdefault(check.layer, []).append(check)
    lines = []
    for layer, items in layers.items():
        worst = (
            FAIL
            if any(c.status == FAIL for c in items)
            else WARN if any(c.status == WARN for c in items) else OK
        )
        lines.append("%s **%s**" % (_SYMBOL[worst], layer))
        for c in items:
            if c.status in (WARN, FAIL):
                lines.append("- %s %s: %s" % (_SYMBOL[c.status], c.name, c.detail))
                if c.fix:
                    lines.append("  Fix: %s" % c.fix)
            else:  # what was found, in one short line each: a person can see what the green ticks stand for
                lines.append(
                    "- %s: %s" % (c.name, c.detail if len(c.detail) <= 90 else c.detail[:87] + "...")
                )
    count = {s: sum(1 for c in checks if c.status == s) for s in (OK, WARN, FAIL)}
    head = "%s checks: %d ok, %d warning(s), %d failure(s)" % (
        len(checks),
        count[OK],
        count[WARN],
        count[FAIL],
    )
    return head + "\n\n" + "\n".join(lines)


def rows(checks: list[Check]) -> list[dict]:
    return [asdict(c) for c in checks]


def as_json(checks: list[Check]) -> str:
    return json.dumps(
        {"platform": platform.platform(), "python": sys.version, "checks": rows(checks)},
        indent=2,
        ensure_ascii=False,
    )
