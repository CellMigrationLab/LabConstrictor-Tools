# Test matrix: who tests what (round `alpha.3`)

Share this page with the team. Each tester takes the rows of one operating system, fills in the cells with `PASS`, `FAIL` or `N/A`, and
pastes the filled table into the test-report issue ([TESTER_START_HERE.md](TESTER_START_HERE.md), section 5). Install instructions, the
exact versions and the steps are in that page; the test numbers (S1, D1, E5 ...) are those of [HUMAN_TEST_PROTOCOL.md](HUMAN_TEST_PROTOCOL.md).

**Must** (M) = the round is not finished without it. **Should** (S) = do it if you have time. `-` = nothing to test.

## 1. What the automated checks already cover (so you need not repeat it)
The one-off audit ran on **Linux only**, with real clicks and key presses, on the released host files, one app at a time and with two apps
installed together: the sandbox checks of each app, every button of the three hosts' plugins for Guess the Condition, Playground and
VLab4Mic, every packaged notebook of the apps, the synthetic datasets with known answers, and the rule that CellTracksColab is shown in no host.
(Results: the `test-results` branch of this repository.) It cannot see:

* **Windows and macOS**: the installers, SmartScreen / Gatekeeper, paths, antivirus, the three hosts on those systems;
* **native file choosers and drag and drop** (a script cannot drive them);
* **how it looks and feels**: truncated labels, windows off screen, confusing messages, slow starts;
* **your own data**: real images, big files, odd calibrations, the tools used the way you would use them in a project.

So: spend your time on those four things, not on pressing every button in order.

## 2. Install matrix (every app, once per operating system)
Steps S1 to S3, then U2 (uninstall). Different installer on each system, so each cell is a real test.

| App (version) | Windows | macOS (Apple silicon) | Linux |
|---|---|---|---|
| Guess the Condition 0.0.1 | M | M | S |
| Playground 0.0.5 | M | M | S |
| VLab4Mic 0.1.6 | M | M | S |
| NucleiSky 0.1.4 (large: PyTorch) | S | S | S |
| CellTracksColab 1.1.2 (notebook only) | M | M | S |

## 3. Host matrix (host x app, per operating system)
Level A of the start page for each cell marked M; level B means the whole app file of [human_tests/](human_tests/) for the cells marked S.

| Host | Guess the Condition | Playground | VLab4Mic | NucleiSky | CellTracksColab |
|---|---|---|---|---|---|
| Napari | Windows M, macOS M, Linux S | Windows M, macOS M, Linux S | Windows M, macOS S, Linux S | Windows S, macOS S | must be **hidden** (D3): Windows M, macOS M |
| Fiji | Windows M, macOS M, Linux S | Windows M, macOS S, Linux S | Windows S, macOS S | Windows S | must be **hidden** (D3): Windows M |
| QuPath 0.7.0 | Windows M, macOS S, Linux S | Windows S, macOS S | must be **not listed** (D2): Windows M, macOS S | Windows S | must be **hidden** (D3): Windows M |

Reading the cells: "Windows M, macOS S" means the Windows tester must do it and the macOS tester should if time allows. An empty cell is optional.

## 4. Checks for your operating system
Do the ones for your system (the full wording is in section 9 of the protocol).

| Windows | macOS (Apple silicon) | Linux |
|---|---|---|
| **W1** an install path with a space is refused with a sentence | **M1** the installer opens after the Gatekeeper "Open Anyway" step; note any extra step | **L1** Napari opens without a Qt platform error (say Wayland or X11) |
| **W2** `menuinst_debug.log` has the registration lines and no `syntax of the command is incorrect` / `is not recognized` | **M2** Napari, Fiji and QuPath each run an app of the set | **L2** an install path with a space: write down exactly what the installer prints |
| **W3** `list` shows the real version, not `(0)` | | |
| **W4** SmartScreen / antivirus does not block the worker (a run starts within 30 s of pressing Run) | | |
| **W5** no `python.exe` of the app is left after closing a host | **E5** the same with Activity Monitor | **E5** the same with `ps aux \| grep '[l]abconstrictor_tools.*serve'` |

For every system also: **E5** (nothing left after closing), **U1** (two apps side by side in one host session), **U2** (uninstall one app, the other keeps working).

## 5. Who takes which row (fill in)
| Row | Tester | Computer (OS version, RAM, antivirus / proxy) | Date | Report issue |
|---|---|---|---|---|
| Windows 10/11 | | | | |
| Windows (second machine, e.g. managed or with a space in the user name) | | | | |
| macOS Apple silicon | | | | |
| Linux | | | | |

Two Windows rows are worth having: a plain machine, and one that is managed (antivirus, no admin) or whose user name has a space; that is where installers fail.
