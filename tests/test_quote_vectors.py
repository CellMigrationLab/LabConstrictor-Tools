"""command.quote against the vectors every host shares (tests/quote_vectors.json).

Fiji and QuPath (Groovy `shellQuote`) and any other host that builds the copied terminal line must produce exactly the `posix`
and `windows` strings of each vector for its `text`; this test holds the reference (`command.quote`) to the same file, and checks
the file itself against independent parsers (shlex for POSIX, the C runtime rules of test_roundtrip_command for Windows), so the
vectors cannot drift from the rules they claim to encode.
"""

import json
import shlex
import unittest
from pathlib import Path

import _paths  # noqa: F401  (must come first)
from test_roundtrip_command import parse_windows_command_line

from labconstrictor_tools import command

VECTORS_FILE = Path(__file__).with_name("quote_vectors.json")
VECTORS = json.loads(VECTORS_FILE.read_text(encoding="utf-8"))
REQUIRED_KINDS = ("backslash", "quote", "space", "unicode", "percent", "caret", "ampersand")


class QuoteVectors(unittest.TestCase):
    def test_the_file_is_well_formed_and_covers_the_hard_cases(self):
        labels = [v["label"] for v in VECTORS]
        self.assertEqual(len(labels), len(set(labels)), "labels must be unique")
        for v in VECTORS:
            self.assertEqual(sorted(v), ["label", "posix", "text", "windows"])
        for kind in REQUIRED_KINDS:
            self.assertTrue(any(kind in label for label in labels), "no vector for " + kind)

    def test_quote_gives_the_expected_text_for_both_shells(self):
        for v in VECTORS:
            with self.subTest(v["label"]):
                self.assertEqual(command.quote(v["text"], windows=False), v["posix"])
                self.assertEqual(command.quote(v["text"], windows=True), v["windows"])

    def test_the_posix_expectations_are_one_shell_word(self):
        for v in VECTORS:
            with self.subTest(v["label"]):
                self.assertEqual(shlex.split(v["posix"]), [v["text"]])

    def test_the_windows_expectations_are_one_argument_for_the_c_runtime(self):
        for v in VECTORS:
            with self.subTest(v["label"]):
                self.assertEqual(
                    parse_windows_command_line("prog " + v["windows"] + " next"), ["prog", v["text"], "next"]
                )


if __name__ == "__main__":
    unittest.main()
