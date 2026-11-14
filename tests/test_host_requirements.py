"""Which host plugin an app needs (`host_requirements.py`, feature `host_requirements_v1`, issue #155): the reference
function, the conformance vectors every host reads, the manifest reader, registration and `check`/`list`."""

import json
import tempfile
import unittest
from pathlib import Path

import _paths  # noqa: F401  (must come first)
import yaml  # type: ignore[import-untyped]  # PyYAML is a test extra; its stubs are not installed
from _paths import GENERIC_PREFIX, SYNTHETIC_MODULE
from test_cli_and_registry import cli

from labconstrictor_tools import conformance, features, registry
from labconstrictor_tools import host_requirements as hr

VECTORS = conformance.load()["host_requirements"]

MANIFEST = """schema: 1
name: StarDist2D
hosts: [notebook, napari, fiji, qupath]
host_requirements:
  qupath:
    min_version: v0.1.0-alpha.6   # the ownership fix
    features: [shapes_owner_v1]
    why: "Replace keeps # your own annotations"
  'fiji':
    min_version: 0.1.0-alpha.6
    required: false
platforms: [linux]
"""


class Vectors(unittest.TestCase):
    def test_every_case_gives_the_expected_verdict_and_exact_sentence(self) -> None:
        for case in VECTORS["cases"]:
            with self.subTest(case["case"]):
                args = (case["entry"], case["host"], case["host_version"], case["host_features"])
                if case["expect"] == "error":
                    with self.assertRaises(ValueError):
                        hr.check(*args)
                else:
                    self.assertEqual(hr.check(*args), (case["expect"], case["sentence"]))

    def test_every_verdict_and_message_is_covered(self) -> None:
        expects = {case["expect"] for case in VECTORS["cases"]}
        self.assertEqual(expects, {"ok", "warn", "refuse", "error"})
        sentences = " ".join(case.get("sentence", "") for case in VECTORS["cases"])
        for marker in ("or newer", "does not have it", "is unknown", "is not valid"):
            self.assertIn(marker, sentences)

    def test_the_version_order_sorts_strictly(self) -> None:
        keys = [hr.version_key(v) for v in VECTORS["version_order"]]
        self.assertEqual(keys, sorted(keys))
        self.assertEqual(len(set(keys)), len(keys))
        self.assertEqual(hr.version_key("v0.1.0-alpha.6"), hr.version_key("0.1.0a6"))
        self.assertEqual(hr.version_key("0.1"), hr.version_key("0.1.0"))

    def test_the_feature_is_announced(self) -> None:
        self.assertIn(hr.FEATURE, features.FEATURES)
        self.assertEqual(conformance.validate(conformance.load()), [])

    def test_a_damaged_section_is_reported(self) -> None:
        self.assertTrue(hr.validate_vectors({}))
        self.assertTrue(hr.validate_vectors([]))
        broken = json.loads(json.dumps(VECTORS))
        broken["messages"]["too_old"]["template"] = "changed"
        self.assertTrue(any("too_old" in p for p in hr.validate_vectors(broken)))


class Declaration(unittest.TestCase):
    def test_bad_declarations_are_refused_with_a_sentence(self) -> None:
        bad = {
            "not a mapping": ["qupath"],
            "notebook": {"notebook": {"min_version": "1.0"}},
            "host not a mapping": {"fiji": "0.1.0"},
            "unknown key": {"fiji": {"min_versoin": "0.1.0"}},
            "nothing": {"fiji": {"why": "x"}},
            "bad version": {"fiji": {"min_version": "latest"}},
            "number version": {"fiji": {"min_version": 0.1}},
            "bad features": {"fiji": {"features": "log_progress_v1"}},
            "bad feature id": {"fiji": {"features": ["Log Progress"]}},
            "two-line why": {"fiji": {"min_version": "1", "why": "a\nb"}},
            "required text": {"fiji": {"min_version": "1", "required": "yes"}},
        }
        for label, value in bad.items():
            with self.subTest(label), self.assertRaises(ValueError):
                hr.parse_declared(value)

    def test_the_manifest_reader_agrees_with_yaml(self) -> None:
        mine = hr.parse_declared(hr.requirements_in_manifest(MANIFEST))
        self.assertEqual(mine, hr.parse_declared(yaml.safe_load(MANIFEST)["host_requirements"]))
        self.assertEqual(mine["qupath"]["why"], "Replace keeps # your own annotations")
        self.assertEqual(list(mine), ["fiji", "qupath"])

    def test_a_manifest_without_the_key_has_no_requirement(self) -> None:
        self.assertIsNone(hr.requirements_in_manifest("schema: 1\nhosts: [notebook]\n"))
        self.assertEqual(hr.requirements_in_manifest("host_requirements: {}\n"), {})

    def test_forms_the_reader_does_not_understand_are_refused(self) -> None:
        for text in (
            "host_requirements: {fiji: {min_version: 1}}\n",
            "host_requirements:\nhosts: [fiji]\n",
            "host_requirements:\n  fiji:\n    min_version: 1\n      why: x\n",
            "host_requirements:\n  fiji:\n    min_version: 1\nhost_requirements:\n  qupath:\n    min_version: 1\n",
            "host_requirements:\n  fiji:\n    features: [a,\n",
        ):
            with self.subTest(text), self.assertRaises(ValueError):
                hr.parse_declared(hr.requirements_in_manifest(text))

    def test_list_text(self) -> None:
        entry = {"host_requirements": hr.parse_declared(hr.requirements_in_manifest(MANIFEST))}
        self.assertEqual(
            hr.declaration_text(entry), "Fiji >= 0.1.0-alpha.6; QuPath >= v0.1.0-alpha.6 + shapes_owner_v1"
        )
        self.assertEqual(hr.declaration_text({}), "none")


class Registration(unittest.TestCase):
    def setUp(self) -> None:
        self.home = Path(tempfile.mkdtemp(prefix="lchome_"))
        self.manifest = self.home / "labconstrictor-app.yaml"

    def register(self, text: str) -> "tuple[int, str, str]":
        self.manifest.write_text(text, encoding="utf-8")
        done = cli("register", "--name", "app", "--prefix", str(GENERIC_PREFIX), "--module", SYNTHETIC_MODULE,
                   "--version", "1", "--app-manifest", str(self.manifest), home=self.home)  # fmt: skip
        return done.returncode, done.stdout, done.stderr

    def test_the_manifest_requirements_land_in_the_entry(self) -> None:
        code, out, error = self.register(MANIFEST)
        self.assertEqual(code, 0, error)
        on_disk = json.loads((self.home / "apps" / "app.json").read_text(encoding="utf-8"))
        self.assertEqual(
            on_disk["host_requirements"]["fiji"], {"min_version": "0.1.0-alpha.6", "required": False}
        )
        self.assertIn(hr.FEATURE, on_disk["features"])
        self.assertEqual(hr.check(on_disk, "fiji", "0.1.0a5")[0], "warn")
        listed = cli("list", home=self.home).stdout
        self.assertIn("needs: Fiji >= 0.1.0-alpha.6; QuPath", listed)

    def test_no_key_means_no_field(self) -> None:
        code, _, error = self.register("hosts: [notebook]\n")
        self.assertEqual(code, 0, error)
        self.assertNotIn("host_requirements", json.loads((self.home / "apps" / "app.json").read_text()))

    def test_an_invalid_key_registers_nothing(self) -> None:
        code, _, error = self.register(
            "hosts: [notebook]\nhost_requirements:\n  notebook:\n    min_version: 1\n"
        )
        self.assertEqual(code, 2)
        self.assertIn("nothing was registered", error)
        self.assertIn("the notebook needs no plugin", error)
        self.assertFalse((self.home / "apps" / "app.json").exists())

    def test_the_library_call_refuses_before_writing(self) -> None:
        with self.assertRaises(ValueError):
            registry.register(
                "app", GENERIC_PREFIX, SYNTHETIC_MODULE, "1", directory=self.home / "apps", hosts=["fiji"],
                requirements={"fiji": {"min_version": "soon"}},
            )  # fmt: skip
        self.assertFalse((self.home / "apps").exists() and list((self.home / "apps").glob("*")))

    def test_check_prints_the_requirements(self) -> None:
        self.manifest.write_text(MANIFEST, encoding="utf-8")
        done = cli(
            "check", "--module", SYNTHETIC_MODULE, "--app-manifest", str(self.manifest), home=self.home
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("✔ host_requirements", done.stdout)
        self.manifest.write_text("hosts: [fiji]\nhost_requirements:\n  fiji:\n    min_version: soon\n")
        done = cli(
            "check", "--module", SYNTHETIC_MODULE, "--app-manifest", str(self.manifest), home=self.home
        )
        self.assertEqual(done.returncode, 1)
        self.assertIn("✖ host_requirements", done.stdout)


if __name__ == "__main__":
    unittest.main()
