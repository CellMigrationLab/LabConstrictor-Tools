"""Notebook form: an optional parameter can be left unset (F9) and numbers are never clamped silently (F8)."""

import unittest
from typing import Annotated

import _paths  # noqa: F401  (must come first)

from labconstrictor_tools import Max, Min, Scalars, tool
from labconstrictor_tools.notebook import MAX_FORM_INTEGER, ToolForm

try:
    import ipywidgets  # noqa: F401

    HAVE_WIDGETS = True
except ImportError:
    HAVE_WIDGETS = False


@tool("Optional things")
def optional_things(
    n: int | None = None,
    x: float | None = None,
    s: str | None = None,
    flag: bool | None = None,
    big: int = 0,
    bounded: Annotated[int, Min(0), Max(10)] = 1,
) -> Scalars:
    return {"n": n, "x": x, "s": s, "flag": flag, "big": big, "bounded": bounded}


@unittest.skipUnless(HAVE_WIDGETS, "ipywidgets not installed")
class UnsetAndRange(unittest.TestCase):
    def received(self, form):
        results = form.run()
        self.assertIsNotNone(results, form.status.value)
        return results[0]["values"]

    def test_optional_parameters_start_unset_and_the_tool_receives_none(self):
        form = ToolForm(optional_things)
        self.assertEqual(set(form.set_toggles), {"n", "x", "s", "flag"})
        self.assertTrue(all(form.controls[k].disabled for k in form.set_toggles))
        got = self.received(form)
        self.assertEqual([got[k] for k in ("n", "x", "s", "flag")], [None] * 4)

    def test_ticking_set_sends_the_value_even_zero_empty_or_false(self):
        form = ToolForm(optional_things)
        for name in form.set_toggles:
            form.set_toggles[name].value = True
            self.assertFalse(form.controls[name].disabled)
        got = self.received(form)
        self.assertEqual([got[k] for k in ("n", "x", "s", "flag")], [0, 0.0, "", False])
        form.set_toggles["n"].value = False
        self.assertTrue(form.controls["n"].disabled)
        self.assertIsNone(self.received(form)["n"])

    def test_required_parameters_have_no_set_box(self):
        form = ToolForm(optional_things)
        self.assertNotIn("big", form.set_toggles)
        self.assertFalse(form.controls["big"].disabled)

    def test_numbers_beyond_a_billion_are_kept(self):
        form = ToolForm(optional_things)
        form.controls["big"].value = 3 * 10**9
        self.assertEqual(self.received(form)["big"], 3 * 10**9)

    def test_an_integer_the_form_cannot_hold_exactly_is_refused_with_a_message(self):
        form = ToolForm(optional_things)
        form.controls["big"].value = MAX_FORM_INTEGER + 1
        self.assertIsNone(form.run())
        self.assertIn("invalid_parameter", form.status.value)
        self.assertIn(str(MAX_FORM_INTEGER), form.status.value)
        form.controls["big"].value = MAX_FORM_INTEGER
        self.assertEqual(self.received(form)["big"], MAX_FORM_INTEGER)

    def test_a_declared_min_max_pair_is_still_enforced_by_the_box(self):
        form = ToolForm(optional_things)
        self.assertEqual(type(form.controls["bounded"]).__name__, "BoundedIntText")
        form.controls["bounded"].value = 99
        self.assertEqual(form.controls["bounded"].value, 10)


if __name__ == "__main__":
    unittest.main()
