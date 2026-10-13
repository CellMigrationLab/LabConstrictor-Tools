"""`labconstrictor_tools.compat.check_schema`: the host rules of docs/PROTOCOL.md, one case per rule."""

import re
import unittest
from typing import TYPE_CHECKING

import _paths  # noqa: F401  (must come first)
from _paths import ROOT

from labconstrictor_tools import compat, features, introspection
from labconstrictor_tools.compat import OK, REFUSE, WARN, check_schema, parse_version

if TYPE_CHECKING:
    from typing import Any

NEED = ["reserved_inputs_v1"]
MIN = "0.2.0rc1"


def schema(**extra: "Any") -> "dict[str, Any]":
    return {"protocol": 1, "tools": [], **extra}


CASES = [
    # (name, schema, min, required, warn_below, expected status, words the reason must contain)
    ("current", schema(tools_version="0.2.0rc1", features=NEED), MIN, NEED, None, OK, ""),
    ("newer release", schema(tools_version="0.3.1", features=NEED + ["x"]), MIN, NEED, None, OK, ""),
    ("unknown protocol", {"protocol": 2, "tools": []}, MIN, NEED, None, REFUSE, "protocol"),
    ("old Tools: nothing recorded", schema(), MIN, NEED, None, REFUSE, "too old"),
    ("old Tools, no feature needed but a minimum", schema(), MIN, [], None, REFUSE, "no version recorded"),
    ("old Tools, nothing demanded", schema(), None, [], None, WARN, "unknown"),
    ("feature missing", schema(tools_version="0.2.0", features=["other"]), None, NEED, None, REFUSE, "reserved_inputs_v1"),
    ("features is not a list", schema(tools_version="0.2.0", features="reserved_inputs_v1"), None, NEED, None, REFUSE, "too old"),
    ("below the minimum", schema(tools_version="0.1.9", features=NEED), MIN, NEED, None, REFUSE, "older than"),
    ("an rc is below its release", schema(tools_version="0.2.0rc1", features=NEED), "0.2.0", NEED, None, REFUSE, "older than"),
    ("below the soft limit", schema(tools_version="0.2.0rc1", features=NEED), MIN, NEED, "0.2.0", WARN, "recommended"),
    ("version not understood", schema(tools_version="banana", features=NEED), None, NEED, None, WARN, "not understood"),
]  # fmt: skip


class Rules(unittest.TestCase):
    def test_every_rule(self) -> None:
        for name, sch, low, need, soft, status, words in CASES:
            with self.subTest(name):
                result = check_schema(sch, low, need, soft)
                self.assertEqual(result.status, status, result)
                self.assertIn(words, result.reason)
                if status != OK:
                    self.assertEqual(result.reason.count(". "), 0, "one sentence: " + result.reason)
                    self.assertTrue(result.reason.strip())

    def test_version_order(self) -> None:
        order = ["0.2.0a1", "0.2.0b1", "0.2.0rc1", "0.2.0", "0.2.1", "0.10.0", "1.0.0"]
        keys = [parse_version(v) for v in order]
        self.assertEqual(keys, sorted(keys))
        self.assertEqual(parse_version("v0.2.0-rc.1"), parse_version("0.2.0rc1"))  # the tag spelling
        self.assertEqual(parse_version("0.2"), parse_version("0.2.0"))
        for bad in ("", "x", None, 3, "0.2.0.1"):
            self.assertIsNone(parse_version(bad), bad)

    def test_a_host_that_passes_nonsense_limits_is_told(self) -> None:
        with self.assertRaises(ValueError):
            check_schema(schema(), "not-a-version")

    def test_the_schema_this_tools_writes_passes_its_own_minimum(self) -> None:
        written = introspection.describe_tools("labconstrictor_tools.examples.synthetic")
        self.assertEqual(check_schema(written, MIN, sorted(features.FEATURES)).status, OK)

    def test_the_rules_in_protocol_md_name_every_status_and_the_helper(self) -> None:
        text = (ROOT / "docs" / "PROTOCOL.md").read_text(encoding="utf-8")
        section = text.split("### Compatibility rules for hosts", 1)[1].split("\n## ", 1)[0]
        for needle in ("`refuse`", "`warn`", "`ok`", "check_schema", "unknown/old", "0.2.0rc1"):
            self.assertTrue(needle in section, "PROTOCOL.md rules lack " + needle)
        self.assertTrue(re.search(r"conformance\.json", section))
        self.assertIs(compat.check_schema, check_schema)


if __name__ == "__main__":
    unittest.main()
