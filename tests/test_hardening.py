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
                [sys.executable, "-m", "venv", "--copies", "--without-pip", str(bare)],
                check=True,
                capture_output=True,
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


class TwoInstallsOfOneApp(unittest.TestCase):
    def test_uninstalling_the_older_install_keeps_the_newer_registration(self):
        home = Path(tempfile.mkdtemp(prefix="lchome_"))
        register(home, "app")  # first install (prefix = GENERIC_PREFIX)
        newer = Path(tempfile.mkdtemp(prefix="lcnewer_"))
        (newer / "bin").mkdir()
        (newer / "bin" / "python").symlink_to(sys.executable)
        done = cli(
            "register", "--name", "app", "--prefix", str(newer), "--module", SYNTHETIC_MODULE, home=home
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        cli(
            "unregister", "--name", "app", "--prefix", str(GENERIC_PREFIX), home=home
        )  # the OLD install is uninstalled
        self.assertTrue((home / "apps" / "app.json").exists(), "newer registration was removed")
        cli("unregister", "--name", "app", "--prefix", str(newer), home=home)
        self.assertFalse((home / "apps" / "app.json").exists())
        register(home, "other")
        cli("unregister", "--name", "other", home=home)  # without --prefix: unconditional, as before
        self.assertFalse((home / "apps" / "other.json").exists())


class Scaling(unittest.TestCase):
    def test_loading_schemas_scans_the_registry_once(self):
        from unittest import mock

        home = Path(tempfile.mkdtemp(prefix="lchome_"))
        old = dict(os.environ)
        try:
            os.environ["LC_HOME"] = str(home)
            for i in range(5):
                registry.register("app%d" % i, sys.prefix, SYNTHETIC_MODULE, "0")
            with mock.patch.object(registry, "load_entries", wraps=registry.load_entries) as scans:
                schemas, _ = registry.load_schemas()
            self.assertEqual(len(schemas), 5)
            self.assertEqual(scans.call_count, 1)
        finally:
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


class RegistryHardening(unittest.TestCase):
    """Findings of the registry audit: planted files, malformed JSON, writable interpreters, hangs, relative LC_HOME."""

    def setUp(self):
        self.home = Path(tempfile.mkdtemp(prefix="lchome_"))
        self._saved = {k: os.environ.get(k) for k in ("LC_HOME", "LC_APPS_PATH")}
        os.environ["LC_HOME"] = str(self.home)
        os.environ["LC_APPS_PATH"] = ""
        self._reset_logger()

    @staticmethod
    def _reset_logger():
        """The log file is chosen when the logger is first used: forget it so the next use follows LC_HOME."""
        import logging

        from labconstrictor_tools import log

        logger = logging.getLogger("labconstrictor")
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
            handler.close()
        log._logger = None

    def tearDown(self):
        self._reset_logger()
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def _entry(self, name="good", **changes):
        folder = registry.apps_dir()
        folder.mkdir(parents=True, exist_ok=True)
        python = registry.python_for(GENERIC_PREFIX)
        entry = {
            "schema": 1, "name": name, "display_name": name, "version": "1", "prefix": str(GENERIC_PREFIX),
            "python": str(python), "module": SYNTHETIC_MODULE, "pythonpath": [], "runtime_path": "",
            "schema_path": str(folder / (name + ".schema.json")),
        }  # fmt: skip
        entry.update(changes)
        (folder / (name + ".json")).write_text(json.dumps(entry))
        (folder / (name + ".schema.json")).write_text(
            json.dumps({"protocol": 1, "tools": [{"id": "t", "label": "T", "inputs": [], "outputs": []}]})
        )
        for path in folder.iterdir():
            path.chmod(0o644)
        return folder

    def test_a_planted_symlink_is_not_followed_when_registering(self):
        victim = self.home / "victim.txt"
        victim.write_text("PRECIOUS")
        folder = registry.apps_dir()
        folder.mkdir(parents=True)
        (folder / "x.json.tmp").symlink_to(victim)
        registry.register("x", GENERIC_PREFIX, SYNTHETIC_MODULE, version="1")
        self.assertEqual(victim.read_text(), "PRECIOUS")
        self.assertEqual(json.loads((folder / "x.json").read_text())["name"], "x")
        self.assertEqual(
            [p.name for p in folder.glob("*.tmp") if p.is_symlink()], ["x.json.tmp"]
        )  # left alone

    def test_a_malformed_entry_is_skipped_with_a_reason_and_good_apps_survive(self):
        self._entry("good")
        folder = self._entry("bad", python=7)
        self._entry("good")  # rewrites nothing of bad
        entries, problems = registry.load_entries()
        self.assertEqual(sorted(entries), ["good"])
        self.assertEqual([name for name, _ in problems], ["bad"])
        self.assertIn("python", problems[0][1])
        (folder / "list.json").write_text("[1, 2]")
        (folder / "list.json").chmod(0o644)
        entries, problems = registry.load_entries()
        self.assertEqual(sorted(entries), ["good"])
        self.assertIn("list", [name for name, _ in problems])

    def test_a_malformed_schema_is_skipped_with_a_reason(self):
        folder = self._entry("good")
        (folder / "good.schema.json").write_text("[]")
        schemas, problems = registry.load_schemas()
        self.assertEqual(schemas, {})
        self.assertEqual(problems, [("good", "schema is not a JSON object")])

    def test_a_schema_outside_the_entry_folder_is_refused(self):
        elsewhere = Path(tempfile.mkdtemp(prefix="elsewhere_"))
        (elsewhere / "s.json").write_text("{}")
        (elsewhere / "s.json").chmod(0o644)
        self._entry("good", schema_path=str(elsewhere / "s.json"))
        entries, problems = registry.load_entries()
        self.assertEqual(entries, {})
        self.assertIn("not in the same folder", problems[0][1])

    @unittest.skipIf(os.name != "posix", "POSIX permissions")
    def test_an_interpreter_folder_writable_by_everybody_is_refused(self):
        prefix = Path(tempfile.mkdtemp(prefix="prefix_"))
        (prefix / "bin").mkdir()
        python = prefix / "bin" / "python"
        python.symlink_to(sys.executable)
        self._entry("ww", prefix=str(prefix), python=str(python))
        (prefix / "bin").chmod(0o777)
        try:
            entries, problems = registry.load_entries()
            self.assertNotIn("ww", entries)
            self.assertIn("writable by everybody", problems[0][1])
            (prefix / "bin").chmod(0o755)
            prefix.chmod(0o755)
            self.assertIn("ww", registry.load_entries()[0])
        finally:
            (prefix / "bin").chmod(0o755)

    def test_unregister_with_an_unreadable_entry_still_removes_it_and_says_so(self):
        from labconstrictor_tools import log

        folder = registry.apps_dir()
        folder.mkdir(parents=True)
        (folder / "junk.json").write_text("{not json")
        self.assertTrue(registry.unregister("junk", prefix="/some/prefix"))
        self.assertFalse((folder / "junk.json").exists())
        self.assertIn("cannot be read", log.tail(20))

    def test_a_hanging_schema_generation_times_out_with_an_explanation(self):
        from unittest import mock

        real_run = subprocess.run

        def hang_on_describe(command, *args, **kwargs):
            if "describe" in command:
                raise subprocess.TimeoutExpired(cmd=command, timeout=1)
            return real_run(command, *args, **kwargs)

        with mock.patch.object(registry.subprocess, "run", side_effect=hang_on_describe):
            with self.assertRaises(RuntimeError) as caught:
                registry.register("slow", GENERIC_PREFIX, SYNTHETIC_MODULE)
        self.assertIn("timed out", str(caught.exception))
        self.assertFalse((registry.apps_dir() / "slow.json").exists())

    def test_a_relative_lc_home_is_made_absolute(self):
        os.environ["LC_HOME"] = "relative_home"
        self.assertTrue(registry.home().is_absolute())

    def test_an_unwritable_log_folder_is_announced_once_on_stderr(self):
        import contextlib
        import io

        from labconstrictor_tools import log

        blocker = self.home / "blocked"
        blocker.write_text("a file where a folder is needed")
        os.environ["LC_HOME"] = str(blocker)
        self._reset_logger()
        stderr = io.StringIO()
        try:
            with contextlib.redirect_stderr(stderr):
                log.error("first")
                log.error("second")
            self.assertEqual(stderr.getvalue().count("cannot write the log file"), 1)
        finally:
            self._reset_logger()
