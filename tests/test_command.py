"""Copy as command: the copied terminal line and the copied Python snippet, run for real, give the same values as the form."""

import json
import os
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import _paths  # noqa: F401  (must come first)
from _paths import GENERIC_PREFIX, SYNTHETIC_MODULE, V3

from labconstrictor_tools import command
from labconstrictor_tools.introspection import describe_tools

ENV_BASE = {**os.environ, "PYTHONPATH": str(V3), "LC_APPS_PATH": ""}


def tool_schema(tool_id):
    __import__(SYNTHETIC_MODULE)  # declaring the tools registers them
    schema = describe_tools(SYNTHETIC_MODULE)
    return next(t for t in schema["tools"] if t["id"] == tool_id)


class Text(unittest.TestCase):
    def test_unset_values_are_left_out_and_files_get_a_placeholder(self):
        tool = tool_schema("kitchen_sink")
        line = command.command_line("App", tool, {"required_string": "hi", "optional_string": None, "count": 4}, windows=False)
        self.assertIn("run App kitchen_sink", line)
        self.assertIn("image=image.tif", line)  # required image: a placeholder, and the line says so
        self.assertIn("# replace the file for: image", line)
        self.assertNotIn("optional_string", line)
        self.assertNotIn("optional_image", line)
        self.assertIn("count=4", line)

    def test_booleans_are_lowercase_and_spaces_are_quoted_for_each_shell(self):
        tool = tool_schema("kitchen_sink")
        values = {"required_string": "two words", "image": "a b.tif", "flag": False}
        posix = command.command_line("My App", tool, values, windows=False)
        windows = command.command_line("My App", tool, values, windows=True)
        self.assertIn("flag=false", posix)
        self.assertIn("'required_string=two words'", posix)
        self.assertIn('"required_string=two words"', windows)
        self.assertIn('"My App"', windows)

    def test_the_snippet_is_valid_python_with_real_booleans(self):
        tool = tool_schema("kitchen_sink")
        text = command.python_snippet("App", tool, {"required_string": 'q"uote', "image": "x.tif", "flag": True})
        compile(text, "snippet", "exec")
        self.assertIn("'flag': True", text)


class RunForReal(unittest.TestCase):
    """What the form held, what the copied text says, and what the tool received are the same."""

    def setUp(self):
        self.home = Path(tempfile.mkdtemp(prefix="lchome_cmd_"))
        self.env = {**ENV_BASE, "LC_HOME": str(self.home)}
        done = subprocess.run(
            [sys.executable, "-m", "labconstrictor_tools", "register", "--name", "synthetic", "--prefix", str(GENERIC_PREFIX),
             "--module", SYNTHETIC_MODULE, "--version", "1"],
            capture_output=True, text=True, env=self.env,
        )  # fmt: skip
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_terminal_line_gives_the_same_values(self):
        tool = tool_schema("unicode_echo")
        line = command.command_line("synthetic", tool, {"text": "µm → ok 'q'"}, python=sys.executable, windows=False)
        done = subprocess.run(shlex.split(line), capture_output=True, text=True, env=self.env, encoding="utf-8")
        self.assertEqual(done.returncode, 0, done.stderr)
        report = json.loads(done.stdout[: done.stdout.index("\n(results")] if "\n(results" in done.stdout else done.stdout)
        self.assertEqual(report["status"], "COMPLETE")
        self.assertEqual(json.dumps(report["results"], ensure_ascii=False).count("µm → ok 'q'"), 1)

    def test_python_snippet_gives_the_same_values(self):
        tool = tool_schema("scalar_echo")
        text = command.python_snippet("synthetic", tool, {"a": 1.5, "b": 2.25})
        done = subprocess.run([sys.executable, "-c", text], capture_output=True, text=True, env=self.env)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("COMPLETE", done.stdout)
        self.assertIn("3.75", done.stdout)


if __name__ == "__main__":
    unittest.main()
