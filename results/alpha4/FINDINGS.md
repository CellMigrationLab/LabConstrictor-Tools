# Alpha.4 final checks: findings (hosts v0.1.0-alpha.4; VLab4Mic 0.1.7, CellTracksColab 1.1.3, NucleiSky 0.1.4; Linux)

Written by the parent from the agent's report (the agent could not write this file). Counts are in RESULTS.md next to it.

## Re-verified as fixed
* **VL-5** (VLab4Mic 0.1.7): a flat or all-zero reference gives `flat_image`; a `.csv` structure file gives `structure_file_type`. Synthetic rows `vm_flat_reference` / `vm_zero_reference` now FAIL with `flat_image` (expectation updated in the matrix: both count as PASS). VL-6 (SSIM 0.7787 for unrelated sparse images) is the one remaining FAIL row of the VLab4Mic synthetic CLI matrix: a truth question, dropped from the generator by the owner.
* **A-CT1 / A-CT2** (CellTracksColab 1.1.3): infinite coordinate gives `non_finite_position`; two spots of one track at one time give `same_time_twice`; normal data completes with exact numbers (53 synthetic rows). `ct_duplicate_time` truth updated to the refusal.
* **A-CT3** (CellTracksColab Custom notebook): with "Use test dataset" unticked and a synthetic CSV folder (2 conditions x 3 experiments x 8 tracks of 20 spots) Submit no longer raises NameError; merged spots 960 rows, 48 tracks, oracle passes.
* **Hidden app:** CellTracksColab 1.1.3 is not listed in Napari, Fiji or QuPath with a neighbour app registered (a test app was the neighbour).
* **N-1** (stray radio windows): 0 strays after 7 insert/clear cycles, 20 single insert/removes and gc, with the VLab4Mic simulate_sample form and with a private two-radio test app. VLab4Mic 0.1.7 has no radio widget in its schema, so the real-radio path was exercised with the test app; a detector control counted 1 for a deliberately shown parentless radio.
* **NucleiSky calibration and known answer:** pixel sizes 0.65 / 0.325 um on the app's own case: rotation 12.17 deg (12 +/- 1), scale 1.0024, offset (700.33, 605.57) against (700.06, 606.1) +/- 4, 429 / 9 nuclei; PASS in CLI, Napari and Fiji. um / nm / micro-sign / 'micron' calibrations, 8-bit and float32 PASS. An uncalibrated image blocks the run (`missing_parameter`); pixel size 0 or negative gives `invalid_parameter`.

## Open: app bugs (NucleiSky 0.1.4)
* **NS-1** NucleiSky3DApp notebook imports `plot_warp_overlay3d` but calls `plot_warp_overlay3D` (NameError). "Run NucleiSky3D" prints "pyramid crashed" and exports nothing; "Run Adaptive" raises NameError. With the alias defined in a cell the rest passes (pyramid, translation (7.2, 29.6, 39.9) against the cut (8, 30, 40)). The package defines the upper-case alias; only the notebook import is wrong.
* **NS-2** `NucleiSky3D_API_Workflow_Example` ends in `RuntimeError: Matching failed` (cell 7) on its own synthetic volume (27 / 15 nuclei, crop scale 1.29): deterministic; the same matcher succeeds on a cleaner, larger volume.
* **NS-3** `relocalize` accepts a reference with a NaN block and returns COMPLETE (rotation 25.03, 250 nuclei): the NaN is silently replaced; it should refuse naming NaN. Same in CLI and Napari file mode.
* **NS-4** (minor) `query_outlines` of the app's own case has vertices at x = -1.0 (range -1.0 to 337) on a 520 px query: outlines leave the image by 1 px.

## Open: host
* **H-F1** (Fiji, intermittent, not reproduced) in the first full Fiji audit of VLab4Mic the `simulate_sample` dialog opened 1066x3024 on a 1600x1000 screen (21 FAIL rows); a simulate_sample-only rerun (77 PASS) and a full rerun (90 PASS) were clean with nothing else running.
* **H-N5** (Napari, minor, known) the status line keeps the previous tool's warning after a tool switch.
* Napari Labels layers are integer: fractional or NaN masks handed over as a layer arrive cast (host limit; file mode refuses them).

## Runner / driver bugs (not host faults)
Napari and QuPath drivers do not know `enabled_when` (4 cellpose/instanseg "set" fields fail the controls row; the Fiji driver passes); Napari audit replays prerequisite case 12 (pixel size -1) inside the next tool's row; layer-mode copy rows expect fixture paths (layer inputs get the documented placeholder `image.tif`); the Fiji placement check flags the second image's overlay of `relocalize` (two shapes outputs, each on its own image); the NucleiSky notebook click scripts had never been run against the app (patched copy /home/user/a4/nb_scripts, diff `NucleiSky/runner_script_patches.diff`); NucleiSky synthetic `ns_masks_exact` / `ns_masks_binary` bound unreachable with 12 nuclei (truth/tolerance).

## Environment
Installers: VLab4Mic 1 m 32 s, CellTracksColab 1 m 33 s, NucleiSky 3 m 20 s (2.8 GB; CPU torch index). All uninstalled (exit 0). The agent deleted scratch under /home/user/apps, a3 raw outputs, all /tmp/lc_ui_audit_tests_*, and by a mistaken glob part of the NucleiSky audit screenshots (44 PNGs remain locally); nothing else.

## Not run
Windows and macOS installers; native file choosers; Cellpose and InstanSeg (model downloads, GPU); the other CellTracksColab notebooks; QuPath synthetic for NucleiSky; Cancel during a long run; a second jar pass for apps other than NucleiSky.
