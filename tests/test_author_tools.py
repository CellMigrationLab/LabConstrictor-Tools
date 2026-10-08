"""Author tooling: `labconstrictor-tools test` and the notebook helper (%%lc_tool, export-notebook)."""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import _paths  # noqa: F401  (must come first)
from _paths import GENERIC_PYTHON, SYNTHETIC_MODULE, V3, ensure_fixtures

NUCLEISKY = GENERIC_PYTHON  # any interpreter with numpy, pandas, tifffile, scipy, ipywidgets, IPython
SYNTHETIC = SYNTHETIC_MODULE


def lc(python, *args, cwd=None):
    env = {
        **os.environ,
        "PYTHONPATH": str(V3),
        "PYTHONNOUSERSITE": "1",
        "MPLBACKEND": "Agg",
        "PYTHONUTF8": "1",
    }
    run = subprocess.run(  # utf-8 both ways: the CLI prints marks (check, cross) that Windows' cp1252 cannot
        [str(python), "-m", "labconstrictor_tools", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        cwd=cwd,
    )
    return run.returncode, run.stdout + run.stderr


class TestCommand(unittest.TestCase):
    def test_case_file_passes_and_reports(self):
        code, out = lc(
            NUCLEISKY,
            "test", "--module", SYNTHETIC, "--cases", str(V3 / "tests/data/synthetic_cases.json"),
        )  # fmt: skip
        self.assertEqual(code, 0, out)
        self.assertIn("4 run, 0 failed", out)

    def test_wrong_expectation_fails_the_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            cases = Path(tmp) / "cases.json"
            cases.write_text(
                json.dumps(
                    [
                        {
                            "tool": "scalar_echo",
                            "inputs": {"a": 1.0, "b": 2.0},
                            "expect": {"results": {"values": {"sum": 99}}},
                        },
                        {"tool": "explode", "expect": {"status": "COMPLETE"}},
                    ]
                )
            )
            code, out = lc(
                NUCLEISKY,
                "test", "--module", SYNTHETIC, "--cases", str(cases), "--json",
            )  # fmt: skip
        self.assertEqual(code, 1, out)
        reports = json.loads(out[out.index("{") :])["reports"]
        self.assertIn("sum is 3.0, expected 99", reports[0]["problems"][0])
        self.assertIn("status FAILED, expected COMPLETE", reports[1]["problems"][0])

    def test_contract_violations_and_skips(self):
        code, out = lc(
            NUCLEISKY,
            "test", "--module", "tools", "--pythonpath", str(V3 / "tests/broken_app"),
            "--timeout", "30",
        )  # fmt: skip
        self.assertEqual(code, 1, out)
        self.assertIn("bad_return", out)
        self.assertIn("tool returned 1 values, declared 2", out)
        self.assertIn("needs_image", out)
        self.assertIn("skipped: required parameter 'image' has no --sample", out)
        self.assertIn("table does not parse", out)
        fine = [ln for ln in out.splitlines() if ln.startswith("✔ fine_image")]
        self.assertTrue(fine, out)  # float64 is converted, so it passes the Fiji-safe dtype check

    def test_deaf_tool_is_flagged_by_check_cancel(self):
        code, out = lc(
            NUCLEISKY,
            "test", "--module", "tools", "--pythonpath", str(V3 / "tests/broken_app"),
            "--only", "deaf", "--check-cancel", "--timeout", "40",
        )  # fmt: skip
        self.assertEqual(
            code, 1, out
        )  # --check-cancel asked for a verdict: a tool that ignores Cancel fails it
        self.assertIn("ignored a cancel request", out)

    def test_samples_feed_required_inputs(self):
        code, out = lc(
            NUCLEISKY,
            "test", "--module", "tools", "--pythonpath", str(V3 / "tests/broken_app"),
            "--only", "needs_image", "--sample", "image=%s" % (ensure_fixtures() / "nucleisky/query.tif"),
        )  # fmt: skip
        self.assertEqual(code, 0, out)
        self.assertIn("1 run, 0 failed", out)


CELL_GOOD = '''def blur_stats(image: Image, sigma: Annotated[float, Min(0)] = 2.0) -> Scalars:
    """Mean after smoothing."""
    from scipy.ndimage import gaussian_filter
    return {"mean": float(gaussian_filter(image.astype(float), sigma).mean())}
'''
CELL_GLOBAL = """def uses_global(image: Image) -> Scalars:
    return {"x": float(helper(image))}
"""
CELL_TWO = """def a(x: float = 1.0) -> Scalars:
    return {}
def b(x: float = 1.0) -> Scalars:
    return {}
"""

DRIVER = """
import json, sys, os
os.chdir(sys.argv[1])
from IPython.core.interactiveshell import InteractiveShell
ip = InteractiveShell.instance()
ip.run_line_magic("load_ext", "labconstrictor_tools.notebook_magic")
cells = json.loads(sys.argv[2])
out = []
for line, body in cells:
    ip.run_cell_magic("lc_tool", line, body)
print("DONE")
"""


def notebook(path, cells):
    path.write_text(
        json.dumps(
            {
                "nbformat": 4,
                "nbformat_minor": 5,
                "metadata": {},
                "cells": [
                    {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": c}
                    for c in cells
                ],
            }
        )
    )


class TestNotebookHelper(unittest.TestCase):
    def magic(self, tmp, cells):
        env = {
            **os.environ,
            "PYTHONPATH": str(V3),
            "PYTHONNOUSERSITE": "1",
            "PYTHONUTF8": "1",
        }  # utf-8 stdout: the marks the tools print are not in cp1252
        run = subprocess.run(
            [str(NUCLEISKY), "-c", DRIVER, tmp, json.dumps(cells)], capture_output=True, text=True, env=env
        )
        self.assertIn("DONE", run.stdout, run.stderr[-2000:])
        return run.stdout

    def test_magic_exports_a_module_that_passes_check_and_test(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = self.magic(tmp, [('"Blur stats" --export lc_tools.py --no-form', CELL_GOOD)] * 2)  # twice
            self.assertIn("exported to lc_tools.py", out)
            text = (Path(tmp) / "lc_tools.py").read_text()
            self.assertEqual(text.count("# >>> lc-tool: blur_stats"), 1, text)  # re-run replaces the block
            self.assertIn('@tool("Blur stats")', text)
            code, report = lc(NUCLEISKY, "check", "--module", "lc_tools", "--pythonpath", tmp)
            self.assertEqual(code, 0, report)
            self.assertIn("blur_stats", report)
            code, report = lc(
                NUCLEISKY, "test", "--module", "lc_tools", "--pythonpath", tmp,
                "--sample", "image=%s" % (ensure_fixtures() / "nucleisky/query.tif"),
            )  # fmt: skip
            self.assertEqual(code, 0, report)

    def test_magic_refuses_names_from_elsewhere_in_the_notebook(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = self.magic(tmp, [("--export lc_tools.py --no-form", CELL_GLOBAL)])
            self.assertIn("uses 'helper', defined elsewhere in the notebook", out)
            self.assertFalse((Path(tmp) / "lc_tools.py").exists())

    def test_ambiguous_cell_and_unknown_function(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = self.magic(tmp, [("--no-form", CELL_TWO), ("--no-form --function b", CELL_TWO)])
            self.assertIn("defines 2 functions (a, b)", out)
            self.assertNotIn("✖ b", out)

    def test_export_notebook_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            nb = Path(tmp) / "nb.ipynb"
            notebook(
                nb,
                [
                    "x = 1\n",
                    '%%lc_tool "Blur stats"\n' + CELL_GOOD,
                    '%%lc_tool --function b\nimport numpy as np\nvalue = 3\nprint("not exported")\n'
                    + CELL_TWO,
                ],
            )
            out_py = Path(tmp) / "lc_tools.py"
            code, out = lc(NUCLEISKY, "export-notebook", str(nb), "--out", str(out_py))
            self.assertEqual(code, 0, out)
            self.assertIn("not exported", out)  # dropped statement is reported, not silently lost
            self.assertIn("blur_stats, b", out)
            code, report = lc(NUCLEISKY, "check", "--module", "lc_tools", "--pythonpath", tmp)
            self.assertEqual(code, 0, report)
            self.assertIn("2 tool(s)", report)

            notebook(nb, ["%%lc_tool\n" + CELL_GLOBAL])  # a broken notebook writes nothing
            out_py.unlink()
            code, out = lc(NUCLEISKY, "export-notebook", str(nb), "--out", str(out_py))
            self.assertEqual(code, 1, out)
            self.assertFalse(out_py.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
