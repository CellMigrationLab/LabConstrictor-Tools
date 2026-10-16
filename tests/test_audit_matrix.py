"""tests/audit/matrix.py: the result matrix of the audit (statuses, NOT_RUN for expected ids that never ran, CHECK/NOTE line parsing, atomic file)."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

import _paths  # noqa: F401  (must come first)
from _paths import ROOT

sys.path.insert(0, str(ROOT / "tests" / "audit"))
from matrix import STATUSES, Matrix  # noqa: E402


class MatrixTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)

    def read(self, matrix: Matrix) -> dict[str, object]:
        document: dict[str, object] = json.loads(matrix.path.read_text(encoding="utf-8"))
        return document

    def test_unknown_status_is_an_error_and_writes_no_row(self) -> None:
        matrix = Matrix(self.directory, "sandbox", "cli", "App")
        with self.assertRaises(ValueError):
            matrix.add("x", "GREEN")
        self.assertEqual(matrix.rows, [])

    def test_every_status_is_accepted_and_counted_on_its_own(self) -> None:
        matrix = Matrix(self.directory, "sandbox", "cli", "App")
        for index, status in enumerate(STATUSES):
            matrix.add("row_%d" % index, status)
        matrix.add("row_again", "PASS")
        self.assertEqual(matrix.counts(), {"PASS": 2, "FAIL": 1, "NOT_RUN": 1, "HUMAN": 1, "NOTE": 1})

    def test_expected_ids_without_a_row_become_not_run_and_red(self) -> None:
        matrix = Matrix(self.directory, "nb", "notebook", "App", expected=["a", "b", "c"])
        matrix.add("a", "PASS")
        self.assertIsNone(self.read(matrix)["finished"], "an unfinished matrix says so")
        counts = matrix.finish()
        self.assertEqual((counts["PASS"], counts["NOT_RUN"]), (1, 2))
        self.assertEqual([r["id"] for r in matrix.rows if r["status"] == "NOT_RUN"], ["b", "c"])
        self.assertIsNotNone(self.read(matrix)["finished"])

    def test_file_is_rewritten_after_every_row_and_named_by_family_host_app(self) -> None:
        matrix = Matrix(self.directory, "synthetic", "napari", "VLab4Mic")
        self.assertEqual(matrix.path.name, "matrix_synthetic_napari_VLab4Mic.json")
        matrix.add("one", "PASS")
        self.assertEqual(len(self.read(matrix)["rows"]), 1)
        matrix.add("two", "FAIL")
        self.assertEqual(len(self.read(matrix)["rows"]), 2)
        self.assertFalse(matrix.path.with_suffix(".json.tmp").exists(), "the temporary file is renamed away")

    def test_detail_is_one_line_and_bounded(self) -> None:
        matrix = Matrix(self.directory, "sandbox", "cli", "App")
        matrix.add("long", "NOTE", "first\nsecond" + "x" * 1000)
        detail = matrix.rows[0]["detail"]
        self.assertNotIn("\n", detail)
        self.assertEqual(len(detail), 500)

    def test_add_output_reads_check_and_note_lines_and_flags_malformed_ones(self) -> None:
        matrix = Matrix(self.directory, "sandbox", "cli", "App")
        added = matrix.add_output(
            "noise\nCHECK a PASS fine\nCHECK b FAIL broken\nCHECK c no verdict here\nNOTE d something\nNOTE e step not run\n"
        )
        self.assertEqual(added, 5)
        status = {r["id"]: r["status"] for r in matrix.rows}
        self.assertEqual(status, {"a": "PASS", "b": "FAIL", "c": "FAIL", "d": "NOTE", "e": "NOT_RUN"})
        self.assertIn("malformed", next(r["detail"] for r in matrix.rows if r["id"] == "c"))


if __name__ == "__main__":
    unittest.main()
