"""tests/audit/collect_results.py: every alphaN round stays apart, scratch recorders are ignored, an unreadable matrix is reported."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

import _paths  # noqa: F401  (must come first)
from _paths import ROOT

sys.path.insert(0, str(ROOT / "tests" / "audit"))
import collect_results  # noqa: E402


def write_matrix(
    path: Path, app: str, rows: list[tuple[str, str]], finished: str | None = "2026-10-15T00:00:00"
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    document = {
        "app": app,
        "family": "sandbox",
        "host": "cli",
        "finished": finished,
        "rows": [{"id": i, "status": s, "detail": "detail of " + i} for i, s in rows],
    }
    path.write_text(json.dumps(document), encoding="utf-8")


class RoundSeparationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        write_matrix(self.root / "App" / "matrix_sandbox_cli_App.json", "App", [("first_round", "FAIL")])
        for name in ("alpha2", "alpha3", "alpha4", "alpha10"):
            write_matrix(
                self.root / name / "App" / "matrix_sandbox_cli_App.json", "App", [("only_" + name, "FAIL")]
            )

    def ids(self, documents: list[dict[str, object]]) -> set[str]:
        return {r["id"] for d in documents for r in d["rows"]}

    def test_rounds_are_listed_in_numeric_order(self) -> None:
        self.assertEqual(collect_results.rounds(self.root), ["alpha2", "alpha3", "alpha4", "alpha10"])

    def test_each_round_loads_only_its_own_matrices(self) -> None:
        self.assertEqual(self.ids(collect_results.load(self.root)), {"first_round"})
        for name in ("alpha2", "alpha3", "alpha4", "alpha10"):
            self.assertEqual(self.ids(collect_results.load(self.root, name)), {"only_" + name})

    def test_collect_writes_one_file_per_round_without_mixing(self) -> None:
        written = collect_results.collect(self.root)
        self.assertEqual(len(written), 5)
        first = (self.root / "RESULTS.md").read_text(encoding="utf-8")
        self.assertIn("first_round", first)
        for name in ("alpha2", "alpha3", "alpha4", "alpha10"):
            self.assertNotIn("only_" + name, first)
            text = (self.root / name / "MATRICES.md").read_text(encoding="utf-8")
            self.assertIn("only_" + name, text)
            self.assertIn("%s round" % name, text)
            self.assertNotIn("first_round", text)
            for other in {"alpha2", "alpha3", "alpha4", "alpha10"} - {name}:
                self.assertNotIn("only_" + other, text)

    def test_the_napari_scratch_recorder_is_ignored(self) -> None:
        write_matrix(
            self.root / "alpha4" / "audit_scratch" / "matrix_x_y_App.json", "App", [("scratch_row", "FAIL")]
        )
        self.assertNotIn("scratch_row", self.ids(collect_results.load(self.root, "alpha4")))

    def test_an_unreadable_matrix_is_reported_not_skipped(self) -> None:
        (self.root / "alpha3" / "matrix_broken.json").write_text("{not json", encoding="utf-8")
        documents = collect_results.load(self.root, "alpha3")
        self.assertEqual(len(documents), 2)
        text = collect_results.render(documents)
        self.assertIn("UNREADABLE", text)

    def test_render_lists_fail_not_run_and_human_rows_and_unfinished_matrices(self) -> None:
        write_matrix(
            self.root / "other" / "matrix_sandbox_cli_Other.json",
            "Other",
            [("a", "PASS"), ("b", "NOT_RUN"), ("c", "HUMAN")],
            finished=None,
        )
        text = collect_results.render(collect_results.load(self.root))
        self.assertIn("NOT FINISHED", text)
        self.assertIn("### Other: NOT_RUN (1)", text)
        self.assertIn("### Other: HUMAN (1)", text)
        self.assertNotIn("`a`", text, "a PASS row is counted, not listed")


if __name__ == "__main__":
    unittest.main()
