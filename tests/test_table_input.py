"""Table inputs (convert.load_inputs with a CSV file): floats exact, names as written, missing files refused, NA texts stay text."""

import tempfile
import unittest
from pathlib import Path

import _paths  # noqa: F401  (must come first)

from labconstrictor_tools import convert
from labconstrictor_tools.types import ToolError

SCHEMA = {
    "id": "t",
    "label": "t",
    "outputs": [],
    "inputs": [{"name": "t", "label": "Table", "type": "table", "required": True}],
}


class TableInput(unittest.TestCase):
    def read(self, content: bytes | str, name: str = "t.csv"):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / name
            path.write_bytes(content if isinstance(content, bytes) else content.encode())
            return convert.load_inputs(SCHEMA, {"t": str(path)})["t"]

    def test_floats_are_exact(self):
        frame = self.read("f\n0.30000000000000004\n6.4575963826141304e+16\n")
        self.assertEqual(frame["f"].tolist(), [float("0.30000000000000004"), float("6.4575963826141304e+16")])

    def test_duplicate_and_empty_names_are_kept(self):
        self.assertEqual(list(self.read("a,a\n1,2\n").columns), ["a", "a"])
        self.assertEqual(list(self.read(",b\n1,2\n").columns), ["", "b"])
        frame = self.read("a,a,b\n1,x,3\n")
        self.assertEqual(frame.iloc[0].tolist(), [1, "x", 3])
        self.assertEqual(frame.dtypes.iloc[0].kind, "i")

    def test_unreadable_files_are_tool_errors(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ToolError) as caught:
                convert.load_inputs(SCHEMA, {"t": str(Path(folder) / "nothing.csv")})
            self.assertEqual(caught.exception.code, "file_not_found")
            self.assertIn("nothing.csv", str(caught.exception))
        for content in (b"", bytes(range(256)) * 4):
            with self.assertRaises(ToolError) as caught:
                self.read(content, "bad.csv")
            self.assertEqual(caught.exception.code, "unreadable_table")
            self.assertIn("bad.csv", str(caught.exception))

    def test_na_words_stay_text_unless_numeric(self):
        words = ["NA", "null", "None", "N/A", "nan", "NaN", "n/a"]
        frame = self.read("t,n,e\n" + "".join("%s,%d,\n" % (w, i) for i, w in enumerate(words)) + "x,7,\n")
        self.assertEqual(frame["t"].tolist(), words + ["x"])
        self.assertEqual(frame["n"].tolist(), list(range(7)) + [7])
        self.assertTrue(frame["e"].isna().all())

    def test_na_word_in_a_numeric_column_is_a_missing_number(self):
        frame = self.read("n,s\n1.5,a\nNA,\nNone,b\n3,\n")
        self.assertEqual(frame["n"].isna().tolist(), [False, True, True, False])
        self.assertEqual(frame["n"].dropna().tolist(), [1.5, 3.0])
        self.assertTrue(frame["s"].isna().tolist()[1])  # an empty cell is missing

    def test_header_only_table_has_its_columns(self):
        frame = self.read("a,b\n")
        self.assertEqual(list(frame.columns), ["a", "b"])
        self.assertEqual(len(frame), 0)


if __name__ == "__main__":
    unittest.main()
