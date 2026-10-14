"""The fail-safe of the release sandbox: a CHECK that never printed is red, the verdict fails the job, expected_fail is never silent.

Covers verdict.py (guard and verdict), required_checks.json, the early returns of hosts_check.py and the wiring in
release_sandbox.yml (dispatch only, so a typo would only show on a real run). The last class is the sabotage test: it breaks the
logic one line at a time in a copy and requires the tests above to go red.
"""

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
import verdict  # noqa: E402  (the sandbox folder is not a package)

WORKFLOW = (ROOT / ".github" / "workflows" / "release_sandbox.yml").read_text(encoding="utf-8")
SPEC = verdict.load_spec(SANDBOX / "required_checks.json")
LOGIC_TESTS = ["VerdictLogic", "RequiredIds", "GuardAndVerdictCommands", "HostsCheckEarlyReturns"]


def run(
    script: str, *args: str, extra_env: "dict[str, str] | None" = None
) -> "subprocess.CompletedProcess[str]":
    env = {**os.environ, "PYTHONPATH": str(ROOT), **(extra_env or {})}
    return subprocess.run(
        [sys.executable, str(SANDBOX / script), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )


class VerdictLogic(unittest.TestCase):
    def test_only_check_lines_with_a_status_count_and_a_fail_beats_a_pass(self) -> None:
        text = "CHECK a PASS x\nNOTE b FAIL not a check\nCHECK c FAIL why\nCHECK d PASS\nCHECK d FAIL\nCHECK e WEIRD\nSECTION x: CHECK f FAIL\n"
        self.assertEqual(verdict.parse_checks(text), {"a": True, "c": False, "d": False})

    def test_a_failed_id_makes_the_verdict_red(self) -> None:
        result = verdict.evaluate("CHECK a PASS\nCHECK b FAIL x\n", [])
        self.assertEqual((result.unexpected, result.exit_code), (["b"], 1))

    def test_all_passing_is_green_and_notes_do_not_count(self) -> None:
        result = verdict.evaluate("CHECK a PASS\nNOTE n FAIL looks like one\n", [])
        self.assertEqual((result.failed, result.exit_code), ([], 0))

    def test_no_check_line_at_all_is_red(self) -> None:
        self.assertEqual(verdict.evaluate("NOTE only\n", []).exit_code, 1)
        self.assertEqual(verdict.evaluate("", ["a"]).exit_code, 1)

    def test_expected_fail_ids_are_not_counted_but_others_are(self) -> None:
        text = "CHECK a FAIL\nCHECK b FAIL\nCHECK c PASS\n"
        result = verdict.evaluate(text, ["a"])
        self.assertEqual((result.expected, result.unexpected, result.exit_code), (["a"], ["b"], 1))
        both = verdict.evaluate(text, ["a", "b"])
        self.assertEqual((both.unexpected, both.exit_code), ([], 0))

    def test_an_expected_fail_that_passed_is_reported_as_stale(self) -> None:
        result = verdict.evaluate("CHECK a PASS\nCHECK b FAIL\n", ["a", "b"])
        self.assertEqual((result.not_failing, result.exit_code), (["a"], 0))

    def test_ids_are_split_on_commas_and_trimmed(self) -> None:
        self.assertEqual(verdict.parse_ids(" a, b ,,c "), ["a", "b", "c"])
        self.assertEqual(verdict.parse_ids(""), [])

    def test_a_missing_check_line_is_found_and_written_as_a_fail(self) -> None:
        text = "CHECK a PASS\nCHECK b FAIL\n"
        self.assertEqual(verdict.missing_ids(text, ["a", "b", "c"]), ["c"])
        self.assertEqual(
            verdict.missing_lines(["c"]), ["CHECK missing_c FAIL expected CHECK line never printed"]
        )
        guarded = text + "\n".join(verdict.missing_lines(["c"])) + "\n"
        self.assertEqual(verdict.evaluate(guarded, []).unexpected, ["b", "missing_c"])
        self.assertEqual(verdict.evaluate(guarded, ["b", "missing_c"]).exit_code, 0)


class RequiredIds(unittest.TestCase):
    def test_the_tools_and_no_tools_variants_differ(self) -> None:
        with_tools = verdict.required_ids(SPEC, True, "Linux")
        without = verdict.required_ids(SPEC, False, "Linux")
        self.assertIn("hosts_3_list_shows_the_declaration", with_tools)
        self.assertIn("6f_run_records_keep_50", with_tools)
        self.assertNotIn("hosts_3_list_shows_the_declaration", without)
        self.assertNotIn("6f_run_records_keep_50", without)
        self.assertNotIn("4_cases_suite", without)
        self.assertIn("hosts_1_app_without_tools_registers_nothing", without)
        self.assertIn("1b_app_without_tools_registered_nothing", without)
        self.assertNotIn("1b_tools_registered", without)

    def test_the_systems_differ(self) -> None:
        linux = verdict.required_ids(SPEC, True, "Linux")
        mac = verdict.required_ids(SPEC, True, "macOS")
        windows = verdict.required_ids(SPEC, True, "Windows")
        self.assertEqual(linux, mac)
        self.assertIn("8a_prefix_removed", linux)
        self.assertNotIn("8a_prefix_removed", windows)
        self.assertIn("8b_registry_entry_removed_by_uninstaller", windows)
        self.assertNotIn("8b_registry_entry_removed_by_uninstaller", linux)
        self.assertIn("W5a_no_app_python_left_after_workers_closed", windows)
        self.assertNotIn("W2_no_cmd_syntax_errors_in_menuinst_debug_log", linux)
        no_tools_windows = verdict.required_ids(SPEC, False, "Windows")
        self.assertIn("W2_no_cmd_syntax_errors_in_menuinst_debug_log", no_tools_windows)
        self.assertNotIn("W3_list_shows_the_real_version", no_tools_windows)

    def test_an_unknown_system_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            verdict.required_ids(SPEC, True, "Solaris")

    def test_no_id_is_listed_twice_in_a_run(self) -> None:
        for tools in (True, False):
            for system in verdict.SYSTEMS:
                ids = verdict.required_ids(SPEC, tools, system)
                self.assertEqual(len(ids), len(set(ids)), (tools, system))

    def test_every_required_id_is_printed_by_a_script_or_a_step_of_the_workflow(self) -> None:
        text = WORKFLOW + "".join(
            (REAL / name).read_text(encoding="utf-8") for name in ("sandbox_checks.py", "hosts_check.py")
        )
        every = {i for section in SPEC["sections"].values() for ids in section.values() for i in ids}
        self.assertEqual([i for i in sorted(every) if i not in text], [])

    def test_the_file_has_only_known_keys(self) -> None:
        keys = {"all", "tools", "no_tools", "unix", "windows", "windows_tools"}
        for name, section in SPEC["sections"].items():
            self.assertLessEqual(set(section), keys, name)


class GuardAndVerdictCommands(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = Path(tempfile.mkdtemp(prefix="lc_verdict_"))
        self.addCleanup(shutil.rmtree, self.folder, ignore_errors=True)
        self.checks = self.folder / "all_checks.txt"

    def passing_run(self, tools: bool, system: str) -> str:
        return "".join("CHECK %s PASS ok\n" % i for i in verdict.required_ids(SPEC, tools, system))

    def test_a_complete_run_passes_the_guard_and_the_verdict(self) -> None:
        self.checks.write_text(self.passing_run(True, "Linux"), encoding="utf-8")
        self.assertEqual(
            run(
                "verdict.py", "guard", "--checks", str(self.checks), "--os", "Linux", "--has-tools", "true"
            ).returncode,
            0,
        )
        self.assertNotIn("missing_", self.checks.read_text(encoding="utf-8"))
        done = run("verdict.py", "verdict", "--checks", str(self.checks))
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertIn("VERDICT GREEN", done.stdout)

    def test_the_hosts_check_that_printed_nothing_turns_the_run_red(self) -> None:
        lines = [
            ln for ln in self.passing_run(True, "Linux").splitlines() if not ln.startswith("CHECK hosts_3_")
        ]
        self.checks.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.assertEqual(
            run("verdict.py", "verdict", "--checks", str(self.checks)).returncode,
            0,
            "without the guard the gap is invisible",
        )
        done = run(
            "verdict.py", "guard", "--checks", str(self.checks), "--os", "Linux", "--has-tools", "true"
        )
        self.assertIn(
            "CHECK missing_hosts_3_list_shows_the_declaration FAIL expected CHECK line never printed",
            done.stdout,
        )
        red = run("verdict.py", "verdict", "--checks", str(self.checks))
        self.assertEqual(red.returncode, 1)
        self.assertIn("VERDICT RED: CHECK missing_hosts_3_list_shows_the_declaration FAIL", red.stdout)

    def test_an_empty_file_is_red_with_every_required_id_missing(self) -> None:
        self.checks.write_text("", encoding="utf-8")
        run("verdict.py", "guard", "--checks", str(self.checks), "--os", "Windows", "--has-tools", "false")
        found = verdict.parse_checks(self.checks.read_text(encoding="utf-8"))
        self.assertEqual(
            sorted(found), sorted("missing_" + i for i in verdict.required_ids(SPEC, False, "Windows"))
        )
        self.assertEqual(run("verdict.py", "verdict", "--checks", str(self.checks)).returncode, 1)

    def test_expected_fail_turns_the_verdict_green_and_says_so_in_a_note(self) -> None:
        self.checks.write_text(
            self.passing_run(True, "Linux") + "CHECK napari_driver_printed_no_check FAIL x\n",
            encoding="utf-8",
        )
        red = run("verdict.py", "verdict", "--checks", str(self.checks))
        self.assertEqual(red.returncode, 1)
        green = run(
            "verdict.py",
            "verdict",
            "--checks",
            str(self.checks),
            "--expected-fail",
            "napari_driver_printed_no_check, other",
        )
        self.assertEqual(green.returncode, 0, green.stdout)
        self.assertIn("NOTE expected_fail input is set: napari_driver_printed_no_check, other", green.stdout)
        self.assertIn("NOTE napari_driver_printed_no_check FAILED, as expected_fail says", green.stdout)
        self.assertIn("NOTE other is in expected_fail but did not fail", green.stdout)

    def test_bad_input_is_exit_2_not_green(self) -> None:
        self.assertEqual(
            run("verdict.py", "verdict", "--checks", str(self.folder / "absent.txt")).returncode, 2
        )
        self.checks.write_text("", encoding="utf-8")
        for bad in (("--os", "Linux", "--has-tools", ""), ("--os", "Plan9", "--has-tools", "true")):
            done = run("verdict.py", "guard", "--checks", str(self.checks), *bad)
            self.assertEqual(done.returncode, 2, bad)
            self.assertEqual(self.checks.read_text(encoding="utf-8"), "", "nothing is appended on bad input")


class HostsCheckEarlyReturns(unittest.TestCase):
    """hosts_check.py: every early return and every crash still prints a FAIL for each id it did not report."""

    ENTRY_IDS = (
        "hosts_1_registry_entry_declares_the_hosts",
        "hosts_2_reference_function_matches_the_matrix",
        "hosts_3_list_shows_the_declaration",
    )

    def setUp(self) -> None:
        self.home = Path(tempfile.mkdtemp(prefix="lchome_"))
        self.addCleanup(shutil.rmtree, self.home, ignore_errors=True)
        (self.home / "apps").mkdir()

    def check(self, *args: str, pythonpath: str = str(ROOT)) -> "tuple[int, str]":
        done = run(
            "hosts_check.py",
            *args,
            extra_env={"LC_HOME": str(self.home), "LC_APPS_PATH": "", "PYTHONPATH": pythonpath},
        )
        return done.returncode, done.stdout

    def statuses(self, out: str) -> "dict[str, bool]":
        return verdict.parse_checks(out)

    def test_no_registry_entry_fails_every_id_and_says_not_run(self) -> None:
        code, out = self.check("entry", "--app", "ghost", "--expect-hosts", "notebook")
        self.assertEqual(code, 1)
        self.assertEqual(self.statuses(out), {i: False for i in self.ENTRY_IDS})
        self.assertIn(
            "CHECK hosts_2_reference_function_matches_the_matrix FAIL not run: no registry entry for ghost",
            out,
        )
        self.assertIn(
            "CHECK hosts_3_list_shows_the_declaration FAIL not run: no registry entry for ghost", out
        )

    def test_a_tools_without_app_hosts_fails_hosts_3_as_not_run(self) -> None:
        # an installed Tools (an editable install in CI) would shadow a stub package: poison the one import instead
        stub = Path(tempfile.mkdtemp(prefix="lc_stub_"))
        self.addCleanup(shutil.rmtree, stub, ignore_errors=True)
        (stub / "sitecustomize.py").write_text(
            "import sys\nsys.modules['labconstrictor_tools.app_hosts'] = None\n", encoding="utf-8"
        )
        (self.home / "apps" / "app.json").write_text(
            json.dumps({"name": "app", "hosts": ["notebook"]}), encoding="utf-8"
        )
        code, out = self.check(
            "entry",
            "--app",
            "app",
            "--expect-hosts",
            "notebook",
            pythonpath=str(stub) + os.pathsep + str(ROOT),
        )
        self.assertEqual(code, 1)
        self.assertEqual(
            self.statuses(out),
            {
                "hosts_1_registry_entry_declares_the_hosts": True,
                "hosts_2_reference_function_matches_the_matrix": False,
                "hosts_3_list_shows_the_declaration": False,
            },
        )
        self.assertIn(
            "CHECK hosts_3_list_shows_the_declaration FAIL not run: this Tools has no app_hosts", out
        )

    def test_an_entry_without_hosts_still_reports_all_three_ids(self) -> None:
        (self.home / "apps" / "app.json").write_text(json.dumps({"name": "app"}), encoding="utf-8")
        code, out = self.check("entry", "--app", "app", "--expect-hosts", "notebook")
        self.assertEqual(code, 1)
        found = self.statuses(out)
        self.assertTrue(set(self.ENTRY_IDS) <= set(found), out)
        self.assertFalse(found["hosts_1_registry_entry_declares_the_hosts"])
        self.assertIn("the installer did not pass hosts", out)

    def test_a_crash_is_a_named_fail_and_the_unprinted_ids_are_failed_too(self) -> None:
        (self.home / "apps" / "app.json").write_text("{not json", encoding="utf-8")
        code, out = self.check("entry", "--app", "app", "--expect-hosts", "notebook")
        self.assertEqual(code, 1)
        found = self.statuses(out)
        self.assertEqual(found, {"hosts_0_check_crashed": False, **{i: False for i in self.ENTRY_IDS}})
        for cid in self.ENTRY_IDS:
            self.assertIn("CHECK %s FAIL printed no CHECK line" % cid, out)

    def test_a_crash_in_the_no_tools_variant_fails_its_id(self) -> None:
        (self.home / "apps" / "app.json").write_text("{not json", encoding="utf-8")
        code, out = self.check("entry", "--app", "app", "--no-tools")
        self.assertEqual(code, 1)
        self.assertIn("CHECK hosts_1_app_without_tools_registers_nothing FAIL printed no CHECK line", out)

    def test_the_required_lists_equal_the_ids_of_required_checks_json(self) -> None:
        sys.path.insert(0, str(SANDBOX))
        import hosts_check

        self.assertEqual(list(hosts_check.REQUIRED_ENTRY), SPEC["sections"]["hosts"]["tools"])
        self.assertEqual(list(hosts_check.REQUIRED_NO_TOOLS), SPEC["sections"]["hosts"]["no_tools"])


class WorkflowWiring(unittest.TestCase):
    def step(self, name_start: str) -> str:
        parts = re.split(r"\n      - ", WORKFLOW)
        found = [p for p in parts if p.startswith(("name: " + name_start, 'name: "' + name_start))]
        self.assertEqual(len(found), 1, name_start)
        return found[0]

    def test_the_input_expected_fail_exists_and_defaults_to_empty(self) -> None:
        block = re.search(r"\n      expected_fail:\n((?:        .*\n)+)", WORKFLOW)
        self.assertIsNotNone(block)
        assert block is not None
        self.assertIn('default: ""', block.group(1))
        self.assertIn("required: false", block.group(1))

    def test_the_summary_runs_the_guard_before_it_counts(self) -> None:
        step = self.step("Summary of every CHECK line")
        self.assertIn("if: always()", step)
        self.assertLess(step.index("verdict.py guard"), step.index("grep -c ' FAIL'"))
        self.assertIn("CHECK guard_could_not_run FAIL", step)

    def test_the_verdict_is_the_last_step_runs_always_and_comes_after_the_upload(self) -> None:
        steps = re.split(r"\n      - ", WORKFLOW)
        last = steps[-1]
        self.assertTrue(last.startswith("name: Verdict"), last[:60])
        self.assertIn("if: always()", last)
        self.assertNotIn("continue-on-error", last)
        self.assertIn("verdict.py verdict", last)
        self.assertIn('--expected-fail "$EXPECTED_FAIL"', last)
        self.assertIn("exit $RC", last)
        self.assertTrue(steps[-2].startswith("# last") or "Keep the evidence" in steps[-2], steps[-2][:80])
        self.assertIn("name: Keep the evidence\n        if: always()", WORKFLOW)

    def test_the_uninstall_and_update_checks_reach_all_checks_txt(self) -> None:
        for name in ("(8) Uninstall (Linux/macOS)", "(8) Nothing else of the user's was touched"):
            self.assertIn("checks_uninstall.txt", self.step(name), name)
        self.assertIn("checks_uninstall.txt", self.step("(8) Uninstall (Windows)"))
        self.assertIn("checks_update.txt", self.step("(7) Checks after the update"))
        self.assertIn("checks_install.txt", self.step("Windows-only check W2"))

    def test_napari_ref_is_fetched_as_a_branch_or_a_tag(self) -> None:
        self.assertIn("/archive/${{ inputs.napari_ref }}.zip", WORKFLOW)
        self.assertNotIn("refs/heads/${{ inputs.napari_ref", WORKFLOW)
        block = re.search(r"\n      napari_ref:\n        description: \"([^\"]*)\"", WORKFLOW)
        assert block is not None
        self.assertIn("Branch or tag", block.group(1))
        self.assertIn("archive/<ref>.zip", block.group(1))


# One deliberate break of the fail-safe each: file, text to replace (it must occur exactly once), replacement.
BREAKS = [
    ("verdict.py", 'found.get(words[1], True) and words[2] == "PASS"', "True"),
    ("verdict.py", "return [i for i in required if i not in seen]", "return []"),
    ("verdict.py", "unexpected=[i for i in failed if i not in expected_fail]", "unexpected=[]"),
    ("verdict.py", "return 1 if self.unexpected or self.no_checks else 0", "return 1 if self.unexpected else 0"),
    ("verdict.py", '"windows" if windows else "unix"', '"unix"'),
    ("verdict.py", '"tools" if has_tools else "no_tools"', '"tools"'),
    ("verdict.py", "        not_failing=[i for i in expected_fail if i not in failed],", "        not_failing=[],"),
    ("hosts_check.py", '        if cid not in seen:\n            rec(cid, False, "not run: %s" % reason)', "        pass"),
    ("hosts_check.py", '            rec(cid, False, "printed no CHECK line")', "            pass"),
    ("hosts_check.py", 'not_run(REQUIRED_ENTRY, "no registry entry for %s" % app)', "pass"),
    ("hosts_check.py", 'not_run(REQUIRED_ENTRY, "this Tools has no app_hosts (older than app_hosts_v1)")', "pass"),
    ("hosts_check.py", 'rec("hosts_0_check_crashed", False,', 'rec("hosts_0_check_crashed", True,'),
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
    """Do the tests above have teeth? Break the fail-safe one line at a time in a copy: each break must turn them red by an assertion."""

    def run_logic_tests(self, sandbox: Path) -> "subprocess.CompletedProcess[str]":
        names = ["test_release_sandbox_verdict.%s" % n for n in LOGIC_TESTS]
        return subprocess.run(
            [sys.executable, "-m", "unittest", *names],
            cwd=ROOT / "tests", capture_output=True, text=True, encoding="utf-8",
            env={**os.environ, "LC_SANDBOX_DIR": str(sandbox), "PYTHONPATH": str(ROOT)},
        )  # fmt: skip

    def test_the_unbroken_copy_is_green(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lc_verdict_sab_") as folder:
            done = self.run_logic_tests(broken_copy(Path(folder), "verdict.py", "SYSTEMS = (", "SYSTEMS = ("))
            self.assertEqual(done.returncode, 0, (done.stdout + done.stderr)[-3000:])

    def test_every_break_turns_the_tests_red(self) -> None:
        survivors: list[str] = []
        for file, old, new in BREAKS:
            with tempfile.TemporaryDirectory(prefix="lc_verdict_sab_") as folder:
                done = self.run_logic_tests(broken_copy(Path(folder), file, old, new))
            if done.returncode == 0:
                survivors.append("%s: %s" % (file, old))
            else:
                self.assertRegex(done.stdout + done.stderr, r"FAILED \((failures|errors)", file + ": " + old)
        self.assertEqual(survivors, [], "these breaks of the fail-safe were NOT caught: add a test for each")


if __name__ == "__main__":
    unittest.main()
