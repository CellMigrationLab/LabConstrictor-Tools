# Human tests: VLab4Mic (Napari and Fiji; not QuPath)

Part of the [human test protocol](../HUMAN_TEST_PROTOCOL.md): fill in its record sheet first, install VLab4Mic (release 0.1.6, decided) and the host(s) as it says.
VLab4Mic simulates fluorescence microscopy images of a virtual sample (a structure, a labelling probe, an imaging modality). **Discovery:** listed in **Napari and Fiji**, **not in QuPath**.
Registered name `VLab4Mic`; tools: **Simulate imaging of a virtual sample** (id `simulate_sample`) and **Compare an image with a reference** (id `compare_images`). It needs internet on the first run with a structure (the structure is downloaded) and about 5 minutes for a full run of the app's own cases (not verified by the authors: only the declaration tests were run). Expected numbers come from the app's `lc_tests/cases.json`.

## VL-0. Command line, the reference values
**Do:** `<APP_PY> -m labconstrictor_tools run VLab4Mic simulate_sample modality=STED random_seed=1`
**Expect:** `COMPLETE`; `modality` STED, `pixel_size_nm` 15, `image_size_px` `66 x 66`, one particle requested and placed; a `simulated` and a `noiseless` image of 66 x 66. With `modality=Widefield` the image is only 10 x 10 pixels (100 nm pixels, 1000 nm field: raise *Sample size XY*, e.g. `sample_size_xy_nm=2000` gives 20 x 20). With `probe=NPC_Nup96_Cterminal_direct` and the default structure: refused (`probe_structure_mismatch`, the message names `7R5K`: that probe belongs to structure 7R5K).

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

## Napari

### VL-N1. Listed, the form, the scroll
**Do:** `Plugins > LabConstrictor tools`, app `VLab4Mic`, tool `Simulate imaging of a virtual sample`. Tick **Show advanced settings** and scroll to the bottom.
**Expect:** the form is the notebook's (structure, labelling, imaging); the advanced settings are behind the box; the **form scrolls** and Run, status and messages stay in view below it.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

### VL-N2. A first simulation, and replace
**Do:** modality STED (random seed 1 if there is a field for it), Run. The first run downloads the structure (up to about a minute); later runs of the same structure take 10 to 60 s. Then change a setting and Run again.
**Expect:** two layers `VLab4Mic:simulated` and `VLab4Mic:noiseless` (66 x 66 for STED with the defaults) and a line under the form naming the result and the pixel size (15 nm). **Every new run replaces the two layers** (no pile). Rename a layer (e.g. `keep1`) and Run again: the renamed layer is **never** replaced and two new layers appear.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

### VL-N3. Compare an image with a reference
**Do:** run **Compare an image with a reference** with the simulated layer as *simulated*, a reference image, and the pixel sizes (the app does not read them from a layer: type the one reported by the simulation, e.g. 0.015 um for STED).
**Expect:** two numbers, `ssim` and `pearson`. The same image against itself gives 1.0 and 1.0; an unrelated image about 0; a constant image is refused (`flat_image`, "same value everywhere"); a stack is refused (`wrong_dimensions`, "2D"); a pixel size of 0 is refused (`invalid_pixel_size`, "greater than 0"). SSIM is high for sparse images even when they do not match: read it with Pearson.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

### VL-N4. Cancel and an error
**Do:** start an SMLM simulation (slow; stopping takes effect between its stages) and Cancel; then choose a probe that does not fit the structure.
**Expect:** the run stops and Run is usable again; the mismatch shows `✖ [probe_structure_mismatch] ...` naming `7R5K`, with Details available.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

## Fiji

### VL-F1. Listed, run, replace
**Do:** `Plugins > LabConstrictor > LabConstrictor Tools...`, `VLab4Mic`, `Simulate imaging of a virtual sample`, STED, OK; then change a setting and OK again.
**Expect:** the dialog has the same settings, grouped as in the notebook (advanced ones under headings; Fiji cannot fold a group: known limit). The simulated image opens in its own window and the settings summary is in the Log; the next run **replaces** the window; a window you renamed is kept.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

### VL-F2. Compare, with the pixel-size limit
**Do:** run **Compare an image with a reference** on two open images.
**Expect:** `ssim` and `pearson` in the Log. The pixel-size fields follow the images' calibration; with an uncalibrated image they are cleared and the run is refused until you type a value; typing exactly the value a box shows clears it (Fiji limit CAL-T9, see F0 of the protocol).

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

## QuPath: absence

### VL-Q1. VLab4Mic is not offered in QuPath
This is test D2 of the protocol: with VLab4Mic installed, `Extensions > LabConstrictor tools...` does **not** list it (press **Rescan apps**); the other apps are unaffected. Record the result here too.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________
