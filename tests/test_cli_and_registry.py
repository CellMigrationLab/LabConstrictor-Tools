"""Command-line tools, registry search path, trust checks and `doctor`. Uses a throw-away LC_HOME for every test."""

import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import _paths  # noqa: F401  (must come first)
from _paths import FIXTURES as FX
from _paths import GENERIC_PREFIX, SYNTHETIC_MODULE, V3

CLI = [sys.executable, "-m", "labconstrictor_tools"]


def cli(*args, home, extra_env=None, input_dir=None):
    env = {**os.environ, "LC_HOME": str(home), "LC_APPS_PATH": "", "PYTHONPATH": str(V3), **(extra_env or {})}
    return subprocess.run([*CLI, *args], capture_output=True, text=True, env=env, cwd=input_dir)


def register(home, name, *extra):
    """Register the example app (synthetic tools, interpreter = the one running the tests) under `name`."""
    result = cli(
        "register", "--name", name, "--prefix", str(GENERIC_PREFIX), "--module", SYNTHETIC_MODULE,
        "--version", "1", *extra, home=home,
    )  # fmt: skip
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


class CliAndRegistry(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp(prefix="lchome_"))

    def test_list_and_run_without_a_gui(self):
        register(self.home, "synthetic")
        listed = json.loads(cli("list", "--json", home=self.home).stdout)
        self.assertIn("table_sum", [t["id"] for t in listed["apps"]["synthetic"]["tools"]])
        ran = cli("run", "synthetic", "table_sum", "tab=%s" % (FX / "celltracks/tracks.csv"), home=self.home)
        self.assertEqual(ran.returncode, 0, ran.stderr)
        report = json.loads(ran.stdout)
        self.assertEqual(report["status"], "COMPLETE")
        values = report["results"][0]["values"]
        self.assertIn("Unique_ID", values["columns"])
        out = self.home / "results"
        again = cli(
            "run", "synthetic", "kitchen_sink", "required_string=x", "image=%s" % (FX / "celltracks/tracks.csv"),
            "--out", str(out), home=self.home,
        )  # fmt: skip
        self.assertEqual(
            json.loads(again.stdout)["status"], "FAILED"
        )  # a CSV is not an image: a clear failure, not a crash

    def test_every_run_leaves_a_record(self):
        register(self.home, "synthetic")
        cli("run", "synthetic", "scalar_echo", "a=1", "b=2", home=self.home)
        cli("run", "synthetic", "explode", "kind=tool_error", home=self.home)
        records = sorted((self.home / "runs").glob("*/run.json"))
        self.assertEqual(len(records), 2)
        ok, failed = (json.loads(r.read_text()) for r in records)
        self.assertEqual(
            (ok["status"], failed["status"], failed["code"]), ("COMPLETE", "FAILED", "expected_failure")
        )
        self.assertEqual(ok["inputs"], {"a": 1.0, "b": 2.0})
        self.assertTrue(ok["interpreter"]["sys.executable"])
        norecord = cli("run", "synthetic", "scalar_echo", "--no-record", home=self.home)
        self.assertEqual(norecord.returncode, 0)
        self.assertEqual(len(list((self.home / "runs").glob("*/run.json"))), 2)

    def test_run_errors_are_helpful(self):
        register(self.home, "synthetic")
        missing = cli(
            "run", "synthetic", "kitchen_sink", "required_string=x", home=self.home
        )  # image is required
        self.assertEqual(missing.returncode, 1)
        self.assertIn("missing_parameter", missing.stdout)
        unknown = cli("run", "synthetic", "kitchen_sink", "bogus=1", home=self.home)
        self.assertNotEqual(unknown.returncode, 0)
        self.assertIn("parameters (name=value)", unknown.stderr)
        badnumber = cli("run", "synthetic", "scalar_echo", "a=abc", home=self.home)
        self.assertIn("expected a float", badnumber.stderr)
        self.assertNotIn("Traceback", badnumber.stderr)

    def test_check_flags_heavy_imports_and_bad_declarations(self):
        d = Path(tempfile.mkdtemp())
        (d / "heavy_tools.py").write_text(
            "import numpy\nfrom labconstrictor_tools import tool, Scalars\n@tool()\ndef t(a: int = 1) -> Scalars:\n    return {}\n"
        )
        heavy = cli("check", "--module", "heavy_tools", "--pythonpath", str(d), home=self.home)
        self.assertEqual(heavy.returncode, 0)
        self.assertIn("numpy", heavy.stdout.split("⚠")[1])
        (d / "bad_tools.py").write_text(
            "from labconstrictor_tools import tool\n@tool()\ndef t(x):\n    pass\n"
        )
        bad = cli("check", "--module", "bad_tools", "--pythonpath", str(d), home=self.home)
        self.assertEqual(bad.returncode, 1)
        self.assertIn("no type annotation", bad.stdout)

    def test_doctor_reports_healthy_stale_and_broken_installs(self):
        register(self.home, "synthetic")
        self.assertEqual(cli("doctor", home=self.home).returncode, 0)
        schema_path = self.home / "apps" / "synthetic.schema.json"
        schema = json.loads(schema_path.read_text())
        schema["tools"].pop()  # the app gained a tool since registration
        schema_path.write_text(json.dumps(schema))
        stale = cli("doctor", home=self.home)
        self.assertEqual(stale.returncode, 0)
        self.assertIn("stale", stale.stdout)
        entry_path = self.home / "apps" / "synthetic.json"
        entry = json.loads(entry_path.read_text())
        entry["python"] = str(self.home / "gone" / "python")
        entry_path.write_text(json.dumps(entry))
        broken = cli("doctor", home=self.home)
        self.assertEqual(broken.returncode, 1)
        self.assertIn("not available on this machine", broken.stdout)

    def test_entries_pointing_outside_their_prefix_or_writable_by_others_are_ignored(self):
        register(self.home, "synthetic")
        entry_path = self.home / "apps" / "synthetic.json"
        original = entry_path.read_text()
        entry = json.loads(original)
        entry["python"] = "/bin/sh"  # a planted entry trying to make the host start an arbitrary program
        entry_path.write_text(json.dumps(entry))
        out = cli("doctor", "--json", home=self.home)
        self.assertIn("not inside the install prefix", out.stdout)
        entry_path.write_text(original)
        entry_path.chmod(entry_path.stat().st_mode | stat.S_IWOTH)
        out = cli("doctor", "--json", home=self.home)
        self.assertIn("writable by other users", out.stdout)

    def test_shared_registry_directory_and_user_override(self):
        shared = Path(tempfile.mkdtemp(prefix="shared_"))
        register(self.home, "shared_app", "--dir", str(shared))
        none_visible = cli("list", home=self.home)
        self.assertNotIn("shared_app", none_visible.stdout)
        visible = cli("list", home=self.home, extra_env={"LC_APPS_PATH": str(shared)})
        self.assertIn("shared_app", visible.stdout)
        register(self.home, "shared_app", "--display-name", "my own copy")
        override = json.loads(
            cli("list", "--json", home=self.home, extra_env={"LC_APPS_PATH": str(shared)}).stdout
        )
        self.assertEqual(
            override["apps"]["shared_app"]["application"], "my own copy"
        )  # the per-user entry wins

    def test_init_writes_a_module_that_passes_check(self):
        d = Path(tempfile.mkdtemp())
        made = cli("init", str(d / "starter_tools.py"), home=self.home)
        self.assertEqual(made.returncode, 0, made.stderr)
        checked = cli("check", "--module", "starter_tools", "--pythonpath", str(d), home=self.home)
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        self.assertNotIn(
            "⚠", checked.stdout
        )  # the template itself keeps its heavy imports inside the function
        self.assertNotEqual(
            cli("init", str(d / "starter_tools.py"), home=self.home).returncode, 0
        )  # never overwrite


if __name__ == "__main__":
    unittest.main(verbosity=2)
