# Results of the alpha2 rerun (generated from the matrices)

## CellTracksColab

| family | host | PASS | FAIL | NOT_RUN | HUMAN | NOTE | finished |
|---|---|---|---|---|---|---|---|
| install | cli | 2 | 0 | 0 | 0 | 0 | 2026-10-15T09:55:29 |
| nb | notebook | 197 | 2 | 0 | 23 | 29 | 2026-10-15T09:06:18 |
| sandbox | cli | 33 | 0 | 0 | 0 | 1 | 2026-10-15T09:02:50 |
| synthetic | cli | 51 | 2 | 0 | 0 | 0 | 2026-10-15T09:04:59 |
| ui | fiji | 1 | 0 | 0 | 1 | 0 | 2026-10-15T09:03:50 |
| ui | napari | 1 | 0 | 0 | 0 | 0 | 2026-10-15T09:03:24Z |
| ui | qupath | 1 | 0 | 0 | 0 | 1 | 2026-10-15T09:04:12Z |

### CellTracksColab: FAIL (4)

* `nb_CellTracksColab_CellTracksColab_Custom_click_auto_load_Submit` (nb/notebook) 'Submit': CallbackFailed: callback of Button('Submit') raised:     CellTracks.file_format = File_Format |                              ^^^^^^^^^^^ | NameError: name 'File_Format' is not defined
* `nb_CellTracksColab_CellTracksColab_Custom_runs` (nb/notebook) 80 cells and stages executed; failing cells: none; failing click stages/assertions: click_auto_load_Submit; executed notebook: /home/user/results/alpha2/CellTracksColab/executed/CellTracksColab_Custom.ipynb
* `syn_ct_inf_position_0_status` (synthetic/cli) status COMPLETE, expected FAILED (error: None)
* `syn_ct_duplicate_time_0_table_bound` (synthetic/cli) Max Speed: largest value 1e+10 (limit 1e+06), all finite: True

### CellTracksColab: HUMAN (24)

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
* `ui_fiji_forms_not_checked` (ui/fiji) 'CellTracksColab' is not listed in Fiji, so there is no form to check

## GuessTheCondition

| family | host | PASS | FAIL | NOT_RUN | HUMAN | NOTE | finished |
|---|---|---|---|---|---|---|---|
| install | cli | 2 | 0 | 0 | 0 | 0 | 2026-10-15T09:55:29 |
| nb | notebook | 46 | 0 | 0 | 0 | 11 | 2026-10-15T08:17:31 |
| sandbox | cli | 46 | 0 | 0 | 0 | 2 | 2026-10-15T08:17:08 |
| synthetic | cli | 146 | 0 | 0 | 0 | 0 | 2026-10-15T08:22:04 |
| synthetic | napari | 142 | 0 | 0 | 0 | 4 | 2026-10-15T08:28:38 |
| ui | fiji | 64 | 1 | 0 | 9 | 0 | 2026-10-15T08:40:05 |
| ui | fiji | 32 | 1 | 0 | 3 | 0 | 2026-10-15T08:49:10 |
| ui | napari | 37 | 0 | 0 | 1 | 0 | 2026-10-15T08:19:04Z |
| ui | qupath | 37 | 0 | 0 | 7 | 0 | 2026-10-15T08:59:16Z |
| ui | fiji | 16 | 1 | 4 | 1 | 0 | 2026-10-15T09:53:41 |
| ui | napari | 40 | 0 | 0 | 1 | 0 | 2026-10-15T09:47:00Z |

### GuessTheCondition: FAIL (3)

* `ui_fiji_panel_form_cancel` (ui/fiji) the summary does not say cancelled; a run started (status 'FAILED'); 1 run record(s) were created
* `ui_fiji_panel_form_cancel` (ui/fiji) the summary does not say cancelled; a run started (status 'FAILED'); 1 run record(s) were created
* `ui_fiji_panel_form_cancel` (ui/fiji) the summary does not say cancelled; a run started (status 'FAILED'); 1 run record(s) were created

### GuessTheCondition: NOT_RUN (4)

* `ui_fiji_panel_copy_terminal` (ui/fiji) no tool completed a run in this audit, so there is no command to copy
* `ui_fiji_panel_copy_python` (ui/fiji) no tool completed a run in this audit, so there is no command to copy
* `ui_fiji_panel_log` (ui/fiji) no tool completed a run, so there is no Log of a run to read
* `ui_fiji_panel_form_ok` (ui/fiji) the audit ended without producing this check (a crash, a timeout, or a step that was never reached)

### GuessTheCondition: HUMAN (22)

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
* `ui_qupath_form_analyze_results_browse` (ui/qupath) the native file chooser of [results_folder] cannot be driven under Xvfb: the browse buttons were checked for presence, enabled state and an action, and the path was typed into the field
* `ui_qupath_form_create_demo_experiment_browse` (ui/qupath) the native file chooser of [output_folder] cannot be driven under Xvfb: the browse buttons were checked for presence, enabled state and an action, and the path was typed into the field
* `ui_qupath_form_list_conditions_browse` (ui/qupath) the native file chooser of [results_folder] cannot be driven under Xvfb: the browse buttons were checked for presence, enabled state and an action, and the path was typed into the field
* `ui_qupath_form_play_round_browse` (ui/qupath) the native file chooser of [results_folder] cannot be driven under Xvfb: the browse buttons were checked for presence, enabled state and an action, and the path was typed into the field
* `ui_qupath_run_play_round_unverified` (ui/qupath) expectation(s) the GUI cannot check: expect.progress_events_min
* `ui_qupath_form_prepare_game_browse` (ui/qupath) the native file chooser of [experiment_folder, results_folder] cannot be driven under Xvfb: the browse buttons were checked for presence, enabled state and an action, and the path was typed into the field
* `ui_qupath_form_undo_last_guess_browse` (ui/qupath) the native file chooser of [results_folder] cannot be driven under Xvfb: the browse buttons were checked for presence, enabled state and an action, and the path was typed into the field
* `ui_fiji_parts` (ui/fiji) only ['panel'] ran (LC_UI_PARTS)
* `ui_napari_panel_cancel_running` (ui/napari) no case of cases.json sets cancel_after_s: a person presses Cancel during a long run

## LabConstrictorPlayground

| family | host | PASS | FAIL | NOT_RUN | HUMAN | NOTE | finished |
|---|---|---|---|---|---|---|---|
| nb | notebook | 45 | 0 | 0 | 0 | 10 | 2026-10-15T10:23:43 |
| sandbox | cli | 54 | 1 | 0 | 0 | 3 | 2026-10-15T10:16:29 |
| synthetic | cli | 163 | 2 | 0 | 2 | 0 | 2026-10-15T10:29:27 |
| synthetic | napari | 163 | 10 | 0 | 0 | 4 | 2026-10-15T10:33:03 |
| ui | fiji | 115 | 3 | 0 | 18 | 0 | 2026-10-15T10:35:04 |
| ui | napari | 60 | 8 | 0 | 14 | 0 | 2026-10-15T10:19:28Z |
| ui | qupath | 28 | 0 | 0 | 3 | 0 | NOT FINISHED |
| install | cli | 1 | 1 | 0 | 0 | 0 | 2026-10-15T10:47:40 |
| nb | notebook | 45 | 0 | 0 | 0 | 10 | 2026-10-15T10:23:43 |
| sandbox | cli | 54 | 1 | 0 | 0 | 3 | 2026-10-15T10:16:29 |
| synthetic | cli | 163 | 2 | 0 | 2 | 0 | 2026-10-15T10:29:27 |
| synthetic | napari | 163 | 10 | 0 | 0 | 4 | 2026-10-15T10:33:03 |
| ui | fiji | 115 | 3 | 0 | 18 | 0 | 2026-10-15T10:35:04 |
| ui | napari | 60 | 8 | 0 | 14 | 0 | 2026-10-15T10:19:28Z |
| ui | qupath | 67 | 0 | 11 | 12 | 0 | 2026-10-15T10:47:09Z |

### LabConstrictorPlayground: FAIL (49)

* `1_installer_succeeds` (sandbox/cli) exit=1
* `syn_pg_ramp_f32_p90_2_value:level_used` (synthetic/cli) level_used = 89.099853515625, expected 89.09999999999991 (tol 0.0001, rtol 0)
* `syn_pg_make_three_channels_1_tiff_slice_means` (synthetic/cli) three_channels.tif: means [42.713, 20.0, 30.0], expected [10, 20, 30]
* `syn_host_napari_pg_channels_cyx_0_host_param` (synthetic/napari) the host reported nothing for 'blobs_channel_0' (host_observed: [])
* `syn_host_napari_pg_channels_cyx_1_host_param` (synthetic/napari) the host reported nothing for 'blobs_channel_1' (host_observed: [])
* `syn_host_napari_pg_channels_cyx_2_host_param` (synthetic/napari) the host reported nothing for 'blobs_channel_2' (host_observed: [])
* `syn_host_napari_pg_channels_cyx_cli_0_status` (synthetic/napari) status COMPLETE, expected FAILED (error: None)
* `syn_host_napari_pg_rgb_0_host_param` (synthetic/napari) the host reported nothing for 'blobs_channel_0' (host_observed: [])
* `syn_host_napari_pg_rgb_1_host_param` (synthetic/napari) the host reported nothing for 'blobs_channel_1' (host_observed: [])
* `syn_host_napari_pg_rgb_2_host_param` (synthetic/napari) the host reported nothing for 'blobs_channel_2' (host_observed: [])
* `syn_host_napari_pg_ramp_f32_p90_2_value:level_used` (synthetic/napari) level_used = 89.099853515625, expected 89.09999999999991 (tol 0.0001, rtol 0)
* `syn_host_napari_pg_pixel_zero_0_status` (synthetic/napari) code 'pixel_size_unknown', expected 'invalid_pixel_size'; message "[pixel_size_unknown] The pixel size of the image is unknown, so an area in um2 cannot be given. Set 'pixel_size' (um per pixel) or calibrate the image." lacks 'above 0'
* `syn_host_napari_pg_make_three_channels_1_tiff_slice_means` (synthetic/napari) no file matches fixtures/pg_make_out/three_channels*.tif under /home/user/synthetic/LabConstrictor-Playground
* `ui_fiji_form_list_devices_controls` (ui/fiji) no control of the form could be activated (0 found)
* `ui_fiji_form_stress_crash_controls` (ui/fiji) no control of the form could be activated (0 found)
* `ui_fiji_form_stress_out_of_memory_controls` (ui/fiji) no control of the form could be activated (0 found)
* `ui_napari_run_feature_tour` (ui/napari) AssertionError: shapes 'outlines': no layer, table or file in the status
* `ui_napari_run_look_inside_file` (ui/napari) AssertionError: top-level windows are ['QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', '_QtMainWindow'], expected ['_QtMainWindow']
* `ui_napari_form_summarise_table_controls` (ui/napari) AssertionError: top-level windows are ['QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', '_QtMainWindow'], expected ['_QtMainWindow']
* `ui_napari_form_bright_area_opens` (ui/napari) a slot raised or a dialog interrupted: EmitLoopError:  |  | While emitting signal 'magicgui.widgets.RadioButtons.changed', an error occurred in a callback: |  |   AttributeError: 'FunctionGui' object has no attribute 'pixel_size' |   ------------------------------------------------------------------ |  |   SIGNAL EMISSION:  |     /home/user/w/venv/lib/python3.11/site-packages/magicgui/backends/_qtpy/widgets.py:1096 in _emit_data |       self._event_filter.valueChanged.emit(self._mgui_get_value()
* `ui_napari_run_bright_area` (ui/napari) a slot raised or a dialog interrupted: EmitLoopError:  |  | While emitting signal 'magicgui.widgets.RadioButtons.changed', an error occurred in a callback: |  |   AttributeError: 'FunctionGui' object has no attribute 'pixel_size' |   ------------------------------------------------------------------ |  |   SIGNAL EMISSION:  |     /home/user/w/venv/lib/python3.11/site-packages/magicgui/backends/_qtpy/widgets.py:1096 in _emit_data |       self._event_filter.valueChanged.emit(self._mgui_get_value()
* `ui_napari_run_align_centres` (ui/napari) AssertionError: prerequisite case 27 (bright_area) ended FAILED pixel_size_unknown, its expect says FAILED invalid_pixel_size | ✖ [pixel_size_unknown] The pixel size of the image is unknown, so an area in um2 cannot be given. Set 'pixel_size' (um per pixel) or calibrate the image.  - click Details… for the full report (log: /home/user/apps/a2_lc_home_Playground/logs/labconstrictor.log)
* `ui_napari_screens_align_centres` (ui/napari) AssertionError: align_centres_form.png does not exist; align_centres_after_run.png does not exist
* `ui_napari_panel_tool_chooser` (ui/napari) a slot raised or a dialog interrupted: EmitLoopError:  |  | While emitting signal 'magicgui.widgets.RadioButtons.changed', an error occurred in a callback: |  |   AttributeError: 'FunctionGui' object has no attribute 'region' |   -------------------------------------------------------------- |  |   SIGNAL EMISSION:  |     /home/user/w/venv/lib/python3.11/site-packages/magicgui/backends/_qtpy/widgets.py:1096 in _emit_data |       self._event_filter.valueChanged.emit(self._mgui_get_value()) |     
* `install_exit0` (install/cli) installer exit=1 after 5m40s: post_install pip step ran out of disk (ENOSPC) while downloading nvidia_cudnn: the Linux requirements pull torch 2.8.0 with its CUDA wheels (about 4 GB download, 4 GB installed); this machine had 6 GB free. Completed by hand (CUDA wheels removed, torch 2.8.0+cpu, rest of post_install.sh rerun): environment
* `1_installer_succeeds` (sandbox/cli) exit=1
* `syn_pg_ramp_f32_p90_2_value:level_used` (synthetic/cli) level_used = 89.099853515625, expected 89.09999999999991 (tol 0.0001, rtol 0)
* `syn_pg_make_three_channels_1_tiff_slice_means` (synthetic/cli) three_channels.tif: means [42.713, 20.0, 30.0], expected [10, 20, 30]
* `syn_host_napari_pg_channels_cyx_0_host_param` (synthetic/napari) the host reported nothing for 'blobs_channel_0' (host_observed: [])
* `syn_host_napari_pg_channels_cyx_1_host_param` (synthetic/napari) the host reported nothing for 'blobs_channel_1' (host_observed: [])
* `syn_host_napari_pg_channels_cyx_2_host_param` (synthetic/napari) the host reported nothing for 'blobs_channel_2' (host_observed: [])
* `syn_host_napari_pg_channels_cyx_cli_0_status` (synthetic/napari) status COMPLETE, expected FAILED (error: None)
* `syn_host_napari_pg_rgb_0_host_param` (synthetic/napari) the host reported nothing for 'blobs_channel_0' (host_observed: [])
* `syn_host_napari_pg_rgb_1_host_param` (synthetic/napari) the host reported nothing for 'blobs_channel_1' (host_observed: [])
* `syn_host_napari_pg_rgb_2_host_param` (synthetic/napari) the host reported nothing for 'blobs_channel_2' (host_observed: [])
* `syn_host_napari_pg_ramp_f32_p90_2_value:level_used` (synthetic/napari) level_used = 89.099853515625, expected 89.09999999999991 (tol 0.0001, rtol 0)
* `syn_host_napari_pg_pixel_zero_0_status` (synthetic/napari) code 'pixel_size_unknown', expected 'invalid_pixel_size'; message "[pixel_size_unknown] The pixel size of the image is unknown, so an area in um2 cannot be given. Set 'pixel_size' (um per pixel) or calibrate the image." lacks 'above 0'
* `syn_host_napari_pg_make_three_channels_1_tiff_slice_means` (synthetic/napari) no file matches fixtures/pg_make_out/three_channels*.tif under /home/user/synthetic/LabConstrictor-Playground
* `ui_fiji_form_list_devices_controls` (ui/fiji) no control of the form could be activated (0 found)
* `ui_fiji_form_stress_crash_controls` (ui/fiji) no control of the form could be activated (0 found)
* `ui_fiji_form_stress_out_of_memory_controls` (ui/fiji) no control of the form could be activated (0 found)
* `ui_napari_run_feature_tour` (ui/napari) AssertionError: shapes 'outlines': no layer, table or file in the status
* `ui_napari_run_look_inside_file` (ui/napari) AssertionError: top-level windows are ['QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', '_QtMainWindow'], expected ['_QtMainWindow']
* `ui_napari_form_summarise_table_controls` (ui/napari) AssertionError: top-level windows are ['QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', 'QRadioButton', '_QtMainWindow'], expected ['_QtMainWindow']
* `ui_napari_form_bright_area_opens` (ui/napari) a slot raised or a dialog interrupted: EmitLoopError:  |  | While emitting signal 'magicgui.widgets.RadioButtons.changed', an error occurred in a callback: |  |   AttributeError: 'FunctionGui' object has no attribute 'pixel_size' |   ------------------------------------------------------------------ |  |   SIGNAL EMISSION:  |     /home/user/w/venv/lib/python3.11/site-packages/magicgui/backends/_qtpy/widgets.py:1096 in _emit_data |       self._event_filter.valueChanged.emit(self._mgui_get_value()
* `ui_napari_run_bright_area` (ui/napari) a slot raised or a dialog interrupted: EmitLoopError:  |  | While emitting signal 'magicgui.widgets.RadioButtons.changed', an error occurred in a callback: |  |   AttributeError: 'FunctionGui' object has no attribute 'pixel_size' |   ------------------------------------------------------------------ |  |   SIGNAL EMISSION:  |     /home/user/w/venv/lib/python3.11/site-packages/magicgui/backends/_qtpy/widgets.py:1096 in _emit_data |       self._event_filter.valueChanged.emit(self._mgui_get_value()
* `ui_napari_run_align_centres` (ui/napari) AssertionError: prerequisite case 27 (bright_area) ended FAILED pixel_size_unknown, its expect says FAILED invalid_pixel_size | ✖ [pixel_size_unknown] The pixel size of the image is unknown, so an area in um2 cannot be given. Set 'pixel_size' (um per pixel) or calibrate the image.  - click Details… for the full report (log: /home/user/apps/a2_lc_home_Playground/logs/labconstrictor.log)
* `ui_napari_screens_align_centres` (ui/napari) AssertionError: align_centres_form.png does not exist; align_centres_after_run.png does not exist
* `ui_napari_panel_tool_chooser` (ui/napari) a slot raised or a dialog interrupted: EmitLoopError:  |  | While emitting signal 'magicgui.widgets.RadioButtons.changed', an error occurred in a callback: |  |   AttributeError: 'FunctionGui' object has no attribute 'region' |   -------------------------------------------------------------- |  |   SIGNAL EMISSION:  |     /home/user/w/venv/lib/python3.11/site-packages/magicgui/backends/_qtpy/widgets.py:1096 in _emit_data |       self._event_filter.valueChanged.emit(self._mgui_get_value()) |     

### LabConstrictorPlayground: NOT_RUN (11)

* `ui_qupath_form_feature_tour_channel` (ui/qupath) image.channel(no multi-channel fixture three_channels.tif)
* `ui_qupath_run_stress_big_image` (ui/qupath) 'stress_big_image' has no case that expects COMPLETE in cases.json (failing, cancel, skipped and stress cases are not run through the form) and is not declared in no_case.json
* `ui_qupath_screens_stress_big_image` (ui/qupath) 'stress_big_image' was not run, so there is no after-run picture
* `ui_qupath_run_stress_crash` (ui/qupath) 'stress_crash' has no case that expects COMPLETE in cases.json (failing, cancel, skipped and stress cases are not run through the form) and is not declared in no_case.json
* `ui_qupath_screens_stress_crash` (ui/qupath) 'stress_crash' was not run, so there is no after-run picture
* `ui_qupath_run_stress_many_points` (ui/qupath) 'stress_many_points' has no case that expects COMPLETE in cases.json (failing, cancel, skipped and stress cases are not run through the form) and is not declared in no_case.json
* `ui_qupath_screens_stress_many_points` (ui/qupath) 'stress_many_points' was not run, so there is no after-run picture
* `ui_qupath_run_stress_out_of_memory` (ui/qupath) 'stress_out_of_memory' has no case that expects COMPLETE in cases.json (failing, cancel, skipped and stress cases are not run through the form) and is not declared in no_case.json
* `ui_qupath_screens_stress_out_of_memory` (ui/qupath) 'stress_out_of_memory' was not run, so there is no after-run picture
* `ui_qupath_run_stress_slow` (ui/qupath) 'stress_slow' has no case that expects COMPLETE in cases.json (failing, cancel, skipped and stress cases are not run through the form) and is not declared in no_case.json
* `ui_qupath_screens_stress_slow` (ui/qupath) 'stress_slow' was not run, so there is no after-run picture

### LabConstrictorPlayground: HUMAN (83)

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
* `ui_qupath_run_stress_hang` (ui/qupath) no case of 'stress_hang' is run (declared in no_case.json: no grace-period kill in the case runner; covered by the host test suites and the sandbox extras); the form checks were made
* `ui_qupath_screens_stress_hang` (ui/qupath) 'stress_hang' is not run, so only the form picture stress_hang_form.png exists, for a person to look at
* `ui_qupath_run_stress_real_memory` (ui/qupath) no case of 'stress_real_memory' is run (declared in no_case.json: opt-in, uses real memory; covered by the sandbox extras); the form checks were made
* `ui_qupath_screens_stress_real_memory` (ui/qupath) 'stress_real_memory' is not run, so only the form picture stress_real_memory_form.png exists, for a person to look at
* `ui_qupath_form_summarise_table_browse` (ui/qupath) the native file chooser of [table] cannot be driven under Xvfb: the browse buttons were checked for presence, enabled state and an action, and the path was typed into the field
* `ui_qupath_run_summarise_table_unverified` (ui/qupath) expectation(s) the GUI cannot check: summary.cells

## VLab4Mic

| family | host | PASS | FAIL | NOT_RUN | HUMAN | NOTE | finished |
|---|---|---|---|---|---|---|---|
| install | cli | 2 | 0 | 0 | 0 | 0 | 2026-10-15T09:55:29 |
| nb | notebook | 43 | 0 | 0 | 2 | 14 | 2026-10-15T09:31:07 |
| sandbox | cli | 54 | 0 | 0 | 0 | 1 | 2026-10-15T09:29:54 |
| synthetic | cli | 83 | 3 | 0 | 4 | 0 | 2026-10-15T09:36:50 |
| synthetic | napari | 78 | 5 | 0 | 1 | 9 | 2026-10-15T09:45:08 |
| ui | fiji | 90 | 0 | 0 | 3 | 0 | 2026-10-15T09:29:37 |
| ui | napari | 21 | 0 | 0 | 3 | 0 | 2026-10-15T09:23:51Z |
| ui | qupath | 1 | 0 | 0 | 0 | 1 | 2026-10-15T09:45:36Z |
| ui | fiji | 20 | 0 | 4 | 2 | 0 | 2026-10-15T09:55:00 |
| ui | napari | 24 | 0 | 0 | 3 | 0 | 2026-10-15T09:51:28Z |

### VLab4Mic: FAIL (8)

* `syn_vm_flat_reference_0_status` (synthetic/cli) status COMPLETE, expected FAILED (error: None)
* `syn_vm_zero_reference_0_status` (synthetic/cli) status COMPLETE, expected FAILED (error: None)
* `syn_vm_different_fields_2_value:ssim` (synthetic/cli) ssim = 0.778662, expected 0.0 (tol 0.3, rtol 0)
* `syn_host_napari_vm_cal_micro_0_host_param` (synthetic/napari) host showed reference_pixel_size_um = None, expected 0.02
* `syn_host_napari_vm_flat_reference_0_status` (synthetic/napari) status COMPLETE, expected FAILED (error: None)
* `syn_host_napari_vm_zero_reference_0_status` (synthetic/napari) status COMPLETE, expected FAILED (error: None)
* `syn_host_napari_vm_pixel_zero_0_status` (synthetic/napari) status COMPLETE, expected FAILED (error: None)
* `syn_host_napari_vm_different_fields_2_value:ssim` (synthetic/napari) ssim = 0.778662, expected 0.0 (tol 0.3, rtol 0)

### VLab4Mic: NOT_RUN (4)

* `ui_fiji_panel_copy_terminal` (ui/fiji) no tool completed a run in this audit, so there is no command to copy
* `ui_fiji_panel_copy_python` (ui/fiji) no tool completed a run in this audit, so there is no command to copy
* `ui_fiji_panel_log` (ui/fiji) no tool completed a run, so there is no Log of a run to read
* `ui_fiji_panel_form_ok` (ui/fiji) the audit ended without producing this check (a crash, a timeout, or a step that was never reached)

### VLab4Mic: HUMAN (18)

* `nb_VLab4Mic_VLab4Mic_main_click_load_structure_from_file` (nb/notebook) the 'Load structure from file' route needs a PDB/CIF file chosen in a file chooser: not driven
* `nb_VLab4Mic_VLab4Mic_parameter_sweeps_click_structure_from_file` (nb/notebook) 'Load structure from file', 'Upload image reference' and the saving-directory chooser need files chosen in a file chooser: not driven
* `syn_vm_cal_anisotropic_note` (synthetic/cli) has no machine oracle for this run (HUMAN): judged by a person
* `syn_vm_cal_um_note` (synthetic/cli) has no machine oracle for this run (works): judged by a person or by a host driver (--with-host)
* `syn_vm_cal_nm_note` (synthetic/cli) has no machine oracle for this run (works): judged by a person or by a host driver (--with-host)
* `syn_vm_cal_micro_note` (synthetic/cli) has no machine oracle for this run (works): judged by a person or by a host driver (--with-host)
* `syn_host_napari_vm_cal_anisotropic_note` (synthetic/napari) has no machine oracle for this run (HUMAN): judged by a person
* `ui_fiji_panel_chooser_app` (ui/fiji) not applicable: only one app is listed, so Fiji shows no app chooser
* `ui_fiji_run_compare_images` (ui/fiji) expectations of the case that Fiji cannot check: max_seconds
* `ui_fiji_run_simulate_sample` (ui/fiji) expectations of the case that Fiji cannot check: max_seconds
* `ui_napari_prerequisite_simulate_sample_case12` (ui/napari) case 12 of simulate_sample cannot be typed into the form (value 1.5 is outside of the allowed range: (0.0, 1.0)); its expected outcome {'status': 'FAILED', 'code': 'invalid_parameter', 'message_contains': 'Labelling efficiency'} is covered by the CLI
* `ui_napari_prerequisite_simulate_sample_case13` (ui/napari) case 13 of simulate_sample cannot be typed into the form (value 0 is outside of the allowed range: (1, 20)); its expected outcome {'status': 'FAILED', 'code': 'invalid_parameter', 'message_contains': 'Number of particles'} is covered by the CLI
* `ui_napari_panel_cancel_running` (ui/napari) no case of cases.json sets cancel_after_s: a person presses Cancel during a long run
* `ui_fiji_parts` (ui/fiji) only ['panel'] ran (LC_UI_PARTS)
* `ui_fiji_panel_copy_empty` (ui/fiji) LC_HOME already holds a last command (state/last_command.json), so the 'nothing to copy yet' state cannot be tested here
* `ui_napari_prerequisite_simulate_sample_case12` (ui/napari) case 12 of simulate_sample cannot be typed into the form (value 1.5 is outside of the allowed range: (0.0, 1.0)); its expected outcome {'status': 'FAILED', 'code': 'invalid_parameter', 'message_contains': 'Labelling efficiency'} is covered by the CLI
* `ui_napari_prerequisite_simulate_sample_case13` (ui/napari) case 13 of simulate_sample cannot be typed into the form (value 0 is outside of the allowed range: (1, 20)); its expected outcome {'status': 'FAILED', 'code': 'invalid_parameter', 'message_contains': 'Number of particles'} is covered by the CLI
* `ui_napari_panel_cancel_running` (ui/napari) no case of cases.json sets cancel_after_s: a person presses Cancel during a long run

## all

| family | host | PASS | FAIL | NOT_RUN | HUMAN | NOTE | finished |
|---|---|---|---|---|---|---|---|
| multi | cli | 11 | 0 | 0 | 0 | 0 | 2026-10-15T09:03:12 |

