# Testing LabConstrictor: start here

You do not need to program. You install an app and a host (Napari, Fiji or QuPath), press the buttons, and tell us what happened.
This page is the whole job in one screen; the long protocol ([HUMAN_TEST_PROTOCOL.md](HUMAN_TEST_PROTOCOL.md)) is the detail behind it.

## 1. Pick what you test (see the [matrix](TEST_MATRIX.md))
Take the row of your operating system. **Windows and macOS matter most:** the automated checks run on Linux, so only you can find install
and window problems on your system. Intel Macs are not supported (tell us instead of testing).

| Level | Time | What |
|---|---|---|
| **A. Smoke** | 30 min | one app, one host: install, open the host, run one tool, uninstall |
| **B. Standard** | 2 h | level A for each app of your matrix row, in each host of your row |
| **C. Full** | half a day | everything in the protocol (ask first) |

Do level A first. If it fails, stop, report it, and do not go on to B.

## 2. What to install: exactly this set (round `alpha.3`)
Only these versions; older ones or `main` are not a test of this round.

| Item | Version | Where |
|---|---|---|
| Tools (installed by the apps) | `v0.3.0-alpha.1` | nothing to download |
| Napari plugin | `v0.1.0-alpha.3` | install line below |
| Fiji plugin | `v0.1.0-alpha.3`, file `labconstrictor-fiji-v0.1.0-alpha.3.jar` | [Fiji releases](https://github.com/CellMigrationLab/LabConstrictor-Fiji/releases/tag/v0.1.0-alpha.3) |
| QuPath plugin | `v0.1.0-alpha.3`, file `labconstrictor-qupath-v0.1.0-alpha.3.jar` | [QuPath releases](https://github.com/CellMigrationLab/LabConstrictor-QuPath/releases/tag/v0.1.0-alpha.3) |
| QuPath itself | **0.7.0** exactly | https://qupath.github.io |
| Napari itself | 0.9 or newer, Python 3.11+, Qt6 (`napari[pyqt6]`) | https://napari.org |
| Fiji itself | current "Fiji with Java" | https://fiji.sc |
| Guess the Condition | 0.0.1 | [releases](https://github.com/CellMigrationLab/GuessTheCondition/releases/tag/0.0.1) |
| Playground | 0.0.5 | [releases](https://github.com/CellMigrationLab/LabConstrictor-Playground/releases/tag/0.0.5) |
| VLab4Mic | 0.1.6 | [releases](https://github.com/CellMigrationLab/LabConstrictor-VLab4Mic/releases/tag/0.1.6) |
| NucleiSky | 0.1.4 | [releases](https://github.com/CellMigrationLab/NucleiSky/releases/tag/0.1.4) |
| CellTracksColab | 1.1.2 (notebook only; no host shows it, on purpose) | [releases](https://github.com/CellMigrationLab/CellTracksColab/releases/tag/1.1.2) |

Installer for each app: Windows `<App>-<version>-Windows-x86_64.exe`, Apple-silicon Mac `<App>-<version>-MacOSX-arm64.pkg`, Linux `<App>-<version>-Linux-x86_64.sh`.

Napari (in a new environment; Windows PowerShell activates with `.\napari-env\Scripts\Activate.ps1`):
```
python -m venv napari-env
source napari-env/bin/activate
pip install "napari[pyqt6]" https://github.com/CellMigrationLab/LabConstrictor-Tools/archive/refs/tags/v0.3.0-alpha.1.zip https://github.com/CellMigrationLab/LabConstrictor-napari/archive/refs/tags/v0.1.0-alpha.3.zip
napari
```
Fiji: put the `.jar` into `Fiji.app/plugins/` (remove any older `labconstrictor-fiji-*.jar`), restart Fiji, menu **Plugins > LabConstrictor > LabConstrictor Tools**.
QuPath: drag the `.jar` onto the QuPath window and restart; menu **Extensions > LabConstrictor tools...**.

## 3. Your computer, in three lines
* **Windows:** the installer is not signed: "Windows protected your PC" > *More info* > *Run anyway*. Install into a folder **without a space**
  (for example `C:\LabConstrictor\Playground`); the installer refuses a space. Commands below are for PowerShell.
* **macOS (Apple silicon):** the installer is not signed: *System Settings > Privacy & Security > Open Anyway*. Same rule: no space in the folder.
* **Linux:** `bash <installer>.sh -b -p ~/labconstrictor/<App>`; if Napari says `Could not load the Qt platform plugin "xcb"`, the `libxcb-*` packages are missing (write it down).
* **All:** installing takes 6 to 8 minutes (PyTorch apps: longer, and about 25 GB of free disk for NucleiSky or Playground); the window can look idle.

## 4. The steps (level A, for one app and one host)
1. **Install** the app (section 2 and 3). Check: `<APP_PY> -m labconstrictor_tools list` shows the app and `doctor` shows no cross
   (`<APP_PY>` is `<install folder>/bin/python` on Linux/macOS and `& "<install folder>\python.exe"` on Windows).   [S1 to S3]
2. **Open the host** and find the app in the list. Check it against the [matrix of who shows what](HUMAN_TEST_PROTOCOL.md#3-which-host-shows-which-app-the-discovery-matrix) (VLab4Mic is not in QuPath, CellTracksColab nowhere).   [D1]
3. **Run one tool** from the app's file in [human_tests/](human_tests/) (the first test of the host section is the normal run) and compare with **Expect**.
4. **Make one mistake on purpose** (the second test of the host section) and check that the message is understandable.
5. **Close the host.** No `python ... labconstrictor_tools serve` should stay in the Task Manager / Activity Monitor / `ps`.   [E5]
6. **Uninstall** the app (Windows: Apps & features; Linux/macOS: `bash <install folder>/uninstall.sh`).   [U2]

For each step tick PASS, FAIL or N/A in the protocol's box. A FAIL needs: what you did, what you expected, what happened, a screenshot.
**If something is unclear in these instructions, that is a documentation bug: tell us, it is not your mistake.**

## 5. Report back
One GitHub issue in [LabConstrictor-Tools](https://github.com/CellMigrationLab/LabConstrictor-Tools/issues) titled
`Test report: <OS> <your name> <date> alpha.3`, with:
* your row of the [matrix](TEST_MATRIX.md) filled in (PASS / FAIL / N/A per cell), and the computer details (OS and version, RAM, antivirus or proxy, admin rights);
* one line per FAIL (test number, what happened, severity) and the screenshots;
* if anything failed: the support bundle (`<APP_PY> -m labconstrictor_tools support-bundle --out bundle.zip`). **Open it first** and remove anything private.

Severity: **Blocker** (cannot install or start, data lost, or a wrong result with no warning) · **Major** (a feature does not work, or an error nobody can understand) · **Minor** (works but confusing) · **Cosmetic**.
