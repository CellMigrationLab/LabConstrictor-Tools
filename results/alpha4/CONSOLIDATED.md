# One-off test round: summary across alpha.1 to alpha.4 (Linux, automated, real input events)

Detail: `RESULTS.md` and `FINDINGS.md` (alpha.1), `alpha2/`, `alpha3/`, `alpha4/` (each with RESULTS.md and FINDINGS.md). Screenshot gallery (private): https://claude.ai/artifact/8YCgwzJN3d6WRmN8PrVWvt

| Round | Hosts | Apps covered | Outcome |
|---|---|---|---|
| alpha.1 | Napari / Fiji / QuPath `v0.1.0-alpha.1` | Guess the Condition, CellTracksColab, Playground (source), NucleiSky and VLab4Mic generators | Run button enabled while running (Napari), Cancel did not cancel (Fiji), Run button did nothing (QuPath), sandbox design bugs (F-001..F-004, Windows trailing-space path), CTC and Playground app bugs |
| alpha.2 | `v0.1.0-alpha.2` | Guess the Condition 0.0.1, CellTracksColab 1.1.2, VLab4Mic 0.1.6, Playground 0.0.5 | Run button fixed in Napari and QuPath; Fiji Cancel partly fixed (FJ-1b); H-N4 stale-control errors; N-1 stray radio windows; VLab4Mic bugs VL-3..VL-13 |
| alpha.3 | `v0.1.0-alpha.3` | Guess the Condition, Playground, VLab4Mic (Napari and Fiji) | FJ-1b, H-N4, RGB chooser, typed-0 note, VL-7 fixed; N-1 isolated |
| alpha.4 | `v0.1.0-alpha.4` | VLab4Mic 0.1.7, CellTracksColab 1.1.3, NucleiSky 0.1.4 (full) | N-1 fixed; VL-5, A-CT1..3 fixed and re-verified; NucleiSky: 3D notebook NameError (NS-1), failing 3D demo (NS-2), NaN reference accepted (NS-3), outlines 1 px outside (NS-4) |

## Fix PRs produced by the rounds (state at 15 Oct 2026, evening)
Merged: Tools #138 #139 #140 #142 #143; Napari #64 #65 #66 #67; Fiji #50 #51 #52 #48; QuPath #38; Playground #33; VLab4Mic fork #19; CellTracksColab #63. Open for review: NucleiSky #41. Closed issues: Playground #31 #32; CellTracksColab #60 #61 #62.

## Still open after alpha.4
* NucleiSky NS-4 (outlines 1 px outside the image, from the shared outline helper in Tools), NS-1..NS-3 in NucleiSky #41.
* VL-3 (sweeps save folder, upstream `vlab4micjupyter`), VL-12 (output images without pixel size: Wave 2 item 5), VL-6 is a truth question.
* H-F1 (Fiji dialog sized 1066x3024 once under load, not reproduced), H-N5 (Napari status line keeps the previous tool's warning).
* Not covered by automation: Windows and macOS installers, native file choosers, Cellpose and InstanSeg, Cancel during long runs.
