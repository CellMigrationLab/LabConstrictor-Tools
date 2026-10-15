# Human tests: CellTracksColab (a notebook app; no host shows it)

Part of the [human test protocol](../HUMAN_TEST_PROTOCOL.md): fill in its record sheet first. CellTracksColab analyses cell-tracking data in notebooks and is distributed as a desktop installer of its notebooks
(release 1.1.2). **Discovery: hidden in Napari, Fiji and QuPath (notebook only).** It is **not** a
host test app: earlier versions of this protocol used it as a second app in Napari and Fiji, that expectation is gone.

What is true today (checked in the repository, not by an installer run): `main` has no `<package>_lc_tools` module and its `post_install` hook has no Tools step, so a release built from `main` registers **no tools**;
a bridge exists only on the held branch `bridge-test` (one tool, "Calculate Track Metrics", which pins Tools from `main`, not a tag). The release sandbox tests CellTracksColab as "must be hidden" using that bridge on purpose; you do not need it.

## CT-1. Install and open the notebook
**Do:** install the latest release (protocol S0 and S1: a path without a space). Start the app from the menu or desktop and open a notebook it offers.
**Expect:** the installer finishes (last line of `menuinst_debug.log`: `Post-install completed successfully.`); the notebook opens in JupyterLab and its first cells run (what to run: see the notebook's own instructions; an analysis with your own data is outside this protocol).

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

## CT-2. No tools were registered
**Do:** `<APP_PY> -m labconstrictor_tools list` with the Python of CellTracksColab (or any other app's Python).
**Expect:** CellTracksColab is not in the list, `menuinst_debug.log` has no `lc_tools` lines and no `WARNING: tool registration failed`; `doctor` has no cross. (If your release does register a tool: write it down, it is a finding; D3 then decides whether the hosts hide it.)

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

## CT-3. Not offered in any host
This is test D3 of the protocol. With CellTracksColab installed next to another app: Napari (Rescan apps), Fiji (restart) and QuPath (Rescan apps) do not list it, show no error about it, and the other app still works. The host writes `'CellTracksColab' is not listed in <host>: the app declares hosts: notebook` to the Tools log and shows it wherever it reports left-out apps. This holds only once the installers pass `--app-manifest` (template 0.1.18 and the app sync are not merged yet): not verified until the apps are re-installed with an installer that passes the hosts. Record the result here too.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes (host): ______________________________

## CT-4. Uninstall leaves other apps alone
Test U2 of the protocol, with CellTracksColab as the app removed: the other app stays registered and runs.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________
