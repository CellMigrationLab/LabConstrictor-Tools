"""The unused-code scan (vulture, min confidence 80) over the production package, and the rules for its whitelist: every entry has a
reason, and an entry that vulture no longer reports is removed. A name that nothing calls is either deleted or whitelisted with a
reason, never left to rot."""

import importlib.util
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import _paths  # noqa: F401  (must come first)
from _paths import ROOT

WHITELIST = ROOT / "tests" / "vulture_whitelist.py"
MIN_CONFIDENCE = "80"
HAVE_VULTURE = importlib.util.find_spec("vulture") is not None


def entries():
    """(name, reason) of every whitelist line that is not a comment or part of the docstring."""
    out = []
    in_doc = False
    for line in WHITELIST.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.count('"""') == 1:
            in_doc = not in_doc
            continue
        if in_doc or not stripped or stripped.startswith(("#", '"""')):
            continue
        name, _, reason = stripped.partition("#")
        out.append((name.strip(), reason.strip()))
    return out


def vulture(*arguments):
    return subprocess.run(
        [sys.executable, "-m", "vulture", *arguments], capture_output=True, text=True, cwd=ROOT, timeout=300
    )


class Whitelist(unittest.TestCase):
    def test_every_entry_has_a_reason_and_names_one_identifier(self):
        for name, reason in entries():
            with self.subTest(name):
                self.assertRegex(name, r"^[A-Za-z_][A-Za-z0-9_.]*$")
                self.assertGreaterEqual(len(reason), 25, "say why %s is not dead code" % name)

    def test_names_are_unique(self):
        names = [n for n, _ in entries()]
        self.assertEqual(sorted(set(names)), sorted(names))


@unittest.skipUnless(HAVE_VULTURE, "pip install vulture")
class Scan(unittest.TestCase):
    def test_the_package_has_no_unused_code_beyond_the_whitelist(self):
        done = vulture("labconstrictor_tools", str(WHITELIST), "--min-confidence", MIN_CONFIDENCE)
        self.assertEqual(done.returncode, 0, "unused code:\n" + done.stdout)

    def test_every_whitelist_entry_is_still_needed(self):
        done = vulture("labconstrictor_tools", "--min-confidence", MIN_CONFIDENCE)
        reported = set(re.findall(r"unused \w+ '([^']+)'", done.stdout))
        stale = [name for name, _ in entries() if name not in reported]
        self.assertEqual(stale, [], "vulture no longer reports these: delete the whitelist lines")

    def test_the_scan_has_teeth(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, "planted.py").write_text(
                "def used(x, never_read):\n    return x\n\nused(1, 2)\n", encoding="utf-8"
            )
            done = vulture(folder, "--min-confidence", MIN_CONFIDENCE)
        self.assertEqual(done.returncode, 3)
        self.assertIn("never_read", done.stdout)


if __name__ == "__main__":
    unittest.main()
