"""Shell text is built in one place (command.quote); nothing in the package runs a string through a shell."""

import argparse
import contextlib
import io
import os
import re
import shlex
import tempfile
import unittest
from pathlib import Path

import _paths  # noqa: F401  (must come first)
from _paths import ROOT

from labconstrictor_tools import cli, command


class Quote(unittest.TestCase):
    def test_plain_text_is_left_alone_and_awkward_text_stays_one_argument(self):
        for windows in (False, True):
            self.assertEqual(command.quote("plain-name_1.tif", windows), "plain-name_1.tif")
            for awkward in ("My App", "it's", 'say "hi"', "a;b", "$HOME", ""):
                self.assertNotEqual(command.quote(awkward, windows), awkward)

    def test_posix_quoting_round_trips_through_a_shell_parser(self):
        for text in ("My App", "it's", 'say "hi"', "a;b && c", "$(x)", "", "ünï code"):
            self.assertEqual(shlex.split(command.quote(text, windows=False)), [text])

    def test_windows_quoting_wraps_in_double_quotes(self):
        self.assertEqual(command.quote("My App", windows=True), '"My App"')
        self.assertEqual(command.quote('say "hi"', windows=True), '"say \\"hi\\""')

    @unittest.skipUnless(os.name == "posix", "the printed line is quoted for this machine's shell")
    def test_init_prints_next_steps_that_survive_a_folder_with_spaces(self):
        with tempfile.TemporaryDirectory() as parent:
            folder = Path(parent) / "my tools"
            folder.mkdir()
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                cli.cmd_init(argparse.Namespace(path=str(folder / "starter_tools.py")))
            line = next(x for x in out.getvalue().splitlines() if "labconstrictor-tools check" in x)
            words = shlex.split(line)
            self.assertEqual(words[words.index("--pythonpath") + 1], str(folder.resolve()))
            self.assertEqual(words[words.index("--module") + 1], "starter_tools")


class NoShell(unittest.TestCase):
    def test_no_module_hands_text_to_a_shell(self):
        pattern = re.compile(r"shell\s*=\s*True|os\.system\(|os\.popen\(|commands\.getoutput")
        offenders = [
            str(path.relative_to(ROOT))
            for path in (ROOT / "labconstrictor_tools").rglob("*.py")
            if pattern.search(path.read_text(encoding="utf-8"))
        ]
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
