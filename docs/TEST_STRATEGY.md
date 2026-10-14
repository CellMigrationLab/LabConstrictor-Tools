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
| 5 | Sandbox wiring, required ids, contact sheet | Tools | to do |
| 6 | Run on the five released apps; fix what it finds; trim the human protocol | all | to do |

Limits we accept: Linux only for the UI audit; fixtures, not real data; a control table is only as good as its author, which is why an unknown control fails.
