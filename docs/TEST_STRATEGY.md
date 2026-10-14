# Test strategy: what a user needs, what we test, what a person still has to judge

Status: **proposal, 14 Oct 2026** (first reassessment after the alpha tags). The aim: bugs are found by machines, with evidence a person can
review in minutes; a human tester spends time only on what a machine cannot judge. Where this file and [HUMAN_TEST_PROTOCOL.md](HUMAN_TEST_PROTOCOL.md)
or [TESTING.md](TESTING.md) disagree, this file is the plan and the others are changed to match it.

## 1. What a user needs (the journeys the tests must cover)
| # | Journey | The user's question |
|---|---|---|
| J1 | Install the app (Windows, macOS Apple silicon, Linux) | "Did it install, without a terminal?" |
| J2 | Open the app's notebook and run it | "Does the notebook run?" |
| J3 | Open a tool in Napari, Fiji or QuPath | "Is my app there, with every tool, and does the form make sense?" |
| J4 | Fill the form (image, file, numbers, choices, calibration) and press **Run** | "Does it run and show the result on the right image?" |
| J5 | Press **Cancel**, close the window, close the host mid-run | "Does it stop, and leave nothing running?" |
| J6 | Read an error or a refusal | "Do I know what to do?" |
| J7 | Use a result later (files kept, run record, Copy as command) | "Can I find and repeat it?" |
| J8 | Update and uninstall | "Is my data kept, is everything else gone?" |
| J9 | Rely on the number | "Is it scientifically right (calibration, frame, no silent rounding)?" |
| J10 | Open each notebook the app ships | "Does every notebook open in the app's environment and run?" |
| J11 | Do my usual analysis in the plugin instead of the notebook | "Does the plugin give the same answer as the notebook workflow I know?" |
| J12 | Install a second app next to the first | "Are both there, each with its own tools, and does one not break the other?" |

## 2. What proves what today, and the gaps
| Layer | Proves | Where | Automated |
|---|---|---|---|
| Tools unit and round-trip tests | protocol, worker, retention, CLI, forms of the example app on all hosts | Tools `tests/`, `roundtrip_*` | yes (CI) |
| Host GUI suites | each host's form, run, cancel, results, calibration, frames | Napari `tests/`, Fiji `tests/cases`, QuPath `tests/gui_test_*` | yes, with the **example** apps |
| Release sandbox | the **released installer** installs, registers, runs the app's `lc_tests`, retention, uninstall, listed or hidden per host | Tools `release_sandbox.yml` | yes, Linux full, macOS and Windows partial |
| Human protocol | everything above again, by hand | `HUMAN_TEST_PROTOCOL.md` | no |

Gaps found (each is a bug waiting for a tester):
1. **The released apps are never driven through the host windows.** The host suites use example apps; the sandbox checks listing and CLI runs, not the form of
   NucleiSky's, Guess the Condition's or VLab4Mic's real tools in Napari, Fiji and QuPath.
2. **No rule that every control is exercised.** A new button or a changed form control is untested until someone adds a case. Nothing fails when a control exists that no test touches.
3. **Screenshots exist only in ad-hoc runs.** A release has no set of pictures a person can review in five minutes.
4. **The human protocol repeats machine checks** (install, listing, run, cancel), so testers spend their time re-finding what CI already knows and have less for what only a person can judge.
5. **Windows and macOS GUI are only smoke-tested** (the Fiji and QuPath drivers run on Linux/Xvfb). Known limit; stated, not hidden.
6. **The update path (`old_tag`) is optional and off by default.**
7. **The packaged notebooks are never opened by a test.** An app can ship a notebook that fails at its first import and every check stays green.
8. **No check that the plugin reproduces what the notebook does.** Tools and notebooks can drift apart (different defaults, different units) unnoticed.
9. **Two apps installed together are never tested.** Every sandbox run installs one app into a clean prefix.
10. **A run stops being useful after its first red line.** Testers (and CI) see one failure at a time; a night of work is lost to a crash or to running out of credits.

## 3. The UI audit (new): press every control, screenshot every tool
One driver per host, in the host's own repository, started by `release_sandbox.yml` against the **installed** app (same environment variables as the listing
drivers, see `tests/release_sandbox/README.md`). Linux, Xvfb.

### 3.1 What a driver does
1. **Enumerate every control** of the host panel (Napari: Qt widgets of the dock widget; Fiji: the Swing/SciJava components of the dialog and the plugin menus; QuPath: JavaFX nodes of the stage). Each control has an entry in the host's **control table** (id, kind, expected effect). A control found that is not in the table is a **FAIL**: a new button forces a new test.
2. **Activate each panel control** and assert the effect in the table: `Run`, `Cancel`, `Details`, `Rescan apps`, `Restart worker`, `Keep the worker running`, `Copy as command` (every entry), the app and tool choosers, and whatever the host has beyond these. A control that is correctly a no-op in a state (Cancel with nothing running) asserts exactly that.
3. **For each tool of the app**: open its form; check one widget per declared parameter, of the declared kind (number, text, choice, image, labels, file, folder, optional switch, calibration); activate every form control (browse, `Use the image's calibration`, pick-channel, enabled-when switches, choices-from dropdowns); read back the state.
4. **Run it**, with inputs from the app's own `lc_tests/cases.json` (first case of the tool, fixtures in `lc_tests/fixtures`). Assert: status complete, every declared result shown (images, labels, points, shapes, tables, messages, files) with the counts the case states; the log and run record exist. A tool listed in `lc_tests/no_case.json` gets form checks only, and the NOTE says so.
5. **Screenshot** the host window: form before the run, after the run, and the result view. Files `screens/<host>/<app>/<tool_id>_form.png`, `_after_run.png`. A screenshot that is missing, empty or one flat colour is a FAIL.
6. Print one `CHECK` line per assertion and exit non-zero on FAIL (same contract as the listing drivers). Never skip silently: anything not run prints `NOTE <id> not run: <reason>`.

### 3.2 Check ids (all prefixed `ui_<host>_`, host = `napari` | `fiji` | `qupath`)
| Id | Passes when |
|---|---|
| `ui_<host>_controls_all_known` | every control found is in the host's control table (FAIL names the unknown ones) |
| `ui_<host>_panel_<control>` | the panel control did what the table says |
| `ui_<host>_form_<tool>_opens` | the form shows one widget per declared parameter, right kind |
| `ui_<host>_form_<tool>_controls` | every control of the form was activated, no error, state as expected |
| `ui_<host>_run_<tool>` | the run completed and showed every declared result |
| `ui_<host>_screens_<tool>` | the form and after-run screenshots exist and are not blank |

`required_checks.json` lists the ids per host and app; a missing id is red (the existing missing-line guard).

### 3.3 The app dimension
Run for the five apps of the matrix (`expected_hosts.json`): the audit runs in each host that **lists** the app, and for a host that must **not** list it
the driver asserts that the app is absent from the chooser and prints no form checks (this is the CellTracksColab case: bridge module present, hidden).

### 3.4 Evidence a person reviews
The sandbox uploads `screens/` and writes one **contact sheet** per app and host (a grid of all screenshots with the tool names). Review = look at the sheets; this replaces the visual part of the human protocol.


### 3.5 Run discipline: one app per run, never stop, write a matrix, push as you go
* **One app at a time (session S1).** Each app is installed alone in a clean prefix and tested alone; nothing from another app can mask a failure.
* **Never stop at a failure.** Every assertion of every check family (UI audit, notebooks, workflows, sandbox checks) is guarded: an exception or a timeout becomes a `FAIL` row with the error text and the run goes on. Per-tool and per-notebook timeouts (default 300 s) stop a hang from blocking the night. Only a crash of the whole runner ends a leg, and the rows already written stay valid.
* **The matrix.** Every check writes a row to `matrix_<family>_<host>_<app>.json` immediately (atomic rewrite): `{id, family, host, app, tool|notebook, control, status PASS|FAIL|NOTE, detail, seconds, screenshot}`. An aggregator turns all matrices of a release into `RESULTS.md` (apps x hosts x families, counts, every FAIL with its detail and screenshot) so the review happens once, after everything ran.
* **Push as you go.** Results must survive a failed job, a cancelled night or an empty credit balance. Each leg (a) uploads its artifacts `if: always()`, and (b) runs a background loop that commits `results/<release-run-id>/` to the branch `test-results` of this repository every 10 minutes and once more at the end (`contents: write`, only that branch, never `main`). The aggregator job also runs `if: always()`.
* **Overnight orchestration.** One dispatch workflow `release_matrix.yml`: legs `S1` per app (`max-parallel: 1`, `fail-fast: false`), then `S2`, then the aggregator. The workflow is dispatch-only (as `release_sandbox.yml`); nothing in it tags, releases or deletes anything.

### 3.6 Two or more apps installed together (session S2)
Install the apps into separate prefixes that share one `LC_HOME` (as a user who installs a second app does) and assert, per host:
* every installed app is listed, each with exactly its own tools (`multi_lists_<app>`), and switching between them shows the right tools (`multi_switch_<A>_<B>`);
* an app that must not be listed in this host stays hidden while the others are listed (CellTracksColab);
* tools with the same display name in two apps do not clash (each runs its own app's code);
* running a tool of A while B is registered, uninstalling B, and updating B leave A listed and runnable (`multi_isolation_<A>_<B>`);
* the registry holds one entry per app, `doctor` is clean.
Sessions: all five apps together, and the pairs that share tool names or the same scientific stack (found by comparing the schemas).

### 3.7 Notebooks (family `nb`): every packaged notebook
Each app ships notebooks (listed in `construct.yaml` `extra_files`, plus the app's `Welcome.ipynb`). For **every** one, in the installed app's own environment, per notebook:
| Id | Passes when |
|---|---|
| `nb_<app>_<nb>_packaged` | the file is in the installed prefix and byte-equal to the file at the release tag |
| `nb_<app>_<nb>_valid` | nbformat validation passes and the kernel resolves to the app's interpreter |
| `nb_<app>_<nb>_imports` | every import of the notebook resolves in the installed environment (import cells run, nothing else) |
| `nb_<app>_<nb>_runs` | the notebook runs top to bottom headless (nbclient, `allow_errors`, per-cell timeout) with the data its tests provide; each failing cell is a row with its error. A cell that waits for a person (a widget with no default) is a `NOTE` naming the cell, not a silent pass |
A notebook that needs real data or a GPU is run as far as the fixtures allow; the cells it cannot run are listed, never hidden. Notebook runs that need the network (data download) say so in the row.

### 3.8 Does the plugin reproduce a typical workflow? (family `wf`)
For each app, Tools holds (in `tests/release_sandbox/workflows/<app>.json`, never in the app repository) the **typical workflow** the app's own notebook teaches, expressed as an ordered chain of tool runs with fixture inputs. Per workflow:
* `wf_<app>_<workflow>_chain`: the chain runs through the CLI/worker and, in each host, through the real form (UI audit machinery), every step completing and showing its results.
* `wf_<app>_<workflow>_matches_notebook`: where the app ships an API/workflow notebook (e.g. NucleiSky `*_API_Workflow_Example`, Guess the Condition `API_Example`), the numeric outputs of the chain equal the notebook's (stated tolerance).
* `wf_<app>_<workflow>_coverage`: a **report, not a pass/fail**: which notebook steps have a plugin tool and which have none (the plugin is allowed to cover less than the notebook; the gap must be known). CellTracksColab is expected to report "plugin covers: 1 tool (calculate_metrics); not exposed in any host".

## 3.9 What each family proves
`ui` = the host windows work; `nb` = the notebook the user opens works; `wf` = the plugin and the notebook tell the same story; `multi` = apps coexist; the sandbox checks = the installer and the registry are right. Together with the contact sheets, a person reviewing `RESULTS.md` sees every failing cell of the matrix with its evidence.

## 4. What stays human
Only what a machine cannot judge:
* Is the scientific result plausible for real data (not the fixtures)?
* Are the sentences, labels and errors understandable to a biologist? (Review the screenshots.)
* Installer screens on Windows (SmartScreen, wizard) and macOS (Gatekeeper, .pkg), and a real-size dataset run.
* Anything the contact sheets show that looks wrong.

Everything else in `HUMAN_TEST_PROTOCOL.md` (install check, listing, run, cancel, retention) is removed from the human list once its automated id is green on the release.

## 5. Order of work
| # | Step | Where | Status |
|---|---|---|---|
| 1 | This strategy | Tools | written |
| 2 | Napari UI audit driver | napari repo | to do |
| 3 | Fiji UI audit driver | Fiji repo | to do |
| 4 | QuPath UI audit driver | QuPath repo | to do |
| 5 | Sandbox wiring, required ids, contact sheet, matrix aggregator, `test-results` push loop | Tools | to do |
| 6 | Notebook family `nb` (runner + per-app notebook list) | Tools | to do |
| 7 | Workflow family `wf` (per-app workflow definitions, comparison with the API notebooks, coverage report) | Tools | to do |
| 8 | Multi-app session S2 | Tools + hosts | to do |
| 9 | `release_matrix.yml` overnight orchestration | Tools | to do |
| 10 | **Adversarial audit of this plan** (independent reviewer, before building 5 to 9) | Tools | to do |
| 11 | Run on the five released apps; review `RESULTS.md`; fix what it finds; trim the human protocol | all | to do |

Limits we accept: Linux only for the UI audit; fixtures, not real data; a control table is only as good as its author, which is why an unknown control fails.
