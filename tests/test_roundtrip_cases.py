"""The case matrix itself: unique ids, deterministic, and complete against the declared types and the example app.

The completeness checks read the declarations from the PRODUCTION code (types.py, introspection.py), so a new type, marker or
tool that nobody wrote a case for makes this file fail. The oracle checks pin the expectations the matrix is built on.
"""

import hashlib
import json
import unittest

import _paths  # noqa: F401  (must come first)
import numpy as np
import roundtrip_cases as rc

from labconstrictor_tools import types as T
from labconstrictor_tools.introspection import describe_tools


def schema_of_app():
    __import__(rc.APP_MODULE)
    return {t["id"]: t for t in describe_tools(rc.APP_MODULE)["tools"]}


def fingerprint(case):
    """A text that changes when the case changes in any way (arrays by content)."""

    def walk(value):
        if isinstance(value, np.ndarray):
            return [
                "array",
                str(value.dtype),
                list(value.shape),
                hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest(),
            ]
        if hasattr(value, "to_csv"):
            return ["frame", value.to_csv(index=False)]
        if hasattr(value, "__dataclass_fields__"):
            return [type(value).__name__] + [walk(getattr(value, f)) for f in value.__dataclass_fields__]
        if isinstance(value, dict):
            return {str(k): walk(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [walk(v) for v in value]
        return repr(value)

    return json.dumps(walk(case), sort_keys=True)


class CaseList(unittest.TestCase):
    def test_ids_are_unique(self):
        ids = [c.id for c in rc.all_cases()]
        self.assertEqual(
            sorted(set(ids)), sorted(ids), "duplicate ids: %s" % sorted({i for i in ids if ids.count(i) > 1})
        )

    def test_generation_is_deterministic(self):
        first = [fingerprint(c) for c in rc.all_cases()]
        rc.all_cases.cache_clear()
        second = [fingerprint(c) for c in rc.all_cases()]
        self.assertEqual(first, second)

    def test_every_case_names_a_tool_of_the_app_and_only_its_parameters(self):
        tools = schema_of_app()
        for case in rc.all_cases():
            with self.subTest(case.id):
                self.assertIn(case.tool, tools)
                known = {p["name"] for p in tools[case.tool]["inputs"]}
                self.assertLessEqual(set(case.send), known)
                outputs = {o["name"] for o in tools[case.tool]["outputs"]}
                self.assertLessEqual(set(case.expect.outputs), outputs)

    def test_every_tool_of_the_app_has_cases(self):
        used = {c.tool for c in rc.all_cases()}
        self.assertEqual(sorted(set(schema_of_app()) - used), [])

    def test_the_slow_transports_get_a_stated_share(self):
        for path, limits in rc.TRANSPORT_LIMITS.items():
            picked = rc.selected(path)
            self.assertGreater(len(picked), 20, path)
            self.assertLess(len(picked), 300, path)
            self.assertEqual(len({c.id for c in picked}), len(picked))
            self.assertTrue(all(path in c.paths for c in picked))
        self.assertEqual(len(rc.selected("worker")), len([c for c in rc.all_cases() if not c.heavy]))


class Completeness(unittest.TestCase):
    """Everything the package declares is walked by at least one case."""

    def setUp(self):
        self.tools = schema_of_app()
        self.cases = rc.all_cases()

    def used(self, key):
        """Values of `key` over the inputs/outputs of the tools that have cases."""
        used_tools = {c.tool for c in self.cases}
        return {
            x[key]
            for tool in used_tools
            for x in self.tools[tool]["inputs"] + self.tools[tool]["outputs"]
            if key in x
        }

    def test_every_input_and_output_type_is_covered(self):
        self.assertEqual(sorted(set(T.INPUT_TYPES.values()) - self.used("type")), [])
        self.assertEqual(sorted(set(T.OUTPUT_TYPES.values()) - self.used("type")), [])

    def test_every_scalar_hint_is_in_the_example_app(self):
        inputs = [p for t in self.tools.values() for p in t["inputs"]]
        self.assertTrue(any(p.get("widget") == "slider" for p in inputs))
        self.assertTrue(any(p.get("widget") == "radio" for p in inputs))
        self.assertTrue(any(p.get("nullable") for p in inputs))
        self.assertTrue(any("minimum" in p and "maximum" not in p for p in inputs))
        self.assertTrue(any("maximum" in p and "minimum" not in p for p in inputs))
        self.assertTrue(any(p.get("region_of") for p in inputs))
        self.assertTrue(
            any(p["type"] == "choice" and all(isinstance(c, int) for c in p["choices"]) for p in inputs)
        )
        self.assertTrue(any(o.get("display") for t in self.tools.values() for o in t["outputs"]))

    def test_the_dtype_lists_cover_every_kind_a_host_can_send(self):
        kinds = {np.dtype(d).kind for d in rc.DTYPES}
        self.assertEqual(kinds, set("biuf"))
        for name in ("uint8", "uint16", "int32", "float32", "float64", "bool"):
            self.assertIn(name, rc.DTYPES)
        ids = {c.id for c in self.cases}
        for shape in ("1x1", "1x7", "7x1", "2x3", "64x64", "3d-3x4x5"):
            self.assertIn("echo_image/uint8/%s" % shape, ids)
        self.assertTrue(any("fortran" in i for i in ids) and any("noncontiguous" in i for i in ids))

    def test_the_scalar_edges_the_task_names_are_present(self):
        ids = {c.id for c in self.cases}
        for name in (
            "echo_float/ok/-0x0.0p+0",
            "echo_float/ok/0x0.0000000000001p-1022",
            "echo_int/ok/9223372036854775807",
            "echo_int/ok/-9223372036854775808",
        ):
            self.assertIn(name, ids)
        for label in (
            "empty",
            "emoji",
            "rtl",
            "combining",
            "single-quote",
            "double-quote",
            "backslash",
            "newline",
            "tab",
            "long-200k",
            "shell-operators",
            "leading-trailing-spaces",
            "path-parent",
        ):
            self.assertIn("echo_string/text/%s" % label, ids)
        for bound in (
            "echo_bounded_int/ok/-5",
            "echo_bounded_int/ok/10",
            "echo_bounded_int/outside/-6",
            "echo_bounded_int/outside/11",
        ):
            self.assertIn(bound, ids)

    def test_every_choice_of_every_choice_tool_has_a_case(self):
        sent = {}
        for case in self.cases:
            if case.expect.status == "COMPLETE":
                for name, value in case.send.items():
                    sent.setdefault((case.tool, name), []).append(value)
        for tool_id, tool in self.tools.items():
            for param in tool["inputs"]:
                if param["type"] == "choice":
                    for choice in param["choices"]:
                        values = sent.get((tool_id, param["name"]), [])
                        self.assertTrue(
                            any(type(v) is type(choice) and v == choice for v in values),
                            "%s.%s: choice %r has no case" % (tool_id, param["name"], choice),
                        )


class Oracle(unittest.TestCase):
    """The expectations are the documented rules (docs/PROTOCOL.md), written out once, here."""

    def test_booleans_become_bytes_and_floats_become_float32(self):
        out = rc.expected_image_out(np.array([[True, False]]))
        self.assertEqual(out.dtypes, ("uint8",))
        self.assertEqual(out.values.tolist(), [[1, 0]])
        out = rc.expected_image_out(np.array([0.1], np.float64))
        self.assertEqual(out.dtypes, ("float32",))
        self.assertEqual(out.values[0], np.float32(0.1))
        self.assertIsNone(rc.expected_image_out(np.array([1e39])))

    def test_integers_never_change_in_value(self):
        self.assertEqual(rc.expected_image_out(np.array([0, 65535], np.int32)).dtypes, ("uint16", "int16"))
        self.assertEqual(rc.expected_image_out(np.array([-5, 5], np.int64)).dtypes, ("uint16", "int16"))
        self.assertEqual(rc.expected_image_out(np.array([2**24], np.int32)).dtypes, ("float32",))
        self.assertIsNone(rc.expected_image_out(np.array([2**24 + 1], np.int32)))
        self.assertIsNone(rc.expected_image_out(np.array([2**64 - 1], np.uint64)))
        self.assertEqual(rc.expected_image_out(np.array([200], np.uint8)).dtypes, ("uint8",))

    def test_the_ramp_is_asymmetric_and_fits_its_dtype(self):
        for dtype in rc.DTYPES:
            a = rc.ramp((6, 6), dtype)
            self.assertEqual(str(a.dtype), dtype)
            self.assertFalse(np.array_equal(a, a.T), dtype)
            if a.dtype.kind in "iu":
                self.assertGreaterEqual(int(a.min()), int(np.iinfo(a.dtype).min))

    def test_the_report_of_an_array_is_its_content_digest(self):
        a = np.arange(6, dtype=np.uint16).reshape(2, 3)
        report = rc.array_report(np.asfortranarray(a))
        self.assertEqual(report["digest"], hashlib.sha256(np.arange(6, dtype="<u2").tobytes()).hexdigest())
        self.assertEqual(report["shape"], [2, 3])


if __name__ == "__main__":
    unittest.main()
