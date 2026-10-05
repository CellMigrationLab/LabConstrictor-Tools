"""Generic integration tests with synthetic tools (no scientific code). Host python needs numpy+tifffile only."""

import glob
import json
import os
import tempfile
import time
import unittest
from pathlib import Path

import _paths  # noqa: F401  (must come first)
import numpy as np
import tifffile
from _paths import EVIDENCE as EV

from labconstrictor_tools import client

REPORT = {}


def jobdirs():
    return set(glob.glob(os.path.join(tempfile.gettempdir(), "lcjob_*")))


class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = client.WorkerProcess("synthetic")

    @classmethod
    def tearDownClass(cls):
        cls.w.close()
        (EV / "generic_integration.json").write_text(json.dumps(REPORT, indent=2, default=str))

    def run_tool(self, tool, inputs, **kw):
        return self.w.task(tool, inputs, **kw).wait(60)

    def test_1_scalar_to_scalar(self):
        t = self.run_tool("scalar_echo", {"a": 1.5, "b": 2.0})
        self.assertEqual(t.status, "COMPLETE")
        self.assertEqual(t.outputs["results"][0]["values"]["sum"], 3.5)
        REPORT["interpreter"] = t.outputs["diagnostics"]
        # the tool ran in a separate worker process in the app's interpreter (a different one when the app has its own env)
        self.assertTrue(t.outputs["diagnostics"]["sys.executable"])
        self.assertNotEqual(t.outputs["diagnostics"].get("pid"), os.getpid())

    def test_2_image_table_scalars(self):
        d = Path(tempfile.mkdtemp())
        a = np.arange(12, dtype=np.uint16).reshape(3, 4)
        tifffile.imwrite(d / "i.tif", a)
        t = self.run_tool(
            "kitchen_sink",
            {
                "required_string": "hi",
                "image": str(d / "i.tif"),
                "count": 4,
                "mode": "gamma",
                "scale": 0.25,
                "flag": False,
            },
        )
        self.assertEqual(t.status, "COMPLETE", t.error)
        r = {x["name"]: x for x in t.outputs["results"]}
        self.assertTrue((tifffile.imread(r["doubled"]["path"]) == a * 2).all())
        self.assertEqual(r["doubled"]["axes"], "YX")
        rows = open(r["rows"]["path"]).read().strip().splitlines()
        self.assertEqual(len(rows), 5)
        self.assertEqual(r["summary"]["values"]["mode"], "gamma")
        self.assertFalse(r["summary"]["values"]["flag"])
        self.assertFalse(r["summary"]["values"]["had_optional_image"])
        self.assertTrue(os.path.isdir(t.outputs["job_dir"]))  # host owns cleanup of successful jobs

    def test_3_table_in(self):
        d = Path(tempfile.mkdtemp())
        (d / "t.csv").write_text("a,b\n1,2\n3,4\n")
        t = self.run_tool("table_sum", {"tab": str(d / "t.csv")})
        self.assertEqual(t.outputs["results"][0]["values"], {"columns": ["a", "b"], "total": 10.0})

    def test_4_validation_errors(self):
        d = Path(tempfile.mkdtemp())
        tifffile.imwrite(d / "i.tif", np.zeros((2, 2), np.uint8))
        base = {"required_string": "x", "image": str(d / "i.tif")}
        for bad, code in (
            ({"count": 0}, "invalid_parameter"),
            ({"count": 11}, "invalid_parameter"),
            ({"mode": "zeta"}, "invalid_parameter"),
            ({"count": 2.5}, "invalid_parameter"),
        ):
            t = self.run_tool("kitchen_sink", {**base, **bad})
            self.assertEqual((t.status, t.code), ("FAILED", code), (bad, t.error))
        t = self.run_tool("kitchen_sink", {"image": str(d / "i.tif")})
        self.assertEqual((t.status, t.code), ("FAILED", "missing_parameter"))
        REPORT["validation_example"] = t.error

    def test_5_errors(self):
        t = self.run_tool("explode", {"kind": "tool_error"})
        self.assertEqual((t.status, t.code), ("FAILED", "expected_failure"))
        t = self.run_tool("explode", {"kind": "exception"})
        self.assertEqual((t.status, t.code), ("FAILED", "ZeroDivisionError"))
        self.assertIn("Traceback", t.traceback)
        self.assertEqual(self.run_tool("scalar_echo", {}).status, "COMPLETE")  # worker survives failures

    def test_6_progress(self):
        ups = []
        t = self.run_tool("slow", {"seconds": 1.2, "steps": 6}, on_update=lambda m, f: ups.append((m, f)))
        self.assertEqual(t.status, "COMPLETE")
        self.assertGreaterEqual(len(ups), 6)
        self.assertEqual(ups[0][0], "step 1 of 6")
        self.assertEqual(ups[-1][1], 1.0)
        REPORT["progress_events"] = ups

    def test_7_cooperative_cancel_no_leaks(self):
        before = jobdirs()
        t = self.w.task("slow", {"seconds": 20, "steps": 40})
        time.sleep(1.0)
        t0 = time.time()
        t.cancel()
        t.wait(10)
        self.assertEqual(t.status, "CANCELED")
        dt = time.time() - t0
        self.assertLess(dt, 2.0)
        self.assertEqual(jobdirs() - before, set())  # worker removed its own temp dir
        self.assertEqual(self.run_tool("scalar_echo", {}).status, "COMPLETE")  # same worker still usable
        REPORT["cooperative_cancel_seconds"] = round(dt, 3)

    def test_8_stubborn_cancel_kill(self):
        w = client.WorkerProcess("synthetic")
        t = w.task("stubborn", {"seconds": 60})
        time.sleep(1.0)
        t.cancel()
        t.wait(2.0)
        self.assertEqual(t.status, "RUNNING")  # worker cannot honour cancel
        pid = w.proc.pid
        t0 = time.time()
        w.kill()  # host escalates
        t.wait(5)
        self.assertIn(t.status, ("CRASHED",))
        time.sleep(0.2)
        self.assertFalse(os.path.exists("/proc/%d" % pid))
        REPORT["forced_kill_seconds"] = round(time.time() - t0, 3)

    def test_8b_declared_axes_are_enforced(self):
        d = Path(tempfile.mkdtemp())
        tifffile.imwrite(d / "stack.tif", np.zeros((3, 4, 5), np.uint8))
        tifffile.imwrite(d / "plane.tif", np.ones((4, 5), np.uint8))
        bad = self.run_tool("plane_mean", {"image": str(d / "stack.tif")})
        self.assertEqual((bad.status, bad.code), ("FAILED", "wrong_dimensions"))
        self.assertIn("2D image (YX) but got 3D", bad.error)
        good = self.run_tool("plane_mean", {"image": str(d / "plane.tif")})
        self.assertEqual(good.status, "COMPLETE")
        REPORT["wrong_dimensions_message"] = bad.error

    def test_9_no_arbitrary_code(self):
        marker = Path(tempfile.gettempdir()) / "lc_pwned"
        marker.unlink(missing_ok=True)
        task = self.w.task.__self__  # noqa
        import json as j
        import uuid

        tid = str(uuid.uuid4())
        tk = client.Task(self.w, "x", None)
        tk.id = tid
        self.w.tasks[tid] = tk
        self.w.proc.stdin.write(
            j.dumps(
                {
                    "task": tid,
                    "requestType": "EXECUTE",
                    "script": "import pathlib; pathlib.Path('%s').write_text('x')" % marker,
                    "inputs": {},
                }
            )
            + "\n"
        )
        self.w.proc.stdin.flush()
        tk.wait(10)
        self.assertEqual((tk.status, tk.code), ("FAILED", "unknown_tool"))
        self.assertFalse(marker.exists())
        t = self.run_tool("not_a_tool", {})
        self.assertEqual((t.status, t.code), ("FAILED", "unknown_tool"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
