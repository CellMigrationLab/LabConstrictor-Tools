"""Real defects the round-trip tests found in the production code. NOT fixed in the test PR: each finding gets its own fix PR.

`FINDINGS` describes each defect (minimal reproduction, expected correct behaviour, what happens today). `KNOWN` lists the test
ids that fail because of it. Keys are `<transport>:<case id>` for the matrix, `property:<name>` for the hypothesis properties and
`winquote:<label>` for the Windows quoting oracle. The runners skip exactly these ids; test_roundtrip_known_failures.py runs them
again and FAILS when one starts passing, so the PR that fixes a finding has to delete its entries (the list cannot rot).
"""

import functools
import os
import platform
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

META = False  # test_roundtrip_known_failures sets this while it re-runs the listed tests, so that they do not skip themselves


@dataclass(frozen=True)
class Finding:
    title: str
    repro: str  # minimal reproduction
    expected: str  # the correct behaviour
    observed: str  # what happens today
    platforms: tuple[str, ...] = ("posix", "nt")  # os.name values on which the defect shows
    min_python: tuple[int, ...] = (0,)  # the defect shows from this Python version on
    machines: tuple[str, ...] = ()  # platform.machine() values on which it shows (empty: every machine)


SCHEMA = '{"id": "t", "label": "t", "outputs": [], "inputs": [{"name": "n", "label": "N", "type": "%s", "required": True}]}'

FINDINGS: dict[str, Finding] = {}

KNOWN: dict[str, str] = {}


def _add(finding: str, *keys: str) -> None:
    for key in keys:
        KNOWN[key] = finding


def is_known(key: str) -> bool:
    """True when `key` is a listed failure on this platform (the runners skip it)."""
    finding = KNOWN.get(key)
    if finding is None:
        return False
    f = FINDINGS[finding]
    return (
        os.name in f.platforms
        and sys.version_info[: len(f.min_python)] >= f.min_python
        and (not f.machines or platform.machine().lower() in f.machines)
    )


def known_failure(key: str) -> Callable[[Any], Any]:
    """Decorator of a test method that currently fails because of a listed defect: it skips itself (and says why)."""

    def wrap(test: Any) -> Any:
        @functools.wraps(test)
        def run(self: Any, *args: Any, **kwargs: Any) -> Any:
            if is_known(key) and not META:
                self.skipTest("known failure %s, watched by test_roundtrip_known_failures" % KNOWN[key])
            return test(self, *args, **kwargs)

        return run

    return wrap
