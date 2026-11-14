"""Which host plugin version an app needs (feature id `host_requirements_v1`, docs/PROTOCOL.md "Host requirements").

An app may declare, in its `labconstrictor-app.yaml`, the oldest plugin of each host it works well with:

    host_requirements:
      qupath:
        min_version: 0.1.0-alpha.6        # a release tag of the plugin, with or without "v"
        features: [shapes_owner_v1]       # optional: host feature ids (docs/HOST_FEATURES.md)
        why: Replace keeps your own annotations   # optional, shown to the person
        required: false                   # optional; true refuses the app instead of warning

`register --app-manifest` copies the declaration into the registry entry (`<name>.json`, field `host_requirements`). Every
host that implements `host_requirements_v1` asks, for each registered app:

    status, sentence = check(entry, "qupath", "0.1.0a5", ["shapes_owner_v1"])
    if sentence: show_and_log(sentence)    # status "warn": list the app and say it; "refuse": do not run it

Rules (the sentences are the exact texts hosts must show or log; conformance.json section `host_requirements`):
1. No `host_requirements`, or nothing for the asking host: ("ok", "").
2. The host's version is at least `min_version` and it has every feature: ("ok", "").
3. Older, or a feature missing: ("warn", sentence), or ("refuse", sentence) when `required` is true.
4. The host's version is unknown or unreadable (Fiji's loose script has none) while `min_version` is set: always ("warn",
   UNKNOWN_VERSION), never a refusal: the plugin may well be new enough. Features are still checked.
5. A declaration that is not valid (hand-edited entry; `register` refuses them): ("warn", INVALID), never a crash.
6. An unknown name for the ASKING host is a programming error in the host: ValueError.
Versions compare as PEP 440 (`v0.1.0-alpha.6` = `0.1.0a6` < `0.1.0rc1` < `0.1.0`; `0.1.0a5.dev0` < `0.1.0a5`).
Standard library only.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

FEATURE = "host_requirements_v1"
HOSTS = ("napari", "fiji", "qupath")  # the notebook is not a plugin: it ships with the app
PLUGIN = {"napari": "napari", "fiji": "Fiji", "qupath": "QuPath"}
UPDATE_URL = "https://github.com/CellMigrationLab/LabConstrictor-{plugin}/releases/latest"
KEYS = ("min_version", "features", "why", "required")

TOO_OLD = "{app} needs LabConstrictor-{plugin} {min_version} or newer{why}; this is {host_version}. Update the plugin: {url}"
MISSING = "{app} needs LabConstrictor-{plugin} with {features}{why}; this plugin does not have it. Update the plugin: {url}"
UNKNOWN_VERSION = (
    "{app} needs LabConstrictor-{plugin} {min_version} or newer{why}; the version of this plugin is unknown. "
    "Update the plugin if the app misbehaves: {url}"
)
INVALID = "{app} has a host_requirements declaration that is not valid ({problem}); register the app again with a valid one"
# problems (also the texts `register` refuses with)
NOT_A_MAPPING = "host_requirements must map host names (napari, fiji, qupath) to their requirements"
UNKNOWN_HOST = (
    "unknown host {name!r} in host_requirements (known: napari, fiji, qupath; the notebook needs no plugin)"
)
HOST_NOT_A_MAPPING = "host_requirements.{host} must hold min_version and/or features"
UNKNOWN_KEY = "unknown key {key!r} in host_requirements.{host} (known: " + ", ".join(KEYS) + ")"
NOTHING_REQUIRED = "host_requirements.{host} needs min_version or features"
BAD_VERSION = "host_requirements.{host}.min_version {value!r} is not a version like 0.1.0-alpha.6"
BAD_FEATURES = "host_requirements.{host}.features must be a list of feature ids like shapes_owner_v1"
BAD_WHY = "host_requirements.{host}.why must be one line of text"
BAD_REQUIRED = "host_requirements.{host}.required must be true or false"

_VERSION = re.compile(
    r"^v?(\d+(?:\.\d+)*)"
    r"(?:[-_.]?(a|alpha|b|beta|c|rc|pre|preview)[-_.]?(\d*))?"
    r"(?:[-_.]?(post|rev|r)[-_.]?(\d*))?"
    r"(?:[-_.]?(dev)[-_.]?(\d*))?"
    r"(?:\+[a-z0-9.]+)?$",
    re.IGNORECASE,
)
_PRE_RANK = {"a": 0, "alpha": 0, "b": 1, "beta": 1, "c": 2, "rc": 2, "pre": 2, "preview": 2}
_FEATURE_ID = re.compile(r"^[a-z][a-z0-9_]*$")


def version_key(text: object) -> tuple:
    """A sortable key for a PEP 440 version or a release tag (`v0.1.0-alpha.6`); ValueError when it is not one."""
    match = _VERSION.match(str(text).strip()) if isinstance(text, str) else None
    if not match:
        raise ValueError("not a version: %r" % (text,))
    release, pre, pre_n, post, post_n, dev, dev_n = match.groups()
    numbers = [int(x) for x in release.split(".")]
    while len(numbers) > 1 and numbers[-1] == 0:
        numbers.pop()
    if pre:
        phase = (0, _PRE_RANK[pre.lower()], int(pre_n or 0))
    elif dev and not post:
        phase = (-1, 0, 0)  # 1.0.dev0 comes before 1.0a1
    else:
        phase = (1, 0, 0)
    after = (1, int(post_n or 0)) if post else (0, 0)
    development = (0, int(dev_n or 0)) if dev else (1, 0)
    return (tuple(numbers), phase, after, development)


def _parse_host(host: str, value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(HOST_NOT_A_MAPPING.format(host=host))
    for key in value:
        if key not in KEYS:
            raise ValueError(UNKNOWN_KEY.format(key=key, host=host))
    if "min_version" not in value and "features" not in value:
        raise ValueError(NOTHING_REQUIRED.format(host=host))
    clean: dict[str, Any] = {}
    if "min_version" in value:
        minimum = value["min_version"]
        try:
            version_key(minimum)
        except ValueError:
            raise ValueError(BAD_VERSION.format(host=host, value=minimum)) from None
        clean["min_version"] = minimum.strip()
    if "features" in value:
        features = value["features"]
        if not isinstance(features, list) or not all(
            isinstance(f, str) and _FEATURE_ID.match(f) for f in features
        ):
            raise ValueError(BAD_FEATURES.format(host=host))
        clean["features"] = list(features)
    if "why" in value:
        why = value["why"]
        if not isinstance(why, str) or "\n" in why or not why.strip():
            raise ValueError(BAD_WHY.format(host=host))
        clean["why"] = why.strip()
    if "required" in value:
        if not isinstance(value["required"], bool):
            raise ValueError(BAD_REQUIRED.format(host=host))
        clean["required"] = value["required"]
    return clean


def parse_declared(value: object) -> dict[str, dict[str, Any]]:
    """The declaration, cleaned, if it is valid; else a ValueError whose message is the problem (one of the texts above)."""
    if not isinstance(value, Mapping):
        raise ValueError(NOT_A_MAPPING)
    for host in value:
        if host not in HOSTS:
            raise ValueError(UNKNOWN_HOST.format(name=host))
    return {host: _parse_host(host, value[host]) for host in HOSTS if host in value}


def check(
    entry: Mapping[str, Any], host: str, host_version: str | None, host_features: object = ()
) -> tuple[str, str]:
    """Does this host plugin meet the app's requirements? -> (ok | warn | refuse, sentence; "" when there is nothing to say)."""
    if host not in HOSTS:
        raise ValueError(
            "unknown host %r (a programming error in the host; known: %s)" % (host, ", ".join(HOSTS))
        )
    app = str(entry.get("display_name") or entry.get("name", ""))
    if "host_requirements" not in entry:
        return "ok", ""
    try:
        declared = parse_declared(entry["host_requirements"])
    except ValueError as problem:
        return "warn", INVALID.format(app=app, problem=problem)
    need = declared.get(host)
    if need is None:
        return "ok", ""
    words = {
        "app": app,
        "plugin": PLUGIN[host],
        "why": " (%s)" % need["why"] if need.get("why") else "",
        "url": UPDATE_URL.format(plugin=PLUGIN[host]),
        "min_version": need.get("min_version", ""),
        "host_version": host_version or "",
    }
    failed = "refuse" if need.get("required") else "warn"
    unknown = False
    if "min_version" in need:
        try:
            if version_key(host_version) < version_key(need["min_version"]):
                return failed, TOO_OLD.format(**words)
        except ValueError:
            unknown = True  # rule 4: say it, never refuse for it; the features still count
    have = set(host_features) if isinstance(host_features, (list, tuple, set, frozenset)) else set()
    missing = [f for f in need.get("features", []) if f not in have]
    if missing:
        return failed, MISSING.format(features=", ".join(missing), **words)
    return ("warn", UNKNOWN_VERSION.format(**words)) if unknown else ("ok", "")


def declaration_text(entry: Mapping[str, Any]) -> str:
    """One line for `labconstrictor-tools list`: what the entry requires of each host plugin."""
    if "host_requirements" not in entry:
        return "none"
    try:
        declared = parse_declared(entry["host_requirements"])
    except ValueError as problem:
        return "INVALID (%s)" % problem
    parts = []
    for host, need in declared.items():
        bits = ([">= " + need["min_version"]] if "min_version" in need else []) + list(
            need.get("features", [])
        )
        parts.append(
            "%s %s%s" % (PLUGIN[host], " + ".join(bits), " (required)" if need.get("required") else "")
        )
    return "; ".join(parts) or "none"


# ---------------------------------------------------------------- the manifest key (Tools has no YAML parser)
_TOP_KEY = re.compile(r"""^(?:host_requirements|"host_requirements"|'host_requirements')[ \t]*:(.*)$""")
_PAIR = re.compile(r"""^([ \t]+)(["']?)([A-Za-z_][A-Za-z0-9_]*)\2[ \t]*:(.*)$""")


def _strip_comment(text: str) -> str:
    """The value without its YAML comment; a quoted value is kept whole, quotes included."""
    text = text.strip()
    if text.startswith("#"):
        return ""
    if text[:1] in ("'", '"'):
        end = text.find(text[0], 1)
        return text[: end + 1] if end > 0 else text
    return re.split(r"[ \t]#", text, maxsplit=1)[0].strip()


def _scalar(text: str) -> object:
    """A YAML scalar or flow list as written in this key: quoted or plain text, true/false, [a, b]."""
    text = _strip_comment(text)
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "'\"":
        return text[1:-1]
    if text.startswith("["):
        if not text.endswith("]"):
            raise ValueError(
                "a list in host_requirements must be written on one line, like [shapes_owner_v1]"
            )
        inner = text[1:-1].strip()
        return [part.strip().strip("'\"") for part in inner.split(",")] if inner else []
    if text.lower() in ("true", "false"):
        return text.lower() == "true"
    return text


def requirements_in_manifest(text: str) -> dict[str, Any] | None:
    """The `host_requirements:` block of a labconstrictor-app.yaml as nested dicts, or None if the file has no such key.

    Only the block form shown in the module docstring is understood (two levels of `key: value`, flow lists on one line);
    anything else is a ValueError. The value is NOT validated here: `parse_declared` does that.
    """
    lines = text.splitlines()
    found = [i for i, line in enumerate(lines) if _TOP_KEY.match(line)]
    if not found:
        return None
    if len(found) > 1:
        raise ValueError("labconstrictor-app.yaml has the key 'host_requirements' twice")
    match = _TOP_KEY.match(lines[found[0]])
    assert match is not None  # found above  # noqa: S101
    rest = _strip_comment(match.group(1))
    if rest in ("{}", ""):
        result: dict[str, Any] = {}
    else:
        raise ValueError("write host_requirements as a block, one host per line (docs/MANIFEST.md)")
    host_indent = None
    current: dict[str, Any] | None = None
    key_indent = None
    for line in lines[found[0] + 1 :]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        pair = _PAIR.match(line)
        if not pair:
            break  # back at column 0: the next top-level key
        indent, key, value = len(pair.group(1).expandtabs()), pair.group(3), pair.group(4)
        if host_indent is None:
            host_indent = indent
        if indent == host_indent:
            if key in result:
                raise ValueError("host_requirements has the host %r twice" % key)
            if _strip_comment(value):
                result[key] = _scalar(value)  # not a block: parse_declared says what is wrong
                current, key_indent = None, None
            else:
                current = result[key] = {}
                key_indent = None
        elif indent > host_indent and current is not None:
            key_indent = key_indent or indent
            if indent != key_indent:
                raise ValueError("host_requirements: inconsistent indentation at %r" % line.strip())
            if key in current:
                raise ValueError("host_requirements: the key %r appears twice" % key)
            current[key] = _scalar(value)
        else:
            raise ValueError("host_requirements: unexpected line %r" % line.strip())
    if rest == "" and not result:
        raise ValueError(NOT_A_MAPPING)
    return result


def from_manifest(manifest: str | None) -> dict[str, dict[str, Any]] | None:
    """The declaration of `register --app-manifest <file>`, cleaned, or None (absent). ValueError (a sentence) when invalid."""
    if manifest is None:
        return None
    try:
        declared = requirements_in_manifest(Path(manifest).read_text(encoding="utf-8-sig"))
    except OSError as error:
        raise ValueError("cannot read %s: %s" % (manifest, error)) from error
    return None if declared is None else parse_declared(declared)


def manifest_report(manifest: str) -> tuple[int, str]:
    """`check --app-manifest <file>`: (exit code, the line to print) for the host_requirements of an app's manifest."""
    try:
        declared = from_manifest(manifest)
    except ValueError as problem:
        return 1, "✖ host_requirements (%s): %s" % (manifest, problem)
    if declared is None:
        return 0, "✔ host_requirements (%s): none (any plugin version)" % manifest
    return 0, "✔ host_requirements (%s): %s" % (manifest, declaration_text({"host_requirements": declared}))


def validate_vectors(section: object) -> list[str]:
    """Problems with the `host_requirements` section of conformance.json (an empty list means valid). Never raises."""
    if not isinstance(section, dict):
        return ["host_requirements: must be an object"]
    problems: list[str] = []
    if section.get("feature") != FEATURE:
        problems.append("host_requirements.feature: must be %r" % FEATURE)
    if section.get("hosts") != list(HOSTS):
        problems.append("host_requirements.hosts: must be %s" % list(HOSTS))
    messages = section.get("messages")
    for key, text in {
        "too_old": TOO_OLD,
        "missing": MISSING,
        "unknown_version": UNKNOWN_VERSION,
        "invalid": INVALID,
    }.items():
        have = messages.get(key) if isinstance(messages, dict) else None
        if not isinstance(have, dict) or have.get("template") != text:
            problems.append(
                "host_requirements.messages.%s: must be the template of host_requirements.py" % key
            )
    order = section.get("version_order")
    if not isinstance(order, list) or len(order) < 2 or not all(isinstance(v, str) for v in order):
        problems.append("host_requirements.version_order: must be a list of version texts, oldest first")
    cases = section.get("cases")
    if not isinstance(cases, list) or not cases:
        return problems + ["host_requirements.cases: must be a non-empty list"]
    seen: set[str] = set()
    for case in cases:
        label = case.get("case") if isinstance(case, dict) else None
        if not isinstance(case, dict) or not isinstance(label, str) or label in seen:
            problems.append("host_requirements.cases: each needs a unique 'case' text (%r)" % (label,))
            continue
        seen.add(label)
        if not isinstance(case.get("entry"), dict) or not isinstance(case.get("host"), str):
            problems.append("host_requirements.cases %r: needs an 'entry' object and a 'host' text" % label)
        elif case.get("expect") not in ("ok", "warn", "refuse", "error"):
            problems.append("host_requirements.cases %r: 'expect' must be ok | warn | refuse | error" % label)
        elif case["expect"] != "error" and not isinstance(case.get("sentence"), str):
            problems.append(
                "host_requirements.cases %r: needs the exact 'sentence' (\"\" when there is none)" % label
            )
    return problems
