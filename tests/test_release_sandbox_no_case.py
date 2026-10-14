"""`lc_tests/no_case.json`: the app-declared allow-list of tools without a case (tests/release_sandbox/no_case.py), its use in
sandbox_checks.py and in the workflow, and a sabotage test that breaks it one line at a time in a copy."""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import _paths  # noqa: F401  (must come first)
from _paths import ROOT

REAL = ROOT / "tests" / "release_sandbox"
SANDBOX = Path(os.environ.get("LC_SANDBOX_DIR") or REAL)  # the sabotage test points this at a broken copy
sys.path.insert(0, str(SANDBOX))
import no_case  # noqa: E402  (the sandbox folder is not a package)

LOGIC_TESTS = ["Declared", "Coverage", "ExtrasStep"]
WHY = {
    "stress_hang": "no grace-period kill in the case runner; covered by the host test suites and the sandbox extras",
    "stress_real_memory": "opt-in, uses real memory; covered by the sandbox extras",
}


class Declared(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = Path(tempfile.mkdtemp(prefix="lc_nocase_"))
        self.addCleanup(shutil.rmtree, self.folder, ignore_errors=True)
        self.path = self.folder / no_case.FILE_NAME

    def load(self, text: str) -> "tuple[dict[str, str], list[str]]":
        self.path.write_text(text, encoding="utf-8")
        return no_case.load_declared(self.path)

    def test_an_absent_file_declares_nothing_and_is_not_a_problem(self) -> None:
        self.assertEqual(no_case.load_declared(self.path), ({}, []))

    def test_a_valid_file_is_read(self) -> None:
        self.assertEqual(self.load(json.dumps(WHY)), (WHY, []))

    def test_every_kind_of_malformed_file_is_a_named_problem(self) -> None:
        for label, text in {
            "not json": "{nope",
            "array": "[]",
            "string": '"x"',
            "empty reason": '{"a": ""}',
            "blank reason": '{"a": "   "}',
            "number reason": '{"a": 3}',
            "null reason": '{"a": null}',
        }.items():
            with self.subTest(label):
                declared, problems = self.load(text)
                self.assertEqual(declared, {}, label)
                self.assertEqual(len(problems), 1, label)
                self.assertIn(
                    "no_case.json",
                    problems[0] if label in ("not json", "array", "string") else no_case.FILE_NAME,
                )

    def test_a_good_entry_survives_next_to_a_bad_one(self) -> None:
        declared, problems = self.load('{"a": "why", "b": ""}')
        self.assertEqual((declared, len(problems)), ({"a": "why"}, 1))


class Coverage(unittest.TestCase):
    def test_a_tool_without_a_case_and_not_declared_is_a_fail(self) -> None:
        found = no_case.coverage(["a", "b"], {"a"}, {}, [])
        self.assertEqual((found.unexplained, found.ok), (["b"], False))

    def test_a_declared_tool_without_a_case_passes_and_is_noted_with_its_reason(self) -> None:
        found = no_case.coverage(["a", "b"], {"a"}, {"b": "opt-in"}, [])
        self.assertTrue(found.ok)
        self.assertEqual(found.notes, ["NOTE 4_no_case_declared_b: opt-in"])

    def test_a_stale_exemption_is_a_fail_for_both_kinds(self) -> None:
        found = no_case.coverage(["a"], {"a"}, {"a": "x", "ghost": "y"}, [])
        self.assertFalse(found.ok)
        self.assertEqual(found.stale, ["a: it has a case", "ghost: it is not a tool of the schema"])
        self.assertEqual(found.notes, [])

    def test_a_malformed_file_is_a_fail_even_when_every_tool_has_a_case(self) -> None:
        found = no_case.coverage(["a"], {"a"}, {}, ["bad"])
        self.assertEqual((found.ok, found.problems), (False, ["bad"]))
        self.assertIn("file problems: ['bad']", found.detail())

    def test_no_exemptions_and_full_coverage_is_ok(self) -> None:
        self.assertTrue(no_case.coverage(["a"], {"a"}, {}, []).ok)


class ExtrasStep(unittest.TestCase):
    ON_PASS = "CHECK 4_stress_real_memory PASS x\nCHECK 5c_killed_after_cancel_names_the_cancel PASS y\n"

    def result(
        self, declared: "dict[str, str]", on: bool, text: str = "", problems: "list[str] | None" = None
    ) -> str:
        return no_case.extras_result(declared, problems or [], on, text)

    def test_nothing_exempt_passes(self) -> None:
        self.assertEqual(
            self.result({}, False),
            "CHECK 4_no_case_tools_are_run_by_extras PASS no tool is exempt from having a case",
        )

    def test_extras_off_is_an_explicit_note_naming_the_tools_never_a_pass(self) -> None:
        line = self.result(WHY, False)
        self.assertTrue(
            line.startswith("NOTE 4_no_case_tools_are_run_by_extras: playground_extras is false"), line
        )
        self.assertIn("were NOT run in this run", line)
        self.assertIn("stress_hang, stress_real_memory", line)

    def test_extras_on_with_a_check_line_per_tool_passes(self) -> None:
        self.assertTrue(
            self.result(WHY, True, self.ON_PASS).startswith("CHECK 4_no_case_tools_are_run_by_extras PASS")
        )

    def test_extras_on_and_a_missing_line_fails_naming_the_tool(self) -> None:
        line = self.result(WHY, True, "CHECK 4_stress_real_memory PASS x\n")
        self.assertTrue(line.startswith("CHECK 4_no_case_tools_are_run_by_extras FAIL"), line)
        self.assertIn("stress_hang (expected CHECK 5c_killed_after_cancel_names_the_cancel)", line)
        self.assertNotIn("stress_real_memory (", line)

    def test_a_tool_no_extras_check_is_known_for_fails(self) -> None:
        line = self.result({"mystery": "why"}, True, self.ON_PASS)
        self.assertIn("FAIL", line)
        self.assertIn("mystery (no extras check is known for it)", line)

    def test_a_malformed_file_fails_in_both_modes(self) -> None:
        for on in (True, False):
            self.assertIn(" FAIL bad", self.result({}, on, problems=["bad"]))

    def test_the_command_reads_the_file_next_to_the_cases(self) -> None:
        folder = Path(tempfile.mkdtemp(prefix="lc_nocase_cmd_"))
        self.addCleanup(shutil.rmtree, folder, ignore_errors=True)
        (folder / "cases.json").write_text("[]", encoding="utf-8")
        (folder / no_case.FILE_NAME).write_text(json.dumps(WHY), encoding="utf-8")
        (folder / "pg.txt").write_text(self.ON_PASS, encoding="utf-8")

        def run(*extra: str) -> str:
            done = subprocess.run(
                [sys.executable, str(SANDBOX / "no_case.py"), "extras", "--cases", str(folder / "cases.json"), *extra],
                capture_output=True, text=True, encoding="utf-8",
            )  # fmt: skip
            self.assertEqual(done.returncode, 0, done.stderr)
            return done.stdout.strip()

        self.assertTrue(
            run(
                "--extras", "playground", "--checks", str(folder / "pg.txt"), str(folder / "absent.txt")
            ).startswith("CHECK 4_no_case_tools_are_run_by_extras PASS")
        )
        self.assertTrue(
            run("--extras", "playground", "--checks", str(folder / "absent.txt")).startswith(
                "CHECK 4_no_case_tools_are_run_by_extras FAIL"
            )
        )
        self.assertTrue(
            run("--extras", "", "--checks", str(folder / "pg.txt")).startswith(
                "NOTE 4_no_case_tools_are_run_by_extras"
            )
        )


class Wiring(unittest.TestCase):
    def test_the_mapped_extras_checks_exist_in_playground_extras(self) -> None:
        text = (REAL / "playground_extras.py").read_text(encoding="utf-8")
        for tool, ids in no_case.EXTRAS_CHECKS.items():
            for cid in ids:
                self.assertIn('"%s"' % cid, text, tool)
            self.assertIn(tool, text)

    def test_sandbox_checks_uses_the_allow_list_for_its_check(self) -> None:
        text = (REAL / "sandbox_checks.py").read_text(encoding="utf-8")
        self.assertIn('rec("4_every_tool_has_a_case", found.ok, found.detail())', text)
        self.assertIn("no_case.load_declared(", text)
        self.assertIn("print(note, flush=True)", text)

    def test_the_workflow_runs_the_extras_step_after_the_extras_and_with_the_needed_files(self) -> None:
        text = (ROOT / ".github" / "workflows" / "release_sandbox.yml").read_text(encoding="utf-8")
        step = re.search(
            r"\n      - name: \(4\) Tools declared without a case.*?(?=\n      - |\n\n)", text, re.S
        )
        self.assertIsNotNone(step)
        assert step is not None
        for needle in (
            "if: env.HAS_TOOLS == 'true'",
            "no_case.py extras",
            '--extras "$EXTRAS"',
            "checks_pg_tools.txt checks_pg_failures.txt",
            "no_case.py crashed",
        ):
            self.assertIn(needle, step.group(0))
        self.assertLess(text.index("playground_extras.py failures"), text.index("no_case.py extras"))


BREAKS = [
    ("no_case.py", "    if not path.exists():\n        return {}, []", "    if not path.exists():\n        return {}, ['absent']"),
    ("no_case.py", "if not isinstance(data, dict):", "if False:"),
    ("no_case.py", "if not isinstance(why, str) or not why.strip()\n    ]", "if not isinstance(why, str)\n    ]"),
    ("no_case.py", "unexplained=[i for i in all_ids if i not in covered and i not in declared]", "unexplained=[]"),
    ("no_case.py", "        if tool in covered or tool not in all_ids\n    ]", "        if False\n    ]"),
    ("no_case.py", "return not (self.unexplained or self.stale or self.problems)", "return not (self.unexplained or self.problems)"),
    ("no_case.py", "    if not extras_on:\n", "    if True:\n"),
    ("no_case.py", "        if not printed.intersection(EXTRAS_CHECKS.get(tool, []))", "        if False"),
    ("no_case.py", "    if problems:\n        return", "    if False:\n        return"),
    ("no_case.py", 'return "CHECK %s PASS no tool is exempt from having a case" % EXTRAS_ID', 'return "CHECK %s PASS no tool is exempt" % EXTRAS_ID'),
]  # fmt: skip


def broken_copy(folder: Path, file: str, old: str, new: str) -> Path:
    copy = folder / "release_sandbox"
    shutil.copytree(REAL, copy)
    target = copy / file
    text = target.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise AssertionError("%s: the text to break occurs %d times: %r" % (file, text.count(old), old))
    target.write_text(text.replace(old, new), encoding="utf-8")
    return copy


class Sabotage(unittest.TestCase):
    """Do the tests above have teeth? Each break of no_case.py must turn them red by an assertion."""

    def run_logic_tests(self, sandbox: Path) -> "subprocess.CompletedProcess[str]":
        names = ["test_release_sandbox_no_case.%s" % n for n in LOGIC_TESTS]
        return subprocess.run(
            [sys.executable, "-m", "unittest", *names],
            cwd=ROOT / "tests", capture_output=True, text=True, encoding="utf-8",
            env={**os.environ, "LC_SANDBOX_DIR": str(sandbox), "PYTHONPATH": str(ROOT)},
        )  # fmt: skip

    def test_the_unbroken_copy_is_green(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lc_nocase_sab_") as folder:
            done = self.run_logic_tests(
                broken_copy(Path(folder), "no_case.py", "FILE_NAME = ", "FILE_NAME = ")
            )
            self.assertEqual(done.returncode, 0, (done.stdout + done.stderr)[-3000:])

    def test_every_break_turns_the_tests_red(self) -> None:
        survivors: list[str] = []
        for file, old, new in BREAKS:
            with tempfile.TemporaryDirectory(prefix="lc_nocase_sab_") as folder:
                done = self.run_logic_tests(broken_copy(Path(folder), file, old, new))
            if done.returncode == 0:
                survivors.append("%s: %s" % (file, old))
            else:
                self.assertRegex(done.stdout + done.stderr, r"FAILED \((failures|errors)", old)
        self.assertEqual(survivors, [], "these breaks of the allow-list were NOT caught: add a test for each")


if __name__ == "__main__":
    unittest.main()
