"""The cross-host conformance data (`conformance.json`, shipped inside the package) and its loader.

    from labconstrictor_tools import conformance
    data = conformance.load()                 # validated; raises ConformanceError listing every problem
    data["limits"]["form_integer_max"]["value"]
    conformance.path()                        # the file itself, for hosts that are not Python (Fiji, QuPath)
    python -m labconstrictor_tools.conformance --path | --validate

The file holds rules that are already decided in docs/SPEC_WRONG_SCIENCE.md (and the compatibility vectors of PROTOCOL.md) as
data: named limits, message templates, the host-internal error codes and the test vectors (coordinate frame, calibration,
retention, run identity, asynchronous lookups, number limits). Every host test loads it and compares its own constants and
behaviour with it; how each host does that is in docs/CONFORMANCE.md. `validate` is the schema: it is checked on every load, so a
broken edit of the file fails every host test at once instead of silently skipping a rule. Standard library only.
"""

import json
import re
import string
import sys
from collections.abc import Mapping
from importlib import resources
from pathlib import Path
from typing import Any

from .compat import OK, REFUSE, WARN, parse_version

CONFORMANCE_VERSION = 1
FILE_NAME = "conformance.json"
STATUSES = ("decided", "default")  # a rule the maintainers confirmed, or the spec's working default
SCOPES = ("tools", "host")  # who runs a fixture
_TOP = ("conformance", "limits", "host_internal_codes", "messages", "compat", "wrong_science")
_SECTIONS = ("coordinate", "calibration", "retention", "run_identity", "async_lookups", "number_limits")
_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*$")
_ID_PATTERNS = {
    "coordinate": r"^CF-\d\d$",
    "calibration": r"^CAL-\d\d$",
    "calibration transitions": r"^CAL-T\d$",
    "retention": r"^H?RET-\d\d$",
    "run_identity": r"^RUN-\d\d$",
    "async_lookups": r"^ASY-\d\d$",
    "number_limits": r"^NUM-\d\d$",
}

_cache: dict[str, Any] | None = None


class ConformanceError(ValueError):
    """The conformance data is malformed; the message lists every problem found, one per line."""


def path() -> Path:
    """The data file inside the installed package (also works from a source checkout)."""
    return Path(str(resources.files(__package__).joinpath(FILE_NAME)))


def load() -> dict[str, Any]:
    """The validated data. Read-only by convention: the same object is returned on every call (copy before changing it)."""
    global _cache
    if _cache is None:
        data = json.loads(path().read_text(encoding="utf-8"))
        problems = validate(data)
        if problems:
            raise ConformanceError("%s is malformed:\n  %s" % (FILE_NAME, "\n  ".join(problems)))
        _cache = data
    return _cache


def validate(data: Any) -> list[str]:
    """Check the data against the schema of the file; returns the problems (an empty list means valid). Never raises."""
    problems: list[str] = []
    if not isinstance(data, dict):
        return ["the file must hold a JSON object"]
    for key in _TOP:
        if key not in data:
            problems.append("missing top-level key %r" % key)
    if problems:
        return problems
    if data["conformance"] != CONFORMANCE_VERSION or isinstance(data["conformance"], bool):
        problems.append("'conformance' must be %d, got %r" % (CONFORMANCE_VERSION, data["conformance"]))
    _limits(data["limits"], problems)
    _codes(data["host_internal_codes"], problems)
    _messages(data["messages"], problems)
    _compat(data["compat"], problems)
    wrong = data["wrong_science"]
    if not isinstance(wrong, dict):
        problems.append("'wrong_science' must be an object")
        return problems
    for name in _SECTIONS:
        if not isinstance(wrong.get(name), dict):
            problems.append("wrong_science: missing section %r" % name)
    if not problems:
        _wrong_science(wrong, data["limits"], problems)
    return problems


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _limits(limits: Any, problems: list[str]) -> None:
    if not isinstance(limits, dict) or not limits:
        problems.append("limits: must be a non-empty object")
        return
    for name, entry in limits.items():
        if not _IDENTIFIER.match(name):
            problems.append("limits: %r is not an identifier" % name)
        if not isinstance(entry, dict) or not _number(entry.get("value")):
            problems.append("limits.%s: needs a numeric 'value'" % name)
            continue
        if entry.get("status") not in STATUSES:
            problems.append("limits.%s: 'status' must be one of %s" % (name, ", ".join(STATUSES)))
        if not isinstance(entry.get("spec"), str):
            problems.append("limits.%s: needs a 'spec' (the rule's place in the spec)" % name)


def _codes(codes: Any, problems: list[str]) -> None:
    if not isinstance(codes, list) or not all(isinstance(c, str) and _IDENTIFIER.match(c) for c in codes):
        problems.append("host_internal_codes: must be a list of identifiers")
    elif len(set(codes)) != len(codes):
        problems.append("host_internal_codes: duplicates")


def _messages(messages: Any, problems: list[str]) -> None:
    if not isinstance(messages, dict) or not messages:
        problems.append("messages: must be a non-empty object")
        return
    for name, entry in messages.items():
        template = entry.get("template") if isinstance(entry, dict) else None
        if not isinstance(template, str) or not template:
            problems.append("messages.%s: needs a 'template' text" % name)
            continue
        try:
            fields = [f for _, f, _, _ in string.Formatter().parse(template) if f is not None]
        except ValueError as error:
            problems.append("messages.%s: bad template (%s)" % (name, error))
            continue
        if any(not _IDENTIFIER.match(f) for f in fields):
            problems.append(
                "messages.%s: placeholders must be {name} identifiers, not positions or expressions" % name
            )


def _compat(compat: Any, problems: list[str]) -> None:
    if not isinstance(compat, dict):
        problems.append("compat: must be an object")
        return
    if parse_version(compat.get("min_tools_version")) is None:
        problems.append("compat.min_tools_version: not a version")
    if not isinstance(compat.get("required_features"), list):
        problems.append("compat.required_features: must be a list")
    cases = compat.get("cases")
    if not isinstance(cases, list) or not cases:
        problems.append("compat.cases: must be a non-empty list")
    else:
        for case in cases:
            ok = (
                isinstance(case, dict)
                and isinstance(case.get("schema"), dict)
                and case.get("expect") in (OK, WARN, REFUSE)
            )
            if not ok or not isinstance(case.get("case"), str):
                problems.append(
                    "compat.cases: each needs 'case', a 'schema' object and 'expect' ok|warn|refuse (%r)"
                    % (case,)
                )
            elif case["expect"] == REFUSE and not isinstance(case.get("reason_contains", ""), str):
                problems.append("compat.cases %r: 'reason_contains' must be text" % case["case"])
    order = compat.get("version_order")
    parsed = [parse_version(v) for v in order] if isinstance(order, list) else None
    if not parsed or None in parsed or parsed != sorted(parsed):  # type: ignore[type-var]
        problems.append("compat.version_order: must be versions in increasing order")


def _ids(label: str, items: Any, problems: list[str], seen: set[str], pattern_key: str | None = None) -> None:
    if not isinstance(items, list) or not items:
        problems.append("%s: must be a non-empty list" % label)
        return
    pattern = _ID_PATTERNS[pattern_key or label.split(".")[-1]]
    for item in items:
        ident = item.get("id") if isinstance(item, dict) else None
        if not isinstance(ident, str) or not re.match(pattern, ident):
            problems.append("%s: an id must match %s, got %r" % (label, pattern, ident))
        elif ident in seen:
            problems.append("%s: duplicate id %s" % (label, ident))
        else:
            seen.add(ident)


def _vector(value: Any, length: int) -> bool:
    return isinstance(value, list) and len(value) == length and all(_number(v) for v in value)


def _wrong_science(wrong: Mapping[str, Any], limits: Mapping[str, Any], problems: list[str]) -> None:
    seen: set[str] = set()
    coordinate = wrong["coordinate"]
    image = coordinate.get("image")
    if not isinstance(image, dict) or not _vector(image.get("shape"), 2):
        problems.append("wrong_science.coordinate.image: needs a 2-number 'shape'")
    rect = coordinate.get("rect")
    if not isinstance(rect, list) or len(rect) != 4 or not all(_vector(v, 2) for v in rect):
        problems.append("wrong_science.coordinate.rect: four [y, x] vertices")
    pixels, values = coordinate.get("rect_mask_pixels"), coordinate.get("rect_mask_values")
    if (
        not isinstance(pixels, list)
        or not all(_vector(p, 2) for p in pixels)
        or not isinstance(values, list)
        or len(values) != len(pixels)
    ):
        problems.append(
            "wrong_science.coordinate: rect_mask_pixels and rect_mask_values must be lists of the same length"
        )
    _ids("wrong_science.coordinate.cases", coordinate.get("cases"), problems, seen, "coordinate")
    calibration = wrong["calibration"]
    units = calibration.get("length_units_um")
    if not isinstance(units, dict) or not all(_number(v) and v > 0 for v in units.values()):
        problems.append("wrong_science.calibration.length_units_um: unit text -> positive um per unit")
    _ids("wrong_science.calibration.cases", calibration.get("cases"), problems, seen, "calibration")
    for case in calibration.get("cases") or []:
        expect = case.get("expect") if isinstance(case, dict) else None
        if not isinstance(expect, dict) or not ({"um_per_px", "um_per_px_each"} & set(expect)):
            problems.append(
                "wrong_science.calibration: %s needs expect.um_per_px or um_per_px_each" % case.get("id")
            )
    _ids(
        "wrong_science.calibration.transitions",
        calibration.get("transitions"),
        problems,
        seen,
        "calibration transitions",
    )
    retention = wrong["retention"]
    for group in ("fixtures_tools", "fixtures_hosts"):
        _ids("wrong_science.retention." + group, retention.get(group), problems, seen, "retention")
        for fixture in retention.get(group) or []:
            expected = "tools" if group == "fixtures_tools" else "host"
            if isinstance(fixture, dict) and fixture.get("scope") != expected:
                problems.append(
                    "wrong_science.retention: %s must have scope %r" % (fixture.get("id"), expected)
                )
    markers = retention.get("markers")
    if not isinstance(markers, dict) or not {"owner_file", "done_file", "lock_file", "done_statuses"} <= set(
        markers
    ):
        problems.append(
            "wrong_science.retention.markers: owner_file, done_file, lock_file and done_statuses are required"
        )
    _ids(
        "wrong_science.run_identity.fixtures",
        wrong["run_identity"].get("fixtures"),
        problems,
        seen,
        "run_identity",
    )
    _ids(
        "wrong_science.async_lookups.fixtures",
        wrong["async_lookups"].get("fixtures"),
        problems,
        seen,
        "async_lookups",
    )
    numbers = wrong["number_limits"]
    _ids("wrong_science.number_limits.cases", numbers.get("cases"), problems, seen, "number_limits")
    for name in numbers.get("limits") or []:
        if name not in limits:
            problems.append("wrong_science.number_limits: limit %r is not in 'limits'" % (name,))


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if arguments == ["--path"]:
        print(path())
        return 0
    if arguments == ["--validate"]:
        problems = validate(json.loads(path().read_text(encoding="utf-8")))
        print("\n".join(problems) if problems else "%s is valid" % FILE_NAME)
        return 1 if problems else 0
    print("usage: python -m labconstrictor_tools.conformance --path | --validate", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
