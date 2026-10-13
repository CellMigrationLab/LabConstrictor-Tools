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
| `tests/roundtrip_known_failures.py` + `test_roundtrip_known_failures.py` | real defects found and not yet fixed (empty today: every finding F1 to F21 is fixed), and the watcher that keeps the list honest |
| `tests/test_input_loading.py` + `tests/input_app/` | how the worker reads an image input: the `order` of a shared-memory block (F read with the right strides on a non-symmetric array, anything but C/F refused) and the memory-mapped read of big TIFFs (mapped cases equal to `tifffile.imread`, every fallback, a tool that writes to its input, the mapping released after a failure) |
| `tests/test_retention.py` | `retention` and `labconstrictor-tools prune` ([SPEC_WRONG_SCIENCE.md](SPEC_WRONG_SCIENCE.md) 3.7: RET-01 to RET-09, RET-12, RET-13): a private `LC_HOME`, every survivor checked by the contents of a sentinel file, four real `prune` processes at once, a lock held by another process, symlinks (and on Windows junctions and read-only files; a link kind that cannot be made is reported as skipped, never as a pass) |
| `tests/test_conformance.py` | `conformance.json` and its loader ([CONFORMANCE.md](CONFORMANCE.md)): the schema (every kind of damage is named), the data against the code (limits, `compat` vectors, retention fixtures once `retention` exists), arithmetic oracles for the coordinate formula and the unit table, and the wheel contents |
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

## What runs when

| Trigger | Workflow | What runs |
|---|---|---|
| Pull request | `ci` | `lint`, then `compat` (Tools against its newest `v*` tag, see below; skips with a printed reason when there is no tag) and 4 test jobs: ubuntu 3.10, ubuntu 3.12 (coverage floor 85), windows 3.12 (plus the Windows-specific suite), macos 3.12 |
| Push to `main`, manual dispatch, nightly (03:17 UTC) | `ci` | `lint`, then `compat` and the full 3 OS x {3.10, 3.12} matrix, so Windows and macOS on 3.10 are still covered, at the latest the next night |
| Nightly (02:41 UTC), manual dispatch | `nightly` | heavy round-trip profile on 3 OS, mutation testing |
| Manual only (`smoke` also on pushes to `claude/smoke-bridge`) | `smoke`, `smoke_install`, `smoke_migration`, `release_sandbox` | end-to-end, install, template-migration and released-app smoke tests: **dispatch-only, no schedule and no pull-request trigger**, so nothing runs them unless a person starts them (a default that names a deleted branch is only found at the next run). `smoke_migration`: an old install of an app (default NucleiSky) gets the template migration, is updated, checked and uninstalled |

**Which smoke workflows default to branch names.** These defaults move or disappear, so a result is only as reproducible as the ref you pass:

| Workflow | Input | Default |
|---|---|---|
| `smoke_install` | `app_ref` | the branch `bridge-test` of `CellMigrationLab/CellTracksColab` |
| `smoke_migration` | `template_ref` | `main` of `CellMigrationLab/LabConstrictor` |
| `smoke_migration` | `app_ref` | the branch `claude/merge-bridge-test` of `CellMigrationLab/NucleiSky` |
| `smoke_migration` | `old_template_ref` | a commit (`900d0cac...`, template 0.1.15): fixed |
| `release_sandbox` | `napari_ref`, `fiji_ref`, `qupath_ref` | `main` of `LabConstrictor-napari`, `LabConstrictor-Fiji`, `labconstrictor-qupath`; pass a tag to pin (`fiji_ref` and `qupath_ref` go to `git clone --branch`: a branch or a tag, not a commit) |
| `release_sandbox` | `tools_pin`, `tag` | the tag `v0.3.0-alpha.1` of Tools, a release tag of the app: fixed |

Third-party actions (not by GitHub) are pinned by full commit SHA with the version in a comment (today only `conda-incubator/setup-miniconda`); GitHub's own `actions/*` are pinned by major tag. Their pip dependencies in the sandbox are not pinned.

Why: a PR branch push used to run both the `push` and the `pull_request` trigger, each with 6 test jobs, and a superseded push kept
running. Now `push` is limited to `main`, a newer push to the same ref cancels the older run (never on `main`), the test jobs wait for
`lint` (about 30 s) so a lint failure costs one runner instead of six, and the PR matrix drops only the combinations where a 3.10-only
or 3.12-only difference is rare (Windows/macOS 3.10). Every job has `timeout-minutes: 60` and pip is cached. The matrix choice is the
`include` expression in `ci.yml`. The cost: a failure that exists only on Windows or macOS with Python 3.10 reaches `main` unseen (the wheel test on an old
setuptools did exactly that, 2026-10-12), because pull requests do not run those two jobs. To run the full matrix on a branch before merging, start `ci` by hand:
`gh workflow run ci.yml --ref <branch>` (or Actions, ci, Run workflow, pick the branch); a `workflow_dispatch` run is not a `pull_request` event, so it gets all 6 test jobs.

## How to add a case

1. A new **value** of an existing type: add a row to the generator of that type in `tests/roundtrip_cases.py` (for instance an entry
   in `STRINGS`, `INT_OK`, `FLOAT_OK`, a frame in `table_frames`, a polygon in `shapes_cases`). Say what must come back by building
   the `Expect` from the input with plain Python (`scalar_report(value)`, `array_report(a)`, `table_report(frame)`, `expected_image_out(a)`).
2. A new **type or hint**: add an echo tool to `examples/roundtrip.py`, a generator of cases, and (for a marker) a row in
   `INPUT_MARKERS` / `OUTPUT_MARKERS` of `tests/test_roundtrip_hints.py`. `test_roundtrip_cases.py` and `test_roundtrip_hints.py`
   fail when a declared type, tool or marker has no case.
3. Run `python -m unittest test_roundtrip_matrix`. If the case fails and the production code is wrong, do not weaken the case:
   see "Known failures". If the expectation was wrong, fix the oracle, not the tolerance.

## The Playground rule

Every new feature or limit needs (1) a tool or case in the Playground app (a tool in its feature tour and a case in "Check the bridge"), (2) a generated case in the round-trip matrix, and (3) the host GUI check, before its pull request is done. **Where it is checked:** (2) is enforced by tests in this repository (`test_roundtrip_cases.py` and `test_roundtrip_hints.py` fail when a declared type, tool or marker has no case); (1) and (3) live in other repositories and run in `release_sandbox` with `playground_extras` (the Playground's own tool runs, the Fiji and QuPath host runs) and in each host's own suite; nothing in Tools fails when (1) is missing, so a reviewer checks it by hand from the pull request description (feature, Playground tool or case, matrix case, ledger row when it fixes a defect). A change with no Playground case says why (a host-side API, a performance feature).

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
* **Sabotage** (`tests/test_sabotage.py`, Linux, minutes: the breaks run in parallel): for each production function **in the table** (the converters, retention, runs, the worker, conformance; not every module has a row yet, for example `log.hint_for_exit` and the registry trust checks do not), a copy of the
  package gets one deliberate break (a flipped comparison, x and y swapped, a case dropped), the guarding slice of the matrix runs
  against the copy, and it **must fail**. A break that survives fails the test and is named. To guard a new function add a row.
* **Mutation testing** (nightly, `.github/workflows/nightly.yml`): `mutmut` on `convert.py`, `introspection.py`, `shapes.py`,
  `region.py` and `command.py`, with the round-trip tests as the test command; the surviving mutants are uploaded as an artifact.
  Each survivor is a missing test.

## Compatibility with the last tag
CI job `compat` installs the newest `v*` tag (sorted with `versionsort.suffix=-alpha` and `-rc`, so a final `v0.3.0` beats its own pre-releases and `-alpha.1` beats `-rc.2`) next to the checkout (when there is none it prints why and passes) and runs `tests/compat_matrix.py --old-python <old interpreter>`: the schema each Tools writes is read by the other's registry loader, a host that needs 0.2 refuses a frozen 0.1 schema (`tests/fixtures/schemas/`, never edited, a new file per Tools version), and each worker accepts the other's requests (reserved inputs one way, none the other). `tests/test_compat_matrix.py` runs the same script against the test interpreter on every system, so the script cannot rot between tags. Hosts will run their own suites against {Tools main, last tag} (host side, later).

## Release sandbox (a released app, on fresh runners)

`.github/workflows/release_sandbox.yml` (dispatch only) tests an app **as a person gets it**: the installers of a GitHub release are downloaded
(nothing is built), installed silently as a plain user into a fresh prefix with a scratch `LC_HOME` on fresh Linux, macOS (Apple silicon) and
Windows runners, exercised, and uninstalled. Run it from Actions, "release-sandbox", or `gh workflow run release_sandbox.yml -f app_repo=<owner/name> -f tag=<release> [-f old_tag=<older release>]`.

| Input | Meaning |
|---|---|
| `app_repo`, `tag` | the released app and release under test (its `.sh` / `.exe` installers are downloaded) |
| `old_tag` | optional older release of the **same** app: install it, make user data, update (Linux `installer.sh -u` in place; macOS and Windows uninstall, then install, as the user docs say), check, uninstall |
| `tools_pin` | tag of labconstrictor-tools the installed app must carry (empty: not checked). With `playground_extras` the Playground check of the installed Tools uses the same pin; when empty it reads the pin from the installed app's own `post_install` line (`LC_TOOLS_SPEC`) instead of a constant |
| `hosts_napari`, `napari_ref` | run the Napari host check on all three systems (software OpenGL on macOS and Windows); `napari_ref` is the branch or tag of the plugin (default `main`) |
| `fiji_ref`, `qupath_ref` | branch or tag of the Fiji and QuPath repositories cloned for the host runs of `playground_extras` and `hosts_qupath` (default `main`) |
| `playground_extras` | LabConstrictor Playground only: its own tool runs and failure paths (`playground_extras.py`), the Fiji host (Linux) and, with `hosts_qupath`, the QuPath host (Linux) |

What is checked, for **any** app (the expectations come from the app, not from the workflow: `construct.yaml`, the registered schema and
`lc_tests/cases.json`; `sandbox_checks.py`):
1. the installer exits 0; `menuinst_debug.log` ends with "Post-install completed successfully." and shows the tools were registered (the `.sh` hook prints "Tools registered", the `.bat` hook "registering the tools of ...");
2. `labconstrictor-tools list` shows every tool of the app's schema at the release version; `doctor` is clean; the installed Tools is the pin;
3. every case of `lc_tests/cases.json` through the worker (`labconstrictor-tools test`), every COMPLETE/FAILED case again through the command line, a notebook form for every tool, and the tools that have no case are named;
4. retention: 60 command-line runs of the first COMPLETE case leave exactly the newest 20 result folders (each with `.lc-owner.json` and `.lc-done.json`) and 50 run records, and `prune --dry-run --json` reports keep 20 / 50, nothing deleted, a user's own folders left alone;
5. uninstall removes the registry entry and the prefix and nothing else of the user's (planted files in the home folder, in `LC_HOME/results`, another app's registry entry);
6. update from `old_tag` keeps user data (results in `LC_HOME`, files in the home folder and, for the in-place Linux update, a file in the prefix);
7. Windows: the installer **refuses** a destination folder whose path contains a space (the constructor default `check_path_spaces`; kept on purpose, documented). In silent mode only the exit code (2) and "nothing written" can be asserted; a UI Automation read of the wizard's text ("Destination Folder contains 1 space") is attempted and reported as a note when it works; no `cmd.exe` syntax error in `menuinst_debug.log`; the registered version is the release's, not `(0)`; no python.exe of the app is left after the Napari host (W5) or after worker processes are closed.

The Napari host check (`napari_check.py`) opens the dock widget, requires the app and every tool of its schema to be listed and, for the Playground, runs
the stress scenarios (cancel, an ignored cancel is shown as "cancelled (worker stopped)", a crash, a layer that changes size during a run).
**Software OpenGL on Windows:** Mesa llvmpipe as in the Napari CI. A venv's `python.exe` is only a launcher that starts the base interpreter, and Windows
looks for `opengl32.dll` next to the process image: copy the Mesa DLLs next to `sys._base_executable`, not next to the venv's `python.exe`
(otherwise Qt gets "GDI Generic" OpenGL 1.1 and napari stops with `GLError 1280 invalid enumerant`).

Not covered: Fiji and QuPath on macOS and Windows (their GUI test runners need Xvfb), Intel Macs, the `.pkg` and `.msi` installers, installers into a path with a space.

## Platforms

Linux, macOS and Windows run the whole set except the sabotage test (Linux only) and the POSIX-only checks (SIGKILL, shared-memory
ownership, children after the host went away, which skip on Windows). Anything specific to a platform is guarded with `os.name`.
