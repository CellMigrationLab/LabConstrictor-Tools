# Findings of the one-off run (classified; nothing fixed until the owner reviews)

Classes: app bug, host bug, Tools bug, sandbox/runner bug, environment. Status: open until the owner decides.

## F-001 (Tools sandbox bug) `sandbox_checks.py cases` is not idempotent for apps whose COMPLETE case writes into the fixtures
* Where: tests/release_sandbox/sandbox_checks.py, function `cases`. It first runs `labconstrictor-tools test --cases cases.json` (the whole suite, which executes every case, including GuessTheCondition case 00 `create_demo_experiment` into `lc_tests/fixtures/results`), then runs each COMPLETE case again through the CLI.
* Evidence (GuessTheCondition 0.0.1, fresh fixtures, private copy of the checkout, no other process): `4_cases_suite PASS reports=22`, then `4_cli_case_00_create_demo_experiment_COMPLETE FAIL status=FAILED code=already_exists`. Run alone in a fresh copy, the same CLI call completes (COMPLETE, demo created).
* Effect: a correct app reports a failing case 00 and `6_runs_complete` FAIL. Would also fail in the GitHub release sandbox for this app.
* Needs: owner decision (regenerate the fixtures between the suite and the CLI phase, or give each phase its own copy).

## F-002 (Tools sandbox bug) the retention step repeats the first case 60 times, so it needs a repeatable first case
* Evidence: `6_runs_complete FAIL run 0 of create_demo_experiment ... already_exists`; the other retention ids (6a, 6b, 6d, 6e, 6f) were never produced and are NOT_RUN. GuessTheCondition's first case creates a folder that must not exist, so it cannot be repeated.
* Effect: the retention contract (markers, newest 20 results, 50 run records, prune) is unverified for Guess the Condition by the sandbox. It must be exercised through a repeatable tool (e.g. prepare_game) instead.
* Needs: owner decision (select the first repeatable COMPLETE case; add a `retention_case` hint to the case format, or exempt with a reason).

## Environment notes
* The user-level Jupyter kernelspec in this container (/root/.local/share/jupyter/kernels/python3) points to a stale interpreter; each installed app has its own kernelspec under <prefix>/share/jupyter. Notebook runs must pin the app's kernel.
* The first real installer run (Guess the Condition 0.0.1, Linux): 4.5 min, 1.2 GB; post-install passed `--app-manifest` to Tools; registered with hosts notebook, napari, fiji, qupath; `doctor` clean.

## F-003 (environment, not an app bug) retention check needs an exclusive LC_HOME
* `6b_results_keep_newest_20` asserts that the kept results are exactly the names of THIS run's last 20 results. In a shared registry (the one-off run installs several apps and runs agents in parallel) other tool runs interleave, so `kept=20` still reports FAIL (16 CellTracksColab results + 4 Guess the Condition results).
* Action taken in the runner: each sandbox family run registers the app into its own empty private LC_HOME (as a clean user would). Result of the rerun is in RESULTS.md.
* Note for the Tools sandbox: the check is only valid in an exclusive registry; that is true in CI (one app per runner), so no change is proposed.
* F-003 result: rerun of CellTracksColab 1.1.2 in a private LC_HOME: 31 PASS, 0 FAIL (registry hosts `notebook` as required, tool cases, retention 6a to 6f all pass). Confirms F-003 was the shared registry, not the app.

## GitHub release sandbox runs of 14 Oct 2026 (dispatched on Tools main at the host tags v0.1.0-alpha.1, Tools pin v0.3.0-alpha.1, no update test)
| App | Linux | macOS arm64 | Windows | Wall time of the slowest leg |
|---|---|---|---|---|
| NucleiSky 0.1.4 | green | green | green | Windows 49 min |
| LabConstrictor-Playground 0.0.4 (extras on) | green | green | green | Windows 33 min |
| LabConstrictor-VLab4Mic 0.1.6 | green | green | green | Windows 33 min |
| GuessTheCondition 0.0.1 | RED | RED | RED | 9 min (fails early) |
* GuessTheCondition is red on all three systems for exactly F-001/F-002 (`4_cli_case_00_create_demo_experiment_COMPLETE FAIL already_exists`, `6_runs_complete FAIL`), reproduced independently here and in CI: it is the sandbox design, not the app.
* What green means: the checks the sandbox has pass. It does not cover the host windows (Fiji and QuPath are only checked for listing), notebooks, or the scientific result of a tool beyond the app's own authored cases.

## Candidate host bugs from the Napari UI audit (agent-reported, reproduced by the agent, NOT yet verified by the parent; class: Napari host)
* **H-N1 Run button stays enabled while a tool runs.** The plugin sets `call_button.enabled = False`, but magicgui's `_disable_button_and_call` sets `enabled = True` in its `finally` right after the click handler returns (`_function_gui.py` lines 230-237), so a second click is silently ignored instead of being blocked. Repro: click Run on any tool and read `gui.call_button.enabled` immediately. The audit reports `ui_napari_panel_run FAIL` for this on Guess the Condition.
* **H-N2 Channel chooser stays empty for an RGB layer.** In the interactions example tool "Mean of a channel": add `viewer.add_image(zeros((8,8,3),uint8), rgb=True)` and pick it; the Channel box stays `['']`, while `w._refresh_channels("image")` called by hand lists Red/Green/Blue. HOST_PARITY C14 says an RGB layer's colours are offered; existing tests cover only RGB files.
* **H-N3 Stale group headings.** `_group_heading` is never cleared when a form is replaced (`_widget.py` lines 685-686), so headings of earlier forms persist.
* **H-N4 (not claimed)** a stale ChoicesFrom callback once raised "'FunctionGui' object has no attribute 'random_seed'" in a Qt slot in an audit variant; not reproduced by hand.
* Environment: the app's source tree under /home/user/apps/src had dirty fixtures from earlier runs by other processes (explains why the first sandbox runs hit `already_exists` there; F-001 stands because the private-copy runs fail the same way).

## F-001 and F-002: fix proposed and proven (owner chose "fix the sandbox in Tools"; PR opened for review, not merged)
* Branch claude/sandbox-idempotent-cases (0ff654f): fresh fixtures between the case phases; retention repeats the first case that runs twice.
* Real run on Guess the Condition 0.0.1 with the change: 46 PASS, 0 FAIL, 0 NOT_RUN (before: 37 PASS, 2 FAIL, 5 NOT_RUN). Negative control: the integration test fails against the old code.

## Synthetic datasets with ground truth (branch claude/oneoff-synthetic, 174 MB, deterministic): proofs and candidate app bugs
Proof state: Guess the Condition (installed app, real worker): all 109 synthetic cases match their `expect`, ground-truth check 146 PASS, 0 FAIL, 0 NOT_RUN. Playground and CellTracksColab were run from SOURCE (not the installed apps; CellTracksColab with matplotlib/ipywidgets stubbed): 162 PASS / 3 FAIL and 51 PASS / 2 FAIL. NucleiSky and VLab4Mic: generators validated only; tool runs pending the installs. Negative controls: 9 right results pass, 25 deliberately wrong results fail. Truth was fixed before each run and never adjusted to match a result (two corrections of the generator are documented in its report).
Candidate app bugs (agent-reported; to be re-run on the INSTALLED apps before they are called confirmed):
* **A-PG1 (Playground, silent wrong result)** `count_above_level` on a float image with one NaN pixel, percentile mode: COMPLETE with `pixels: 0, level_used: None`.
* **A-PG2 (Playground, silent wrong result)** `bright_area` on a rectangle with one NaN pixel: COMPLETE with `area_um2: 0.0` (truth 150 or a refusal).
* **A-PG3 (Playground, doc mismatch)** `make_test_data` three_channels: docstring says channel means 10, 20, 30; the file has 42.7, 20, 30 (channel 0 includes the nuclei).
* **A-CT1 (CellTracksColab, no validation)** `calculate_metrics` with one infinite coordinate: COMPLETE with infinite speeds and distance.
* **A-CT2 (CellTracksColab, product decision)** two spots at the same time: COMPLETE with Max Speed 1e10 (dt=0 replaced by 1e-10).
* Decision item: a raw TrackMate export with its 3 descriptive rows below the header is refused (`missing_track_id`); the notebook loader drops those rows.
* The sandbox demo case artifact (F-001) also appears in the app's own cases.json when run twice: covered by Tools#138.

## Tools#138 merged (owner approved merge on green): 94527478 -> 8ad2dc2 on Tools main (all six checks green on head 1853e6b)
* GitHub release sandbox for Guess the Condition 0.0.1 re-dispatched on the new main (host refs v0.1.0-alpha.1, Tools pin v0.3.0-alpha.1) to confirm the Windows and macOS legs; result to be recorded here.
* Fiji#50 merged (e35337f), Fiji issues #29 and #31 closed with a comment (ship in the next Fiji release).

## Napari UI audit on the RELEASED host v0.1.0-alpha.1 (driver branch claude/ui-audit-napari, head 83124ff)
* Guess the Condition 0.0.1 (installed app), all 6 tools: 36 PASS, 1 FAIL, 1 HUMAN, 0 NOT_RUN (matrix results/GuessTheCondition/matrix_ui_napari_GuessTheCondition.json). Control check: 11 controls found = the 11 table rows; every tool's form opens, controls and run PASS; analyse_results ran and showed message, values, two tables and the PDF.
* **H-N1 confirmed on the released host (class: Napari host bug):** `ui_napari_panel_run FAIL: Run stayed enabled while the tool ran (a second click is silently ignored)`.
* CellTracksColab 1.1.2 with both apps registered in one registry: `ui_napari_not_listed PASS: CellTracksColab is not in the app chooser ['GuessTheCondition']` (hidden by design, while Guess the Condition is listed).
* H-N2 (RGB layer leaves the Channel chooser empty) was reproduced by the agent on the repository's example app (interactions), not on a real app; H-N3 stale headings is minor; H-N4 not minimised, not claimed.
* HUMAN: `ui_napari_panel_cancel_running` (no case with cancel_after_s in Guess the Condition's cases).
* Screenshot checks assert only existence, freshness and plausible size; pictures are for a person to review.

## CellTracksColab 1.1.2 notebooks (8 notebooks; runner branch claude/oneoff-notebooks head 53564b9)
First run: 153 PASS, 59 FAIL, 23 HUMAN, 28 NOTE. After classifying every failure and fixing the click scripts and runner (not the checks): **197 PASS, 2 FAIL, 23 HUMAN, 29 NOTE, 0 NOT_RUN**.
* **A-CT3 (CellTracksColab app notebook bug, VERIFIED by the parent in the notebook source)** `CellTracksColab_Custom.ipynb` cell 7, `on_submit_clicked`: `global File_Format` then `if Use_test_dataset: File_Format = "csv"` then `CellTracks.file_format = File_Format`. When "Use test dataset" is unticked (a user loading their own data) `File_Format` is never assigned, so Submit raises `NameError: name 'File_Format' is not defined` and every later cell fails (merged_spots_df, merged_tracks_df, ...). The TrackMate notebook has `File_Format = File_Format_widget.value`; the Custom notebook lacks it. Reproduction: open Custom, untick "Use test dataset", choose a folder, press Submit. The two remaining FAIL rows are this bug; the script records a NOTE `workaround_file_format` and defines the variable as a user could, so the rest of the notebook is still tested (it then passes its whole oracle: spots, exact metrics, QC and plot files, balanced dataset).
* Script/runner bugs fixed (not app bugs): HDBSCAN defaults larger than the 48 synthetic tracks (everything labelled noise), per-cell ROI name fields in Distance_to_ROI, shallow output-file patterns, gzip data in .csv files read as text, plot cells with nothing ticked counted as PASS.
* HUMAN (23): native tkinter "Find folder/file" dialogs (21 rows), the Zenodo "Use test dataset" download (2 rows), exemplar tracks on a raw video (Dimensionality_Reduction cells 31 and 33).
* Caveat: the runner's negative controls were not rerun by the agent after its last change set; the parent reruns them (results/nb_negative_controls_rerun.txt).
* Parent rerun of the notebook runner's negative controls after the agent's last change set: 30 of 30 as expected (results/nb_negative_controls_rerun.txt).

## Guess the Condition sandbox on the NEW Tools main (run 38620177855, after Tools#138): Linux green, macOS arm64 green, Windows RED on exactly one check
* Windows: `4_cli_case_21_play_round_FAILED FAIL status=FAILED code=no_image` (the case expects `empty_guess`). This check ALSO failed in the earlier Windows run (38600019401), so it is not caused by Tools#138; the fix removed the other Windows failures (case 00 `already_exists`, `6_runs_complete`, and the five retention ids that never ran).
* **F-004 (Windows-only, cause UNKNOWN; class: app or CLI quoting, needs a Windows investigation).** The case runs `play_round results_folder=... user_name=Fresh guess="   "` (blank guess). In `guessthecondition_lc_tools/__init__.py` lines 138-140 a guess that is not None and blank raises `empty_guess` BEFORE `session.answer`; `no_image` is raised inside `session.answer` (session.py:354), so on Windows the guess must have reached the tool as a NON-blank string. Hypothesis (not verified): the three-space argument is altered by Windows command-line quoting between the sandbox's `subprocess.run` list, the CLI's `key=value` parser and the tool (for example literal quote characters kept, so the guess is `"   "`). The same case passes on Linux and macOS. Not reproducible here (Linux container). Needs: a Windows run printing the received `guess` repr, or a human on Windows.

## QuPath UI audit on the RELEASED extension v0.1.0-alpha.1 (driver branch claude/ui-audit-qupath, head b8cf3bc)
Guess the Condition 0.0.1, all 6 tools, 18 screenshots: 36 PASS, 1 FAIL, 7 HUMAN, 0 NOT_RUN (results/GuessTheCondition/matrix_ui_qupath_GuessTheCondition.json). Hidden app (`hosts: [notebook]`): `not_listed` PASS. Negative controls: all caught (extra/removed control, blank result, failing tool, dying worker, hung tool, watchdog, wrongly listed app).
* **Q-1 (QuPath host bug, SEVERE, VERIFIED by the parent): the Run button does nothing in the released v0.1.0-alpha.1.** `LabConstrictorTools.groovy` line 1111: `runButton.onAction = { run() }`. Inside the closure, `run()` resolves to the closure's own `Closure.run()`, which calls itself: StackOverflowError, the dialog's `run()` (line 2048) is never called, the status stays unchanged. Independent reproduction with QuPath's own Groovy 5.0.4: a class whose closure calls `run()` gives `StackOverflowError, dialog.run() calls = 0`; `{ this.run() }` gives `dialog.run() calls = 1`. The agent's real-click run logs a StackOverflowError for every Run click, and a local patch to `this.run()` made all Run checks pass with real clicks (then reverted). Only this closure is affected (the other handlers call methods that Closure does not define). Why nothing caught it: every existing GUI body calls `dlg.run()` directly and never presses the button; the release sandbox only checks listing for QuPath.
* Q-2 (probable): setting an image chooser to null throws IllegalArgumentException ('argument type mismatch') from the Image-area listener (line ~1619) and QuPath opens its Log window; not shown to be reachable by a person.
* Q-3: 'Open in QuPath' with a project open first asks 'Import images to project' then 'Save changes' (behaviour note; the audit answers Import and No).
* Q-4 (possible follow-on of Q-1): in click mode `panel_keep_worker` also FAILs ('a click did not untick the box'); not isolated.
* Environment note: the QuPath harness rewrote the shared QuPath install (jar and QuPath.cfg); the first QuPath.cfg backup may already contain a previous agent's jar entry.

## Fiji UI audit on the RELEASED plugin v0.1.0-alpha.1 (script and jar; driver branch claude/ui-audit-fiji, head 1d73674)
Guess the Condition 0.0.1 vs released script: 36 expected ids: 32 PASS, 3 FAIL, 4 HUMAN. All six `form_*_opens`, `run_*` (analyze_results: images_guessed=3, declared values) and `screens_*` PASS. Hidden app (`hosts: [notebook]`): `app_not_in_chooser` PASS. Multi-app (example apps): both listed, switching works. Jar mode on the released jar: forms, run, copy terminal/python, menu PASS; same Cancel FAILs as script mode. Negative controls: all 9 scenarios go red (removed/extra control, OK off-screen, blank screenshots, failing tool, wrong value, blank results, hung tool killed by the watchdog, listed when hidden / hidden when listed).
* **FJ-1 (Fiji host bug, severe; agent-verified in the bytecode, to be confirmed by the parent): Cancel does not cancel.** In every LabConstrictor dialog, pressing Cancel on the tool chooser opens the next dialog (the form); pressing Cancel on a form RUNS the tool with the form's values (the run record then says FAILED only because `output_folder` was empty). Cause: scijava-common 2.101 `ModuleRunner.call()` returns the module even when cancelled, while `harvest()` in LabConstrictor_Tools.groovy treats only `null` as cancel; no `isCanceled()` use anywhere in the repo. Seen with real Robot clicks and with doClick().
* **FJ-2 (Fiji/SciJava, user-visible): the percentage slider is off by one.** Setting the slider (min 1, max 100) to 99 leaves the number box at 100; setting it to 25 sent percentage_to_test=26 (50 gave 51); typing 25 into the number box sent 25.
* FJ-3 (feature gap): the combo box for ChoicesFrom string parameters accepts only the listed names; the CLI also accepts a number or any case ('2', 'mutant'), the Fiji form cannot enter them.
* FJ-4 (documented, not a defect): a tool with exactly one file input shows SciJava's native file prompt instead of a form.
* HUMAN: the app chooser (only one app listed) and three prerequisite play_round guesses that cannot be typed into the combo; replayed through the CLI for their effect on the game state.
* Driver caveat: the play_round after-run screenshot of one release run showed no image window (the image was open per ImagePlus; a rerun showed it): treated as timing under load.

## QuPath fix PR for Q-1 opened: https://github.com/CellMigrationLab/LabConstrictor-QuPath/pull/38 (branch claude/qupath-run-button-fix, head 7d64e60; not merged)
* `this.run()` plus a new GUI body that fires the real Run button. With the fix 4 of 4 PASS; with the line reverted the test FAILS (negative control). Needs a new QuPath tag from the owner (v0.1.0-alpha.1 contains the bug).

## F-004 RESOLVED: root cause found with Windows Python under Wine; fix PR Tools#139 (https://github.com/CellMigrationLab/LabConstrictor-Tools/pull/139, head 38e5a8b, not merged)
* Class: Tools sandbox harness bug (Windows-only), NOT the app and NOT the Tools CLI. `cli_params` turned any string input for which `(base / v).exists()` into an absolute path; on Windows `Path(base) / "   "` is `base` itself (the system drops trailing spaces), so the blank guess became the test-files folder (`guess=Z:\tmp\wtest\base`) and the tool answered `no_image` instead of `empty_guess`.
* Reproduced under Wine (Windows Python 3.12.8): before `['guess=Z:\\tmp\\wtest\\base', ...]`; after the fix `['guess=   ', ...]`. Negative control: the new unit test fails against the old code.
* Method note: Wine 9.0 (apt, 0.7 GB) plus the Windows embeddable Python (22 MB) runs stdlib-level Windows behaviour (paths, quoting, subprocess) in this Linux container in seconds; it cannot run the constructor installers or the GUI hosts.

## H-N1 fix opened and verified: Napari PR #64 (https://github.com/CellMigrationLab/LabConstrictor-napari/pull/64, branch claude/napari-run-button-fix, head e71bd97; not merged)
* Cause confirmed: magicgui's `_disable_button_and_call` runs `enabled = True` in `finally` right after the click handler returns. Fix: a slot connected to `call_button.changed` re-applies the real run state after magicgui's own slot.
* Parent re-ran the regression test: on UNFIXED main it FAILS (`running_run_disabled`, `still_disabled_after_second_click`, `cancel_run_disabled_while_running`); with the fix `FAILURES: none`. Audit driver on Guess the Condition with the fix: 37 PASS, 0 FAIL, `ui_napari_panel_run PASS`.
* Follow-up causes (not in the PR): H-N2 RGB chooser: magicgui `Container.reset_choices()` resets the static `ComboBox(choices=[""])` after `_refresh_channels` filled it; proposed fix: callable choices in `_add_channel_choosers`. H-N3: `_group_heading` is never initialised or reset (`__init__`, `_clear_form`).

## Fiji Cancel fix opened and verified: PR https://github.com/CellMigrationLab/LabConstrictor-Fiji/pull/<see PR list> (branch claude/fiji-cancel-fix, head b790363; not merged)
* FJ-1 root cause CORRECTED by the fix agent (javap on scijava-common 2.101): the module is never marked cancelled, because the plugin's `LCModule` is not `Cancelable` and `AbstractModule.cancel()` is empty; `ModuleRunner.call()` returns the module anyway and `harvest()` only treated null as cancel. Fix: `LCModule.cancel()` sets a flag, `harvest()` returns null when set, and the plugin says "cancelled, nothing was run".
* Verified by the parent: both new regression cases pass with the fix in real Fiji (2/2); on unfixed main both fail (agent run); 20 existing GUI cases pass (agent run).
* **FJ-2 (slider off by one) WITHDRAWN as a plugin bug**: the audit driver set the raw JSlider position (SciJava's slider uses internal positions 0..N with calibrated value = pos*step + min), so position 25 shows 26 because min=1. The number box and the value sent are consistent. Not verified with a real mouse drag.
