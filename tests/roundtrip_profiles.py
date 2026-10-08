"""Hypothesis profiles of the round-trip tests. `ci` (the default) is deterministic: derandomized, 200 examples per property,
no example database, no deadline. `nightly` (LC_HYPOTHESIS_PROFILE=nightly) draws fresh random examples, thousands per property.
"""

import os

from hypothesis import HealthCheck, settings

_CHECKS = list(HealthCheck)
CI_EXAMPLES = 200
NIGHTLY_EXAMPLES = 5000

settings.register_profile(
    "ci",
    max_examples=CI_EXAMPLES,
    derandomize=True,
    deadline=None,
    database=None,
    suppress_health_check=_CHECKS,
)
settings.register_profile(
    "nightly",
    max_examples=NIGHTLY_EXAMPLES,
    derandomize=False,
    deadline=None,
    database=None,
    suppress_health_check=_CHECKS,
)
PROFILE = os.environ.get("LC_HYPOTHESIS_PROFILE", "ci")
settings.load_profile(PROFILE)
