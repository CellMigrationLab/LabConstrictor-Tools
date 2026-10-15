# Results of the alpha3 rerun (generated from the matrices)

## GuessTheCondition

| family | host | PASS | FAIL | NOT_RUN | HUMAN | NOTE | finished |
|---|---|---|---|---|---|---|---|
| sandbox | cli | 46 | 0 | 0 | 0 | 2 | 2026-10-15T12:36:11 |
| ui | fiji | 28 | 0 | 0 | 2 | 0 | NOT FINISHED |
| ui | napari | 37 | 0 | 0 | 1 | 0 | 2026-10-15T12:37:44Z |

### GuessTheCondition: HUMAN (3)

* `ui_fiji_panel_chooser_app` (ui/fiji) not applicable: only one app is listed, so Fiji shows no app chooser
* `ui_fiji_run_create_demo_experiment` (ui/fiji) expectations of the case that Fiji cannot check: max_seconds
* `ui_napari_panel_cancel_running` (ui/napari) no case of cases.json sets cancel_after_s: a person presses Cancel during a long run

