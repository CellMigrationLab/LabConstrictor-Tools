# Alpha.4 final checks of the LabConstrictor tools bridge (hosts v0.1.0-alpha.4, Linux, one app at a time, 15 Oct 2026)

Hosts (verified before use): Napari `napari-labconstrictor` tag v0.1.0-alpha.4 (napari 0.9.2 PyQt6, labconstrictor-tools 0.3.0a1) in /home/user/w/venv; Fiji loose script byte-identical to the alpha.4 zip (sha256 of zip and jar OK), jar used for one jar-mode pass (loose script restored afterwards, `diff -r` against the backup identical); QuPath alpha.4 jar. Drivers: tip of claude/ui-audit-napari, -fiji, -qupath (worktrees wt3_*), unchanged. Tools/sandbox/notebook runners unchanged except the patched NucleiSky click scripts (copy in /home/user/a4/nb_scripts, `NucleiSky/runner_script_patches.diff`). Apps: VLab4Mic 0.1.7, CellTracksColab 1.1.3, NucleiSky 0.1.4, each installed (installer with PIP_EXTRA_INDEX_URL = pytorch CPU index), tested, uninstalled with its uninstall.sh (exit 0, prefix gone) before the next.

## Counts

| app | family | host | PASS | FAIL | NOT_RUN | HUMAN | NOTE | remark |
|---|---|---|---|---|---|---|---|---|
| VLab4Mic 0.1.7 | sandbox basic,hosts,cases | cli | 49 | 0 | 0 | 0 | 0 | new cases (flat ref, zero ref, csv structure) PASS: `flat_image`, `flat_image`, `structure_file_type` |
| VLab4Mic | ui | napari | 21 | 0 | 0 | 3 | 0 | compare_images + simulate_sample forms |
| VLab4Mic | ui | fiji (script), final pass | 90 | 0 | 0 | 5 | 0 | pass 1 had 21 FAIL (simulate_sample dialog 1066x3024, oversized), not reproduced in 2 reruns, see findings |
| VLab4Mic | ui | fiji (script), pass 1 | 70 | 21 | 0 | 4 | 0 | kept as `ui_fiji_pass1` |
| VLab4Mic | ui | fiji simulate_sample only | 77 | 0 | 0 | 5 | 0 | |
| VLab4Mic | synthetic | cli | 85 | 1 | 0 | 4 | 0 | the FAIL is VL-6 truth row (ssim 0.778662); vm_flat_reference / vm_zero_reference now FAIL with flat_image = expectation updated, PASS |
| VLab4Mic | N-1 radio check | napari | 3 | 0 | 0 | 0 | 0 | simulate_sample has NO radio in 0.1.7 (4 combo boxes): see findings |
| RadioProbe (test app, my own) | N-1 radio check | napari | 3 | 0 | 0 | 0 | 0 | form with two radios, 7 layer cycles + 20 single insert/remove + gc: 0 strays |
| CellTracksColab 1.1.3 | sandbox basic,hosts,cases,retention | cli | 33 | 0 | 0 | 0 | 0 | |
| CellTracksColab | synthetic | cli | 53 | 0 | 0 | 0 | 0 | ct_duplicate_time expectation updated (was COMPLETE), counted PASS, raw checker line FAIL is in synthetic_check.txt |
| CellTracksColab | listing (not listed) | napari / fiji / qupath | 1 / 1 / 1 | 0 | 0 | 1 / 0 / 0 | 0 / 0 / 1 | with RadioNeighbour (hosts napari,fiji,qupath) registered next to it |
| CellTracksColab | nb (Custom only) | notebook | 38 | 1 | 0 | 3 | 4 | the FAIL is `notebooks_inventory` (only one notebook was run: artifact of --only) |
| NucleiSky 0.1.4 | sandbox basic,hosts,cases,retention | cli | 49 | 0 | 0 | 0 | 1 | |
| NucleiSky | nb all 7, final scripts | notebook | 86 | 7 | 0 | 8 | 40 | 7 FAIL = 1 app bug (3DApp) + 3D API example demo (app); earlier passes kept in `nb_pass*` |
| NucleiSky | synthetic | cli | 111 | 3 | 0 | 1 | 0 | ns_nan_reference (app), 2 points_map (truth/tolerance) |
| NucleiSky | synthetic | napari (layer) | 127 | 5 | 0 | 1 | 0 | + mask_fractions, mask_nan: Labels layers are integer |
| NucleiSky | synthetic | napari (file input) | 129 | 3 | 0 | 1 | 0 | same 3 as the CLI |
| NucleiSky | ui | napari (layer) | 15 | 6 | 0 | 1 | 0 | all 6 = driver gaps (below) |
| NucleiSky | ui | napari (file input) | 17 | 4 | 0 | 1 | 0 | copy rows PASS here |
| NucleiSky | ui | fiji (script) | 77 | 1 | 0 | 3 | 0 | driver gap |
| NucleiSky | ui | fiji (jar) | 76 | 1 | 0 | 4 | 0 | same driver gap |
| NucleiSky | ui | qupath | 20 | 1 | 0 | 2 | 0 | driver gap (enabled_when) |

## The new refusals, re-verified
* VLab4Mic 0.1.7: flat reference -> FAILED `flat_image` "The reference image has the same value everywhere: similarity cannot be measured."; all-zero reference same; .csv as structure file -> `structure_file_type` (cases 19/29/30/31 of the app's own cases.json and the synthetic CLI set). This replaces VL-5 (alpha.3: COMPLETE).
* CellTracksColab 1.1.3 through the CLI: infinite coordinate -> `non_finite_position` ("1 row(s) have an infinite position or time"); two spots at one time -> `same_time_twice` ("2 spot(s) share a time with another spot of the same track"); normal data (ct_linear_2d and 22 other datasets) COMPLETE with the exact numbers.
* CellTracksColab Custom notebook, "Use test dataset" UNTICKED, local synthetic CSV folder (2 conditions x 3 experiments x 8 tracks of 20 spots): Submit no longer raises NameError (0 NameError in the log, `click_auto_load_Submit PASS`, merged_Spots 960 rows / 48 tracks / 2 conditions, whole notebook oracle PASS). The script still prints its old 'workaround' NOTE row (stale text of the click script, not a new failure).

## Napari layer-event check (N-1)
VLab4Mic simulate_sample (0.1.7) has no radio at all (its four choices are combo boxes; the host only builds RadioButtons for `widget: radio`, and the installed schema has none), so the requested test could not be run as stated: with that form shown, layers inserted and removed 1/3/3/3/6/6/10 at a time, 20 single insert/remove, gc: 0 stray top-level QRadioButtons (PASS, but no radio on screen). To exercise the real code path a test app with two radio parameters was registered in a private registry (VLab4Mic's python, module `radio_probe_lc_tools`): same cycles: 0 strays; detector control (a deliberately shown parentless QRadioButton counts 1). `VLab4Mic/napari_alpha4*`.

## NucleiSky calibration rules and the known answer
* Pixel sizes 0.65 / 0.325 um: sandbox case 0 (reference 1600x1600, query 520x520): rotation 12.17 deg (12 +/- 1), scale 1.0024, offset (700.33, 605.57) vs (700.06, 606.1) +/- 4, 429 / 9 nuclei: PASS (CLI sandbox, and again through Napari and Fiji forms). ns_normal (-20 deg at 2x), ns_pure_shift, ns_rotation_only (+35), um / nm / micro-sign / 'micron' calibrations, 8-bit and float32: all PASS.
* An uncalibrated image blocks the run: `ns_small_nocal` and `ns_small_pixelunit` refused `missing_parameter` (CLI); in Napari the field stays blank and Run is blocked (host rows PASS); sandbox cases 20-22 (`missing_parameter`), 23-25 (`invalid_parameter` for 0 and negative sizes) PASS.

## Not run / limits
Windows and macOS installers; native file choosers (HUMAN); Cellpose / InstanSeg (model downloads, GPU: HUMAN rows); the full notebook family of CellTracksColab (only Custom was asked); QuPath synthetic for NucleiSky (not asked); Cancel during a long run (no case with cancel_after_s).
