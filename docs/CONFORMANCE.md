# Conformance data: `labconstrictor_tools/conformance.json`

One machine-readable file, shipped inside the `labconstrictor-tools` wheel (`[tool.setuptools.package-data]`), that holds the rules every host must agree on, as data. It implements part of the proposal in [HOST_PARITY.md](HOST_PARITY.md#2-proposed-conformance-file) (roadmap phase 0.3, "87a") and carries the fixtures of [SPEC_WRONG_SCIENCE.md](SPEC_WRONG_SCIENCE.md) under the key `wrong_science`. Hosts keep their own constants and code; their tests read this file and compare. A change of a rule is a change of this file and a failing test in every host that has not followed.

**Only decided rules are in it.** A rule the spec marks `(default, not yet confirmed)` has `"status": "default"`; a rule nobody decided is not in the file (see "Gaps" below). The file never holds a value only one host needs.

## Layout

| Key | Content | Run by |
|---|---|---|
| `conformance` | format version (1) | the loader |
| `limits` | named numbers: `results_kept`, `run_records_kept`, `form_integer_max` (9007199254740991), `unbounded_float` (1e15), `choices_debounce_ms`, `choices_busy_retry_ms`, `worker_close_timeout_s`, `lookup_in_flight_max`, `lookup_pending_max`, `lookup_timeout_s`; each `{value, status: decided\|default, spec, ...}` | every host: its constant must equal `value` |
| `host_internal_codes` | the four new host-side codes (`frame_unsupported_transform`, `selection_mixed_planes`, `selection_plane_mismatch`, `target_unavailable`) | hosts |
| `messages` | sentence templates with `{name}` placeholders (Python `str.format`; other languages replace `{name}`) | hosts compare the text they produce |
| `compat` | the compatibility rules of [PROTOCOL.md](PROTOCOL.md) as vectors | Tools (`compat.check_schema`); Fiji and QuPath apply the same rules in their language |
| `wrong_science.coordinate` | base image `ASYM`, the rectangle (vertices `[y, x]`, decided) and its mask, `axis_order` (which fixture field is y first and which is `[width, height]`), the placement formula, cases CF-01..CF-14 | hosts (and an arithmetic check in Tools) |
| `wrong_science.calibration` | unit table (um per unit; the accepted names are exactly its keys, matched as exact text), `unit_names.refused` (the names that are an unknown unit), micro-sign spellings, the damaged-sign rule, anisotropy and default-dpi rules, the `_calibration` request shape, cases CAL-01..CAL-19 and transitions CAL-T1..T9 | hosts (and an arithmetic check in Tools) |
| `wrong_science.retention` | marker names and fields; `fixtures_tools` RET-01..09, 12, 13 (structured: setup, action, expect) and `fixtures_hosts` HRET-01..04, RET-10, 11, 14 (prose) | Tools runs `fixtures_tools` against `retention.prune` and the CLI; every host runs `fixtures_hosts` with the `prune` subprocess replaced by a recorder |
| `wrong_science.run_identity`, `async_lookups` | RUN-01..06, ASY-01..08 (prose sequences and expectations) | hosts |
| `wrong_science.number_limits` | NUM-01..05 | hosts (Napari, Fiji dialog and macro, QuPath, notebook) |

A host that cannot run a case reports it as **unsupported**, never as passed (SPEC_WRONG_SCIENCE 1.5, 3.7).

## The loader

`labconstrictor_tools.conformance` (standard library only):

```python
from labconstrictor_tools import conformance
data = conformance.load()          # validated on every first load; ConformanceError lists every problem
conformance.path()                 # the file, for hosts that are not Python
conformance.validate(some_dict)    # the schema: a list of problems, empty when valid
```
`python -m labconstrictor_tools.conformance --path` prints the file's location (inside the app's or the host's Python environment); `--validate` checks it. The schema checks structure, not host behaviour: required keys, numeric `value`, `status`, identifier names, `{name}` placeholders only, unique ids with the right prefix per section, `compat` vectors in order, the four-vertex rectangle, a positive um factor per unit. A malformed edit therefore fails every host test at once; it cannot silently skip a rule.

## How each host's test loads it

| Host | Test | Loading | Checks |
|---|---|---|---|
| Tools (CLI, `command.py`, `convert.py`, notebook) | `tests/test_conformance.py` | `conformance.load()` | limits against the code, `compat` vectors against `check_schema`, the retention `fixtures_tools` against `retention.prune` and the CLI, arithmetic of the coordinate and unit data |
| Napari | `tests/test_conformance.py` (a plain script, no Qt needed for most of it) | `from labconstrictor_tools import conformance; conformance.load()` (Tools is a dependency of the plugin) | constants against `limits` (`_INT_RANGE`, `_FLOAT_RANGE` against `form_integer_max`, `unbounded_float`), `ResultPresenter` and refusal sentences against `messages`, `host_internal_codes`, CF placement through a fake viewer (`viewer.add_points` receives the Napari data coordinate), region mask through `selection_mask`, CAL and NUM cases through the schema and form code, HRET fixtures with a recorder instead of `prune` |
| Fiji | a case type `conformance` in `tests/run_cases.py`; Groovy side `tests/conformance_check.groovy` | the Python driver runs `python -m labconstrictor_tools.conformance --path` with the app's interpreter and passes the result in the environment variable `LC_CONFORMANCE`; Groovy: `new JsonSlurper().parse(new File(System.getenv("LC_CONFORMANCE")))` | the harness parses the script text without its last line with `new GroovyShell().parse(...)` and calls the helper functions (`polygonRoi`, `selectionMask`, `macroNumber`, ...) and reads the `@Field` constants against `limits` |
| QuPath | `tests/gui_test_conformance_body.groovy`, run by `tests/run_gui_test.sh` (or `tests/headless_core.groovy` where no GUI is needed) | `LcJson.parse(new File(System.getenv("LC_CONFORMANCE")))`, same environment variable | the static members (`LcConst.*`, `LcDialog.*`, `LcArea.clamped`, `LcRegistry.load`) against `limits` and `messages`; CF placement, CAL and NUM cases |

Rules for a host test: it fails when a key it knows is missing (no silent skip); it reports `unsupported` for a case it cannot run; it compares its **own** behaviour (drawn coordinates, request contents, files on disk), not only that no error occurred (SPEC_WRONG_SCIENCE 1.5).

## Gaps: what the spec does not yet decide (so the file does not contain it)

1. **Keys of the HOST_PARITY sketch that are not in SPEC_WRONG_SCIENCE**: `max_shapes`, `table_rows_shown`, `region_max_objects`, `max_export_bytes`, `max_display_bytes`, `cancel_grace_s`, `worker_orphan_grace_s`, `worker_idle_s`, the log limits, `error_codes`, `notice_codes`, `worker_exit_hints`, `number_text`, `quoting` and `command_vectors`, `results_text`, `trust_vectors`, and the wording of the HOST_PARITY `messages` that are not in the wrong-science spec. They are proposals of the parity audit, not decisions; `number_text` also diverges from the Tools CLI today (TOOLS-7), and the Windows quoting of a trailing backslash is marked "TO DECIDE". `tests/quote_vectors.json` remains the shared quoting source until these are decided. `host_error` (QuPath's internal code) is not listed in `host_internal_codes` because the spec names only the four new ones.
3. **CF-07, 08, 10, 11, 12, 13** and all of RUN, ASY, HRET and RET-10/11/14 are sequences with prose expectations; the spec defines no machine-executable vocabulary for them, so only Tools' own fixtures (RET-01..09, 12, 13) are structured, and the others are interpreted by each host's harness.
5. **Number limits** (6): the refusal sentence is given for integers only (`'L' must be <= 9007199254740991`, the `>=` form from HOST_PARITY I06); the float sentence and the message when a GUI box cannot hold the number are not specified. The spec writes the keys as `limits.form_integer_max = 9007199254740991`; the file nests the number as `limits.form_integer_max.value` (the layout of the HOST_PARITY sketch) so that it can carry `status` and `spec`.
7. **Lookup limits** (5.4: one in flight, 8 pending, 60 s) and the other working decisions of SPEC 8 are `status: default`, not yet confirmed.
8. **Napari N-D, QuPath downsample d != 1, TimeIntervalOf and ZStepOf** fixtures wait for Wave 2 (spec header); CF-14 is data, but no host exports at d != 1 yet.
9. **Run-identity and async fixtures have no pass criteria for timing** (no clock or barrier vocabulary): each host's harness decides how to build the "deterministic barriers" of 5.7.
