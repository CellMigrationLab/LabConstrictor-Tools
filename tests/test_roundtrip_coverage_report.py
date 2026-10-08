"""tests/coverage_report.py on a tiny package whose answer is known: what only a test calls is listed, what production code
calls is not, and the floor makes the script fail."""

import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

import _paths  # noqa: F401  (must come first)
from _paths import ROOT

SCRIPT = ROOT / "tests" / "coverage_report.py"
HAVE_COVERAGE_AND_VULTURE = all(
    __import__("importlib.util").util.find_spec(m) for m in ("coverage", "vulture")
)


@unittest.skipUnless(HAVE_COVERAGE_AND_VULTURE, "pip install coverage vulture")
class CoverageReport(unittest.TestCase):
    def build(self, folder: Path) -> Path:
        package = folder / "tiny"
        package.mkdir()
        (package / "__init__.py").write_text("", encoding="utf-8")
        (package / "core.py").write_text(
            textwrap.dedent("""
                def helper():
                    return 1


                def entry():
                    return helper()


                def main():
                    return entry()


                def only_the_tests_call_me():
                    return 2


                def nobody_calls_me():
                    return 3
                """),
            encoding="utf-8",
        )
        (package / "lonely.py").write_text("VALUE = 1\n", encoding="utf-8")
        (folder / "run_tests.py").write_text(
            "import tiny.core as core\ncore.main()\ncore.only_the_tests_call_me()\n", encoding="utf-8"
        )
        (folder / "rc.toml").write_text(
            '[tool.coverage.run]\nsource_pkgs = ["tiny"]\nbranch = true\ndata_file = ".coverage"\n',
            encoding="utf-8",
        )
        return package

    def test_it_lists_what_only_tests_reach_and_what_nothing_reaches(self):
        with tempfile.TemporaryDirectory() as name:
            folder = Path(name)
            package = self.build(folder)
            run = subprocess.run(
                [sys.executable, "-m", "coverage", "run", "--rcfile", "rc.toml", "run_tests.py"],
                cwd=folder, capture_output=True, text=True, timeout=120,
            )  # fmt: skip
            self.assertEqual(run.returncode, 0, run.stderr)
            report = subprocess.run(
                [sys.executable, str(SCRIPT), "--package", str(package), "--rcfile", str(folder / "rc.toml")],
                cwd=folder, capture_output=True, text=True, timeout=120,
            )  # fmt: skip
            self.assertEqual(report.returncode, 0, report.stderr + report.stdout)
            section_2 = report.stdout.split("== 2.")[1].split("== 3.")[0]
            section_3 = report.stdout.split("== 3.")[1].split("== 4.")[0]
            self.assertIn("only_the_tests_call_me", section_2)
            self.assertIn("function main", section_2)  # the "entry point" nothing in the package calls
            self.assertNotIn("function helper", section_2 + section_3)
            self.assertNotIn("function entry", section_2 + section_3)
            self.assertIn("nobody_calls_me", section_3)
            self.assertIn("lonely", report.stdout.split("== 4.")[1])
            below = subprocess.run(
                [sys.executable, str(SCRIPT), "--package", str(package), "--rcfile", str(folder / "rc.toml"), "--fail-under", "99.9"],
                cwd=folder, capture_output=True, text=True, timeout=120,
            )  # fmt: skip
            self.assertEqual(below.returncode, 1)
            self.assertIn("below the floor", below.stderr)


if __name__ == "__main__":
    unittest.main()
