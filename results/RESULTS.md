# Results of the one-off test run

## CellTracksColab

| family | host | PASS | FAIL | NOT_RUN | HUMAN | NOTE | finished |
|---|---|---|---|---|---|---|---|
| nb | notebook | 197 | 2 | 0 | 23 | 29 | 2026-10-14T19:26:07 |
| sandbox | cli | 31 | 0 | 0 | 0 | 0 | 2026-10-14T17:57:48 |
| ui | napari | 1 | 0 | 0 | 0 | 0 | 2026-10-14T19:23:52Z |

### CellTracksColab: FAIL (2)

* `nb_CellTracksColab_CellTracksColab_Custom_click_auto_load_Submit` (nb/notebook) 'Submit': CallbackFailed: callback of Button('Submit') raised:     CellTracks.file_format = File_Format |                              ^^^^^^^^^^^ | NameError: name 'File_Format' is not defined
* `nb_CellTracksColab_CellTracksColab_Custom_runs` (nb/notebook) 80 cells and stages executed; failing cells: none; failing click stages/assertions: click_auto_load_Submit; executed notebook: /home/user/results/CellTracksColab/executed/CellTracksColab_Custom.ipynb

### CellTracksColab: HUMAN (23)

* `nb_CellTracksColab_CellTracksColab_Custom_click_zenodo_test_dataset` (nb/notebook) the default "Use test dataset" downloads T_Cells_spots_only.zip from Zenodo (up to 10 minutes): not used, the synthetic dataset is loaded instead
* `nb_CellTracksColab_CellTracksColab_Custom_click_auto_load_Find_folder` (nb/notebook) button 'Find folder' opens a native or upload dialog: not clicked, the path or file is set directly in the field
* `nb_CellTracksColab_CellTracksColab_Custom_click_auto_load_Find_folder` (nb/notebook) button 'Find folder' opens a native or upload dialog: not clicked, the path or file is set directly in the field
* `nb_CellTracksColab_CellTracksColab_Dimensionality_Reduction_click_auto_load_Find_file` (nb/notebook) button 'Find file' opens a native or upload dialog: not clicked, the path or file is set directly in the field
* `nb_CellTracksColab_CellTracksColab_Dimensionality_Reduction_click_auto_load_Find_file` (nb/notebook) button 'Find file' opens a native or upload dialog: not clicked, the path or file is set directly in the field
* `nb_CellTracksColab_CellTracksColab_Dimensionality_Reduction_click_auto_load_Find_folder` (nb/notebook) button 'Find folder' opens a native or upload dialog: not clicked, the path or file is set directly in the field
* `nb_CellTracksColab_CellTracksColab_Dimensionality_Reduction_human_cell_31` (nb/notebook) needs the raw video of the experiment (Video path widget) to overlay the exemplar tracks: no video exists for the synthetic tracks
* `nb_CellTracksColab_CellTracksColab_Dimensionality_Reduction_human_cell_33` (nb/notebook) exports movies of the exemplar tracks from the raw video chosen in cell 31
* `nb_CellTracksColab_CellTracksColab_Distance_to_ROI_click_auto_load_Find_file` (nb/notebook) button 'Find file' opens a native or upload dialog: not clicked, the path or file is set directly in the field
* `nb_CellTracksColab_CellTracksColab_Distance_to_ROI_click_auto_load_Find_file` (nb/notebook) button 'Find file' opens a native or upload dialog: not clicked, the path or file is set directly in the field
* `nb_CellTracksColab_CellTracksColab_Distance_to_ROI_click_auto_load_Find_folder` (nb/notebook) button 'Find folder' opens a native or upload dialog: not clicked, the path or file is set directly in the field
* `nb_CellTracksColab_CellTracksColab_Distance_to_ROI_click_auto_roi_Find_folder` (nb/notebook) button 'Find folder' opens a native or upload dialog: not clicked, the path or file is set directly in the field
* `nb_CellTracksColab_CellTracksColab_TrackMate_click_zenodo_test_dataset` (nb/notebook) the default "Use test dataset" downloads T_Cells_spots_only.zip from Zenodo (up to 10 minutes): not used, the synthetic dataset is loaded instead
* `nb_CellTracksColab_CellTracksColab_TrackMate_click_auto_load_Find_folder` (nb/notebook) button 'Find folder' opens a native or upload dialog: not clicked, the path or file is set directly in the field
* `nb_CellTracksColab_CellTracksColab_TrackMate_click_auto_load_Find_folder` (nb/notebook) button 'Find folder' opens a native or upload dialog: not clicked, the path or file is set directly in the field
* `nb_CellTracksColab_CellTracksColab_TrackMate_Plate_click_auto_load_Find_folder` (nb/notebook) button 'Find folder' opens a native or upload dialog: not clicked, the path or file is set directly in the field
* `nb_CellTracksColab_CellTracksColab_TrackMate_Plate_click_auto_load_Find_folder` (nb/notebook) button 'Find folder' opens a native or upload dialog: not clicked, the path or file is set directly in the field
* `nb_CellTracksColab_CellTracksColab_Track_Clustering_click_auto_load_Find_file` (nb/notebook) button 'Find file' opens a native or upload dialog: not clicked, the path or file is set directly in the field
* `nb_CellTracksColab_CellTracksColab_Track_Clustering_click_auto_load_Find_file` (nb/notebook) button 'Find file' opens a native or upload dialog: not clicked, the path or file is set directly in the field
* `nb_CellTracksColab_CellTracksColab_Track_Clustering_click_auto_load_Find_folder` (nb/notebook) button 'Find folder' opens a native or upload dialog: not clicked, the path or file is set directly in the field
* `nb_CellTracksColab_CellTracksColab_Viewer_click_auto_load_Find_file` (nb/notebook) button 'Find file' opens a native or upload dialog: not clicked, the path or file is set directly in the field
* `nb_CellTracksColab_CellTracksColab_Viewer_click_auto_load_Find_file` (nb/notebook) button 'Find file' opens a native or upload dialog: not clicked, the path or file is set directly in the field
* `nb_CellTracksColab_CellTracksColab_Viewer_click_auto_load_Find_folder` (nb/notebook) button 'Find folder' opens a native or upload dialog: not clicked, the path or file is set directly in the field

## GuessTheCondition

| family | host | PASS | FAIL | NOT_RUN | HUMAN | NOTE | finished |
|---|---|---|---|---|---|---|---|
| nb | notebook | 46 | 0 | 0 | 0 | 11 | 2026-10-14T18:18:50 |
| sandbox | cli | 37 | 2 | 5 | 0 | 1 | 2026-10-14T17:58:52 |
| ui | napari | 36 | 1 | 0 | 1 | 0 | 2026-10-14T19:22:31Z |
| ui | qupath | 36 | 1 | 0 | 7 | 0 | 2026-10-14T19:27:46Z |
| sandbox | cli | 46 | 0 | 0 | 0 | 2 | 2026-10-14T18:18:20 |

### GuessTheCondition: FAIL (4)

* `4_cli_case_00_create_demo_experiment_COMPLETE` (sandbox/cli) status=FAILED code=already_exists
* `6_runs_complete` (sandbox/cli) run 0 of create_demo_experiment: eriment/run.json", |   "error": "[already_exists] /home/user/apps/run_src/GuessTheCondition/lc_tests/fixtures/results/GuessTheCondition_demo already exists: choose another folder, or delete it.", |   "code": "already_exists", |   "log": "/home/user/apps/lc_sbx_GuessTheCondition/logs/labconstrictor.log" | } |
* `ui_napari_panel_run` (ui/napari) AssertionError: Run stayed enabled while the tool ran (a second click is silently ignored) (tool create_demo_experiment)
* `ui_qupath_panel_run` (ui/qupath) AssertionError: LC_UI_RUN_VIA=call: the Run button was not clicked in this launch, so it is not shown to work

### GuessTheCondition: NOT_RUN (5)

* `6a_markers_present` (sandbox/cli) expected, never executed
* `6b_results_keep_newest_20` (sandbox/cli) expected, never executed
* `6d_prune_dry_run_json` (sandbox/cli) expected, never executed
* `6e_foreign_folders_left_alone` (sandbox/cli) expected, never executed
* `6f_run_records_keep_50` (sandbox/cli) expected, never executed

### GuessTheCondition: HUMAN (8)

* `ui_napari_panel_cancel_running` (ui/napari) no case of cases.json sets cancel_after_s: a person presses Cancel during a long run
* `ui_qupath_form_analyze_results_browse` (ui/qupath) the native file chooser of [results_folder] cannot be driven under Xvfb: the browse buttons were checked for presence, enabled state and an action, and the path was typed into the field
* `ui_qupath_form_create_demo_experiment_browse` (ui/qupath) the native file chooser of [output_folder] cannot be driven under Xvfb: the browse buttons were checked for presence, enabled state and an action, and the path was typed into the field
* `ui_qupath_form_list_conditions_browse` (ui/qupath) the native file chooser of [results_folder] cannot be driven under Xvfb: the browse buttons were checked for presence, enabled state and an action, and the path was typed into the field
* `ui_qupath_form_play_round_browse` (ui/qupath) the native file chooser of [results_folder] cannot be driven under Xvfb: the browse buttons were checked for presence, enabled state and an action, and the path was typed into the field
* `ui_qupath_run_play_round_unverified` (ui/qupath) expectation(s) the GUI cannot check: expect.progress_events_min
* `ui_qupath_form_prepare_game_browse` (ui/qupath) the native file chooser of [experiment_folder, results_folder] cannot be driven under Xvfb: the browse buttons were checked for presence, enabled state and an action, and the path was typed into the field
* `ui_qupath_form_undo_last_guess_browse` (ui/qupath) the native file chooser of [results_folder] cannot be driven under Xvfb: the browse buttons were checked for presence, enabled state and an action, and the path was typed into the field

## all

| family | host | PASS | FAIL | NOT_RUN | HUMAN | NOTE | finished |
|---|---|---|---|---|---|---|---|
| multi | cli | 11 | 0 | 0 | 0 | 0 | 2026-10-14T17:59:43 |

