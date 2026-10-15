# Install: an app and the three hosts

This is the one page that says how to install a LabConstrictor app and the programs that run its tools (Napari, Fiji, QuPath). The
installation instructions of the apps and the hosts are kept here and in the host repositories, not in the app repositories. For testing
you install exactly the versions of the [test set](HUMAN_TEST_PROTOCOL.md#0-record-sheet-the-test-set-fill-in-before-you-start); this page
describes how, the protocol says which versions.

Round `alpha.4`: Tools `v0.3.0-alpha.1`, Napari, Fiji and QuPath plugins `v0.1.0-alpha.4` (all three published; the full table of versions is in the [test set](HUMAN_TEST_PROTOCOL.md#01-the-test-set-round-alpha4-the-maintainer-updates-this-table-for-each-round)). A tester starts at [TESTER_START_HERE.md](TESTER_START_HERE.md).

## 1. Install an app (one click)
1. Download the installer for your system from the app's **GitHub Releases page** (Windows `.exe`, Apple-silicon Mac `.pkg` or `.sh`, Linux `.sh`; **Intel Macs are not supported**). Take the **exact release specified in the current test round**, not simply the newest available release. The apps: [Playground](https://github.com/CellMigrationLab/LabConstrictor-Playground/releases), [NucleiSky](https://github.com/CellMigrationLab/NucleiSky/releases), [VLab4Mic](https://github.com/CellMigrationLab/LabConstrictor-VLab4Mic/releases), [Guess the Condition](https://github.com/CellMigrationLab/GuessTheCondition/releases), [CellTracksColab](https://github.com/CellMigrationLab/CellTracksColab/releases) (a notebook app: no host shows it).
2. Run it. Installing takes 6 to 8 minutes for a small app and longer for the apps that bring PyTorch; the window may look idle. You need internet during the installation.
3. The installers are not code-signed: Windows says "Windows protected your PC" (More info, Run anyway); macOS refuses until you use System Settings > Privacy & Security > Open Anyway. Download only from the app's own release page.
4. The installer registers the app's tools for the hosts. Check: `<install folder>/bin/python -m labconstrictor_tools list` (Windows: `<install folder>\python.exe`) shows the app, and `doctor` shows no cross. CellTracksColab 1.1.2 **does register** `Calculate Track Metrics`, but its manifest specifies `hosts: [notebook]`; it should appear in `list` and be hidden in Napari, Fiji and QuPath.

**Install rules**
* **No space in the install path.** The installer refuses a path with a space (on Windows the wizard says `Destination Folder contains 1 space`). If your Windows user name has a space the default folder is refused: use `C:\LabConstrictor\<app>`; on macOS and Linux `~/labconstrictor/<app>`. Linux/macOS behaviour for a path with a space: not verified.
* **Updating.** macOS and Windows: uninstall the old version, then install the new one. Linux: `bash <installer>.sh -u -p <install folder>` updates in place **only if the previous install finished**; after a failed install delete `<install folder>/pkgs` (or uninstall) first.
* **Tagged versions only.** An app installs Tools from a tag (`LC_TOOLS_PIN` in its `post_install` hook), never from `main`; you install a tagged release of each host, never a `main.zip`. Releases are not moved or recreated ([OPERATIONS.md](OPERATIONS.md#releases-and-tags)). Install the explicitly pinned version of each item in the protocol's record sheet when testing a round.

## 2. What the hosts need
* **labconstrictor-tools 0.3.0a1 or newer in the app** (tag `v0.3.0-alpha.1`). Fiji and QuPath leave out an app with an older Tools (version below 0.3.0a1, or missing, or without the feature `reserved_inputs_v1`) with a sentence in the Log (`this app's labconstrictor-tools 0.2.0rc1 is older than the 0.3.0a1 this host needs: update it`); QuPath also refuses the run with it. The Napari plugin requires `labconstrictor-tools>=0.3.0a1`. Apps released before their pin was changed (pin `v0.2.0-rc.1`) are therefore not usable in Fiji and QuPath until they are re-released ([OPERATIONS.md](OPERATIONS.md#pinning-tools-in-app-installers)).
* **At least one registered app.** A host with no app says so; install an app, then press **Rescan apps** (Napari, QuPath) or restart Fiji.
* Which host shows which app is a separate rule ([HUMAN_TEST_PROTOCOL.md](HUMAN_TEST_PROTOCOL.md#3-which-host-shows-which-app-the-discovery-matrix)); installing a host does not install any app.

## 3. Napari
Python 3.11 or newer, in the environment you start Napari from. Use a **Qt6** backend: `napari[pyqt6]` (or `napari[pyside6]`); **not** `napari[pyqt5]` (PyQt5 is not tested and napari deprecated it in 0.8.0).

    python -m pip install "napari[pyqt6]" https://github.com/CellMigrationLab/LabConstrictor-Tools/archive/refs/tags/v0.3.0-alpha.1.zip https://github.com/CellMigrationLab/LabConstrictor-napari/archive/refs/tags/v0.1.0-alpha.4.zip

Both addresses are source archives of tags (no `git` needed); `v0.1.0-alpha.4` is the plugin tag of the test set (checked on Linux: both archives install). Then start Napari and choose **Plugins > LabConstrictor tools**. The plugin installs no Qt backend of its own.

## 4. Fiji
1. Download `labconstrictor-fiji-v0.1.0-alpha.4.jar` from the [LabConstrictor-Fiji Releases page](https://github.com/CellMigrationLab/LabConstrictor-Fiji/releases/tag/v0.1.0-alpha.4) (`SHA256SUMS` lists the checksums).
2. Put it into `Fiji.app/plugins/` (not a subfolder; remove an older `labconstrictor-fiji-*.jar`) and restart Fiji.
3. Run **Plugins > LabConstrictor > LabConstrictor Tools...**.

No-jar alternative: the same release has `labconstrictor-fiji-script-v0.1.0-alpha.4.zip` with the script `LabConstrictor_Tools.groovy` **and the `lib` folder it needs**; unzip it so both sit in `Fiji.app/scripts/Plugins/LabConstrictor/`; the entry is **Plugins > LabConstrictor > LabConstrictor Tools** (no dots). Macro calls need the jar. Install one of the two, not both. The release build/smoke evidence is not a replacement for human Windows/macOS checks; see the assigned matrix.

## 5. QuPath
QuPath **0.7.0** (built with Java 25; the jar needs it; other versions are not supported).
1. Download `labconstrictor-qupath-v0.1.0-alpha.4.jar` from the [LabConstrictor-QuPath Releases page](https://github.com/CellMigrationLab/LabConstrictor-QuPath/releases/tag/v0.1.0-alpha.4).
2. Drag it onto the QuPath window (or copy it into the extensions folder shown in QuPath's Preferences) and restart QuPath.
3. Run **Extensions > LabConstrictor tools...**.

Script Editor alternative: download the **single file** `LabConstrictorTools-all.groovy` from the same release, open it in QuPath's Script Editor and run it. The script in the repository is split into part files; only the all-in-one file from the release works in the Script Editor. Linux is tested in CI; macOS (Apple silicon) and Windows are tried by the release run and informative only.

## 6. Check it works
Open the host and look for the app in its list. If the list is empty or an app is missing: `labconstrictor-tools list` and `labconstrictor-tools doctor` in the app's Python say why (an interpreter that is gone, a Tools that is too old), and the log is `~/.labconstrictor/logs/labconstrictor.log` ([OPERATIONS.md](OPERATIONS.md#when-something-goes-wrong-logs)). To help test the integrations, follow the [human test protocol](HUMAN_TEST_PROTOCOL.md).
