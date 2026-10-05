"""Import first in every test script. Makes the checkout importable and gives every run a private, pre-populated registry
(never the user's real ~/.labconstrictor).

Portable by default: the "app" under test is the example app `labconstrictor_tools.examples.synthetic`, registered against the
interpreter running the tests (needs numpy, pandas, tifffile, scipy, ipywidgets). Real LabConstrictor apps are optional:

    LC_TEST_NUCLEISKY_PYTHON=/path/to/NucleiSky/bin/python      LC_TEST_CELLTRACKS_PYTHON=...      LC_TEST_VLAB4MIC_PYTHON=...

Tests that need a real app skip (or report SKIP) when its interpreter is not given.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
V3 = ROOT  # historical name used by the test scripts
FIXTURES = ROOT / "fixtures"
EVIDENCE = ROOT / "evidence"
EVIDENCE.mkdir(exist_ok=True)  # reports written by some suites (git-ignored)
SYNTHETIC_MODULE = "labconstrictor_tools.examples.synthetic"
sys.path.insert(0, str(ROOT))

# Same interpreter for host and "app": prefix = the environment running the tests.
GENERIC_PYTHON = Path(os.environ.get("LC_TEST_PYTHON") or sys.executable)
GENERIC_PREFIX = Path(os.environ.get("LC_TEST_PREFIX") or sys.prefix)


def real_app_python(name):
    """Interpreter of a real installed app (nucleisky | celltracks | vlab4mic) or None."""
    value = os.environ.get("LC_TEST_%s_PYTHON" % name.upper())
    return Path(value) if value and Path(value).exists() else None


def prefix_of(python):
    """Install prefix of an interpreter: <prefix>/bin/python or <prefix>/python.exe."""
    python = Path(python)
    return python.parent.parent if python.parent.name in ("bin", "Scripts") else python.parent


def ensure_fixtures():
    """Generate the (large, deterministic) NucleiSky test images on first use instead of committing 5 MB of TIFF."""
    if not (FIXTURES / "nucleisky" / "query.tif").exists():
        subprocess.run(
            [sys.executable, str(FIXTURES / "make_nucleisky.py"), str(FIXTURES / "nucleisky")], check=True
        )
    return FIXTURES


def register_synthetic(home):
    env = {**os.environ, "LC_HOME": str(home), "PYTHONPATH": str(ROOT)}
    subprocess.run(
        [sys.executable, "-m", "labconstrictor_tools", "register", "--name", "synthetic", "--prefix", str(GENERIC_PREFIX),
         "--module", SYNTHETIC_MODULE, "--version", "0.0"],
        check=True, capture_output=True, env=env,
    )  # fmt: skip


if "LC_HOME" not in os.environ or os.environ.get("LC_TEST_FRESH_HOME", "1") == "1":
    _home = Path(tempfile.mkdtemp(prefix="lc_test_home_"))
    os.environ["LC_HOME"] = str(_home)
    register_synthetic(_home)
