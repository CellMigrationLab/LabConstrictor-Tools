"""`runs.build_record`, `runs.record_json` and `runs.done_status`: what a Python host uses to write its own run record without
pruning (docs/PROTOCOL.md, "Result folders and run records"; docs/SPEC_WRONG_SCIENCE.md 3.2).

`runs.record` (the CLI and the Python client) must write exactly what it always did. Expected values are written out by hand.
"""

import json
import os
import re
import tempfile
import types
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

import _paths  # noqa: F401  (must come first)
from _paths import ROOT

from labconstrictor_tools import retention, runs


def task(status="COMPLETE", **extra):
    values = {
        "status": status,
        "error": None,
        "code": None,
        "traceback": None,
        "outputs": {
            "results": [
                {
                    "name": "mask",
                    "type": "labels",
                    "path": "/r/mask.tif",
                    "matrix_yx": [[1, 0, 0], [0, 1, 0]],
                },
                {"name": "n", "type": "values", "value": 3},
            ],
            "timings": {"run_wall_s": 1.5},
            "diagnostics": {"python": "3.12"},
        },
    }
    values.update(extra)
    return types.SimpleNamespace(**values)


INPUTS = {"image": "/data/a.tif", "sigma": 2.0, "_job_dir": "/home/x/results/r1"}
EXPECTED = {
    "app": "synthetic",
    "app_version": "0.0",
    "tool": "blur",
    "finished_utc": "2026-10-13T08:00:00+00:00",
    "seconds": 1.23,
    "status": "COMPLETE",
    "error": None,
    "code": None,
    "traceback": None,
    "inputs": {"image": "/data/a.tif", "sigma": 2.0},
    "results": [
        {"name": "mask", "type": "labels", "path": "/r/mask.tif"},
        {"name": "n", "type": "values", "value": 3},
    ],
    "timings": {"run_wall_s": 1.5},
    "interpreter": {"python": "3.12"},
    "stderr_tail": "oops",
}


class Home(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="lc_runrec_")
        self.addCleanup(self._tmp.cleanup)
        self.home = Path(self._tmp.name) / "home"
        self.home.mkdir()
        _paths.register_synthetic(self.home)  # the app version comes from the registry entry
        patcher = mock.patch.dict(os.environ, {"LC_HOME": str(self.home)})
        patcher.start()
        self.addCleanup(patcher.stop)

    def build(self, **extra):
        return runs.build_record(
            "synthetic",
            "blur",
            INPUTS,
            task(),
            1.2345,
            "oops",
            finished_utc="2026-10-13T08:00:00+00:00",
            **extra,
        )


class BuildRecord(Home):
    def test_the_content_is_what_a_run_record_holds_and_nothing_else(self):
        self.assertEqual(self.build(), EXPECTED)
        self.assertEqual(list(self.build()), list(EXPECTED))  # the same keys in the same order

    def test_it_writes_nothing_and_prunes_nothing(self):
        with (
            mock.patch.object(retention, "prune") as prune,
            mock.patch.object(retention, "write_owner") as owner,
        ):
            self.build()
        prune.assert_not_called()
        owner.assert_not_called()
        self.assertEqual(sorted(p.name for p in self.home.iterdir() if p.name != "apps"), [])

    def test_record_writes_the_same_content(self):
        folder = runs.record("synthetic", "blur", INPUTS, task(), 1.2345, "oops")
        written = json.loads((folder / "run.json").read_text(encoding="utf-8"))
        finished = written.pop("finished_utc")
        self.assertTrue(re.fullmatch(r"\d{4}-\d\d-\d\dT[\d:.]+\+00:00", finished), finished)
        expected = dict(EXPECTED)
        expected.pop("finished_utc")
        self.assertEqual(written, expected)
        self.assertNotIn("run_id", written)  # the CLI's record has no run_id and no started_utc
        self.assertNotIn("started_utc", written)

    def test_the_text_is_what_record_writes(self):
        content = self.build()
        with mock.patch.object(runs, "build_record", return_value=content):
            folder = runs.record("synthetic", "blur", INPUTS, task(), 1.2345, "oops")
        self.assertEqual((folder / "run.json").read_text(encoding="utf-8"), runs.record_json(content))
        self.assertEqual(runs.record_json(content), json.dumps(content, indent=2, default=str))
        self.assertEqual(json.loads(runs.record_json(content)), content)

    def test_a_host_gets_its_run_id_and_start_in_the_record(self):
        content = self.build(run_id="3f2a9c", started_utc="2026-10-13T07:59:58+00:00")
        self.assertEqual(list(content)[:5], ["run_id", "app", "app_version", "tool", "started_utc"])
        self.assertEqual((content["run_id"], content["started_utc"]), ("3f2a9c", "2026-10-13T07:59:58+00:00"))
        rest = {k: v for k, v in content.items() if k not in ("run_id", "started_utc")}
        self.assertEqual(rest, EXPECTED)

    def test_without_finished_utc_it_is_now_in_utc(self):
        content = runs.build_record("synthetic", "blur", INPUTS, task(), 1.0)
        finished = datetime.fromisoformat(content["finished_utc"])
        self.assertEqual(finished.utcoffset().total_seconds(), 0)
        self.assertLess(abs((datetime.now(finished.tzinfo) - finished).total_seconds()), 60)

    def test_the_stderr_tail_is_cut_and_the_input_dict_is_left_alone(self):
        inputs = dict(INPUTS)
        content = runs.build_record("synthetic", "blur", inputs, task(), 1.0, "x" * 9000 + "end")
        self.assertEqual(len(content["stderr_tail"]), runs.STDERR_TAIL_CHARS)
        self.assertTrue(content["stderr_tail"].endswith("xend"))
        self.assertEqual(inputs, INPUTS)
        self.assertIn("_job_dir", inputs)

    def test_an_app_that_is_not_registered_has_no_version(self):
        self.assertIsNone(runs.build_record("nobody", "t", {}, task(), 1.0)["app_version"])

    def test_values_that_are_not_json_are_written_as_text(self):
        content = runs.build_record("synthetic", "blur", {"folder": Path("/data/x")}, task(), 1.0)
        self.assertEqual(json.loads(runs.record_json(content))["inputs"], {"folder": str(Path("/data/x"))})


class DoneStatus(unittest.TestCase):
    def test_every_way_a_task_ends(self):
        table = {
            ("COMPLETE", False): "ok",
            ("COMPLETE", True): "ok",
            ("CANCELED", False): "cancelled",
            ("CANCELED", True): "cancelled",
            ("FAILED", False): "failed",
            ("FAILED", True): "failed",  # the tool raised: failed, whether or not Cancel was pressed
            ("CRASHED", False): "failed",
            ("CRASHED", True): "cancelled",  # the person asked for the stop (HOST_PARITY J08)
            ("RUNNING", False): "failed",
            ("SOMETHING_NEW", True): "failed",
        }
        for (status, cancelled), expected in table.items():
            with self.subTest(status=status, cancel_requested=cancelled):
                self.assertEqual(runs.done_status(status, cancelled), expected)
        self.assertEqual(runs.done_status("CRASHED"), "failed")  # no Cancel unless said so

    def test_every_answer_is_a_status_a_done_marker_may_hold(self):
        for status in ("COMPLETE", "CANCELED", "FAILED", "CRASHED", "RUNNING"):
            for cancelled in (False, True):
                self.assertIn(runs.done_status(status, cancelled), retention.STATUSES)


class RecordKeepsItsBehaviour(Home):
    def test_every_status_gets_the_done_status_it_always_had(self):
        for status, expected in (
            ("COMPLETE", "ok"),
            ("CANCELED", "cancelled"),
            ("CRASHED", "failed"),
            ("FAILED", "failed"),
        ):
            folder = runs.record("synthetic", "blur", {}, task(status), 1.0)
            self.assertEqual(json.loads((folder / ".lc-done.json").read_text())["status"], expected, status)
            self.assertEqual(json.loads((folder / ".lc-owner.json").read_text())["host"], "cli")

    def test_a_crash_after_cancel_is_cancelled_in_the_record_folder_too(self):
        folder = runs.record("synthetic", "blur", {}, task("CRASHED", cancel_requested=True), 1.0)
        self.assertEqual(json.loads((folder / ".lc-done.json").read_text())["status"], "cancelled")
        folder = runs.record("synthetic", "blur", {}, task("CRASHED", cancel_requested=False), 1.0)
        self.assertEqual(json.loads((folder / ".lc-done.json").read_text())["status"], "failed")

    def test_record_still_prunes_and_still_never_raises(self):
        with mock.patch.object(retention, "prune") as prune:
            runs.record("synthetic", "blur", {}, task(), 1.0)
        prune.assert_called_once_with("runs")
        with mock.patch.object(retention, "write_owner", side_effect=OSError("disk full")):
            self.assertIsNone(runs.record("synthetic", "blur", {}, task(), 1.0))


class HostFlow(Home):
    """What Napari does, with the three functions: the folder exists from the start, the host finishes it, nothing is pruned."""

    def make_old_records(self, count):
        for index in range(count):
            folder = self.home / "runs" / ("20260101T0000%02d_old_tool" % index)
            folder.mkdir(parents=True, exist_ok=True)
            retention.write_owner(folder, "run", "napari")
            retention.write_done(folder, "ok")

    def test_a_host_record_is_finished_without_a_prune_and_pruned_later_by_tools_only(self):
        self.make_old_records(55)
        folder = self.home / "runs" / "20261013T080000000000_synthetic_blur"
        folder.mkdir()
        retention.write_owner(folder, "run", "napari")
        self.assertFalse((folder / ".lc-done.json").exists())  # started, not finished: nobody may remove it
        content = runs.build_record(
            "synthetic", "blur", INPUTS, task("CRASHED", cancel_requested=True), 2.0, run_id="r1"
        )
        (folder / "run.json").write_text(runs.record_json(content), encoding="utf-8")
        retention.write_done(folder, runs.done_status("CRASHED", True))
        self.assertEqual(json.loads((folder / ".lc-done.json").read_text())["status"], "cancelled")
        self.assertEqual(json.loads((folder / "run.json").read_text())["run_id"], "r1")
        self.assertEqual(len(list((self.home / "runs").iterdir())), 56)  # nothing was removed on the way
        retention.prune("runs")  # the host's subprocess, run here
        remaining = sorted(p.name for p in (self.home / "runs").iterdir())
        self.assertEqual(len(remaining), retention.RUN_RECORDS_KEPT)
        self.assertIn(folder.name, remaining)  # the newest is kept


class Documented(unittest.TestCase):
    def test_protocol_and_operations_describe_the_three_functions_and_the_version(self):
        protocol = (ROOT / "docs" / "PROTOCOL.md").read_text(encoding="utf-8")
        operations = (ROOT / "docs" / "OPERATIONS.md").read_text(encoding="utf-8")
        for name in ("runs.build_record(", "runs.record_json(", "runs.done_status("):
            self.assertIn(name, protocol)
        for name in ("runs.build_record", "runs.record_json", "runs.done_status"):
            self.assertIn(name, operations)
        self.assertIn("not in 0.2.0rc1", protocol)
        self.assertIn("There is no `features` id for them", protocol)
        self.assertIn("There is no feature id for them", operations)

    def test_there_is_no_feature_id_for_them(self):
        from labconstrictor_tools import features

        self.assertEqual(sorted(features.FEATURES), ["reserved_inputs_v1", "retention_prune"])
