"""sandbox_checks.py: the case phases start from regenerated fixtures (an app that creates a folder in its fixtures is not red on the second phase) and the retention step repeats
the first case that can be run twice in a row. Sabotage: `LC_SANDBOX_DIR=<a copy of the old sandbox_checks.py>` makes the integration test fail.
"""

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from typing import Any

import _paths  # noqa: F401  (must come first)
from _paths import ROOT

SANDBOX = Path(os.environ.get("LC_SANDBOX_DIR") or ROOT / "tests" / "release_sandbox")
sys.path.insert(0, str(SANDBOX))
import sandbox_checks as sc  # noqa: E402  (the sandbox folder is not a package)

MAKER = "import sys\nfrom pathlib import Path\nout = Path(sys.argv[1])\n(out / 'results').mkdir()\n"


def report(status: str, code: str | None = None) -> str:
    return json.dumps({"status": status, "code": code, "job_dir": "/x/%d" % len(sc.OUT)})


class FreshFixtures(unittest.TestCase):
    def test_regenerates_an_app_that_makes_its_fixtures(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            base = Path(t)
            (base / "make_fixtures.py").write_text(MAKER)
            (base / "fixtures" / "results" / "demo").mkdir(parents=True)
            ok, why = sc.fresh_fixtures(base)
            self.assertTrue(ok, why)
            self.assertEqual(sorted(p.name for p in (base / "fixtures" / "results").iterdir()), [])

    def test_leaves_shipped_fixtures_alone_and_says_so(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            base = Path(t)
            (base / "fixtures").mkdir()
            (base / "fixtures" / "a.csv").write_text("x")
            ok, why = sc.fresh_fixtures(base)
            self.assertTrue(ok)
            self.assertIn("left as they are", why)
            self.assertTrue((base / "fixtures" / "a.csv").exists())

    def test_a_failing_generator_is_not_silent(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            base = Path(t)
            (base / "make_fixtures.py").write_text("raise SystemExit(3)\n")
            ok, why = sc.fresh_fixtures(base)
            self.assertFalse(ok)
            self.assertIn("exit 3", why)


class RepeatableCase(unittest.TestCase):
    def setUp(self) -> None:
        self.real_lc = sc.lc
        self.calls: dict[str, int] = {}

    def tearDown(self) -> None:
        sc.lc = self.real_lc

    def fake(self, once_tools: set[str]) -> Any:
        def lc(*args: str, timeout: float = 900) -> tuple[int, str, str]:
            tool = args[2]
            self.calls[tool] = self.calls.get(tool, 0) + 1
            if tool in once_tools and self.calls[tool] > 1:
                return 1, report("FAILED", "already_exists"), ""
            return 0, report("COMPLETE"), ""

        return lc

    def cases(self) -> list[dict[str, Any]]:
        return [
            {"tool": "create_demo", "inputs": {}},
            {"tool": "failing_by_design", "inputs": {}, "expect": {"status": "FAILED"}},
            {"tool": "prepare", "inputs": {}},
        ]

    def test_skips_a_case_that_cannot_run_twice_and_names_it(self) -> None:
        sc.lc = self.fake({"create_demo"})
        with tempfile.TemporaryDirectory() as t:
            case, tried = sc.repeatable_case("A", self.cases(), Path(t))
        self.assertEqual(case and case["tool"], "prepare")
        self.assertEqual(len(tried), 1)
        self.assertIn("create_demo", tried[0])
        self.assertIn("already_exists", tried[0])

    def test_none_repeatable_is_reported_with_every_reason(self) -> None:
        sc.lc = self.fake({"create_demo", "prepare"})
        with tempfile.TemporaryDirectory() as t:
            case, tried = sc.repeatable_case("A", self.cases(), Path(t))
        self.assertIsNone(case)
        self.assertEqual(len(tried), 2)

    def test_the_first_case_is_used_when_it_repeats(self) -> None:
        sc.lc = self.fake(set())
        with tempfile.TemporaryDirectory() as t:
            case, tried = sc.repeatable_case("A", self.cases(), Path(t))
        self.assertEqual(case and case["tool"], "create_demo")
        self.assertEqual(tried, [])


class CasesPhases(unittest.TestCase):
    """The integration the real failure came from: the suite phase creates a folder in the fixtures, then the CLI phase runs the same case."""

    def setUp(self) -> None:
        self.real_lc = sc.lc
        sc.OUT.clear()

    def tearDown(self) -> None:
        sc.lc = self.real_lc

    def test_cli_phase_after_the_suite_does_not_hit_already_exists(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            base = Path(t)
            (base / "make_fixtures.py").write_text(MAKER)
            (base / "fixtures" / "results").mkdir(parents=True)
            cases = base / "cases.json"
            cases.write_text(
                json.dumps(
                    [
                        {
                            "tool": "create_demo",
                            "inputs": {"output_folder": "fixtures/results"},
                            "expect": {"max_seconds": 5},
                        }
                    ]
                )
            )
            demo = base / "fixtures" / "results" / "demo"

            def lc(*args: str, timeout: float = 900) -> tuple[int, str, str]:
                if args[0] == "test":  # the suite phase runs the case once and leaves its folder behind
                    demo.mkdir(parents=True, exist_ok=True)
                    return 0, json.dumps({"reports": [], "untested": []}), ""
                if demo.exists():
                    return 1, report("FAILED", "already_exists"), ""
                demo.mkdir(parents=True)
                return 0, report("COMPLETE"), ""

            sc.lc = lc
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                sc.cases(Namespace(app="A", module="m", cases=str(cases)))
            text = out.getvalue()
        self.assertIn("CHECK 4_fixtures_regenerated_between_phases PASS", text)
        self.assertIn("CHECK 4_cli_case_00_create_demo_COMPLETE PASS", text, text)


if __name__ == "__main__":
    unittest.main()
