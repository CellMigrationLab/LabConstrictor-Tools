"""tests/audit/notebooks/nb_common.py: where the click scripts are looked up (VL-1), notebook discovery, cell comparison, the worker environment.
Everything here is plain files: no installed app, no kernel, no network."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

import _paths  # noqa: F401  (must come first)
from _paths import ROOT

AUDIT = ROOT / "tests" / "audit"
sys.path.insert(0, str(AUDIT / "notebooks"))
import nb_common  # noqa: E402

SCRIPTS = AUDIT / "notebooks" / "scripts"


def notebook(path: Path, cells: list[tuple[str, object]]) -> None:
    document = {"cells": [{"cell_type": kind, "source": source} for kind, source in cells]}
    path.write_text(json.dumps(document), encoding="utf-8")


class ScriptPathTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def make(self, folder: str) -> Path:
        (self.root / folder).mkdir()
        target = self.root / folder / "nb.py"
        target.write_text("x = 1\n", encoding="utf-8")
        return target

    def test_a_script_under_the_registry_name_is_found(self) -> None:
        target = self.make("Plain")
        self.assertEqual(nb_common.script_path(self.root, "Plain", "nb"), target)

    def test_vl1_a_script_under_the_repository_folder_name_is_found(self) -> None:
        target = self.make("LabConstrictor-VLab4Mic")
        self.assertEqual(nb_common.script_path(self.root, "VLab4Mic", "nb"), target)

    def test_vl1_the_playground_registry_name_finds_its_repository_folder(self) -> None:
        target = self.make("LabConstrictor-Playground")
        self.assertEqual(nb_common.script_path(self.root, "LabConstrictorPlayground", "nb"), target)

    def test_the_registry_name_wins_when_both_folders_exist(self) -> None:
        wanted = self.make("VLab4Mic")
        self.make("LabConstrictor-VLab4Mic")
        self.assertEqual(nb_common.script_path(self.root, "VLab4Mic", "nb"), wanted)

    def test_a_missing_script_returns_the_registry_path_so_the_caller_can_name_it(self) -> None:
        self.assertEqual(nb_common.script_path(self.root, "Missing", "nb"), self.root / "Missing" / "nb.py")

    def test_every_committed_script_folder_is_reachable_by_the_registry_name(self) -> None:
        for app in (
            "CellTracksColab",
            "GuessTheCondition",
            "LabConstrictorPlayground",
            "NucleiSky",
            "VLab4Mic",
        ):
            for name in ("Welcome",):
                self.assertTrue(nb_common.script_path(SCRIPTS, app, name).is_file(), "%s/%s" % (app, name))
        self.assertTrue(nb_common.script_path(SCRIPTS, "VLab4Mic", "VLab4Mic_main").is_file())
        self.assertTrue(
            nb_common.script_path(SCRIPTS, "LabConstrictorPlayground", "LabConstrictorPlayground").is_file()
        )


class DiscoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def test_discover_lists_the_notebooks_of_extra_files(self) -> None:
        (self.root / "construct.yaml").write_text(
            "name: X\nextra_files:\n  - notebooks/A.ipynb: X/notebooks/A.ipynb\n  - README.md: X/README.md\n  - notebooks/B.ipynb: X/B.ipynb\n",
            encoding="utf-8",
        )
        found = nb_common.discover(self.root)
        self.assertEqual([n.name for n in found], ["A", "B"])
        self.assertEqual(found[0].installed_rel, "X/notebooks/A.ipynb")

    def test_a_construct_file_without_notebooks_is_an_error(self) -> None:
        (self.root / "construct.yaml").write_text(
            "name: X\nextra_files:\n  - README.md: X/README.md\n", encoding="utf-8"
        )
        with self.assertRaises(ValueError):
            nb_common.discover(self.root)

    def test_read_cells_accepts_both_ways_of_storing_source(self) -> None:
        path = self.root / "n.ipynb"
        notebook(path, [("code", ["a = 1\n", "b = 2"]), ("markdown", "# title")])
        self.assertEqual(nb_common.read_cells(path), [("code", "a = 1\nb = 2"), ("markdown", "# title")])


class ComparisonTests(unittest.TestCase):
    def test_equal_cells_have_no_difference(self) -> None:
        cells = [("code", "x"), ("markdown", "y")]
        self.assertIsNone(nb_common.first_difference(cells, list(cells)))

    def test_the_first_differing_cell_is_named(self) -> None:
        a = [("code", "x"), ("code", "same"), ("code", "z")]
        b = [("code", "x"), ("code", "other"), ("code", "z")]
        self.assertIn("cell 1 source differs", nb_common.first_difference(a, b) or "")
        self.assertIn(
            "cell 0 type differs", nb_common.first_difference([("code", "x")], [("markdown", "x")]) or ""
        )

    def test_a_missing_or_extra_cell_is_named(self) -> None:
        one, two = [("code", "x")], [("code", "x"), ("code", "y")]
        self.assertIn("cell 1 is missing in the installed", nb_common.first_difference(one, two) or "")
        self.assertIn("cell 1 exists only in the installed", nb_common.first_difference(two, one) or "")

    def test_ids_are_sanitised(self) -> None:
        self.assertEqual(nb_common.sanitise("Guess the-Condition.v2"), "Guess_the_Condition_v2")
        self.assertEqual(nb_common.check_id("App-1", "Nb 2", "runs"), "nb_App_1_Nb_2_runs")


class WorkerEnvironmentTests(unittest.TestCase):
    def test_home_is_a_scratch_folder_pip_has_no_index_and_pythonpath_is_dropped(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            home, prefix = Path(raw) / "home", Path(raw) / "prefix"
            home.mkdir()
            env = nb_common.worker_env(
                prefix, home, "/lc", base={"PYTHONPATH": "/leak", "PATH": "/usr/bin", "HOME": "/real"}
            )
            self.assertEqual(env["HOME"], str(home))
            self.assertEqual(env["PIP_NO_INDEX"], "1")
            self.assertEqual(env["LC_HOME"], "/lc")
            self.assertNotIn("PYTHONPATH", env)
            self.assertTrue(env["PATH"].startswith(str(prefix / "bin")))
            self.assertEqual(env["JUPYTER_PATH"], str(prefix / "share" / "jupyter"))
            self.assertTrue((home / "tmp").is_dir())


if __name__ == "__main__":
    unittest.main()
