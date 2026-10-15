# Results of the alpha3 rerun (generated from the matrices)

## GuessTheCondition

| family | host | PASS | FAIL | NOT_RUN | HUMAN | NOTE | finished |
|---|---|---|---|---|---|---|---|
| sandbox | cli | 46 | 0 | 0 | 0 | 2 | 2026-10-15T12:36:11 |
| synthetic | cli | 146 | 0 | 0 | 0 | 0 | 2026-10-15T12:44:49 |
| ui | napari | 0 | 0 | 0 | 0 | 0 | NOT FINISHED |
| synthetic | napari | 142 | 0 | 0 | 0 | 4 | 2026-10-15T13:04:26 |
| ui | fiji | 71 | 0 | 0 | 10 | 0 | 2026-10-15T12:52:28 |
| ui | fiji | 33 | 1 | 0 | 5 | 0 | 2026-10-15T13:09:28 |
| ui | fiji | 20 | 0 | 4 | 4 | 0 | 2026-10-15T13:11:47 |
| ui | napari | 37 | 0 | 0 | 1 | 0 | 2026-10-15T12:37:44Z |
| ui | qupath | 37 | 0 | 0 | 7 | 0 | 2026-10-15T13:18:41Z |

### GuessTheCondition: FAIL (1)

* `ui_fiji_fj1b_cancel_form_prepare_game` (ui/fiji) a real click on form_cancel did not close the dialog within 5000 ms

### GuessTheCondition: NOT_RUN (4)

* `ui_fiji_panel_copy_terminal` (ui/fiji) no tool completed a run in this audit, so there is no command to copy
* `ui_fiji_panel_copy_python` (ui/fiji) no tool completed a run in this audit, so there is no command to copy
* `ui_fiji_panel_log` (ui/fiji) no tool completed a run, so there is no Log of a run to read
* `ui_fiji_panel_form_ok` (ui/fiji) the audit ended without producing this check (a crash, a timeout, or a step that was never reached)

### GuessTheCondition: HUMAN (27)

* `ui_fiji_panel_chooser_app` (ui/fiji) not applicable: only one app is listed, so Fiji shows no app chooser
* `ui_fiji_run_create_demo_experiment` (ui/fiji) expectations of the case that Fiji cannot check: max_seconds
* `ui_fiji_run_prepare_game` (ui/fiji) expectations of the case that Fiji cannot check: max_seconds
* `ui_fiji_run_play_round` (ui/fiji) expectations of the case that Fiji cannot check: max_seconds
* `ui_fiji_prerequisite_play_round_5` (ui/fiji) an earlier case (expects FAILED) was replayed through the command line for its effect on the app's state, because the Fiji form cannot express its input (the form could not be filled from the case: Guess: 'Guess' has no item 'Nonsense' (items: [, Control, Mutant]))
* `ui_fiji_run_undo_last_guess` (ui/fiji) expectations of the case that Fiji cannot check: max_seconds
* `ui_fiji_prerequisite_play_round_6` (ui/fiji) an earlier case (expects COMPLETE) was replayed through the command line for its effect on the app's state, because the Fiji form cannot express its input (the form could not be filled from the case: Guess: 'Guess' has no item '2' (items: [, Control, Mutant]))
* `ui_fiji_prerequisite_play_round_7` (ui/fiji) an earlier case (expects COMPLETE) was replayed through the command line for its effect on the app's state, because the Fiji form cannot express its input (the form could not be filled from the case: Guess: 'Guess' has no item 'mutant' (items: [, Control, Mutant]))
* `ui_fiji_run_analyze_results` (ui/fiji) expectations of the case that Fiji cannot check: max_seconds
* `ui_fiji_fj1b_missing_image` (ui/fiji) no tool of this app has a required image input: nothing to refuse
* `ui_fiji_panel_copy_empty` (ui/fiji) LC_HOME already holds a last command (state/last_command.json), so the 'nothing to copy yet' state cannot be tested here
* `ui_fiji_panel_chooser_app` (ui/fiji) not applicable: only one app is listed, so Fiji shows no app chooser
* `ui_fiji_run_create_demo_experiment` (ui/fiji) expectations of the case that Fiji cannot check: max_seconds
* `ui_fiji_run_prepare_game` (ui/fiji) expectations of the case that Fiji cannot check: max_seconds
* `ui_fiji_fj1b_missing_image` (ui/fiji) no tool of this app has a required image input: nothing to refuse
* `ui_fiji_parts` (ui/fiji) only ['panel'] ran (LC_UI_PARTS)
* `ui_fiji_panel_copy_empty` (ui/fiji) LC_HOME already holds a last command (state/last_command.json), so the 'nothing to copy yet' state cannot be tested here
* `ui_fiji_panel_chooser_app` (ui/fiji) not applicable: only one app is listed, so Fiji shows no app chooser
* `ui_fiji_fj1b_missing_image` (ui/fiji) no tool of this app has a required image input: nothing to refuse
* `ui_napari_panel_cancel_running` (ui/napari) no case of cases.json sets cancel_after_s: a person presses Cancel during a long run
* `ui_qupath_form_analyze_results_browse` (ui/qupath) the native file chooser of [results_folder] cannot be driven under Xvfb: the browse buttons were checked for presence, enabled state and an action, and the path was typed into the field
* `ui_qupath_form_create_demo_experiment_browse` (ui/qupath) the native file chooser of [output_folder] cannot be driven under Xvfb: the browse buttons were checked for presence, enabled state and an action, and the path was typed into the field
* `ui_qupath_form_list_conditions_browse` (ui/qupath) the native file chooser of [results_folder] cannot be driven under Xvfb: the browse buttons were checked for presence, enabled state and an action, and the path was typed into the field
* `ui_qupath_form_play_round_browse` (ui/qupath) the native file chooser of [results_folder] cannot be driven under Xvfb: the browse buttons were checked for presence, enabled state and an action, and the path was typed into the field
* `ui_qupath_run_play_round_unverified` (ui/qupath) expectation(s) the GUI cannot check: expect.progress_events_min
* `ui_qupath_form_prepare_game_browse` (ui/qupath) the native file chooser of [experiment_folder, results_folder] cannot be driven under Xvfb: the browse buttons were checked for presence, enabled state and an action, and the path was typed into the field
* `ui_qupath_form_undo_last_guess_browse` (ui/qupath) the native file chooser of [results_folder] cannot be driven under Xvfb: the browse buttons were checked for presence, enabled state and an action, and the path was typed into the field

## LabConstrictorPlayground

| family | host | PASS | FAIL | NOT_RUN | HUMAN | NOTE | finished |
|---|---|---|---|---|---|---|---|
| sandbox | cli | 48 | 0 | 0 | 0 | 2 | NOT FINISHED |

