# Testing LabConstrictor: start here

You do not need to program. You install an app and a host (Napari, Fiji or QuPath), press the buttons, and tell us what happened.
This page is the starting point; the long protocol ([HUMAN_TEST_PROTOCOL.md](HUMAN_TEST_PROTOCOL.md)) is the detail behind it.

## 1. Choose your operating system and follow its checklist

You do not need to sign up for a separate host or work packet. **Choose [Windows, macOS or Linux in the testing table](TEST_MATRIX.md)**, write your initials next to the checks you perform, and report what worked and what did not. Ideally one person tests several apps on their own computer. Other volunteers may fill any remaining rows. You may stop and send partial results.

**Use this sequence:** install an app → open its notebook or a host → run its built-in demo → try one intentional error → record PASS, FAIL, BLOCKED or NOT TESTED. **Do not uninstall until all testing on that computer is done.** A missing test dataset means BLOCKED for the data-dependent step, not a failure of the installation.

**Data first:** [TEST_DATA.md](TEST_DATA.md) maps every test to the exact data it needs. Playground (P0), Guess the Condition (G0) and VLab4Mic (V0) can begin without downloaded TIFF files. NucleiSky's numerical matching check needs generated N1 TIFFs; CellTracksColab's full TrackMate notebook needs a validated C2 dataset, which has not yet been packaged.

## 2. Exact releases for this round (`alpha.4`)
Only these versions; older ones or `main` are not a test of this round.

| Item | Version | Where |
|---|---|---|
| Tools (installed by the apps) | `v0.3.0-alpha.1` | nothing to download |
| Napari plugin | `v0.1.0-alpha.4` | install line below |
| Fiji plugin | `v0.1.0-alpha.4`, file `labconstrictor-fiji-v0.1.0-alpha.4.jar` | [Fiji releases](https://github.com/CellMigrationLab/LabConstrictor-Fiji/releases/tag/v0.1.0-alpha.4) |
| QuPath plugin | `v0.1.0-alpha.4`, file `labconstrictor-qupath-v0.1.0-alpha.4.jar` | [QuPath releases](https://github.com/CellMigrationLab/LabConstrictor-QuPath/releases/tag/v0.1.0-alpha.4) |
| QuPath itself | **0.7.0** exactly | https://qupath.github.io |
| Napari itself | 0.9 or newer, Python 3.11+, Qt6 (`napari[pyqt6]`) | https://napari.org |
| Fiji itself | current "Fiji with Java" | https://fiji.sc |
| Guess the Condition | 0.0.1 | [releases](https://github.com/CellMigrationLab/GuessTheCondition/releases/tag/0.0.1) |
| Playground | 0.0.5 | [releases](https://github.com/CellMigrationLab/LabConstrictor-Playground/releases/tag/0.0.5) |
| VLab4Mic | 0.1.7 | [releases](https://github.com/CellMigrationLab/LabConstrictor-VLab4Mic/releases/tag/0.1.7) |
| NucleiSky | 0.1.4 | [releases](https://github.com/CellMigrationLab/NucleiSky/releases/tag/0.1.4) |
| CellTracksColab | 1.1.3 (bridge registered; `hosts: [notebook]`; host menus deliberately hide it) | [releases](https://github.com/CellMigrationLab/CellTracksColab/releases/tag/1.1.3) |

### Direct downloads (click, no searching on the release page)
Installers (take the one for your system; Intel Macs are not supported):

| App | Windows `.exe` | macOS Apple silicon `.pkg` | Linux `.sh` |
|---|---|---|---|
| Guess the Condition 0.0.1 | [download](https://github.com/CellMigrationLab/GuessTheCondition/releases/download/0.0.1/GuessTheCondition-0.0.1-Windows-x86_64.exe) | [download](https://github.com/CellMigrationLab/GuessTheCondition/releases/download/0.0.1/GuessTheCondition-0.0.1-MacOSX-arm64.pkg) | [download](https://github.com/CellMigrationLab/GuessTheCondition/releases/download/0.0.1/GuessTheCondition-0.0.1-Linux-x86_64.sh) |
| Playground 0.0.5 | [download](https://github.com/CellMigrationLab/LabConstrictor-Playground/releases/download/0.0.5/LabConstrictorPlayground-0.0.5-Windows-x86_64.exe) | [download](https://github.com/CellMigrationLab/LabConstrictor-Playground/releases/download/0.0.5/LabConstrictorPlayground-0.0.5-MacOSX-arm64.pkg) | [download](https://github.com/CellMigrationLab/LabConstrictor-Playground/releases/download/0.0.5/LabConstrictorPlayground-0.0.5-Linux-x86_64.sh) |
| VLab4Mic 0.1.7 | [download](https://github.com/CellMigrationLab/LabConstrictor-VLab4Mic/releases/download/0.1.7/VLab4Mic-0.1.7-Windows-x86_64.exe) | [download](https://github.com/CellMigrationLab/LabConstrictor-VLab4Mic/releases/download/0.1.7/VLab4Mic-0.1.7-MacOSX-arm64.pkg) | [download](https://github.com/CellMigrationLab/LabConstrictor-VLab4Mic/releases/download/0.1.7/VLab4Mic-0.1.7-Linux-x86_64.sh) |
| NucleiSky 0.1.4 (large) | [download](https://github.com/CellMigrationLab/NucleiSky/releases/download/0.1.4/NucleiSky-0.1.4-Windows-x86_64.exe) | [download](https://github.com/CellMigrationLab/NucleiSky/releases/download/0.1.4/NucleiSky-0.1.4-MacOSX-arm64.pkg) | [download](https://github.com/CellMigrationLab/NucleiSky/releases/download/0.1.4/NucleiSky-0.1.4-Linux-x86_64.sh) |
| CellTracksColab 1.1.3 | [download](https://github.com/CellMigrationLab/CellTracksColab/releases/download/1.1.3/CellTracksColab-1.1.3-Windows-x86_64.exe) | [download](https://github.com/CellMigrationLab/CellTracksColab/releases/download/1.1.3/CellTracksColab-1.1.3-MacOSX-arm64.pkg) | [download](https://github.com/CellMigrationLab/CellTracksColab/releases/download/1.1.3/CellTracksColab-1.1.3-Linux-x86_64.sh) |

Host plugins (the same files for every system):
* Fiji: [labconstrictor-fiji-v0.1.0-alpha.4.jar](https://github.com/CellMigrationLab/LabConstrictor-Fiji/releases/download/v0.1.0-alpha.4/labconstrictor-fiji-v0.1.0-alpha.4.jar) (checksums: [SHA256SUMS](https://github.com/CellMigrationLab/LabConstrictor-Fiji/releases/download/v0.1.0-alpha.4/SHA256SUMS))
* QuPath: [labconstrictor-qupath-v0.1.0-alpha.4.jar](https://github.com/CellMigrationLab/LabConstrictor-QuPath/releases/download/v0.1.0-alpha.4/labconstrictor-qupath-v0.1.0-alpha.4.jar) (checksums: [SHA256SUMS](https://github.com/CellMigrationLab/LabConstrictor-QuPath/releases/download/v0.1.0-alpha.4/SHA256SUMS))
* Napari: no file to download, it is installed with `pip` (below).

### Where each file goes
| What | Where | How you know it worked |
|---|---|---|
| **App installer** (`.exe` / `.pkg` / `.sh`) | run it; choose an install folder **without a space** | `<APP_PY> -m labconstrictor_tools list` shows the registered tools (including CellTracksColab's notebook-only tool) |
| **Napari plugin** (no JAR) | `pip install ...` into the Napari environment (the commands just below) | Napari: **Plugins > LabConstrictor tools** exists |
| **Fiji JAR** | into the folder `Fiji.app/plugins/` itself (not a subfolder); delete any older `labconstrictor-fiji-*.jar`; restart Fiji | menu **Plugins > LabConstrictor > LabConstrictor Tools** (if it is missing, type `LabConstrictor` into Fiji's search bar and tell us) |
| **QuPath JAR** | drag the file onto the open QuPath window, or copy it into the extensions folder shown in QuPath's Preferences; restart QuPath | menu **Extensions > LabConstrictor tools...** |

Two hints marked *not verified by us on that system*: on **macOS** `Fiji.app` is a folder you reach with right-click > *Show Package Contents* if
Finder treats it as an application; on **Windows** `Fiji.app` is the unzipped Fiji folder wherever you put it (do not run Fiji from inside the zip).

Napari, in a new environment (Windows PowerShell activates with `.\napari-env\Scripts\Activate.ps1`):
```
python -m venv napari-env
# macOS/Linux: source napari-env/bin/activate
# Windows PowerShell: .\napari-env\Scripts\Activate.ps1
python -m pip install "napari[pyqt6]" https://github.com/CellMigrationLab/LabConstrictor-Tools/archive/refs/tags/v0.3.0-alpha.1.zip https://github.com/CellMigrationLab/LabConstrictor-napari/archive/refs/tags/v0.1.0-alpha.4.zip
napari
```
On Windows, use PowerShell with its Windows activation command instead of `source`; if script execution is disabled, use `cmd.exe` with `napari-env\Scripts\activate.bat`. Then **Plugins > LabConstrictor tools** (press **Rescan apps** after installing an app).

## 3. Your computer, in three lines
* **Windows:** the installer may be unsigned and trigger SmartScreen. Check the file is from the intended release; use *More info > Run anyway* only if your local security policy permits it. Never disable antivirus or bypass organisation policy. Install into a folder **without a space**
  (for example `C:\LabConstrictor\Playground`); the installer refuses a space. Commands below are for PowerShell.
* **macOS (Apple silicon):** an unsigned installer may need *System Settings > Privacy & Security > Open Anyway*; proceed only after checking the release and respecting your security policy. Same rule: no space in the folder.
* **Linux:** `bash <installer>.sh -b -p ~/labconstrictor/<App>`; if Napari says `Could not load the Qt platform plugin "xcb"`, the `libxcb-*` packages are missing (write it down).
* **All:** installing takes 6 to 8 minutes (PyTorch apps: longer); the window can look idle.

**Disk budget (keep all apps installed until the end, so plan for it).** Measured on Linux: Guess the Condition 1.2 GB, VLab4Mic 1.5 GB; Playground and NucleiSky bring PyTorch
(about 9 GB installed each, and about 5 GB of download caches while installing; on Linux the installer fetches the CUDA build and **fails with exit code 1 when the disk fills**:
it did on a machine with 6 GB free). All five apps together need roughly **25 GB free for the apps plus 10 GB of caches while the last one installs**. Install in this order and stop when
the disk is short (say which apps you reached): Guess the Condition, VLab4Mic, CellTracksColab, Playground, NucleiSky. An app you could not install is **BLOCKED**, not FAIL.
**Linux without a GPU:** set `PIP_EXTRA_INDEX_URL=https://download.pytorch.org/whl/cpu` before running the Playground installer; it then picks the CPU build of PyTorch and finishes in about 2 minutes using about 2 GB (checked on Linux with Playground 0.0.5).

## Known issues (do not report these again; add details only if yours differs)
* **VLab4Mic 0.1.7:** the images `simulate_sample` writes carry no pixel size (type it when you compare them); the parameter-sweeps notebook probably ignores the folder chosen for saving until the upstream widgets package is fixed.
* **Fiji:** a pixel-size field follows the image's calibration and has no "use the image's calibration" button; typing the value the box already shows clears it and blocks the run; fields that do not apply are not greyed out ([HOST_FEATURES.md](HOST_FEATURES.md)).
* **Napari:** typing 0 in a pixel-size box resets it to the image's calibration and says so in the status line; it cannot reach the tool's own "invalid pixel size" message.
* **NucleiSky 0.1.4:** the two 3D notebooks have known faults, fixed on the main branch but not in this release: NucleiSky3DApp stops with a `NameError` (`plot_warp_overlay3D`) when you run it, and the 3D API workflow example ends with "Matching failed" on its own demo volume. A reference image containing NaN is accepted instead of refused.
* **Napari alpha.4:** the status line can keep the previous tool's warning after you pick another tool (fixed on main). **QuPath alpha.4:** a points CSV whose cell contains a line break can split into several points (fixed on main). **Fiji alpha.4:** after you stop a long run, a worker's child process can stay alive and a finished run can briefly show without its outputs (fix pending).
* **All hosts:** native file choosers cannot be tested by our automation: a chooser that does not open **is** worth reporting.
The full list of automated findings is in the `test-results` branch of this repository (`alpha2/FINDINGS.md`, `alpha3/FINDINGS.md`).

## 4. Basic workflow for each app and host you choose
1. **Install** the app (section 2 and 3). Check: `<APP_PY> -m labconstrictor_tools list` shows the app and `doctor` shows no cross
   (`<APP_PY>` is `<install folder>/bin/python` on Linux/macOS and `& "<install folder>\python.exe"` on Windows).   [S1 to S3]
2. **Open your preferred host** and find the app in the list. Check it against the [matrix of who shows what](HUMAN_TEST_PROTOCOL.md#3-which-host-shows-which-app-the-discovery-matrix) (VLab4Mic is not in QuPath, CellTracksColab nowhere).   [D1]
3. **Run one tool** from the app's file in [human_tests/](human_tests/) (the first test of your host's section in the app's file; for Playground in any host that is **Feature tour**, PG-2) and compare with **Expect**.
4. **Make one mistake on purpose** (the second test of the host section) and check that the message is understandable.
5. **When your packet includes notebook checks, open the app's notebook** (menu entry or desktop shortcut of the app): JupyterLab opens, `Welcome` runs without a red error, and the main notebook works on its demo data. [NB1 to NB3, which notebooks: [matrix](TEST_MATRIX.md#5-data-at-a-glance)]
6. **Close the host and shut down JupyterLab, if used.** Merely closing the browser tab does not stop Jupyter. Check that no app-owned worker or Jupyter server remains. Do not terminate unrelated Python processes. [E5, NB5]
7. **Do not uninstall yet**, until all the tests you plan on your computer are finished. Preserve the installation for another host and the two-app coexistence checks. [U1, U2]

For each test you attempt record PASS, FAIL, BLOCKED, N/A (with reason) or NOT TESTED in your packet report. A FAIL needs: what you did, what you expected, what happened, a screenshot.
**If something is unclear in these instructions, that is a documentation bug: tell us, it is not your mistake.**

## 5. Report back

The round is tracked in [issue #141](https://github.com/CellMigrationLab/LabConstrictor-Tools/issues/141): comment there with your initials and the rows you take, and post your report there.

Fill the rightmost column of **your operating system's [testing table](TEST_MATRIX.md)** (PASS / FAIL / BLOCKED / NOT TESTED / N/A, with a brief note) and post **one report per person/OS** in [LabConstrictor-Tools issues](https://github.com/CellMigrationLab/LabConstrictor-Tools/issues/new). Include your initials, OS version/architecture, app and host versions, and any antivirus/proxy restrictions. For each FAIL include what you clicked, expected and observed, and a screenshot. For BLOCKED say what prerequisite or test data was missing. A simple passing demo does **not** require a support bundle.

If useful, collect a support bundle before uninstalling (`<APP_PY> -m labconstrictor_tools support-bundle --out bundle.zip`), inspect it and remove anything sensitive before sharing. Don't upload private images or raw logs containing secrets.

Severity: **Blocker** (cannot install or start, data lost, or an unwarned wrong scientific result) · **Major** (a feature does not work or error is incomprehensible) · **Minor** (works but confusing) · **Cosmetic**.
