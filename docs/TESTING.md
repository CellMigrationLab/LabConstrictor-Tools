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
| `tests/audit/` and `tests/test_audit_*.py` | the audit tooling of [TEST_STRATEGY.md](TEST_STRATEGY.md) (section 0.1): result matrix, round-separating collector, runners for installed apps, the notebook click-script runner, synthetic datasets with ground truth, host launchers. Not collected and not run in CI (they need installed apps and hosts); linted, formatted, annotated and type-checked like the rest. The `test_audit_*.py` files test the parts that need no app (matrix statuses, round separation, script lookup, synthetic truths) and do run in CI |
| `scripts/check_annotations.py`, `scripts/verify_annotation_only.py` | dev tools, not tests: the annotation check that runs in the `lint` job, and the proof that a change touched annotations only (see "Annotations and type checking") |

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
| Pull request | `ci` | `lint` (black, ruff, the annotation check, mypy, vulture), then `compat` (Tools against its newest `v*` tag, see below; skips with a printed reason when there is no tag) and 4 test jobs: ubuntu 3.10, ubuntu 3.12 (coverage floor 85), windows 3.12 (plus the Windows-specific suite), macos 3.12 |
| Push to `main`, manual dispatch, nightly (03:17 UTC) | `ci` | `lint`, then `compat` and the full 3 OS x {3.10, 3.12} matrix, so Windows and macOS on 3.10 are still covered, at the latest the next night |
| Nightly (02:41 UTC), manual dispatch | `nightly` | heavy round-trip profile on 3 OS, mutation testing |
| Manual only (`smoke` also on pushes to `claude/smoke-bridge`) | `smoke`, `smoke_install`, `smoke_migration`, `release_sandbox` | end-to-end, install, template-migration and released-app smoke tests: **dispatch-only, no schedule and no pull-request trigger**, so nothing runs them unless a person starts them (a default that names a deleted branch is only found at the next run). `smoke_migration`: an old install of an app (default NucleiSky) gets the template migration, is updated, checked and uninstalled. People test by hand with the [human test protocol](HUMAN_TEST_PROTOCOL.md) |

**Which smoke workflows default to branch names.** These defaults move or disappear, so a result is only as reproducible as the ref you pass:

| Workflow | Input | Default |
|---|---|---|
| `smoke_install` | `app_ref` | the branch `bridge-test` of `CellMigrationLab/CellTracksColab` (branch exists, checked 14 Oct 2026; it is the held bridge branch, not `main`, which registers no tools) |
| `smoke_migration` | `template_ref` | `main` of `CellMigrationLab/LabConstrictor` |
| `smoke_migration` | `app_ref` | the branch `claude/merge-bridge-test` of `CellMigrationLab/NucleiSky` (branch exists, checked 14 Oct 2026 in the GitHub branch list; the bridge it carried is now on NucleiSky `main`, so the branch is only a leftover: if it is deleted the default breaks and `app_ref` must be `main` or a tag; `.github/workflows/smoke_migration.yml` lines 31 and 67) |
| `smoke_migration` | `old_template_ref` | a commit (`900d0cac...`, template 0.1.15): fixed |
| `release_sandbox` | `napari_ref`, `fiji_ref`, `qupath_ref` | `main` of `LabConstrictor-napari`, `LabConstrictor-Fiji`, `labconstrictor-qupath`; pass a tag to pin `fiji_ref` and `qupath_ref` (they go to `git clone --branch`: a branch or a tag, not a commit). `napari_ref` is put into `.../archive/<napari_ref>.zip` (`release_sandbox.yml`, step "Napari host check"), which GitHub resolves for a branch and for a tag (checked with `curl` for `main` and for a tag of this repository, not by a sandbox run) |
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

## Annotations and type checking

**The rule: every function, method and nested function is annotated, in the package, the tests, the example apps and the scripts:
every parameter except `self` / `cls`, `*args` and `**kwargs` included, and the return type, `-> None` included.** No blanket `Any`
where the type is known; `Any` is for values that really are anything (a JSON value, the keyword arguments passed on to another call).

How it is checked (both in the `lint` job of `ci`, the first one is the quick one):

* `python scripts/check_annotations.py` reads the files with `ast` (it imports nothing) and lists every function that misses an
  annotation, per file and line. It covers `labconstrictor_tools`, `tests`, `scripts` and `fixtures`; `--summary` prints the count per
  file. The one allowed exception is a function that is unannotated on purpose, because the test is about declaring a tool without
  annotations: write `# lc-annotations: skip - <reason>` on its `def` line (today: `bad1` in `tests/test_introspection.py`).
* `mypy` (no arguments: paths and flags are in `pyproject.toml`, `[tool.mypy]`) checks the same four folders with
  `disallow_untyped_defs` and `disallow_incomplete_defs`, `warn_unused_ignores` and the unresolved-name checks. The package is checked
  completely, as before. The example apps and the tests are checked completely **except** the error codes listed in the second
  `[[tool.mypy.overrides]]` block, which belong to how tests are written: the semantic marker types (`Image`, `Table`, `Scalars`) are
  classes that an annotated tool function can never match, tests hand deliberately partial or invalid schemas to the code under
  test, and they read pipes of a `Popen` they just opened. Shrinking that list is future work; removing a code from it and fixing what
  appears is the way to do it.

Rules for adding annotations (they must never change what a program does):

* An annotation that is evaluated when the `def` runs may only use names that exist at run time. A name that is needed only for
  the type goes under `if TYPE_CHECKING:` and the annotation that uses it is written as a string (`-> "Any"`).
* Do **not** add `from __future__ import annotations` to a file that does not have it. It turns every annotation of the file into a
  string, and the tools declared in a test (and the functions a test passes to `describe_tool`) are read with
  `typing.get_type_hints`, which cannot resolve names of the enclosing function. The `@tool` functions of the examples and of the test
  apps keep exactly the annotations their schema needs.
* A `# type: ignore[code]` needs a reason on the same line.
* `python scripts/verify_annotation_only.py` (a dev tool, not part of CI) is the proof for a change that claims to touch
  annotations only: it removes annotations, `TYPE_CHECKING` scaffolding and `from __future__ import annotations` from the old and the
  new version of every changed `.py` file and compares the syntax trees with `ast.dump`; any difference is listed. Compare the
  schemas too: `python -m labconstrictor_tools describe --module <module>` for each example and test app before and after must be
  byte for byte the same.

## Known failures

A defect the matrix finds is not fixed in the same PR. Its test ids go into `tests/roundtrip_known_failures.py` under a finding
(minimal reproduction, expected behaviour, observed behaviour). The runners skip exactly those ids; `test_roundtrip_known_failures.py`
runs them again and **fails when one starts to pass**, so the fix PR must delete the entries, and the list cannot rot. Keys:
`<transport>:<case id>`, `property:<name>`, `hint:<id>`, `failure:<tool>`, `lifecycle:<name>`, `test:<module.Class.method>`,
`winquote:<label>`, `winproc:<label>` (the real Windows process start). A finding can be limited to a Python version (`min_python`) or machine type (`machines`): F20 only on ARM.

## Known CI flake

Napari Windows PySide6 test jobs crashed intermittently (about 6% of jobs) after printing `FAILURES: none`, when the test process called `os._exit` with the viewer still open. Root cause found by experiment on 14 Oct: closing the viewer first gave 0 fatal crashes in 90 runs, the control 6 in 60.

**Status: fixed in the test that crashed, not observed since; watch.** Napari PR #62 is merged (9e5f24c): the viewer is closed before `os._exit`. After the merge the Windows PySide6 job passed 4 of 4 and `test_calibration_transitions.py` printed no fatal-exception line. The crash rate after the fix is **not measured**; 4 passes prove little. A loop of 15 runs is a regression guard, not a proof. If a job crashes again after `FAILURES: none`, a rerun passes and the product assertions are true, but report it here.

Five scripts still print the first-chance line `Windows fatal exception: access violation` (`test_async_close`, `test_parity_copy_notes`, `test_parity_region`, `test_region`, `test_retention_exit`). They all exit 0 with `FAILURES: none`; the line is harmless as far as seen, and its cause is not investigated.

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
| `old_tag` | optional older release of the **same** app: install it, make user data, update (Linux `installer.sh -u` in place; macOS and Windows uninstall, then install, as the user docs say), check, uninstall. The Linux `-u` works only if the previous install finished: after a failed install the update breaks (conda-standalone) until `<prefix>/pkgs` is deleted or the app is uninstalled ([INSTALL.md](INSTALL.md)) |
| `tools_pin` | tag of labconstrictor-tools the installed app must carry (empty: not checked). With `playground_extras` the Playground check of the installed Tools uses the same pin; when empty it reads the pin from the installed app's own `post_install` line (`LC_TOOLS_SPEC`) instead of a constant |
| `hosts_napari`, `hosts_fiji`, `hosts_qupath` | choice `auto` (default) or `skip`: `auto` runs that host's check and asserts "listed" or "not listed" as the app's expectation says (Napari on all three systems, software OpenGL on macOS and Windows; Fiji and QuPath on Linux); `skip` does not run it |
| `napari_ref`, `fiji_ref`, `qupath_ref` | branch or tag of the Napari, Fiji and QuPath repositories (default `main`). `napari_ref` is fetched as `.../archive/<ref>.zip`, which GitHub resolves for a branch and for a tag alike (a tag and a branch of the same name in one repository: which one wins is not verified) |
| `expected_fail` | CHECK ids that are expected to be red in this run, comma separated (default empty). The verdict step ignores exactly these ids and prints a `NOTE` with them (and a `NOTE` for each that did not fail), so a run on an old release says what it expects to be red and an expected failure is never silent |
| `expected_hosts` | optional override of the expected hosts, e.g. `notebook,fiji`; empty: the row of the app in `tests/release_sandbox/expected_hosts.json` (an app without a row fails the run) |
| `playground_extras` | LabConstrictor Playground only: its own tool runs and failure paths (`playground_extras.py`) and its Fiji and QuPath tool cases (Linux); the listing checks of Fiji and QuPath run for any app |

**Verdict.** The steps end in `|| true` so that one failing step does not stop the others; the last step, "Verdict", is what turns the job red (`tests/release_sandbox/verdict.py`, tested by `tests/test_release_sandbox_verdict.py`). First the step "Summary of every CHECK line" collects every `CHECK` line into `all_checks.txt` and runs the guard: each id of `tests/release_sandbox/required_checks.json` (basic, hosts, cases, retention, uninstall, Windows-only; separate lists for an app without tools and for Windows versus Linux and macOS) that has no `CHECK` line becomes `CHECK missing_<id> FAIL expected CHECK line never printed`. Then, after the artifacts are uploaded (`if: always()`), the verdict step fails the job when any `CHECK <id> FAIL` line is left, except the ids of `expected_fail`; no `CHECK` line at all is red too. `NOTE` lines never gate (for example the Windows wizard message, `W1b`), the exit code of the Windows uninstaller (2, the NSIS conda step) is not a `CHECK` and does not gate, and a `continue-on-error` step does not fail the job by itself; the `CHECK ... FAIL` lines it printed do (Napari, Fiji, QuPath, `W1a`). Not guarded against a missing line: the Napari, Fiji, QuPath and Playground-extras checks (their steps print a FAIL when a driver printed no `CHECK` line) and the update test (`old_tag`); its lines do gate when they print FAIL.

What is checked, for **any** app (the expectations come from the app, not from the workflow: `construct.yaml`, the registered schema and
`lc_tests/cases.json`; `sandbox_checks.py`):
1. the installer exits 0; `menuinst_debug.log` ends with "Post-install completed successfully." and shows the tools were registered (the `.sh` hook prints "Tools registered", the `.bat` hook "registering the tools of ...");
2. `labconstrictor-tools list` shows every tool of the app's schema at the release version; `doctor` is clean; the installed Tools is the pin;
3. every case of `lc_tests/cases.json` through the worker (`labconstrictor-tools test`), every COMPLETE/FAILED case again through the command line, a notebook form for every tool, and every tool must have a case or be declared with a reason in the optional `lc_tests/no_case.json` (`{tool_id: reason}`; the Playground has one since its PR #29): an undeclared tool, a stale exemption (the tool has a case or is not in the schema) and a malformed file are FAIL; each exemption is a `NOTE 4_no_case_declared_<id>`; `4_no_case_tools_are_run_by_extras` requires the Playground extras to have run each exempt tool (a NOTE saying they were not run when `playground_extras` is false);
4. retention: 60 command-line runs of the first COMPLETE case leave exactly the newest 20 result folders (each with `.lc-owner.json` and `.lc-done.json`) and 50 run records, and `prune --dry-run --json` reports keep 20 / 50, nothing deleted, a user's own folders left alone;
5. uninstall removes the registry entry and the prefix and nothing else of the user's (planted files in the home folder, in `LC_HOME/results`, another app's registry entry);
6. update from `old_tag` keeps user data (results in `LC_HOME`, files in the home folder and, for the in-place Linux update, a file in the prefix);
7. Windows: the installer **refuses** a destination folder whose path contains a space (the constructor default `check_path_spaces`; kept on purpose, documented). In silent mode only the exit code (2) and "nothing written" can be asserted; a UI Automation read of the wizard's text ("Destination Folder contains 1 space") is attempted and reported as a note when it works; no `cmd.exe` syntax error in `menuinst_debug.log`; the registered version is the release's, not `(0)`; no python.exe of the app is left after the Napari host (W5) or after worker processes are closed.

The Napari host check (`napari_check.py`) runs in a venv with `napari[pyqt6]` (Qt6; `napari[pyqt5]` is not used: the plugin's README says PyQt5 is not tested) and the plugin from the branch `napari_ref`; it opens the dock widget, requires the app and every tool of its schema to be listed (or, when the expectation says "not listed", the app to be absent from the dropdown with the skip sentence in the Tools log) and, for the Playground, runs
the stress scenarios (cancel, an ignored cancel is shown as "cancelled (worker stopped)", a crash, a layer that changes size during a run).
**Software OpenGL on Windows:** Mesa llvmpipe as in the Napari CI. A venv's `python.exe` is only a launcher that starts the base interpreter, and Windows
looks for `opengl32.dll` next to the process image: copy the Mesa DLLs next to `sys._base_executable`, not next to the venv's `python.exe`
(otherwise Qt gets "GDI Generic" OpenGL 1.1 and napari stops with `GLError 1280 invalid enumerant`).

Not covered: Fiji and QuPath on macOS and Windows (their GUI test runners need Xvfb), Intel Macs, the `.pkg` and `.msi` installers, installers into a path with a space on Linux and macOS (on Windows it is tested, as a refusal: W1 above).

### Which apps and hosts the sandbox covers today

The discovery matrix (decided 14 Oct; binding rule in Tools, feature `app_hosts_v1`, Tools PR #133, merged; discovery rule: see PROTOCOL.md, section "App hosts (which host lists an app)") is in [HUMAN_TEST_PROTOCOL.md](HUMAN_TEST_PROTOCOL.md#3-which-host-shows-which-app-the-discovery-matrix): CellTracksColab hidden from Napari, Fiji and QuPath (notebook only); Guess the Condition, Playground and NucleiSky listed in all three; VLab4Mic listed in Napari and Fiji, not in QuPath. The sandbox reads the expectation from `tests/release_sandbox/expected_hosts.json` (the contract for the host drivers is in [tests/release_sandbox/README.md](../tests/release_sandbox/README.md)). What the workflow can assert (read from `release_sandbox.yml` and `tests/release_sandbox/`, 14 Oct 2026):

| Item | Today |
|---|---|
| Expectation per app | `expected_hosts.json` (one row per app: `hosts`, `repo`, `tools_module`); the `expected_hosts` input overrides it; an app with neither stops the run |
| Registry and Tools (`hosts_check.py`) | the entry the installer wrote declares the expected `hosts` (red for an installer that passes none), `listed_for` gives the expected answer for each host, `list` shows the declaration |
| Napari listing (`hosts_napari`, `auto`, all three systems) | any app: "lists the app" (with every tool of its schema) or "does not list the app" (a "not listed" assertion) plus the skip sentence in the Tools log |
| Fiji and QuPath listing (`hosts_fiji`, `hosts_qupath`, Linux) | any app, through a driver in the host repository (Fiji `tests/sandbox_listing.py`, QuPath `tests/gui_test_listing_body.groovy`; both are on the `main` of their repository); for a `fiji_ref` / `qupath_ref` that lacks its driver the workflow prints `CHECK fiji_listing_driver_present FAIL` / `CHECK qupath_listing_body_present FAIL`. Their tool cases still need `playground_extras` and only exist for the Playground |
| An app with no tools (CellTracksColab, tools module `optional`) | stated (`tools_module_absent_as_declared`); the tool, case and retention checks do not run; the sandbox asserts that nothing is registered or, if the installer registers a module, that its `hosts` is `[notebook]`; an app whose row says `required` and has no module stops the run |
| Apps run so far | which app each of the five `release-sandbox` runs on `claude/release-sandbox-run` tested: not verified |

The three hosts honour the rule (Napari #61, Fiji #47, QuPath #35: merged; no host has a tag, so the default `main` of each is the ref to use). What still fails is the registry check: it needs an installer that passes `hosts` (template 0.1.18, template PR #33: not merged, it waits for the Tools tag `v0.3.0-alpha.1`), so `hosts_1_registry_entry_declares_the_hosts` is red for every app released before that and the hosts list such an app everywhere.

A run on a release that predates these fixes states what it expects, e.g. `-f expected_fail=3_tools_version_is_the_pin,hosts_1_registry_entry_declares_the_hosts`: without the input the verdict step is red, with it the verdict is green and the NOTE lists the ids.

Only released installers can be tested (they are downloaded from the app's release), so an app is tested after its release with the new pin, with `tools_pin=v0.3.0-alpha.1`.

## Platforms

Linux, macOS and Windows run the whole set except the sabotage test (Linux only) and the POSIX-only checks (SIGKILL, shared-memory
ownership, children after the host went away, which skip on Windows). Anything specific to a platform is guarded with `os.name`.
