"""Copy as command, executed for real: the quoting helper against a real shell and against the documented Windows parsing rules,
and an app whose NAME has spaces and quotes, run through the copied snippet and the copied terminal line."""

import json
import os
import shlex
import subprocess
import sys
import unittest
from pathlib import Path

import _paths  # noqa: F401  (must come first)
import roundtrip_cases as rc
import roundtrip_harness as harness
from roundtrip_known_failures import is_known

from labconstrictor_tools import command

ARGV_PRINTER = "import sys, json; sys.stdout.buffer.write(json.dumps(sys.argv[1:]).encode('ascii'))"
TEXTS = {**rc.STRINGS}
TEXTS.pop("long-200k")
TEXTS.pop("long-unicode-50k")  # longer than a command line can hold
TEXTS.update(
    {
        "quote-after-backslashes": 'a\\\\"b',
        "only-quote": '"',
        "only-backslash": "\\",
        "two-trailing-backslashes": "dir\\\\",
        "spaced-trailing-backslash": "C:\\My Data\\",
        "spaced-quote-after-backslash": 'x y\\"z',
    }
)


def parse_windows_command_line(text):
    """The documented rules of the Microsoft C runtime (and CommandLineToArgvW) for splitting a command line into arguments:
    2n backslashes before a quote give n backslashes and the quote toggles quoting; 2n+1 give n backslashes and a literal quote;
    backslashes elsewhere are literal; white space separates arguments outside quotes. Written here as the independent oracle.
    """
    args, current, quoted, started, i = [], [], False, False, 0
    while i < len(text):
        c = text[i]
        if c == "\\":
            j = i
            while j < len(text) and text[j] == "\\":
                j += 1
            count = j - i
            if j < len(text) and text[j] == '"':
                current.append("\\" * (count // 2))
                if count % 2:
                    current.append('"')
                    j += 1
                i = j
            else:
                current.append("\\" * count)
                i = j
            started = True
        elif c == '"':
            quoted, started, i = not quoted, True, i + 1
        elif c in " \t" and not quoted:
            if started:
                args.append("".join(current))
                current, started = [], False
            i += 1
        else:
            current.append(c)
            started = True
            i += 1
    if started:
        args.append("".join(current))
    return args


class WindowsParser(unittest.TestCase):
    """The parser itself must agree with Python's own writer of Windows command lines (subprocess.list2cmdline)."""

    def test_the_oracle_inverts_the_standard_library_writer(self):
        for label, text in TEXTS.items():
            with self.subTest(label):
                self.assertEqual(
                    parse_windows_command_line(subprocess.list2cmdline(["prog", text])), ["prog", text]
                )


def windows_process_problems(text):
    """Start a real process with the line command.quote(windows=True) builds and read back the argument it received."""
    line = "%s -c %s %s" % (
        command.quote(sys.executable, True),
        command.quote(ARGV_PRINTER, True),
        command.quote(text, True),
    )
    done = subprocess.run(line, capture_output=True, timeout=60)
    try:
        got = json.loads(done.stdout)
    except ValueError:
        return ["no argument list came back: %r" % done.stderr[-200:]]
    return [] if got == [text] else ["the program received %r, expected %r" % (got, [text])]


class QuotingHelper(unittest.TestCase):
    def test_windows_quoting_keeps_every_text_one_argument(self):
        for label, text in TEXTS.items():
            if is_known("winquote:" + label):
                continue
            with self.subTest(label):
                line = "prog " + command.quote(text, windows=True)
                self.assertEqual(parse_windows_command_line(line), ["prog", text])

    @unittest.skipUnless(os.name == "posix", "needs /bin/sh")
    def test_posix_quoting_survives_a_real_shell(self):
        for label, text in TEXTS.items():
            if "\x00" in text:
                continue
            with self.subTest(label):
                line = "%s -c %s %s" % (
                    command.quote(sys.executable, False),
                    command.quote(ARGV_PRINTER, False),
                    command.quote(text, False),
                )
                done = subprocess.run(line, shell=True, capture_output=True, timeout=60)
                self.assertEqual(done.returncode, 0, done.stderr)
                self.assertEqual(json.loads(done.stdout), [text])

    @unittest.skipUnless(os.name == "nt", "the real Windows process start")
    def test_windows_quoting_survives_the_real_process_start(self):
        for label, text in TEXTS.items():
            if is_known("winproc:" + label):
                continue
            with self.subTest(label):
                self.assertEqual(windows_process_problems(text), [])


class CopiedText(unittest.TestCase):
    """The text a host puts on the clipboard has a documented format (docs/HOST_FEATURES.md): the same in every host."""

    def tool(self, tool_id):
        return harness.roundtrip_app.schemas(rc.APP_MODULE)[tool_id]

    def test_booleans_are_lower_case_in_the_terminal_line_and_real_booleans_in_the_snippet(self):
        for flag, word in ((True, "true"), (False, "false")):
            line = command.command_line("app", self.tool("echo_bool"), {"value": flag}, windows=False)
            self.assertEqual(shlex.split(line)[-1], "value=" + word)
            self.assertIn(
                "'value': %s," % flag, command.python_snippet("app", self.tool("echo_bool"), {"value": flag})
            )

    def test_numbers_and_text_are_written_as_they_are_and_unset_values_are_left_out(self):
        tool = self.tool("echo_defaults")
        values = {"number": 12, "ratio": 0.1, "text": "two words", "flag": None, "mode": "a"}
        words = shlex.split(command.command_line("app", tool, values, windows=False))
        self.assertEqual(words[-4:], ["number=12", "ratio=0.1", "text=two words", "mode=a"])
        self.assertEqual(words[:6], ["python", "-m", "labconstrictor_tools", "run", "app", "echo_defaults"])
        self.assertNotIn("flag", " ".join(words))

    def test_a_missing_file_gets_a_placeholder_and_a_note_in_both_forms(self):
        tool = self.tool("echo_image")
        line = command.command_line("app", tool, {}, windows=False)
        self.assertTrue(line.startswith("# replace the file for: image\n"))
        self.assertIn("image=image.tif", line)
        snippet = command.python_snippet("app", tool, {})
        self.assertTrue(snippet.startswith("# replace the file for: image"))
        self.assertEqual(command.placeholders(tool, {"image": "x.tif"}), [])
        self.assertEqual(command.placeholders(tool, {}), ["image"])


class AppNameWithSpacesAndQuotes(unittest.TestCase):
    """A copied command names the app: a name with spaces or quotes must still be one argument and still find the app."""

    NAMES = ["round trip app", "it's a round trip", "two  spaces", "café µm"] + (
        ['say "round trip"'] if os.name != "nt" else []
    )

    @classmethod
    def setUpClass(cls):
        cls.session = harness.Session()
        env = {**os.environ, "PYTHONPATH": str(_paths.ROOT)}
        for name in cls.NAMES:
            done = subprocess.run(
                [sys.executable, "-m", "labconstrictor_tools", "register", "--name", name, "--prefix", str(_paths.GENERIC_PREFIX),
                 "--module", rc.APP_MODULE, "--version", "0"],
                capture_output=True, text=True, env=env, encoding="utf-8",
            )  # fmt: skip
            assert done.returncode == 0, done.stderr

    @classmethod
    def tearDownClass(cls):
        cls.session.close()

    def run_line(self, line):
        shell = os.name != "nt"
        done = subprocess.run(
            line, shell=shell, capture_output=True, env=self.session.subprocess_env(), timeout=180
        )
        return done.stdout.decode("utf-8", errors="replace"), done.stderr.decode("utf-8", errors="replace")

    def test_terminal_line_and_snippet_give_the_direct_values(self):
        tool = self.session.tools["echo_string"]
        text = 'it\'s "quoted" \\ é µm'
        direct = (
            self.session.worker()
            .task("echo_string", {"value": text})
            .wait(60)
            .outputs["results"][0]["values"]
        )
        self.assertEqual(direct["value"], text)
        for name in self.NAMES:
            with self.subTest("terminal line / " + name):
                line = command.command_line(name, tool, {"value": text}, python=sys.executable)
                stdout, stderr = self.run_line(line)
                report = harness._parse_cli_report(stdout) if "{" in stdout else None
                self.assertIsNotNone(report, stderr[-1500:])
                self.assertEqual(report["status"], "COMPLETE", report)
                self.assertEqual(report["results"][0]["values"], direct)
            with self.subTest("snippet / " + name):
                snippet = command.python_snippet(name, tool, {"value": text})
                done = subprocess.run(
                    [sys.executable, "-c", snippet],
                    capture_output=True,
                    env=self.session.subprocess_env(),
                    timeout=180,
                )
                out = done.stdout.decode("utf-8")
                self.assertTrue(
                    out.startswith("COMPLETE"), out + done.stderr.decode("utf-8", errors="replace")[-1500:]
                )
                self.assertIn(repr(direct["codepoints"]), out)

    def test_a_placeholder_is_marked_and_the_line_still_parses(self):
        tool = self.session.tools["echo_image"]
        line = command.command_line("round trip app", tool, {}, python=sys.executable, windows=False)
        first, second = line.split("\n")
        self.assertTrue(first.startswith("# replace the file for: image"))
        self.assertIn("image=image.tif", second)
        self.assertEqual(Path(shlex.split(second)[0]).name, Path(sys.executable).name)


def tearDownModule():
    """Release what this module's tests left to the garbage collector now, so that a ResourceWarning for an unclosed pipe is
    raised here and not in whichever test happens to run next (some older tests count ResourceWarnings)."""
    import gc

    gc.collect()


if __name__ == "__main__":
    unittest.main()
