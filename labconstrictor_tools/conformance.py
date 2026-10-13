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
TASK_STATUSES = (
    "COMPLETE",
    "CANCELED",
    "FAILED",
    "CRASHED",
)  # how a task can end (client.Task.status after it is done)
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
        _references(wrong, data["messages"], data["host_internal_codes"], problems)
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


def _length_units(units: Any, match: Any, problems: list[str]) -> None:
    """The unit catalog: canonical unit -> {um_per_unit, symbols, words}. Symbols match as exact text, words case-insensitively
    after trimming, so a word is written lower case and trimmed, and no two units may own the same name."""
    label = "wrong_science.calibration.length_units"
    if not isinstance(units, dict) or not units:
        problems.append("%s: must be a non-empty object (canonical unit -> its factor and names)" % label)
        return
    owner: dict[str, str] = {}  # the key a text is looked up by -> canonical unit
    for canonical, entry in units.items():
        if not isinstance(entry, dict):
            problems.append(
                "%s.%s: must be an object with um_per_unit, symbols and words" % (label, canonical)
            )
            continue
        factor = entry.get("um_per_unit")
        if factor is None or not _number(factor) or factor <= 0:
            problems.append("%s.%s: needs a positive um_per_unit" % (label, canonical))
        for kind in ("symbols", "words"):
            names = entry.get(kind)
            if not isinstance(names, list) or not all(isinstance(n, str) and n for n in names):
                problems.append("%s.%s.%s: must be a list of non-empty text" % (label, canonical, kind))
                continue
            for name in names:
                if kind == "symbols":
                    key = "s:" + name
                    bad = name != name.strip() or name.startswith("\ufffd")
                else:
                    key = "w:" + name.casefold()
                    bad = name != name.strip().casefold() or name.startswith("\ufffd")
                if bad:
                    problems.append(
                        "%s.%s.%s: %r must be trimmed%s, and never start with U+FFFD"
                        % (label, canonical, kind, name, " and lower case" if kind == "words" else "")
                    )
                elif key in owner:
                    problems.append(
                        "%s: the name %r is listed for both %s and %s" % (label, name, owner[key], canonical)
                    )
                else:
                    owner[key] = canonical
    for key, canonical in list(
        owner.items()
    ):  # a symbol that is also a word of another unit would be ambiguous
        if key.startswith("s:") and owner.get("w:" + key[2:].casefold(), canonical) != canonical:
            problems.append(
                "%s: the symbol %r is also a word of %s" % (label, key[2:], owner["w:" + key[2:].casefold()])
            )
    base = units.get(match.get("canonical") if isinstance(match, dict) else None)
    if not isinstance(match, dict) or not isinstance(base, dict) or base.get("um_per_unit") != 1.0:
        problems.append("%s: unit_match.canonical must name the unit whose um_per_unit is 1.0" % label)


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
    _length_units(calibration.get("length_units"), calibration.get("unit_match"), problems)
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
    _done_status(retention, problems)
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


def _done_status(retention: Mapping[str, Any], problems: list[str]) -> None:
    """The mapping of a task's end to the done status (spec 3.2): every task status maps to a status the marker may hold."""
    label = "wrong_science.retention.done_status"
    rule = retention.get("done_status")
    markers = retention.get("markers")
    allowed = markers.get("done_statuses") if isinstance(markers, dict) else None
    if not isinstance(rule, dict) or not isinstance(allowed, list):
        problems.append("%s: needs an object (and retention.markers.done_statuses)" % label)
        return
    by_task = rule.get("by_task_status")
    if not isinstance(by_task, dict) or set(by_task) != set(TASK_STATUSES):
        problems.append(
            "%s.by_task_status: needs exactly the task statuses %s" % (label, ", ".join(TASK_STATUSES))
        )
        by_task = {}
    for task_status, done in by_task.items():
        if done not in allowed:
            problems.append("%s.by_task_status.%s: %r is not a done status" % (label, task_status, done))
    if rule.get("crashed_after_cancel") not in allowed:
        problems.append("%s.crashed_after_cancel: must be one of the done statuses" % label)
    for fixture in retention.get("fixtures_hosts") or []:
        if not isinstance(fixture, dict) or "done_status" not in fixture:
            continue
        ident = fixture.get("id")
        if fixture.get("task_status") not in TASK_STATUSES or not isinstance(
            fixture.get("cancel_requested"), bool
        ):
            problems.append(
                "wrong_science.retention: %s needs task_status and a true/false cancel_requested" % ident
            )


def prescribed_done_status(rule: Mapping[str, Any], task_status: str, cancel_requested: bool) -> str | None:
    """The done status the data prescribes for a task that ended as `task_status` (a crash after Cancel is its own entry)."""
    if task_status == "CRASHED" and cancel_requested:
        return rule.get("crashed_after_cancel")
    return (rule.get("by_task_status") or {}).get(task_status)


def _references(wrong: Mapping[str, Any], messages: Any, codes: Any, problems: list[str]) -> None:
    """A fixture that names a message or a code names one that exists, so a renamed sentence cannot leave a fixture behind."""
    for fixture in wrong["run_identity"].get("fixtures") or []:
        if not isinstance(fixture, dict):
            continue
        if "message" in fixture and fixture["message"] not in (
            messages if isinstance(messages, dict) else {}
        ):
            problems.append(
                "wrong_science.run_identity: %s names the unknown message %r"
                % (fixture.get("id"), fixture["message"])
            )
        if "code" in fixture and fixture["code"] not in (codes if isinstance(codes, list) else []):
            problems.append(
                "wrong_science.run_identity: %s names the unknown code %r"
                % (fixture.get("id"), fixture["code"])
            )


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
