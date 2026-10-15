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

## VLab4Mic

| family | host | PASS | FAIL | NOT_RUN | HUMAN | NOTE | finished |
|---|---|---|---|---|---|---|---|
| install | cli | 2 | 0 | 0 | 0 | 0 | 2026-10-15T08:08:11 |
| nb | notebook | 43 | 0 | 0 | 2 | 14 | 2026-10-15T07:55:04 |
| sandbox | cli | 52 | 0 | 0 | 0 | 0 | 2026-10-15T07:49:10 |
| synthetic | cli | 83 | 3 | 0 | 1 | 0 | 2026-10-15T08:06:33 |
| synthetic | napari | 5 | 1 | 0 | 1 | 0 | 2026-10-15T08:06:33 |
| ui | fiji | 63 | 27 | 0 | 3 | 0 | 2026-10-15T07:52:53 |
| ui | napari | 15 | 6 | 0 | 1 | 0 | 2026-10-15T07:44:50Z |
| ui | qupath | 1 | 0 | 0 | 0 | 1 | 2026-10-15T07:50:11Z |

### VLab4Mic: FAIL (37)

* `syn_vm_flat_reference_0_status` (synthetic/cli) status COMPLETE, expected FAILED (error: None)
* `syn_vm_zero_reference_0_status` (synthetic/cli) status COMPLETE, expected FAILED (error: None)
* `syn_vm_different_fields_2_value:ssim` (synthetic/cli) ssim = 0.778662, expected 0.0 (tol 0.3, rtol 0)
* `syn_host_napari_vm_cal_micro` (synthetic/napari) file vm_cal_micro.tif: pixel size box shows '', expected 0.02
* `ui_fiji_panel_chooser_cancel` (ui/fiji) the plugin did not end within 6000 ms of the click on Cancel; dialogs showing now: [Compare an image with a reference]
* `ui_fiji_panel_form_cancel` (ui/fiji) the summary does not say cancelled
* `ui_fiji_form_simulate_sample_controls` (ui/fiji) the slider is at 19 but the number box beside it shows 20
* `ui_fiji_form_simulate_sample_controls` (ui/fiji) the slider is at 5000 but the number box beside it shows 0.5
* `ui_fiji_form_simulate_sample_controls` (ui/fiji) the slider is at 450000 but the number box beside it shows 45.0
* `ui_fiji_form_simulate_sample_controls` (ui/fiji) the control has no visible part: a real click cannot reach it
* `ui_fiji_form_simulate_sample_controls` (ui/fiji) the slider is at 5000 but the number box beside it shows 0.5
* `ui_fiji_form_simulate_sample_controls` (ui/fiji) the control has no visible part: a real click cannot reach it
* `ui_fiji_form_simulate_sample_controls` (ui/fiji) the control has no visible part: a real click cannot reach it
* `ui_fiji_form_simulate_sample_controls` (ui/fiji) the control has no visible part: a real click cannot reach it
* `ui_fiji_form_simulate_sample_controls` (ui/fiji) the control has no visible part: a real click cannot reach it
* `ui_fiji_form_simulate_sample_controls` (ui/fiji) the control has no visible part: a real click cannot reach it
* `ui_fiji_form_simulate_sample_controls` (ui/fiji) the control has no visible part: a real click cannot reach it
* `ui_fiji_form_simulate_sample_controls` (ui/fiji) the control has no visible part: a real click cannot reach it
* `ui_fiji_form_simulate_sample_controls` (ui/fiji) the control has no visible part: a real click cannot reach it
* `ui_fiji_form_simulate_sample_controls` (ui/fiji) the control has no visible part: a real click cannot reach it
* `ui_fiji_form_simulate_sample_controls` (ui/fiji) the control has no visible part: a real click cannot reach it
* `ui_fiji_form_simulate_sample_controls` (ui/fiji) the control has no visible part: a real click cannot reach it
* `ui_fiji_form_simulate_sample_controls` (ui/fiji) the control has no visible part: a real click cannot reach it
* `ui_fiji_form_simulate_sample_controls` (ui/fiji) the control has no visible part: a real click cannot reach it
* `ui_fiji_form_simulate_sample_controls` (ui/fiji) the control has no visible part: a real click cannot reach it
* `ui_fiji_form_simulate_sample_controls` (ui/fiji) the control has no visible part: a real click cannot reach it
* `ui_fiji_form_simulate_sample_controls` (ui/fiji) the control has no visible part: a real click cannot reach it
* `ui_fiji_form_simulate_sample_controls` (ui/fiji) the control has no visible part: a real click cannot reach it
* `ui_fiji_form_simulate_sample_controls` (ui/fiji) the control has no visible part: a real click cannot reach it
* `ui_fiji_form_simulate_sample_controls` (ui/fiji) the control has no visible part: a real click cannot reach it
* `ui_fiji_form_simulate_sample_controls` (ui/fiji) 24 of 62 control(s) failed: slider 'number of particles': the slider is at 19 but the number box beside it shows 20; slider 'labelling efficiency': the slider is at 5000 but the number box beside it shows 0.5; slider 'wobble cone (deg)': the slider is at 450000 but the number box beside it shows 45.0; set_checkbox 'set degree of labelling': the control has no visible part: a real click cannot reach it; slider 'structural integrity': the slider is at 5000 but the number box beside it shows 0.5...
* `ui_napari_form_simulate_sample_controls` (ui/napari) AssertionError: xy_orientation_angles (string): AssertionError: xy_orientation_angles is not enabled when random_orientations=True; xz_orientation_angles (string): AssertionError: xz_orientation_angles is not enabled when random_orientations=True; yz_orientation_angles (string): AssertionError: yz_orientation_angles is not enabled when random_orientations=True; rotation_angles (string): AssertionError: rotation_angles is not enabled when random_rotations=True
* `ui_napari_run_simulate_sample` (ui/napari) AssertionError: status FAILED, expected COMPLETE ([AttributeError] 'MolecularReplicates' object has no attribute 'struct')
* `ui_napari_form_compare_images_controls` (ui/napari) AssertionError: simulated_pixel_size_um (float): AssertionError: after 'use the image's calibration' (no image) the box shows '0.5'
* `ui_napari_run_compare_images` (ui/napari) ValueError: value 1.5 is outside of the allowed range: (0.0, 1.0) (at _ranged_widget.py:125)
* `ui_napari_screens_compare_images` (ui/napari) AssertionError: compare_images_form.png does not exist; compare_images_after_run.png does not exist
* `ui_napari_panel_run` (ui/napari) AssertionError: Run stayed enabled while the tool ran (a second click is silently ignored) (tool simulate_sample)

### VLab4Mic: HUMAN (8)

* `nb_VLab4Mic_VLab4Mic_main_click_load_structure_from_file` (nb/notebook) the 'Load structure from file' route needs a PDB/CIF file chosen in a file chooser: not driven
* `nb_VLab4Mic_VLab4Mic_parameter_sweeps_click_structure_from_file` (nb/notebook) 'Load structure from file', 'Upload image reference' and the saving-directory chooser need files chosen in a file chooser: not driven
* `syn_vm_cal_anisotropic` (synthetic/cli) no machine oracle for the anisotropic-calibration dataset (judged by a person); on the host see synthetic napari rows
* `syn_host_napari_vm_cal_anisotropic` (synthetic/napari) file vm_cal_anisotropic.tif: pixel size box shows '', expected 'HUMAN'
* `ui_fiji_panel_chooser_app` (ui/fiji) not applicable: only one app is listed, so Fiji shows no app chooser
* `ui_fiji_run_compare_images` (ui/fiji) expectations of the case that Fiji cannot check: max_seconds
* `ui_fiji_run_simulate_sample` (ui/fiji) expectations of the case that Fiji cannot check: max_seconds
* `ui_napari_panel_cancel_running` (ui/napari) no case of cases.json sets cancel_after_s: a person presses Cancel during a long run

## all

| family | host | PASS | FAIL | NOT_RUN | HUMAN | NOTE | finished |
|---|---|---|---|---|---|---|---|
| multi | cli | 11 | 0 | 0 | 0 | 0 | 2026-10-14T17:59:43 |

