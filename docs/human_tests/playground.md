# Human tests: Playground (Napari, Fiji, QuPath)

Part of the [human test protocol](../HUMAN_TEST_PROTOCOL.md): fill in its record sheet first, install the Playground (release 0.0.4, decided) and the host(s) as it says.
The Playground is a **test application**: it answers "is this computer, this installation and its GPU in order?" and carries one small tool per bridge feature, so the same
steps show what each host does. **Discovery:** listed in Napari, Fiji and QuPath. Registered name `LabConstrictorPlayground` (this is the name in the command line); 17 tools
(the app's `lc_tools` module declares them; the test cases of the app are in `lc_tests/cases.json`). Expected values below come from the app's README and those cases; where a
host's behaviour is not in a document it says "not verified".

Run every test in **each host you were asked to test**; the *Do* is the same, the *Expect* says what differs. Write the host in the Notes.

## PG-0. Test data
Two sources. (a) The tool **Make test data** (folder: a new empty folder `<TESTDATA>`; kind `all`; size 64). Terminal:
`<APP_PY> -m labconstrictor_tools run LabConstrictorPlayground make_test_data folder=<TESTDATA> kind=all size=64`.
(b) The app's own fixtures: download the source archive of the Playground release in the record sheet,
`https://github.com/CellMigrationLab/LabConstrictor-Playground/archive/refs/tags/<PG_TAG>.zip`, unzip it and use the folder `lc_tests/fixtures/data` (called `<FIXTURES>` below; whether
every release tag carries it: not verified, it exists on `main`).

**Expect:** (a) `<TESTDATA>` holds `three_channels.tif` (a 3-channel image whose channels have the means 10, 20 and 30), `rgb.tif`, `labels.tif`, `timelapse.tif` and `points.csv`.
(b) `<FIXTURES>` holds `demo_blobs.tif` (16 round blobs), `square_a.tif` and `square_b.tif` (a 4 x 4 square of 255 in a 32 x 32 image), `top_half_region.tif`, `empty_region.tif`, `wrong_size_region.tif`, `settings.json`, `notes.txt`, `measurements.csv`.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

## PG-1. Check everything (the readout testers send us)
**Do:** run **Check everything** (no inputs needed; the internet check is optional). Terminal: `<APP_PY> -m labconstrictor_tools run LabConstrictorPlayground check_everything`.
**Expect:** a short readout with a mark per layer (machine: memory, disk, write access, path problems; worker; GPU tools; PyTorch; a speed test; what the installer decided about the GPU build) and a table of details and the report file (`report.json`): ✔ fine, ⚠ works but something will bite later (low disk, a long path on Windows, the GPU build fell back to CPU), ✖ broken with a line that says what to do. Takes about a minute. A ⚠ for "GPU build fell back to CPU" on a computer without an NVIDIA GPU is normal (the README: CPU build; Apple silicon uses Metal "mps"). **Attach the readout and `report.json` to your report.**

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes (any ⚠ or ✖ and its text): ______________________________

## PG-2. Feature tour with the demo image, and Replace
**Do:** run **Feature tour** with no image (leave the image input unset). Change the threshold and run again.
**Expect:** a message that mentions 16 blobs; labels, outlines (16), points (16, columns y, x, label), a measurements table (16 rows). The second run **updates** the earlier results instead of adding new ones: Napari: the same layers/dock updated; Fiji: the previous window, overlay and ROIs are closed and replaced; QuPath: the results window is reused and the point annotation replaced.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes (host): ______________________________

## PG-3. Feature tour on a chosen image, selection, look-for
**Do:** open `<FIXTURES>/demo_blobs.tif`. Run **Feature tour** on it; then with "use the selection" ticked and a rectangle covering the top half (Napari: a Shapes layer with one rectangle selected; Fiji: a rectangle ROI; QuPath: a selected annotation); then *Look for* = `dark`.
**Expect:** all 16 blobs; with the top-half selection about 11 (the app's case with its prepared `top_half_region.tif` gives 11; a rectangle you draw by hand may differ by one: write the number); `dark` finds 3. The result points/outlines sit on the right blobs (zoom and check). QuPath: results appear on the open image only when it is the image the run used; otherwise a table and the line "Not placed on an image (...)".

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes (counts you saw): ______________________________

## PG-4. A tool with nothing to find is a notice, a bad region is an error
**Do:** run **Feature tour** with threshold 1.0 and minimum size 500 px (no image). Then use "use the selection" with an empty/zero-size selection if the host lets you.
**Expect:** the first shows a notice `No blob found ...` (a message, not a red error); the second an error that says the region is empty.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

## PG-5. Channels
**Do:** open `three_channels.tif` from PG-0 (a). Run **Feature tour** choosing channel 3 (Napari: the channel chooser; Fiji: a channel number; QuPath: channel names).
**Expect:** the tool works on channel 3 only (a tool that receives the wrong channel would give a different count or intensity; the summary states the channel: not verified how it is worded).

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

## PG-6. A dependent drop-down
**Do:** open **Run a small test on a device**. Look at the *device* drop-down; run **List the devices**; run the test on `cpu`.
**Expect:** the drop-down lists the devices of **List the devices** (`cpu`, plus `cuda:0` or `mps` where PyTorch finds one). Fiji: a text field the first time and a drop-down from the previous run's values afterwards. The test runs on the chosen device.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

## PG-7. Parameters that another switches on (EnabledWhen)
**Do:** open **Count the pixels above a level** on `<FIXTURES>/square_a.tif`. Mode `fixed`, level 100: run. Mode `percentile`, percentile 99: run.
**Expect:** pixels 16 both times (`level_used` 100, then 255). Napari and QuPath **grey out** the parameter that does not apply to the mode; **Fiji shows both** (known limit) and the tool accepts both: a level typed in percentile mode is ignored.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes (host): ______________________________

## PG-8. Pixel size from the image, and never a guess
**Do:** open `<FIXTURES>/square_a.tif` (uncalibrated) and run **Area of the bright region** with the pixel size empty. Then give the image a calibration (Napari: layer scale 0.5 with unit um; Fiji: `Image > Properties...` unit `um`, pixel width 0.5; QuPath: the image's pixel size in the image properties) and run again. Then type 0.25 yourself and run.
**Expect:** the first is **refused** with a message about the pixel size (code `pixel_size_unknown` on the command line); never an area made with a guessed size. The second: the field is prefilled from the calibration and the area is **4 um2** (16 bright pixels of 0.5 um). The typed 0.25 gives 1 um2.
**Napari:** a bare scale with pixel units is *not* a calibration (blank, run blocked). **Fiji (limit):** typing 0.5 when the box already shows 0.5 clears the field and blocks the run (no "use the image's calibration" button; undetectable typing, conformance case CAL-T9): record it; type another value or reselect the image.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes (host): ______________________________

## PG-9. Two images and a transform
**Do:** run **Align the centres of two images** with *image* = `square_a.tif` and *reference* = `square_b.tif` (both in `<FIXTURES>`; the 4 x 4 squares are at rows 4-7, columns 8-11 and rows 14-17, columns 20-23).
**Expect:** a translation of 10 rows and 12 columns (y 4-7 to 14-17, x 8-11 to 20-23: the transform has 10 and 12 in its last column; derived from the fixture layout, not verified by a run) as a 3x3 matrix; the host shows the moved image over the reference (Napari: an overlay layer; Fiji: an overlay window; QuPath: the matrix is shown, nothing is drawn). 

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

## PG-10. Text and table inputs
**Do:** run **Look inside a file** on `<FIXTURES>/settings.json` and `notes.txt` and **Summarise a table** on a CSV (`<FIXTURES>/measurements.csv`).
**Expect:** the keys and plain values of the JSON (the number of lines of the text file; a file over 1 MB is refused); for the CSV the count, mean, minimum and maximum of each numeric column as a table plus the rows and columns. Results: Napari table dock; Fiji Results table; QuPath table in the results window.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

## PG-11. Stress tools: the host must survive each and say what happened
**Do (one at a time; after each, run **List the devices** to see that the host works):**
1. **Stress: slow run with progress**, 30 s: press **Cancel** (Napari, QuPath) or **Esc** (Fiji) after a few seconds.
2. **Stress: crash the worker.**
3. **Stress: out of memory (simulated).**
4. **Stress: a tool that ignores Cancel** (60 s): press Cancel.
5. **Stress: big image** and **many points** (optional).
**Expect:** 1: the run stops within seconds and says cancelled; the progress bar moved before. 2: the host says the worker ended unexpectedly (the app's case status is CRASHED) with a likely cause, and the next run works. 3: a labelled `MemoryError` message (the same on every system; nothing real is allocated). 4: after Cancel the worker is killed after about 3 s and the status says `cancelled (worker stopped)` (Napari wording; Fiji/QuPath: not verified). 5: results shown or a stated limit (Napari: a table dock shows at most 100 000 rows, more points are reported, not drawn). Do **not** use the "Real memory pressure" tool unless you accept that a child process uses up to 512 MB.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes (host, each of 1 to 5): ______________________________

## PG-12. Message and copy as command
**Do:** after any run copy the command (Napari: the *Copy as command* button; Fiji: the Log after each run, or the menu entry "Copy last run as command"; QuPath: the menu button). Paste it into a terminal (for Python: `client.run_once(...)`) and run it.
**Expect:** the same values as the form run (parameters you set; unset optional ones left out). On Windows cmd.exe the line follows the C runtime quoting rules; PowerShell reads quotes by other rules: use the Python snippet there.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________
