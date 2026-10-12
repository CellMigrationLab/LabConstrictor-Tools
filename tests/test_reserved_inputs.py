"""Reserved underscore inputs (`_job_dir`, `_calibration`, `_axes`, ...): accepted and ignored, never an error.

This must hold before issue #51 (reject undeclared inputs) is enforced: #51 may only reject what
`convert.undeclared_inputs` returns, and that function consults `protocol.RESERVED_INPUTS`.
"""

import re
import unittest
from unittest import mock

import _paths  # noqa: F401  (must come first)
from _paths import ROOT
from test_worker_protocol import RawWorker, execute

from labconstrictor_tools import convert, decorators, introspection, protocol
from labconstrictor_tools.decorators import tool

SCHEMA = {
    "id": "t",
    "label": "T",
    "inputs": [{"name": "size", "label": "Size", "type": "integer", "required": False, "default": 3}],
    "outputs": [],
}


def documented_reserved_names():
    text = (ROOT / "docs" / "PROTOCOL.md").read_text(encoding="utf-8")
    section = text.split("## Reserved inputs", 1)[1].split("\n## ", 1)[0]
    return set(re.findall(r"^\| `(_\w+)` \|", section, re.M))


class ReservedList(unittest.TestCase):
    def test_the_documented_list_is_the_code_list(self):
        self.assertEqual(documented_reserved_names(), set(protocol.RESERVED_INPUTS))
        for name in ("_job_dir", "_calibration", "_axes"):
            self.assertIn(name, protocol.RESERVED_INPUTS)

    def test_load_inputs_consults_the_reserved_list(self):
        """Failing-if-missing: if the list is not what decides, #51 would reject `_calibration` and `_axes`."""
        sent = {"size": 5, "_calibration": {"pixel_size": {}}, "_axes": {"image": "YX"}, "_job_dir": "x"}
        self.assertEqual(convert.undeclared_inputs(SCHEMA, sent), [])
        # take the names off the list (and switch the underscore rule off): the very same call must now see them
        with (
            mock.patch.object(convert, "RESERVED_INPUTS", frozenset({"_job_dir"})),
            mock.patch.object(convert, "RESERVED_PREFIX", "\0"),
        ):
            self.assertEqual(convert.undeclared_inputs(SCHEMA, sent), ["_axes", "_calibration"])

    def test_undeclared_inputs_names_only_what_a_tool_does_not_declare(self):
        self.assertEqual(convert.undeclared_inputs(SCHEMA, {"size": 1, "oops": 2, "_future": 3}), ["oops"])

    def test_load_inputs_never_hands_reserved_inputs_to_the_tool(self):
        sent = {"size": 5, "_calibration": {"a": 1}, "_axes": {"i": "YX"}, "_from_the_future": 1}
        self.assertEqual(convert.load_inputs(SCHEMA, sent), {"size": 5})

    def test_a_tool_cannot_declare_a_reserved_name(self):
        for name in sorted(protocol.RESERVED_INPUTS):
            module = "reserved_name_test_" + name
            namespace = {"__name__": module}
            exec(f"def f({name}: int = 1) -> None: ...", namespace)  # noqa: S102
            namespace["f"].__module__ = module
            tool(namespace["f"])
            try:
                with self.subTest(name), self.assertRaisesRegex(introspection.DeclarationError, "reserved"):
                    introspection.describe_tools(module)
            finally:
                decorators.forget_module(module)


class WorkerAcceptsThem(unittest.TestCase):
    def test_a_real_worker_ignores_reserved_inputs_it_knows_and_those_it_does_not(self):
        w = RawWorker()
        try:
            reserved = {
                "_calibration": {
                    "pixel_size": {"of": "image", "x": {"value": 0.5, "unit": "um", "source": "user"}}
                },
                "_axes": {"image": "YX"},
                "_next_protocol_field": [1, 2, 3],
            }
            w.send(execute("r", "defaults", reserved))
            last = w.read_until("r")[-1]
            self.assertEqual(last["responseType"], "COMPLETION", last)
        finally:
            w.close()


if __name__ == "__main__":
    unittest.main()
