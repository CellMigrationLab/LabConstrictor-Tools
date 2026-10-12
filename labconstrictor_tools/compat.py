"""Host-side compatibility check: may this host use a schema written by this version of Tools?

    result = check_schema(schema, min_tools_version="0.2.0rc1", required_features=["reserved_inputs_v1"])
    result.status   # "ok" | "warn" | "refuse"
    result.reason   # one sentence for the person ("" when ok)

The rules are written in docs/PROTOCOL.md ("Compatibility rules for hosts"); Fiji and QuPath apply the same rules in their
own language and test them against the vectors in `conformance.json`. Standard library only, never raises on odd input.
"""

import re
from collections.abc import Iterable, Mapping
from typing import Any, NamedTuple

from .registry import SUPPORTED_PROTOCOLS

OK, WARN, REFUSE = "ok", "warn", "refuse"

_VERSION = re.compile(r"^v?(\d+)\.(\d+)(?:\.(\d+))?(?:[-.]?(a|alpha|b|beta|rc|c)[-.]?(\d+))?$", re.I)
_PRE_ORDER = {"a": 0, "alpha": 0, "b": 1, "beta": 1, "rc": 2, "c": 2}


class Compat(NamedTuple):
    status: str
    reason: str


def parse_version(text: object) -> tuple[int, int, int, int, int] | None:
    """`0.2.0rc1` / `v0.2.0-rc.1` / `0.2` -> a sortable tuple (a release sorts after its pre-releases); None if not a version."""
    match = _VERSION.match(text.strip()) if isinstance(text, str) else None
    if not match:
        return None
    major, minor, patch, pre, number = match.groups()
    rank = (_PRE_ORDER[pre.lower()], int(number)) if pre else (3, 0)
    return (int(major), int(minor), int(patch or 0), *rank)


def check_schema(
    schema: Mapping[str, Any],
    min_tools_version: str | None = None,
    required_features: Iterable[str] = (),
    warn_below_tools_version: str | None = None,
) -> Compat:
    """Apply the host rules to one cached schema (docs/PROTOCOL.md). A missing field means unknown/old, never an error."""
    for name, limit in (
        ("min_tools_version", min_tools_version),
        ("warn_below_tools_version", warn_below_tools_version),
    ):
        if limit and parse_version(limit) is None:
            raise ValueError("%s %r is not a version (programming error in the host)" % (name, limit))
    required = sorted(set(required_features))
    protocol = schema.get("protocol")
    if protocol not in SUPPORTED_PROTOCOLS:
        return Compat(REFUSE, "this app speaks protocol %r, which this host does not support" % (protocol,))
    raw_version, raw_features = schema.get("tools_version"), schema.get("features")
    version = parse_version(raw_version)
    features = {str(f) for f in raw_features} if isinstance(raw_features, list) else None
    if features is None and required:
        return Compat(
            REFUSE,
            "this app's labconstrictor-tools is too old (it lists no features, this host needs %s): update it"
            % ", ".join(required),
        )
    missing = [f for f in required if features is not None and f not in features]
    if missing:
        return Compat(REFUSE, "this app's labconstrictor-tools lacks %s: update it" % ", ".join(missing))
    if min_tools_version:
        if raw_version in (None, ""):
            return Compat(
                REFUSE,
                "this app's labconstrictor-tools is too old (no version recorded, this host needs %s or newer): update it"
                % min_tools_version,
            )
        wanted = parse_version(min_tools_version)
        if version is not None and wanted is not None and version < wanted:
            return Compat(
                REFUSE,
                "this app's labconstrictor-tools %s is older than the %s this host needs: update it"
                % (raw_version, min_tools_version),
            )
    if raw_version in (None, ""):
        return Compat(
            WARN, "the version of this app's labconstrictor-tools is unknown (it predates version 0.2)"
        )
    if version is None:
        return Compat(
            WARN, "the labconstrictor-tools version %r of this app is not understood" % (raw_version,)
        )
    soft = parse_version(warn_below_tools_version)
    if soft is not None and version < soft:
        return Compat(
            WARN,
            "this app's labconstrictor-tools %s is older than the recommended %s: update it"
            % (raw_version, warn_below_tools_version),
        )
    return Compat(OK, "")
