# Results of the one-off test run

## GuessTheCondition

| family | host | PASS | FAIL | NOT_RUN | HUMAN | NOTE | finished |
|---|---|---|---|---|---|---|---|
| sandbox | cli | 36 | 2 | 5 | 0 | 1 | 2026-10-14T17:47:48 |

### GuessTheCondition: FAIL (2)

* `4_cli_case_00_create_demo_experiment_COMPLETE` (sandbox/cli) status=FAILED code=already_exists
* `6_runs_complete` (sandbox/cli) run 0 of create_demo_experiment: n_create_demo_experiment/run.json", |   "error": "[already_exists] /home/user/apps/run_src/GuessTheCondition/lc_tests/fixtures/results/GuessTheCondition_demo already exists: choose another folder, or delete it.", |   "code": "already_exists", |   "log": "/home/user/apps/lc_home/logs/labconstrictor.log" | } |

### GuessTheCondition: NOT_RUN (5)

* `6a_markers_present` (sandbox/cli) expected, never executed
* `6b_results_keep_newest_20` (sandbox/cli) expected, never executed
* `6d_prune_dry_run_json` (sandbox/cli) expected, never executed
* `6e_foreign_folders_left_alone` (sandbox/cli) expected, never executed
* `6f_run_records_keep_50` (sandbox/cli) expected, never executed

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

### VLab4Mic: how to read this section

* Release 0.1.6, Linux installer, installed into /home/user/apps/VLab4Mic with a private LC_HOME, then uninstalled (results kept). Hosts: released alpha.1 artifacts (Napari 0.1.0a1, Fiji script v0.1.0-alpha.1, QuPath v0.1.0-alpha.1). Registry hosts: notebook, napari, fiji (QuPath must NOT list it: PASS, but the QuPath registry held only this app, so that check cannot fail by listing another app).
* `nb notebook`: the FINAL matrix was produced with a patched COPY of the click scripts (results/VLab4Mic/nb_scripts_patched/PATCH.diff); the committed scripts give 11 FAIL (results/VLab4Mic/nb_history/). See findings VL-1 and VL-2. 2 HUMAN = native file choosers.
* `ui napari / fiji` rows repeat one id per control; the FAIL counts are rows, not ids. Distinct failing ids: Napari 6 (+1 HUMAN), Fiji 3. Almost all are audit-driver or already-known host defects (FINDINGS VL-4 to VL-8).
* `synthetic cli`: 41 datasets from /home/user/synthetic/LabConstrictor-VLab4Mic through `labconstrictor-tools run` (ground-truth checker: 83 PASS, 3 FAIL, 1 HUMAN); `synthetic napari`: calibration shown by the compare_images form for the synthetic files, plus a real Run in the Napari widget (results/VLab4Mic/synthetic_host_napari_run.json).
