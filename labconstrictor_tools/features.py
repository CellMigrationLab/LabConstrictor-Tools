"""Stable feature ids of this Tools version. They are written into every schema and registry entry (`features`).

An id means: "this Tools version implements the rule" (a worker/CLI behaviour), so a host that needs the rule can check for it
instead of comparing version numbers. Rules: an id is never renamed or reused; it is added in the same change that implements
the behaviour (never ahead of it); an id is listed in docs/PROTOCOL.md (tested). Hosts treat an unknown id as a newer feature
and a missing `features` list as "unknown/old".
"""

FEATURES: dict[str, str] = {
    "reserved_inputs_v1": "the worker accepts and ignores reserved underscore inputs it does not know (_job_dir, _calibration, _axes, ...)",
    "retention_prune": "the CLI command `prune` and the `retention` module: only marker-owned, finished folders under results/ and runs/ are removed (hosts only mark a run finished)",
}
