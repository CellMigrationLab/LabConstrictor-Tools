# Human test checklist — alpha.3 (one volunteer per operating system)

**Volunteer workflow:** choose your OS, put your initials in its first column, download and install the exact [alpha.3 releases](TESTER_START_HERE.md#2-exact-releases-for-this-round-alpha3), and work down **your OS table**. You are welcome to cover only part of a table; leave the rest as **NOT TESTED** so another volunteer can pick it up. **No GitHub knowledge or programming required for the first tests.**

**Before you begin:** read the [short starter guide](TESTER_START_HERE.md) and [test-data guide](TEST_DATA.md). The first three apps need no external images. For precise imaging or tracking validation, use the data IDs below. **Do not download the DL4MicEverywhere branch in the user-provided example:** it concerns a different project and is **not** part of LabConstrictor alpha.3.

**Results:** write **PASS / FAIL / BLOCKED / NOT TESTED / N/A**, followed by what happened or a link to a screenshot/issue. PASS means you actually observed the expected result, not just that the application opened. **BLOCKED** means you could not do the test (including missing sample data). Only use **N/A** when a feature does not apply to the software or hardware. For an app that must be *absent* from a host, correctly absent = **PASS** if the app was first confirmed registered.

**Test set:** Playground 0.0.5; Guess the Condition 0.0.1; VLab4Mic 0.1.6; NucleiSky 0.1.4; CellTracksColab 1.1.2; Tools v0.3.0-alpha.1; host plugins v0.1.0-alpha.3; QuPath 0.7.0. Record the exact OS and versions actually used.

## 1. Windows — volunteer: ________  Windows version: ________

| Assignee | What needs to be tested | Test data / expected result | It works? Notes / issue |
|---|---|---|---|
| ___ | **W1. Install Playground** from the Windows .exe. Open the notebook from the desktop/menu; JupyterLab and Welcome launch. | No data; installation and notebook open (§S1, NB1/2§) | NOT TESTED |
| ___ | **W2. Install Guess the Condition**. Launch notebook; create a demo experiment, prepare it, play a round and analyse results. | **G0**: create 12 images (2 conditions × 3 repeats × 2). Different fresh experiment/results folders; §GC-1–7§ | NOT TESTED |
| ___ | **W3. Install VLab4Mic**. Launch notebook and simulate an STED image. | **V0**: built-in simulation; first-run structure retrieval may need internet. §VL-N2§ or notebook | NOT TESTED |
| ___ | **W4. Install NucleiSky**. Launch JupyterLab and Welcome; then check matching on a reference and query image. | **N1**: synthetic TIFF pair, generated as [explained here](TEST_DATA.md#data-n1-nucleisky-matching-fixtures), physical pixel sizes 0.65 / 0.325 µm; verify transformed output and expected rotation (§NS-0/N4§). If no fixture, report matching BLOCKED, not install PASS | NOT TESTED |
| ___ | **W5. Install CellTracksColab**. Launch JupyterLab and Welcome; open TrackMate notebook. | No data for launch. **C2** needed for full notebook import; report NB3 BLOCKED if no validated export (§CT-1§) | NOT TESTED |
| ___ | **W6. Check that all installed apps are registered correctly** with §list§ / §doctor§. | No data. **CellTracksColab must register Calculate Track Metrics** but declare notebook-only; see §CT-2§ | NOT TESTED |
| ___ | **W7. In Napari**, install alpha.3 plugin; find Playground and run **Check everything** and **Feature tour** twice. | **P0**: no image needed; expect system report, 16-blob demo, output replaced on rerun (§PG-1/2§) | NOT TESTED |
| ___ | **W8. In Napari**, play a Guess the Condition demo round and simulate a VLab4Mic image. | **G0 + V0**; sensible forms, progress, images, actionable errors; §GC-1–3, VL-N1/2§ | NOT TESTED |
| ___ | **W9. In Fiji**, install alpha.3 JAR and repeat Playground **Feature tour**, then one Guess the Condition game round. | **P0 + G0**; correct windows/ROIs, menus and results; §F0, PG-2, GC-1–3§ | NOT TESTED |
| ___ | **W10. In QuPath 0.7.0**, install alpha.3 JAR and repeat Playground **Feature tour**, then one Guess the Condition round. | **P0 + G0**; app chooser and results usable; §Q0, PG-2, GC-1–3§ | NOT TESTED |
| ___ | **W11. Check host discovery rules** in each installed host. | No data: Playground/Guess/NucleiSky listed in all hosts; VLab4Mic **not listed in QuPath**; CellTracksColab **not listed in any host**, although registered (§D1–D3§) | NOT TESTED |
| ___ | **W12. Check calibration, channels and scientific output** in at least one host. | **P1**: tagged TIFF/CSV fixtures; 16 pixels with 0.5 µm calibration = **4 µm²**, with 0.25 µm = **1 µm²** (§PG-5/7/8/9§) | NOT TESTED |
| ___ | **W13. Make a deliberate mistake** (missing pixel size or invalid/empty input); close and relaunch a host. | **P1** or **N1**: understandable error and recovery; no surviving app-owned worker after host close (§PG-4, E5§) | NOT TESTED |
| ___ | **W14. Test two apps together**, then uninstall **one** after finishing other tests. | No data: remaining app still starts and runs, registry clean (§U1/2§). **Do this last.** | NOT TESTED |
| ___ | **W15. Windows-specific issues**: unsigned installer/SmartScreen, spaces in install path, antivirus, missing permissions, no orphan Python after shutdown. | No data (§W1–W5§ in protocol); do not disable organisation security controls. Path-refusal check is optional on a **disposable install**, not required on a personal setup | NOT TESTED |

## 2. macOS Apple silicon — volunteer: ________  Mac model / macOS: ________

| Assignee | What needs to be tested | Test data / expected result | It works? Notes / issue |
|---|---|---|---|
| ___ | **M1. Install Playground** .pkg; start notebook and Welcome. | No data (§S1, NB1/2§); note Gatekeeper behaviour and whether a signed-install warning is understandable | NOT TESTED |
| ___ | **M2. Install Guess the Condition**, run the demo game and inspect analysis. | **G0**: built-in 12-TIFF demo; §GC-1–7§ | NOT TESTED |
| ___ | **M3. Install VLab4Mic**, launch notebook, simulate a microscopy image. | **V0**; note network request or MPS/GPU/CPU message; §VL-N2§ | NOT TESTED |
| ___ | **M4. Install NucleiSky**, open notebook; test image registration if fixture available. | **N1**, 0.65/0.325 µm synthetic TIFF pair and numeric result (§NS-0/N4§); no fixture = registration BLOCKED | NOT TESTED |
| ___ | **M5. Install CellTracksColab**, open Welcome and TrackMate notebook; check registered but hidden tool. | No data for launch/registry; **C2** needed for main notebook import (§CT-1/2§) | NOT TESTED |
| ___ | **M6. Check registry and doctor** for all five installed apps. | No data; CellTracksColab registered notebook-only; no registration failures (§S2/3§) | NOT TESTED |
| ___ | **M7. Napari**: install alpha.3 plugin, run Playground Feature tour twice, one Guess round and VLab4Mic simulation. | **P0 + G0 + V0**; replace outputs correctly, menus and progress (§PG-1/2, GC-1–3, VL-N1/2§) | NOT TESTED |
| ___ | **M8. Fiji**: install alpha.3 JAR, run Playground Feature tour and VLab4Mic comparison/simulation. | **P0 + V0**; for numerical comparison use **V1**, not a random TIFF (§F0, PG-2, VL-F1/2§) | NOT TESTED |
| ___ | **M9. QuPath 0.7.0**: install alpha.3 JAR, run Playground Feature tour and one Guess round. | **P0 + G0**; output, preview and UX (§Q0, PG-2, GC-1–3§) | NOT TESTED |
| ___ | **M10. Test host discovery** in each installed host. | No data: CellTracksColab excluded from all hosts; VLab4Mic excluded from QuPath; others shown (§D1–D3§) | NOT TESTED |
| ___ | **M11. Test image calibration**, native file chooser, channel selection, output placement and a deliberately bad input. | **P1**: square TIFF/three-channel TIFF; physical area 4 µm² at 0.5 µm/pixel (§PG-5/7/8§) | NOT TESTED |
| ___ | **M12. Close the notebook and host**, check cleanup; then uninstall **one app last**. | No data: explicitly shut down JupyterLab, not just browser tab; no orphan workers; another installed app remains usable (§NB5, E5, U1/2§) | NOT TESTED |
| ___ | **M13. Mac-specific observations**: Gatekeeper, app shortcuts, menu text, ARM64/Metal support, display or window sizing. | No data (§M1/2§); record limitations; do not bypass institutional controls | NOT TESTED |

## 3. Linux — volunteer: ________  Distribution / desktop: ________

| Assignee | What needs to be tested | Test data / expected result | It works? Notes / issue |
|---|---|---|---|
| ___ | **L1. Install Playground**, launch JupyterLab, run Check everything and Feature tour from a host. | **P0**, no data; 16-blob demo and clean result (§S1, PG-1/2§) | NOT TESTED |
| ___ | **L2. Install Guess the Condition**, generate demo and play one game. | **G0**; 12 synthetic TIFF images; §GC-1–7§ | NOT TESTED |
| ___ | **L3. Install VLab4Mic**, simulate an image; note CPU/CUDA, if available. | **V0**: no input TIFF; internet may be necessary | NOT TESTED |
| ___ | **L4. Install NucleiSky**, start notebook and check a known registration. | **N1** reference/query generated TIFFs; 0.65/0.325 µm (§NS-0/N4§) | NOT TESTED |
| ___ | **L5. Install CellTracksColab**, start notebook and verify bridge registered but hidden. | No data for registration and visibility; **C2** only for complete TrackMate import (§CT-1–3§) | NOT TESTED |
| ___ | **L6. Test Napari + alpha.3 plugin** with Playground and one other app. | **P0 + G0 or V0**; note Qt6, Wayland/X11, menus and workers (§N0, L1§) | NOT TESTED |
| ___ | **L7. Test Fiji + alpha.3 JAR** with Playground. | **P0**; windows, results, correctly handled errors (§F0, PG-2/4§) | NOT TESTED |
| ___ | **L8. Test QuPath 0.7.0 + alpha.3 JAR** with Playground. | **P0**; output placement and chooser (§Q0, PG-2§) | NOT TESTED |
| ___ | **L9. Discovery and calibration checks** across installed hosts. | No data for hidden hosts; **P1** TIFFs for calibration (§D1–D3, PG-8§) | NOT TESTED |
| ___ | **L10. Shutdown and uninstall** after testing, with another app still installed. | No data; keep other app working; no remaining app-owned worker (§NB5, E5, U1/2§) | NOT TESTED |
| ___ | **L11. Linux-specific observations**: X11/Wayland, permissions, installer paths, file chooser, missing Qt plugins. | No data (§L1/2§). Path-space test only in an expendable installation | NOT TESTED |

Linux automation provides useful coverage, but **does not count as a human PASS** for the rows above. A volunteer may reasonably prioritise Windows or macOS, where desktop behaviour has less manual evidence.

## 4. Optional deeper tests — on any OS

These are **not** prerequisites for saying that the ordinary application launches and the default demo works. Assign when someone has suitable expertise, data or time.

| Assignee | What needs to be tested | Test data and objective | It works? Notes / issue |
|---|---|---|---|
| ___ | **Full Playground bridge feature tour**: channels, ROI, dependent settings, calibration, transforms, CSV, cancel, errors | **P1**, app guide [PG-3 to PG-12](human_tests/playground.md#pg-3-feature-tour-on-a-chosen-image-selection-look-for) | NOT TESTED |
| ___ | **NucleiSky scientific reference** in Napari/Fiji/QuPath, match numerical transform and image placement | **N1**, generated reference/query, optional masks, ground truth; [NucleiSky guide](human_tests/nucleisky.md) | NOT TESTED |
| ___ | **VLab4Mic image comparison**: identical vs unrelated, flat and stack rejection, image units | **V1**, generated TIFFs and optional mini-ring CIF; [VLab4Mic guide](human_tests/vlab4mic.md) | NOT TESTED |
| ___ | **CellTracksColab bridge calculations** via CLI, independently verify track metrics | **C1** simple known-track CSV and [cases](https://github.com/CellMigrationLab/CellTracksColab/blob/1.1.2/lc_tests/cases.json); this is **not** a Napari/Fiji/QuPath tool | NOT TESTED |
| ___ | **CellTracksColab full TrackMate notebook** including import, plots and output | **C2** validated dataset **not yet packaged**; provide sample and expected results or report BLOCKED | NOT TESTED |
| ___ | **Real microscopy example** with meaningful calibration, channel and ROI choices | **R1**, keep private scientific data locally, report observations without uploading sensitive files | NOT TESTED |
| ___ | **Maintainer-only destructive tests**: deliberately break app Python, dependencies, worker, upgrade or offline installation | Disposable machine/environment only; [protocol E1–E3, U3/4](HUMAN_TEST_PROTOCOL.md#8-when-something-is-wrong-these-tests-change-an-app-do-them-last-and-restore-afterwards) | NOT TESTED |

## 5. Data at a glance

**Most important:** a volunteer should never need to find a test dataset without being told which one.

| ID | Origin | Where to get it |
|---|---|---|
| **P0** | Built-in Playground feature demo | No download |
| **G0** | Guess the Condition's own Create a demo experiment | No download; supply empty folders |
| **V0** | VLab4Mic built-in simulation | No input TIFF; network may be needed |
| **P1** | Tagged Playground synthetic test files | [Source ZIP](https://github.com/CellMigrationLab/LabConstrictor-Playground/archive/refs/tags/0.0.5.zip) → `lc_tests/fixtures/data` |
| **N1** | NucleiSky synthetic nuclei/matching test | [Generator and OS commands](TEST_DATA.md#data-n1-nucleisky-matching-fixtures) |
| **V1** | VLab4Mic known comparison images | [Generator](TEST_DATA.md#data-v1-vlab4mic-image-comparison) |
| **C1** | Two-track bridge CSV | [Direct CSV](https://raw.githubusercontent.com/CellMigrationLab/CellTracksColab/1.1.2/lc_tests/fixtures/tracks.csv) |
| **C2** | Full TrackMate notebook test | **Not packaged/validated yet** — see [dataset gap](TEST_DATA.md#data-c1c2-celltrackscolab) |
| **R1** | A volunteer's shareable real workflow | Keep files local; do not upload private images |

The complete instructions, expected values and scientific test limitations are in [TEST_DATA.md](TEST_DATA.md).

## 6. How to report

**One report per OS/tester is enough.** Fill the last column of your OS table (or copy the rows you tested) and [open one issue here](https://github.com/CellMigrationLab/LabConstrictor-Tools/issues/new). Suggested title: `Human testing alpha.3 — Windows 11 — <initials>`.

Record: tester initials; OS/version/architecture; app/host release versions; whether the machine had older LabConstrictor installs; any antivirus/proxy/admin restrictions; each test's result; a screenshot and expected-versus-observed description for any FAIL; which data ID was used; whether a test was **BLOCKED** because data was missing; and any confusing interface behaviour even when it worked. You do **not** need a support bundle for a passing test. Inspect/redact bundles before sharing.

A **FAIL** is a feature malfunction or wrong result; **BLOCKED** is an unmet prerequisite; **NOT TESTED** is a row no one has attempted; **N/A** is truly not relevant. If installation fails, report downstream tests as **BLOCKED**, never PASS.

**Keep installed apps until you have finished all testing on that computer; uninstall only at the end.** If testing one app uninstalls or breaks another, that is a failure.

## 7. Maintainer follow-up

The tester-facing download experience will improve substantially with **one small, versioned fixture ZIP** containing P1, N1, V1, C1 and a validated C2 TrackMate example, with checksums and expected output. This **has not been published yet**, so the guide uses verified tagged sources and generators, and does not invent a bundle link. Fix any stale or ambiguous wording in the test guides before declaring the round finished.

The existing [detailed protocol](HUMAN_TEST_PROTOCOL.md) and [per-app procedures](human_tests/) remain available as reference; **they are not required reading before a first smoke test**.
