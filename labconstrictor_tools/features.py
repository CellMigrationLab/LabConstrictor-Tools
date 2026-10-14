"""Stable feature ids of this Tools version. They are written into every schema and registry entry (`features`).

An id means: "this Tools version implements the rule" (a worker/CLI behaviour), so a host that needs the rule can check for it
instead of comparing version numbers. Rules: an id is never renamed or reused; it is added in the same change that implements
the behaviour (never ahead of it), with one exception: an id added later for a behaviour that has already shipped is allowed when it
is the only way for a host to tell the versions apart (`shm_order_v1`, added after the behaviour of 0.3.0a1's #125 landed); an id is listed in docs/PROTOCOL.md (tested). Hosts treat an unknown id as a newer feature
and a missing `features` list as "unknown/old".
"""

FEATURES: dict[str, str] = {
    "reserved_inputs_v1": "the worker accepts and ignores reserved underscore inputs it does not know (_job_dir, _calibration, _axes, ...)",
    "shm_order_v1": "a shared-memory image descriptor's `order` is honoured for C and F (a block is read in the order it was written) and anything else is refused with unreadable_image",
    "app_hosts_v1": "`register` records the app's declared `hosts` (notebook, napari, fiji, qupath) in the registry entry and every host lists an app only for a host in that list (app_hosts.listed_for); an entry without `hosts` is listed everywhere, and said so",
    "retention_prune": "the CLI command `prune` and the `retention` module: only marker-owned, finished folders under results/ and runs/ are removed (hosts only mark a run finished)",
}
