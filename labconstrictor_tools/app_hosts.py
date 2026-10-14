"""Which hosts may list an app: the per-host discovery rule (feature id `app_hosts_v1`, docs/PROTOCOL.md "App hosts").

An app declares `hosts:` (a list of notebook | napari | fiji | qupath) in its `labconstrictor-app.yaml`. `register` copies the
list into the registry entry (`<name>.json`, field `hosts`). Every host asks `listed_for(entry, "<its own name>")` for each
registered app and never lists an app for which the answer is False. Napari, Fiji and QuPath apply the same rule in their own
language and test it against the vectors of `conformance.json` (section `app_hosts`).

    listed, sentence = listed_for(entry, "napari")
    if sentence: log.warning(sentence)        # a skip or a compatibility listing is always said, never silent
    if not listed: continue

Rules (the sentences are the exact texts hosts must show or log):
1. `hosts` absent from the entry: listed in EVERY host (older installers do not pass it) and the sentence `ABSENT` says so.
2. `hosts` a non-empty list of unique known host names containing the asking host: listed, empty sentence.
3. `hosts` valid but without the asking host: NOT listed, sentence `NOT_LISTED`.
4. `hosts` present but not valid (not a list, empty, a non-text item, an unknown or repeated name): NOT listed anywhere,
   sentence `INVALID` with the problem; `register` refuses such a declaration, so only a hand-edited entry can have one.
5. An unknown name for the ASKING host is a programming error in the host: ValueError.
The command line (`run`, `check`, `test`, notebooks) is never filtered by this rule: it is about discovery in a host only.
Standard library only; never raises on an odd entry.
"""

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

FEATURE = "app_hosts_v1"
HOSTS = ("notebook", "napari", "fiji", "qupath")

NOT_LISTED = "'{app}' is not listed in {host}: the app declares hosts: {hosts}"
ABSENT = "'{app}' declares no hosts, so it is listed in every host; register it with --app-manifest (or --hosts) to choose"
INVALID = "'{app}' is not listed in {host}: its hosts declaration is not valid ({problem}); register the app again with a valid one"
# problems (also the texts `register` refuses with)
NOT_A_LIST = "hosts must be a list of host names"
EMPTY = "hosts is empty; write at least notebook"
NOT_TEXT = "hosts must contain only text"
UNKNOWN = "unknown host name {name!r} (known: " + ", ".join(HOSTS) + ")"
REPEATED = "host name {name!r} appears twice"
EMPTY_ITEM = "hosts has an empty item (a trailing or doubled comma, or a bare '-')"  # only the manifest reader and --hosts

_TOP_KEY = re.compile(r"""^(?:hosts|"hosts"|'hosts')[ \t]*:(.*)$""")  # the key may be quoted (valid YAML)
# a block item may be unindented (`hosts:` then `- fiji` at column 0 is valid YAML)
_BLOCK_ITEM = re.compile(r"^[ \t]*-(?:[ \t]+|$)(.*)$")


def parse_declared(value: object) -> list[str]:
    """The declared list if it is valid, else a ValueError whose message is the problem (one of the texts above)."""
    if not isinstance(value, list):
        raise ValueError(NOT_A_LIST)
    if not value:
        raise ValueError(EMPTY)
    if not all(isinstance(name, str) for name in value):
        raise ValueError(NOT_TEXT)
    for name in value:
        if name not in HOSTS:
            raise ValueError(UNKNOWN.format(name=name))
    for name in value:
        if value.count(name) > 1:
            raise ValueError(REPEATED.format(name=name))
    return list(value)


def listed_for(entry: Mapping[str, Any], host: str) -> tuple[bool, str]:
    """May `host` list this registry entry? -> (listed, sentence for the person or the log; "" when there is nothing to say)."""
    if host not in HOSTS:
        raise ValueError(
            "unknown host %r (a programming error in the host; known: %s)" % (host, ", ".join(HOSTS))
        )
    app = str(entry.get("name", ""))
    if "hosts" not in entry:
        return True, ABSENT.format(app=app)
    try:
        declared = parse_declared(entry["hosts"])
    except ValueError as problem:
        return False, INVALID.format(app=app, host=host, problem=problem)
    if host in declared:
        return True, ""
    return False, NOT_LISTED.format(app=app, host=host, hosts=", ".join(declared))


def declaration_status(entry: Mapping[str, Any]) -> str:
    """`declared` (a valid list), `absent` (no `hosts` field: listed in every host) or `invalid` (present but not valid)."""
    if "hosts" not in entry:
        return "absent"
    try:
        parse_declared(entry["hosts"])
    except ValueError:
        return "invalid"
    return "declared"


def declaration_text(entry: Mapping[str, Any]) -> str:
    """One line for `labconstrictor-tools list`: what the entry declares, including that nothing is declared."""
    if "hosts" not in entry:
        return "not declared (listed in every host)"
    try:
        return ", ".join(parse_declared(entry["hosts"]))
    except ValueError as problem:
        return "INVALID (%s): listed in no host" % problem


def _strip_comment(text: str) -> str:
    """Drop a YAML comment (` #` to the end of the line); the host names never contain one."""
    return re.split(r"[ \t]#", text, maxsplit=1)[0].strip()


def _name(text: str) -> str:
    return _strip_comment(text).strip("'\"")


def _without_empty_items(names: list[str]) -> list[str]:
    """The names, or a ValueError when one is empty (`[notebook, ]`, `- ` alone): the problem is the comma, not a host name."""
    if "" in names:
        raise ValueError(EMPTY_ITEM)
    return names


def hosts_in_manifest(text: str) -> list[str] | None:
    """The `hosts:` line of a labconstrictor-app.yaml (a flow list `[a, b]` or a block list), or None if the file has no
    such key. Only that one top-level key is understood (Tools has no YAML parser); anything else after `hosts:` is a
    ValueError. The value is NOT validated here (an empty list comes back empty): `parse_declared` does that.
    """
    lines = text.splitlines()
    found = [i for i, line in enumerate(lines) if _TOP_KEY.match(line)]
    if not found:
        return None
    if len(found) > 1:
        raise ValueError("labconstrictor-app.yaml has the key 'hosts' twice")
    match = _TOP_KEY.match(lines[found[0]])
    assert match is not None  # found above  # noqa: S101
    rest = _strip_comment(match.group(1))
    if rest.startswith("["):
        if not rest.endswith("]"):
            raise ValueError("the hosts list must be written on one line, like hosts: [notebook, napari]")
        inner = rest[1:-1].strip()
        return _without_empty_items([_name(part) for part in inner.split(",")]) if inner else []
    if rest:
        raise ValueError(NOT_A_LIST)
    names: list[str] = []
    for line in lines[found[0] + 1 :]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        item = _BLOCK_ITEM.match(line)
        if not item:
            break
        names.append(_name(item.group(1)))
    return _without_empty_items(names)


def from_arguments(hosts: str | None, manifest: str | None) -> list[str] | None:
    """The declaration `register` was given: `--hosts a,b`, or the `hosts:` of `--app-manifest <file>`, or None (absent).
    Raises ValueError (a sentence) when it is invalid or the manifest cannot be read: nothing is registered then.
    """
    if hosts is not None and manifest is not None:
        raise ValueError("give --hosts or --app-manifest, not both")
    if hosts is not None:
        return parse_declared(_without_empty_items([name.strip() for name in hosts.split(",")]))
    if manifest is None:
        return None
    try:
        declared = hosts_in_manifest(Path(manifest).read_text(encoding="utf-8-sig"))
    except OSError as error:
        raise ValueError("cannot read %s: %s" % (manifest, error)) from error
    return None if declared is None else parse_declared(declared)


def manifest_report(manifest: str) -> tuple[int, str]:
    """`check --app-manifest <file>`: (exit code, the line to print) for the hosts declaration of an app's manifest."""
    try:
        declared = from_arguments(None, manifest)
    except ValueError as problem:
        return 1, "✖ hosts (%s): %s" % (manifest, problem)
    if declared is None:
        return (
            0,
            "⚠ %s has no hosts: line, so every host lists the app; write one, like hosts: [notebook, napari]"
            % manifest,
        )
    return 0, "✔ hosts (%s): %s" % (manifest, ", ".join(declared))


def validate_vectors(section: object) -> list[str]:
    """Problems with the `app_hosts` section of conformance.json (an empty list means valid). Never raises."""
    problems: list[str] = []
    if not isinstance(section, dict):
        return ["app_hosts: must be an object"]
    if section.get("feature") != FEATURE:
        problems.append("app_hosts.feature: must be %r" % FEATURE)
    if section.get("known_hosts") != list(HOSTS):
        problems.append("app_hosts.known_hosts: must be %s" % list(HOSTS))
    cases = section.get("cases")
    if not isinstance(cases, list) or not cases:
        return problems + ["app_hosts.cases: must be a non-empty list"]
    seen: set[str] = set()
    for case in cases:
        label = case.get("case") if isinstance(case, dict) else None
        if not isinstance(case, dict) or not isinstance(label, str) or label in seen:
            problems.append("app_hosts.cases: each needs a unique 'case' text (%r)" % (label,))
            continue
        seen.add(label)
        if not isinstance(case.get("entry"), dict) or not isinstance(case.get("host"), str):
            problems.append("app_hosts.cases %r: needs an 'entry' object and a 'host' text" % label)
        elif case.get("expect") not in ("listed", "not_listed", "error"):
            problems.append("app_hosts.cases %r: 'expect' must be listed | not_listed | error" % label)
        elif case["expect"] != "error" and not isinstance(case.get("sentence"), str):
            problems.append(
                "app_hosts.cases %r: needs the exact 'sentence' (\"\" when there is none)" % label
            )
    compat = section.get("compat_cases")
    if not isinstance(compat, list) or not compat:
        problems.append("app_hosts.compat_cases: must be a non-empty list")
    else:
        for case in compat:
            if not (
                isinstance(case, dict)
                and isinstance(case.get("schema"), dict)
                and case.get("expect") in ("ok", "refuse")
            ):
                problems.append(
                    "app_hosts.compat_cases: each needs a 'schema' object and 'expect' ok|refuse (%r)"
                    % (case,)
                )
    messages = section.get("messages")
    for key, text in {"not_listed": NOT_LISTED, "absent": ABSENT, "invalid": INVALID}.items():
        have = messages.get(key) if isinstance(messages, dict) else None
        if not isinstance(have, dict) or have.get("template") != text:
            problems.append("app_hosts.messages.%s: must be the template of app_hosts.py" % key)
    return problems
