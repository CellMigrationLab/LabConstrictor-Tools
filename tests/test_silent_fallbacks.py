"""Failures that used to disappear (an `except ...: pass`, or a finding that was shown but never logged) are now visible:
each test asserts the log line or the stderr line that was missing before."""

import io
import logging
import sys
import tempfile
import threading
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

import _paths  # noqa: F401  (must come first)
from test_diagnostics import fake_torch

from labconstrictor_tools import client, convert, diagnostics as d, exporter, log, protocol
from labconstrictor_tools import types as T


class Diagnostics(unittest.TestCase):
    def test_a_probe_that_raises_is_logged_with_its_traceback_and_still_reported(self):
        def broken():
            raise RuntimeError("probe exploded")

        with self.assertLogs("labconstrictor.diagnostics", "ERROR") as logs:
            checks = d.run_checks(benchmark=False, extra=[broken])
        failed = [c for c in checks if c.layer == "probe" and c.status == d.FAIL]
        self.assertEqual(len(failed), 1)
        self.assertIn("probe exploded", failed[0].detail)
        self.assertIn("RuntimeError: probe exploded", "\n".join(logs.output))  # the traceback is in the record

    def test_torch_devices_logs_a_failing_cuda_query_instead_of_hiding_it(self):
        torch = fake_torch(cuda=True)

        def boom():
            raise RuntimeError("driver mismatch")

        torch.cuda.is_available = boom
        with mock.patch.object(d, "_torch_module", return_value=torch):
            with self.assertLogs("labconstrictor.diagnostics", "ERROR") as logs:
                names = d.torch_devices()
        self.assertEqual(names, ["cpu"])
        self.assertIn("driver mismatch", "\n".join(logs.output))

    def test_torch_devices_logs_a_broken_import(self):
        with mock.patch.object(d, "_torch_module", side_effect=ImportError("libcudart missing")):
            with self.assertLogs("labconstrictor.diagnostics", "ERROR") as logs:
                self.assertEqual(d.torch_devices(), [])
        self.assertIn("libcudart missing", "\n".join(logs.output))

    def test_a_broken_torch_import_is_logged_and_reported(self):
        with mock.patch.object(d, "_torch_module", side_effect=ImportError("libcudart missing")):
            with self.assertLogs("labconstrictor.diagnostics", "ERROR"):
                checks = d.probe_torch()
        self.assertEqual(checks[0].status, d.FAIL)

    def test_missing_package_metadata_is_the_only_thing_swallowed_in_the_worker_probe(self):
        # a source tree: the fallback is announced in the log, not silent
        from importlib import metadata

        with mock.patch.object(metadata, "version", side_effect=metadata.PackageNotFoundError("x")):
            with self.assertLogs("labconstrictor.diagnostics", "INFO") as logs:
                checks = d.probe_worker()
        self.assertTrue(any("running from a source folder" in c.detail for c in checks))
        self.assertIn("not installed as a package", "\n".join(logs.output))


class LogModule(unittest.TestCase):
    def test_version_fallback_is_logged_once(self):
        from importlib import metadata

        with mock.patch.object(metadata, "version", side_effect=metadata.PackageNotFoundError("x")):
            with mock.patch.object(log, "_version_fallback_logged", False):
                with self.assertLogs("labconstrictor", "INFO") as logs:
                    self.assertEqual(log.version(), "unknown (checkout)")
                    log.version()
        self.assertEqual(len(logs.output), 1)

    def test_unreadable_log_tail_says_why(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(log, "log_path", return_value=Path(tmp) / "missing.log"):
                with self.assertLogs("labconstrictor", "DEBUG") as logs:
                    self.assertEqual(log.tail(), "")
        self.assertIn("cannot read the log file", logs.output[0])


class Channel(unittest.TestCase):
    def test_a_host_that_is_gone_is_reported_once_on_stderr(self):
        class Gone:
            def write(self, text):
                raise BrokenPipeError(32, "Broken pipe")

            def flush(self):
                pass

        channel = object.__new__(protocol.Channel)  # not __init__: it would redirect this process's stdout
        channel._out, channel._lock, channel._reported_closed = Gone(), threading.Lock(), False
        with redirect_stderr(io.StringIO()) as err:
            channel.send("t1", "UPDATE", message="a")
            channel.send("t1", "UPDATE", message="b")
        self.assertEqual(err.getvalue().count("cannot write to the host"), 1)
        self.assertIn("BrokenPipeError", err.getvalue())


class ClientPipes(unittest.TestCase):
    def test_a_pipe_that_cannot_be_closed_is_logged(self):
        pipe = mock.Mock()
        pipe.close.side_effect = OSError("bad descriptor")
        with self.assertLogs("labconstrictor", "DEBUG") as logs:
            client.WorkerProcess._close_pipe(pipe)
        self.assertIn("bad descriptor", "\n".join(logs.output))


class Readers(unittest.TestCase):
    def test_an_unreadable_image_is_logged_with_its_cause_and_still_a_tool_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp, "bad.tif")
            bad.write_bytes(b"this is not a tiff")
            with self.assertLogs("labconstrictor.convert", "ERROR") as logs:
                with self.assertRaises(T.ToolError) as caught:
                    convert._read_image(str(bad))
        self.assertEqual(caught.exception.code, "unreadable_image")
        self.assertIn("Traceback", "\n".join(logs.output))

    def test_a_cell_that_fails_on_its_own_is_logged_with_its_traceback(self):
        source = "import nothing_like_this_exists\ndef f(x: int) -> int:\n    return x\n"
        with self.assertLogs("labconstrictor.exporter", "ERROR") as logs:
            prepared = exporter.check(exporter.prepare(source))
        self.assertTrue(any("the cell fails on its own" in p for p in prepared.problems))
        self.assertIn("Traceback", "\n".join(logs.output))


if __name__ == "__main__":
    unittest.main()
