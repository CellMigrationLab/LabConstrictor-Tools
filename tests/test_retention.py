"""Retention (docs/SPEC_WRONG_SCIENCE.md section 3): `labconstrictor_tools.retention` and the CLI command `prune`.

Fixtures RET-01 .. RET-09, RET-12, RET-13 of section 3.7, plus the unsafe paths, the markers, the dry run, the report and the
two places that create owned folders (`run` and the run records). Every survivor is checked by the contents of a sentinel file,
not only by count. Everything runs in a private LC_HOME made by the test; nothing touches a real one.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING
from unittest import mock

import _paths  # noqa: F401  (must come first)
from _paths import ROOT

from labconstrictor_tools import cli, log, retention, runs

if TYPE_CHECKING:
    from typing import Any

BASE = datetime(2026, 10, 1, 8, 0, 0, tzinfo=timezone.utc)


def stamp(index: int) -> str:
    """`created` values that increase with `index`."""
    return (BASE + timedelta(seconds=index, milliseconds=7)).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def result_name(index: int) -> str:
    return "%s_%06x_app_tool" % ((BASE + timedelta(seconds=index)).strftime("%Y%m%dT%H%M%S"), index)


def run_name(index: int) -> str:
    return "%s_app_tool" % (BASE + timedelta(seconds=index)).strftime("%Y%m%dT%H%M%S%f")


def sentinel(name: str) -> bytes:
    return ("keep %s" % name).encode()


class Home(unittest.TestCase):
    """A temporary LC_HOME with helpers that build the folders of the fixtures."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="lc_retention_")
        self.addCleanup(self._tmp.cleanup)
        self.home = Path(self._tmp.name) / "home"
        self.results = self.home / "results"
        self.runs = self.home / "runs"
        self.results.mkdir(parents=True)
        self.runs.mkdir()
        self.outside = Path(self._tmp.name) / "outside"
        self.outside.mkdir()

    def owned(
        self,
        root: Path,
        name: str,
        index: int,
        *,
        done: bool = True,
        kind: str | None = None,
        marker_name: str | None = None,
        **extra: "Any",
    ) -> Path:
        """A folder with a valid owner marker (and a done marker) and a sentinel file."""
        folder = root / name
        folder.mkdir()
        (folder / "data.txt").write_bytes(sentinel(name))
        marker = {
            "lc_marker": 1,
            "kind": kind or ("result" if root.name == "results" else "run"),
            "name": marker_name or name,
            "host": "cli",
            "pid": 1234,
            "created": stamp(index),
            "token": "00000000-0000-4000-8000-%012d" % index,
        }
        marker.update(extra)
        (folder / ".lc-owner.json").write_text(json.dumps({k: v for k, v in marker.items() if v is not None}))
        if done:
            (folder / ".lc-done.json").write_text(json.dumps({"finished": stamp(index + 1), "status": "ok"}))
        return folder

    def done_results(self, count: int, first: int = 0) -> list[str]:
        return [self.owned(self.results, result_name(i), i).name for i in range(first, first + count)]

    def done_runs(self, count: int, first: int = 0) -> list[str]:
        return [self.owned(self.runs, run_name(i), i).name for i in range(first, first + count)]

    def foreign(self, root: Path, name: str) -> Path:
        folder = root / name
        folder.mkdir()
        (folder / "x.txt").write_text("keep")
        return folder

    def names(self, root: Path, *, owned_only: bool = False) -> list[str]:
        found = sorted(p.name for p in root.iterdir())
        return [n for n in found if (root / n / ".lc-owner.json").exists()] if owned_only else found

    def assert_intact(self, folder: Path, text: str = "keep", name: str = "x.txt") -> None:
        self.assertEqual((folder / name).read_text(), text, "%s lost its contents" % folder)

    def env(self) -> dict[str, str]:
        return {**os.environ, "LC_HOME": str(self.home), "PYTHONPATH": str(ROOT)}

    def cli_prune(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "labconstrictor_tools", "prune", *args],
            env=self.env(), capture_output=True, text=True, timeout=120,
        )  # fmt: skip


class Eligibility(Home):
    def test_RET_01_a_foreign_folder_survives_and_the_newest_20_owned_remain(self) -> None:
        foreign = self.foreign(self.results, "20261008T120000_reanalysis_backup")
        made = self.done_results(300)
        report = retention.prune("results", home=self.home)
        self.assert_intact(foreign)
        self.assertEqual(self.names(self.results, owned_only=True), sorted(made[-20:]))
        for name in made[-20:]:
            self.assertEqual((self.results / name / "data.txt").read_bytes(), sentinel(name))
        self.assertEqual(len(report.roots[0].deleted), 280)
        self.assertEqual(len(report.roots[0].kept), 20)

    def test_RET_01_through_the_cli_and_the_default_root_is_both(self) -> None:
        foreign = self.foreign(self.results, "20261008T120000_reanalysis_backup")
        self.done_results(30)
        kept_runs = self.done_runs(60)
        done = self.cli_prune()
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assert_intact(foreign)
        self.assertEqual(len(self.names(self.results, owned_only=True)), 20)
        self.assertEqual(self.names(self.runs), sorted(kept_runs[-50:]))

    def test_RET_02_runs_keep_50_and_a_foreign_run_folder_survives(self) -> None:
        foreign = self.foreign(self.runs, "0000_keep_this_analysis")
        self.done_runs(120)
        done = self.cli_prune("--root", "runs")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assert_intact(foreign)
        self.assertEqual(len(self.names(self.runs, owned_only=True)), 50)

    def test_the_other_root_is_not_touched_by_root_results(self) -> None:
        self.done_runs(60)
        self.done_results(30)
        self.cli_prune("--root", "results")
        self.assertEqual(len(self.names(self.runs)), 60)
        self.assertEqual(len(self.names(self.results)), 20)

    def test_RET_03_folders_without_a_done_file_are_never_removed(self) -> None:
        crashed = [self.owned(self.results, result_name(i), i, done=False).name for i in range(25)]
        retention.prune("results", home=self.home)
        self.assertEqual(self.names(self.results), sorted(crashed))
        for name in crashed:
            self.assertEqual((self.results / name / "data.txt").read_bytes(), sentinel(name))

    def test_RET_04_thirty_finished_folders_keep_the_latest_20_by_created(self) -> None:
        made = self.done_results(30)
        retention.prune("results", home=self.home)
        self.assertEqual(self.names(self.results), sorted(made[10:]))

    def test_RET_06_a_copied_and_renamed_folder_is_foreign(self) -> None:
        copy = self.owned(self.results, "20261008T120000_000000_app_copy", -5, marker_name=result_name(0))
        self.done_results(30)
        retention.prune("results", home=self.home)
        self.assertEqual((copy / "data.txt").read_bytes(), sentinel(copy.name))

    def test_RET_07_legacy_folders_without_a_marker_are_never_removed(self) -> None:
        legacy = []
        for i in range(30):
            folder = self.results / ("2026010%dT0000%02d_abcdef_app_tool" % (i % 9 + 1, i))
            folder.mkdir()
            (folder / "data.txt").write_bytes(sentinel(folder.name))
            if i % 2:  # a done marker alone is not ownership either
                (folder / ".lc-done.json").write_text(json.dumps({"finished": stamp(0), "status": "ok"}))
            legacy.append(folder.name)
        self.done_results(25, first=100)
        retention.prune("results", home=self.home)
        for name in legacy:
            self.assertEqual((self.results / name / "data.txt").read_bytes(), sentinel(name))
        self.assertEqual(len(self.names(self.results, owned_only=True)), 20)

    def test_RET_12_a_crashed_owned_folder_survives_next_to_30_finished(self) -> None:
        crashed = self.owned(self.results, result_name(0), 0, done=False)
        self.done_results(30, first=1)
        retention.prune("results", home=self.home)
        self.assertEqual((crashed / "data.txt").read_bytes(), sentinel(crashed.name))
        self.assertEqual(len(self.names(self.results, owned_only=True)), 21)

    def test_RET_13_equal_created_values_are_ordered_by_name(self) -> None:
        names = [
            "20261001T080000_aaaaaa_app_tool",
            "20261001T080000_bbbbbb_app_tool",
            "20261001T080000_cccccc_app_tool",
        ]
        for name in reversed(names):
            self.owned(self.results, name, 5)  # the same `created` for all three
        retention.prune("results", home=self.home, keep={"results": 2})
        self.assertEqual(self.names(self.results), names[1:])
        again = retention.prune("results", home=self.home, keep={"results": 2})
        self.assertEqual(again.roots[0].deleted, [])

    def test_the_order_is_by_created_in_the_marker_not_by_the_folder_name(self) -> None:
        newest_by_marker = self.owned(
            self.results, "0000_zzz", 100
        )  # sorts first by name, is the newest by `created`
        old = [self.owned(self.results, result_name(i), i).name for i in range(3)]
        retention.prune("results", home=self.home, keep={"results": 2})
        self.assertEqual(self.names(self.results), sorted([newest_by_marker.name, old[2]]))

    def test_the_quota_counts_only_eligible_folders(self) -> None:
        for i in range(
            30
        ):  # foreign, crashed and legacy folders do not use it up, and none is evicted to make room
            self.foreign(self.results, "foreign_%d" % i)
        self.owned(self.results, result_name(0), 0, done=False)
        made = self.done_results(22, first=1)
        retention.prune("results", home=self.home)
        self.assertEqual(self.names(self.results, owned_only=True), sorted(made[2:] + [result_name(0)]))
        self.assertEqual(len([n for n in self.names(self.results) if n.startswith("foreign_")]), 30)


class UnsafePaths(Home):
    def link(self, target: Path, where: Path) -> str:
        """Make a symlink, and on Windows a junction too; returns what was made. Skips when no link can be made."""
        try:
            os.symlink(target, where, target_is_directory=True)
            return "symlink"
        except (OSError, NotImplementedError):
            if os.name == "nt":
                made = subprocess.run(
                    ["cmd", "/c", "mklink", "/J", str(where), str(target)], capture_output=True
                )
                if made.returncode == 0:
                    return "junction"
            self.skipTest(
                "unsupported: this system cannot create a link here (reported as unsupported, never as a pass)"
            )
            return ""

    def test_RET_05_a_symlink_to_an_owned_looking_folder_outside_is_left_alone(self) -> None:
        self.outside.joinpath("data.txt").write_bytes(b"outside")
        for marker, content in (
            (
                ".lc-owner.json",
                json.dumps(
                    {
                        "lc_marker": 1,
                        "kind": "result",
                        "name": result_name(0),
                        "created": stamp(0),
                        "token": "0" * 8 + "-aaaa",
                    }
                ),
            ),
            (".lc-done.json", json.dumps({"finished": stamp(1), "status": "ok"})),
        ):
            (self.outside / marker).write_text(content)
        made = self.done_results(40, first=1)
        self.link(self.outside, self.results / result_name(0))
        retention.prune("results", home=self.home)
        self.assertTrue((self.results / result_name(0)).is_symlink())
        self.assertEqual(
            sorted(p.name for p in self.outside.iterdir()), [".lc-done.json", ".lc-owner.json", "data.txt"]
        )
        self.assertEqual((self.outside / "data.txt").read_bytes(), b"outside")
        real = sorted(p.name for p in self.results.iterdir() if not p.is_symlink())
        self.assertEqual(real, sorted(made[-20:]))
        for name in made[-20:]:
            self.assertEqual((self.results / name / "data.txt").read_bytes(), sentinel(name))

    def test_a_link_inside_a_removed_folder_is_removed_as_a_link_and_its_target_survives(self) -> None:
        victim = self.owned(self.results, result_name(0), 0)
        (self.outside / "precious.txt").write_text("precious")
        self.link(self.outside, victim / "inner_link")
        self.done_results(20, first=1)
        report = retention.prune("results", home=self.home)
        self.assertEqual(report.roots[0].deleted, [result_name(0)])
        self.assertFalse(victim.exists())
        self.assertEqual((self.outside / "precious.txt").read_text(), "precious")

    def test_a_symlinked_owner_marker_does_not_make_a_folder_eligible(self) -> None:
        elsewhere = self.outside / "marker.json"
        elsewhere.write_text(
            json.dumps(
                {
                    "lc_marker": 1,
                    "kind": "result",
                    "name": "linked",
                    "created": stamp(0),
                    "token": "0" * 8 + "-bbbb",
                }
            )
        )
        folder = self.foreign(self.results, "linked")
        try:
            os.symlink(elsewhere, folder / ".lc-owner.json")
        except (OSError, NotImplementedError):
            self.skipTest("unsupported: no symlinks here")
        (folder / ".lc-done.json").write_text(json.dumps({"finished": stamp(1), "status": "ok"}))
        self.done_results(25)
        retention.prune("results", home=self.home)
        self.assert_intact(folder)

    def test_a_file_in_the_root_is_left_alone(self) -> None:
        (self.results / "notes.txt").write_text("keep")
        self.done_results(25)
        retention.prune("results", home=self.home)
        self.assertEqual((self.results / "notes.txt").read_text(), "keep")

    def test_a_name_outside_the_allowed_characters_is_left_alone_even_with_valid_markers(self) -> None:
        odd = self.owned(self.results, "my results (final)", 0)
        self.done_results(25, first=1)
        report = retention.prune("results", home=self.home)
        self.assert_intact(odd, sentinel(odd.name).decode(), "data.txt")
        self.assertIn(
            ("my results (final)", "the name has characters outside A-Za-z0-9_.-"), report.roots[0].skipped
        )

    def test_a_marker_of_the_wrong_kind_or_version_or_without_time_or_token_is_not_ownership(self) -> None:
        cases = {
            "wrongkind": {"kind": "run"},
            "version2": {"lc_marker": 2},
            "booleanversion": {"lc_marker": True},
            "notime": {"created": None},
            "badtime": {"created": "yesterday"},
            "notoken": {"token": None},
            "unsafetoken": {"token": "../../x"},
        }
        for i, (name, change) in enumerate(cases.items()):
            self.owned(self.results, name, i, **change)
        self.done_results(25, first=10)
        retention.prune("results", home=self.home)
        for name in cases:
            self.assertEqual((self.results / name / "data.txt").read_bytes(), sentinel(name), name)

    def test_broken_markers_are_not_ownership(self) -> None:
        for name, owner in {
            "emptyfile": "",
            "binary": b"\xff\xfe",
            "alist": "[1]",
            "huge": " " * (retention.MAX_MARKER_BYTES + 1),
        }.items():
            folder = self.foreign(self.results, name)
            mode = "wb" if isinstance(owner, bytes) else "w"
            with open(folder / ".lc-owner.json", mode) as handle:
                handle.write(owner)
            (folder / ".lc-done.json").write_text("{}")
        self.done_results(25)
        retention.prune("results", home=self.home)
        for name in ("emptyfile", "binary", "alist", "huge"):
            self.assert_intact(self.results / name)

    def test_a_done_file_that_is_not_a_done_marker_keeps_the_folder(self) -> None:
        for i, content in enumerate(["", "{}", '{"status": "maybe"}', "[]"]):
            folder = self.owned(self.results, "d%d" % i, i, done=False)
            (folder / ".lc-done.json").write_text(content)
        self.done_results(25, first=10)
        retention.prune("results", home=self.home)
        for i in range(4):
            self.assertTrue((self.results / ("d%d" % i)).is_dir())

    def test_a_root_that_does_not_exist_is_reported_and_nothing_is_created(self) -> None:
        empty = Path(self._tmp.name) / "emptyhome"
        empty.mkdir()
        report = retention.prune(home=empty)
        self.assertEqual([r.exists for r in report.roots], [False, False])
        self.assertEqual(list(empty.iterdir()), [])
        missing = Path(self._tmp.name) / "no_such_home"
        retention.prune(home=missing)
        self.assertFalse(missing.exists())
        self.assertIn("does not exist", report.text())

    def test_only_the_two_roots_can_be_named(self) -> None:
        with self.assertRaises(ValueError):
            retention.prune("state", home=self.home)
        refused = self.cli_prune("--root", "state")
        self.assertEqual(refused.returncode, 2)

    def test_state_logs_and_other_folders_in_the_home_are_never_touched(self) -> None:
        for name in ("state", "logs", "apps", "out"):
            (self.home / name).mkdir()
            self.owned(self.home / name, result_name(0), 0)
        self.done_results(25)
        retention.prune(home=self.home)
        for name in ("state", "logs", "apps", "out"):
            self.assertTrue((self.home / name / result_name(0)).is_dir())

    @unittest.skipUnless(os.name == "nt", "read-only files and junctions are Windows behaviours")
    def test_windows_removes_read_only_files_and_junctions_inside_without_following_them(self) -> None:
        victim = self.owned(self.results, result_name(0), 0)
        os.chmod(victim / "data.txt", 0o444)
        (self.outside / "precious.txt").write_text("precious")
        made = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(victim / "junction"), str(self.outside)], capture_output=True
        )
        if made.returncode != 0:
            self.skipTest("unsupported: cannot create a junction here")
        self.done_results(20, first=1)
        report = retention.prune("results", home=self.home)
        self.assertEqual(report.roots[0].deleted, [result_name(0)], report.text())
        self.assertEqual((self.outside / "precious.txt").read_text(), "precious")

    @unittest.skipUnless(os.name == "nt", "junctions are Windows reparse points")
    def test_windows_a_junction_in_the_root_is_left_alone(self) -> None:
        self.outside.joinpath("data.txt").write_text("outside")
        for marker, content in (
            (
                ".lc-owner.json",
                json.dumps(
                    {
                        "lc_marker": 1,
                        "kind": "result",
                        "name": result_name(0),
                        "created": stamp(0),
                        "token": "0" * 8 + "-cccc",
                    }
                ),
            ),
            (".lc-done.json", json.dumps({"finished": stamp(1), "status": "ok"})),
        ):
            (self.outside / marker).write_text(content)
        made = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(self.results / result_name(0)), str(self.outside)],
            capture_output=True,
        )
        if made.returncode != 0:
            self.skipTest("unsupported: cannot create a junction here")
        self.done_results(40, first=1)
        retention.prune("results", home=self.home)
        self.assertEqual((self.outside / "data.txt").read_text(), "outside")


class FeatureClaim(unittest.TestCase):
    """`retention_prune` is listed in `features` exactly because the command and the module exist (docs/PROTOCOL.md)."""

    def test_the_feature_is_claimed_and_the_command_and_the_module_exist(self) -> None:
        from labconstrictor_tools import __main__ as entry
        from labconstrictor_tools import features

        self.assertIn("retention_prune", features.FEATURES)
        parsed = entry.build_parser().parse_args(["prune", "--root", "runs", "--dry-run"])
        self.assertEqual((parsed.command, parsed.root, parsed.dry_run), ("prune", "runs", True))
        for name in ("prune", "write_owner", "write_done", "RESULTS_KEPT", "RUN_RECORDS_KEPT"):
            self.assertTrue(hasattr(retention, name), name)

    def test_the_policy_numbers_are_the_documented_ones(self) -> None:
        self.assertEqual((retention.RESULTS_KEPT, retention.RUN_RECORDS_KEPT), (20, 50))
        text = (ROOT / "docs" / "SPEC_WRONG_SCIENCE.md").read_text(encoding="utf-8")
        self.assertIn("`RESULTS_KEPT = 20`, `RUN_RECORDS_KEPT = 50`", text)

    def test_the_protocol_page_lists_the_feature_as_implemented(self) -> None:
        row = next(
            line
            for line in (ROOT / "docs" / "PROTOCOL.md").read_text(encoding="utf-8").splitlines()
            if line.startswith("| `retention_prune`")
        )
        self.assertNotIn("planned", row)


class Deleting(Home):
    def test_a_removal_goes_through_a_deleting_folder_and_a_leftover_is_finished_next_time(self) -> None:
        victim = self.owned(self.results, result_name(0), 0)
        self.done_results(20, first=1)
        token = json.loads((victim / ".lc-owner.json").read_text())["token"]
        victim.rename(
            self.results / (retention.DELETING_PREFIX + token)
        )  # what an interrupted prune leaves behind
        report = retention.prune("results", home=self.home)
        self.assertEqual(report.roots[0].deleted, [retention.DELETING_PREFIX + token])
        self.assertEqual(len(self.names(self.results)), 20)

    def test_a_deleting_folder_that_is_not_ours_is_left_alone(self) -> None:
        lookalike = self.foreign(self.results, ".lc-deleting-0000000000000000")
        wrong_token = self.owned(self.results, ".lc-deleting-ffffffffffff", 5)
        report = retention.prune("results", home=self.home)
        self.assert_intact(lookalike)
        self.assertEqual((wrong_token / "data.txt").read_bytes(), sentinel(wrong_token.name))
        self.assertEqual(report.roots[0].deleted, [])

    def test_the_rename_happens_before_any_file_is_removed(self) -> None:
        self.done_results(21)
        seen = []
        real = retention._remove_tree

        def spy(path: Path) -> "Any":
            seen.append((path.name, sorted(p.name for p in path.iterdir())))
            return real(path)

        with mock.patch.object(retention, "_remove_tree", side_effect=spy):
            retention.prune("results", home=self.home)
        ((name, content),) = seen
        self.assertTrue(name.startswith(retention.DELETING_PREFIX), name)
        self.assertIn(".lc-owner.json", content)  # still whole when the removal starts

    def test_a_folder_swapped_for_a_link_after_the_plan_is_not_followed(self) -> None:
        made = self.done_results(21)
        (self.outside / "precious.txt").write_text("precious")
        real = retention._delete

        def swap_then_delete(entry: "Any", root: "Any", kind: "Any") -> None:
            if entry.name == made[0]:
                for child in (self.results / made[0]).iterdir():
                    child.unlink()
                (self.results / made[0]).rmdir()
                try:
                    os.symlink(self.outside, self.results / made[0], target_is_directory=True)
                except (OSError, NotImplementedError):
                    self.skipTest("unsupported: no symlinks here")
            return real(entry, root, kind)

        with mock.patch.object(retention, "_delete", side_effect=swap_then_delete):
            report = retention.prune("results", home=self.home)
        self.assertEqual((self.outside / "precious.txt").read_text(), "precious")
        self.assertEqual([name for name, _ in report.roots[0].failed], [made[0]])
        self.assertTrue(
            (self.results / made[0]).is_symlink(), "the swapped-in link must stay where it was, not be moved"
        )
        self.assertFalse(report.ok)

    @unittest.skipIf(
        os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0),
        "needs POSIX permissions and a non-root user",
    )
    def test_a_folder_that_cannot_be_removed_is_reported_and_the_others_still_go(self) -> None:
        made = self.done_results(23)
        locked = self.results / made[0]
        os.chmod(locked, 0o500)  # cannot unlink inside
        try:
            report = retention.prune("results", home=self.home)
        finally:
            for stuck in self.results.glob(retention.DELETING_PREFIX + "*"):
                os.chmod(stuck, 0o700)
        self.assertEqual([n for n, _ in report.roots[0].failed], [made[0]])
        self.assertEqual(len(report.roots[0].deleted), 2)
        self.assertFalse(report.ok)
        leftovers = [n for n in self.names(self.results) if n.startswith(retention.DELETING_PREFIX)]
        self.assertEqual(len(leftovers), 1)  # renamed, then stuck: the next prune retries it
        os.chmod(self.results / leftovers[0], 0o500)
        try:
            self.assertEqual(self.cli_prune().returncode, 1)
        finally:
            os.chmod(self.results / leftovers[0], 0o700)
        self.assertEqual(self.cli_prune().returncode, 0)
        self.assertEqual(len(self.names(self.results)), 20)


class Lock(Home):
    HOLDER = (
        "import sys, pathlib\n"
        "from labconstrictor_tools import retention\n"
        "with retention._retention_lock(pathlib.Path(sys.argv[1])) as held:\n"
        "    print('held' if held else 'no', flush=True)\n"
        "    sys.stdin.readline()\n"
    )

    def hold(self) -> subprocess.Popen:
        holder = subprocess.Popen(
            [sys.executable, "-c", self.HOLDER, str(self.home)],
            env=self.env(), stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
        )  # fmt: skip
        self.addCleanup(holder.wait, 30)
        self.addCleanup(holder.stdin.close)
        self.addCleanup(holder.stdout.close)
        self.assertEqual(holder.stdout.readline().strip(), "held")
        return holder

    def test_RET_09_a_lock_held_by_another_process_means_exit_0_and_nothing_deleted(self) -> None:
        made = self.done_results(30)
        holder = self.hold()
        report = retention.prune("results", home=self.home)
        self.assertTrue(report.locked_out)
        done = self.cli_prune()
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("another prune is running", done.stdout)
        self.assertEqual(self.names(self.results), sorted(made))
        holder.stdin.write("\n")
        holder.stdin.flush()
        holder.wait(30)
        retention.prune("results", home=self.home)  # the lock is free again
        self.assertEqual(len(self.names(self.results)), 20)

    def test_a_dry_run_does_not_need_the_lock_and_does_not_create_it(self) -> None:
        self.done_results(30)
        self.hold()
        report = retention.prune("results", home=self.home, dry_run=True)
        self.assertFalse(report.locked_out)
        self.assertEqual(len(report.roots[0].deleted), 10)

    def test_a_file_system_without_locks_means_nothing_is_deleted(self) -> None:
        made = self.done_results(30)
        with mock.patch.object(retention, "_try_lock", return_value=False):
            report = retention.prune("results", home=self.home)
        self.assertTrue(report.locked_out)
        self.assertEqual(self.names(self.results), sorted(made))

    def test_a_lock_file_that_cannot_be_opened_means_nothing_is_deleted_and_no_exception(self) -> None:
        made = self.done_results(30)
        (self.home / retention.LOCK_FILE).mkdir()  # a folder where the lock file should be
        report = retention.prune("results", home=self.home)
        self.assertTrue(report.locked_out)
        self.assertEqual(self.names(self.results), sorted(made))

    def test_RET_08_four_prunes_at_once_leave_exactly_20_and_every_process_exits_0(self) -> None:
        foreign = self.foreign(self.results, "20261008T120000_reanalysis_backup")
        self.done_results(100)
        processes = [
            subprocess.Popen(
                [sys.executable, "-m", "labconstrictor_tools", "prune", "--root", "results"],
                env=self.env(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )  # fmt: skip
            for _ in range(4)
        ]
        outputs = [p.communicate(timeout=120) for p in processes]
        self.assertEqual([p.returncode for p in processes], [0, 0, 0, 0], outputs)
        self.assert_intact(foreign)
        self.assertEqual(len(self.names(self.results, owned_only=True)), 20)
        self.assertEqual(
            len(self.names(self.results)), 21
        )  # 20 owned + the foreign one, no .lc-deleting leftovers


class DryRunAndReport(Home):
    def test_a_dry_run_changes_nothing_and_names_exactly_what_a_real_run_removes(self) -> None:
        self.foreign(self.results, "mine")
        self.owned(self.results, result_name(500), 500, done=False)
        made = self.done_results(25)
        before = sorted(p.relative_to(self.home).as_posix() for p in self.home.rglob("*"))
        dry = retention.prune("results", home=self.home, dry_run=True)
        self.assertEqual(sorted(p.relative_to(self.home).as_posix() for p in self.home.rglob("*")), before)
        real = retention.prune("results", home=self.home)
        self.assertEqual(dry.roots[0].deleted, real.roots[0].deleted)
        self.assertEqual(dry.roots[0].deleted, made[:5])
        self.assertEqual(dry.roots[0].kept, real.roots[0].kept)

    def test_the_cli_dry_run_says_so_and_removes_nothing(self) -> None:
        self.done_results(25)
        done = self.cli_prune("--dry-run")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("dry run: nothing is changed", done.stdout)
        self.assertIn("would remove", done.stdout)
        self.assertEqual(len(self.names(self.results)), 25)

    def test_the_report_names_the_policy_the_removed_and_the_left_alone(self) -> None:
        self.foreign(self.results, "20261008T120000_reanalysis_backup")
        self.owned(self.results, result_name(500), 500, done=False)
        made = self.done_results(21)
        text = retention.prune("results", home=self.home).text()
        self.assertIn("keep the newest 20", text)
        self.assertIn("removed %s" % made[0], text)
        self.assertIn("left alone", text)
        self.assertIn("20261008T120000_reanalysis_backup: no .lc-owner.json", text)
        self.assertIn("%s: no .lc-done.json" % result_name(500), text)

    def test_the_json_report_is_data(self) -> None:
        self.done_results(21)
        done = self.cli_prune("--json", "--root", "results")
        data = json.loads(done.stdout)
        self.assertEqual(data["roots"][0]["keep"], 20)
        self.assertEqual(len(data["roots"][0]["deleted"]), 1)
        self.assertEqual(len(data["roots"][0]["kept"]), 20)

    def test_a_long_list_of_left_alone_folders_is_cut_in_the_text_but_not_in_the_json(self) -> None:
        for i in range(retention.LISTED_SKIPS + 5):
            self.foreign(self.results, "f%03d" % i)
        report = retention.prune("results", home=self.home)
        self.assertIn("and 5 more", report.text())
        self.assertEqual(len(report.as_dict()["roots"][0]["skipped"]), retention.LISTED_SKIPS + 5)


class Writers(Home):
    def test_the_owner_marker_is_valid_and_the_folder_is_not_yet_eligible(self) -> None:
        folder = self.results / result_name(0)
        folder.mkdir()
        retention.write_owner(folder, "result", "cli")
        marker = json.loads((folder / ".lc-owner.json").read_text())
        self.assertEqual(marker["lc_marker"], 1)
        self.assertEqual((marker["kind"], marker["name"], marker["host"]), ("result", folder.name, "cli"))
        self.assertEqual(marker["pid"], os.getpid())
        self.assertRegex(marker["created"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$")
        self.assertRegex(marker["token"], r"^[0-9a-f-]{36}$")
        self.assertEqual(retention.prune("results", home=self.home, keep={"results": 0}).roots[0].deleted, [])

    def test_the_done_marker_is_written_atomically_with_a_valid_status(self) -> None:
        folder = self.owned(self.results, result_name(0), 0, done=False)
        retention.write_done(folder, "cancelled")
        done = json.loads((folder / ".lc-done.json").read_text())
        self.assertEqual(done["status"], "cancelled")
        self.assertRegex(done["finished"], r"Z$")
        self.assertEqual(
            sorted(p.name for p in folder.iterdir()), [".lc-done.json", ".lc-owner.json", "data.txt"]
        )  # no temporary left
        with self.assertRaises(ValueError):
            retention.write_done(folder, "great")
        self.assertEqual(
            retention.prune("results", home=self.home, keep={"results": 0}).roots[0].deleted, [folder.name]
        )

    def test_a_folder_that_held_nothing_is_discarded_and_one_with_files_is_not(self) -> None:
        empty = self.results / "empty"
        empty.mkdir()
        retention.write_owner(empty, "result", "cli")
        self.assertTrue(retention.discard_unused(empty))
        self.assertFalse(empty.exists())
        full = self.owned(self.results, "full", 1, done=False)
        self.assertFalse(retention.discard_unused(full))
        self.assertTrue(full.is_dir())
        self.assertTrue((full / ".lc-owner.json").is_file())  # nothing of it was taken apart


class CliCreatesOwnedFolders(Home):
    def setUp(self) -> None:
        super().setUp()
        patcher = mock.patch.dict(os.environ, {"LC_HOME": str(self.home)})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_a_results_folder_made_by_run_has_its_owner_marker_and_never_removes_anything(self) -> None:
        old = self.done_results(30)
        foreign = self.foreign(self.results, "20260101T000000_abcdef_mine")
        folder = cli._new_results_dir("my app", "tool")
        marker = json.loads((folder / ".lc-owner.json").read_text())
        self.assertEqual((marker["kind"], marker["name"], marker["host"]), ("result", folder.name, "cli"))
        self.assertEqual(
            self.names(self.results), sorted(old + [folder.name, foreign.name])
        )  # creating prunes nothing

    def test_finishing_a_run_marks_it_done_and_prunes_afterwards(self) -> None:
        old = self.done_results(25)
        folder = cli._new_results_dir("app", "tool")
        (folder / "result.csv").write_text("1")
        cli._finish_results_dir(str(folder), "ok")
        self.assertEqual(json.loads((folder / ".lc-done.json").read_text())["status"], "ok")
        self.assertEqual(len(self.names(self.results)), 20)
        self.assertTrue(folder.is_dir())
        self.assertEqual(self.names(self.results)[:-1] + [folder.name], sorted(old[-19:] + [folder.name]))

    def test_a_run_that_produced_nothing_leaves_no_folder_behind(self) -> None:
        folder = cli._new_results_dir("app", "tool")
        cli._finish_results_dir(str(folder), "failed")
        self.assertFalse(folder.exists())

    def test_a_successful_run_that_wrote_nothing_keeps_its_folder(self) -> None:
        folder = cli._new_results_dir("app", "tool")  # the run reports this path, so it has to exist
        cli._finish_results_dir(str(folder), "ok")
        self.assertEqual(json.loads((folder / ".lc-done.json").read_text())["status"], "ok")

    def test_a_failed_run_with_files_keeps_them_marked_failed(self) -> None:
        folder = cli._new_results_dir("app", "tool")
        (folder / "partial.csv").write_text("1")
        cli._finish_results_dir(str(folder), "failed")
        self.assertEqual(json.loads((folder / ".lc-done.json").read_text())["status"], "failed")

    def test_a_problem_while_finishing_is_logged_and_never_raised(self) -> None:
        folder = cli._new_results_dir("app", "tool")
        (folder / "r.csv").write_text("1")
        with (
            mock.patch.object(retention, "prune", side_effect=OSError("disk full")),
            mock.patch.object(log, "warning") as warned,
        ):
            cli._finish_results_dir(str(folder), "ok")  # must not raise
        shown = warned.call_args.args[0] % warned.call_args.args[1:]
        self.assertIn("could not finish the results folder", shown)
        self.assertIn("disk full", shown)
        self.assertTrue(
            (folder / ".lc-done.json").is_file()
        )  # the run was marked done before the prune failed

    def test_two_runs_in_the_same_second_get_different_marked_folders(self) -> None:
        with mock.patch.object(cli.time, "strftime", return_value="20240101T000000"):
            first = cli._new_results_dir("app", "tool")
            second = cli._new_results_dir("app", "tool")
        self.assertNotEqual(first, second)
        for folder in (first, second):
            self.assertEqual(json.loads((folder / ".lc-owner.json").read_text())["name"], folder.name)

    def test_a_run_record_has_markers_and_old_records_are_pruned_without_touching_foreign_ones(self) -> None:
        foreign = self.foreign(self.runs, "0000_keep_this_analysis")
        self.done_runs(55)
        import types

        task = types.SimpleNamespace(status="COMPLETE", error=None, code=None, traceback=None, outputs={})
        folder = runs.record("app", "tool", {}, task, 1.0)
        self.assertEqual(json.loads((folder / ".lc-done.json").read_text())["status"], "ok")
        self.assertEqual(json.loads((folder / ".lc-owner.json").read_text())["kind"], "run")
        self.assertEqual(len(self.names(self.runs, owned_only=True)), retention.RUN_RECORDS_KEPT)
        self.assert_intact(foreign)

    def test_a_cancelled_or_crashed_run_record_says_so(self) -> None:
        import types

        for status, expected in (("CANCELED", "cancelled"), ("CRASHED", "failed"), ("FAILED", "failed")):
            task = types.SimpleNamespace(status=status, error="x", code="c", traceback=None, outputs={})
            folder = runs.record("app", "tool", {}, task, 1.0)
            self.assertEqual(json.loads((folder / ".lc-done.json").read_text())["status"], expected, status)


class RealRun(Home):
    """`labconstrictor-tools run` end to end: the folder it makes is owned and finished, and a run that produced nothing leaves none."""

    def run_tool(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "labconstrictor_tools", "run", "synthetic", *args],
            env={**self.env(), "PYTHONUTF8": "1"}, capture_output=True, text=True, encoding="utf-8", timeout=300,
        )  # fmt: skip

    def test_a_real_run_leaves_an_owned_finished_folder_and_a_record(self) -> None:
        import numpy as np
        import tifffile

        _paths.register_synthetic(self.home)
        image = self.home / "in.tif"
        tifffile.imwrite(image, np.zeros((4, 4), dtype=np.uint16))
        done = self.run_tool("kitchen_sink", "required_string=x", "image=%s" % image)
        self.assertEqual(done.returncode, 0, done.stderr)
        (folder,) = list(self.results.iterdir())
        self.assertEqual(json.loads((folder / ".lc-owner.json").read_text())["name"], folder.name)
        self.assertEqual(json.loads((folder / ".lc-done.json").read_text())["status"], "ok")
        self.assertTrue((folder / "doubled.tif").is_file())
        (record,) = list(self.runs.iterdir())
        self.assertEqual(json.loads((record / ".lc-done.json").read_text())["status"], "ok")

    def test_a_failed_run_that_wrote_nothing_leaves_no_results_folder_but_a_failed_record(self) -> None:
        _paths.register_synthetic(self.home)
        done = self.run_tool("explode", "kind=tool_error")
        self.assertEqual(done.returncode, 1, done.stderr)
        self.assertEqual(list(self.results.iterdir()), [])
        (record,) = list(self.runs.iterdir())
        self.assertEqual(json.loads((record / ".lc-done.json").read_text())["status"], "failed")


if __name__ == "__main__":
    unittest.main()
