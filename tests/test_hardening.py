"""Regression tests for problems found while testing the bridge from source: NaN, strict JSON, registry priority and trust,
unsafe app names, skipped-app explanations and the message after a forced kill on Cancel. Private LC_HOME for every test.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import _paths  # noqa: F401  (must come first)
from _paths import GENERIC_PREFIX, SYNTHETIC_MODULE, V3
from test_cli_and_registry import cli, register

from labconstrictor_tools import client, convert, registry


class Finite(unittest.TestCase):
    PARAM = {"name": "x", "label": "X", "type": "float", "required": True, "minimum": 0}

    def test_nan_and_inf_are_rejected_not_compared(self):
        for bad in (float("nan"), float("inf"), "nan"):
            with self.assertRaises(convert.ToolError) as caught:
                convert._load_one(self.PARAM, bad)
            self.assertEqual(caught.exception.code, "invalid_parameter")
        self.assertEqual(convert._load_one(self.PARAM, 1.5), 1.5)

    def test_values_survive_strict_json(self):
        import numpy as np

        out = convert._write_one(
            {"type": "values", "name": "v"},
            {
                "n": np.int64(5),
                "f": np.float32(1.5),
                "nan": float("nan"),
                "inf": float("inf"),
                "l": [np.int8(1), float("nan")],
            },
            Path(tempfile.mkdtemp()),
        )
        self.assertEqual(out["values"], {"n": 5, "f": 1.5, "nan": None, "inf": None, "l": [1, None]})
        self.assertIsInstance(out["values"]["n"], int)
        json.dumps(out, allow_nan=False)

    def test_channel_never_writes_nan_tokens(self):
        code = (
            "from labconstrictor_tools.protocol import Channel\n"
            "Channel().send('t', 'COMPLETION', outputs={'v': float('nan'), 'w': [float('inf')]})\n"
        )
        done = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": str(V3)},
        )
        self.assertEqual(
            json.loads(done.stdout, parse_constant=lambda c: self.fail("non-JSON token " + c))["outputs"],
            {"v": None, "w": [None]},
        )


class RegistryNamesAndPriority(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp(prefix="lchome_"))
        self.shared = Path(tempfile.mkdtemp(prefix="lcshared_"))

    def test_unsafe_names_are_refused(self):
        for bad in ("../x", "a/b", "a\\b", "..", ""):
            done = cli(
                "register",
                "--name",
                bad,
                "--prefix",
                str(GENERIC_PREFIX),
                "--module",
                SYNTHETIC_MODULE,
                home=self.home,
            )
            self.assertNotEqual(done.returncode, 0, bad)
            self.assertIn("invalid app name", done.stderr)
        self.assertEqual(list(self.home.rglob("*.json")), [])
        self.assertNotEqual(cli("unregister", "--name", "../x", home=self.home).returncode, 0)

    def test_a_shared_entry_cannot_take_over_a_per_user_name(self):
        register(self.home, "synthetic")
        entry = json.loads((self.home / "apps" / "synthetic.json").read_text())
        (self.shared / "zz.json").write_text(
            json.dumps({**entry, "display_name": "OTHER"})
        )  # file name differs from app name
        os.chmod(self.shared / "zz.json", 0o644)
        env = {"LC_APPS_PATH": str(self.shared)}
        old = dict(os.environ)
        try:
            os.environ.update(LC_HOME=str(self.home), **env)
            self.assertEqual(registry.load_all()["synthetic"].get("display_name"), "synthetic")
        finally:
            os.environ.clear()
            os.environ.update(old)

    @unittest.skipUnless(
        os.name == "posix" and os.getuid() == 0, "needs root to create a file owned by someone else"
    )
    def test_foreign_owned_or_group_writable_shared_entry_is_skipped(self):
        register(self.home, "synthetic")
        source = self.home / "apps"
        for name in ("synthetic.json", "synthetic.schema.json"):
            (self.shared / name).write_text((source / name).read_text())
        (self.home / "apps" / "synthetic.json").unlink()
        old = dict(os.environ)
        try:
            os.environ.update(LC_HOME=str(self.home), LC_APPS_PATH=str(self.shared))
            os.chmod(self.shared / "synthetic.json", 0o666)  # world writable
            entries, problems = registry.load_entries()
            self.assertNotIn("synthetic", entries)
            self.assertIn("writable by other users", dict(problems)["synthetic"])
            os.chmod(self.shared / "synthetic.json", 0o644)
            os.chown(self.shared / "synthetic.json", 65534, 65534)  # nobody
            registry._LOGGED_PROBLEMS.clear()
            entries, problems = registry.load_entries()
            self.assertNotIn("synthetic", entries)
            self.assertIn("not owned", dict(problems)["synthetic"])
            os.chown(self.shared / "synthetic.json", 0, 0)  # root-owned (an administrator): fine
            self.assertIn("synthetic", registry.load_entries()[0])
        finally:
            os.environ.clear()
            os.environ.update(old)


class SkippedAppsAreExplained(unittest.TestCase):
    def test_cli_and_client_say_why_an_app_cannot_be_used(self):
        home = Path(tempfile.mkdtemp(prefix="lchome_"))
        prefix = Path(tempfile.mkdtemp(prefix="lcprefix_"))
        (prefix / "bin").mkdir()
        (prefix / "bin" / "python").symlink_to(sys.executable)
        done = cli(
            "register", "--name", "doomed", "--prefix", str(prefix), "--module", SYNTHETIC_MODULE, home=home
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        (prefix / "bin" / "python").unlink()
        ran = cli("run", "doomed", "scalar_echo", home=home)
        self.assertIn("interpreter", ran.stderr)
        self.assertNotIn("unknown app", ran.stderr)
        old = dict(os.environ)
        try:
            os.environ["LC_HOME"] = str(home)
            with self.assertRaises(client.WorkerStartError) as caught:
                client.WorkerProcess("doomed")
            self.assertIn("is missing", str(caught.exception))
            with self.assertRaises(client.WorkerStartError) as caught:
                client.WorkerProcess("never-registered")
            self.assertIn("not registered", str(caught.exception))
        finally:
            os.environ.clear()
            os.environ.update(old)


class CancelThatHadToKill(unittest.TestCase):
    def test_message_blames_the_tool_not_the_oom_killer(self):
        home = Path(tempfile.mkdtemp(prefix="lchome_"))
        register(home, "synthetic")
        old = dict(os.environ)
        try:
            os.environ["LC_HOME"] = str(home)
            import threading

            with client.WorkerProcess("synthetic") as worker:
                task = worker.task("stubborn", {"seconds": 60})
                task.launched.wait(10)
                task.cancel()
                threading.Timer(1.0, worker.kill).start()
                task.wait(20)
            self.assertEqual(task.status, "CRASHED")
            self.assertIn("did not stop when Cancel was pressed", task.error)
            self.assertNotIn("out of memory", task.error)
        finally:
            os.environ.clear()
            os.environ.update(old)


if __name__ == "__main__":
    unittest.main()
