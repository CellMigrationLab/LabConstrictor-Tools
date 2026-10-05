"""Windows-portable test: run with the app's python.exe (host AND worker are Windows processes). No /proc, no numpy at module level."""

import glob
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

POC = (
    Path(__file__).resolve().parents[2]
)  # the directory holding labconstrictor_tools/ (v3, or C:\\poc under Wine)
sys.path.insert(0, str(POC))
from labconstrictor_tools import client, registry

PREFIX = Path(os.environ.get("LC_TEST_PREFIX") or sys.prefix)  # an environment with numpy, pandas, tifffile
SYNTHETIC = "labconstrictor_tools.examples.synthetic"
R = {
    "platform": sys.platform,
    "host_python": sys.executable,
    "os_name": os.name,
    "pathsep": os.pathsep,
    "home": str(registry.home()),
}


def tmpdirs():
    return set(glob.glob(os.path.join(tempfile.gettempdir(), "lc*")))


class W(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        shutil.rmtree(registry.home(), ignore_errors=True)
        cls.e2 = registry.register("synthetic", PREFIX, SYNTHETIC, "0", [], "Synthetic")

    @classmethod
    def tearDownClass(cls):
        (Path(tempfile.gettempdir()) / "labconstrictor_windows_report.json").write_text(
            json.dumps(R, indent=2, default=str)
        )

    def test_01_layout_and_registry(self):
        R["registry_entry"] = self.e2
        self.assertTrue(self.e2["python"].lower().endswith("python.exe"))
        self.assertTrue(Path(self.e2["python"]).exists())
        R["python_for"] = str(registry.python_for(PREFIX))
        self.assertIn("synthetic", registry.load_all())
        s = registry.schema("synthetic")
        self.assertIn("kitchen_sink", [t["id"] for t in s["tools"]])
        R["schema_cached_bytes"] = Path(self.e2["schema_path"]).stat().st_size

    def run_tool(self, app, tool, inputs, **kw):
        w = client.WorkerProcess(app)
        try:
            return w.task(tool, inputs, **kw).wait(600)
        finally:
            w.close()

    def test_02_isolation_and_scalar(self):
        t = self.run_tool("synthetic", "scalar_echo", {"a": 1.5, "b": 2.0})
        self.assertEqual(t.status, "COMPLETE", t.error)
        d = t.outputs["diagnostics"]
        R["worker_diagnostics"] = d
        self.assertTrue(d["sys.executable"].lower().endswith("python.exe"))

    def test_03_unicode_stdout_and_text(self):
        t = self.run_tool("synthetic", "unicode_echo", {"text": "µm → ✓ naïve"})
        self.assertEqual(t.status, "COMPLETE", t.error)
        self.assertEqual(t.outputs["results"][0]["values"]["text"], "µm → ✓ naïve")
        R["unicode_roundtrip"] = True

    def test_04_paths_with_spaces_and_unicode(self):
        d = Path(tempfile.mkdtemp(prefix="lc dir µ "))
        f = d / "tráck ß data µ.csv"
        f.write_text(
            "Unique_ID,POSITION_T,POSITION_X,POSITION_Y,POSITION_Z\nA,0,0,0,0\nA,1,1,0,0\nA,2,2,0,0\n",
            encoding="utf-8",
        )
        t = self.run_tool("synthetic", "path_info", {"some_file": str(f)})
        self.assertEqual(t.status, "COMPLETE", t.error)
        v = t.outputs["results"][0]["values"]
        self.assertTrue(v["exists"])
        self.assertEqual(v["name"], f.name)
        R["path_with_spaces_unicode"] = v
        t = self.run_tool("synthetic", "table_sum", {"tab": str(f)})
        self.assertEqual(t.status, "COMPLETE", t.error)
        values = t.outputs["results"][0]["values"]
        self.assertEqual(values["columns"][0], "Unique_ID")
        self.assertEqual(values["total"], 6.0)  # POSITION_T and POSITION_X are 0+1+2 each; Y and Z are 0
        R["table_with_unicode_path"] = values
        shutil.rmtree(d, True)
        shutil.rmtree(t.outputs["job_dir"], True)

    def test_05_image_roundtrip(self):
        import numpy as np
        import tifffile

        d = Path(tempfile.mkdtemp())
        a = np.arange(12, dtype=np.uint16).reshape(3, 4)
        tifffile.imwrite(d / "i.tif", a)
        t = self.run_tool(
            "synthetic",
            "kitchen_sink",
            {"required_string": "hi", "image": str(d / "i.tif"), "count": 3, "mode": "gamma"},
        )
        self.assertEqual(t.status, "COMPLETE", t.error)
        r = {x["name"]: x for x in t.outputs["results"]}
        self.assertTrue((tifffile.imread(r["doubled"]["path"]) == a * 2).all())
        R["image_roundtrip"] = True
        shutil.rmtree(t.outputs["job_dir"], True)
        shutil.rmtree(d, True)

    def test_06_progress_and_cooperative_cancel(self):
        ups = []
        w = client.WorkerProcess("synthetic")
        t = w.task("slow", {"seconds": 1.2, "steps": 6}, on_update=lambda m, f: ups.append(m))
        t.wait(60)
        self.assertEqual(t.status, "COMPLETE")
        self.assertGreaterEqual(len(ups), 6)
        R["progress_events"] = len(ups)
        before = tmpdirs()
        t = w.task("slow", {"seconds": 20, "steps": 40})
        time.sleep(1.0)
        t0 = time.time()
        t.cancel()
        t.wait(10)
        self.assertEqual(t.status, "CANCELED")
        R["cooperative_cancel_seconds"] = round(time.time() - t0, 2)
        self.assertEqual(tmpdirs() - before, set())
        t = w.task("scalar_echo", {})
        t.wait(20)
        self.assertEqual(t.status, "COMPLETE")
        w.close()
        R["worker_exit_code_after_stdin_close"] = w.proc.returncode

    def test_07_forced_kill(self):
        w = client.WorkerProcess("synthetic")
        self.assertEqual(
            w.task("scalar_echo", {}).wait(600).status, "COMPLETE"
        )  # worker is up: cancel must reach a RUNNING tool
        t = w.task("stubborn", {"seconds": 60})
        time.sleep(1.0)
        t.cancel()
        t.wait(2.0)
        self.assertEqual(t.status, "RUNNING")
        t0 = time.time()
        w.kill()
        t.wait(5)
        R["forced_kill"] = {
            "status": t.status,
            "returncode": w.proc.returncode,
            "seconds": round(time.time() - t0, 2),
        }
        self.assertIsNotNone(w.proc.returncode)
        self.assertEqual(t.status, "CRASHED")

    def test_08_errors_and_no_arbitrary_code(self):
        t = self.run_tool("synthetic", "explode", {"kind": "exception"})
        self.assertEqual((t.status, t.code), ("FAILED", "ZeroDivisionError"))
        self.assertIn("Traceback", t.traceback)
        marker = Path(tempfile.gettempdir()) / "lc_pwned.txt"
        marker.unlink(missing_ok=True)
        t = self.run_tool("synthetic", "x", {})
        self.assertEqual(t.code, "unknown_tool")
        w = client.WorkerProcess("synthetic")
        import uuid

        tid = str(uuid.uuid4())
        tk = client.Task(w, "x", None)
        tk.id = tid
        w.tasks[tid] = tk
        w.proc.stdin.write(
            json.dumps(
                {
                    "task": tid,
                    "requestType": "EXECUTE",
                    "script": "import pathlib; pathlib.Path(%r).write_text('x')" % str(marker),
                    "inputs": {},
                }
            )
            + "\n"
        )
        w.proc.stdin.flush()
        tk.wait(10)
        self.assertEqual(tk.code, "unknown_tool")
        self.assertFalse(marker.exists())
        w.close()
        R["arbitrary_code_rejected"] = True


if __name__ == "__main__":
    unittest.main(verbosity=2)
