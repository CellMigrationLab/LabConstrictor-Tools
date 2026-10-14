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
