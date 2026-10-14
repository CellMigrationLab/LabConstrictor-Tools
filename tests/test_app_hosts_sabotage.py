"""Does `test_app_hosts` have teeth? Same method as test_sabotage.py: copy the package and the tests to a temporary tree, apply
ONE deliberate break to the host-discovery rule, run test_app_hosts there and require it to go red (by an assertion, not by
an error that would also appear for a typo). A break that survives is named: a case is missing."""

import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import _paths  # noqa: F401  (must come first)
from _paths import ROOT
from test_sabotage import Break, apply, build_tree, run_slice, unittest_slice

GUARD = unittest_slice("test_app_hosts")

BREAKS = [
    Break("listed_for: an excluded host is listed", "app_hosts.py", "    if host in declared:", "    if True:", GUARD),
    Break("listed_for: an absent field is refused", "app_hosts.py", "return True, ABSENT.format(app=app)", "return False, ABSENT.format(app=app)", GUARD),
    Break("listed_for: an absent field is listed silently", "app_hosts.py", "return True, ABSENT.format(app=app)", 'return True, ""', GUARD),
    Break("listed_for: the unknown asking host is answered, not refused", "app_hosts.py", "    if host not in HOSTS:\n        raise", "    if False:\n        raise", GUARD),
    Break("parse_declared: an empty list is accepted", "app_hosts.py", "    if not value:\n        raise ValueError(EMPTY)", "    if False:\n        raise ValueError(EMPTY)", GUARD),
    Break("parse_declared: an unknown name is accepted", "app_hosts.py", "        if name not in HOSTS:", "        if False:", GUARD),
    Break("parse_declared: a text instead of a list is accepted", "app_hosts.py", "    if not isinstance(value, list):", "    if not isinstance(value, (list, str)):", GUARD),
    Break("parse_declared: a repeated name is accepted", "app_hosts.py", "        if value.count(name) > 1:", "        if value.count(name) > 99:", GUARD),
    Break("hosts_in_manifest: the key inside a text block is read", "app_hosts.py", '_TOP_KEY = re.compile(r"""^(?:hosts', '_TOP_KEY = re.compile(r"""^\\s*(?:hosts', GUARD),
    Break("hosts_in_manifest: a quoted key is not read", "app_hosts.py", '(?:hosts|"hosts"|\'hosts\')[ \\t]*:', '(?:hosts)[ \\t]*:', GUARD),
    Break("hosts_in_manifest: a second hosts key is ignored", "app_hosts.py", "    if len(found) > 1:", "    if len(found) > 99:", GUARD),
    Break("hosts_in_manifest: a comment after the value is kept", "app_hosts.py", "    return re.split(r\"[ \\t]#\", text, maxsplit=1)[0].strip()", "    return text.strip()", GUARD),
    Break("hosts_in_manifest: an unindented block item is not read", "app_hosts.py", '_BLOCK_ITEM = re.compile(r"^[ \\t]*-', '_BLOCK_ITEM = re.compile(r"^[ \\t]+-', GUARD),
    Break("hosts_in_manifest: an empty item is not named", "app_hosts.py", '    if "" in names:', "    if False:", GUARD),
    Break("from_arguments: the byte order mark is not dropped", "app_hosts.py", 'encoding="utf-8-sig"', 'encoding="utf-8"', GUARD),
    Break("register: an absent declaration is not logged", "registry.py", "        log.warning(app_hosts.ABSENT.format(app=name))", "        pass", GUARD),
    Break("register command: a manifest without hosts is not said on stderr", "__main__.py", "        if hosts is None and args.app_manifest:", "        if False:", GUARD),
    Break("list: the status of the declaration is not shown", "cli_list.py", '"hosts_status": status', '"hosts_status": {}', GUARD),
    Break("register: an invalid declaration is written", "registry.py", "app_hosts.parse_declared(hosts if isinstance(hosts, (str, list)) else list(hosts))", "list(hosts)", GUARD),
    Break("register: the declaration is dropped", "registry.py", '        entry["hosts"] = declared', "        pass", GUARD),
    Break("list: the declaration is not shown", "cli_list.py", '            print("    hosts: %s" % app_hosts.declaration_text(entries[name]))', "            pass", GUARD),
    Break("feature: the id is not advertised", "features.py", '    "app_hosts_v1":', '    "app_hosts_v1_off":', GUARD),
]  # fmt: skip


@unittest.skipUnless(sys.platform.startswith("linux"), "the sabotage runs are part of the Linux CI job")
class Sabotage(unittest.TestCase):
    def test_every_break_turns_the_guard_red(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lc_hosts_sabotage_") as folder:
            base = Path(folder)
            control = run_slice(build_tree(base / "unbroken"), GUARD)
            self.assertEqual(
                control.returncode,
                0,
                "the guard fails on the UNBROKEN copy:\n" + (control.stdout + control.stderr)[-3000:],
            )
            survivors: list[str] = []
            dishonest: list[str] = []
            for index, break_ in enumerate(BREAKS):
                tree = build_tree(base / ("break%d" % index))
                apply(break_, tree)
                done: subprocess.CompletedProcess[str] = run_slice(tree, GUARD)
                shutil.rmtree(tree, ignore_errors=True)  # one tree at a time: the tests are copied each time
                output = done.stderr + done.stdout
                if done.returncode == 0:
                    survivors.append(break_.id)
                elif not re.search(r"FAILED \((failures|errors)", output):
                    dishonest.append(
                        "%s: the guard did not fail by an assertion:\n%s" % (break_.id, output[-600:])
                    )
            self.assertEqual(dishonest, [])
            self.assertEqual(
                survivors, [], "these breaks of the hosts rule were NOT caught: add a case for each"
            )


class TheTableIsHonest(unittest.TestCase):
    def test_every_break_applies_to_the_current_source_and_compiles(self) -> None:
        ids = [b.id for b in BREAKS]
        self.assertEqual(len(ids), len(set(ids)))
        with tempfile.TemporaryDirectory(prefix="lc_hosts_table_") as folder:
            for index, break_ in enumerate(BREAKS):
                with self.subTest(break_.id):
                    tree = Path(folder) / ("t%d" % index)
                    (tree / "labconstrictor_tools").mkdir(parents=True)
                    source = ROOT / "labconstrictor_tools" / break_.file
                    (tree / "labconstrictor_tools" / break_.file).write_text(
                        source.read_text(encoding="utf-8"), encoding="utf-8"
                    )
                    apply(break_, tree)


if __name__ == "__main__":
    unittest.main()
