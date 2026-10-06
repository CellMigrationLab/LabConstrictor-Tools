"""Regression tests for problems found in the second source test run: a damaged TIFF that tifffile reads as an empty array,
worker pipes that were never closed, and --pythonpath being shadowed by the host interpreter's site-packages.
"""

import gc
import os
import sys
import tempfile
import time
import unittest
import warnings
from pathlib import Path

import _paths  # noqa: F401  (must come first)

from labconstrictor_tools import client, convert
from labconstrictor_tools.types import ToolError


class Run2(unittest.TestCase):
    def test_tiff_with_bad_first_page_offset_is_an_error_not_an_empty_image(self):
        path = Path(tempfile.mkdtemp()) / "damaged.tif"
        path.write_bytes(b"II*\x00garbage not a tiff")
        with self.assertRaises(ToolError) as caught:
            convert._read_image(str(path))
        self.assertEqual(caught.exception.code, "unreadable_image")

    def test_worker_pipes_are_closed_when_the_worker_ends(self):
        from _paths import SYNTHETIC_MODULE

        with warnings.catch_warnings(record=True) as seen:
            warnings.simplefilter("always", ResourceWarning)
            with client.WorkerProcess(module=SYNTHETIC_MODULE) as worker:
                proc = worker.proc
                task = worker.task("scalar_echo", {"a": 1, "b": 2})
                task.wait(60)
            worker._stderr_thread.join(5)
            for _ in range(50):  # the reader threads close the pipes when they see EOF
                if proc.stdout.closed and proc.stderr.closed:
                    break
                import time

                time.sleep(0.1)
            del worker, task
            gc.collect()
        self.assertTrue(proc.stdout.closed and proc.stderr.closed)
        self.assertEqual([str(w.message) for w in seen if issubclass(w.category, ResourceWarning)], [])

    def test_pythonpath_comes_before_the_runtime_path(self):
        folder = Path(tempfile.mkdtemp())
        (folder / "shadow_lc_tools.py").write_text(
            "from labconstrictor_tools import Scalars, tool\n"
            "@tool('Where')\n"
            "def where() -> Scalars:\n"
            "    import os\n"
            "    return {'pythonpath': os.environ['PYTHONPATH'].split(os.pathsep)[0]}\n"
        )
        with client.WorkerProcess(module="shadow_lc_tools", pythonpath=[str(folder)]) as worker:
            task = worker.task("where", {})
            task.wait(60)
        self.assertEqual(task.status, "COMPLETE", task.error)
        first = task.outputs["results"][0]["values"]["pythonpath"]
        self.assertEqual(Path(first).resolve(), folder.resolve())


class Schema(unittest.TestCase):
    def test_nullable_and_folder_in_the_manifest(self):
        from pathlib import Path as P
        from typing import Annotated, Optional

        from labconstrictor_tools import Folder, Min, Scalars
        from labconstrictor_tools.decorators import tool
        from labconstrictor_tools.introspection import describe_tool

        @tool("T", id="nullable_probe")
        def t(
            a: Optional[int] = None,
            b: Annotated[float, Min(0)] = 1.0,
            c: Optional[str] = None,
            d: Optional[Folder] = None,
            e: Optional[P] = None,
        ) -> Scalars:
            return {}

        by = {p["name"]: p for p in describe_tool(t.__lc_tool__)["inputs"]}
        self.assertTrue(
            by["a"]["nullable"] and by["c"]["nullable"] and by["d"]["nullable"] and by["e"]["nullable"]
        )
        self.assertNotIn("nullable", by["b"])
        self.assertEqual((by["d"]["type"], by["e"]["type"]), ("folder", "file"))

    def test_folder_input_must_be_a_directory(self):
        param = {"name": "f", "label": "F", "type": "folder", "required": True}
        self.assertEqual(convert._load_one(param, tempfile.gettempdir()), Path(tempfile.gettempdir()))
        with self.assertRaises(ToolError) as caught:
            convert._load_one(param, "/definitely/not/here")
        self.assertEqual(caught.exception.code, "folder_not_found")


class Hardening(unittest.TestCase):
    @unittest.skipIf(sys.version_info < (3, 11), "PYTHONSAFEPATH needs Python 3.11+")
    def test_host_cwd_does_not_shadow_the_tools_imports(self):
        cwd = Path(tempfile.mkdtemp())
        (cwd / "colorsys.py").write_text("SHADOWED = True\n")
        tools = Path(tempfile.mkdtemp())
        (tools / "cwd_probe_lc_tools.py").write_text(
            "from labconstrictor_tools import Scalars, tool\n"
            "@tool('Probe')\n"
            "def probe() -> Scalars:\n"
            "    import colorsys\n"
            "    return {'shadowed': hasattr(colorsys, 'SHADOWED')}\n"
        )
        before = os.getcwd()
        os.chdir(cwd)
        try:
            with client.WorkerProcess(module="cwd_probe_lc_tools", pythonpath=[str(tools)]) as worker:
                task = worker.task("probe", {})
                task.wait(60)
        finally:
            os.chdir(before)
        self.assertEqual(task.status, "COMPLETE", task.error)
        self.assertFalse(task.outputs["results"][0]["values"]["shadowed"])

    @unittest.skipIf(os.name != "posix", "POSIX path semantics")
    def test_a_filesystem_root_is_not_an_install_prefix(self):
        from labconstrictor_tools import registry

        folder = Path(tempfile.mkdtemp())
        entry_file = folder / "evil.json"
        entry_file.write_text("{}")
        os.chmod(entry_file, 0o644)
        reason = registry._untrusted_reason(entry_file, {"prefix": "/", "python": sys.executable})
        self.assertIn("filesystem root", reason or "")

    def test_cli_results_go_to_a_known_folder_and_old_ones_are_pruned(self):
        from labconstrictor_tools import cli, registry

        os.environ["LC_HOME"] = tempfile.mkdtemp()
        try:
            for _ in range(cli.RESULTS_KEPT + 5):
                folder = cli._new_results_dir("a", "t")
                folder.mkdir(parents=True, exist_ok=True)
                (folder / "x").write_text("1")
                time.sleep(0.002)
                folder.rename(folder.with_name(folder.name + "_%d" % int(time.time() * 1000)))
            kept = list((registry.home() / "results").iterdir())
            self.assertLessEqual(len(kept), cli.RESULTS_KEPT)
        finally:
            os.environ.pop("LC_HOME", None)


class Presentation(unittest.TestCase):
    def test_group_advanced_and_enabled_when_in_the_manifest(self):
        from typing import Annotated, Literal, Optional

        from labconstrictor_tools import Advanced, EnabledWhen, Group, Scalars
        from labconstrictor_tools.decorators import tool
        from labconstrictor_tools.introspection import DeclarationError, describe_tool

        @tool("P", id="presentation_probe")
        def p(
            mode: Annotated[Literal["a", "b"], Group("Main")] = "a",
            fixed_seed: Annotated[bool, Group("Advanced seed"), Advanced()] = False,
            seed: Annotated[Optional[int], Advanced(), EnabledWhen("fixed_seed")] = None,
            extra: Annotated[int, EnabledWhen("mode", "b")] = 1,
        ) -> Scalars:
            return {}

        by = {i["name"]: i for i in describe_tool(p.__lc_tool__)["inputs"]}
        self.assertEqual(by["mode"]["group"], "Main")
        self.assertTrue(by["fixed_seed"]["advanced"] and by["seed"]["advanced"])
        self.assertNotIn("advanced", by["mode"])
        self.assertEqual(by["seed"]["enabled_when"], {"param": "fixed_seed"})
        self.assertEqual(by["extra"]["enabled_when"], {"param": "mode", "equals": ["b"]})

        @tool("Q", id="presentation_probe_bad")
        def q(a: Annotated[int, EnabledWhen("nope")] = 1) -> Scalars:
            return {}

        with self.assertRaises(DeclarationError):
            describe_tool(q.__lc_tool__)


class QuietFailuresAreVisible(unittest.TestCase):
    """Failures that used to vanish are now in the log (or on stderr, which the host logs)."""

    @staticmethod
    def _reset_logger():
        """The log file is chosen when the logger is first used: forget it so the next use follows LC_HOME."""
        import logging

        from labconstrictor_tools import log

        lg = logging.getLogger("labconstrictor")
        for handler in list(lg.handlers):
            lg.removeHandler(handler)
            handler.close()
        log._logger = None

    def setUp(self):
        self._saved = os.environ.get("LC_HOME")
        os.environ["LC_HOME"] = tempfile.mkdtemp()
        self._reset_logger()

    def tearDown(self):
        if self._saved is None:
            os.environ.pop("LC_HOME", None)
        else:
            os.environ["LC_HOME"] = self._saved
        self._reset_logger()

    def test_a_failed_run_record_is_logged_and_does_not_raise(self):
        import types as _types
        from unittest import mock

        from labconstrictor_tools import log, runs

        task = _types.SimpleNamespace(
            status="COMPLETE", error=None, code=None, traceback=None, outputs={}, cancel_requested=False
        )
        with mock.patch.object(runs, "_prune", side_effect=OSError("disk full")):
            self.assertIsNone(runs.record("app", "tool", {}, task, 1.0))
        self.assertIn("could not write the run record", log.tail(20))
        self.assertIn("disk full", log.tail(20))

    def test_a_failed_process_group_kill_is_logged(self):
        import types as _types
        from unittest import mock

        from labconstrictor_tools import log

        worker = client.WorkerProcess.__new__(client.WorkerProcess)
        worker.proc = _types.SimpleNamespace(pid=4242)
        with mock.patch.object(os, "killpg", side_effect=PermissionError("not allowed")):
            worker._kill_group()
        self.assertIn("could not stop its process group", log.tail(20))

    def test_a_worker_line_that_is_not_an_object_does_not_kill_the_reader(self):
        import types as _types
        from unittest import mock

        from labconstrictor_tools import log

        worker = client.WorkerProcess.__new__(client.WorkerProcess)
        seen = []
        task = _types.SimpleNamespace(handle=seen.append)
        worker.tasks = {"t1": task}
        worker.proc = _types.SimpleNamespace(
            pid=7, stdout=iter(["[1, 2]\n", "garbage\n", '{"task": "t1", "responseType": "UPDATE"}\n'])
        )
        with (
            mock.patch.object(client.WorkerProcess, "_on_exit"),
            mock.patch.object(client.WorkerProcess, "_close_pipe"),
        ):
            worker._read_responses()
        self.assertEqual(
            [m["responseType"] for m in seen], ["UPDATE"]
        )  # the good line after two bad ones arrived
        self.assertIn("not a protocol message", log.tail(20))

    def test_malformed_requests_are_reported_on_stderr_and_skipped(self):
        import contextlib
        import io
        from unittest import mock

        from labconstrictor_tools import protocol

        lines = ["not json\n", "[1, 2]\n", '{"task": "a", "requestType": "EXECUTE"}\n']
        captured = io.StringIO()
        with (
            mock.patch.object(protocol, "_stdin_lines", return_value=iter(lines)),
            contextlib.redirect_stderr(captured),
        ):
            requests = list(protocol.Channel.read_requests())
        self.assertEqual(requests, [{"task": "a", "requestType": "EXECUTE"}])
        self.assertIn("not JSON", captured.getvalue())
        self.assertIn("not an object", captured.getvalue())

    def test_a_progress_update_without_a_message_reaches_the_callback_as_text(self):
        import types as _types

        received = []
        task = client.Task(
            _types.SimpleNamespace(proc=_types.SimpleNamespace(pid=1)), "t", lambda m, f: received.append(m)
        )
        task.handle({"responseType": "UPDATE", "current": 5, "maximum": 10})
        self.assertEqual(received, [""])


if __name__ == "__main__":
    unittest.main(verbosity=2)
