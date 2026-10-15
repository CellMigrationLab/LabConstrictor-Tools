# Results of the alpha.2 rerun (generated from the matrices)

## GuessTheCondition

| family | host | PASS | FAIL | NOT_RUN | HUMAN | NOTE | finished |
|---|---|---|---|---|---|---|---|
| nb | notebook | 46 | 0 | 0 | 0 | 11 | 2026-10-15T08:17:31 |
| sandbox | cli | 46 | 0 | 0 | 0 | 2 | 2026-10-15T08:17:08 |
| synthetic | cli | 146 | 0 | 0 | 0 | 0 | 2026-10-15T08:22:04 |
| ui | napari | 0 | 0 | 0 | 0 | 0 | NOT FINISHED |
| synthetic | napari | 142 | 0 | 0 | 0 | 4 | 2026-10-15T08:28:38 |
| ui | fiji | 64 | 1 | 0 | 9 | 0 | 2026-10-15T08:40:05 |
| ui | fiji | 32 | 1 | 0 | 3 | 0 | 2026-10-15T08:49:10 |
| ui | napari | 37 | 0 | 0 | 1 | 0 | 2026-10-15T08:19:04Z |
| ui | qupath | 12 | 0 | 0 | 0 | 0 | NOT FINISHED |

### GuessTheCondition: FAIL (2)

* `ui_fiji_panel_form_cancel` (ui/fiji) the summary does not say cancelled; a run started (status 'FAILED'); 1 run record(s) were created
* `ui_fiji_panel_form_cancel` (ui/fiji) the summary does not say cancelled; a run started (status 'FAILED'); 1 run record(s) were created

### GuessTheCondition: HUMAN (13)

* `ui_fiji_panel_chooser_app` (ui/fiji) not applicable: only one app is listed, so Fiji shows no app chooser
* `ui_fiji_run_create_demo_experiment` (ui/fiji) expectations of the case that Fiji cannot check: max_seconds
* `ui_fiji_run_prepare_game` (ui/fiji) expectations of the case that Fiji cannot check: max_seconds
* `ui_fiji_run_play_round` (ui/fiji) expectations of the case that Fiji cannot check: max_seconds
* `ui_fiji_prerequisite_play_round_5` (ui/fiji) an earlier case (expects FAILED) was replayed through the command line for its effect on the app's state, because the Fiji form cannot express its input (the form could not be filled from the case: Guess: 'Guess' has no item 'Nonsense' (items: [, Control, Mutant]))
* `ui_fiji_run_undo_last_guess` (ui/fiji) expectations of the case that Fiji cannot check: max_seconds
* `ui_fiji_prerequisite_play_round_6` (ui/fiji) an earlier case (expects COMPLETE) was replayed through the command line for its effect on the app's state, because the Fiji form cannot express its input (the form could not be filled from the case: Guess: 'Guess' has no item '2' (items: [, Control, Mutant]))
* `ui_fiji_prerequisite_play_round_7` (ui/fiji) an earlier case (expects COMPLETE) was replayed through the command line for its effect on the app's state, because the Fiji form cannot express its input (the form could not be filled from the case: Guess: 'Guess' has no item 'mutant' (items: [, Control, Mutant]))
* `ui_fiji_run_analyze_results` (ui/fiji) expectations of the case that Fiji cannot check: max_seconds
* `ui_fiji_panel_chooser_app` (ui/fiji) not applicable: only one app is listed, so Fiji shows no app chooser
* `ui_fiji_run_create_demo_experiment` (ui/fiji) expectations of the case that Fiji cannot check: max_seconds
* `ui_fiji_run_prepare_game` (ui/fiji) expectations of the case that Fiji cannot check: max_seconds
* `ui_napari_panel_cancel_running` (ui/napari) no case of cases.json sets cancel_after_s: a person presses Cancel during a long run

