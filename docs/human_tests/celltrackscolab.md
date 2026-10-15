# Human tests: CellTracksColab (a notebook app; no host shows it)

Part of the [human test protocol](../HUMAN_TEST_PROTOCOL.md): fill in its record sheet first. CellTracksColab analyses cell-tracking data in notebooks and is distributed as a desktop installer of its notebooks
(release 1.1.3). **Discovery: hidden in Napari, Fiji and QuPath (notebook only).** It is **not** a
host UI test app: earlier versions of this protocol used it as a second app in Napari and Fiji, that expectation is gone.

**What is shipped in release 1.1.2 (verified in the tagged source):** the `celltracks_lc_tools` module declares **Calculate Track Metrics** (`calculate_metrics`), the installer pins Tools `v0.3.0-alpha.1` and registers the module with `--app-manifest`, and `labconstrictor-app.yaml` declares `hosts: [notebook]`. It **must be registered but not offered in Napari, Fiji or QuPath**. A missing registration is a failure even when it makes the hosts appear to hide the app. The actual installer behaviour remains to be verified by a human.

## CT-1. Install and open the notebook
**Do:** install the latest release (protocol S0 and S1: a path without a space). Start the app from the menu or desktop and open a notebook it offers.
**Expect:** the installer finishes (last line of `menuinst_debug.log`: `Post-install completed successfully.`); the notebook opens in JupyterLab and its first cells run (what to run: see the notebook's own instructions; a full TrackMate import needs a validated dataset that is not yet packaged: [TEST_DATA.md](../TEST_DATA.md#data-c1c2-celltrackscolab)).

- [ ] PASS  - [ ] FAIL  - [ ] BLOCKED  - [ ] N/A   Notes: ______________________________

## CT-2. Registered bridge, deliberately excluded from image hosts
**Do:** `<APP_PY> -m labconstrictor_tools list` with the Python of CellTracksColab (or any other app's Python).
**Expect:** `list` contains **CellTracksColab 1.1.3**, a `Calculate Track Metrics` tool and the notebook-only host declaration; `menuinst_debug.log` confirms installation and registration of `celltracks_lc_tools` without `WARNING: tool registration failed`; `doctor` is clean. This step **must pass before CT-3 can establish that host exclusion works**.

- [ ] PASS  - [ ] FAIL  - [ ] BLOCKED  - [ ] N/A   Notes: ______________________________

## CT-3. Not offered in any host
This is test D3 of the protocol. With CellTracksColab installed next to another app: Napari (Rescan apps), Fiji (restart) and QuPath (Rescan apps) do not list it, show no error about it, and the other app still works. The host writes `'CellTracksColab' is not listed in <host>: the app declares hosts: notebook` to the Tools log and shows it wherever it reports left-out apps. The 1.1.2 release source contains the manifest and the installer hooks that pass it; these behaviours must now be **tested**, not treated as future work. Check CT-2 first, or the absence in hosts could be a false PASS. Record the result here too.

- [ ] PASS  - [ ] FAIL  - [ ] BLOCKED  - [ ] N/A   Notes (host): ______________________________

## CT-4. Uninstall leaves other apps alone
Test U2 of the protocol, with CellTracksColab as the app removed: the other app stays registered and runs.

- [ ] PASS  - [ ] FAIL  - [ ] BLOCKED  - [ ] N/A   Notes: ______________________________
