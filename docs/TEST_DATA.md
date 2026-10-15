# Test data for the alpha.3 human-testing round

This page is for people testing LabConstrictor on **their own Windows, Apple-silicon macOS, or Linux computer**. Start with [TESTER_START_HERE.md](TESTER_START_HERE.md), then record results in the [OS checklist](TEST_MATRIX.md). **You do not need to prepare all these datasets before starting.** Most first-use tests use the apps' built-in examples.

**Simple rule:** only use synthetic, public, or explicitly shareable data in GitHub reports. Never attach confidential microscopy images, patient images, private paths, or an unreviewed support bundle.

## Which data do I need?

| Data ID | App and test | What you need | Where it comes from | Ready for a volunteer? |
|---|---|---|---|---|
| **P0** | Playground: **Check everything**, **Feature tour** (`PG-1/2`) | Nothing: Feature tour generates the **16-blob** demo image itself; use no input image | Built into **Playground 0.0.5** | **Yes — no download** |
| **G0** | Guess the Condition: create demo, prepare, guess, analyse (`GC-1–7`) | Two new empty writable folders, one for experiment and one for results; the app creates **12 TIFF images** across 2 conditions and 3 repeats | **Create a demo experiment** in Guess the Condition 0.0.1 | **Yes — no data download** |
| **V0** | VLab4Mic: simulate an image (`VL-N2/VL-F1`) | No input TIFF; use the default simulation, e.g. STED. First run with a remote structure may need internet access | Built into **VLab4Mic 0.1.6** | **Yes, with internet if structure must download** |
| **P1** | Playground: calibrated TIFF, channels, ROIs, CSV, images (`PG-3, PG-5, PG-7–10`) | Small synthetic TIFFs plus `settings.json`, `notes.txt` and `measurements.csv` | [Playground 0.0.5 source ZIP](https://github.com/CellMigrationLab/LabConstrictor-Playground/archive/refs/tags/0.0.5.zip), directory `lc_tests/fixtures/data/` | **Yes — download and unzip** |
| **N1** | NucleiSky: scientifically check alignment (`NS-0, NS-N3–N6/NS-F2–F4/NS-Q2`) | Synthetic `reference.tif` (1600×1600), `query.tif` (520×520), optional masks, `ground_truth.json`; pixel sizes **0.65 µm / 0.325 µm** | [Tagged fixture generator](https://raw.githubusercontent.com/CellMigrationLab/NucleiSky/0.1.4/lc_tests/make_fixtures.py); preparation below | **Yes, but requires one-time generation** |
| **V1** | VLab4Mic: image comparison (`VL-N3/VL-F2`) | `reference_20nm.tif`, `same_field_40nm.tif`, `flat_20nm.tif`, `stack.tif`, `mini_ring.cif` | [Tagged fixture generator](https://raw.githubusercontent.com/CellMigrationLab/LabConstrictor-VLab4Mic/0.1.6/lc_tests/make_fixtures.py); preparation below | **Yes, but requires one-time generation** |
| **C1** | CellTracksColab **bridge**: registered tool calculation (optional; `CT-2`) | Small CSV with two known trajectories: `tracks.csv` and optionally `tracks_2d.csv` | [tracks.csv](https://raw.githubusercontent.com/CellMigrationLab/CellTracksColab/1.1.2/lc_tests/fixtures/tracks.csv), [tracks_2d.csv](https://raw.githubusercontent.com/CellMigrationLab/CellTracksColab/1.1.2/lc_tests/fixtures/tracks_2d.csv) | **Yes — direct download** |
| **C2** | CellTracksColab **TrackMate notebook** (`NB3`) | A complete, documented **TrackMate CSV/XML export and expected import results**, not merely the tiny `C1` bridge CSV | **No validated human-test dataset has been identified in release 1.1.2** | **Not yet**: use your own non-sensitive export, or report **BLOCKED (missing dataset)** |
| **R1** | Real-world usability, optional | An image/ROI/channel workflow you actually use; known calibration and expected orientation/output | Your own **non-sensitive or locally retained** files | **Optional — never upload confidential data** |

**Important:** the C1 bridge fixture is a *spot table to test the tool*. It must **not** be presented as a proven TrackMate notebook import example. CellTracksColab 1.1.2 declares `hosts: [notebook]`: **Calculate Track Metrics** is registered but intentionally **does not appear** in Napari, Fiji or QuPath. The basic CT-2/CT-3 discovery checks need **no CSV**.

## Five-minute start: no downloaded test data

1. Install **Playground 0.0.5** from [the tester start page](TESTER_START_HERE.md#direct-downloads-click-no-searching-on-the-release-page), open one host, choose **Feature tour**, leave its image input empty and press Run. Expect 16 demo blobs, labels and a table. Press Run again: the earlier results should be replaced rather than duplicated.
2. In Playground run **Check everything** and read the device/system report. A GPU warning on a CPU-only machine is not automatically a failure.
3. Install **Guess the Condition 0.0.1**; create two empty folders first. **Create a demo experiment** generates the 12 TIFF images. Use that generated folder to **Prepare the game**, make a guess, and inspect the saved output.
4. Install **VLab4Mic 0.1.6** if you can. Simulate an image and check it displays properly. A structure download on the first run is expected; record network/proxy problems.
5. Install **CellTracksColab 1.1.2**. You can check that its JupyterLab window opens and the bridge is registered but absent from all image-host menus **without obtaining a TrackMate dataset**.

The [OS checklists](TEST_MATRIX.md) explicitly distinguish these first-use tests from the data-dependent ones.

## Data P1: Playground source fixtures

1. Click [download Playground 0.0.5 source ZIP](https://github.com/CellMigrationLab/LabConstrictor-Playground/archive/refs/tags/0.0.5.zip) and extract it.
2. Open `LabConstrictor-Playground-0.0.5/lc_tests/fixtures/data/` (the first folder name may include a GitHub-generated prefix).
3. Use the files **from this tagged release**, not a newer `main` branch: `demo_blobs.tif`, `square_a.tif`, `square_b.tif`, `three_channels.tif`, `top_half_region.tif`, `measurements.csv` and the other small fixtures.
4. For calibration tests, open `square_a.tif` (uncalibrated) and then set **0.5 µm/pixel** through the host's image calibration control. The 16 bright pixels should correspond to **4 µm²**; explicit 0.25 µm/pixel gives **1 µm²**. See [PG-8](human_tests/playground.md#pg-8-pixel-size-from-the-image-and-never-a-guess).

You may also use Playground's **Make test data** tool to generate `three_channels.tif`, `rgb.tif`, `labels.tif`, `timelapse.tif` and `points.csv` in an empty folder. However, this does **not** replace the tagged `square_a.tif` and `square_b.tif` reference fixtures for numerical checks.

## Data N1: NucleiSky matching fixtures

A human must first generate a reference image and a matching query from NucleiSky's **tagged** fixture generator. Run the next commands only once in a fresh work folder, **after NucleiSky has been installed**.

**Windows PowerShell** (replace the Python path with your actual NucleiSky install path):

```powershell
mkdir $HOME\LabConstrictor-test-data
cd $HOME\LabConstrictor-test-data
curl.exe -fL -o make_nucleisky_fixtures.py https://raw.githubusercontent.com/CellMigrationLab/NucleiSky/0.1.4/lc_tests/make_fixtures.py
& "C:\LabConstrictor\NucleiSky\python.exe" make_nucleisky_fixtures.py ns
```

**macOS / Linux terminal** (replace the install prefix):

```bash
mkdir -p ~/LabConstrictor-test-data
cd ~/LabConstrictor-test-data
curl -fL -o make_nucleisky_fixtures.py https://raw.githubusercontent.com/CellMigrationLab/NucleiSky/0.1.4/lc_tests/make_fixtures.py
"<NUCLEISKY_INSTALL_PREFIX>/bin/python" make_nucleisky_fixtures.py ns
```

Expect the line `ok (1600, 1600) (520, 520)` and the files in `LabConstrictor-test-data/ns/`. This generator needs NumPy, SciPy and tifffile, which the NucleiSky app is expected to supply; if the command cannot run, report **BLOCKED**, with the error text. Do not substitute arbitrary images for a known-answer transform test.

Open the `reference.tif` and `query.tif` from that **same generated set**, specify **0.65 µm** and **0.325 µm**, and consult [NucleiSky expectations](human_tests/nucleisky.md#ns-n4-run-with-default-settings): rotation around **12°**, with the source app's case-specific tolerances. The images intentionally have no usable physical pixel calibration until you enter it.

## Data V1: VLab4Mic image comparison

For comparison and negative-input tests, the tagged [VLab4Mic fixture generator](https://raw.githubusercontent.com/CellMigrationLab/LabConstrictor-VLab4Mic/0.1.6/lc_tests/make_fixtures.py) generates the TIFF images and a small local `mini_ring.cif`. Download `make_fixtures.py` to a **different** working folder (do not overwrite NucleiSky's script) and run it with VLab4Mic's installed Python:

```text
<YOUR_VLAB4MIC_PYTHON> make_fixtures.py vlab4mic
```

Use `reference_20nm.tif` against itself first (SSIM and Pearson expected near **1**), then `unrelated_20nm.tif`, `flat_20nm.tif` and `stack.tif` for the error/shape checks. Refer to [VL-N3](human_tests/vlab4mic.md#vl-n3-compare-an-image-with-a-reference) or [VL-F2](human_tests/vlab4mic.md#vl-f2-compare-with-the-pixel-size-limit). **Do not mix up nanometres and micrometres:** 20 nm = 0.020 µm. Data-generation mechanics are a tester prerequisite, not a property of the bridge.

## Data C1/C2: CellTracksColab

- **C1 (bridge tool):** right-click the [two-track CSV](https://raw.githubusercontent.com/CellMigrationLab/CellTracksColab/1.1.2/lc_tests/fixtures/tracks.csv) and save it as `tracks.csv`, without adding `.txt`. This sample has two tracks. The [tagged cases](https://github.com/CellMigrationLab/CellTracksColab/blob/1.1.2/lc_tests/cases.json) give numerical expectations for the `calculate_metrics` tool; test this via the command-line interface only as an **optional technical check**, not through a host UI.
- **C2 (notebook):** a real TrackMate export or a separately validated synthetic export is needed to assess importing, trajectories, plots and tables. No such sample has been verified in the tagged source. You can still **PASS** opening the notebook (`NB1/2`) without claiming `NB3` passed; record `NB3 BLOCKED (test dataset missing)` unless the actual import ran successfully.

## Maintainer TODO — improve this before a broader human round

Publish **one small, versioned, checksum-listed `LabConstrictor-alpha.3-test-data.zip`** containing P1, N1, V1, C1 and a **validated** C2 TrackMate demo. Include a one-page `README`, the expected outcomes, original upstream tags/commit SHAs, and clear separation between synthetic and real data. Then replace the generator/source-archive steps above with **one download link**. Until that bundle is published, **do not invent a download URL or imply C2 is provided**.
