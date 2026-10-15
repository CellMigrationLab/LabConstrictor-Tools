# Alpha.2 rerun of the one-off round (released v0.1.0-alpha.2 hosts, 15 Oct 2026)

Hosts (verified by checksum): Napari `napari-labconstrictor` from tag v0.1.0-alpha.2 (napari 0.9.2 PyQt6, labconstrictor-tools 0.3.0a1) in /home/user/w/venv; Fiji script zip (sha256 a0e00252...; the loose script is byte-identical to the tag) and jar (13bdbf16...); QuPath jar 7806fb2b... + LabConstrictorTools-all.groovy. Apps: Linux x86_64 installers of the latest releases: GuessTheCondition 0.0.1, CellTracksColab 1.1.2, VLab4Mic 0.1.6 and (added by the coordinator) Playground 0.0.5. Every app was installed, tested and uninstalled (uninstall.sh exit 0, prefix and registry entry gone; GuessTheCondition stayed until the two-app session with VLab4Mic had run). The alpha.1 results were not touched; this is results/alpha2/. Generated tables of every matrix: MATRICES.md. Findings with classes and evidence: FINDINGS.md.

Tooling used: Tools main 477923d (release_sandbox with #138/#139) + the oneoff runners (worktree /home/user/wt_a2, not committed), notebook runner branch claude/oneoff-notebooks (pushed, 4 commits: VL-1, VL-2 and three more runner fixes), audit drivers claude/ui-audit-napari (pushed dc3662d: VL-10 fixed, new ui_synthetic_napari.py) and claude/ui-audit-fiji (pushed: VL-11 fixed). The QuPath driver was used unchanged.

## Counts per app / family / host (alpha.2 | alpha.1 where the same row existed)

| app | family | host | alpha.2 PASS | FAIL | NOT_RUN | HUMAN | NOTE | alpha.1 PASS | FAIL | NOT_RUN | HUMAN |
|---|---|---|---|---|---|---|---|---|---|---|---|
| CellTracksColab | install | cli | 2 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | n/a |
| CellTracksColab | nb | notebook | 197 | 2 | 0 | 23 | 29 | 197 | 2 | 0 | 23 |
| CellTracksColab | sandbox | cli | 33 | 0 | 0 | 0 | 1 | 31 | 0 | 0 | 0 |
| CellTracksColab | synthetic | cli | 51 | 2 | 0 | 0 | 0 | n/a | n/a | n/a | n/a |
| CellTracksColab | ui | fiji | 1 | 0 | 0 | 1 | 0 | n/a | n/a | n/a | n/a |
| CellTracksColab | ui | napari | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 |
| CellTracksColab | ui | qupath | 1 | 0 | 0 | 0 | 1 | n/a | n/a | n/a | n/a |
| GuessTheCondition | install | cli | 2 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | n/a |
| GuessTheCondition | nb | notebook | 46 | 0 | 0 | 0 | 11 | 46 | 0 | 0 | 0 |
| GuessTheCondition | sandbox | cli | 46 | 0 | 0 | 0 | 2 | 46 | 0 | 0 | 0 |
| GuessTheCondition | synthetic | cli | 146 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | n/a |
| GuessTheCondition | synthetic | napari | 142 | 0 | 0 | 0 | 4 | n/a | n/a | n/a | n/a |
| GuessTheCondition | ui | fiji | 64 | 1 | 0 | 9 | 0 | n/a | n/a | n/a | n/a |
| GuessTheCondition | ui | napari | 40 | 0 | 0 | 1 | 0 | 36 | 1 | 0 | 1 |
| GuessTheCondition | ui | qupath | 37 | 0 | 0 | 7 | 0 | 36 | 1 | 0 | 7 |
| LabConstrictorPlayground | install | cli | 1 | 1 | 0 | 0 | 0 | n/a | n/a | n/a | n/a |
| LabConstrictorPlayground | nb | notebook | 45 | 0 | 0 | 0 | 10 | n/a | n/a | n/a | n/a |
| LabConstrictorPlayground | sandbox | cli | 54 | 1 | 0 | 0 | 3 | n/a | n/a | n/a | n/a |
| LabConstrictorPlayground | synthetic | cli | 163 | 2 | 0 | 2 | 0 | n/a | n/a | n/a | n/a |
| LabConstrictorPlayground | synthetic | napari | 163 | 10 | 0 | 0 | 4 | n/a | n/a | n/a | n/a |
| LabConstrictorPlayground | ui | fiji | 115 | 3 | 0 | 18 | 0 | n/a | n/a | n/a | n/a |
| LabConstrictorPlayground | ui | napari | 60 | 8 | 0 | 14 | 0 | n/a | n/a | n/a | n/a |
| LabConstrictorPlayground | ui | qupath | 67 | 0 | 11 | 12 | 0 | n/a | n/a | n/a | n/a |
| VLab4Mic | install | cli | 2 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 |
| VLab4Mic | nb | notebook | 43 | 0 | 0 | 2 | 14 | 43 | 0 | 0 | 2 |
| VLab4Mic | sandbox | cli | 54 | 0 | 0 | 0 | 1 | 52 | 0 | 0 | 0 |
| VLab4Mic | synthetic | cli | 83 | 3 | 0 | 4 | 0 | 83 | 3 | 0 | 1 |
| VLab4Mic | synthetic | napari | 78 | 5 | 0 | 1 | 9 | 5 | 1 | 0 | 1 |
| VLab4Mic | ui | fiji | 90 | 0 | 0 | 3 | 0 | 63 | 27 | 0 | 3 |
| VLab4Mic | ui | napari | 24 | 0 | 0 | 3 | 0 | 15 | 6 | 0 | 1 |
| VLab4Mic | ui | qupath | 1 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 |
| all | multi | cli | 11 | 0 | 0 | 0 | 0 | 11 | 0 | 0 | 0 |


How to read it: where an app has two matrices for one host (the single-app audit and the two-app session) the table shows the one with more rows, so GuessTheCondition `ui napari` (40 PASS) is the two-app session; the single-app audit is 37 PASS, 1 HUMAN. The alpha.1 columns for VLab4Mic `ui napari` and `ui fiji` held driver artifacts (VL-10, VL-11), now fixed, so those rows are not like for like. `synthetic napari` is new for every app: every case of the synthetic cases.json through the real form and Run click, then check_ground_truth.py --with-host (the alpha.1 VLab4Mic number was a calibration-box probe only). Playground's alpha.1 rows were not part of that round (n/a).

## What was fixed since alpha.1 (re-verified with a real click or the real worker)

| alpha.1 finding | alpha.2 | evidence |
|---|---|---|
| H-N1 Napari Run stays enabled while running | FIXED | `ui_napari_panel_run PASS: clicked ... started, disabled while running, enabled after (COMPLETE)` on GuessTheCondition and VLab4Mic (Qt mouse click on the real button). Whole Napari audit of GuessTheCondition: 37 PASS, 1 HUMAN, 0 FAIL (alpha.1: 36 PASS, 1 FAIL) |
| Q-1 QuPath Run button does nothing | FIXED | `ui_qupath_panel_run PASS: a real click started a run (Run off, Cancel on, then back)` (JavaFX Robot); GuessTheCondition QuPath audit 37 PASS, 7 HUMAN, 0 FAIL (alpha.1: 36 PASS, 1 FAIL); Q-4 (`panel_keep_worker`) also PASS; Playground (17 tools) 67 PASS, 0 FAIL |
| FJ-1 Fiji Cancel runs the tool | PARTLY FIXED (see FJ-1b in FINDINGS) | Cancel on the tool chooser: `ui_fiji_panel_chooser_cancel PASS: ... cancelled, no run, no worker, no run record` (script and jar). Cancel on a FORM that has an empty required input still runs the tool and writes a FAILED record: `ui_fiji_panel_form_cancel FAIL` on GuessTheCondition (script and jar, real Robot click) |
| Fiji macro replay refuses omitted required values (#29) | FIXED | Fiji case `macro_omitted_required_scalar_is_refused` PASS in real Fiji on the released script (error `[missing_parameter] 'Free' is required`); results/alpha2/hosts_fiji_cases/run_cases.out (macro call, no click involved) |
| Affine cross-check hides the overlay (#31) | FIXED | case `affine_with_an_unrelated_image_still_shows_the_overlay` PASS (overlay window opened, log says why the comparison was skipped) |
| Playground NaN images (A-PG1, A-PG2) | FIXED in 0.0.5 | count_above_level, bright_area and align_centres on lc_tests/fixtures/data/square_nan.tif all end FAILED with code `non_finite_pixels` (results/alpha2/Playground/nan_check/); synthetic pg_nan_float, pg_nan_count, pg_area_nan, pg_align_nan PASS |
| Playground make_test_data docstring (A-PG3) | FIXED (doc) | docstring now says the first channel is 10 plus the nuclei (depends on size), the others flat at 20 and 30; a real run gives means [24.5, 20, 30] at size 256. The synthetic case still expects [10, 20, 30] (truth outdated, see FINDINGS) |
| VL-1, VL-2 runner bugs | FIXED in the runner | VLab4Mic notebooks 43 PASS, 0 FAIL, 2 HUMAN with the committed scripts (no symlink, no patched copy) |
| VL-10, VL-11 driver artifacts | FIXED in the drivers | VLab4Mic Napari audit 21 PASS, 3 HUMAN, 0 FAIL; Fiji audit 90 PASS, 3 HUMAN, 0 FAIL (simulate_sample controls: 62 of 62 activated) |

## Still failing / unchanged since alpha.1
* FJ-1b (Fiji form Cancel with an empty required input), H-N4 (Napari stale ChoicesFrom/EnabledWhen callbacks, now reproduced by hand on Playground), VL-7 (Napari does not read a micrometre unit written by Fiji), VL-3, VL-4, VL-5, VL-6, VL-12 (VLab4Mic app), A-CT1, A-CT2, A-CT3 (CellTracksColab): see FINDINGS.md.

## Per-app sections

### GuessTheCondition 0.0.1
Install 53 s, exit 0, hosts notebook, napari, fiji, qupath. Sandbox 46 PASS, 0 FAIL, 0 NOT_RUN (alpha.1 after #138: same). Notebooks 46 PASS, 0 FAIL, 11 NOTE. Napari audit 37 PASS, 1 HUMAN (cancel while running: no cancel case). Fiji audit (script) 64 PASS, 9 HUMAN, 1 FAIL (FJ-1b); jar mode (create_demo_experiment, prepare_game) 32 PASS, 3 HUMAN, same 1 FAIL; the loose script was restored afterwards (diff identical to the alpha.2 script). QuPath 37 PASS, 7 HUMAN (native file choosers, progress_events_min). Synthetic: CLI 146 PASS, 0 FAIL (35 datasets); Napari 142 PASS, 4 NOTE (two datasets refused by the form itself with the tool's sentence (images per repeat 0 and 51), two percentages the bounded field cannot hold: refusal happens before the tool; not green, not red).

### CellTracksColab 1.1.2 (hidden from every host)
Install 73 s, exit 0, hosts notebook only. Sandbox 33 PASS, 0 FAIL. Notebooks (8) 197 PASS, 2 FAIL, 23 HUMAN, 29 NOTE: the same two FAIL rows as alpha.1, both the Custom notebook NameError (A-CT3). Hidden checks, in a registry that also holds GuessTheCondition (so a wrongly listed app would show): Napari `CellTracksColab is not in the app chooser ['GuessTheCondition']`, Fiji `not in the chooser (Fiji lists: GuessTheCondition)`, QuPath `absent from the app chooser (it offers [GuessTheCondition])`: all PASS. Multi family (two apps in one private registry: lists, hosts, doctor, run, unregister keeps the other): 11 PASS. Synthetic CLI on the INSTALLED app: 51 PASS, 2 FAIL (A-CT1 infinite coordinate COMPLETE; A-CT2 Max Speed 1e10): confirms both on the installed app. Napari synthetic: not possible (hidden by design).

### VLab4Mic 0.1.6
Install 62 s, exit 0, hosts notebook, napari, fiji. Sandbox 54 PASS. Notebooks 43 PASS, 0 FAIL, 2 HUMAN with the committed (fixed) scripts. Napari audit 21 PASS, 3 HUMAN; Fiji audit 90 PASS, 3 HUMAN; QuPath hidden: PASS with GuessTheCondition as the listed neighbour. Two apps in one registry (GuessTheCondition + VLab4Mic): Napari `multi_lists` x2 and `multi_switch` PASS and both apps audited with 0 FAIL; Fiji `multi_lists` x2 and `multi_switch` PASS (parts limited to the panel, the other panel rows of that matrix are not-run artifacts of the restriction). Synthetic CLI 83 PASS, 3 FAIL, 4 HUMAN (same as alpha.1: VL-5 x2, VL-6); Napari (calibration read from the file by the host) 78 PASS, 5 FAIL, 1 HUMAN, 9 NOTE: VL-5 x2, VL-6, VL-7 (`vm_cal_micro` box stays empty), `vm_pixel_zero` (see FINDINGS N-2).

### Playground 0.0.5 (registry name LabConstrictorPlayground)
Installer exit 1 (environment: disk, see FINDINGS E-1); completed by hand. Sandbox 54 PASS, 1 FAIL (only `1_installer_succeeds`), 3 NOTE. Notebooks 45 PASS, 0 FAIL. Napari audit 60 PASS, 8 FAIL, 14 HUMAN (H-N4 and runner artifacts, FINDINGS). Fiji audit 115 PASS, 3 FAIL, 18 HUMAN (the 3 FAIL are zero-parameter tools: driver artifact). QuPath 67 PASS, 12 HUMAN, 11 NOT_RUN (stress tools, driver does not mark them HUMAN), 0 FAIL. Synthetic CLI 163 PASS, 2 FAIL, 2 HUMAN (float32 tolerance and outdated truth, not app bugs); Napari 163 PASS, 10 FAIL (all classified in FINDINGS).

## What could not be run
Windows and macOS installers; native file choosers (HUMAN); Cancel during a long run in the hosts for apps without a cancel case (Playground's stress_slow cancel case ran in Napari: PASS); Playground's NucleiSky sibling and Playground 0.0.5 on QuPath form 'channel' (no multi-channel fixture in that audit app); Napari synthetic for CellTracksColab (hidden).
