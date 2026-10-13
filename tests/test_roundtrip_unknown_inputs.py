"""2026-10-12 (issue #51): the worker ignored input names the tool does not declare, so `{"sigam": 5.0}` ran the tool with the
default sigma and reported COMPLETE. Driven through the real client and worker, like a host or a programmatic caller.
"""

import os
import tempfile
import unittest
from pathlib import Path
from typing import TYPE_CHECKING

import _paths  # noqa: F401  (must come first)

from labconstrictor_tools.client import WorkerProcess

if TYPE_CHECKING:
    from typing import Any

APP = Path(__file__).resolve().parent / "protocol_app"


class UnknownInputs(unittest.TestCase):
    def setUp(self) -> None:
        self.calls = Path(tempfile.mkdtemp(prefix="lccalls_")) / "calls.txt"
        os.environ["LC_CALL_LOG"] = str(self.calls)  # the worker inherits it
        self.addCleanup(os.environ.pop, "LC_CALL_LOG", None)
        self.worker = WorkerProcess(module="tools", pythonpath=[str(APP)])
        self.addCleanup(self.worker.close)

    def calls_made(self) -> list[str]:
        return self.calls.read_text(encoding="utf-8").splitlines() if self.calls.exists() else []

    def run_tool(self, inputs: "dict[str, Any]") -> "Any":
        return self.worker.task("records_call", inputs).wait(60)

    def test_a_misspelt_renamed_or_extra_input_is_refused_and_the_tool_does_not_run(self) -> None:
        for label, inputs, named in (
            ("typo", {"sigam": 5.0}, ["sigam"]),
            ("renamed or deleted", {"sigma_px": 5.0}, ["sigma_px"]),
            ("right name plus an extra", {"sigma": 5.0, "extra": "x"}, ["extra"]),
            ("several", {"b": 1, "a": 2}, ["a", "b"]),
        ):
            with self.subTest(label):
                task = self.run_tool(inputs)
                self.assertEqual((task.status, task.code), ("FAILED", "invalid_parameter"), task.error)
                for name in named:
                    self.assertIn(repr(name), task.error)
                self.assertIn("sigma", task.error, "the message must say what the tool does take")
        self.assertEqual(self.calls_made(), [], "a refused request must not reach the scientific function")

    def test_a_declared_parameter_is_used_and_an_omitted_one_keeps_its_default(self) -> None:
        given = self.run_tool({"sigma": 5.0})
        omitted = self.run_tool({})
        self.assertEqual(given.status, "COMPLETE", given.error)
        self.assertEqual(omitted.status, "COMPLETE", omitted.error)
        self.assertEqual(self.calls_made(), ["sigma=5.0", "sigma=2.0"])

    def test_reserved_protocol_fields_are_not_unknown_parameters(self) -> None:
        job = tempfile.mkdtemp(prefix="lcjob_")
        task = self.run_tool(
            {"_job_dir": job, "_calibration": {}, "_axes": {}, "_a_future_field": 1, "sigma": 1.5}
        )
        self.assertEqual(task.status, "COMPLETE", task.error)
        self.assertEqual(self.calls_made(), ["sigma=1.5"])


if __name__ == "__main__":
    unittest.main()
