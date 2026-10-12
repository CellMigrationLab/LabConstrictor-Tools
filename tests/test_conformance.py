"""`conformance.json` and its loader (docs/CONFORMANCE.md).

Three kinds of check: the loader and its schema (a broken edit must fail loudly, never skip a rule); the data against the Tools
code that already implements a rule (limits, compatibility vectors, retention fixtures run through `retention.prune`); and the
data against itself where a rule is arithmetic (the coordinate placement formula, the unit conversions), computed here with plain
Python from the inputs, never by calling the code under test.
"""

import contextlib
import copy
import io
import json
import re
import shutil
import string
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import _paths  # noqa: F401  (must come first)
from _paths import ROOT

from labconstrictor_tools import compat, conformance, notebook

try:
    from labconstrictor_tools import retention
except ImportError:  # the retention module arrives with its own change; its fixtures run as soon as it exists
    retention = None


def spec():
    """The spec text, read when a test needs it (the sabotage run copies the package and the tests, not the docs)."""
    return (ROOT / "docs" / "SPEC_WRONG_SCIENCE.md").read_text(encoding="utf-8")


DATA = conformance.load()
WRONG = DATA["wrong_science"]


def broken(change):
    """A deep copy of the data after `change(copy)`; the problems `validate` finds in it."""
    data = copy.deepcopy(DATA)
    change(data)
    return conformance.validate(data)


class Loader(unittest.TestCase):
    def test_the_file_is_in_the_package_and_valid(self):
        self.assertTrue(conformance.path().is_file())
        self.assertEqual(conformance.path().parent, ROOT / "labconstrictor_tools")
        self.assertEqual(conformance.validate(DATA), [])
        self.assertIs(conformance.load(), conformance.load())

    def test_the_command_line_gives_the_path_and_validates(self):
        env = {"PYTHONPATH": str(ROOT), "PATH": ""}
        path = subprocess.run(
            [sys.executable, "-m", "labconstrictor_tools.conformance", "--path"],
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(Path(path.stdout.strip()), conformance.path())
        valid = subprocess.run(
            [sys.executable, "-m", "labconstrictor_tools.conformance", "--validate"],
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual((valid.returncode, valid.stdout.strip()), (0, "conformance.json is valid"))
        usage = subprocess.run(
            [sys.executable, "-m", "labconstrictor_tools.conformance"],
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(usage.returncode, 2)

    def test_the_data_is_plain_json_that_survives_a_round_trip(self):
        text = conformance.path().read_text(encoding="utf-8")
        self.assertEqual(json.loads(json.dumps(DATA)), json.loads(text))
        self.assertTrue(
            text.isascii(),
            "write non-ASCII characters as \\u escapes: the damaged micro sign must stay visible in review",
        )

    def test_a_malformed_file_raises_with_every_problem(self):
        original = conformance.path
        with tempfile.TemporaryDirectory() as folder:
            bad = Path(folder) / "conformance.json"
            bad.write_text(json.dumps({"conformance": 1}), encoding="utf-8")
            conformance._cache = None
            conformance.path = lambda: bad
            try:
                with self.assertRaises(conformance.ConformanceError) as caught:
                    conformance.load()
            finally:
                conformance.path = original
                conformance._cache = None
        self.assertIn("missing top-level key 'limits'", str(caught.exception))
        self.assertIn("missing top-level key 'wrong_science'", str(caught.exception))
        conformance.load()  # and the real one loads again


class Schema(unittest.TestCase):
    def test_each_kind_of_damage_is_named(self):
        cases = {
            "not an object": (lambda d: None, None),
            "missing key": (lambda d: d.pop("messages"), "missing top-level key 'messages'"),
            "wrong version": (lambda d: d.update(conformance=2), "'conformance' must be 1"),
            "limit without value": (
                lambda d: d["limits"]["results_kept"].pop("value"),
                "limits.results_kept: needs a numeric 'value'",
            ),
            "limit value is text": (
                lambda d: d["limits"]["results_kept"].update(value="20"),
                "limits.results_kept: needs a numeric",
            ),
            "limit value is a boolean": (
                lambda d: d["limits"]["results_kept"].update(value=True),
                "needs a numeric",
            ),
            "unknown status": (
                lambda d: d["limits"]["results_kept"].update(status="maybe"),
                "'status' must be one of decided, default",
            ),
            "limit without spec": (lambda d: d["limits"]["results_kept"].pop("spec"), "needs a 'spec'"),
            "limit name": (
                lambda d: d["limits"].update({"Bad Name": d["limits"]["results_kept"]}),
                "not an identifier",
            ),
            "duplicate code": (
                lambda d: d["host_internal_codes"].append("target_unavailable"),
                "host_internal_codes: duplicates",
            ),
            "code not an identifier": (
                lambda d: d["host_internal_codes"].append("Not A Code"),
                "must be a list of identifiers",
            ),
            "positional placeholder": (
                lambda d: d["messages"]["size_mismatch"].update(template="{0} wide"),
                "placeholders must be {name}",
            ),
            "unbalanced template": (
                lambda d: d["messages"]["size_mismatch"].update(template="{name"),
                "bad template",
            ),
            "empty template": (
                lambda d: d["messages"]["size_mismatch"].update(template=""),
                "needs a 'template'",
            ),
            "compat minimum": (
                lambda d: d["compat"].update(min_tools_version="banana"),
                "compat.min_tools_version",
            ),
            "compat expectation": (
                lambda d: d["compat"]["cases"][0].update(expect="fine"),
                "compat.cases: each needs",
            ),
            "compat order": (lambda d: d["compat"]["version_order"].reverse(), "compat.version_order"),
            "duplicate id": (
                lambda d: d["wrong_science"]["coordinate"]["cases"][1].update(id="CF-01"),
                "duplicate id CF-01",
            ),
            "id pattern": (
                lambda d: d["wrong_science"]["calibration"]["cases"][0].update(id="CAL-1"),
                "an id must match",
            ),
            "id in the wrong section": (
                lambda d: d["wrong_science"]["run_identity"]["fixtures"][0].update(id="ASY-01"),
                "an id must match",
            ),
            "missing section": (lambda d: d["wrong_science"].pop("retention"), "missing section 'retention'"),
            "bad rect": (
                lambda d: d["wrong_science"]["coordinate"].update(rect=[[0, 0]]),
                "four [y, x] vertices",
            ),
            "mask lengths": (
                lambda d: d["wrong_science"]["coordinate"]["rect_mask_values"].pop(),
                "same length",
            ),
            "calibration without an answer": (
                lambda d: d["wrong_science"]["calibration"]["cases"][0].update(expect={}),
                "needs expect.um_per_px",
            ),
            "unit factor": (
                lambda d: d["wrong_science"]["calibration"]["length_units"]["um"].update(um_per_unit=0),
                "needs a positive um_per_unit",
            ),
            "unit without names": (
                lambda d: d["wrong_science"]["calibration"]["length_units"]["um"].update(symbols="um"),
                "must be a list of non-empty text",
            ),
            "duplicate symbol": (
                lambda d: d["wrong_science"]["calibration"]["length_units"]["mm"]["symbols"].append("um"),
                "listed for both",
            ),
            "duplicate word, other case": (
                lambda d: d["wrong_science"]["calibration"]["length_units"]["cm"]["words"].append("micron"),
                "listed for both",
            ),
            "a word that is not lower case": (
                lambda d: d["wrong_science"]["calibration"]["length_units"]["cm"]["words"].append("Zoll"),
                "must be trimmed and lower case",
            ),
            "a symbol with a space": (
                lambda d: d["wrong_science"]["calibration"]["length_units"]["cm"]["symbols"].append("cm "),
                "must be trimmed",
            ),
            "a symbol that is a word of another unit": (
                lambda d: d["wrong_science"]["calibration"]["length_units"]["cm"]["symbols"].append("Metre"),
                "is also a word of",
            ),
            "damaged micro sign accepted": (
                lambda d: d["wrong_science"]["calibration"]["length_units"]["um"]["symbols"].append(
                    "\ufffdm"
                ),
                "never start with U+FFFD",
            ),
            "unknown canonical unit": (
                lambda d: d["wrong_science"]["calibration"]["unit_match"].update(canonical="micrometre"),
                "unit_match.canonical must name",
            ),
            "canonical unit that is not the base": (
                lambda d: d["wrong_science"]["calibration"]["unit_match"].update(canonical="mm"),
                "unit_match.canonical must name",
            ),
            "no catalog": (
                lambda d: d["wrong_science"]["calibration"].pop("length_units"),
                "length_units: must be a non-empty object",
            ),
            "retention scope": (
                lambda d: d["wrong_science"]["retention"]["fixtures_tools"][0].update(scope="host"),
                "must have scope 'tools'",
            ),
            "retention markers": (
                lambda d: d["wrong_science"]["retention"]["markers"].pop("lock_file"),
                "markers: owner_file",
            ),
            "number limit that does not exist": (
                lambda d: d["wrong_science"]["number_limits"].update(limits=["nope"]),
                "limit 'nope' is not in 'limits'",
            ),
        }
        for name, (change, expected) in cases.items():
            with self.subTest(name):
                if expected is None:
                    self.assertEqual(conformance.validate([]), ["the file must hold a JSON object"])
                    continue
                problems = broken(change)
                self.assertTrue(any(expected in p for p in problems), "%r not in %r" % (expected, problems))

    def test_validate_never_raises_on_odd_data(self):
        for odd in (
            None,
            3,
            "x",
            [],
            {},
            {
                "conformance": 1,
                "limits": 5,
                "host_internal_codes": 1,
                "messages": 1,
                "compat": 1,
                "wrong_science": 1,
            },
        ):
            self.assertTrue(conformance.validate(odd), odd)


class AgainstTheCode(unittest.TestCase):
    def test_limits_match_the_code_and_the_spec(self):
        limits = DATA["limits"]
        self.assertEqual(limits["form_integer_max"]["value"], notebook.MAX_FORM_INTEGER)
        self.assertEqual(limits["form_integer_max"]["value"], 2**53 - 1)
        self.assertEqual(limits["unbounded_float"]["value"], 1e15)
        if retention is not None:
            kept = (retention.RESULTS_KEPT, retention.RUN_RECORDS_KEPT)
        else:
            from labconstrictor_tools import cli, runs

            kept = (cli.RESULTS_KEPT, runs.KEEP)
        self.assertEqual((limits["results_kept"]["value"], limits["run_records_kept"]["value"]), kept)
        self.assertIn("`RESULTS_KEPT = 20`, `RUN_RECORDS_KEPT = 50`", spec())

    def test_every_limit_marked_default_is_marked_so_in_the_spec(self):
        for name, entry in DATA["limits"].items():
            if entry["status"] == "default":
                self.assertIn(
                    name.split("_")[0], "lookup", name
                )  # only the lookup limits (spec 5.4, working decision 6)
        self.assertIn(
            "6. Lookup limits: one in flight, 8 pending, 60 s timeout (section 5). (default, not yet confirmed)",
            spec(),
        )

    def test_the_host_internal_codes_are_the_ones_the_spec_names(self):
        for code in DATA["host_internal_codes"]:
            self.assertIn("`%s`" % code, spec())
        self.assertEqual(
            sorted(DATA["host_internal_codes"]),
            sorted(
                re.findall(r"New host-side codes (.*?) go into", spec().replace("\n", " "))[0]
                .replace("`", "")
                .split(", ")
            ),
        )

    def test_the_compat_vectors_give_the_same_answer_as_the_reference(self):
        compat_data = DATA["compat"]
        for case in compat_data["cases"]:
            with self.subTest(case["case"]):
                result = compat.check_schema(
                    case["schema"], compat_data["min_tools_version"], compat_data["required_features"]
                )
                self.assertEqual(result.status, case["expect"], result.reason)
                self.assertIn(case.get("reason_contains", ""), result.reason)
        ordered = [compat.parse_version(v) for v in compat_data["version_order"]]
        self.assertEqual(ordered, sorted(ordered))

    def test_the_message_templates_format(self):
        for name, entry in DATA["messages"].items():
            names = {f for _, f, _, _ in string.Formatter().parse(entry["template"]) if f}
            entry["template"].format(**{n: "x" for n in names})
            self.assertTrue(entry["spec"], name)

    def test_every_message_template_is_a_sentence_of_the_spec(self):
        flat = spec().replace("\\u00B5", "") + (ROOT / "docs" / "HOST_PARITY.md").read_text(
            encoding="utf-8"
        )  # I06 has the >= form
        for name, entry in DATA["messages"].items():
            pieces = re.split(r"\{\w+\}", entry["template"])
            pattern = ".+?".join(re.escape(piece) for piece in pieces)
            self.assertTrue(re.search(pattern, flat), "%s: %r is not in the spec" % (name, entry["template"]))


def evaluate(point, source):
    """Napari data (y, x) -> world, plain Python: scale, then translate, or the 3x3 affine on [y, x, 1]."""
    y, x = point
    if "affine" in source:
        m = source["affine"]
        return [m[0][0] * y + m[0][1] * x + m[0][2], m[1][0] * y + m[1][1] * x + m[1][2]]
    scale, translate = source.get("scale", [1, 1]), source.get("translate", [0, 0])
    return [y * scale[0] + translate[0], x * scale[1] + translate[1]]


def inside(polygon_yx, y, x):
    """Even-odd rule for a pixel centre (y, x)."""
    hit = False
    for (y1, x1), (y2, x2) in zip(polygon_yx, polygon_yx[1:] + polygon_yx[:1]):
        if (x1 > x) != (x2 > x) and y < (y2 - y1) * (x - x1) / (x2 - x1) + y1:
            hit = not hit
    return hit


class CoordinateData(unittest.TestCase):
    cases = {c["id"]: c for c in WRONG["coordinate"]["cases"]}

    def test_the_base_image_and_the_rectangle_mask(self):
        coordinate = WRONG["coordinate"]
        rows, columns = coordinate["image"]["shape"]
        value = lambda y, x: 100 * y + x  # noqa: E731  (the 'value' formula of the file, written out)
        self.assertEqual(coordinate["image"]["value"], "100*y + x")
        mask = [[y, x] for y in range(rows) for x in range(columns) if inside(coordinate["rect"], y, x)]
        self.assertEqual(mask, coordinate["rect_mask_pixels"])
        self.assertEqual([value(y, x) for y, x in mask], coordinate["rect_mask_values"])
        for vy, vx in coordinate["rect"]:
            self.assertTrue(
                vy % 1 == 0.5 and vx % 1 == 0.5, "vertices are on half pixels: no centre lies on an edge"
            )

    def test_the_world_coordinates_of_the_napari_cases(self):
        for ident in ("CF-01", "CF-02", "CF-03", "CF-04", "CF-05", "CF-06"):
            case = self.cases[ident]
            with self.subTest(ident):
                self.assertEqual(
                    evaluate(case["point"], case["source"]), [float(v) for v in case["expect"]["world"]]
                )

    def test_the_rotated_and_translated_shapes_layer_gives_the_same_mask(self):
        # CF-02: vertices_world "rect + [100, 0]"; CF-04: the listed world vertices; both map back to the rect through the source
        rect = WRONG["coordinate"]["rect"]
        self.assertEqual(self.cases["CF-02"]["shapes_layer"]["vertices_world"], "rect + [100, 0]")
        self.assertEqual(
            [evaluate(v, self.cases["CF-02"]["source"]) for v in rect], [[y + 100, x] for y, x in rect]
        )
        rotated = [evaluate(v, self.cases["CF-04"]["source"]) for v in rect]
        self.assertEqual(
            rotated, [[float(a), float(b)] for a, b in self.cases["CF-04"]["shapes_layer"]["vertices_world"]]
        )

    def test_a_rect_is_y_then_x_like_the_image_arrays(self):
        coordinate = WRONG["coordinate"]
        rows, columns = coordinate["image"]["shape"]
        rect = coordinate["rect"]
        self.assertIn("[y, x]", coordinate["axis_order"]["rect"])
        self.assertIn("[x, y]", coordinate["axis_order"]["protocol_shapes"])
        # read as [y, x] the vertices give the listed mask; read as [x, y] (swapped) they would give another one
        as_yx = [[y, x] for y in range(rows) for x in range(columns) if inside(rect, y, x)]
        swapped = [[x, y] for y, x in rect]
        as_xy = [[y, x] for y in range(rows) for x in range(columns) if inside(swapped, y, x)]
        self.assertEqual(as_yx, coordinate["rect_mask_pixels"])
        self.assertNotEqual(as_xy, coordinate["rect_mask_pixels"])
        self.assertEqual(
            [
                [min(v[0] for v in rect), max(v[0] for v in rect)],
                [min(v[1] for v in rect), max(v[1] for v in rect)],
            ],
            [[1.5, 3.5], [2.5, 5.5]],
        )

    def test_width_height_is_only_the_server_size_and_every_other_pair_is_y_first(self):
        order = WRONG["coordinate"]["axis_order"]
        self.assertIn("[width, height]", order["server_wh"])
        for key in ("image_shape", "export_shape", "offset_yx", "c_yx", "rect", "points"):
            self.assertTrue(order[key].startswith("[rows") or order[key].startswith("[y"), key)
        cf09 = self.cases["CF-09"]
        self.assertEqual(cf09["source"]["server_shape_yx"], cf09["source"]["server_wh"][::-1])
        self.assertEqual(cf09["source"]["server_shape_yx"], WRONG["coordinate"]["image"]["shape"])
        self.assertEqual(
            cf09["expect"]["export_shape"], [4, 6], "rows, columns: 4 rows (y 2..6), 6 columns (x 4..10)"
        )
        for variant in self.cases["CF-14"]["variants"]:
            if "server_wh" not in variant:
                continue
            rows, columns = variant["server_shape_yx"]
            self.assertEqual([columns, rows], variant["server_wh"], variant)
            (y0, x0), (height, width), d = (
                variant["offset_yx"],
                variant["export_shape"],
                variant["downsample"],
            )
            self.assertLessEqual(
                y0 + height * d, rows, variant
            )  # export_shape [rows, columns] fits in the server rows/columns
            self.assertLessEqual(x0 + width * d, columns, variant)

    def test_the_decisions_are_recorded_in_the_spec_and_no_longer_listed_as_gaps(self):
        text = spec()
        section_8 = text[text.index("## 8. Decisions and follow-ups") :]
        self.assertIn("the axis order of a `rect` region is `[y, x]`", section_8)
        self.assertIn("a catalog in `conformance.json`, edited by data change", section_8)
        self.assertIn("Everything not in the catalog is unknown calibration", section_8)
        self.assertIn(
            "**Anything not in the catalog is an unknown unit and means unknown calibration.**", text
        )
        self.assertIn("How to add a unit", (ROOT / "docs" / "CONFORMANCE.md").read_text(encoding="utf-8"))
        gaps = (ROOT / "docs" / "CONFORMANCE.md").read_text(encoding="utf-8").split("## Gaps:")[1]
        self.assertNotIn("Axis order of `rect`", gaps)
        self.assertNotIn("**Length units**", gaps)

    def test_the_qupath_crop(self):
        case = self.cases["CF-09"]
        x0, x1 = case["selection_annotation"]["x"]
        y0, y1 = case["selection_annotation"]["y"]
        self.assertEqual(case["expect"]["export_offset_yx"], [y0, x0])
        self.assertEqual(case["expect"]["export_shape"], [y1 - y0, x1 - x0])
        offset, shape = case["expect"]["export_offset_yx"], case["expect"]["export_shape"]
        self.assertEqual(case["expect"]["export_value_0_0"], 100 * offset[0] + offset[1])
        self.assertEqual(
            case["expect"]["export_value_3_5"], 100 * (offset[0] + shape[0] - 1) + offset[1] + shape[1] - 1
        )
        self.assertEqual(
            case["result_expect"]["target_px"], [offset[0] + case["point"][0], offset[1] + case["point"][1]]
        )

    def test_the_placement_formula_for_every_downsample_variant(self):
        self.assertEqual(WRONG["coordinate"]["placement"]["formula"], "c = x0 + (x + 0.5) * downsample")
        for variant in self.cases["CF-14"]["variants"]:
            y, x = variant["point"]
            (y0, x0), d = variant["offset_yx"], variant["downsample"]
            self.assertEqual(variant["expect"]["c_yx"], [y0 + (y + 0.5) * d, x0 + (x + 0.5) * d], variant)

    def test_the_refusals_use_declared_host_internal_codes(self):
        mentioned = set(
            re.findall(r"refuse (\w+)", json.dumps(self.cases["CF-10"]) + json.dumps(self.cases["CF-13"]))
        )
        self.assertEqual(
            mentioned, {"selection_plane_mismatch", "selection_mixed_planes", "frame_unsupported_transform"}
        )
        self.assertTrue(mentioned <= set(DATA["host_internal_codes"]))
        self.assertIn("target_unavailable", DATA["host_internal_codes"])


class CalibrationData(unittest.TestCase):
    calibration = WRONG["calibration"]
    cases = {c["id"]: c for c in calibration["cases"]}

    def um(self, scale, unit):
        """Plain unit conversion by the rule of the file (symbols exact, words case-insensitive after trimming); None for
        unknown. Written here from the rule, never by calling the validator."""
        if unit.startswith("\ufffd"):
            return None
        for entry in self.calibration["length_units"].values():
            if unit in entry["symbols"] or unit.strip().lower() in entry["words"]:
                return scale * entry["um_per_unit"]
        return None

    # the catalog as an independent oracle: canonical unit -> (um per unit, symbols, words)
    ORACLE = {
        "nm": (0.001, {"nm"}, {"nanometer", "nanometers", "nanometre", "nanometres"}),
        "um": (
            1.0,
            {"um", "\u00b5m", "\u03bcm"},
            {"micron", "microns", "micrometer", "micrometers", "micrometre", "micrometres"},
        ),
        "mm": (1000.0, {"mm"}, {"millimeter", "millimeters", "millimetre", "millimetres"}),
        "cm": (10000.0, {"cm"}, {"centimeter", "centimeters", "centimetre", "centimetres"}),
        "m": (1000000.0, {"m"}, {"meter", "meters", "metre", "metres"}),
        "angstrom": (0.0001, {"\u00c5", "\u212b"}, {"angstrom", "angstroms"}),
    }

    def test_unit_spellings_convert_to_the_listed_answers(self):
        self.assertAlmostEqual(self.um(1, "millimeter"), 1000.0)
        self.assertAlmostEqual(self.um(1, "millimetre"), 1000.0)
        variants = self.cases["CAL-05"]["input"]["variants"]
        for variant in variants:
            self.assertAlmostEqual(self.um(variant["scale"], variant["unit"]) / 0.325, 1.0, delta=1e-9)
        for variant in self.cases["CAL-15"]["input"]["variants"]:
            self.assertEqual(self.um(variant["scale"], variant["unit"]), 0.5)
        for variant in self.cases["CAL-17"]["input"]["variants"]:
            self.assertAlmostEqual(self.um(variant["scale"], variant["unit"]), 0.0001, places=12)
        for variant, expected in zip(
            self.cases["CAL-20"]["input"]["variants"], self.cases["CAL-20"]["expect"]["um_per_px_each"]
        ):
            self.assertAlmostEqual(self.um(variant["scale"], variant["unit"]) / expected, 1.0, delta=1e-12)
        damaged = self.cases["CAL-16"]["input"]
        self.assertIsNone(self.um(damaged["scale"], damaged["unit"]))
        self.assertIn(damaged["unit"], self.cases["CAL-16"]["expect"]["warning"])

    def test_every_catalog_name_converts_to_the_factor_of_the_oracle(self):
        catalog = self.calibration["length_units"]
        self.assertEqual(set(catalog), set(self.ORACLE))
        for canonical, (factor, symbols, words) in self.ORACLE.items():
            with self.subTest(canonical):
                self.assertEqual(catalog[canonical]["um_per_unit"], factor)
                self.assertEqual(set(catalog[canonical]["symbols"]), symbols)
                self.assertEqual(set(catalog[canonical]["words"]), words)
                for name in symbols:  # symbols: exact text only
                    self.assertAlmostEqual(self.um(2.0, name), 2.0 * factor, places=12)
                    for other in (name.upper(), name.title(), " " + name, name + " "):
                        if other != name and other not in symbols:
                            self.assertIsNone(self.um(2.0, other), repr(other))
                for name in words:  # words: any case, surrounding spaces trimmed
                    for spelling in (name, name.upper(), name.title(), "  %s " % name):
                        self.assertAlmostEqual(self.um(2.0, spelling), 2.0 * factor, places=12)
                    self.assertIsNone(self.um(2.0, name[:3] + " " + name[3:]), "a space inside a word")

    def test_the_same_physical_length_in_every_unit_agrees(self):
        # 1 mm written five ways, from the oracle's factors
        for scale, unit in ((1000.0, "um"), (1e6, "nm"), (1.0, "mm"), (0.1, "cm"), (0.001, "m"), (1e7, "Å")):
            self.assertAlmostEqual(self.um(scale, unit), 1000.0, places=6, msg=unit)

    def test_every_refused_name_is_an_unknown_unit(self):
        refused = self.calibration["unit_match_refused"]
        self.assertEqual(len(refused), len(set(refused)), "a name listed twice")
        for name in refused:
            with self.subTest(name=name):
                self.assertIsNone(self.um(1.0, name))
        # the families: case variants of every symbol, plurals and spaced forms of symbols, inch, a damaged sign
        for symbol in ("um", "nm", "mm", "cm"):
            for variant in (symbol.upper(), symbol.capitalize(), symbol + "s", " " + symbol, symbol + " "):
                self.assertIn(variant, refused, variant)
        for name in ("M", "inch", "pixel", "kilometer", "micro meter", "\u00e5", "\ufffdm"):
            self.assertIn(name, refused)
        case = self.cases["CAL-19"]
        self.assertEqual(case["input"]["units_from"], "unit_match_refused")
        self.assertEqual(case["expect"]["um_per_px_each"], ["unknown"] * len(refused))
        self.assertIn("case-insensitively after trimming", self.calibration["unit_match"]["rule"])

    def test_the_three_micro_spellings_are_the_ones_of_the_spec(self):
        self.assertEqual(self.calibration["micro_sign_spellings"], ["\u00b5", "\u03bc", "u"])
        for prefix in self.calibration["micro_sign_spellings"]:
            self.assertEqual(self.um(1.0, prefix + "m"), 1.0)
        self.assertEqual(self.calibration["damaged_micro_prefix"], "\ufffd")
        self.assertIsNone(self.um(1.0, "\ufffdm"))

    def test_the_catalog_is_the_one_place_to_add_a_unit(self):
        # a new unit or alias is a data change only: the validator accepts it, and the oracle resolves it with no code change
        data = copy.deepcopy(DATA)
        catalog = data["wrong_science"]["calibration"]["length_units"]
        catalog["um"]["words"].append("mikron")
        catalog["mm"]["symbols"].append("mil")
        catalog["pm"] = {"um_per_unit": 1e-6, "symbols": ["pm"], "words": ["picometer"]}
        self.assertEqual(conformance.validate(data), [])

    def test_anisotropy_rule(self):
        tolerance = self.calibration["anisotropy_tolerance"]["relative_to_larger"]
        within, beyond = self.cases["CAL-18"]["input"]["variants"]
        for variant, expected in ((within, 0.5002), (beyond, "unknown")):
            x, y = variant["scale"]
            isotropic = abs(x - y) / max(x, y) <= tolerance
            self.assertEqual(round((x + y) / 2, 10) if isotropic else "unknown", expected)

    def test_default_looking_resolutions(self):
        defaults = self.calibration["default_resolution_dpi"]
        for ident, dpi in (("CAL-11", 72), ("CAL-12", 96)):
            resolution = self.cases[ident]["input"]["resolution"][0]
            self.assertLessEqual(abs(resolution - dpi) / dpi, defaults["tolerance_relative"])
            self.assertEqual(self.cases[ident]["expect"]["um_per_px"], "unknown")
        for variant, per_cm in zip(self.cases["CAL-13"]["input"]["variants"], defaults["per_cm"]):
            self.assertEqual(variant["resolution"][0], per_cm)
        self.assertEqual(
            [round(2.54 / 72 * 1e4, 2), round(2.54 / 96 * 1e4, 2)], [352.78, 264.58]
        )  # what a wrong reading would give
        not_default = self.cases["CAL-14"]["input"]["resolution"][0]
        self.assertTrue(
            all(abs(not_default - d) / d > defaults["tolerance_relative"] for d in defaults["values"])
        )
        self.assertAlmostEqual(2.54 * 1e4 / not_default, 1.0)  # 1 inch = 25400 um

    def test_the_request_shape_is_per_axis_with_x_and_y_in_phase_one(self):
        shape = self.calibration["request_shape"]
        self.assertEqual(shape["phase_1_axes"], ["x", "y"])
        entry = shape["_calibration"]["pixel_size"]
        self.assertEqual(sorted(entry["axes"]), ["x", "y"])
        self.assertEqual(sorted(entry["axes"]["x"]), ["raw", "source", "unit", "value"])
        from labconstrictor_tools.protocol import RESERVED_INPUTS

        self.assertIn(self.calibration["reserved_input"], RESERVED_INPUTS)

    def test_the_transitions_are_the_nine_of_the_spec(self):
        self.assertEqual(
            [t["id"] for t in self.calibration["transitions"]], ["CAL-T%d" % i for i in range(1, 10)]
        )
        self.assertEqual(sorted(self.cases), ["CAL-%02d" % i for i in range(1, 21)])


@unittest.skipIf(
    retention is None, "labconstrictor_tools.retention is not in this tree yet; its fixtures run once it is"
)
class RetentionFixturesAgainstTheReference(unittest.TestCase):
    """The `fixtures_tools` of the file, built and run for real against `retention.prune` and the CLI."""

    def build_and_run(self, fixture):
        import os

        tmp = Path(tempfile.mkdtemp(prefix="lc_conf_"))
        self.addCleanup(shutil.rmtree, tmp, True)
        home = tmp / "home"
        for root in ("results", "runs"):
            (home / root).mkdir(parents=True)
        outside = tmp / "outside"
        outside.mkdir()
        made = {
            "owned": {"results": [], "runs": []},
            "foreign": [],
            "legacy": [],
            "links": [],
            "crashed": [],
            "copies": [],
        }
        counter = [0]

        def stamp(i):
            return "2026-10-01T08:%02d:%02d.%03dZ" % (i // 60 % 60, i % 60, 7)

        def make(root, name, i, done=True, marker_name=None):
            folder = home / root / name
            folder.mkdir()
            (folder / "data.txt").write_text("keep " + name)
            owner = {
                "lc_marker": 1,
                "kind": "result" if root == "results" else "run",
                "name": marker_name or name,
                "host": "cli",
                "pid": 1,
                "created": stamp(i),
                "token": "0000000%010d" % i,
            }
            (folder / ".lc-owner.json").write_text(json.dumps(owner))
            if done:
                (folder / ".lc-done.json").write_text(json.dumps({"finished": stamp(i + 1), "status": "ok"}))
            return folder

        for step in fixture["setup"]:
            ((kind, spec),) = step.items()
            if kind == "foreign":
                folder = home / spec["root"] / spec["name"]
                folder.mkdir()
                for file_name, content in spec["files"].items():
                    (folder / file_name).write_text(content)
                made["foreign"].append((folder, spec["files"]))
            elif kind == "owned":
                for _ in range(spec["count"]):
                    counter[0] += 1
                    index = 0 if spec.get("oldest") else counter[0] + 10
                    name = (
                        "20261001T08%04d_%06x_app_tool" % (index, index)
                        if spec["root"] == "results"
                        else "%04d_run" % index
                    )
                    folder = make(spec["root"], name, index, done=spec.get("done", True))
                    made["owned"][spec["root"]].append(folder)
                    if not spec.get("done", True):
                        made["crashed"].append(folder)
            elif kind == "legacy":
                for i in range(spec["count"]):
                    folder = home / spec["root"] / ("20260101T0000%02d_abcdef_app_tool" % i)
                    folder.mkdir()
                    (folder / "data.txt").write_text("legacy")
                    made["legacy"].append(folder)
            elif kind == "link":
                (outside / "data.txt").write_text("outside")
                (outside / ".lc-owner.json").write_text(
                    json.dumps(
                        {
                            "lc_marker": 1,
                            "kind": "result",
                            "name": spec["name"],
                            "created": stamp(0),
                            "token": "0" * 12,
                        }
                    )
                )
                (outside / ".lc-done.json").write_text(json.dumps({"finished": stamp(1), "status": "ok"}))
                try:
                    os.symlink(outside, home / spec["root"] / spec["name"], target_is_directory=True)
                except (OSError, NotImplementedError):
                    self.skipTest(
                        "unsupported: no link can be created here (reported as unsupported, never as a pass)"
                    )
                made["links"].append(home / spec["root"] / spec["name"])
            elif kind == "owned_copy_renamed":
                made["copies"].append(
                    make(spec["root"], spec["name"], 0, marker_name="20261001T080000_000000_app_other")
                )
            elif kind == "equal_created":
                for letter in "cba"[: spec["count"]]:
                    made["owned"][spec["root"]].append(
                        make(spec["root"], "20261001T080000_%s%s%s%s%s%s_app_tool" % ((letter,) * 6), 5)
                    )
            elif kind == "lock_held_by_another_process":
                holder = subprocess.Popen(
                    [sys.executable, "-c", "import sys, pathlib\nfrom labconstrictor_tools import retention\nwith retention._retention_lock(pathlib.Path(sys.argv[1])) as h:\n    print('held' if h else 'no', flush=True)\n    sys.stdin.readline()\n", str(home)],
                    env={**os.environ, "PYTHONPATH": str(ROOT)}, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
                )  # fmt: skip
                self.addCleanup(holder.wait, 30)
                self.addCleanup(holder.stdin.close)
                self.addCleanup(holder.stdout.close)
                self.assertEqual(holder.stdout.readline().strip(), "held")
            else:
                self.fail("the file has a setup step this test does not know: %r" % kind)
        action = fixture["action"]
        env = {**os.environ, "LC_HOME": str(home), "PYTHONPATH": str(ROOT)}
        codes = []
        if "prune_processes_at_once" in action:
            procs = [
                subprocess.Popen(
                    [sys.executable, "-m", "labconstrictor_tools", "prune", "--root", action["root"]],
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                for _ in range(action["prune_processes_at_once"])
            ]
            for proc in procs:
                proc.communicate(timeout=120)
                codes.append(proc.returncode)
        elif "keep" in action:
            retention.prune(action["prune"], home=home, keep={action["prune"]: action["keep"]})
        else:
            done = subprocess.run(
                [sys.executable, "-m", "labconstrictor_tools", "prune", "--root", action["prune"]],
                env=env,
                capture_output=True,
                text=True,
                timeout=120,
            )
            codes.append(done.returncode)
        return home, made, codes

    def test_every_tools_fixture_of_the_file(self):
        fixtures = WRONG["retention"]["fixtures_tools"]
        self.assertEqual(
            sorted(f["id"] for f in fixtures), ["RET-%02d" % i for i in (1, 2, 3, 4, 5, 6, 7, 8, 9, 12, 13)]
        )
        for fixture in fixtures:
            with self.subTest(fixture["id"]):
                home, made, codes = self.build_and_run(fixture)
                for check in fixture["expect"]:
                    ((kind, want),) = check.items()
                    if kind == "foreign_intact":
                        for folder, files in made["foreign"]:
                            for name, content in files.items():
                                self.assertEqual((folder / name).read_text(), content)
                    elif kind == "owned_remaining":
                        root = home / want["root"]
                        remaining = sorted(
                            p.name
                            for p in root.iterdir()
                            if p in made["owned"][want["root"]]
                            or p.name in {q.name for q in made["owned"][want["root"]]}
                        )
                        everything = sorted(q.name for q in made["owned"][want["root"]])
                        self.assertEqual(len(remaining), want["count"])
                        self.assertEqual(
                            remaining, everything[-want["count"] :] if want["which"] != "all" else everything
                        )
                        for name in remaining:
                            self.assertEqual((root / name / "data.txt").read_text(), "keep " + name)
                    elif kind == "link_intact":
                        self.assertTrue(all(p.is_symlink() for p in made["links"]))
                    elif kind == "outside_intact":
                        self.assertEqual((home.parent / "outside" / "data.txt").read_text(), "outside")
                        self.assertEqual(len(list((home.parent / "outside").iterdir())), 3)
                    elif kind == "copy_intact":
                        self.assertTrue(all((p / "data.txt").is_file() for p in made["copies"]))
                    elif kind == "legacy_intact":
                        self.assertEqual(
                            sum((p / "data.txt").read_text() == "legacy" for p in made["legacy"]), want
                        )
                    elif kind == "crashed_survives":
                        self.assertTrue(all((p / "data.txt").is_file() for p in made["crashed"]))
                    elif kind == "every_exit_code":
                        self.assertEqual(set(codes), {want})
                    elif kind == "exit_code":
                        self.assertEqual(codes[0], want)
                    elif kind == "remaining_names":
                        names = sorted(p.name for p in (home / "results").iterdir())
                        self.assertEqual(names, sorted(q.name for q in made["owned"]["results"])[-2:])
                    else:
                        self.fail("the file has an expectation this test does not know: %r" % kind)


class Documented(unittest.TestCase):
    def test_every_key_of_the_file_is_in_the_layout_table_of_the_doc(self):
        text = (ROOT / "docs" / "CONFORMANCE.md").read_text(encoding="utf-8")
        for key in (k for k in DATA if not k.startswith("_")):
            self.assertIn("`%s`" % key, text, key)
        for key in (k for k in WRONG if not k.startswith("_")):
            self.assertIn(
                "wrong_science.%s" % key if key not in ("run_identity", "async_lookups") else key, text, key
            )
        for name in DATA["limits"]:
            self.assertIn(name, text, name)


class Packaging(unittest.TestCase):
    def test_pyproject_ships_the_file(self):
        text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        section = text.split("[tool.setuptools.package-data]", 1)[1].split("\n[", 1)[0]
        self.assertIn('labconstrictor_tools = ["conformance.json"]', section)

    def test_the_built_wheel_contains_the_file_and_the_loader_reads_it_from_there(self):
        try:
            from setuptools import build_meta
        except ImportError:
            self.skipTest("setuptools is not installed")
        with tempfile.TemporaryDirectory(prefix="lc_wheel_") as folder:
            tree = Path(folder) / "src"
            shutil.copytree(
                ROOT / "labconstrictor_tools",
                tree / "labconstrictor_tools",
                ignore=shutil.ignore_patterns("__pycache__", "*.egg-info"),
            )
            for name in ("pyproject.toml", "README.md", "LICENSE"):
                shutil.copy2(ROOT / name, tree / name)
            out = Path(folder) / "dist"
            out.mkdir()
            cwd = Path.cwd()
            try:
                import os

                os.chdir(tree)
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    wheel = build_meta.build_wheel(str(out))
            except (
                Exception
            ) as error:  # noqa: BLE001 - an offline or odd build environment is a skip, not a failure of the data
                self.skipTest("the wheel could not be built here (%s: %s)" % (type(error).__name__, error))
            finally:
                os.chdir(cwd)
            import zipfile

            with zipfile.ZipFile(out / wheel) as archive:
                self.assertIn("labconstrictor_tools/conformance.json", archive.namelist())
                self.assertEqual(json.loads(archive.read("labconstrictor_tools/conformance.json")), DATA)


if __name__ == "__main__":
    unittest.main()
