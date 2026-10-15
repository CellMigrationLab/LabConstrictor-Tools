# Results of the alpha3 rerun (generated from the matrices)

## GuessTheCondition

| family | host | PASS | FAIL | NOT_RUN | HUMAN | NOTE | finished |
|---|---|---|---|---|---|---|---|
| sandbox | cli | 46 | 0 | 0 | 0 | 2 | 2026-10-15T12:36:11 |
| synthetic | cli | 146 | 0 | 0 | 0 | 0 | 2026-10-15T12:44:49 |
| ui | napari | 0 | 0 | 0 | 0 | 0 | NOT FINISHED |
| ui | fiji | 69 | 0 | 0 | 9 | 0 | NOT FINISHED |
| ui | napari | 37 | 0 | 0 | 1 | 0 | 2026-10-15T12:37:44Z |

### GuessTheCondition: HUMAN (10)

* `ui_fiji_panel_chooser_app` (ui/fiji) not applicable: only one app is listed, so Fiji shows no app chooser
* `ui_fiji_run_create_demo_experiment` (ui/fiji) expectations of the case that Fiji cannot check: max_seconds
* `ui_fiji_run_prepare_game` (ui/fiji) expectations of the case that Fiji cannot check: max_seconds
* `ui_fiji_run_play_round` (ui/fiji) expectations of the case that Fiji cannot check: max_seconds
* `ui_fiji_prerequisite_play_round_5` (ui/fiji) an earlier case (expects FAILED) was replayed through the command line for its effect on the app's state, because the Fiji form cannot express its input (the form could not be filled from the case: Guess: 'Guess' has no item 'Nonsense' (items: [, Control, Mutant]))
* `ui_fiji_run_undo_last_guess` (ui/fiji) expectations of the case that Fiji cannot check: max_seconds
* `ui_fiji_prerequisite_play_round_6` (ui/fiji) an earlier case (expects COMPLETE) was replayed through the command line for its effect on the app's state, because the Fiji form cannot express its input (the form could not be filled from the case: Guess: 'Guess' has no item '2' (items: [, Control, Mutant]))
* `ui_fiji_prerequisite_play_round_7` (ui/fiji) an earlier case (expects COMPLETE) was replayed through the command line for its effect on the app's state, because the Fiji form cannot express its input (the form could not be filled from the case: Guess: 'Guess' has no item 'mutant' (items: [, Control, Mutant]))
* `ui_fiji_run_analyze_results` (ui/fiji) expectations of the case that Fiji cannot check: max_seconds
* `ui_napari_panel_cancel_running` (ui/napari) no case of cases.json sets cancel_after_s: a person presses Cancel during a long run

