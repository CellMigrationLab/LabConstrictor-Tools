"""`tools_version` and `features` in the schema, the registry entry, `describe` and `doctor` (docs/PROTOCOL.md)."""

import json
import re
import tempfile
import unittest
from pathlib import Path

import _paths  # noqa: F401  (must come first)
from _paths import ROOT, SYNTHETIC_MODULE
from test_cli_and_registry import cli, register

import labconstrictor_tools
from labconstrictor_tools import features, introspection, registry


def documented_feature_ids() -> set[str]:
    text = (ROOT / "docs" / "PROTOCOL.md").read_text(encoding="utf-8")
    section = text.split("## Tools version and features", 1)[1].split("\n## ", 1)[0]
    return set(re.findall(r"^\| `(\w+)` \|", section, re.M))


class Schema(unittest.TestCase):
    def test_the_generated_schema_carries_the_version_and_the_features(self) -> None:
        schema = introspection.describe_tools(SYNTHETIC_MODULE)
        self.assertEqual(schema["tools_version"], labconstrictor_tools.__version__)
        self.assertEqual(schema["features"], sorted(features.FEATURES))
        self.assertIn("reserved_inputs_v1", schema["features"])
        self.assertEqual(schema["protocol"], 1)  # additive: still protocol 1

    def test_the_ids_of_this_version(self) -> None:
        # shm_order_v1 (PR #125) is what tells 0.3.0a1 from the rc.1 / rc.2 / main that all reported 0.2.0rc1 with the first two
        self.assertEqual(sorted(features.FEATURES), ["reserved_inputs_v1", "retention_prune", "shm_order_v1"])
        text = (ROOT / "docs" / "PROTOCOL.md").read_text(encoding="utf-8")
        self.assertIn("The behaviour already existed (PR #125) before the id", text)
        self.assertIn(
            "Tools >= 0.3.0a1 maps big TIFF files", text
        )  # an optimisation: documented, no feature id

    def test_every_feature_id_is_documented(self) -> None:
        self.assertTrue(set(features.FEATURES) <= documented_feature_ids())

    def test_describe_prints_them(self) -> None:
        home = Path(tempfile.mkdtemp(prefix="lchome_"))
        printed = json.loads(cli("describe", "--module", SYNTHETIC_MODULE, home=home).stdout)
        self.assertEqual(printed["tools_version"], labconstrictor_tools.__version__)
        self.assertEqual(printed["features"], sorted(features.FEATURES))


class RegistryAndDoctor(unittest.TestCase):
    def setUp(self) -> None:
        self.home = Path(tempfile.mkdtemp(prefix="lchome_"))

    def test_register_writes_them_into_the_entry_and_the_cached_schema(self) -> None:
        entry = register(self.home, "synthetic")
        self.assertEqual(entry["tools_version"], labconstrictor_tools.__version__)
        self.assertEqual(entry["features"], sorted(features.FEATURES))
        on_disk = json.loads((self.home / "apps" / "synthetic.json").read_text())
        cached = json.loads((self.home / "apps" / "synthetic.schema.json").read_text())
        self.assertEqual(on_disk["tools_version"], cached["tools_version"])
        self.assertEqual(on_disk["features"], cached["features"])

    def test_doctor_prints_them_and_does_not_call_an_upgrade_stale(self) -> None:
        register(self.home, "synthetic")
        shown = cli("doctor", home=self.home).stdout
        self.assertIn(
            "Tools %s, features: %s"
            % (labconstrictor_tools.__version__, ", ".join(sorted(features.FEATURES))),
            shown,
        )
        path = self.home / "apps" / "synthetic.schema.json"
        schema = json.loads(path.read_text())
        schema["tools_version"] = "0.1.0"
        schema["features"] = []
        path.write_text(json.dumps(schema))
        older = cli("doctor", home=self.home).stdout
        self.assertNotIn("stale", older)
        self.assertIn("Tools 0.1.0, features: none listed", older)

    def test_a_schema_from_before_0_2_is_still_read_and_reported_as_unknown(self) -> None:
        register(self.home, "synthetic")
        path = self.home / "apps" / "synthetic.schema.json"
        schema = json.loads(path.read_text())
        del schema["tools_version"], schema["features"]  # what Tools 0.1 wrote
        path.write_text(json.dumps(schema))
        listed = json.loads(cli("list", "--json", home=self.home).stdout)
        self.assertIn("synthetic", listed["apps"])
        self.assertIn("Tools version unknown", cli("doctor", home=self.home).stdout)

    def test_a_host_of_protocol_1_ignores_fields_it_does_not_know(self) -> None:
        schema = introspection.describe_tools(SYNTHETIC_MODULE)
        schema["features"] = ["from_the_future"]
        schema["a_new_field"] = {"x": 1}
        self.assertIs(registry._validated_schema(schema), schema)


if __name__ == "__main__":
    unittest.main()
