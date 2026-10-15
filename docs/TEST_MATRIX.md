# Human testing matrix — alpha.3

**Start here:** [TESTER_START_HERE.md](TESTER_START_HERE.md). This is the **assignment and coverage tracker**, not the step-by-step test script. The detailed steps and expected results are in [HUMAN_TEST_PROTOCOL.md](HUMAN_TEST_PROTOCOL.md) and the [app guides](human_tests/). Test **the exact alpha.3 releases** listed in the start page; record what is actually installed.

## How to divide the work

1. **Coordinator:** put a name against each *Must* (M) packet below. Ideally use distinct physical Windows and Apple-silicon Mac computers; reuse installations and test data between packets on the **same** computer. Put the report issue link in the table when it arrives. Nobody needs to complete every packet.
2. **Tester:** take **one packet ID** and follow its linked app guide(s). Do the ordinary successful run **and one understandable failure** for each app/host combination. Record the result using the [short report template](#copy-and-paste-report-template). If you cannot start, report **BLOCKED**, not PASS or N/A. You do **not** have to understand the long protocol in advance.
3. **Keep apps installed** until discovery, two-app coexistence and notebook/host checks on that computer are finished. **Uninstall last** in a designated lifecycle packet. Capture logs/support bundles **before** uninstalling.
4. **Coordinator:** a release is not human-tested simply because every row has a name. Verify completed Must results, all expected-hidden tests, cross-platform coverage, open failures and evidence. An unresolved Major/Blocker must be explicitly triaged, not turned into N/A.

**Status vocabulary:** `NOT RUN` (including unassigned), `IN PROGRESS`, `PASS`, `FAIL`, `BLOCKED` (prerequisite failed), `N/A` (genuinely not applicable, with reason). A correctly *absent* app is a **PASS** of a negative discovery test, never N/A. `Should` (S) means optional coverage, not permission to skip a Must test. A known defect is still FAIL.

**Time estimates** below are **hands-on estimates after the downloads and host installation**; first installs, PyTorch downloads, notebook computations and macOS/Windows security prompts can add substantial time. Do not promise a 30-minute end-to-end install. A packet may be divided further by app if needed.

## 1. Assignable test packets (coordinator fills this table)

| Packet | Priority | Computer / responsibility | Exact minimum checks | Hands-on time* | Owner | Status | Report issue |
|---|---|---|---|---|---|---|---|
| **W-INSTALL-A** | M | Windows, standard personal machine: Guess the Condition, Playground, VLab4Mic | `S0–S3` on each; `NB1–NB2`; versions `W2–W3` | 45–75 min | — | NOT RUN | — |
| **W-INSTALL-B** | M | Windows: NucleiSky and CellTracksColab | `S0–S3`, `NB1–NB2`; `CT-2` (bridge registered but host-hidden) | 30–75 min | — | NOT RUN | — |
| **W-NAPARI** | M | Windows Napari integration | `N0, D1`; `PG-1/2`, `GC-1/2/3`, `VL-N1/N2`; `D3`; native chooser + readable error | 60–100 min | — | NOT RUN | — |
| **W-FIJI** | M | Windows Fiji integration | `F0, D1`; `PG-1/2`, `GC-1/2/3`, `VL-F1`; `D3`; image calibration and file chooser | 60–100 min | — | NOT RUN | — |
| **W-QUPATH** | M | Windows QuPath 0.7.0 integration | `Q0, D1`; `PG-1/2`, `GC-1/2/3`, **VLab4Mic absent `D2`**, **CellTracksColab absent `D3`** | 60–100 min | — | NOT RUN | — |
| **W-EDGE** | M | Different Windows machine: managed/antivirus/proxy/no-admin **or** username with spaces | `W1–W5`; launch one app and one host; document permission/security prompts. No request to disable security controls | 30–75 min | — | NOT RUN | — |
| **M-INSTALL-A** | M | Apple-silicon Mac: Guess the Condition, Playground, VLab4Mic | `S0–S3`, `NB1–NB2` on each; `M1` | 45–75 min | — | NOT RUN | — |
| **M-INSTALL-B** | M | Apple-silicon Mac: NucleiSky and CellTracksColab | `S0–S3`, `NB1–NB2`; `CT-2` | 30–75 min | — | NOT RUN | — |
| **M-NAPARI** | M | macOS Napari integration | `N0, D1`; `PG-1/2`, `GC-1/2/3`, `VL-N1/N2`; `D3`; file chooser and result placement | 60–100 min | — | NOT RUN | — |
| **M-FIJI** | M | macOS Fiji integration | `F0, D1`; `PG-1/2`, `VL-F1/F2`, `D3`; `M2` (Fiji part) | 45–90 min | — | NOT RUN | — |
| **M-QUPATH** | M | macOS QuPath 0.7.0 integration | `Q0, D1`; `PG-1/2`, `GC-1/2/3`, **`D2`**, **`D3`**; `M2` (QuPath part) | 60–100 min | — | NOT RUN | — |
| **W-LIFECYCLE** | M | One Windows machine, **after other packets** | `U1` two usable apps together; `E5, NB5`; `E4` optional; `U2` uninstall only one and confirm other still runs | 25–45 min | — | NOT RUN | — |
| **M-LIFECYCLE** | M | One Mac, **after other packets** | `U1, E5, NB5, U2`; `M2` (Napari part if not already done) | 25–45 min | — | NOT RUN | — |
| **L-SPOTCHECK** | S | Linux, human desktop (CI already covers Linux logic) | `L1, L2`; Playground in Napari + Fiji + QuPath (`PG-1/2`); native dialogs; `E5` | 45–90 min | — | NOT RUN | — |
| **REAL-DATA** | S | Any platform; microscopy user | One real TIFF/image + calibration, ROI/channel selection, and output sanity check in a host; one genuine user workflow; privacy-safe screenshots | 30–60 min | — | NOT RUN | — |
| **ADVANCED-FAILURES** | S | Maintainer-controlled disposable test install only | `E1–E3` broken interpreter/missing dependency/worker crash; `U3–U4` updates and interrupted/offline installation. **Not for ordinary testers** | Variable | — | NOT RUN | — |

*If two packet owners use different machines, each must perform the necessary installations; do not treat a successful install on somebody else's computer as their result. Assign a **machine label** (e.g. W-01/M-01) in each report to match packets performed on the same setup. The same person may own multiple rows.

### Host × app coverage map

This is a coverage target, **not** a result table. Each cell says which packet owns it: `M` required, `S` optional follow-on, `—` not a host run. Results go into the packet's report. **Hidden** means an explicit, successful absence check with the app installed.

| OS / host | Guess the Condition | Playground | VLab4Mic | NucleiSky | CellTracksColab |
|---|---|---|---|---|---|
| **Windows / Napari** | M W-NAPARI | M W-NAPARI | M W-NAPARI | S W-NAPARI (`NS-N3/N4`) | **Hidden M W-NAPARI** |
| **Windows / Fiji** | M W-FIJI | M W-FIJI | M W-FIJI | S W-FIJI (`NS-F1/F3`) | **Hidden M W-FIJI** |
| **Windows / QuPath** | M W-QUPATH | M W-QUPATH | **Absent M W-QUPATH** | S W-QUPATH (`NS-Q1/Q2`) | **Hidden M W-QUPATH** |
| **Mac / Napari** | M M-NAPARI | M M-NAPARI | M M-NAPARI | S M-NAPARI (`NS-N3/N4`) | **Hidden M M-NAPARI** |
| **Mac / Fiji** | S M-FIJI (`GC-1/2/3`) | M M-FIJI | M M-FIJI | S M-FIJI (`NS-F1/F3`) | **Hidden M M-FIJI** |
| **Mac / QuPath** | M M-QUPATH | M M-QUPATH | **Absent M M-QUPATH** | S M-QUPATH (`NS-Q1/Q2`) | **Hidden M M-QUPATH** |
| **Linux / each host** | S | S L-SPOTCHECK | S (Napari/Fiji); **absent** in QuPath | S | **Hidden S** |

**Expected discovery** ([protocol `3](HUMAN_TEST_PROTOCOL.md#3-which-host-shows-which-app-the-discovery-matrix)): Guess the Condition, Playground and NucleiSky are offered in all three hosts; VLab4Mic is offered only in Napari and Fiji; **CellTracksColab 1.1.2 ships the `Calculate Track Metrics` bridge tool but its manifest says `hosts: [notebook]`**, so hosts must hide it. First verify the app was registered: otherwise the absence check is inconclusive. `D1` must only be marked PASS for apps actually installed on that machine; uninstalled/missing apps are NOT RUN or BLOCKED.

**Deliberately additional to the Must map:** NucleiSky scientific workflow in each host/OS is important but expensive. If the alpha round must validate scientific data rather than just bridge usability, promote at least **Windows/Napari NS-N3–N6** and **macOS/Fiji NS-F1–F4** to Must and allocate dedicated testers. Do not silently claim NucleiSky has been tested because it installed.

## 2. Installer and notebook coverage

The host packets **do not replace** installer tests: an installer uses different platform code on Windows and Mac. Each installation must record the exact release file, OS build, machine ID, prefix path, success/failure, `list` and `doctor` output and any security prompt.

| App | Windows installation | Apple-silicon installation | Main notebook (NB3 when feasible) | Minimum meaningful notebook check |
|---|---|---|---|---|
| Guess the Condition `0.0.1` | W-INSTALL-A | M-INSTALL-A | `GuessTheCondition` | `NB1, NB2`, demo-game workflow `NB3` optional |
| Playground `0.0.5` | W-INSTALL-A | M-INSTALL-A | `LabConstrictorPlayground` | `NB1, NB2`, `Check everything` (PG-1), `NB3` optional |
| VLab4Mic `0.1.6` | W-INSTALL-A | M-INSTALL-A | `VLab4Mic_main` | `NB1, NB2`, simulation `NB3` optional |
| NucleiSky `0.1.4` | W-INSTALL-B | M-INSTALL-B | `NucleiSky2DApp` | `NB1, NB2`; `NB3` optional / possibly long |
| CellTracksColab `1.1.2` | W-INSTALL-B | M-INSTALL-B | `CellTracksColab_TrackMate` | `NB1, NB2`; `NB3` requires sample TrackMate data; mark BLOCKED if assigned without data |

**Other packaged notebooks (Should only):** Guess the Condition: `GuessTheCondition_API_Example`; Playground: `Welcome`; VLab4Mic: `VLab4Mic_parameter_sweeps`; NucleiSky: `NucleiSky2DBenchmarking`, `NucleiSky2D_API_Workflow_Example`, `NucleiSky3DApp`, `NucleiSky3DBenchmarking`, `NucleiSky3D_API_Workflow_Example`; CellTracksColab: `CellTracksColab_Custom`, `CellTracksColab_Dimensionality_Reduction`, `CellTracksColab_Distance_to_ROI`, `CellTracksColab_TrackMate_Plate`, `CellTracksColab_Track_Clustering`, `CellTracksColab_Viewer`. `Welcome` is already covered by NB2 for *each* app.

**Notebook–host parity (`NB4`, Should):** choose one *deterministic* operation with fixed input, settings and seed (e.g. Playground square image or VLab4Mic same-image comparison); compare numeric values within declared tolerance. Paths, timestamps, autogenerated file names and UI representations need not be identical.

## 3. What testers should actually look for

| User-facing theme | Test / evidence | Why it matters |
|---|---|---|
| **First use** | Can a scientist find the host plugin and an app without terminal expertise? Note every unexpected dialog or menu path | Discoverability |
| **Data selection** | A native open/save chooser, drag-and-drop where supported, and a real TIFF/CSV | Scripted CI cannot reproduce real chooser behaviour |
| **Image semantics** | Calibration/pixel units, 2D vs multichannel, image dimensions, ROI/channel selection, correct overlay or output location | Prevent plausible-but-wrong scientific results |
| **Feedback** | Run/progress/cancel; a deliberate invalid input with a *readable, actionable* message; recovery after error | Avoid silent failures |
| **Interoperability** | A second app alongside the first, rescan after install/uninstall, outputs retained in intended location | Real usage has multiple apps |
| **Lifecycle** | Install on clean/non-clean machine, start/stop notebook server, shut down workers, uninstall without losing another app's results | Hidden background failures |
| **Accessibility** | Labels not cut off; usable scroll; controls visible on typical laptop display; keyboard focus and legible warning | Basic usability, not just correctness |

**Priority of evidence:** a one-sentence outcome plus **one screenshot when a step fails**; for numerical mismatches include the observed value and the expected value. Do not upload patient images, confidential data or untouched support bundles. Run `support-bundle` **while the app is still installed**, inspect/redact it, and share it only if it adds value. No screenshot is required for every PASS.

## 4. Copy-and-paste report template

Create **one GitHub issue per packet**, not one giant document per person: [new test-report issue](https://github.com/CellMigrationLab/LabConstrictor-Tools/issues/new). Title: `Human test [W-NAPARI] — Windows 11 — 2026-10-15` (replace the packet, OS and date). Multiple packets on one machine may share the environment details; link the first report.

```text
Packet ID:
Tester (name or GitHub handle):
Machine ID (e.g. W-01):
OS/build + CPU architecture:
RAM / free disk space:
Managed machine / admin restrictions / antivirus / proxy:
App release(s), installer filenames, install prefix(es):
Host version(s), plugin tag(s); Napari Python and Qt backend:
Clean first install or prior LabConstrictor installation?:

Results (one per assigned test; add rows):
- PG-1 / Windows / Napari: PASS | FAIL | BLOCKED | N/A | NOT RUN
  Expected:
  Observed:
  Evidence (screenshot/log/issue link):
- ...
- Negative discovery (when assigned): D2 or D3 = PASS only if absent as expected

Confusing / slow / surprising even when passing:
Defects: test ID, steps, expected vs observed, severity (Blocker/Major/Minor/Cosmetic), screenshot
Support bundle: not needed / collected and reviewed / linked privately (no secrets)
Tests NOT RUN or BLOCKED and why:
Would you recommend these instructions to another non-programmer? What was hard?
```

After fixing a bug, **retest the failed step on the same OS/host/app/release combination** and link that result to the original issue. A different platform passing does not close the failing cell.

## 5. Progress summary (maintainer updates)

| Milestone | Definition | Status |
|---|---|---|
| Windows installers | W-INSTALL-A and W-INSTALL-B complete; W-EDGE also documents a second computer | NOT RUN |
| macOS installers | M-INSTALL-A and M-INSTALL-B complete with exact Apple-silicon build | NOT RUN |
| Windows hosts | W-NAPARI, W-FIJI, W-QUPATH complete, including **negative discovery** | NOT RUN |
| macOS hosts | M-NAPARI, M-FIJI, M-QUPATH complete, including **negative discovery** | NOT RUN |
| Two apps / clean exit / uninstall | W-LIFECYCLE and M-LIFECYCLE complete | NOT RUN |
| Scientific NucleiSky | At least one measured result in two host/OS combinations (`Should` unless explicitly promoted) | NOT RUN |
| Real-data usability | At least one microscope user has tried a calibrated real image and reported their workflow | NOT RUN |

Automation on Linux is helpful background, but it is **not evidence that a human test passed**. The [release sandbox description](TESTING.md#release-sandbox-a-released-app-on-fresh-runners) describes its limits; do not interpret CI as Windows/macOS manual coverage.
