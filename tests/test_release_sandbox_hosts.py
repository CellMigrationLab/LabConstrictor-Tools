"""The per-app host expectations of the release sandbox (tests/release_sandbox/expected_hosts.json), the check that reads them
and the workflow that uses them: they must agree with the matrix of docs/PROTOCOL.md and with the reference function.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import _paths  # noqa: F401  (must come first)
from _paths import GENERIC_PREFIX, ROOT, SYNTHETIC_MODULE
from test_cli_and_registry import cli

from labconstrictor_tools import app_hosts

SANDBOX = ROOT / "tests" / "release_sandbox"
sys.path.insert(0, str(SANDBOX))
import expected_hosts  # noqa: E402  (the sandbox folder is not a package)

MATRIX = {
    "CellTracksColab": {"napari": "not_listed", "fiji": "not_listed", "qupath": "not_listed"},
    "GuessTheCondition": {"napari": "listed", "fiji": "listed", "qupath": "listed"},
    "LabConstrictorPlayground": {"napari": "listed", "fiji": "listed", "qupath": "listed"},
    "NucleiSky": {"napari": "listed", "fiji": "listed", "qupath": "listed"},
    "VLab4Mic": {"napari": "listed", "fiji": "listed", "qupath": "not_listed"},
}


class ExpectedHosts(unittest.TestCase):
    def test_the_file_is_valid_and_is_the_decided_matrix(self) -> None:
        data = expected_hosts.load()
        self.assertEqual(sorted(data["apps"]), sorted(MATRIX))
        for name, row in data["apps"].items():
            found = expected_hosts.expectation(data, name, row["repo"])
            self.assertEqual({h: found[h] for h in expected_hosts.GUI_HOSTS}, MATRIX[name], name)
            self.assertIn("notebook", row["hosts"], name)
        self.assertEqual(data["apps"]["CellTracksColab"]["tools_module"], "optional")
        for name in set(MATRIX) - {"CellTracksColab"}:
            self.assertEqual(data["apps"][name]["tools_module"], "required", name)

    def test_it_agrees_with_the_reference_function_for_every_app_and_host(self) -> None:
        data = expected_hosts.load()
        for name, row in data["apps"].items():
            for host in expected_hosts.GUI_HOSTS:
                with self.subTest(app=name, host=host):
                    listed, _ = app_hosts.listed_for({"name": name, "hosts": row["hosts"]}, host)
                    self.assertEqual("listed" if listed else "not_listed", MATRIX[name][host])

    def test_it_agrees_with_the_matrix_vectors_of_conformance_json(self) -> None:
        from labconstrictor_tools import conformance

        data = expected_hosts.load()
        by_alias = {"Playground": "LabConstrictorPlayground"}
        for case in conformance.load()["app_hosts"]["cases"]:
            if case["case"].startswith("matrix: ") and case["host"] != "notebook":
                app = by_alias.get(case["entry"]["name"], case["entry"]["name"])
                self.assertEqual(
                    sorted(case["entry"]["hosts"]), sorted(data["apps"][app]["hosts"]), case["case"]
                )

    def test_an_app_without_a_row_is_refused_not_defaulted(self) -> None:
        data = expected_hosts.load()
        with self.assertRaises(ValueError) as caught:
            expected_hosts.expectation(data, "NewApp")
        self.assertIn("never assumes 'listed everywhere'", str(caught.exception))
        found = expected_hosts.expectation(data, "NewApp", "o/n", "notebook,fiji")
        self.assertEqual(
            (found["napari"], found["fiji"], found["qupath"]), ("not_listed", "listed", "not_listed")
        )

    def test_a_row_of_another_repository_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            expected_hosts.expectation(expected_hosts.load(), "VLab4Mic", "SomeoneElse/vlab4mic")

    def test_a_bad_override_is_refused(self) -> None:
        for bad in ("", "napari,napari", "emacs", "Napari"):
            with self.subTest(bad), self.assertRaises(ValueError):
                expected_hosts.parse_hosts(bad)

    def test_the_validator_names_every_kind_of_damage(self) -> None:
        good = json.loads((SANDBOX / "expected_hosts.json").read_text(encoding="utf-8"))
        self.assertEqual(expected_hosts.validate(good), [])
        for label, change in {
            "version": lambda d: d.update(expected_hosts=2),
            "empty hosts": lambda d: d["apps"]["NucleiSky"].update(hosts=[]),
            "unknown host": lambda d: d["apps"]["NucleiSky"].update(hosts=["emacs"]),
            "tools_module": lambda d: d["apps"]["NucleiSky"].update(tools_module="maybe"),
            "repo": lambda d: d["apps"]["NucleiSky"].update(repo="nucleisky"),
        }.items():
            with self.subTest(label):
                broken = json.loads(json.dumps(good))
                change(broken)
                self.assertTrue(expected_hosts.validate(broken), label)

    def test_the_env_command_prints_what_the_workflow_reads(self) -> None:
        done = subprocess.run(
            [sys.executable, str(SANDBOX / "expected_hosts.py"), "env", "--app-name", "VLab4Mic",
             "--repo", "CellMigrationLab/labconstrictor-vlab4mic"],
            capture_output=True, text=True, encoding="utf-8",
        )  # fmt: skip
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(
            done.stdout.split(),
            ["EXPECT_HOSTS=notebook,napari,fiji", "EXPECT_NAPARI=listed", "EXPECT_FIJI=listed",
             "EXPECT_QUPATH=not_listed", "TOOLS_MODULE=required"],
        )  # fmt: skip
        refused = subprocess.run(
            [sys.executable, str(SANDBOX / "expected_hosts.py"), "env", "--app-name", "Nope"],
            capture_output=True, text=True, encoding="utf-8",
        )  # fmt: skip
        self.assertEqual(refused.returncode, 2)


class HostsCheck(unittest.TestCase):
    """hosts_check.py against a private registry: it must say PASS for the declared matrix and FAIL for anything else."""

    def setUp(self) -> None:
        self.home = Path(tempfile.mkdtemp(prefix="lchome_"))

    def register(self, *extra: str) -> None:
        done = cli("register", "--name", "app", "--prefix", str(GENERIC_PREFIX), "--module", SYNTHETIC_MODULE,
                   "--version", "1", *extra, home=self.home)  # fmt: skip
        self.assertEqual(done.returncode, 0, done.stderr)

    def check(self, *args: str) -> "tuple[int, str]":
        done = subprocess.run(
            [sys.executable, str(SANDBOX / "hosts_check.py"), *args],
            capture_output=True, text=True, encoding="utf-8",
            env={**os.environ, "LC_HOME": str(self.home), "LC_APPS_PATH": "", "PYTHONPATH": str(ROOT)},
        )  # fmt: skip
        return done.returncode, done.stdout

    def test_the_declared_matrix_passes(self) -> None:
        self.register("--hosts", "notebook,napari,fiji")
        code, out = self.check("entry", "--app", "app", "--expect-hosts", "notebook,fiji,napari")
        self.assertEqual(code, 0, out)
        self.assertEqual(out.count(" PASS "), 3, out)

    def test_a_wrong_declaration_fails_by_name(self) -> None:
        self.register("--hosts", "notebook,napari,fiji,qupath")
        code, out = self.check("entry", "--app", "app", "--expect-hosts", "notebook,napari,fiji")
        self.assertEqual(code, 1)
        self.assertIn("CHECK hosts_1_registry_entry_declares_the_hosts FAIL", out)
        self.assertIn("CHECK hosts_2_reference_function_matches_the_matrix FAIL", out)
        self.assertIn("qupath: listed=True", out)

    def test_an_app_registered_without_hosts_is_a_failure_that_says_why(self) -> None:
        self.register()
        code, out = self.check("entry", "--app", "app", "--expect-hosts", "notebook")
        self.assertEqual(code, 1)
        self.assertIn("the installer did not pass hosts", out)

    def test_an_app_without_tools_must_leave_no_entry(self) -> None:
        code, out = self.check("entry", "--app", "ghost", "--no-tools")
        self.assertEqual(code, 0, out)
        self.assertIn("CHECK hosts_1_app_without_tools_registers_nothing PASS", out)
        self.register("--hosts", "notebook")
        code, out = self.check("entry", "--app", "app", "--no-tools")
        self.assertEqual(code, 1)
        self.assertIn("hosts_1_app_without_tools_registers_nothing FAIL", out)

    def test_the_sentence_command_prints_what_a_host_must_log(self) -> None:
        self.register("--hosts", "notebook,fiji")
        code, out = self.check("sentence", "--app", "app", "--host", "qupath")
        self.assertEqual(
            (code, out.strip()), (0, "'app' is not listed in qupath: the app declares hosts: notebook, fiji")
        )
        self.assertEqual(self.check("sentence", "--app", "app", "--host", "fiji")[1].strip(), "")


class NapariDriver(unittest.TestCase):
    def test_it_refuses_to_run_without_an_expectation(self) -> None:
        env = {k: v for k, v in os.environ.items() if k != "LC_EXPECT_NAPARI"}
        done = subprocess.run(
            [sys.executable, str(SANDBOX / "napari_check.py")], capture_output=True, text=True, env=env
        )
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("LC_EXPECT_NAPARI must be 'listed' or 'not_listed'", done.stderr)


class Workflow(unittest.TestCase):
    """The workflow file keeps the promises of the README (it is dispatch-only, so a typo would only show on a real run)."""

    text = (ROOT / ".github" / "workflows" / "release_sandbox.yml").read_text(encoding="utf-8")

    def test_the_expectation_comes_from_the_file_and_is_not_a_default_true(self) -> None:
        self.assertIn("expected_hosts.py env --app-name", self.text)
        self.assertIn("EXPECT_NAPARI", self.text)
        self.assertIn("inputs.hosts_napari != 'skip'", self.text)
        for name in ("hosts_napari", "hosts_fiji", "hosts_qupath"):
            block = re.search(r"\n      %s:\n((?:        .*\n)+)" % name, self.text)
            self.assertIsNotNone(block, name)
            assert block is not None
            self.assertIn("default: auto", block.group(1), name)
            self.assertNotIn("default: true", block.group(1), name)

    def test_fiji_and_qupath_run_for_any_app_and_a_missing_driver_is_red(self) -> None:
        self.assertNotIn(
            "runner.os == 'Linux' && env.EXTRAS == 'playground' && inputs.hosts_qupath", self.text
        )
        self.assertIn("CHECK fiji_listing_driver_present FAIL", self.text)
        self.assertIn("CHECK qupath_listing_body_present FAIL", self.text)
        self.assertIn('LC_EXPECT_LISTED="$EXPECT_FIJI"', self.text)
        self.assertIn('LC_EXPECT_LISTED="$EXPECT_QUPATH"', self.text)

    def test_an_app_without_tools_is_accepted_explicitly(self) -> None:
        self.assertIn("CHECK tools_module_absent_as_declared PASS", self.text)
        self.assertIn("tools_module is required", self.text)
        self.assertIn("HAS_TOOLS=false", self.text)
        self.assertEqual(
            self.text.count("env.HAS_TOOLS == 'true'"), 4, "cases, retention, playground extras, Windows W3"
        )


if __name__ == "__main__":
    unittest.main()
