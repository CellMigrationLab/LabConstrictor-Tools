# Clean-sandbox test of the LabConstrictor tools bridge (Linux)

Tester: Claude (AI agent), as a brand-new user `newuser`. Protocol followed: `docs/HUMAN_TEST_PROTOCOL.md` on `main` of LabConstrictor-Tools (fetched raw). No source was edited, nothing was pushed, no PR was opened.

## 1. Environment

| Item | Value |
|---|---|
| OS | Ubuntu 24.04.5, kernel 6.18.44, x86_64, 4 CPU, 15 GB RAM, no GPU, X11 only (Xvfb 1600x1000x24) |
| Python | NucleiSky app 3.12.13; CellTracksColab app 3.12.x; Napari env (`python3 -m venv`) 3.13.16; Napari 0.9.2, PyQt5 5.15.11 |
| Fiji | "Fiji with Java" latest (ImageJ 2.18.0/1.54p, Java 21.0.7), unzipped to `~/Fiji` |
| NucleiSky | `bridge-test` @ `d12f3b42f8199500e235f32657a45d6f4834287f` |
| CellTracksColab | `bridge-test` @ `64a709d23f27231b06bc239f9b5ef580a5fcaee6` |
| LabConstrictor-Tools `main` head | `f1e46e8be074df8c0d71d8d1c16e2cee12122f81` (PR 12 "Protocol and small fixes after the clean-sandbox walk-through") |
| LabConstrictor-Fiji `main` (jar build, F12) | `b5ccb43ecc7a558bf4a141c41af4ef358c8f091e` |
| Installers (built here) | `NucleiSky-0.1.1-Linux-x86_64.sh` 224,704,746 bytes; `CellTracksColab-1.1.0-Linux-x86_64.sh` 217,618,690 bytes |
| Build (constructor 3.17.3, micromamba env) | CellTracksColab: 12 s (pip+bump) + **56 s**; NucleiSky: 0 s + **29 s** (second build; the conda package cache was already warm from the first, so 29 s is not a cold number) |
| Install as plain user | NucleiSky `-b -p ~/ns`: **6 min 02 s** (installed folder 8.8 GB; `~/.cache` 4.5 GB, as the protocol says). CellTracksColab: **1 min 02 s** |
| Free disk at start | 30 GB; at the end 11 GB left |

**Test-environment setup (not part of the product):**
* Proxy CA: `install -m 644 /root/.ccr/ca-bundle.crt /home/proxy-ca.pem`; every step ran as `newuser` through `runuser -u newuser -- env … SSL_CERT_FILE/REQUESTS_CA_BUNDLE/PIP_CERT/CURL_CA_BUNDLE/GIT_SSL_CAINFO=/home/proxy-ca.pem`. Certificate checks were never disabled; `HTTPS_PROXY` untouched. No certificate failure occurred after that.
* The container itself exports `PYTHONUNBUFFERED=1`; my wrapper removes it (`env -u`), so `env | grep -E '^(LC_|PYTHON)'` is empty for the user.
* apt packages installed as root: `libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-render-util0 libxcb-xinerama0 libxcb-xkb1 libxkbcommon-x11-0 libxcb-shape0 libxcb-cursor0 xdotool x11-utils imagemagick xclip unzip python3-venv python3-pip libgl1 libegl1 libdbus-1-3 libfontconfig1`; **in addition** `openbox` (a window manager, needed so Java receives keyboard focus: without it Esc never reached Fiji, see F7) and `maven` (F12, jar build). I installed the Qt libraries up front, so I cannot say whether Napari starts without them.
* Micromamba (6.9 MB) was downloaded from `micro.mamba.pm` for the build.
* Order deviation: N0 (Napari env) was created before S1 (it does not depend on the installers). The Fiji script was in place before Fiji's first start, so "one restart" was folded into later restarts (the menu entry was present at the first start; also after two later restarts).

**What was automated, and how**
* Napari: a Python/Qt driver in the Napari environment under `xvfb-run`. It really opens the plugin through the Plugins menu action, opens images with `viewer.open()` (instead of the File dialog), sets form values (including the "or file" fields via `.value`, instead of the file dialog behind *Select file*), and clicks the real **Run / Cancel / Restart worker / Rescan** buttons with `QPushButton.click()`. It reads the status line, layers and tables from the widget. Screenshots are `QMainWindow.grab()`.
* Fiji: real mouse and keyboard through `xdotool` on a persistent Xvfb display, with screenshots by ImageMagick `import` and the Log/table text read through the clipboard (`ctrl+a`, `ctrl+c`, `xclip`). Images were opened with the real File > Open dialog (GTK), files chosen with the real "Open"/"Choose a file" dialogs (path typed with ctrl+L). Menu path was read from a screenshot of the opened menu. Nothing was done with Fiji's own scripting or the project's test harness.
* Not done by hand: nothing was clicked by a human; nothing was seen on a real desktop.

## 2. Results table

D = DEMONSTRATED (I ran it and saw it), I = INFERRED (did not run).

| Id | Result | D/I | Note |
|---|---|---|---|
| Sec. 2 test data | PASS | D | last line `ok (1600, 1600) (520, 520)`; `reference.tif` 5,120,256 B (5.1 MB), `query.tif` 541,056 B (0.5 MB); extra `*_binary`/`*_fractions` files as stated |
| S1 | PASS | D | no extra variables; log last line `Post-install completed successfully.` |
| S2 | PASS | D | `Found nucleisky_lc_tools: registering the tools of NucleiSky for Napari and Fiji`, `Successfully installed labconstrictor-tools-0.1.0`, `Tools registered (labconstrictor-tools list shows them).`; no `WARNING: tool registration failed`; `list` shows `NucleiSky  (0.1.1)` / `relocalize               Relocalize 2D` |
| S3 | PASS | D | CellTracksColab log has the same lines (`celltracks_lc_tools`); `list` shows `CellTracksColab  (1.1.0)` + `calculate_metrics        Calculate Track Metrics` and `NucleiSky  (0.1.1)` |
| S4 | PASS | D | `✔ CellTracksColab    1 tool(s), schema current, interpreter /home/newuser/ct/bin/python (0.05 s)`, same for NucleiSky; registry and log lines present |
| S5 | PASS | D | only LabConstrictor folder is `~/.labconstrictor` (apps, logs, runs, results). Extra items seen: `.cache .conda .mamba .config(gtk-3.0, matplotlib, menus, napari) .local/share(applications, desktop-directories, mime) .java .imagej .cellpose .m2`; `~/.config/menus/applications.menu.<date>` backup exists. Two items are **not** in the protocol list: `~/.local/share/applications/fiji.desktop` (written by Fiji at first start) and `~/.m2` (only because I built the jar for F12). `.conda/.mamba/.cache` already existed before the installers because of my build step |
| C1 | PASS | D | `"status": "COMPLETE"`, table; `(results are in …)` is the last line **in a terminal** (it is on stderr: when output is piped it comes first); `table.csv` has the header and 2 data rows |
| C2 | PASS | D | `"status": "FAILED"`, `"code": "unreadable_image"`, `"error": "[unreadable_image] cannot read fake.tif: not a TIFF file: header=b'hell'"`; exit code 1; **no empty folder** left in `~/.labconstrictor/results/` |
| N0 | PASS | D | commands exactly as printed; Napari 0.9.2; install 1 min 17 s; Plugins menu entry `LabConstrictor tools (LabConstrictor)`; PyQt5 deprecation notice appears ("napari support for the PyQt5 backend is deprecated and will be removed in fall of 2026") |
| N1 | PASS | D | apps `['CellTracksColab', 'NucleiSky']`; buttons Run, Cancel (disabled), Rescan apps, Restart worker, Details… (disabled), reuse box ticked. (The dock opens on CellTracksColab, the first item) |
| N2 | PASS | D | headings Images, Segmentation, Matching; all labels and defaults as listed (0.6500, 0.3250, threshold, otsu, 1.0000, 5, watershed ticked, auto); InstanSeg fields disabled; screenshot |
| N3 | PASS | D | layers `reference`, `query`; pixel sizes stay 0.65 / 0.325 (images opened with `viewer.open`, not the File dialog) |
| N4 | PASS | D | `✔ done in 12.0s  rotation_deg=12.1721, scale=1.0024, offset_y_px=700.3293, offset_x_px=605.5654, bbox_y0y1x0x1=[637, 963, 597, 923], n_nuclei_reference=429, n_nuclei_query=9, matcher=quad`; layers `NucleiSky:alignment`, `NucleiSky:query_aligned`; Run enabled, Details enabled. First Napari run 12.9 s wall (no 2-minute compile). Protocol text omits `offset_y_px=…, offset_x_px=…` |
| N5 | PASS | D | numeric check: correlation of `query_aligned` with the reference crop 0.998 (0.349 when shifted by 15 px); screenshot shows a small bright patch inside the field |
| N6 | PASS | D | quad and hashing: same rotation 12.1721, `matcher=quad` / `matcher=hashing`; `triangles`: `⚠ No match found with the 'triangles' matcher. This is not an error in the images: try Matcher = auto, or another matcher.` (identical); `graph` same; Run enabled afterwards |
| N7 | PASS | D | layer chooser greyed (enabled=False) once a file is set; same numbers |
| N8 | PASS | D | with `instanseg`: threshold method, blur, min area, watershed disabled, three InstanSeg fields enabled; reverse on switching back |
| N9 | PASS | D | `li` + min area 80: `n_nuclei_reference=425`, `n_nuclei_query=9`, rotation 12.2927. Cellpose: `n_nuclei_reference=347`, rotation 12.1704, **191 s** on 4 CPUs (the protocol says "20 minutes or more"; the model download was not timed and may have been cached in the installer) |
| N10 | PASS | D | Fine-tuning appears/hides; Peak distance 5; Fixed seed and Time limit greyed with unticked **set** boxes; run with 3 / 60 = same as N4 (429/9, 12.1721); unticked: same |
| N11 | PASS | D | reference mask only and both masks: `n_nuclei_reference=393`, `n_nuclei_query=9`, rotation 12.186 / 12.1737; wrong size: `✖ [mask_shape_mismatch] Reference mask must have the same size as its image: mask (520, 520), image (1600, 1600)  - click Details… …` after 0.5 s, Run enabled |
| N12 | PASS | D | progress texts `starting worker…`, `segmenting nuclei`, `cancelling…` → `cancelled` (2.6 s); second: `matching 9 query nuclei against 429 reference nuclei`, `cancelling…` → `cancelled (worker stopped)` (3.7 s); next normal run completed (429/9) |
| N13 | PASS (message) | D | `✖ [unreadable_image] cannot read fake.tif: not a TIFF file: header=b'hell'  - click Details… for the full report (log: …)`; Details has error, run record and log tail. **But** the "fixed" item is not fixed: see defect D1 |
| N14 | PASS | D | `✔ done in 1.0s  table 'table' (2 rows)`; table columns `Unique_ID, Track Duration, Mean Speed, Median Speed, Max Speed, Min Speed, Speed Standard Deviation, Total Distance Traveled, Directionality`; switching apps shows the right tool |
| N15 | PASS | D | after Restart worker: 11.8 s, 2.2 s, 2.1 s; box unticked: 13.0 s, 12.7 s |
| N16 | PASS | D | after `viewer.close()` no `labconstrictor_tools … serve` process within 1 s (checked 15 s) |
| F0 | PASS | D | Option A; menu path seen in a screenshot of the opened menu: `Plugins > LabConstrictor > LabConstrictor Tools` (no ellipsis). Not via the search bar |
| F1 | PASS | D | images opened with real File > Open; dialog `LabConstrictor`, drop-down `CellTracksColab`, `NucleiSky`; tool form `Relocalize 2D` opens directly |
| F2 | PASS | D | note text, headings `— Images —, — Segmentation —, — Matching —, — Advanced settings —, — Fine-tuning —`, **Reference = reference.tif, Query = query.tif** (right way round), "(or file)" fields, pixel sizes 0.6500/0.3250, "Use reference mask / Use query mask", **Set fixed seed**, **Set time limit**. Extra label "Image source" before the note |
| F3 | PASS | D | windows `NucleiSky:query_aligned` and `Alignment overlay (green = reference, magenta = query)` (green field, white/pink cluster); Log: `NucleiSky values: [rotation_deg:12.17212626022287, n_nuclei_query:9, bbox_y0y1x0x1:[637, 963, 597, 923], offset_y_px:700.3292583727874, scale:1.0023526330819807, offset_x_px:605.5653830528295, n_nuclei_reference:429, matcher:quad]`. A run takes ~12 s every time (Fiji starts a new worker per run) |
| F4 | PASS | D | hashing: `matcher:hashing`; triangles: plain message window titled `LabConstrictor: NucleiSky` with `No match found with the 'triangles' matcher. This is not an error in the images: try Matcher = auto, or another matcher.` |
| F5 | PASS | D | "Set fixed seed" ticked + 3, "Set time limit" ticked + 60 → same Log line as F3; second run unticked → same |
| F6 | PASS | D | after Close All the form shows plain `Reference`, `Query`, `Reference mask`, `Query mask` file fields with *Browse*, no image selectors; files chosen through the Open dialog; same result |
| F7 | PASS | D | only with a window manager (see §3 and D7). Esc ~4 s after OK: no result windows, Log `LabConstrictor: the run was cancelled`, run record status `CANCELED`; status bar says "LabConstrictor: done". The next run (F8, F9) worked |
| F8 | PASS | D | window titled `LabConstrictor: NucleiSky` with `[unreadable_image] cannot read fake.tif: not a TIFF file: header=b'hell'`, run record and log file named, no Java stack trace. **But** see D4 (raw JSON lines, 3463 px wide) |
| F9 | PASS | D | plain "Choose a file" window; Results window `table` with 2 rows; columns up to `Spe…` visible on screen, the 9 values per row confirmed by copying the table text; the headers `Total Distance Traveled`, `Directionality` were not visible on screen (window too narrow) |
| F10 | PASS | D | both runs showed the same `Image stats` dialog with `query.tif` selected; two Log lines `synthetic values: [shape:[520, 520], mean:118.50476701183432, dtype:uint16]`. The "known open question" did **not** reproduce, on a virtual screen with a window manager. Cleaned up with `unregister` (prints `True`) |
| F11 | PASS | D | Log: `LabConstrictor: skipped CellTracksColab: not available on this machine (interpreter /home/newuser/ct/bin/python is missing)` |
| F12 | **FAIL** | D | see D3. Recorded line is `run("Relocalize 2D", "reference=reference.tif query=query.tif reference_pixel_size_um=0.65 … set_fixed_seed=false fixed_seed=0 set_max_seconds=false max_seconds=0.0");`; expected `run("LabConstrictor Tools...", "app=NucleiSky tool=[Relocalize 2D] …")` without `fixed_seed=`/`max_seconds=`. Replaying the recorded line: `Macro Error: Unrecognized command: "Relocalize 2D" in line 1`. The protocol's own line was typed into the Recorder but my run of it was invalid (images were closed) so it was **not tested** |
| F13 | PASS | D | File > Quit; no `labconstrictor_tools serve` process during idle Fiji or after quit (checked right after, ≤ 25 s); Fiji process also gone |
| E1 | PASS | D | `doctor`: `✖ CellTracksColab    not available on this machine (interpreter /home/newuser/ct/bin/python is missing)` (exit code 1); `list`: `CellTracksColab  -- skipped: not available on this machine (interpreter … is missing)`; Napari lists only NucleiSky, status `⚠ skipped: CellTracksColab (not available on this machine (interpreter /home/newuser/ct/bin/python is missing))`; Fiji: F11. Restore with `mv` was sufficient, `doctor` clean again |
| E2 | PASS | D | pandas 2.2.2: `✖ [ModuleNotFoundError] No module named 'pandas'  - click Details…`, Details has a traceback; reinstall of 2.2.2 restored the tool |
| E3 | PASS | D | (a) = N13; (b) `✖ [unreadable_image] cannot read short.tif: failed to read 5120000 bytes, got 2999744`; (c) `test é 日本/query.tif` works (filesystem encoding utf-8 even with empty `LANG`). Done in Napari only, Fiji not run |
| E4 | PASS | D | worker killed with SIGKILL: `✖ worker exited unexpectedly (code -9): the worker was killed (out of memory? the OS OOM killer ends big image jobs this way)  - click Details…`; Run enabled; next run completed |
| E5 | PASS | D | zip (32 KB) holds `logs/labconstrictor.log`, `apps/*.json` (+schemas), 10 × `runs/*/run.json`, `doctor.txt`, `environment.txt`; no image/table contents; no tokens or proxy values found (grep: only the package name `asttokens`) |
| U1 | PASS | D | one Napari session: NucleiSky → CellTracksColab → NucleiSky all ran; one Fiji session: NucleiSky and CellTracksColab runs |
| U2 | N/A (partial) | D | `bash ~/ct/uninstall.sh` (6.4 s): `CellTracksColab` gone from `list`, `~/.labconstrictor/apps`, the menu `.desktop` file, and Napari (also after *Rescan apps*); NucleiSky still runs (429/9). **Fiji was not reopened after the uninstall**, so that third place was not checked |
| U3 | N/A (partial) | D | installed to A, then B (registration prefix changed to B); uninstalled A: `list` still shows CellTracksColab, registry prefix B, tool runs (**by command line, not in Napari as written**); uninstalled B: gone from `list` |
| U4 | PASS | D | install finished (rc 0); log: `WARNING: Requirement '/nonexistent/x.whl' looks like a filename, but the file does not exist` and `WARNING: tool registration failed - see the pip and register output above in this file; CellTracksColab itself is installed.`; `list` lacks the app; app Python works; the variable was set only on that one command |
| L1 | PASS | D | X11 (Xvfb), Napari widget fully usable, no Qt platform error. Wayland not tested |
| W1–W5, M1–M2 | N/A | – | Windows/macOS not available |

**Appendix A numbers (all matched):** rotation 12.17° (12.1721), scale 1.002 (1.0024), 429/9, matcher auto → quad, `li` + min area 80 → 425/9, masks → 393/9, `triangles` and `graph` → "No match found…" in both Napari and Fiji.

### The "fixed since the previous run" list

| # | Item | Result |
|---|---|---|
| 1 | Fiji menu entry (F0) | PASS: `Plugins > LabConstrictor > LabConstrictor Tools` shown in an opened menu (screenshot) |
| 2 | Fiji image choosers (F2/F3) | PASS: Reference = `reference.tif`, Query = `query.tif`; defaults run: rotation 12.1721, `n_nuclei_query:9`; images opened with File > Open |
| 3 | Nothing remembered (B-03) | PASS: after F8 (typed `fake.tif`) and a Fiji restart the file fields were empty, Matcher `auto`, both "Set …" boxes unticked (screenshot). Also not remembered between runs in one session |
| 4 | Napari Details (N13) | **FAIL**: after a successful run then the `fake.tif` run, Details still shows the matcher's debug lines of the earlier run (D1) |
| 5 | C2 no empty results folder | PASS |
| 6 | U4 uninstall warning | **FAIL**: warning appeared (`WARNING: could not remove CellTracksColab from the LabConstrictor tools registry; Napari/Fiji may still list it (run: "/home/newuser/ctU4/bin/python" -m labconstrictor_tools unregister --name CellTracksColab).`). The command starts with the app's own Python, but pasted afterwards it fails: `bash: line 1: /home/newuser/ctU4/bin/python: No such file or directory` (the uninstaller deletes the prefix right after printing it; in this case the app's Python never had `labconstrictor_tools` either) (D2) |
| 7 | Cancel in Fiji (F7) | PASS (with a window manager) |

## 3. Discrepancies between the protocol text and reality

1. **N4**, "At the end the status line reads `✔ done in <n>s  rotation_deg=12.17..., scale=1.002..., bbox_y0y1x0x1=[637, 963, 597, 923], n_nuclei_reference=429, …`": the real line has `offset_y_px=700.3293, offset_x_px=605.5654,` between scale and bbox. Correct by adding them (or by saying "the line contains").
2. **C1**, "a last line `(results are in …)`": it is the last line only in a terminal (it is written to stderr); with a pipe it is first. Harmless, but "also visible in the terminal" would be more exact.
3. **N9**, "Cellpose … about 20 minutes or more on a computer without a graphics card": measured 191 s on 4 CPU cores (model already available or fast download). Reword.
4. **F12**, whole test: the recorded line and replay do not behave as described (see D3). Sentence: "the recorder shows one line like `run("LabConstrictor Tools...", "app=NucleiSky tool=[Relocalize 2D] …")`. The line does not contain `fixed_seed=` or `max_seconds=`…". Reality: `run("Relocalize 2D", "… fixed_seed=0 … max_seconds=0.0")`. Also the Fiji README says the same as the protocol.
5. **F8**, "an error window … saying `[unreadable_image] cannot read fake.tif: not a TIFF file ...` and naming the log file": true, but the window also prints raw `[SERVICE-12] {"task": …}` lines and is 3463 px wide (D4). Mention it or fix it.
6. **F11**, "open the Log window (`Window > Log`; the line may already be there)": the Window menu has no "Log" entry; the Log window opened by itself when the plugin ran. Suggest "the Log window opens by itself when you start the plugin".
7. **F7**, "press the Esc key while the progress bar is moving": needs the Fiji window to have keyboard focus (click on the Fiji main window first). On a bare X server without a window manager Esc is never delivered (my test environment, not a product problem).
8. **S5**, list of expected folders: also `~/.local/share/applications/fiji.desktop` (created by Fiji itself on first start) and `~/.m2` (Maven, only for option B). At its first start Fiji printed `Failed to install URI scheme: fiji … Cannot run program "xdg-mime": error=13, Permission denied`, harmless in this container.
9. **OPERATIONS.md** (not the protocol) says to copy `LabConstrictor.groovy` and that the entry is `Plugins > LabConstrictor > LabConstrictor (script)`; the protocol (correctly, as tested) says `LabConstrictor_Tools.groovy` and the entry is `LabConstrictor Tools`. A reader following OPERATIONS.md gets a script whose name has no underscore, which Fiji does not list in its menus (per the protocol's own warning). Fix OPERATIONS.md.
10. **N13/U4**: see D1, D2.
11. **E3 (c)**, "(copy `query.tif` to a folder `test é 日本`)": works, including with empty `LANG` and `LC_ALL`.
12. Everything else (commands, quoting, `<TESTDATA>`, `<NS_PY>`/`<CT_PY>`, file names, expected strings of S1–S4, C2, N6, N11–N16, F3, F4, E1, E2, E4) worked as printed.

## 4. Defects

**D1 – Minor – Napari Details shows the matching log of earlier runs (item 4 of the "fixed" list is not fixed).**
* Repro: Napari, NucleiSky, open `reference`/`query`, Run (success); then set *Reference* file to `<TESTDATA>/fake.tif`, Run (fails); press **Details…** (or read `widget.last_details`).
* Saw: the "worker output (tail)" section is gone, but the section `log (tail):` lists 40 lines of `~/.labconstrictor/logs/labconstrictor.log`, among them `Matcher: Quad`, `QUAD RANSAC …`, `Match quality`, `task … COMPLETE tool=relocalize`, from earlier runs, even from an earlier Napari session (`pid=2909`).
* Expected: Details without the earlier run's matching log.

**D2 – Minor – U4 uninstall warning names a command that cannot work.**
* Repro: `LC_TOOLS_SPEC=/nonexistent/x.whl bash NucleiSky-or-CellTracks….sh -b -p ~/ctU4`, then `bash ~/ctU4/uninstall.sh`, then paste the command it prints.
* Saw: `WARNING: could not remove CellTracksColab from the LabConstrictor tools registry; … (run: "/home/newuser/ctU4/bin/python" -m labconstrictor_tools unregister --name CellTracksColab).` → pasting gives `No such file or directory` because the prefix has been deleted by the same script a moment later. The registration had never happened in this case (so there was nothing to remove, and with the NucleiSky Python `unregister` just prints `False`), i.e. the warning is also a false alarm here.
* Expected: a command that works when pasted (for example with another app's Python or `python -m labconstrictor_tools unregister …` from any environment that has it), and no warning when nothing was registered.

**D3 – Major (for people who use macros; jar only) – Fiji macro recording and replay do not work as documented.**
* Repro: jar built with `mvn package` (clean clone, rc 0), copied to `Fiji/plugins`, groovy script removed, Fiji restarted; open `reference.tif`, `query.tif`; Plugins > Macros > Record…; Plugins > LabConstrictor > LabConstrictor Tools…; OK with defaults; then put the cursor on the recorded line and press the Recorder's *Run*.
* Saw: (1) an ImageJ error dialog "Recorder: Duplicate keyword: Command: "Relocalize 2D" Keyword: "max_seconds" Value: 0.0. Add an underscore to the corresponding label in the dialog to make the first word unique." (2) recorded line `run("Relocalize 2D", "reference=reference.tif query=query.tif reference_pixel_size_um=0.65 query_pixel_size_um=0.325 use_reference_mask=false reference_mask=query.tif use_query_mask=false query_mask=query.tif segmentation=threshold threshold_method=otsu blur_sigma=1.0 min_area_px=5 watershed_split=true instanseg_model=brightfield_nuclei instanseg_target=nuclei instanseg_cleanup_fragments=true matcher=auto peak_distance_px=5 set_fixed_seed=false fixed_seed=0 set_max_seconds=false max_seconds=0.0");` (3) running it: `Macro Error: Unrecognized command: "Relocalize 2D" in line 1`.
* Expected (protocol and Fiji README): `run("LabConstrictor Tools...", "app=NucleiSky tool=[Relocalize 2D] …")`, no `fixed_seed=` / `max_seconds=` when unset, and a replay that runs without a dialog.
* Not tested: the exact documented form typed by hand (my attempt had no images open).

**D4 – Minor – Fiji error dialog is huge and shows protocol noise.**
* Repro: F8 (file `fake.tif` as Reference, no image open).
* Saw: the dialog `LabConstrictor: NucleiSky` is 3463 × 225 px, because it includes full-length lines like `[SERVICE-12] {"task":"…","requestType":"EXECUTE","inputs":{…`. On a 1600 px wide screen the OK button is off-screen; Enter and Space did not close it in my setup, Alt+F4 (window manager) did.
* Expected: a short message (the first line, the run record, the log file) that fits a normal screen.

**D5 – Minor, uncertain – Napari: a run started immediately after another one can lose its job folder.**
* Seen once in my scripted driver: a second Run clicked 35 ms after the previous run reported COMPLETE (before the widget handled "done") started a new worker and then failed with `[FileNotFoundError] [Errno 2] No such file or directory: '/tmp/lcin_…/out/query_aligned.tif'`; the following run worked. Probably the "done" handler of the first run deleted `self._job_dir`, which already held the second run's folder (code reading, not demonstrated). A person cannot click that fast, so I rate it Minor; I did not reproduce it again. In the same event a second NucleiSky worker was started while the first was still alive in the cache.

**D6 – Cosmetic (docs) – OPERATIONS.md uses the old script name** (`LabConstrictor.groovy`, menu entry `LabConstrictor (script)`); see discrepancy 9.

**D7 – Observation, not a defect – Fiji Esc needs keyboard focus.** Without a window manager Java never had a focused window and the Esc key was ignored (two failed tries); with openbox and the Fiji window clicked, it cancelled correctly.

No Blocker was found.

## 5. Verdict

**Not yet** (a small list, no Blocker): the installation, registration, both tools, cancel, errors, E1–E5, U1–U4 and L1 all work on Linux and match the protocol. Before human testers get it:
1. F12 (macro) does not work as the protocol and the Fiji README say (D3). Either fix it, or remove F12 from the protocol until the recorder issue is solved.
2. Two items marked as fixed are still open: Napari Details shows earlier matching logs (D1) and the U4 warning command cannot be pasted (D2).
3. Fiji error dialog size (D4) will confuse testers on small screens; the OPERATIONS.md script name (D6) is wrong.
Everything else can go to testers unchanged (with the small text corrections in section 3).

**What I could not check:** Windows and macOS (and the `.bat` hooks); a real desktop (all GUI work was on a virtual display, by script or `xdotool`); the Napari *Select file* and File > Open dialogs (I set the same values directly); Fiji with a path containing spaces/non-English letters; Fiji after uninstalling an app (U2 third place); the U3 tool run in Napari/Fiji (CLI only); the protocol's own macro line (F12); Napari start-up without the extra Qt libraries (they were installed before the first start); Wayland; the first Cellpose model download time; the first-run compile of "up to 2 minutes" never appeared (first run in Napari 12.9 s, in Fiji ~12 s).

## 6. Screenshots (folder `docs/img/`)

`N2_napari_form`, `N4_napari_result`, `N5_napari_aligned_over_reference`, `N6_napari_triangles_notice`, `N14_napari_table_celltracks`, `F0_fiji_menu_…` (menu path), `F2_fiji_form_top/bottom`, `F3_fiji_alignment_overlay`, `F4_fiji_triangles_message`, `F7_fiji_progress_before_esc`, `F8_fiji_error_dialog_3463px_wide`, `F9_fiji_table_result`, `F11_fiji_log_skipped_app`, `B03_fiji_form_defaults_after_restart`, `F12_fiji_recorder_*` (three, for D3).
