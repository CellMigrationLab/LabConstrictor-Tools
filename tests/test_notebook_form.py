"""The notebook front-end: build the form from a declaration and run it in-process, inside an app's own interpreter."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import _paths  # noqa: F401  (must come first)
from _paths import FIXTURES as FX
from _paths import V3

SCRIPT = """
import json, sys, importlib
tools = importlib.import_module("labconstrictor_tools.examples.synthetic")
from labconstrictor_tools.notebook import ToolForm
f = ToolForm(tools.{fn})
out = {{"controls": {{k: type(v).__name__ for k, v in f.controls.items()}}}}
for name, value in {values!r}.items():
    f.controls[name].value = value
results = f.run()
out["results"] = None if results is None else [(r["type"], r["name"]) for r in results]
out["status"] = f.status.value
print("JSON:" + json.dumps(out))
"""


def in_app(function, values):
    code = SCRIPT.format(fn=function, values=values)
    env = {**os.environ, "PYTHONPATH": str(V3), "PYTHONNOUSERSITE": "1", "MPLBACKEND": "Agg"}
    run = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env=env,
    )
    line = [ln for ln in run.stdout.splitlines() if ln.startswith("JSON:")]
    assert line, run.stderr[-2000:]
    return json.loads(line[0][5:])


class NotebookForm(unittest.TestCase):
    def test_table_tool_runs_in_the_notebook_kernel(self):
        out = in_app("table_sum", {"tab": str(FX / "celltracks/tracks.csv")})
        self.assertEqual(out["controls"], {"tab": "Text"})
        self.assertEqual(out["results"], [["values", "values"]])
        self.assertIn("done", out["status"])

    def test_every_control_type_and_shared_validation(self):
        d = Path(tempfile.mkdtemp())
        import numpy as np
        import tifffile

        tifffile.imwrite(d / "i.tif", np.ones((4, 5), np.uint16))
        values = {
            "required_string": "hi",
            "image": str(d / "i.tif"),
            "count": 4,
            "mode": "gamma",
            "flag": False,
        }
        out = in_app("kitchen_sink", values)
        self.assertEqual(out["controls"]["count"], "BoundedIntText")
        self.assertEqual(out["controls"]["mode"], "Dropdown")
        self.assertEqual(out["controls"]["flag"], "Checkbox")
        self.assertEqual([r[0] for r in out["results"]], ["image", "table", "values"])
        missing = in_app("kitchen_sink", {"required_string": "hi"})  # no image: same message as everywhere
        self.assertIsNone(missing["results"])
        self.assertIn("missing_parameter", missing["status"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
