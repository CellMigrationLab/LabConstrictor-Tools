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
| sandbox | cli | 55 | 0 | 0 | 0 | 3 | 2026-10-15T13:24:09 |
| alpha3 | napari | 15 | 0 | 0 | 0 | 0 | 2026-10-15T13:28:33Z |
| synthetic | cli | 163 | 2 | 0 | 2 | 0 | 2026-10-15T13:29:55 |
| ui | fiji | 120 | 0 | 0 | 18 | 0 | 2026-10-15T13:46:34 |
| ui | napari | 64 | 4 | 0 | 14 | 0 | 2026-10-15T13:31:43Z |
| ui | qupath | 48 | 0 | 1 | 6 | 0 | NOT FINISHED |

### LabConstrictorPlayground: FAIL (6)

* `syn_pg_ramp_f32_p90_2_value:level_used` (synthetic/cli) level_used = 89.099853515625, expected 89.09999999999991 (tol 0.0001, rtol 0)
* `syn_pg_make_three_channels_1_tiff_slice_means` (synthetic/cli) three_channels.tif: means [42.713, 20.0, 30.0], expected [10, 20, 30]
* `ui_napari_run_look_inside_file` (ui/napari) AssertionError: top-level windows are ['QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', '_QtMainWindow'], expected ['_QtMainWindow']
* `ui_napari_form_summarise_table_controls` (ui/napari) AssertionError: top-level windows are ['QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', '_QtMainWindow'], expected ['_QtMainWindow']
* `ui_napari_run_align_centres` (ui/napari) AssertionError: prerequisite case 27 (bright_area) ended FAILED pixel_size_unknown, its expect says FAILED invalid_pixel_size | ✖ [pixel_size_unknown] The pixel size of the image is unknown, so an area in um2 cannot be given. Set 'pixel_size' (um per pixel) or calibrate the image.  - click Details… for the full report (log: /home/user/apps/a3_lc_home_Playground/logs/labconstrictor.log)
* `ui_napari_screens_align_centres` (ui/napari) AssertionError: align_centres_form.png does not exist; align_centres_after_run.png does not exist

### LabConstrictorPlayground: NOT_RUN (1)

* `ui_qupath_form_feature_tour_channel` (ui/qupath) image.channel(no multi-channel fixture three_channels.tif)

### LabConstrictorPlayground: HUMAN (40)

* `syn_pg_channels_cyx_note` (synthetic/cli) has no machine oracle for this run (works): judged by a person or by a host driver (--with-host)
* `syn_pg_rgb_note` (synthetic/cli) has no machine oracle for this run (works): judged by a person or by a host driver (--with-host)
* `ui_fiji_panel_chooser_app` (ui/fiji) not applicable: only one app is listed, so Fiji shows no app chooser
* `ui_fiji_run_check_everything` (ui/fiji) expectations of the case that Fiji cannot check: max_seconds
* `ui_fiji_run_feature_tour` (ui/fiji) expectations of the case that Fiji cannot check: max_seconds
* `ui_fiji_screens_stress_big_image` (ui/fiji) no run, so no after-run screenshot; the form screenshot was taken (evidence for a person)
* `ui_fiji_run_stress_big_image` (ui/fiji) no run: a stress tool: it is never run through the form
* `ui_fiji_screens_stress_crash` (ui/fiji) no run, so no after-run screenshot; the form screenshot was taken (evidence for a person)
* `ui_fiji_run_stress_crash` (ui/fiji) no run: a stress tool: it is never run through the form
* `ui_fiji_screens_stress_hang` (ui/fiji) no run, so no after-run screenshot; the form screenshot was taken (evidence for a person)
* `ui_fiji_run_stress_hang` (ui/fiji) no run: no grace-period kill in the case runner; covered by the host test suites and the sandbox extras
* `ui_fiji_screens_stress_many_points` (ui/fiji) no run, so no after-run screenshot; the form screenshot was taken (evidence for a person)
* `ui_fiji_run_stress_many_points` (ui/fiji) no run: a stress tool: it is never run through the form
* `ui_fiji_screens_stress_out_of_memory` (ui/fiji) no run, so no after-run screenshot; the form screenshot was taken (evidence for a person)
* `ui_fiji_run_stress_out_of_memory` (ui/fiji) no run: a stress tool: it is never run through the form
* `ui_fiji_screens_stress_real_memory` (ui/fiji) no run, so no after-run screenshot; the form screenshot was taken (evidence for a person)
* `ui_fiji_run_stress_real_memory` (ui/fiji) no run: opt-in, uses real memory; covered by the sandbox extras
* `ui_fiji_screens_stress_slow` (ui/fiji) no run, so no after-run screenshot; the form screenshot was taken (evidence for a person)
* `ui_fiji_run_stress_slow` (ui/fiji) no run: a stress tool: it is never run through the form
* `ui_fiji_run_summarise_table` (ui/fiji) expectations of the case that Fiji cannot check: summary cells
* `ui_napari_run_stress_big_image` (ui/napari) stress_big_image is a stress tool: the app's own extras run it, the UI audit never does
* `ui_napari_screens_stress_big_image` (ui/napari) stress_big_image is a stress tool: the app's own extras run it, the UI audit never does; the form screenshot stress_big_image_form.png was taken
* `ui_napari_run_stress_crash` (ui/napari) stress_crash is a stress tool: the app's own extras run it, the UI audit never does
* `ui_napari_screens_stress_crash` (ui/napari) stress_crash is a stress tool: the app's own extras run it, the UI audit never does; the form screenshot stress_crash_form.png was taken
* `ui_napari_run_stress_hang` (ui/napari) stress_hang is a stress tool: the app's own extras run it, the UI audit never does
* `ui_napari_screens_stress_hang` (ui/napari) stress_hang is a stress tool: the app's own extras run it, the UI audit never does; the form screenshot stress_hang_form.png was taken
* `ui_napari_run_stress_many_points` (ui/napari) stress_many_points is a stress tool: the app's own extras run it, the UI audit never does
* `ui_napari_screens_stress_many_points` (ui/napari) stress_many_points is a stress tool: the app's own extras run it, the UI audit never does; the form screenshot stress_many_points_form.png was taken
* `ui_napari_run_stress_out_of_memory` (ui/napari) stress_out_of_memory is a stress tool: the app's own extras run it, the UI audit never does
* `ui_napari_screens_stress_out_of_memory` (ui/napari) stress_out_of_memory is a stress tool: the app's own extras run it, the UI audit never does; the form screenshot stress_out_of_memory_form.png was taken
* `ui_napari_run_stress_real_memory` (ui/napari) stress_real_memory is a stress tool: the app's own extras run it, the UI audit never does
* `ui_napari_screens_stress_real_memory` (ui/napari) stress_real_memory is a stress tool: the app's own extras run it, the UI audit never does; the form screenshot stress_real_memory_form.png was taken
* `ui_napari_run_stress_slow` (ui/napari) stress_slow is a stress tool: the app's own extras run it, the UI audit never does
* `ui_napari_screens_stress_slow` (ui/napari) stress_slow is a stress tool: the app's own extras run it, the UI audit never does; the form screenshot stress_slow_form.png was taken
* `ui_qupath_form_align_centres_browse` (ui/qupath) the native file chooser of [image, reference] cannot be driven under Xvfb: the browse buttons were checked for presence, enabled state and an action, and the path was typed into the field
* `ui_qupath_form_bright_area_browse` (ui/qupath) the native file chooser of [image] cannot be driven under Xvfb: the browse buttons were checked for presence, enabled state and an action, and the path was typed into the field
* `ui_qupath_form_count_above_level_browse` (ui/qupath) the native file chooser of [image] cannot be driven under Xvfb: the browse buttons were checked for presence, enabled state and an action, and the path was typed into the field
* `ui_qupath_form_feature_tour_browse` (ui/qupath) the native file chooser of [image, region] cannot be driven under Xvfb: the browse buttons were checked for presence, enabled state and an action, and the path was typed into the field
* `ui_qupath_form_look_inside_file_browse` (ui/qupath) the native file chooser of [file] cannot be driven under Xvfb: the browse buttons were checked for presence, enabled state and an action, and the path was typed into the field
* `ui_qupath_form_make_test_data_browse` (ui/qupath) the native file chooser of [folder] cannot be driven under Xvfb: the browse buttons were checked for presence, enabled state and an action, and the path was typed into the field

