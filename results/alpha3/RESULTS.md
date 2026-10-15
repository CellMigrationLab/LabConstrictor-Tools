# Alpha.3 re-verification of the LabConstrictor tools bridge (released v0.1.0-alpha.3 hosts, 15 Oct 2026)

Hosts (checked): Napari `napari-labconstrictor` from tag v0.1.0-alpha.3 (commit 09d94697, napari 0.9.2 PyQt6, labconstrictor-tools 0.3.0a1) in /home/user/w/venv; Fiji script zip unpacked in scripts/Plugins/LabConstrictor (byte-identical to the zip, sha256 of zip and jar OK) and the release jar for the jar-mode passes (the loose script was restored after every jar pass, `diff -r` against a backup identical; the audit driver removes it and does not restore it itself); QuPath jar b9a94b44... (= alpha.3 jar, sha256 OK). Apps (Linux x86_64 installers of the latest releases, one at a time, each uninstalled with its uninstall.sh, exit 0, prefix gone): GuessTheCondition 0.0.1, Playground 0.0.5 (registry name LabConstrictorPlayground), VLab4Mic 0.1.6. Alpha.1 and alpha.2 results were not touched (this round is results/alpha3/ only). Findings: FINDINGS.md.

Drivers used (pushed, no PRs): claude/ui-audit-napari daeb412, claude/ui-audit-fiji 0f926ea, claude/ui-audit-qupath 867aee5 (what changed: FINDINGS.md, Drivers). Tools branch claude/test-strategy 4952c54 (local commit: scripts of this round, collect_results keeps every alphaN round apart).

## Counts per app / family / host

| app | family | host | PASS | FAIL | NOT_RUN | HUMAN | NOTE | alpha.2 (same row) |
|---|---|---|---|---|---|---|---|---|
| GuessTheCondition 0.0.1 | sandbox | cli | 46 | 0 | 0 | 0 | 2 | alpha2: 46 PASS 2 NOTE |
| GuessTheCondition | synthetic | cli | 146 | 0 | 0 | 0 | 0 | alpha2: 146 PASS |
| GuessTheCondition | synthetic | napari | 142 | 0 | 0 | 0 | 4 | alpha2: 142 PASS 4 NOTE |
| GuessTheCondition | ui | napari | 37 | 0 | 0 | 1 | 0 | alpha2: 37 PASS 1 HUMAN (single app) |
| GuessTheCondition | ui | fiji (script) | 71 | 0 | 0 | 10 | 0 | alpha2: 64 PASS 1 FAIL 9 HUMAN |
| GuessTheCondition | ui | fiji (jar, 2 tools) | 33 | 1 | 0 | 5 | 0 | alpha2: 32 PASS 1 FAIL 3 HUMAN |
| GuessTheCondition | ui | fiji (jar, panel part only, rerun of the 1 FAIL) | 20 | 0 | 4 | 4 | 0 | NOT_RUN = tool rows outside the restricted part |
| GuessTheCondition | ui | qupath | 37 | 0 | 0 | 7 | 0 | alpha2: 37 PASS 7 HUMAN |
| LabConstrictorPlayground 0.0.5 | sandbox | cli | 55 | 0 | 0 | 0 | 3 | alpha2: 54 PASS 1 FAIL (installer) 3 NOTE |
| LabConstrictorPlayground | synthetic | cli | 163 | 2 | 0 | 2 | 0 | alpha2: 163 PASS 2 FAIL 2 HUMAN |
| LabConstrictorPlayground | synthetic | napari | 169 | 3 | 0 | 0 | 5 | alpha2: 163 PASS 10 FAIL 4 NOTE (old driver pass of this round: same) |
| LabConstrictorPlayground | ui | napari | 66 | 2 | 0 | 15 | 0 | alpha2: 60 PASS 8 FAIL 14 HUMAN (first pass of this round, older driver: 64 PASS 4 FAIL 14 HUMAN) |
| LabConstrictorPlayground | ui | fiji (script) | 120 | 0 | 0 | 18 | 0 | alpha2: 115 PASS 3 FAIL 18 HUMAN |
| LabConstrictorPlayground | ui | qupath | 67 | 0 | 1 | 22 | 0 | alpha2: 67 PASS 12 HUMAN 11 NOT_RUN |
| LabConstrictorPlayground | alpha3 checks | napari (real inputs) | 15 | 0 | 0 | 0 | 0 | new |
| VLab4Mic 0.1.6 | ui | napari | 21 | 0 | 0 | 3 | 0 | alpha2: 21 PASS 3 HUMAN |
| VLab4Mic | ui | fiji (script) | 90 | 0 | 0 | 5 | 0 | alpha2: 90 PASS 3 HUMAN |
| VLab4Mic | synthetic | napari | 79 | 3 | 0 | 1 | 10 | alpha2: 78 PASS 5 FAIL 1 HUMAN 9 NOTE |
| VLab4Mic | alpha3 checks | napari (real inputs) | 12 | 0 | 0 | 0 | 0 | new |

Reading the table: `PASS/FAIL/NOT_RUN/HUMAN/NOTE` are matrix statuses; HUMAN = for a person (native file chooser, stress tools, expectations a GUI cannot check). A row with 'PANEL PART ONLY' is a restricted rerun (LC_UI_PARTS=panel): its NOT_RUN rows are the tool rows outside the restriction, an artifact of the restriction. Superseded passes are kept on disk and named so (`ui_napari_pass1_old_driver`, `synthetic_napari_pass1_old_driver`, `ui_fiji_pass1_contended_with_synthetic_run`).

## What alpha.3 changed, re-verified with real input (every row a matrix row)

| claim | result | evidence |
|---|---|---|
| (1) Fiji FJ-1b: Cancel on a tool form with an empty required file/folder ends the command (nothing runs, no FAILED run record, status 'LabConstrictor: cancelled') | FIXED | GuessTheCondition script mode: `ui_fiji_panel_form_cancel PASS` (alpha.2: FAIL, run record FAILED missing_parameter), and a new row per tool, a plain Robot click on Cancel of the untouched form: `ui_fiji_fj1b_cancel_form_<tool>` PASS for all 6 tools (create_demo_experiment, prepare_game, list_conditions, play_round, undo_last_guess, analyze_results): "cancelled, nothing ran, no run record, status line 'LabConstrictor: cancelled'". Jar mode: create_demo_experiment PASS; prepare_game FAIL once ("a real click on form_cancel did not close the dialog within 5000 ms": one-off, rerun of the same row PASS, `ui_fiji_jar_rerun_PANEL_PART_ONLY`); Playground make_test_data (Data folder required, empty): script PASS, jar PASS; Playground first form (align_centres) and VLab4Mic first form (compare_images) `ui_fiji_panel_form_cancel` PASS |
| Cancel on the app chooser and tool chooser | FIXED (alpha.2 already for the chooser) | `ui_fiji_panel_chooser_cancel PASS` in every Fiji audit; with TWO apps listed (Playground + a registry copy PlaygroundTwin) the first chooser is the app chooser: Cancel PASS, `ui_fiji_panel_chooser_app` lists both; tool chooser Cancel (one app) PASS |
| required image with no image open still refuses with missing_parameter | OK (unchanged) | Playground align_centres, script and jar: `[missing_parameter] 'Image' is required: open an image or choose a file`, status line 'Command canceled: Align the centres of two images', no tool run (`ui_fiji_fj1b_missing_image_align_centres`); VLab4Mic compare_images (script): `[missing_parameter] 'Reference' is required ...` |
| (2) Napari: no AttributeError ('region'/'pixel_size') when switching tools back and forth (H-N4) | FIXED | Playground, 17 tools x 10 rounds there and back = 340 form switches, every radio and check box flipped (all choices): 0 exceptions on stderr/excepthook/Qt (own capture; its negative control, a failing psygnal callback, IS captured); the alpha.2 reproduction script (h_n4_repro) gives `ERRORS 0` (alpha.2: 2 x `no attribute 'region'`): `napari_alpha3/`, `h_n4_repro_alpha3.txt` |
| RGB layer Channel chooser lists Red/Green/Blue after an RGB layer is inserted, and stays | FIXED | feature_tour 'image': RGB layer chosen -> Red/Green/Blue, visible; same 2 s later; same after another layer was inserted and removed with the RGB layer chosen; each colour chosen and read back; again after a tool switch. Through the real form: `pg_rgb` and `pg_channels_cyx` (file in the 'or file' row, channel k picked, Run clicked) give 1/2/3 blobs (PASS, was a driver gap). Note: inserting an RGB layer does not select it in the form's layer chooser (value stays empty until the person picks it): a behaviour, not a failure |
| group headings fine | OK | every tool with groups (Playground 9 tools, VLab4Mic 2): the form's headings are exactly the schema's (advanced parameters last, as the host lays them out) and the same after visiting other tools and back |
| typing 0 into a pixel-size box shows 'status: 0 means: use the image's calibration' | FIXED (was silent) | Playground bright_area and VLab4Mic compare_images (both pixel-size boxes): image with a 0.5 um scale chosen, box 0.5; type 0 + Enter via QTest key events: status line "0 means: use the image's calibration", box shows 0.5 again |
| micrometre calibration written by Fiji fills the pixel-size field with 0.02 (VL-7) | FIXED | `evidence_fiji_written_um.tif` (ImageJ description `unit=\u00B5m`) and synthetic `vm_cal_micro.tif` in the 'or file' row: both pixel-size boxes of compare_images show 0.02; synthetic Napari `vm_cal_um`, `vm_cal_nm`, `vm_cal_micro` host_param PASS (0.02), `vm_cal_none` None PASS |
| (3) regression pass | see the table | GuessTheCondition: sandbox 46 PASS, Napari 37 PASS, Fiji script 71 PASS, QuPath 37 PASS, synthetic CLI 146 PASS, synthetic Napari 142 PASS: 0 FAIL |

## alpha.2 failures re-verified

| alpha.2 failure | alpha.3 |
|---|---|
| FJ-1b Fiji form Cancel runs the tool | FIXED (script and jar) |
| H-N4 Napari stale callbacks, AttributeError | FIXED |
| N-1 leftover top-level QRadioButtons | STILL FAILING (16 windows in the Playground audit, alpha.2: 22; minimal repro, see FINDINGS) |
| N-2 typed 0 silently replaced | PARTLY: no longer silent (status line says so); a typed 0 still cannot reach the tool's own refusal (`pg_pixel_zero` host row FAIL: ends pixel_size_unknown, truth says invalid_pixel_size) |
| VL-7 micrometre calibration | FIXED |
| Playground installer fails on a 6 GB disk (E-1) | environment, avoided: installer with `PIP_EXTRA_INDEX_URL=https://download.pytorch.org/whl/cpu` in the environment ran to exit 0 in 98 s with torch 2.8.0+cpu; `1_installer_succeeds` PASS is therefore with the CPU index, not the stock installer |
| Fiji driver fails zero-parameter tools (driver) | FIXED in the driver (Playground Fiji 120 PASS 0 FAIL, alpha.2 3 FAIL) |
| QuPath driver NOT_RUN for stress tools (driver) | FIXED in the driver (HUMAN, 22 HUMAN 1 NOT_RUN, alpha.2 12 HUMAN 11 NOT_RUN) |
| Napari driver wording / channel / job-folder gaps (driver) | FIXED in the driver (Playground synthetic Napari 169 PASS 3 FAIL, alpha.2 163/10) |
| unchanged app bugs VL-5 (flat/all-zero reference COMPLETE) | STILL FAILING (VLab4Mic synthetic Napari `vm_flat_reference`, `vm_zero_reference` COMPLETE) |
| VL-6 SSIM 0.7787 for unrelated images | STILL there (`vm_different_fields` ssim 0.778662; truth question) |
| VL-3, VL-4, VL-12, VL-13, CellTracksColab A-CT1..3, Playground synthetic float32/docstring rows | not re-run (outside this round's scope, or unchanged by construction): the two Playground synthetic FAIL rows are the same two truth/tolerance rows as alpha.2 |

## What could not be run
Windows and macOS installers; native file chooser dialogs (HUMAN rows); Cancel during a long run for apps without a cancel case; Playground on QuPath form 'channel' (no multi-channel fixture: 1 NOT_RUN); VLab4Mic on QuPath and the notebook / CellTracksColab / multi-app families (not asked this round); a negative control of the new Fiji FJ-1b rows against the alpha.2 script (the apps were uninstalled; the same predicate failed on alpha.2 as `ui_fiji_panel_form_cancel`); a full second Fiji jar-mode audit of Playground and VLab4Mic (jar mode was run once, for GuessTheCondition's two tools and for the Playground FJ-1b rows, as asked).
