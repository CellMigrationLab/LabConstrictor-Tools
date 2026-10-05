"""Regression tests for problems found while testing the bridge from source: NaN, strict JSON, registry priority and trust,
unsafe app names, skipped-app explanations and the message after a forced kill on Cancel. Private LC_HOME for every test.
"""

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
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


def _drain(stream, sink):
    for line in stream:
        sink.append(line)


class WorkerSurvivesGarbage(unittest.TestCase):
    def test_non_object_json_lines_do_not_make_the_worker_deaf(self):
        env = {**os.environ, "PYTHONPATH": str(V3)}
        for junk in (b"[1,2,3]\n", b"42\n", b"null\n", b'"str"\n', b"\xff\xfe\n", b"{broken\n"):
            p = subprocess.Popen(
                [sys.executable, "-m", "labconstrictor_tools", "serve", "--module", SYNTHETIC_MODULE],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env,
            )  # fmt: skip
            try:
                request = {
                    "task": "good",
                    "requestType": "EXECUTE",
                    "script": "lc:scalar_echo",
                    "inputs": {"a": 1, "b": 2},
                }
                p.stdin.write(junk + json.dumps(request).encode() + b"\n")
                p.stdin.flush()
                answered = False
                lines = []
                threading.Thread(target=_drain, args=(p.stdout, lines), daemon=True).start()
                end = time.time() + 10
                while not answered and time.time() < end:
                    answered = any(b"COMPLETION" in line for line in lines)
                    time.sleep(0.1)
                self.assertTrue(answered, "worker went deaf after %r" % junk)
            finally:
                p.kill()


class ProcessHygiene(unittest.TestCase):
    def test_a_tools_child_process_dies_with_the_worker(self):
        import psutil

        folder = Path(tempfile.mkdtemp(prefix="lcmod_"))
        (folder / "spawner_lc_tools.py").write_text(
            "import subprocess, sys\nfrom labconstrictor_tools import Scalars, tool\n\n"
            "@tool('Spawn')\ndef spawn() -> Scalars:\n"
            "    child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])\n"
            "    return {'pid': child.pid}\n"
        )
        old = dict(os.environ)
        try:
            os.environ["LC_HOME"] = tempfile.mkdtemp(prefix="lchome_")
            with client.WorkerProcess(module="spawner_lc_tools", pythonpath=[folder]) as worker:
                pid = worker.task("spawn", {}).wait(30).outputs["results"][0]["values"]["pid"]
                self.assertTrue(psutil.pid_exists(pid))
            time.sleep(1)
            self.assertFalse(
                psutil.pid_exists(pid) and psutil.Process(pid).status() != "zombie",
                "child outlived the worker",
            )
        finally:
            os.environ.clear()
            os.environ.update(old)

    def test_worker_stderr_kept_by_the_host_is_bounded(self):
        tail = client._Tail()
        for _ in range(50):
            tail.append("e" * 100_000 + "\n")
        kept = sum(len(x) for x in tail)
        self.assertLess(kept, client._Tail.LIMIT + 200_000)
        self.assertTrue(list(tail)[-1].startswith("e"))


class RuntimeDoesNotLeakIntoTheApp(unittest.TestCase):
    def test_runtime_path_is_only_added_when_the_app_lacks_the_package(self):
        home = Path(tempfile.mkdtemp(prefix="lchome_"))
        old = dict(os.environ)
        try:
            os.environ["LC_HOME"] = str(home)
            has = registry.register("has", sys.prefix, SYNTHETIC_MODULE, "0")
            self.assertEqual(
                has["runtime_path"], ""
            )  # Tools is installed in this environment: nothing to inject
            bare = Path(tempfile.mkdtemp(prefix="lcbare_")) / "env"
            subprocess.run(
                [sys.executable, "-m", "venv", "--without-pip", str(bare)], check=True, capture_output=True
            )
            lacking = registry.register("lacking", bare, SYNTHETIC_MODULE, "0")
            self.assertEqual(
                lacking["runtime_path"], registry.runtime_path()
            )  # an app without the package still works
            with client.WorkerProcess("lacking") as worker:
                self.assertEqual(worker.task("scalar_echo", {"a": 1, "b": 2}).wait(60).status, "COMPLETE")
        finally:
            os.environ.clear()
            os.environ.update(old)


class UmaskDoesNotBreakOwnEntries(unittest.TestCase):
    @unittest.skipUnless(os.name == "posix", "POSIX permissions")
    def test_entries_registered_under_umask_002_are_still_trusted(self):
        home = Path(tempfile.mkdtemp(prefix="lchome_"))
        previous = os.umask(0o002)
        old = dict(os.environ)
        try:
            os.environ["LC_HOME"] = str(home)
            registry.register("mine", sys.prefix, SYNTHETIC_MODULE, "0")
            self.assertIn("mine", registry.load_all())
            self.assertEqual((home / "apps" / "mine.json").stat().st_mode & 0o022, 0)
        finally:
            os.umask(previous)
            os.environ.clear()
            os.environ.update(old)


class Races(unittest.TestCase):
    def test_entry_unregistered_during_a_scan_is_not_reported_as_broken(self):
        from unittest import mock

        home = Path(tempfile.mkdtemp(prefix="lchome_"))
        register(home, "synthetic")
        old = dict(os.environ)
        try:
            os.environ["LC_HOME"] = str(home)
            real = Path.read_text

            def vanished(self, *a, **k):
                if self.name == "synthetic.json":
                    raise FileNotFoundError(2, "gone", str(self))
                return real(self, *a, **k)

            with mock.patch.object(Path, "read_text", vanished):
                entries, problems = registry.load_entries()
            self.assertEqual((entries, problems), ({}, []))
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


class NarrowConsoles(unittest.TestCase):
    def test_status_symbols_do_not_crash_on_a_cp1252_stdout(self):
        """Found on windows-latest CI: UnicodeEncodeError for the check mark printed by check/test/support-bundle."""
        env = {
            **os.environ,
            "LC_HOME": tempfile.mkdtemp(prefix="lchome_"),
            "PYTHONPATH": str(V3),
            "PYTHONIOENCODING": "cp1252",
        }
        done = subprocess.run(
            [sys.executable, "-m", "labconstrictor_tools", "check", "--module", SYNTHETIC_MODULE],
            capture_output=True, text=True, encoding="cp1252", env=env,
        )  # fmt: skip
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertNotIn("UnicodeEncodeError", done.stderr)


if __name__ == "__main__":
    unittest.main()
