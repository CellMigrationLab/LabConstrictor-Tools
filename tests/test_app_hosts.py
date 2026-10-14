"""The per-host discovery rule (`app_hosts.py`, feature `app_hosts_v1`): the reference function, the vectors every host reads,
registration, `list`, and the promise that the command line is never filtered."""

import json
import logging
import os
import tempfile
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING
from unittest import mock

import _paths  # noqa: F401  (must come first)
from _paths import GENERIC_PREFIX, ROOT, SYNTHETIC_MODULE
from test_cli_and_registry import cli

from labconstrictor_tools import app_hosts, compat, conformance, features, introspection, registry
from labconstrictor_tools.app_hosts import HOSTS, listed_for

if TYPE_CHECKING:
    from typing import Any

VECTORS = conformance.load()["app_hosts"]
ALL = list(HOSTS)


def entry(hosts: "Any" = None, name: str = "App", present: bool = True) -> "dict[str, Any]":
    return {"name": name, **({"hosts": hosts} if present else {})}


class Function(unittest.TestCase):
    def test_a_listed_host_gets_no_sentence(self) -> None:
        for host in ALL:
            self.assertEqual(listed_for(entry(ALL), host), (True, ""))

    def test_an_excluded_host_is_refused_with_the_exact_sentence(self) -> None:
        listed, sentence = listed_for(entry(["notebook", "fiji"], "VLab4Mic"), "qupath")
        self.assertFalse(listed)
        self.assertEqual(
            sentence, "'VLab4Mic' is not listed in qupath: the app declares hosts: notebook, fiji"
        )

    def test_an_absent_field_is_listed_everywhere_and_says_so(self) -> None:
        for host in ALL:
            listed, sentence = listed_for(entry(present=False, name="Old"), host)
            self.assertTrue(listed)
            self.assertEqual(
                sentence,
                "'Old' declares no hosts, so it is listed in every host; register it with --app-manifest (or --hosts) to choose",
            )

    def test_every_invalid_declaration_is_not_listed_anywhere_and_says_why(self) -> None:
        problems = {
            "text": ("napari", "hosts must be a list of host names"),
            "null": (None, "hosts must be a list of host names"),
            "empty": ([], "hosts is empty; write at least notebook"),
            "item": (["napari", 3], "hosts must contain only text"),
            "unknown": (
                ["napari", "napary"],
                "unknown host name 'napary' (known: notebook, napari, fiji, qupath)",
            ),
            "case": (["Napari"], "unknown host name 'Napari' (known: notebook, napari, fiji, qupath)"),
            "twice": (["fiji", "fiji"], "host name 'fiji' appears twice"),
        }
        for label, (value, problem) in problems.items():
            for host in ALL:
                with self.subTest(label, host=host):
                    listed, sentence = listed_for(entry(value, "X"), host)
                    self.assertFalse(listed)
                    self.assertIn("(%s)" % problem, sentence)
                    self.assertTrue(sentence.startswith("'X' is not listed in %s: " % host))

    def test_an_unknown_asking_host_is_a_programming_error(self) -> None:
        for host in ("emacs", "Napari", "", "jupyter"):
            with self.assertRaises(ValueError):
                listed_for(entry(ALL), host)

    def test_the_function_does_not_change_the_entry_and_ignores_other_fields(self) -> None:
        original = {**entry(["fiji"]), "python": "/x", "features": ["app_hosts_v1"]}
        before = json.dumps(original, sort_keys=True)
        listed_for(original, "fiji")
        self.assertEqual(json.dumps(original, sort_keys=True), before)

    def test_the_declaration_line_of_list(self) -> None:
        self.assertEqual(app_hosts.declaration_text(entry(["notebook", "fiji"])), "notebook, fiji")
        self.assertEqual(
            app_hosts.declaration_text(entry(present=False)), "not declared (listed in every host)"
        )
        self.assertIn("INVALID", app_hosts.declaration_text(entry([])))


class Vectors(unittest.TestCase):
    """conformance.json section app_hosts: the data Fiji and QuPath read must be what the reference function answers."""

    def test_every_case_is_what_the_reference_function_answers(self) -> None:
        for case in VECTORS["cases"]:
            with self.subTest(case["case"]):
                if case["expect"] == "error":
                    with self.assertRaises(ValueError):
                        listed_for(case["entry"], case["host"])
                    continue
                listed, sentence = listed_for(case["entry"], case["host"])
                self.assertEqual(listed, case["expect"] == "listed")
                self.assertEqual(sentence, case["sentence"])

    def test_the_vectors_cover_what_the_task_asked_for(self) -> None:
        names = " | ".join(case["case"] for case in VECTORS["cases"])
        for needle in ("matrix: CellTracksColab in napari", "matrix: VLab4Mic in qupath", "absent field", "empty list",
                       "string instead of a list", "unknown host name in the list", "unknown asking host"):  # fmt: skip
            self.assertIn(needle, names)
        expects = {case["expect"] for case in VECTORS["cases"]}
        self.assertEqual(expects, {"listed", "not_listed", "error"})

    def test_the_decided_matrix_is_in_the_vectors(self) -> None:
        matrix = {
            "CellTracksColab": [],
            "GuessTheCondition": ["napari", "fiji", "qupath"],
            "Playground": ["napari", "fiji", "qupath"],
            "NucleiSky": ["napari", "fiji", "qupath"],
            "VLab4Mic": ["napari", "fiji"],
        }
        listed: dict[str, list[str]] = {}
        for case in VECTORS["cases"]:
            if case["case"].startswith("matrix: ") and case["host"] != "notebook":
                hosts = listed.setdefault(case["entry"]["name"], [])
                if case["expect"] == "listed":
                    hosts.append(case["host"])
        self.assertEqual(
            {app: sorted(hosts) for app, hosts in listed.items()}, {a: sorted(h) for a, h in matrix.items()}
        )

    def test_the_messages_of_the_file_are_the_templates_of_the_code(self) -> None:
        messages = VECTORS["messages"]
        self.assertEqual(messages["not_listed"]["template"], app_hosts.NOT_LISTED)
        self.assertEqual(messages["absent"]["template"], app_hosts.ABSENT)
        self.assertEqual(messages["invalid"]["template"], app_hosts.INVALID)

    def test_the_compat_rule_and_cases(self) -> None:
        rule = VECTORS["compat_rule"]
        self.assertEqual(rule["required_features"], [app_hosts.FEATURE])
        for case in VECTORS["compat_cases"]:
            with self.subTest(case["case"]):
                result = compat.check_schema(
                    case["schema"], rule["min_tools_version"], rule["required_features"]
                )
                self.assertEqual(result.status, case["expect"], result)
                self.assertIn(case.get("reason_contains", ""), result.reason)

    def test_a_broken_section_is_refused_by_the_validator(self) -> None:
        data = json.loads(json.dumps(conformance.load()))
        self.assertEqual(conformance.validate(data), [])
        for label, change in {
            "feature": lambda d: d["app_hosts"].update(feature="other"),
            "hosts": lambda d: d["app_hosts"].update(known_hosts=["napari"]),
            "no cases": lambda d: d["app_hosts"].update(cases=[]),
            "bad expect": lambda d: d["app_hosts"]["cases"][0].update(expect="maybe"),
            "no sentence": lambda d: d["app_hosts"]["cases"][0].pop("sentence"),
            "message drift": lambda d: d["app_hosts"]["messages"]["absent"].update(template="x"),
            "section missing": lambda d: d.pop("app_hosts"),
        }.items():
            with self.subTest(label):
                broken = json.loads(json.dumps(data))
                change(broken)
                self.assertTrue(conformance.validate(broken), label)


class Manifest(unittest.TestCase):
    def test_flow_and_block_lists_and_comments(self) -> None:
        cases = {
            "name: A\nhosts: [notebook, napari, fiji, qupath]\nkind: utility\n": ALL,
            "hosts: [ notebook ]   # only the notebook\n": ["notebook"],
            "hosts: ['napari', \"fiji\"]\n": ["napari", "fiji"],
            "hosts:\n  - notebook\n  - fiji  # why\n# a comment\n\n  - qupath\nkind: x\n": [
                "notebook",
                "fiji",
                "qupath",
            ],
            "hosts: []\n": [],
            "name: A\n": None,
        }
        for text, expected in cases.items():
            with self.subTest(text):
                self.assertEqual(app_hosts.hosts_in_manifest(text), expected)

    def test_a_hosts_line_inside_a_text_block_is_not_the_key(self) -> None:
        text = "description: |-\n  hosts: [napari]\nkind: utility\n"
        self.assertIsNone(app_hosts.hosts_in_manifest(text))

    def test_forms_that_are_not_understood_are_refused(self) -> None:
        for text in ("hosts: napari\n", "hosts: [napari,\n  fiji]\n", "hosts: [a]\nhosts: [b]\n"):
            with self.subTest(text), self.assertRaises(ValueError):
                app_hosts.hosts_in_manifest(text)

    def test_a_quoted_key_and_an_unindented_block_list_are_read(self) -> None:
        cases = {
            '"hosts": [qupath]\n': ["qupath"],
            "'hosts' : [fiji, notebook]\n": ["fiji", "notebook"],
            "hosts:\n- fiji\n- qupath\nkind: x\n": ["fiji", "qupath"],
            "hosts:\r\n  - fiji\r\n": ["fiji"],
            "hosts:\t[fiji]\n": ["fiji"],
            "hosts:\n---\n": [],
        }
        for text, expected in cases.items():
            with self.subTest(text):
                self.assertEqual(app_hosts.hosts_in_manifest(text), expected)

    def test_crlf_lines_and_a_comment_after_the_value_are_read(self) -> None:
        text = "name: A\r\nhosts: [notebook, fiji]   # tested\r\nkind: utility\r\n"
        self.assertEqual(app_hosts.hosts_in_manifest(text), ["notebook", "fiji"])
        self.assertEqual(app_hosts.hosts_in_manifest("hosts: [notebook#x]\n"), ["notebook#x"])

    def test_an_empty_item_is_named_as_such(self) -> None:
        for text in ("hosts: [notebook, ]\n", "hosts: [,]\n", "hosts:\n  - notebook\n  -\n"):
            with self.subTest(text), self.assertRaisesRegex(ValueError, "empty item"):
                app_hosts.hosts_in_manifest(text)
        with self.assertRaisesRegex(ValueError, "empty item"):
            app_hosts.from_arguments("napari,", None)

    def test_a_second_top_level_key_in_any_spelling_is_refused(self) -> None:
        with self.assertRaisesRegex(ValueError, "twice"):
            app_hosts.hosts_in_manifest('hosts: [napari]\n"hosts": [fiji]\n')

    def test_a_file_with_a_byte_order_mark_is_read(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "labconstrictor-app.yaml"
            path.write_bytes(b"\xef\xbb\xbfhosts: [qupath]\r\nkind: x\r\n")  # what Windows Notepad writes
            self.assertEqual(app_hosts.from_arguments(None, str(path)), ["qupath"])

    def test_the_status_of_an_entry(self) -> None:
        self.assertEqual(app_hosts.declaration_status(entry(ALL)), "declared")
        self.assertEqual(app_hosts.declaration_status(entry(present=False)), "absent")
        for bad in (None, [], ["emacs"], "fiji"):
            self.assertEqual(app_hosts.declaration_status(entry(bad)), "invalid", bad)

    def test_from_arguments(self) -> None:
        self.assertIsNone(app_hosts.from_arguments(None, None))
        self.assertEqual(app_hosts.from_arguments("notebook, fiji", None), ["notebook", "fiji"])
        for bad in ("", "napari,", "napari,napari", "emacs"):
            with self.subTest(bad), self.assertRaises(ValueError):
                app_hosts.from_arguments(bad, None)
        with self.assertRaises(ValueError):
            app_hosts.from_arguments("fiji", "labconstrictor-app.yaml")
        with self.assertRaises(ValueError):
            app_hosts.from_arguments(None, str(ROOT / "no" / "such" / "file.yaml"))

    def test_the_app_manifests_of_the_matrix_parse(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "labconstrictor-app.yaml"
            path.write_text("schema: 1\nhosts: [notebook, napari, fiji]\n", encoding="utf-8")
            self.assertEqual(app_hosts.from_arguments(None, str(path)), ["notebook", "napari", "fiji"])
            path.write_text("schema: 1\nhosts: []\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                app_hosts.from_arguments(None, str(path))
            path.write_text("schema: 1\n", encoding="utf-8")
            self.assertIsNone(app_hosts.from_arguments(None, str(path)))


@contextmanager
def captured_log() -> Iterator[list[str]]:
    from labconstrictor_tools import log

    lines: list[str] = []

    class Collect(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            lines.append(record.getMessage())

    handler = Collect()
    log.logger().addHandler(handler)
    try:
        yield lines
    finally:
        log.logger().removeHandler(handler)


class Registration(unittest.TestCase):
    def setUp(self) -> None:
        self.home = Path(tempfile.mkdtemp(prefix="lchome_"))

    def register(self, *extra: str) -> "tuple[int, dict[str, Any] | None, str]":
        done = cli("register", "--name", "app", "--prefix", str(GENERIC_PREFIX), "--module", SYNTHETIC_MODULE,
                   "--version", "1", *extra, home=self.home)  # fmt: skip
        return done.returncode, (json.loads(done.stdout) if done.returncode == 0 else None), done.stderr

    def test_hosts_land_in_the_entry_and_the_cached_files_agree(self) -> None:
        code, written, _ = self.register("--hosts", "notebook,napari,fiji")
        self.assertEqual(code, 0)
        assert written is not None
        self.assertEqual(written["hosts"], ["notebook", "napari", "fiji"])
        on_disk = json.loads((self.home / "apps" / "app.json").read_text(encoding="utf-8"))
        self.assertEqual(on_disk["hosts"], ["notebook", "napari", "fiji"])
        self.assertIn("app_hosts_v1", on_disk["features"])

    def test_the_manifest_is_read(self) -> None:
        manifest = self.home / "labconstrictor-app.yaml"
        manifest.write_text("schema: 1\nhosts: [notebook]\n", encoding="utf-8")
        code, written, _ = self.register("--app-manifest", str(manifest))
        self.assertEqual(code, 0)
        assert written is not None
        self.assertEqual(written["hosts"], ["notebook"])

    def test_without_a_declaration_the_field_is_absent_and_it_is_logged(self) -> None:
        with captured_log() as lines:
            written = registry.register(
                "app", GENERIC_PREFIX, SYNTHETIC_MODULE, "1", directory=self.home / "apps"
            )
        self.assertNotIn("hosts", written)
        self.assertNotIn("hosts", json.loads((self.home / "apps" / "app.json").read_text(encoding="utf-8")))
        self.assertIn(app_hosts.ABSENT.format(app="app"), lines)

    def test_a_manifest_without_a_hosts_line_registers_and_says_so_on_stderr(self) -> None:
        manifest = self.home / "labconstrictor-app.yaml"
        manifest.write_text("schema: 1\nname: x\n", encoding="utf-8")
        code, written, error = self.register("--app-manifest", str(manifest))
        self.assertEqual(code, 0, error)
        assert written is not None
        self.assertNotIn("hosts", written)
        self.assertIn("has no hosts: line", error)
        self.assertIn(app_hosts.ABSENT.format(app="app"), error)

    def test_a_manifest_with_a_byte_order_mark_or_a_quoted_key_is_not_read_as_absent(self) -> None:
        for raw in (b"\xef\xbb\xbfhosts: [qupath]\r\n", b'"hosts": [qupath]\n'):
            with self.subTest(raw):
                manifest = self.home / "labconstrictor-app.yaml"
                manifest.write_bytes(raw)
                code, written, error = self.register("--app-manifest", str(manifest))
                self.assertEqual(code, 0, error)
                assert written is not None
                self.assertEqual(written["hosts"], ["qupath"])
                self.assertNotIn("no hosts", error)

    def test_an_invalid_declaration_writes_nothing_and_exits_2(self) -> None:
        for extra in (("--hosts", "emacs"), ("--hosts", ""), ("--hosts", "fiji,fiji")):
            with self.subTest(extra):
                code, _, error = self.register(*extra)
                self.assertEqual(code, 2, error)
                self.assertIn("nothing was registered", error)
                self.assertFalse((self.home / "apps" / "app.json").exists())
                self.assertFalse((self.home / "apps" / "app.schema.json").exists())
        manifest = self.home / "m.yaml"
        manifest.write_text("hosts: []\n", encoding="utf-8")
        code, _, error = self.register("--app-manifest", str(manifest))
        self.assertEqual(code, 2)
        self.assertIn("hosts is empty", error)
        code, _, error = self.register("--app-manifest", str(self.home / "missing.yaml"))
        self.assertEqual(code, 2)
        self.assertIn("cannot read", error)

    def test_the_library_call_refuses_an_invalid_list_before_writing_anything(self) -> None:
        for hosts in ([], ["emacs"], ["fiji", "fiji"], "fiji"):
            with self.subTest(hosts=hosts), self.assertRaises(ValueError):
                registry.register("app", GENERIC_PREFIX, SYNTHETIC_MODULE, "1", directory=self.home / "apps", hosts=hosts)  # type: ignore[arg-type]
            self.assertEqual(
                list((self.home / "apps").glob("*")) if (self.home / "apps").exists() else [], []
            )

    def test_both_flags_are_refused_by_the_parser(self) -> None:
        code, _, error = self.register("--hosts", "fiji", "--app-manifest", "x.yaml")
        self.assertEqual(code, 2)
        self.assertIn("not allowed with", error)

    def test_the_registry_returns_the_field_untouched_even_when_it_is_wrong(self) -> None:
        self.register("--hosts", "fiji")
        path = self.home / "apps" / "app.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["hosts"] = []
        path.write_text(json.dumps(data), encoding="utf-8")
        path.chmod(0o644)
        with mock.patch.dict(os.environ, {"LC_HOME": str(self.home), "LC_APPS_PATH": ""}):
            entries = registry.load_entries()[0]
        self.assertEqual(entries["app"]["hosts"], [])
        self.assertFalse(listed_for(entries["app"], "fiji")[0])


class CommandLine(unittest.TestCase):
    """`list` shows the declaration; `run` is never filtered by it."""

    def setUp(self) -> None:
        self.home = Path(tempfile.mkdtemp(prefix="lchome_"))

    def register(self, name: str, *extra: str) -> None:
        done = cli("register", "--name", name, "--prefix", str(GENERIC_PREFIX), "--module", SYNTHETIC_MODULE,
                   "--version", "1", *extra, home=self.home)  # fmt: skip
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_list_shows_the_declaration_in_text_and_json(self) -> None:
        self.register("only_notebook", "--hosts", "notebook")
        self.register("everywhere", "--hosts", ",".join(ALL))
        self.register("old")
        text = cli("list", home=self.home).stdout
        self.assertIn("only_notebook  (1)\n    hosts: notebook\n", text)
        self.assertIn("everywhere  (1)\n    hosts: notebook, napari, fiji, qupath\n", text)
        self.assertIn("old  (1)\n    hosts: not declared (listed in every host)\n", text)
        listed = json.loads(cli("list", "--json", home=self.home).stdout)
        self.assertEqual(listed["hosts"], {"only_notebook": ["notebook"], "everywhere": ALL, "old": None})
        self.assertEqual(
            listed["hosts_status"], {"only_notebook": "declared", "everywhere": "declared", "old": "absent"}
        )
        self.assertIn(
            "tools", listed["apps"]["only_notebook"]
        )  # an app hidden from every host is still listed here

    def test_run_is_not_filtered_for_an_app_that_no_host_may_list(self) -> None:
        self.register("hidden", "--hosts", "notebook")
        table = self.home / "table.csv"
        table.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")
        shown = cli("run", "hidden", "table_sum", "tab=%s" % table, home=self.home)
        self.assertEqual(shown.returncode, 0, shown.stderr)
        self.assertEqual(json.loads(shown.stdout)["status"], "COMPLETE")

    def test_check_reports_the_hosts_line_of_a_manifest(self) -> None:
        manifest = self.home / "labconstrictor-app.yaml"
        for text, code, words in (
            ("hosts: [notebook, fiji]\n", 0, "✔ hosts"),
            ("name: x\n", 0, "no hosts: line"),
            ("hosts: []\n", 1, "✖ hosts"),
        ):
            with self.subTest(text):
                manifest.write_text(text, encoding="utf-8")
                done = cli(
                    "check", "--module", SYNTHETIC_MODULE, "--app-manifest", str(manifest), home=self.home
                )
                self.assertEqual(done.returncode, code, done.stdout + done.stderr)
                self.assertIn(words, done.stdout)


class Feature(unittest.TestCase):
    def test_the_schema_this_tools_writes_carries_the_feature(self) -> None:
        written = introspection.describe_tools(SYNTHETIC_MODULE)
        self.assertIn("app_hosts_v1", written["features"])
        self.assertIn("app_hosts_v1", features.FEATURES)
        self.assertEqual(app_hosts.FEATURE, "app_hosts_v1")

    def test_a_host_that_needs_it_refuses_a_tools_without_it(self) -> None:
        old = {"protocol": 1, "tools": [], "tools_version": "0.3.0a1", "features": ["reserved_inputs_v1"]}
        result = compat.check_schema(old, "0.3.0a1", ["app_hosts_v1"])
        self.assertEqual(result.status, compat.REFUSE)
        self.assertIn("app_hosts_v1", result.reason)
        written = introspection.describe_tools(SYNTHETIC_MODULE)
        self.assertEqual(compat.check_schema(written, "0.3.0a1", ["app_hosts_v1"]).status, compat.OK)


if __name__ == "__main__":
    unittest.main()
