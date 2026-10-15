"""tests/audit/syn_to_matrix.py: the check output of the synthetic datasets becomes matrix rows; host-side refusals and CLI-only expectations are notes."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

import _paths  # noqa: F401  (must come first)
from _paths import ROOT

sys.path.insert(0, str(ROOT / "tests" / "audit"))
import syn_to_matrix  # noqa: E402
from matrix import Matrix  # noqa: E402

OUTPUT = """CHECK ds_one_1_value PASS ok
CHECK ds_two_2_value FAIL wrong number
CHECK pg_cli_3_value FAIL worker without chooser
NOTE ds_three judged by a person
NOTE ds_four plain information
"""


class ConvertTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)

    def rows(self, host: str, special: dict[str, str]) -> dict[str, tuple[str, str]]:
        matrix = Matrix(self.directory / host, "synthetic", host, "App")
        syn_to_matrix.convert(matrix, host, OUTPUT, special)
        return {r["id"]: (r["status"], r["tool"]) for r in matrix.rows}

    def test_cli_rows_keep_their_verdict(self) -> None:
        rows = self.rows("cli", {})
        self.assertEqual(rows["syn_ds_one_1_value"], ("PASS", "ds_one"))
        self.assertEqual(rows["syn_ds_two_2_value"], ("FAIL", "ds_two"))
        self.assertEqual(
            rows["syn_pg_cli_3_value"][0], "FAIL", "a CLI expectation that fails on the CLI is a failure"
        )
        self.assertEqual(rows["syn_ds_three_note"][0], "HUMAN")
        self.assertEqual(rows["syn_ds_four_note"][0], "NOTE")

    def test_host_rows_of_a_refused_dataset_and_cli_only_expectations_become_notes(self) -> None:
        rows = self.rows("napari", {"ds_two": "the form refused"})
        self.assertEqual(rows["syn_host_napari_ds_two_2_value"][0], "NOTE")
        self.assertEqual(
            rows["syn_host_napari_ds_one_1_value"][0], "PASS", "a PASS is never turned into a note"
        )
        self.assertEqual(rows["syn_host_napari_pg_cli_3_value"][0], "NOTE")

    def test_special_datasets_read_the_host_reports_and_name_an_unreadable_one(self) -> None:
        reports = self.directory / "reports"
        reports.mkdir()
        (reports / "not_expressible.json").write_text(
            json.dumps([{"dataset": "ds_a", "why": "too big"}]), encoding="utf-8"
        )
        (reports / "ds_b.json").write_text(
            json.dumps(
                {"status": "DRIVER_ERROR", "error": "Run did not start a task; status: Pick an image | more"}
            ),
            encoding="utf-8",
        )
        (reports / "ds_c.json").write_text(json.dumps({"status": "COMPLETE"}), encoding="utf-8")
        (reports / "ds_d.json").write_text("{broken", encoding="utf-8")
        (reports / "case_001.json").write_text(
            "{broken", encoding="utf-8"
        )  # case files are not reports of a dataset
        special, unreadable = syn_to_matrix.special_datasets(reports)
        self.assertEqual(sorted(special), ["ds_a", "ds_b"])
        self.assertIn("Pick an image", special["ds_b"])
        self.assertEqual([name for name, _ in unreadable], ["ds_d.json"])


if __name__ == "__main__":
    unittest.main()
