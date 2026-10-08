# Testing the bridge

The round-trip tests prove that every value that travels between a host and a tool arrives unchanged, in both directions, through
every real path, and that the tests themselves would notice if the production code broke. (Older suites are listed in
[tests/README.md](../tests/README.md); this page covers the round-trip work.)

## The rule: production code, independent oracles

* Tests call the **production entry points** a person or a host calls: `client.WorkerProcess` (the worker protocol), the `run`
  command, the text of `command.python_snippet` and `command.command_line` executed for real, `notebook.ToolForm`,
  `convert.load_inputs` / `build_results`, `shapes.labels_to_shapes`, `region.bbox`.
* **No test-only reimplementation** of the thing under test and **no mock standing in for it**.
* Every expected value is an **oracle**: computed in the test from the inputs with plain Python or numpy (`hashlib`, `int`,
  `np.unique`, an even-odd rasteriser, the documented Windows quoting rules), never by calling the converter under test.
* A test that would still pass with the production code deleted is a bug in the test. Section "Production-code guarantees" shows
  how that is checked.

## What is where

| File | Role |
|---|---|
| `labconstrictor_tools/examples/roundtrip.py` | the app under test: an echo tool for every declared type (input type -> the matching output, plus a report of what it received) and transforms with known results |
| `tests/roundtrip_cases.py` | the **case matrix**: plain data, generated. A `Case` = tool + host-side values + `Expect` (status, code, what the tool must have received, what the host must read back) |
| `tests/roundtrip_harness.py` | writes what a host writes (TIFF, CSV, files, shared memory), runs a case through one transport, reads what a host reads, compares |
| `tests/test_roundtrip_matrix.py` | the matrix through the worker protocol, the command line, the copied snippet, the copied terminal line and the notebook form |
| `tests/test_roundtrip_properties.py` | hypothesis properties (converters only raise `ToolError`, identity, strict JSON, text never becomes a path or shell text) |
| `tests/test_roundtrip_geometry.py` | metamorphic geometry checks (translate, transpose, flip, holes, `min_area`, region box, pixel centres) |
| `tests/test_roundtrip_hints.py` | schema hints generated from the marker list of `types.py`: valid combinations obey the manifest, invalid ones are refused |
| `tests/test_roundtrip_failures.py` + `tests/failure_app/` | failure injection through the real client |
| `tests/test_roundtrip_command.py` | quoting against a real shell and the Windows rules; app names with spaces and quotes |
| `tests/roundtrip_known_failures.py` + `test_roundtrip_known_failures.py` | real defects found, and the watcher that keeps the list honest |
| `tests/test_sabotage.py`, `coverage_report.py`, `vulture_whitelist.py` | the production-code guarantees |

Transports and what each can carry: `worker` carries everything (including shared-memory images and invalid JSON types), `cli`,
`terminal` and `snippet` carry what fits on a command line, `notebook` carries what the form's controls can hold. A case lists the
transports that can carry it (`Case.paths`).

## Profiles and time

| Profile | Selected by | What runs |
|---|---|---|
| `ci` (default) | nothing | every case on the worker protocol; an even sample of each group on the slow transports (`TRANSPORT_LIMITS`); hypothesis derandomized, 200 examples per property. About 3 minutes on a laptop. |
| `nightly` | `LC_ROUNDTRIP_PROFILE=nightly`, `LC_HYPOTHESIS_PROFILE=nightly` | heavy cases (4096x3000 images, 64 MB file, 300k-row table, 20k polygons, 5 MB text), every case on every transport, 5000 random examples per property |

Run a slice: `LC_ROUNDTRIP_FILTER='echo_bounded' python -m unittest test_roundtrip_matrix` (a regular expression on case ids),
`python -m unittest test_roundtrip_properties -k identity`.

## How to add a case

1. A new **value** of an existing type: add a row to the generator of that type in `tests/roundtrip_cases.py` (for instance an entry
   in `STRINGS`, `INT_OK`, `FLOAT_OK`, a frame in `table_frames`, a polygon in `shapes_cases`). Say what must come back by building
   the `Expect` from the input with plain Python (`scalar_report(value)`, `array_report(a)`, `table_report(frame)`, `expected_image_out(a)`).
2. A new **type or hint**: add an echo tool to `examples/roundtrip.py`, a generator of cases, and (for a marker) a row in
   `INPUT_MARKERS` / `OUTPUT_MARKERS` of `tests/test_roundtrip_hints.py`. `test_roundtrip_cases.py` and `test_roundtrip_hints.py`
   fail when a declared type, tool or marker has no case.
3. Run `python -m unittest test_roundtrip_matrix`. If the case fails and the production code is wrong, do not weaken the case:
   see "Known failures". If the expectation was wrong, fix the oracle, not the tolerance.

## Known failures

A defect the matrix finds is not fixed in the same PR. Its test ids go into `tests/roundtrip_known_failures.py` under a finding
(minimal reproduction, expected behaviour, observed behaviour). The runners skip exactly those ids; `test_roundtrip_known_failures.py`
runs them again and **fails when one starts to pass**, so the fix PR must delete the entries, and the list cannot rot. Keys:
`<transport>:<case id>`, `property:<name>`, `hint:<id>`, `failure:<tool>`, `lifecycle:<name>`, `test:<module.Class.method>`,
`winquote:<label>`, `winproc:<label>` (the real Windows process start). A finding can be limited to a Python version (`min_python`) or machine type (`machines`): F20 only on ARM.

## The ledger

`docs/REGRESSION_LEDGER.md` has one row per bug (date, symptom, root cause, fix PR, guarding test). A bug found in the field becomes
a matrix row or a test, and a row; `tests/test_roundtrip_ledger.py` checks that every named guard exists.

## Production-code guarantees

* **Coverage** (`[tool.coverage]` in `pyproject.toml`): only `labconstrictor_tools`, branch coverage, tests and examples omitted,
  subprocesses (workers, the command line, snippets) followed. CI runs the Linux Python 3.12 job under coverage and fails below the
  floor (see `ci.yml`: the measured level rounded down). `python tests/coverage_report.py` also lists production code that only the
  tests execute (nothing in the package refers to it) and code nothing executes.
  Locally: `cd tests && python -m coverage run -m unittest discover -p "test_*.py" && python -m coverage combine && python coverage_report.py`.
* **Unused code**: `vulture labconstrictor_tools tests/vulture_whitelist.py --min-confidence 80` runs in the lint job. Every
  whitelist entry has a reason, and a stale entry fails `test_roundtrip_unused_code.py`.
* **Sabotage** (`tests/test_sabotage.py`, Linux, about a minute and a half): for each production function in a table, a copy of the
  package gets one deliberate break (a flipped comparison, x and y swapped, a case dropped), the guarding slice of the matrix runs
  against the copy, and it **must fail**. A break that survives fails the test and is named. To guard a new function add a row.
* **Mutation testing** (nightly, `.github/workflows/nightly.yml`): `mutmut` on `convert.py`, `introspection.py`, `shapes.py`,
  `region.py` and `command.py`, with the round-trip tests as the test command; the surviving mutants are uploaded as an artifact.
  Each survivor is a missing test.

## Platforms

Linux, macOS and Windows run the whole set except the sabotage test (Linux only) and the POSIX-only checks (SIGKILL, shared-memory
ownership, children after the host went away, which skip on Windows). Anything specific to a platform is guarded with `os.name`.
