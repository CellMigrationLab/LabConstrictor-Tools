"""Schema hints, generated from the marker list of types.py: every combination that introspection accepts gives a schema that
obeys docs/MANIFEST.md and docs/PROTOCOL.md (checked by `manifest_problems`, written here from those documents), and every
invalid combination is refused with a message that names the parameter.

The tools are built from annotations at run time and declared through the real `@tool` decorator, then described by the real
`describe_tools`; nothing here calls the validators under test, and the rules come from the documents, not from the code.
"""

import enum
import inspect
import itertools
import json
import unittest
from pathlib import Path
from typing import Annotated, Any, Literal

import _paths  # noqa: F401  (must come first)
import roundtrip_app
import roundtrip_cases as rc
from roundtrip_known_failures import KNOWN, is_known

from labconstrictor_tools import convert, decorators
from labconstrictor_tools import types as T
from labconstrictor_tools.introspection import DeclarationError, describe_tools
from labconstrictor_tools.types import ToolError

REQUIRED = inspect.Parameter.empty


class Color3(enum.Enum):
    A = "a"
    B = "b"
    C = "c"


# base label -> (annotation, schema type, is a number, is a choice, number of choices, is a file-like input)
BASES: dict[str, tuple[Any, str]] = {
    "int": (int, "integer"),
    "float": (float, "float"),
    "str": (str, "string"),
    "bool": (bool, "boolean"),
    "literal3": (Literal["a", "b", "c"], "choice"),
    "literal2": (Literal["a", "b"], "choice"),
    "literal7": (Literal["a", "b", "c", "d", "e", "f", "g"], "choice"),
    "enum3": (Color3, "choice"),
    "image": (T.Image, "image"),
    "labels": (T.Labels, "labels"),
    "table": (T.Table, "table"),
    "file": (T.File, "file"),
    "folder": (T.Folder, "folder"),
    "path": (Path, "file"),
}
NUMERIC = ("int", "float")
CHOICES_2_TO_5 = ("literal3", "literal2", "enum3")
ALL = tuple(BASES)
DEFAULTS = {
    "int": 3,
    "float": 0.5,
    "str": "x",
    "bool": True,
    "literal3": "b",
    "literal2": "a",
    "literal7": "c",
    "enum3": Color3.B,
}

# ----------------------------------------------------------------------------------------------- the marker rules
# What each marker means (docs/MANIFEST.md) and where it applies. `makes` builds the marker, `fits` lists the bases it is valid
# on, `needs` names the markers that must accompany it, `effect` is what must appear in the parameter's schema.
INPUT_MARKERS: dict[str, dict[str, Any]] = {
    "Min": dict(makes=lambda: T.Min(0), fits=NUMERIC, needs=(), effect={"minimum": 0}),
    "Max": dict(makes=lambda: T.Max(10), fits=NUMERIC, needs=(), effect={"maximum": 10}),
    "Unit": dict(makes=lambda: T.Unit("um/px"), fits=NUMERIC, needs=(), effect={"unit": "um/px"}),
    "Description": dict(
        makes=lambda: T.Description("some help"), fits=ALL, needs=(), effect={"description": "some help"}
    ),
    "Label": dict(makes=lambda: T.Label("Nice name"), fits=ALL, needs=(), effect={"label": "Nice name"}),
    "Group": dict(makes=lambda: T.Group("Section"), fits=ALL, needs=(), effect={"group": "Section"}),
    "Advanced": dict(makes=lambda: T.Advanced(), fits=ALL, needs=(), effect={"advanced": True}),
    "ClearAfterRun": dict(
        makes=lambda: T.ClearAfterRun(), fits=ALL, needs=(), effect={"clear_after_run": True}
    ),
    "Collapsed": dict(
        makes=lambda: T.Collapsed(), fits=ALL, needs=("Group",), effect={"group_collapsed": True}
    ),
    "Widget:slider": dict(
        makes=lambda: T.Widget("slider"), fits=NUMERIC, needs=("Min", "Max"), effect={"widget": "slider"}
    ),
    "Widget:radio": dict(
        makes=lambda: T.Widget("radio"), fits=CHOICES_2_TO_5, needs=(), effect={"widget": "radio"}
    ),
    "EnabledWhen": dict(
        makes=lambda: T.EnabledWhen("other"), fits=ALL, needs=(), effect={"enabled_when": {"param": "other"}}
    ),
    "PixelSizeOf": dict(
        makes=lambda: T.PixelSizeOf("image"), fits=("float",), needs=(), effect={"pixel_size_of": "image"}
    ),
    "Axes": dict(makes=lambda: T.Axes("YX"), fits=("image", "labels"), needs=(), effect={"axes": "YX"}),
    "PickChannel": dict(
        makes=lambda: T.PickChannel(), fits=("image",), needs=(), effect={"pick_channel": True}
    ),
    "RegionOf": dict(
        makes=lambda: T.RegionOf("image"),
        fits=("labels",),
        needs=(),
        effect={"region_of": "image"},
        optional_only=True,
    ),
    "ChoicesFrom": dict(
        makes=lambda: T.ChoicesFrom("src"),
        fits=("str",),
        needs=(),
        effect={"choices_from": {"tool": "src", "depends": [], "field": "choices"}},
    ),
}
OUTPUT_MARKERS: dict[str, dict[str, Any]] = {
    "Name": dict(
        makes=lambda: T.Name("renamed"),
        fits=(
            "ImageOut",
            "LabelsOut",
            "TableOut",
            "Scalars",
            "MessageOut",
            "FileOut",
            "Affine",
            "PointsOut",
            "ShapesOut",
        ),
    ),
    "Replace": dict(
        makes=lambda: T.Replace(),
        fits=("ImageOut", "LabelsOut", "TableOut", "Affine", "PointsOut", "ShapesOut"),
    ),
    "Axes": dict(makes=lambda: T.Axes("YX"), fits=("ImageOut", "LabelsOut")),
    "ApplyTo": dict(makes=lambda: T.ApplyTo("image"), fits=("Affine", "PointsOut", "ShapesOut")),
}
OUTPUT_TYPES = {
    "ImageOut": T.ImageOut,
    "LabelsOut": T.LabelsOut,
    "TableOut": T.TableOut,
    "Scalars": T.Scalars,
    "MessageOut": T.MessageOut,
    "FileOut": T.FileOut,
    "Affine": T.Affine,
    "PointsOut": T.PointsOut,
    "ShapesOut": T.ShapesOut,
}
# markers whose misuse the documents call an error but that are not input markers on every base: Widget has two forms
MARKER_CLASSES = {
    "Min",
    "Max",
    "Unit",
    "Description",
    "Label",
    "Group",
    "Advanced",
    "ClearAfterRun",
    "Collapsed",
    "Widget",
    "EnabledWhen",
    "PixelSizeOf",
    "Axes",
    "PickChannel",
    "RegionOf",
    "ChoicesFrom",
    "Name",
    "Replace",
    "ApplyTo",
}


def discovered_markers():
    """Every marker class types.py defines: subclasses of its marker base, plus the three that carry several values."""
    found = {
        n
        for n, c in vars(T).items()
        if inspect.isclass(c) and issubclass(c, T._Marker) and c is not T._Marker
    }
    return found | {"EnabledWhen", "ChoicesFrom", "ApplyTo"}


# ------------------------------------------------------------------------------------------------ building tools
COUNTER = itertools.count(1)


def declare(params, returns=None, extra=(), module=None):
    """Declare a tool (and `extra` ones) from annotations through the real @tool decorator -> (module name, its tool id)."""
    module = module or "lc_generated_hints_%d" % next(COUNTER)

    def make(name, plist, ret):
        def fn(*args, **kwargs):
            return None

        fn.__name__ = fn.__qualname__ = name
        fn.__module__ = module
        fn.__annotations__ = {n: a for n, a, _ in plist}
        if ret is not None:
            fn.__annotations__["return"] = ret
        fn.__signature__ = inspect.Signature(
            [
                inspect.Parameter(n, inspect.Parameter.POSITIONAL_OR_KEYWORD, default=d, annotation=a)
                for n, a, d in plist
            ],
            return_annotation=ret if ret is not None else inspect.Signature.empty,
        )
        decorators.tool(name)(fn)

    try:
        make("subject", params, returns)
        for name, plist, ret in extra:
            make(name, plist, ret)
    except BaseException:
        decorators.forget_module(module)
        raise
    return module


def describe(module):
    try:
        return describe_tools(module)
    finally:
        decorators.forget_module(module)


def companions():
    """The parameters around the one under test: an image to refer to, a flag to depend on."""
    return [("image", T.Image, REQUIRED)], [("other", bool, False)]


def under_test(base, optional, markers):
    annotation = BASES[base][0]
    default = REQUIRED
    if optional:  # True: `T | None = None`; "bare": `T | None` with no default (optional all the same)
        annotation = annotation | None  # type: ignore[operator]
        default = None if optional is True else REQUIRED
    if markers:
        annotation = Annotated[(annotation, *markers)]
    return ("p", annotation, default)


def source_tool():
    return ("src", [("q", str, "q")], T.Scalars)


def schema_for(base, optional, marker_names, with_default=False):
    markers = [INPUT_MARKERS[n]["makes"]() for n in marker_names]
    first, last = companions()
    p = under_test(base, optional, markers)
    if with_default and base in DEFAULTS and not optional:
        p = (p[0], p[1], DEFAULTS[base])
    module = declare(first + [p] + last, extra=[source_tool()])
    schema = describe(module)
    return {t["id"]: t for t in schema["tools"]}["subject"], schema


# --------------------------------------------------------------------------------- the validator, from the documents
INPUT_TYPE_NAMES = {
    "string",
    "integer",
    "float",
    "boolean",
    "choice",
    "image",
    "labels",
    "table",
    "file",
    "folder",
}
OUTPUT_TYPE_NAMES = {"image", "labels", "table", "values", "affine", "file", "message", "points", "shapes"}


def manifest_problems(tool):
    """Every way a tool schema breaks the semantics of docs/MANIFEST.md and docs/PROTOCOL.md (empty list: it conforms)."""
    problems = []
    by_name = {i["name"]: i for i in tool["inputs"]}
    if len(by_name) != len(tool["inputs"]):
        problems.append("duplicate input names")
    for i in tool["inputs"]:
        n = i["name"]
        if i["type"] not in INPUT_TYPE_NAMES:
            problems.append("%s: unknown type %r" % (n, i["type"]))
        if not isinstance(i.get("label"), str) or not i["label"]:
            problems.append("%s: no label" % n)
        if not isinstance(i.get("required"), bool):
            problems.append("%s: required must be true/false" % n)
        if i.get("nullable") and (i["required"] or "default" in i):
            problems.append("%s: nullable means optional with no default value" % n)
        if not i["required"] and "default" not in i and not i.get("nullable"):
            problems.append("%s: optional without default must be nullable" % n)
        numeric = i["type"] in ("integer", "float")
        for key in ("minimum", "maximum", "unit", "pixel_size_of"):
            if key in i and not numeric:
                problems.append("%s: %s on a %s" % (n, key, i["type"]))
        if "minimum" in i and "maximum" in i and i["minimum"] > i["maximum"]:
            problems.append("%s: minimum above maximum" % n)
        if numeric and "default" in i:
            if (
                "minimum" in i
                and i["default"] < i["minimum"]
                or "maximum" in i
                and i["default"] > i["maximum"]
            ):
                problems.append("%s: default outside the bounds" % n)
        if i["type"] == "choice":
            if not i.get("choices"):
                problems.append("%s: a choice without choices" % n)
            elif "default" in i and i["default"] not in i["choices"]:
                problems.append("%s: default is not one of the choices" % n)
        elif "choices" in i:
            problems.append("%s: choices on a %s" % (n, i["type"]))
        widget = i.get("widget")
        if widget == "slider" and not (numeric and "minimum" in i and "maximum" in i):
            problems.append("%s: a slider needs a number with Min and Max" % n)
        if widget == "radio" and not (i["type"] == "choice" and 2 <= len(i.get("choices", [])) <= 5):
            problems.append("%s: radio buttons need 2 to 5 choices" % n)
        if widget not in (None, "slider", "radio"):
            problems.append("%s: unknown widget %r" % (n, widget))
        if i.get("group_collapsed") and "group" not in i:
            problems.append("%s: Collapsed needs a Group" % n)
        if "pixel_size_of" in i and (
            i["type"] != "float" or by_name.get(i["pixel_size_of"], {}).get("type") != "image"
        ):
            problems.append("%s: PixelSizeOf must be a float naming an Image parameter" % n)
        if "region_of" in i and not (
            i["type"] == "labels"
            and not i["required"]
            and by_name.get(i["region_of"], {}).get("type") == "image"
        ):
            problems.append("%s: RegionOf is an optional Labels input naming an Image parameter" % n)
        if i.get("pick_channel") and not (i["type"] == "image" and i.get("axes") in (None, "YX")):
            problems.append("%s: PickChannel is for an Image input of a 2D tool" % n)
        if "axes" in i and i["type"] not in ("image", "labels"):
            problems.append("%s: axes on a %s" % (n, i["type"]))
        rule = i.get("enabled_when")
        if rule is not None and (rule.get("param") not in by_name or rule["param"] == n):
            problems.append("%s: EnabledWhen must name another parameter" % n)
        if "choices_from" in i and (
            i["type"] != "string" or set(i["choices_from"]) != {"tool", "depends", "field"}
        ):
            problems.append("%s: ChoicesFrom is for a string and has tool, depends and field" % n)
    names = [o["name"] for o in tool["outputs"]]
    if len(set(names)) != len(names):
        problems.append("duplicate output names")
    for o in tool["outputs"]:
        if o["type"] not in OUTPUT_TYPE_NAMES:
            problems.append("output %s: unknown type %r" % (o["name"], o["type"]))
        if o.get("replace") and o["type"] not in ("image", "labels", "table", "affine", "points", "shapes"):
            problems.append("output %s: Replace on a %s" % (o["name"], o["type"]))
        for key in ("apply_to", "relative_to"):
            if key in o.get("display", {}) and o["display"][key] not in by_name:
                problems.append("output %s: %s names no parameter" % (o["name"], key))
        if "axes" in o and o["type"] not in ("image", "labels"):
            problems.append("output %s: axes on a %s" % (o["name"], o["type"]))
    try:
        json.dumps(tool, allow_nan=False)
    except ValueError:
        problems.append("the schema is not strict JSON")
    return problems


# ------------------------------------------------------------------------------------------------- valid combinations
def valid_marker_pool(base, optional):
    pool = []
    for name, rule in INPUT_MARKERS.items():
        if base not in rule["fits"]:
            continue
        if rule.get("optional_only") and not optional:
            continue
        if name == "Widget:radio" and base == "literal7":
            continue
        pool.append(name)
    return pool


def with_needs(names):
    out = list(names)
    for n in names:
        for need in INPUT_MARKERS[n]["needs"]:
            if need not in out:
                out.append(need)
    return out


def valid_combinations():
    """Every pair of applicable markers (companions added), every single one, and all of them together, for every base."""
    for base in ALL:
        for optional in (False, True, "bare"):
            pool = valid_marker_pool(base, optional)
            subsets = (
                [()]
                + [(a,) for a in pool]
                + list(itertools.combinations(pool, 2))
                + ([tuple(pool)] if len(pool) > 2 else [])
            )
            for subset in subsets:
                yield base, optional, tuple(with_needs(subset))


class ValidCombinations(unittest.TestCase):
    def test_every_accepted_combination_obeys_the_manifest(self):
        count = 0
        for base, optional, names in valid_combinations():
            label = "%s%s+%s" % (
                base,
                {False: "", True: "?", "bare": "?(no default)"}[optional],
                "+".join(names) or "none",
            )
            with self.subTest(label):
                tool, _ = schema_for(base, optional, names)
                self.assertEqual(manifest_problems(tool), [], label)
                param = {i["name"]: i for i in tool["inputs"]}["p"]
                self.assertEqual(param["type"], BASES[base][1])
                self.assertEqual(param["required"], not optional)
                self.assertEqual(bool(param.get("nullable")), bool(optional))
                if optional:
                    self.assertNotIn("default", param)
                for n in names:
                    for key, value in INPUT_MARKERS[n]["effect"].items():
                        self.assertEqual(param.get(key), value, "%s: %s" % (label, key))
                hint_keys = {
                    "minimum",
                    "maximum",
                    "unit",
                    "group",
                    "advanced",
                    "clear_after_run",
                    "group_collapsed",
                    "widget",
                    "enabled_when",
                    "pixel_size_of",
                    "pick_channel",
                    "region_of",
                    "choices_from",
                    "description",
                }
                expected = {k for n in names for k in INPUT_MARKERS[n]["effect"]}
                self.assertEqual(
                    sorted(k for k in param if k in hint_keys and k != "description"),
                    sorted(k for k in expected if k in hint_keys and k != "description"),
                    label,
                )
            count += 1
        self.assertGreater(count, 200)

    def test_bounds_declared_by_min_and_max_are_enforced_by_the_converter(self):
        """Min and Max are 'bounds, enforced everywhere': the converter must refuse the neighbours and accept the bounds."""
        for base in NUMERIC:
            for names in (("Min",), ("Max",), ("Min", "Max"), ("Min", "Max", "Widget:slider")):
                tool, _ = schema_for(base, False, names)
                kind = float if base == "float" else int
                step = 1e-9 if base == "float" else 1
                bounds = {}
                if "Min" in names:
                    bounds["lo"] = 0
                if "Max" in names:
                    bounds["hi"] = 10
                with self.subTest(base=base, names=names):
                    if "lo" in bounds:
                        self.assertEqual(
                            convert.load_inputs(_without_image(tool), {"p": kind(0)})["p"], kind(0)
                        )
                        with self.assertRaises(ToolError) as caught:
                            convert.load_inputs(_without_image(tool), {"p": kind(0) - kind(step)})
                        self.assertEqual(caught.exception.code, "invalid_parameter")
                    if "hi" in bounds:
                        self.assertEqual(
                            convert.load_inputs(_without_image(tool), {"p": kind(10)})["p"], kind(10)
                        )
                        with self.assertRaises(ToolError) as caught:
                            convert.load_inputs(_without_image(tool), {"p": kind(10) + kind(step)})
                        self.assertEqual(caught.exception.code, "invalid_parameter")

    def test_defaults_travel_into_the_schema_and_must_be_valid(self):
        for base in DEFAULTS:
            tool, _ = schema_for(base, False, ())
            self.assertEqual(manifest_problems(tool), [])
            tool, _ = schema_for(base, False, (), with_default=True)
            param = {i["name"]: i for i in tool["inputs"]}["p"]
            expected = DEFAULTS[base].value if isinstance(DEFAULTS[base], enum.Enum) else DEFAULTS[base]
            self.assertEqual(param["default"], expected)
            self.assertFalse(param["required"])
            self.assertEqual(manifest_problems(tool), [])

    def test_outputs_with_their_markers(self):
        for out_name, rule in OUTPUT_MARKERS.items():
            for type_name in rule["fits"]:
                label = "%s on %s" % (out_name, type_name)
                with self.subTest(label):
                    annotation = Annotated[OUTPUT_TYPES[type_name], rule["makes"]()]
                    module = declare([("image", T.Image, REQUIRED)], annotation)
                    tool = {t["id"]: t for t in describe(module)["tools"]}["subject"]
                    self.assertEqual(manifest_problems(tool), [], label)
                    output = tool["outputs"][0]
                    if out_name == "Name":
                        self.assertEqual(output["name"], "renamed")
                    if out_name == "Replace":
                        self.assertTrue(output["replace"])
                    if out_name == "Axes":
                        self.assertEqual(output["axes"], "YX")
                    if out_name == "ApplyTo":
                        self.assertEqual(output["display"], {"apply_to": "image"})

    def test_the_marker_table_covers_every_marker_in_types_py(self):
        in_table = {n.split(":")[0] for n in INPUT_MARKERS} | set(OUTPUT_MARKERS)
        self.assertEqual(
            sorted(discovered_markers() - in_table), [], "a marker of types.py has no generated combinations"
        )
        self.assertEqual(sorted(in_table - discovered_markers()), [])
        self.assertEqual(discovered_markers(), MARKER_CLASSES)
        self.assertEqual(set(T.WIDGETS), {"slider", "radio"})

    def test_example_apps_conform_to_the_manifest(self):
        for module in (
            "labconstrictor_tools.examples.synthetic",
            "labconstrictor_tools.examples.interactions",
            rc.APP_MODULE,
        ):
            tools = roundtrip_app.schemas(module)
            self.assertGreater(len(tools), 3, module)
            for tool in tools.values():
                with self.subTest("%s %s" % (module, tool["id"])):
                    self.assertEqual(manifest_problems(tool), [])

    def test_the_schema_is_deterministic(self):
        first = schema_for("float", True, ("Min", "Max", "Unit", "Widget:slider", "Group", "Collapsed"))[1]
        second = schema_for("float", True, ("Min", "Max", "Unit", "Widget:slider", "Group", "Collapsed"))[1]
        self.assertEqual(json.dumps(first, sort_keys=False), json.dumps(second, sort_keys=False))

    def test_hint_pairs_in_both_orders_give_the_same_schema(self):
        pool = valid_marker_pool("float", False)
        for a, b in itertools.combinations(pool, 2):
            names_ab, names_ba = with_needs((a, b)), with_needs((b, a))
            with self.subTest("%s,%s" % (a, b)):
                ab = {i["name"]: i for i in schema_for("float", False, names_ab)[0]["inputs"]}["p"]
                ba = {i["name"]: i for i in schema_for("float", False, names_ba)[0]["inputs"]}["p"]
                self.assertEqual(ab, ba)


class TheValidatorHasTeeth(unittest.TestCase):
    """manifest_problems must flag each rule it states: a schema broken in exactly one way gives exactly that complaint."""

    GOOD = {
        "id": "t",
        "label": "T",
        "inputs": [
            {"name": "image", "label": "Image", "type": "image", "required": True},
            {
                "name": "n",
                "label": "N",
                "type": "float",
                "required": True,
                "minimum": 0,
                "maximum": 5,
                "widget": "slider",
            },
            {
                "name": "c",
                "label": "C",
                "type": "choice",
                "required": False,
                "choices": ["a", "b"],
                "default": "a",
                "widget": "radio",
            },
        ],
        "outputs": [{"name": "m", "type": "affine", "display": {"apply_to": "image"}}],
    }

    def broken(self, **changes):
        tool = json.loads(json.dumps(self.GOOD))
        for path, value in changes.items():
            target = tool
            *parents, last = path.split(".")
            for part in parents:
                target = target[int(part)] if part.isdigit() else target[part]
            if value is None:
                del target[int(last) if last.isdigit() else last]
            else:
                target[int(last) if last.isdigit() else last] = value
        return manifest_problems(tool)

    def test_the_good_schema_is_clean(self):
        self.assertEqual(manifest_problems(self.GOOD), [])

    def test_each_rule_is_enforced(self):
        rules = {
            "inputs.1.maximum": (-1, "minimum above maximum"),
            "inputs.1.default": (9, "default outside the bounds"),
            "inputs.1.minimum": (None, "slider needs"),
            "inputs.2.choices": (["a"], "radio buttons"),
            "inputs.2.default": ("z", "not one of the choices"),
            "inputs.0.group_collapsed": (True, "Collapsed needs a Group"),
            "inputs.0.pixel_size_of": ("n", "PixelSizeOf"),
            "inputs.1.region_of": ("image", "RegionOf"),
            "inputs.0.enabled_when": ({"param": "image"}, "EnabledWhen"),
            "inputs.0.type": ("number", "unknown type"),
            "inputs.1.choices_from": ({"tool": "x"}, "ChoicesFrom"),
            "outputs.0.display": ({"apply_to": "nothing"}, "names no parameter"),
        }
        for path, (value, fragment) in rules.items():
            with self.subTest(path):
                problems = self.broken(**{path: value})
                self.assertTrue(any(fragment in p for p in problems), problems)

    def test_nan_in_a_schema_is_not_strict_json(self):
        self.assertTrue(any("strict JSON" in p for p in self.broken(**{"inputs.1.default": float("nan")})))


def _without_image(tool):
    return {**tool, "inputs": [i for i in tool["inputs"] if i["name"] == "p"]}


# ----------------------------------------------------------------------------------------- invalid combinations
class Cell:
    """One invalid declaration: how to build it, what it is called, and the exception that must refuse it."""

    def __init__(self, cell_id, build, why, errors=(DeclarationError,)):
        self.id, self.build, self.why, self.errors = cell_id, build, why, errors


def refused(cell):
    """The text of the error that refuses the declaration, or None when it is accepted."""
    try:
        cell.build()
    except cell.errors as error:
        return str(error)
    return None


def _param_cell(cell_id, base, optional, names, why, **kwargs):
    return Cell(cell_id, lambda: schema_for(base, optional, names, **kwargs), why)


def invalid_cells():
    cells = []
    not_numeric = ("str", "bool", "literal3", "image", "file")
    for marker in ("Min", "Max"):
        for base in not_numeric:
            cells.append(
                _param_cell("%s-on-%s" % (marker, base), base, False, (marker,), "bounds apply to numbers")
            )
    for base in ("str", "bool", "image", "file"):
        cells.append(
            _param_cell(
                "Widget:slider-on-%s" % base, base, False, ("Widget:slider",), "a slider is a bounded number"
            )
        )
    cells.append(
        _param_cell(
            "Widget:slider-without-bounds", "int", False, ("Widget:slider",), "a slider needs Min and Max"
        )
    )
    cells.append(
        _param_cell(
            "Widget:slider-without-max", "int", False, ("Widget:slider", "Min"), "a slider needs Min and Max"
        )
    )
    cells.append(
        _param_cell(
            "Widget:slider-without-min",
            "float",
            False,
            ("Widget:slider", "Max"),
            "a slider needs Min and Max",
        )
    )
    for base in ("literal7", "int", "str", "bool", "image"):
        cells.append(
            _param_cell(
                "Widget:radio-on-%s" % base,
                base,
                False,
                ("Widget:radio",),
                "radio buttons are 2 to 5 choices",
            )
        )
    for base in ("str", "int", "image", "table"):
        cells.append(
            _param_cell(
                "RegionOf-on-%s" % base, base, True, ("RegionOf",), "RegionOf is for an optional Labels input"
            )
        )
    cells.append(
        _param_cell(
            "RegionOf-on-required-labels",
            "labels",
            False,
            ("RegionOf",),
            "RegionOf is for an OPTIONAL Labels input",
        )
    )
    for base in ("int", "bool", "literal3", "image", "file"):
        cells.append(
            _param_cell(
                "ChoicesFrom-on-%s" % base, base, False, ("ChoicesFrom",), "ChoicesFrom is for a string"
            )
        )
    for base in ("str", "int", "labels", "table"):
        cells.append(
            _param_cell(
                "PickChannel-on-%s" % base, base, False, ("PickChannel",), "PickChannel is for an Image"
            )
        )
    cells.append(
        Cell(
            "Collapsed-without-Group",
            lambda: schema_for("str", False, ("Collapsed",)),
            "Collapsed needs a Group",
        )
    )
    cells.append(
        Cell(
            "PickChannel-with-ZYX",
            lambda: _custom("p", Annotated[T.Image, T.PickChannel(), T.Axes("ZYX")]),
            "PickChannel gives a 2D channel",
        )
    )
    cells.append(
        Cell(
            "EnabledWhen-unknown-parameter",
            lambda: _custom("p", Annotated[str | None, T.EnabledWhen("nothing")], default=None),
            "EnabledWhen names no parameter",
        )
    )
    cells.append(
        Cell(
            "EnabledWhen-itself",
            lambda: _custom("p", Annotated[str | None, T.EnabledWhen("p")], default=None),
            "a parameter cannot enable itself",
        )
    )
    cells.append(
        Cell(
            "PixelSizeOf-unknown-parameter",
            lambda: _custom("p", Annotated[float, T.PixelSizeOf("nothing")]),
            "PixelSizeOf names no parameter",
        )
    )
    cells.append(
        Cell(
            "RegionOf-unknown-parameter",
            lambda: _custom("p", Annotated[T.Labels | None, T.RegionOf("nothing")], default=None),
            "RegionOf names no parameter",
        )
    )
    cells.append(
        Cell(
            "RegionOf-names-a-non-image",
            lambda: _custom("p", Annotated[T.Labels | None, T.RegionOf("other")], default=None),
            "RegionOf names an Image",
        )
    )
    cells.append(
        Cell(
            "Optional-with-a-default",
            lambda: _custom("p", int | None, default=3),
            "Optional with a non-None default cannot be expressed",
        )
    )
    cells.append(
        Cell(
            "default-below-minimum",
            lambda: _custom("p", Annotated[int, T.Min(5)], default=1),
            "the default violates Min",
        )
    )
    cells.append(
        Cell(
            "default-above-maximum",
            lambda: _custom("p", Annotated[float, T.Max(1.0)], default=2.0),
            "the default violates Max",
        )
    )
    cells.append(
        Cell("default-of-the-wrong-type", lambda: _custom("p", int, default="x"), "the default is not an int")
    )
    cells.append(
        Cell(
            "default-not-a-choice",
            lambda: _custom("p", Literal["a", "b"], default="c"),
            "the default is not a choice",
        )
    )
    cells.append(Cell("unsupported-annotation", lambda: _custom("p", list), "unsupported annotation"))
    cells.append(
        Cell(
            "duplicate-output-names",
            lambda: _custom_out(
                tuple[Annotated[T.ImageOut, T.Name("same")], Annotated[T.TableOut, T.Name("same")]]
            ),
            "output names must differ",
        )
    )
    for type_name in ("Scalars", "MessageOut", "FileOut"):
        cells.append(
            Cell(
                "Replace-on-%s" % type_name,
                lambda t=type_name: _custom_out(Annotated[OUTPUT_TYPES[t], T.Replace()]),
                "Replace is for results that can be replaced",
            )
        )
    cells.append(
        Cell(
            "ApplyTo-unknown-parameter",
            lambda: _custom_out(Annotated[T.Affine, T.ApplyTo("nothing")]),
            "ApplyTo names no parameter",
        )
    )
    cells.append(
        Cell(
            "ApplyTo-relative-to-unknown-parameter",
            lambda: _custom_out(Annotated[T.Affine, T.ApplyTo("image", "nothing")]),
            "relative_to names no parameter",
        )
    )
    cells.append(
        Cell(
            "ChoicesFrom-unknown-tool",
            lambda: _custom("p", Annotated[str, T.ChoicesFrom("nothing")]),
            "ChoicesFrom names no tool",
        )
    )
    cells.append(
        Cell(
            "ChoicesFrom-itself",
            lambda: _custom("p", Annotated[str, T.ChoicesFrom("subject")]),
            "ChoicesFrom cannot be the tool itself",
        )
    )
    cells.append(
        Cell(
            "ChoicesFrom-source-without-Scalars",
            lambda: _custom("p", Annotated[str, T.ChoicesFrom("plain")], extra=[("plain", [], T.MessageOut)]),
            "the source must return Scalars",
        )
    )
    cells.append(
        Cell(
            "ChoicesFrom-depends-missing-in-source",
            lambda: _custom("p", Annotated[str, T.ChoicesFrom("src", depends=["nope"])]),
            "depends names a parameter of both tools",
        )
    )
    cells.append(
        Cell(
            "ChoicesFrom-source-needs-a-parameter",
            lambda: _custom(
                "p",
                Annotated[str, T.ChoicesFrom("src")],
                extra=[("src", [("must", int, REQUIRED)], T.Scalars)],
            ),
            "the source has a required parameter that is not in depends",
        )
    )
    cells.append(
        Cell(
            "Widget-unknown-form",
            lambda: T.Widget("dial"),
            "only slider and radio exist",
            errors=(ValueError,),
        )
    )
    # accepted today although the documents say the combination is meaningless
    for base in ("str", "int", "table", "file"):
        cells.append(
            _param_cell(
                "Axes-on-%s" % base, base, False, ("Axes",), "axes describe the dimensions of an image"
            )
        )
    for base in ("int", "str", "bool"):
        cells.append(
            _param_cell("PixelSizeOf-on-%s" % base, base, False, ("PixelSizeOf",), "PixelSizeOf is a float")
        )
    cells.append(
        Cell("Min-above-Max", lambda: _custom("p", Annotated[int, T.Min(5), T.Max(1)]), "the range is empty")
    )
    cells.append(
        Cell(
            "Min-is-not-a-number",
            lambda: _custom("p", Annotated[int, T.Min("a")]),
            "the bound is not a number",
        )
    )
    for marker, make in (
        ("Name", lambda: T.Name("x")),
        ("Replace", lambda: T.Replace()),
        ("ApplyTo", lambda: T.ApplyTo("image")),
    ):
        for base in ("str", "image"):
            cells.append(
                Cell(
                    "%s-on-the-input-%s" % (marker, base),
                    lambda m=make, b=base: _custom("p", Annotated[BASES[b][0], m()]),
                    "%s is an output marker" % marker,
                )
            )
    return cells


def _custom(name, annotation, default=REQUIRED, extra=None):
    first = [("image", T.Image, REQUIRED)]
    module = declare(
        first + [(name, annotation, default), ("other", bool, False)],
        extra=[source_tool()] if extra is None else extra,
    )
    return describe(module)


def _custom_out(annotation):
    module = declare([("image", T.Image, REQUIRED)], annotation)
    return describe(module)


class InvalidCombinations(unittest.TestCase):
    def test_every_invalid_combination_is_refused_with_a_message_that_names_the_culprit(self):
        cells = invalid_cells()
        self.assertGreater(len(cells), 70)
        self.assertEqual(len({c.id for c in cells}), len(cells))
        for cell in cells:
            if is_known("hint:" + cell.id):
                continue
            with self.subTest(cell.id):
                message = refused(cell)
                self.assertIsNotNone(message, "accepted: %s" % cell.why)
                self.assertGreater(len(message), 15, "a readable message, not a bare error")
                self.assertTrue(
                    any(
                        word in message
                        for word in (
                            "'p'",
                            "'subject'",
                            "Widget",
                            "'image'",
                            "output",
                            "apply_to",
                            "ChoicesFrom",
                            "tool",
                            "Optional",
                            "default",
                            "PickChannel",
                            "RegionOf",
                            "EnabledWhen",
                            "PixelSizeOf",
                            "Collapsed",
                            "annotation",
                            "unsupported",
                        )
                    ),
                    "the message names neither the parameter nor the hint: %r" % message,
                )

    def test_a_refusal_is_a_declaration_error_and_never_a_crash(self):
        for cell in invalid_cells():
            if is_known("hint:" + cell.id):
                continue
            try:
                cell.build()
            except cell.errors:
                continue
            except Exception as error:  # noqa: BLE001 - the point of the test: any other exception is a crash
                self.fail("%s: %s: %s" % (cell.id, type(error).__name__, error))

    def test_known_misuse_still_accepted_is_listed(self):
        listed = {k.split(":", 1)[1] for k in KNOWN if k.startswith("hint:")}
        self.assertLessEqual(listed, {c.id for c in invalid_cells()})


if __name__ == "__main__":
    unittest.main()
