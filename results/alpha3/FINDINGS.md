# Alpha.3 findings (hosts Napari, Fiji, QuPath v0.1.0-alpha.3; apps Guess the Condition 0.0.1, Playground 0.0.5, VLab4Mic 0.1.6)

Written by the parent from the report of the re-verification agent (the agent could not write this file). Counts and the alpha.2 comparison are in RESULTS.md next to it.

## Fixed in alpha.3 (re-verified with real clicks and inputs on Linux)
* **FJ-1b (Fiji host): Cancel on a tool form with an empty required input.** Script mode: all 6 Guess the Condition tools and Playground `make_test_data` pass (cancelled, nothing ran, no run record, status `LabConstrictor: cancelled`). Jar mode: passes; one `prepare_game` Cancel did not close its dialog within 5 s once and passed on rerun (not reproduced; 17 other Cancel clicks passed). A required image with no image open still refuses with `missing_parameter`.
* **H-N4 (Napari host): stale-control AttributeError.** 17 Playground tools x 10 rounds (340 switches): 0 exceptions (alpha.2: 2).
* **RGB Channel chooser (Napari host):** lists Red/Green/Blue after the layer is picked and keeps them.
* **Group headings (Napari host):** fine for all 11 grouped tools, also after switching away and back.
* **Typed 0 (Napari host):** shows "0 means: use the image's calibration" and the box refills.
* **VL-7 (Napari host):** a micrometre calibration written by Fiji fills the pixel-size box with 0.02 (evidence file and `vm_cal_micro`).

## Still failing or open
* **N-1 (Napari host, isolated): stray top-level QRadioButton windows.** Repro without the audit: show the Playground "Count the pixels above a level" form (radio `mode`), then repeat "insert N images, clear": strays after N=1/3/3/3/6 are 0/4/8/12/22; `gc.collect()` changes nothing; they are parentless 'fixed' and 'percentile' duplicates. Probable cause (read, not proven): `_refresh_layer_choices` calls `reset_choices()` on every widget on each layer event and the radio widget rebuilds its buttons without freeing the old ones. Files: `alpha3/LabConstrictorPlayground/n1_repro2_*`.
* **N-2 (Napari host): partly fixed.** A typed 0 no longer changes silently, but still cannot reach the tool's own `invalid_pixel_size` refusal (an uncalibrated image ends `pixel_size_unknown`). Design decision CAL-T4 kept by the owner.
* Minor: the status line keeps a stale "0 means ..." sentence after the next file is chosen; inserting an RGB layer does not select it in the layer chooser.
* **VL-5 (VLab4Mic app bug):** `compare_images` accepts a flat or all-zero reference (`vm_flat_reference`, `vm_zero_reference`). VL-6 (SSIM 0.7787 for unrelated sparse images) is a truth question, dropped from the generator by owner decision. VL-3, VL-4, VL-12, VL-13 not re-run.
* Playground: no app bug. Its synthetic FAIL rows are truth/tolerance rows (`pg_ramp_f32_p90`, `pg_make_three_channels`) and `pg_pixel_zero` (N-2).

## Environment
* **E-1 Playground installer on Linux:** with `PIP_EXTRA_INDEX_URL=https://download.pytorch.org/whl/cpu` the stock 0.0.5 installer picks torch 2.8.0+cpu, finishes with exit 0 in 98 s and uses about 2 GB; without it, a machine with about 6 GB free fills up with CUDA wheels (exit 1). Worth telling users without a GPU (in TESTER_START_HERE.md).
* Never run two audits at once against the same `LC_HOME` ("N run record(s) were created" false failures); CPU load makes the Fiji form layout late (21 false FAILs on VLab4Mic `simulate_sample` when a synthetic run was concurrent; clean rerun 90 PASS).
* VLab4Mic installer 6 m 37 s (alpha.2: 62 s), network speed.

## Not run
Windows and macOS installers; native file choosers (HUMAN rows); Cancel during a long run for apps without a cancel case; Playground multi-channel form in QuPath (1 NOT_RUN); Cancel on SciJava's native file prompt; a negative control of the new FJ-1b rows against the alpha.2 script; jar-mode audits of Playground and VLab4Mic beyond the FJ-1b rows; not asked this round: VLab4Mic in QuPath, the notebook family, CellTracksColab, the multi-app family.

## Driver changes (branches pushed, no PRs)
`claude/ui-audit-fiji` 0f926ea (zero-parameter tools pass; `ui_fiji_fj1b_*` rows), `claude/ui-audit-qupath` 867aee5 (stress tools without a case are HUMAN), `claude/ui-audit-napari` daeb412 (status wording, typed-0 replay is HUMAN, channel chooser for stack/RGB, `data_dir.txt`, `_cli` datasets are NOTE), `claude/test-strategy` 4952c54 (local only in the agent's worktree; collect_results keeps alphaN folders apart).
