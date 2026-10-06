# Human test protocol: LabConstrictor tools in Napari and Fiji

**Purpose.** Check, by hand and on a real computer, that a LabConstrictor app (NucleiSky and CellTracksColab are used here) installs,
registers its tools, and that those tools work in **Napari** and in **Fiji**, and fail in an understandable way when something is wrong.

**Who.** Anyone who can install a program and use Napari/Fiji. No programming is needed; a few steps type one command into a terminal.

**How long.** About 2 hours for everything, 30 minutes for the *Quick path*. Run it once per operating system (Windows, macOS, Linux).

**What this protocol replaces.** `docs/TESTING_PROMPT.md` is a prompt for an AI agent that tests from source; this file is the one for people.

## How to use this document
1. Copy this file (or paste it into a new GitHub issue: the boxes then become clickable). Print it if you prefer paper.
2. Fill in the **Record sheet** (section 0).
3. Do the sections in order. Each test has **Do** (what to do), **Expect** (what you should see) and three boxes. Tick exactly one:
   * `PASS` : what you see matches **Expect**.
   * `FAIL` : it differs. Write what you saw in *Notes*, and take a screenshot.
   * `N/A` : you could not do the step (say why in *Notes*; "no Windows machine" is a valid reason).
4. Do not skip a failing test: note it and continue, unless the test says **STOP**.
5. At the end, send the record sheet, the screenshots and a support bundle (section 10).

**Quick path (30 minutes, after the installers have run).** Section 2 (test data), S1, S2, S3, N0, N1, N3, N4, N6, F0, F1, F3, F5, U1, U2. Everything else is the full protocol.

**Severity** (use it when you write a FAIL):
| Level | Meaning |
|---|---|
| Blocker | cannot install, cannot start, data lost, or a wrong scientific result **without any warning** |
| Major | a feature does not work, or an error is shown but nobody could understand it |
| Minor | works, but confusing, slow, or a wrong label |
| Cosmetic | spelling, alignment |

**Words used.** *App* = a LabConstrictor installer program (NucleiSky, CellTracksColab). *Tool* = one function of an app that appears
in Napari/Fiji (NucleiSky: "Relocalize 2D"; CellTracksColab: "Calculate Track Metrics"). *Registry* = the folder where installed apps
announce themselves. *Prefix* = the folder you chose when installing the app.

---

## 0. Record sheet (fill in before you start)
| Field | Your entry |
|---|---|
| Tester name and date | |
| Operating system and version (e.g. Windows 11 23H2, macOS 14.5 Apple silicon, Ubuntu 24.04) | |
| Computer: RAM, is it a managed/office computer with antivirus or admin restrictions? | |
| Are you behind a proxy or firewall? | |
| Do you have admin rights? (Yes / No) | |
| Napari version and how it was installed | |
| Fiji version (Help > About ImageJ) | |
| NucleiSky installer file name | |
| CellTracksColab installer file name | |
| Was LabConstrictor installed on this computer before? (existing apps, existing `.labconstrictor` folder) | |
| Prefix (install folder) of NucleiSky / CellTracksColab | |

---

## 1. What you need
- [ ] A computer with the operating system you will report on, and at least 25 GB of free disk space (NucleiSky downloads PyTorch: its installed folder is about 9 GB, the download caches take about 5 GB more, and the optional Cellpose model 1.2 GB). On a very bare Linux system Napari may also need the `libxcb-*` system packages (error `Could not load the Qt platform plugin "xcb"`): install them with your package manager; that is a computer setup problem, not a LabConstrictor one.
- [ ] Internet access during installation (the installers download packages) and, for item N9, for the first Cellpose/InstanSeg run.
- [ ] The two installers for your operating system (from the project's release page or from the person who sent you this protocol): NucleiSky and CellTracksColab.
- [ ] Python 3.10 or newer to create the Napari environment (or an existing Napari installation you are allowed to modify; a fresh one is better).
- [ ] Fiji (https://fiji.sc, "Fiji with Java"). Use a fresh unzipped copy, not your daily one, if you can.
- [ ] A screenshot tool, a text editor, and this document.

**Folder names used below.** Replace `<PREFIX_NS>` and `<PREFIX_CT>` with the install folders of NucleiSky and CellTracksColab
(type the real folder: nothing in `<...>` is a variable your terminal understands).

**Which Python.** Each app has its own Python. The commands below start it by its full path:

| | Linux / macOS (terminal) | Windows (PowerShell) |
|---|---|---|
| NucleiSky's Python (`<NS_PY>`) | `<PREFIX_NS>/bin/python` | `& "<PREFIX_NS>\python.exe"` |
| CellTracksColab's Python (`<CT_PY>`) | `<PREFIX_CT>/bin/python` | `& "<PREFIX_CT>\python.exe"` |

In every command, `<NS_PY>` / `<CT_PY>` stands for the matching line of this table, typed in full (in PowerShell the `&` and the quotes are
needed, also when the path has no space). Unless a test says otherwise, use **NucleiSky's** Python for `list`, `doctor` and `support-bundle`.
Windows users: if your terminal is `cmd.exe` instead of PowerShell, leave out the `&`.

**Where things are**
| What | Linux / macOS | Windows |
|---|---|---|
| Registry folder (do not delete) | `~/.labconstrictor/apps` | `%USERPROFILE%\.labconstrictor\apps` |
| Log file | `~/.labconstrictor/logs/labconstrictor.log` | `%USERPROFILE%\.labconstrictor\logs\labconstrictor.log` |
| Installer log of an app | `<PREFIX>/menuinst_debug.log` | `<PREFIX>\menuinst_debug.log` |
| Run records | `~/.labconstrictor/runs/` | `%USERPROFILE%\.labconstrictor\runs\` |
| Results of command-line runs | `~/.labconstrictor/results/` | `%USERPROFILE%\.labconstrictor\results\` |

---

## 2. Test data (5 minutes)
You need three small files. They are generated with the Python that comes with the installed NucleiSky (it already has everything needed).

**Do, Linux/macOS (terminal):**
```
mkdir testdata
cd testdata
curl -L -O https://raw.githubusercontent.com/CellMigrationLab/NucleiSky/bridge-test/lc_tests/make_fixtures.py
<PREFIX_NS>/bin/python make_fixtures.py ns
curl -L -o tracks.csv https://raw.githubusercontent.com/CellMigrationLab/CellTracksColab/bridge-test/lc_tests/fixtures/tracks.csv
echo hello > fake.tif
```
**Do, Windows (PowerShell; type `curl.exe`, not `curl`, which PowerShell redirects to something else):**
```
mkdir testdata
cd testdata
curl.exe -L -O https://raw.githubusercontent.com/CellMigrationLab/NucleiSky/bridge-test/lc_tests/make_fixtures.py
& "<PREFIX_NS>\python.exe" make_fixtures.py ns
curl.exe -L -o tracks.csv https://raw.githubusercontent.com/CellMigrationLab/CellTracksColab/bridge-test/lc_tests/fixtures/tracks.csv
"hello" | Out-File -Encoding ascii fake.tif
```
`fake.tif` is a text file that pretends to be an image (used to check the error messages). Cutting a real image short is optional (test E3).

**Write down the full path of this `testdata` folder** (in the terminal: `pwd` on Linux/macOS, `Get-Location` in PowerShell). From here on,
**`<TESTDATA>` means that exact folder**, for example `/home/anna/testdata` or `C:\Users\Anna\testdata`; `testdata/ns/reference.tif` means `<TESTDATA>/ns/reference.tif`.

**Expect:** the folder `ns` contains `reference.tif` (5.1 MB), `query.tif` (0.5 MB), `reference_mask.tif`, `query_mask.tif`, `ground_truth.json`, plus a few more masks used only by the project's own automated tests (`*_binary.tif`, `*_fractions.tif`: ignore them); the last line printed by the generator is `ok (1600, 1600) (520, 520)`.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

---

## 3. Installation and registration

### S1. Install NucleiSky
**Do:** run the NucleiSky installer. Choose an install folder (write it in the record sheet). Wait until it says it has finished.
(Linux batch example: `bash NucleiSky-0.1.1-Linux-x86_64.sh -b -p <PREFIX_NS>`. macOS: use the macOS installer file you were given, for example `bash <that file> -b -p <PREFIX_NS>`; never the Linux file.) This takes several minutes (it downloads PyTorch).

**Expect:** the installer finishes without an error message and without asking to close it manually after a failure.
The file `<PREFIX_NS>/menuinst_debug.log` exists and its last line is `Post-install completed successfully.`

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

### S2. The tools were registered during installation
**Do:** open `menuinst_debug.log` of NucleiSky and search for `lc_tools`. (During installation the installer downloads the small *labconstrictor-tools* package from GitHub, so the computer needs internet access at that moment; the log shows `Successfully installed labconstrictor-tools-...`.)
* Linux/macOS: expect the lines `Found nucleisky_lc_tools: registering the tools of NucleiSky for Napari and Fiji` and
  `Tools registered (labconstrictor-tools list shows them).` There must be **no** line starting with `WARNING: tool registration failed`.
* Windows: expect the line `Found nucleisky_lc_tools: registering ...`, followed by a block of text that contains `"schema_path"`,
  and **no** line starting with `WARNING: tool registration failed`. (The Windows script does not print "Tools registered".)

Then run, with NucleiSky's Python (see "Which Python"):
* Linux/macOS: `<PREFIX_NS>/bin/python -m labconstrictor_tools list`
* Windows PowerShell: `& "<PREFIX_NS>\python.exe" -m labconstrictor_tools list`

**Expect:** the output contains `NucleiSky  (0.1.1)` followed by an indented line `relocalize               Relocalize 2D`.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

### S3. Install CellTracksColab
**Do:** run the CellTracksColab installer (same as S1, install folder `<PREFIX_CT>`). Then run `list` with CellTracksColab's Python:
* Linux/macOS: `<PREFIX_CT>/bin/python -m labconstrictor_tools list`
* Windows PowerShell: `& "<PREFIX_CT>\python.exe" -m labconstrictor_tools list`

**Expect:** the installer finishes; its `menuinst_debug.log` shows the same registration lines as in S2 (module `celltracks_lc_tools`).
`list` shows **both** apps: `CellTracksColab  (1.1.0)` with `calculate_metrics        Calculate Track Metrics`, and `NucleiSky  (0.1.1)`.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

### S4. Diagnose
**Do:**
* Linux/macOS: `<PREFIX_NS>/bin/python -m labconstrictor_tools doctor`
* Windows PowerShell: `& "<PREFIX_NS>\python.exe" -m labconstrictor_tools doctor`

**Expect:** one line per app starting with a check mark, e.g. `NucleiSky    1 tool(s), schema current, interpreter <PREFIX_NS>/bin/python (0.05 s)`; no line starting with a cross.
The last lines name the registry folder and the log file location.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

### S5. Nothing unexpected was installed or written
**Do:** look in your home folder.

**Expect:** the only new **LabConstrictor** folder is `.labconstrictor` (registry, logs, runs). The installer itself may also create menu entries (on Linux under `~/.local/share/applications` and `~/.local/share/desktop-directories`) and the folders of the tools it uses (`~/.conda`, `~/.mamba`, `~/.cache`, `~/.config`, `~/.local/share/mime`; later also `~/.imagej` and `~/.java` from Fiji and `~/.cellpose` from Cellpose), including dated backups of `~/.config/menus/applications.menu`: that is normal and not a failure. No error dialogs appeared during installation. Installation did not require administrator rights unless you chose a protected folder.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

---

## 4. Command line (optional, 10 minutes)
### C1. Run a tool without any window
**Do:**
* Linux/macOS: `<PREFIX_CT>/bin/python -m labconstrictor_tools run CellTracksColab calculate_metrics tracks=<TESTDATA>/tracks.csv`
* Windows PowerShell: `& "<PREFIX_CT>\python.exe" -m labconstrictor_tools run CellTracksColab calculate_metrics tracks=<TESTDATA>\tracks.csv`

**Expect:** a JSON report with `"status": "COMPLETE"`, a result of type `table`, and a last line `(results are in ...results/<time>_<id>_CellTracksColab_calculate_metrics - use --out DIR ...; the newest 20 runs are kept)`. (`<id>` is a short random string, so that two runs in the same second never share a folder.) The folder contains `table.csv` with two data rows.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

### C2. A readable error
**Do:**
* Linux/macOS: `<PREFIX_NS>/bin/python -m labconstrictor_tools run NucleiSky relocalize reference=<TESTDATA>/fake.tif query=<TESTDATA>/ns/query.tif`
* Windows PowerShell: `& "<PREFIX_NS>\python.exe" -m labconstrictor_tools run NucleiSky relocalize reference=<TESTDATA>\fake.tif query=<TESTDATA>\ns\query.tif`

**Expect:** `"status": "FAILED"`, `"code": "unreadable_image"` and an `error` that says `cannot read fake.tif: not a TIFF file`. No Python traceback dump is needed to understand it.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

---

## 5. Napari

### N0. Prepare Napari (once)
**Do:** create a fresh environment and install (Linux/macOS shown). On Windows run the same commands but activate the environment with
PowerShell: `.\napari-env\Scripts\Activate.ps1`, or with cmd.exe: `napari-env\Scripts\activate.bat`. (If PowerShell refuses with an
"execution of scripts is disabled" error, that is a setting of your computer, not a LabConstrictor problem: write it in the notes and use cmd.exe.)
```
python -m venv napari-env
source napari-env/bin/activate
pip install "napari[pyqt5]" https://github.com/CellMigrationLab/LabConstrictor-Tools/archive/refs/heads/main.zip https://github.com/CellMigrationLab/napari-labconstrictor/archive/refs/heads/main.zip
napari
```
(The two long web addresses are the project's source archives: pip downloads them like any package, no `git` program is needed.)

**Expect:** Napari opens. `Plugins` menu contains **LabConstrictor tools** (the entry reads `LabConstrictor tools (LabConstrictor)`; on other Napari versions it may sit in a submenu). A one-time notice about the PyQt5 backend is normal.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

### N1. The apps are listed
**Do:** `Plugins > LabConstrictor tools`. Open the first drop-down.

**Expect:** the dock opens at the right. The first drop-down lists `CellTracksColab` and `NucleiSky`. The second lists the tool of the chosen app. The panel has the buttons **Run**, **Cancel** (greyed), **Rescan apps**, **Restart worker**, **Details...** (greyed), and the box *Keep the worker running between runs (faster repeat runs)*.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

### N2. The NucleiSky form
**Do:** choose app `NucleiSky`, tool `Relocalize 2D`.

**Expect:** a description line, then three bold headings in this order: **Images**, **Segmentation**, **Matching**, and below them a box **Show advanced settings** (unticked; the fourth heading, *Fine-tuning*, appears only when you tick it, see N10).
Under *Images*: *Reference* with a layer drop-down and a row *or file* (button *Select file*), *Query* with *or file*, *Reference pixel size um (um/px)* = 0.6500, *Query pixel size um (um/px)* = 0.3250, *Reference mask* and *Query mask* (each with *or file*).
Under *Segmentation*: *Segmentation* = threshold, *Threshold method* = otsu, *Blur sigma (px)* = 1.0000, *Min area (px)* = 5, *Watershed split* ticked, then *InstanSeg model*, *InstanSeg target*, *InstanSeg: clean up fragments* (these three greyed). Under *Matching*: *Matcher* = auto.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

### N3. Open the test images
**Do:** `File > Open File(s)...`, select `testdata/ns/reference.tif` and `testdata/ns/query.tif`. In the form set *Reference* = `reference`, *Query* = `query`.

**Expect:** two layers appear. The drop-downs offer them. The pixel-size fields stay 0.65 and 0.325 (these files carry no calibration).

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

### N4. Run with default settings
**Do:** press **Run**. (The very first run after installation can take up to 2 minutes while code is compiled and loaded. After that, a run in a new worker takes about 10 to 20 seconds and a run in a kept worker about 2 seconds.)

**Expect:** the status line shows a progress message (`segmenting nuclei`, then `matching 9 query nuclei against 429 reference nuclei`) and the progress bar moves. At the end the status line reads
`✔ done in <n>s  rotation_deg=12.17..., scale=1.002..., bbox_y0y1x0x1=[637, 963, 597, 923], n_nuclei_reference=429, n_nuclei_query=9, matcher=quad`.
Two new layers appear: `NucleiSky:alignment` and `NucleiSky:query_aligned`. The Run button is usable again and **Details...** is enabled.
Accept rotation between 12.0 and 12.4, scale between 0.99 and 1.01. The nucleus counts should be exactly 429 and 9.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes (numbers you saw): ______________________________

### N5. The result is placed correctly
**Do:** hide `reference` and `query`; show `NucleiSky:query_aligned` over `reference` (set its blending to `additive` if needed) and zoom to the bright cluster.

**Expect:** the aligned query is a small bright patch located inside the large reference field, and its nuclei sit on top of the reference's nuclei (no obvious shift or rotation).

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

### N6. Choose the matcher
**Do:** set *Matcher* to `quad`, run; then `hashing`, run; then `triangles`, run.

**Expect:** `quad` and `hashing`: `✔ done`, the same rotation (about 12.17) and `matcher=quad` / `matcher=hashing` at the end of the status line. `triangles`: the status line shows **`⚠ No match found with the 'triangles' matcher. This is not an error in the images: try Matcher = auto, or another matcher.`**
This is the correct outcome for these test images. It must be a notice (a status line beginning with ⚠), not one beginning with ✖, and the Run button must work again afterwards.
(`graph` behaves like `triangles` on these images.)

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

### N7. Images from files instead of layers
**Do:** set *Matcher* back to `auto`. Next to *Reference*, press *Select file* (under *or file*) and choose `testdata/ns/reference.tif`; do the same for *Query* with `query.tif`. Run.

**Expect:** after you pick a file, the layer drop-down above it is greyed out (the file wins). The run gives the same numbers as N4.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

### N8. Settings that do not apply are greyed out
**Do:** clear both *or file* rows (empty field). Set *Segmentation* to `instanseg`.

**Expect:** *Threshold method*, *Blur sigma*, *Min area* and *Watershed split* become greyed out and the three *InstanSeg* fields become usable. Switching back to `threshold` reverses it. (Do **not** run with `instanseg` here.)

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

### N9. Other segmentation settings (optional: needs internet; the Cellpose run takes about 20 minutes or more on a computer without a graphics card)
**Do:** set *Segmentation* = `threshold`, *Threshold method* = `li`, *Min area* = 80, run. Then set *Segmentation* = `cellpose`, run.

**Expect:** the `li` run completes with `n_nuclei_reference` close to 425 (not 429) and `n_nuclei_query=9`. The Cellpose run is slow (the status line says it is loading cellpose and the progress bar keeps moving; the first time it also downloads a model of about 1 GB); it completes with about 347 reference nuclei and a rotation near 12.17, or, if the download is blocked, shows a message `segmentation_unavailable ... the first run needs internet` instead of freezing. (InstanSeg is known not to find nuclei in these synthetic images; do not report that.)

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

### N10. Advanced settings and "unset" values
**Do:** tick **Show advanced settings**. Untick it, tick it again.

**Expect:** a group **Fine-tuning** appears with *Peak distance (px)* = 5, *Fixed seed* and *Time limit (s)*; each of the last two has a box **set** below it, unticked, and the value field is greyed out. Unticking *Show advanced settings* hides them again.
Now tick **set** under *Fixed seed*, type 3; tick **set** under *Time limit*, type 60; run.
**Expect:** the run completes with the same result as N4. Untick both **set** boxes and run again: same result (an unset value must not behave like 0: a time limit of 0 would have stopped the matching).

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

### N11. Existing masks
**Do:** in *Reference mask* press *Select file* (under *or file*) and choose `testdata/ns/reference_mask.tif`; run. Then also set *Query mask* from `query_mask.tif`; run. Finally set *Reference mask* to `query_mask.tif` (wrong size) and run.

**Expect:** the first two runs complete with `n_nuclei_reference=393` and `n_nuclei_query=9` and a rotation near 12.17-12.19. The wrong-size run shows a status line beginning with ✖:
`✖ [mask_shape_mismatch] Reference mask must have the same size as its image: mask (520, 520), image (1600, 1600) ...`, stops within a few seconds, and the Run button works again.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

### N12. Cancel
**Do:** clear the masks. Press **Run**, and press **Cancel** as soon as the status line says `segmenting nuclei` (you have about 3 seconds). Wait. Run again. This time press **Cancel** when it says `matching 9 query nuclei against 429 reference nuclei`.

**Expect:** first: the status line becomes `cancelled`. Second: it becomes `cancelled (worker stopped)` within about 5 seconds (the tool does not check for Cancel while matching, so its process is stopped). Both times Run is usable again, and a following normal run (N4) completes.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

### N13. An error you can understand
**Do:** in *Reference* use *Select file* and choose `testdata/fake.tif` (the text file); *Query* = `query`. Run. Then press **Details...**.

**Expect:** a status line beginning with ✖: `✖ [unreadable_image] cannot read fake.tif: not a TIFF file: header=b'hell'  - click Details... for the full report (log: ...)`. **Details...** opens a window with the error, the worker output, the run record location and the end of the log.
The sentence tells you what is wrong without a programmer.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

### N14. The second app: a table result
**Do:** clear *or file* rows. Choose app `CellTracksColab`, tool `Calculate Track Metrics`. For *Tracks* press *Select file* and choose `testdata/tracks.csv`. Run.

**Expect:** `✔ done ... table 'table' (2 rows)`. A table panel appears at the bottom whose columns include `Unique_ID`, `Track Duration`, `Mean Speed`, `Total Distance Traveled`, `Directionality` (it also has the median, maximum, minimum and standard deviation of the speed).
Switching between the two apps in the first drop-down works and shows the right tool each time.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

### N15. Faster second run
**Do:** choose app `NucleiSky`, tool `Relocalize 2D` again (N14 left CellTracksColab selected, which has no Matcher). Set *Reference* = `reference`, *Query* = `query`, clear the *or file* rows, and set *Matcher* = `auto`. Make sure *Keep the worker running between runs (faster repeat runs)* is ticked. Press **Restart worker**, then press **Run** three times in a row (wait for each to finish).

**Expect:** the first run after the restart takes the longest (10 to 20 seconds; up to 2 minutes if it is the first run since installation), the second and third about 2 seconds each. Write the three times in the notes. Then untick the box and run twice: both take about as long as the first run.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes (times): ______________________________

### N16. Closing leaves nothing behind
**Do:** close Napari. Open the process list (Task Manager on Windows, Activity Monitor on macOS, `ps aux | grep '[l]abconstrictor_tools.*serve'` on Linux).

**Expect:** no `python ... labconstrictor_tools serve ...` process remains within 15 seconds.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

---

## 6. Fiji

### F0. Install the plugin (once)
**Option A, no build (use this):** download the file `LabConstrictor_Tools.groovy` from
https://github.com/CellMigrationLab/LabConstrictor-Fiji/blob/main/src/main/resources/org/cellmigrationlab/labconstrictor/LabConstrictor_Tools.groovy
(button *Download raw file*; keep the name exactly, **the underscore matters**: Fiji lists a script in its menus only when its name contains one)
and put it into the folder `scripts/Plugins/LabConstrictor/` inside your Fiji folder (create the two folders `scripts/Plugins` and `LabConstrictor` if they do not exist; the Fiji folder is called `Fiji.app` on macOS and Windows and `Fiji` on Linux), then restart Fiji. The menu entry is `Plugins > LabConstrictor > LabConstrictor Tools`; write down the exact menu path you see. (If you cannot find it in the menu, type `LabConstrictor` into Fiji's search bar at the top and press *Run*, and write that down as a failure of this test.)

**Option B, jar (needed for the macro test F12; needs Java and Maven):** clone the Fiji repository, run `mvn package`, copy `target/labconstrictor-fiji-0.1.0.jar` into the `plugins` folder of your Fiji folder, restart Fiji. The entry is `Plugins > LabConstrictor > LabConstrictor Tools...`.

**Expect:** after restart the menu entry exists. Do not install both options at the same time.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Menu path you used: ______________________________

### F1. Choose app and tool
**Do:** open `File > Open...` for `testdata/ns/reference.tif` first and then `testdata/ns/query.tif` (the order matters: the first open image is offered as the reference). Start the plugin from the menu.

**Expect:** a small dialog titled *LabConstrictor* with a drop-down *Application* lists `CellTracksColab` and `NucleiSky` (pick `NucleiSky`, OK). (With only one app registered this dialog is skipped.) The tool has only one choice, so there is no tool dialog; the tool form opens directly, titled *Relocalize 2D*.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

### F2. The form
**Expect (in the form from F1):** a note *Images are taken from the open windows. To use a file instead, choose it in the matching '(or file)' field.*; the headings **— Images —**, **— Segmentation —**, **— Matching —**, **— Advanced settings —**, **— Fine-tuning —** (in that order); *Reference* and *Query* choosers preselected with the two open images (check they are the right way round: reference = the big 1600 x 1600 image); *Reference (or file)* / *Query (or file)* fields; *Reference pixel size um (um/px)* and *Query pixel size um (um/px)*; checkboxes *Use reference mask* / *Use query mask*; the segmentation fields; *Matcher*; *Peak distance (px)*; **Set fixed seed** with *Fixed seed*; **Set time limit** with *Time limit (s)*.
Fields that do not apply to the chosen segmentation are **not** greyed out in Fiji (known limitation, do not report).

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

### F3. Run with defaults
**Do:** set the pixel sizes to 0.65 (reference) and 0.325 (query) if they differ, leave everything else, press OK.

**Expect:** a progress bar in Fiji's status line, then: a new image window **NucleiSky:query_aligned**, a window **Alignment overlay (green = reference, magenta = query)** showing a green field of nuclei with a small white/pink cluster where the query lies, and, in the **Log** window, a line starting `NucleiSky values: [rotation_deg:12.17..., ...` that also contains `n_nuclei_reference:429`, `n_nuclei_query:9` and `matcher:quad` (the order of the entries may differ).

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes (numbers): ______________________________

### F4. Matcher choice and "no match"
**Do:** start the plugin again, set *Matcher* = `hashing`, OK; then again with `triangles`.

**Expect:** `hashing` works (`matcher=hashing`). `triangles` shows a plain **message** window (information, not the red error style) with `No match found with the 'triangles' matcher. This is not an error in the images: try Matcher = auto, or another matcher.`

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

### F5. Unset values
**Do:** start the plugin; tick **Set fixed seed** and type 3; tick **Set time limit** and type 60; OK. Then run again with both boxes unticked.

**Expect:** both runs complete with the same result as F3.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

### F6. Files instead of windows
**Do:** `Window > Close All`. Start the plugin.

**Expect:** the form now shows file-chooser fields named *Reference*, *Query* and the optional masks, and no open-image selectors (there is no open image to choose from). Select `testdata/ns/reference.tif` and `query.tif` through them and run: same result as F3.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

### F7. Cancel
**Do:** run again and press the **Esc** key while the progress bar is moving.

**Expect:** the run stops within a few seconds, no result windows appear, the Log window says `LabConstrictor: the run was cancelled` (Fiji's own status line may only say that the command finished), and the next run works.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

### F8. An error you can understand
**Do:** start the plugin with no image open, choose `testdata/fake.tif` as *Reference (or file)* and `query.tif` as the query; OK.

**Expect:** an error window titled `LabConstrictor: NucleiSky` saying `[unreadable_image] cannot read fake.tif: not a TIFF file ...` and naming the log file. No Java stack trace shown.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

### F9. CellTracksColab: a table result
**Do:** start the plugin, choose `CellTracksColab`; this tool has a single input, so Fiji shows only a plain *Choose a file* window instead of a form: choose `testdata/tracks.csv` in it.

**Expect:** a window named **table** (Fiji Results table) with 2 rows whose columns include `Unique_ID`, `Track Duration`, `Mean Speed`, `Total Distance Traveled`, `Directionality`.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

### F10. Run a one-image tool twice (known open question; needs a real desktop, not a remote or virtual screen)
**Do:** register the small example app that ships with the tools package, using the Python of your Napari environment (it has everything the example needs):
`<napari-env>/bin/python -m labconstrictor_tools register --name synthetic --prefix <napari-env> --module labconstrictor_tools.examples.synthetic`
(Windows PowerShell: `& "<napari-env>\Scripts\python.exe" -m labconstrictor_tools register --name synthetic --prefix "<napari-env>" --module labconstrictor_tools.examples.synthetic`). In Fiji open `testdata/ns/query.tif`. Start the plugin, choose application `synthetic`, tool `Image stats`, OK. Then start the plugin **again** and run `Image stats` a second time with the image still open.

**Expect:** both runs show the same dialog (with the open image selected) and print a line `synthetic values: [shape:[520, 520], dtype:uint16, mean:...]` (the order may differ) in the Log window.
**Mark FAIL** if the second run shows only a bare *Choose a file* prompt instead of the dialog, and describe exactly what you did (this is a known, unexplained problem; your observation is what we need).
Clean up afterwards: `<napari-env>/bin/python -m labconstrictor_tools unregister --name synthetic` (Windows: the same with `& "<napari-env>\Scripts\python.exe"`).

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

### F11. Skipped or missing apps are reported (do this together with E1)
**Do:** while CellTracksColab is broken as described in E1, start the plugin in Fiji and open the **Log** window (`Window > Log`; the line may already be there).

**Expect:** a line `LabConstrictor: skipped CellTracksColab: not available on this machine (interpreter ... is missing)` explains why the app is missing from the list.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

### F12. Macro recording and replay (jar only: option B)
**Do:** `Plugins > Macros > Record...`. Run NucleiSky with defaults through the dialog (F3). Look at the recorder text. Copy the recorded line into a macro (`Plugins > Macros > New...`), close the result windows, and run the macro.

**Expect:** the recorder shows one line like `run("LabConstrictor Tools...", "app=NucleiSky tool=[Relocalize 2D] reference=reference.tif query=query.tif reference_pixel_size_um=0.65 ...");`. The line **does not** contain `fixed_seed=` or `max_seconds=` when those were not set. Running the macro runs the tool without any dialog and gives the same result. A wrong tool name in the macro gives a message that lists the valid tools.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

### F13. Closing leaves nothing behind
**Do:** close Fiji and check the process list as in N16.

**Expect:** no `labconstrictor_tools serve` process remains.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

---

## 7. When something is wrong (these tests change the app: do them last, and restore afterwards)

### E1. Registry listing survives a broken app
**Do:** first **close Napari and Fiji completely** and check in the process list that no CellTracksColab worker (`python ... labconstrictor_tools serve`) is left; Windows will not rename a program that is still running. Then rename CellTracksColab's Python:
* Linux/macOS: `mv <PREFIX_CT>/bin/python <PREFIX_CT>/bin/python.off`
* Windows PowerShell: `Rename-Item "<PREFIX_CT>\python.exe" python.off`

Run `doctor` and `list` with **NucleiSky's** Python (see "Which Python"). Start Napari, open the widget, and read the status line. Start Fiji and open its **Log** window after starting the plugin.

**Expect:** `doctor` shows a cross for `CellTracksColab` with `not available on this machine (interpreter ... is missing)`; `list` says `CellTracksColab  -- skipped: ...`. NucleiSky stays usable. Napari lists only `NucleiSky` and its status line reads `⚠ skipped: CellTracksColab (...)`. **Restore the file name before you continue** (Linux/macOS: `mv <PREFIX_CT>/bin/python.off <PREFIX_CT>/bin/python`; Windows PowerShell: `Rename-Item "<PREFIX_CT>\python.off" python.exe`) and check that `doctor` is clean again.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

### E2. A package is missing inside an app
**Do:** first write down the installed version: `<CT_PY> -m pip show pandas` (look at the `Version:` line; write it in the notes). Then `<CT_PY> -m pip uninstall -y pandas`, and run `Calculate Track Metrics` in Napari. Afterwards reinstall **exactly the version you wrote down**: `<CT_PY> -m pip install pandas==<that version>`. (`<CT_PY>`: see "Which Python"; on Windows it is `& "<PREFIX_CT>\python.exe"`.)

**Expect:** `✖ [ModuleNotFoundError] No module named 'pandas'  - click Details...`. Details shows the traceback. After reinstalling, the tool works again.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

### E3. Damaged and unusual files
**Do:** in Napari (and Fiji if you like) use these as the *Reference* file: (a) a text file called `fake.tif` (done in N13); (b) a TIFF cut short: Linux/macOS `head -c 3000000 <TESTDATA>/ns/reference.tif > <TESTDATA>/short.tif`; Windows PowerShell `$b=[IO.File]::ReadAllBytes("<TESTDATA>\ns\reference.tif"); [IO.File]::WriteAllBytes("<TESTDATA>\short.tif",$b[0..2999999])`; (c) a path with spaces and non-English letters (copy `query.tif` to a folder `test é 日本` and use it).

**Expect:** (a) as N13. (b) `✖ [unreadable_image] cannot read short.tif: failed to read ... bytes, got ...`. (c) the run works exactly as with the normal path.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

### E4. A process killed from outside
**Do:** start a NucleiSky run in Napari. While it runs, in the process list end the `python ... labconstrictor_tools serve` process of NucleiSky.

**Expect:** the status line says `✖ worker exited unexpectedly (code ...)` with a likely cause (for example "the worker was killed"), Run is usable again, and the next run works.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

### E5. Support bundle
**Do:** `<NS_PY> -m labconstrictor_tools support-bundle --out <TESTDATA>/bundle.zip` (Windows PowerShell: `& "<PREFIX_NS>\python.exe" -m labconstrictor_tools support-bundle --out "<TESTDATA>\bundle.zip"`), open the zip.

**Expect:** it contains `logs/labconstrictor.log`, `apps/*.json`, the latest `runs/*/run.json`, `doctor.txt` and `environment.txt`. It contains file names, folder names and the parameter values of recent runs, but **no image or table contents**. The tool does not intentionally collect passwords or tokens, but the logs and run records are **not scrubbed of secrets**: read through the files in the zip before you share it, and remove it if it contains paths, parameter values, tokens or anything else private (your user name will appear in paths; that is expected, tell us if you do not want to share it).

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

---

## 8. Several apps, updates and uninstall

### U1. Both apps work side by side
**Do:** with both apps installed (S3), in one Napari session switch between NucleiSky and CellTracksColab and run each (N4, N14); in Fiji the same.

**Expect:** each app runs in its own Python (no conflict between their packages); both runs succeed in the same session.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

### U2. Uninstall one app
**Do:** first close Napari and Fiji and check in the process list that no CellTracksColab worker is running (on Windows a running worker locks files). Then uninstall CellTracksColab with its normal uninstaller (Windows: *Apps & features*; Linux/macOS: run `bash <PREFIX>/uninstall.sh`, where `<PREFIX>` is the folder you installed into). Then run `list` (NucleiSky's Python) and reopen Napari and Fiji only now: look at Napari (press *Rescan apps*) and Fiji (restart the plugin).

**Expect:** `CellTracksColab` is gone from all three; `NucleiSky` is still listed and still runs. `~/.labconstrictor/apps` no longer contains `CellTracksColab.json`.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

### U3. Install the same app twice, then remove the older one
**Do:** (close Napari and Fiji before every uninstall below, and reopen them only when the uninstall has finished) install CellTracksColab into a folder `A` (it may already exist from S3 or U2; install it again if you removed it). Then install it **again** into a different folder `B`. Uninstall the copy in `A` only. Run `list` and run the tool in Napari.

**Expect:** after uninstalling `A`, `list` still shows `CellTracksColab` and the tool still runs (the newer installation, `B`, owns the registration). After you also uninstall `B`, `CellTracksColab` disappears from `list`.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

### U4. Installation without internet for the tools package (optional, advanced)
**Do:** before running an installer, set an unreachable source: Linux/macOS `LC_TOOLS_SPEC=/nonexistent/x.whl bash installer.sh -b -p <new folder>`; Windows cmd.exe: `set LC_TOOLS_SPEC=C:\nonexistent\x.whl`, Windows PowerShell: `$env:LC_TOOLS_SPEC='C:\nonexistent\x.whl'`, then start the installer from the same window.
**Afterwards, in that same window, remove the setting** (cmd.exe: `set LC_TOOLS_SPEC=`; PowerShell: `Remove-Item Env:LC_TOOLS_SPEC`), or every later installer started from it fails the same way.

**Expect:** the installation still **finishes** and the app itself works; `menuinst_debug.log` contains `WARNING: tool registration failed - ...`; `list` does not show the app. (Remove that install afterwards.)

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

---

## 9. Operating-system specific checks
### Windows only
- [ ] **W1** The installer path contains a space (for example `C:\Users\Your Name\Apps\NucleiSky`) and installation, registration (S2) and a run still work. Notes: ______
- [ ] **W2** `menuinst_debug.log` has the registration lines described in S2 (Windows variant) and none of: `The syntax of the command is incorrect`, `was unexpected at this time`, `is not recognized`. Notes: ______
- [ ] **W3** The registered version is correct: `list` (S2) shows `NucleiSky  (0.1.1)` and **not** `(0)` or `(no version)`. Notes: ______
- [ ] **W4** Antivirus / SmartScreen did not block the worker (a run starts within 30 s of pressing Run). Notes: ______
- [ ] **W5** After closing Napari or Fiji, no `python.exe` of the app remains in Task Manager. Notes: ______
### macOS only
- [ ] **M1** Gatekeeper/notarisation: the installer starts after the usual "downloaded from the internet" confirmation; describe any extra step needed. Notes: ______
- [ ] **M2** Apple silicon and Intel (state which): Napari widget and Fiji both run NucleiSky with the N4 result. Notes: ______
### Linux only
- [ ] **L1** Napari under Wayland or X11 (state which): the widget is usable (no Qt platform error). Notes: ______

---

## 10. Report back
Send, in one message or issue titled `Test report: <OS> <your name> <date>`:
- [ ] this document with all boxes ticked and the record sheet filled in;
- [ ] screenshots of: N2 (the form), N4 (result), N6 (triangles message), F2 (Fiji form), F3 (overlay), and one screenshot per FAIL;
- [ ] the support bundle zip (test E5) if anything failed. **Open it first**: the logs and run records are not scrubbed of secrets; leave out or remove anything private;
- [ ] a short free-text answer to: *Was anything confusing, slow, or surprising even though the test passed?*

**Bug description template** (one per FAIL): Test number; what you did (exact clicks/commands); what you expected; what happened; severity; screenshot; support bundle attached (yes/no).

---

## Appendix A. Reference values (default NucleiSky settings, test data from `make_fixtures.py`)
| Quantity | Value |
|---|---|
| rotation | 12.17° (accept 12.0 to 12.4) |
| scale | 1.002 (accept 0.99 to 1.01) |
| nuclei found: reference / query | 429 / 9 |
| matcher chosen by `auto` | quad |
| with `li` threshold and min area 80 | 425 / 9 |
| with reference mask (and query mask) | 393 / 9 |
| `triangles` and `graph` | "No match found ..." (this is expected on these images) |
| time of a normal run | about 10 to 20 s (first run after installation up to 2 minutes) |

## Appendix B. What the author of this protocol did and did not verify
The commands, file names, expected texts and numbers were checked on **Linux** (Ubuntu 24.04, Python 3.12 app environments, Napari 0.9, Fiji with Java 21) with the real installers and the same fixtures,
driving Napari and Fiji from automated scripts rather than by hand. **Not verified:** any Windows or macOS step (including every Windows command here and the `.bat` installer hooks), the exact menu path of the Fiji script
(F0), the on-screen look of a real desktop session, the Napari `Plugins` menu wording on other Napari versions, and F10 (needs a real desktop). If a step in this document is wrong or unclear, please say so; that is a documentation bug.
