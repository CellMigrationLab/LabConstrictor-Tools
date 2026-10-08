# Spec (proposal): Wave 2 of the manifest roadmap

Status: **for review, nothing is implemented.** Same rules as Wave 1 ([SPEC_WAVE1.md](SPEC_WAVE1.md)): the manifest stays small and organised in four families ([MANIFEST.md](MANIFEST.md)); everything is additive within `protocol: 1`; a host that does not know a hint shows a plain, working form. Out of scope: `TracksOut` (parked) and GEFF (maybe later; nothing here blocks it).

| # | Item | Family | New names | Hosts |
|---|---|---|---|---|
| 1 | Time-lapse and 3D images | Types + Links + Behaviour | `Axes("TZYX")` (extended), `TimeIntervalOf`, `ZStepOf`, `PerPlane`, `t` / `z` columns and properties | Napari, Fiji, QuPath (+ CLI, notebook) |
| 2 | Figures and reports | Types + Look | `FigureOut`, `Format` | all, plus CLI and notebook |
| 3 | Host action "open" | Behaviour | `Open()`, `LinkOut` | all, plus CLI and notebook |

Order of work: 1 (largest, unlocks apps), then 2, then 3 (small, builds on 2 for HTML/PDF). Each item ships as a Tools PR (schema, validation, docs, example, `check` line, tests), then one PR per host, then the apps. A feature is "done" only when it meets the checklist at the end of MANIFEST.md.

---

## 1. Time-lapse and 3D images

### 1.1 Axis conventions
* Axis letters: `T` (time), `Z` (depth), `C` (channel), `Y`, `X`. Nothing else in Wave 2 (`S` samples/RGB stays "channel last, host-handled as today"; `Q` and unknown OME axes are refused, see 1.9).
* **The declaration decides the order the tool receives.** `Axes("TZYX")` means the function gets a 4D array whose dimension 0 is T, 1 is Z, 2 is Y, 3 is X. The worker transposes; the tool never sees the file's order. `Y` and `X` are always last, `C`, if declared, comes before `Y` (hence `CYX`, `TCYX`, `CZYX`, `TCZYX`); this keeps arrays C-contiguous in the common case and gives one canonical order to document.
* Wire order inside files is whatever the host writes; the **axes come from the file** (1.3), never guessed from the shape when metadata exists.
* Existing behaviour is unchanged: no `Axes` = host passes the image as it is; `Axes("YX")` = exactly 2D; `DEFAULT_AXES` for outputs without a declaration stays `{2: YX, 3: ZYX, 4: CZYX}` (a tool that returns a time series must declare `Axes("TYX")` on the output).

### 1.2 How a tool declares what it needs
| Declaration | Meaning | The tool receives |
|---|---|---|
| `Axes("YX")` | 2D only (today) | 2D array |
| `Axes("ZYX")`, `Axes("TYX")`, `Axes("TZYX")`, `Axes("CYX")` ... | exactly these axes, in this order | array with those dimensions, in that order |
| `Axes("TYX", "YX")` (several strings) | accepts any of them; the worker picks the first that fits and the tool reads `ndim` | array of the matching shape |
| `Axes("TYX"), PickChannel()` | as `TYX`, for one channel chosen by the person | the stack of that channel (no `C`) |
| `Axes("YX"), PerPlane("TZ")` | the tool is written for one plane; the worker calls it once per plane (see 1.6) | 2D array, once per plane |

Rules (declaration errors at registration, exact text):
* `parameter 'image': Axes('TYZX') is not valid: Y and X must be last (use 'TZYX')`
* `parameter 'image': Axes('TTYX') repeats the axis T`
* `parameter 'image': Axes('TYX') uses letters from T Z C Y X only; got 'Q'` (message lists the valid letters)
* `PickChannel` today requires `YX`; relaxed to "any axes without `C`" (error: `PickChannel gives the tool one channel, so Axes must not contain C`).
* An axis is only *needed* when it is in the string. Length-1 axes in the file that are not declared are squeezed away; an undeclared axis longer than 1 is refused (`wrong_dimensions`, 1.9).

### 1.3 What the tool receives, and how the file says what the axes are
* **Still a TIFF path on the wire** (`image` / `labels` inputs). Hosts write **OME-TIFF or ImageJ-hyperstack TIFF with axes metadata** (tifffile `metadata={"axes": "TZCYX"}`); the worker reads `series[0].axes` with tifffile and reorders to the declared axes.
* Optional reserved input `_axes` (like `_job_dir`): `{"<param>": "TZCYX"}`, the axes of the file the host just wrote when it cannot write metadata; it overrides the file. `_axes` with a wrong length is `bad_request`.
* A TIFF without axes metadata: 2D = `YX`; 3D = `ZYX` (as `DEFAULT_AXES` today); 4D = `CZYX`. Hosts that know better must send `_axes`. A tool can never be given a guessed `T`.
* Shared-memory ndarray objects (Appose) carry `axes` next to `shape` and `dtype`; without it the same defaults apply.
* Calibration: see 1.4. It is *not* embedded for the tool; the tool gets it as ordinary float parameters.
* dtype rules are those of Wave 1 (`portable_dtype`); nothing changes.

### 1.4 `TimeIntervalOf` and `ZStepOf` (Links)
```python
@tool("Track speed")
def speed(
    movie: Annotated[Image, Axes("TYX")],
    pixel_size: Annotated[float, PixelSizeOf("movie"), Unit("um/px")] = 1.0,
    dt: Annotated[float, TimeIntervalOf("movie"), Unit("s")] = 1.0,
    dz: Annotated[Optional[float], ZStepOf("volume"), Unit("um")] = None,
): ...
```
| | `PixelSizeOf` (today) | `TimeIntervalOf` | `ZStepOf` |
|---|---|---|---|
| Schema key | `pixel_size_of` | `time_interval_of` | `z_step_of` |
| Parameter type | `float` | `float` | `float` |
| Unit | um/px | **seconds** | **micrometres** |
| Prefill from | layer scale / calibration | Fiji `frameInterval`, OME `TimeIncrement`, QuPath server `getTimeUnit`, Napari layer `scale[T]` | Fiji `pixelDepth`, OME `PhysicalSizeZ`, QuPath `getZSpacingMicrons`, Napari `scale[Z]` |
* Declaration rules: applies to a `float` (or `Optional[float]`) parameter and names an `Image` / `Labels` parameter of the same tool whose `Axes` contain `T` (resp. `Z`) or that has no `Axes`. Error: `parameter 'dt': TimeIntervalOf('movie') needs 'movie' to have a T axis (its Axes are 'YX')`.
* Hosts convert to the fixed units above (Fiji `frameInterval` in `timeUnit` -> s; QuPath minutes/ms -> s). Unknown or zero calibration: the parameter keeps its default and the host shows "not calibrated" in the tooltip; it never sends 0.
* `Unit("s")` / `Unit("um")` stay free text for display; the units in the table are the contract.

### 1.5 What a tool returns for stacks
| Output | Rule |
|---|---|
| `ImageOut` / `LabelsOut` | declare `Axes("TYX")` etc. on the output; the result `axes` carries it; hosts show a stack (Napari layer with dims sliders, Fiji hyperstack, QuPath preview + "Open in QuPath" for the plane set) |
| `PointsOut` | columns `y`, `x` stay first; **optional columns `z` and `t`** (integer, zero-based plane indices of the image named by `ApplyTo`, else the first image input) |
| `ShapesOut` | each feature has optional properties `t` and `z` (zero-based integers); coordinates stay `[x, y]` per plane |
| `TableOut` | an ordinary table; a `t` / `z` column by convention (hosts do not interpret it) |
| `Scalars`, `MessageOut`, `Affine` | unchanged (a per-frame Affine is refused with `PerPlane`, 1.6) |
* A point or shape without `t` / `z` when its `apply_to` image has that axis with length > 1 is placed on plane 0 and the host says so once (status line). `labconstrictor-tools test` reports it as a contract problem: `points 'peaks': image has a T axis but no 't' column (placed on frame 0)`.
* A `t` / `z` outside the image is dropped by the host and counted: `3 points were outside the image planes and were not shown` (never an error).
* Pixel centres at integers, as before; `t` and `z` are plane indices, never physical times.

### 1.6 Per-plane or whole-stack execution: `PerPlane` (Behaviour)
* **Whole stack** (tool declares `TYX` / `ZYX` / ...): one task, the tool loops and calls `progress(fraction, "frame 12 of 300")` and `check_cancel()` itself, as today.
* **Per plane**: `Annotated[Image, Axes("YX"), PerPlane("TZ")]` on an image or labels input. The tool stays 2D; given a larger image the worker iterates over the listed axes that are present, in C order, calls the tool once per plane and merges the results:
  * `ImageOut` / `LabelsOut`: stacked back along the iterated axes (shape check: every plane must return the same shape and dtype or `per_plane_mismatch`);
  * `PointsOut` / `ShapesOut`: the worker adds `t` / `z` (the plane indices) to each row / feature; a tool that already returns the column keeps its own;
  * `TableOut`: rows concatenated with `t` / `z` columns added when the tool did not return them;
  * `Scalars`, `MessageOut`, `Affine`, `FileOut`, `FigureOut`: refused **at registration** (`PerPlane cannot be used with the output 'x' (a Scalars result); return a TableOut with one row per plane instead`).
  * Several iterated inputs must have the same plane grid; other inputs are passed whole to every call.
* **Progress and cancel come for free:** the worker reports `UPDATE {message: "frame 12 of 300", current: 12, maximum: 300}` per plane (scaled to `PROGRESS_MAXIMUM`) and checks cancel between planes (cancel latency is one plane; a tool that never returns is killed like today). A failing plane ends the task: `per_plane_failed` with the plane named (below); partial results are discarded.
* **Memory:** the worker reads one plane at a time (tifffile page/memmap), so the stack never has to fit in RAM; this is why `PerPlane` is the recommended way for 2D tools. Outputs are written to disk plane by plane (tifffile `TiffWriter`).
* Without `PerPlane`, a 2D tool given a stack is refused (`wrong_dimensions`), exactly as today. Hosts offer a "Run on: this plane / all planes" chooser only for inputs with `PerPlane`; "this plane" sends just the viewer's plane (Napari current dims point, Fiji current slice/frame, QuPath current z/t).

### 1.7 Host behaviour
| | Napari | Fiji | QuPath | CLI | Notebook |
|---|---|---|---|---|---|
| Show a stack input | any layer with ndim > 2; axes from layer metadata (OME reader) else a small "Axes of this layer" chooser, default from the tool's declaration | hyperstack (C, Z, T from the ImagePlus dimensions); no chooser | the open image's z-planes and timepoints | file path; axes from the file | file path or ndarray + `axes=` |
| Export | write OME-TIFF of the layer data (selected channel only with `PickChannel`) | export hyperstack (or one plane / one channel) as ImageJ TIFF with axes | export plane set as OME-TIFF; **Image area** gets a new line **Planes: current plane / all z / all t / all** (default current plane) | n/a | n/a |
| `TimeIntervalOf`, `ZStepOf` prefill | layer scale | calibration | server metadata | from file (OME / ImageJ tags) when parameter not given | same |
| Stack output | layer, dims sliders move through t/z | hyperstack window | plane-aware preview; annotations placed on their plane | file | `ndarray` or file path + preview of the middle plane |
| Points/shapes with `t`, `z` | N-D points/shapes layer (coordinates `[t, z, y, x]`) | point/polygon ROIs with `setPosition(c, z, t)` | annotations with `ImagePlane.getPlane(z, t)` | rows in the table | table |
| "Run on" chooser (`PerPlane`) | yes | yes | yes (with the Image area) | `all` unless `plane=t:3,z:2` given | `plane=` argument |
| Progress / cancel per plane | yes | yes (Esc) | yes | Ctrl-C | interrupt |
| Copy as command | image has no name: placeholder `movie=movie.tif` + comment; `plane=` is not added (the file is sent whole) | same, plus a note when only the current plane was sent | note line like the existing Image area one: `# movie: QuPath sent planes 'current plane' (the command line sends the whole file)` | n/a | n/a |

### 1.8 Size and memory limits
| Constant | Value | Where | Meaning / how to change |
|---|---|---|---|
| `MAX_STACK_BYTES` | 4 GiB | worker (`convert`) | a whole-stack input larger than this (after `PickChannel` and axis selection) is refused; env `LC_MAX_STACK_BYTES`; not applied to `PerPlane` inputs |
| `MAX_PLANE_PIXELS` | 100 000 000 | QuPath guard, existing | per plane, unchanged (`lc.qupath.max_export_pixels`) |
| `lc.qupath.max_export_planes` | 500 | QuPath | planes of one export when "all" is chosen; above it the run is refused with the two ways out |
| `lc.qupath.max_export_bytes` | 4 GiB | QuPath | planes x plane bytes; same property style as the pixel budget; invalid value ignored and logged once |
| `MAX_POINTS_HINT` / `MAX_LABELS_HINT` | 1 000 000 points / 50 000 outlines **per run** | hosts | the Wave 1 outline limit now counts all planes together; hosts say how many were left out |
| Napari / Fiji | no limit of their own | | a stack that is already open is not copied twice: Napari writes in chunks (dask-aware), Fiji streams planes |
Nothing is ever downsampled or cropped silently. The QuPath refusal message pattern stays: `'<name>' would send 1200 planes (limit 500). Choose Planes: current plane, or a smaller selection, or use a file.`

### 1.9 Failure modes and error codes
| Code | When | Message (exact) |
|---|---|---|
| `wrong_dimensions` (existing, extended) | dims do not fit and no `PerPlane` | `'<label>' must have axes <declared> but the file has axes <actual> with shape <shape>; pick a channel or plane, or choose a tool made for stacks` |
| `unknown_axes` | OME axes contain a letter outside TZCYX, or `_axes` is invalid | `cannot use '<name>': axis '<Q>' is not supported (only T Z C Y X)` |
| `stack_too_large` | `MAX_STACK_BYTES` exceeded | `'<label>' is <n.n> GiB as a stack (limit <m.m> GiB); use a smaller region or a tool that works plane by plane` |
| `per_plane_failed` | the tool raised for one plane | `'<tool>' failed on frame <t>, plane <z>: <original message>` (a `ToolError` code is kept in `cause_code`) |
| `per_plane_mismatch` | planes return different shapes / dtypes | `plane <t>,<z> returned shape <a> but the first returned <b>` |
| `empty_image` (existing) | no pixels | unchanged |
| `no_match` / `no_result` | unchanged, shown as notices; with `PerPlane` it is raised only when **every** plane gave no result |

### 1.10 Tests
Generated round-trip cases, in the style of the cases files read by `labconstrictor_tools.testing` (a generator `tests/roundtrip_cases.py` is proposed to write them; `tests/data/synthetic_cases.json` shows the format), run on a synthetic example tool per row:

| Case | Input | Expect |
|---|---|---|
| `tyx_ok` | OME-TIFF `TYX` 5x32x32 | `status ok`, image `shape [5,32,32]`, `axes TYX` |
| `zyx_from_tzyx_len1` | file `TZYX` with T=1 into `Axes("ZYX")` | squeezed, ok |
| `tzcyx_to_tzyx_pickchannel` | OME `TZCYX`, channel 1 | tool gets `TZYX` of channel 1 (checked by `mean`) |
| `order_swapped` | OME `ZTYX` into `Axes("TZYX")` | transposed correctly (pixel value encodes its t and z) |
| `no_metadata_3d` | plain 3D TIFF | treated as `ZYX`; into `TYX` tool -> `wrong_dimensions` |
| `stack_into_2d_tool` | `TYX` into `Axes("YX")` | `status failure`, `code wrong_dimensions` |
| `perplane_tyx` | 4 frames, 2D tool | stacked result `shape [4,h,w]`, `progress_events_min 4` |
| `perplane_points` | 3 frames | points table has a `t` column 0..2 |
| `perplane_cancel` | `cancel_after_s` mid-run | `CANCELATION` within one plane |
| `perplane_bad_plane` | tool raises on frame 2 | `per_plane_failed`, message contains `frame 2` |
| `calibration_prefill` | parameters not given | defaults used; `time_interval_of` / `z_step_of` present in schema |
| `unknown_axis` | `_axes: "QYX"` | `unknown_axes` |
| `too_large` | `LC_MAX_STACK_BYTES=1000` | `stack_too_large` |
| `points_missing_t` | tool returns points without `t` on a stack | contract problem reported by `test` |
Also unit tests for the declaration errors in 1.2 and 1.4, and an extension of `RESULT_KEYS` (`image`: `axes`; `points`: `t_values`). Host GUI checks (each host's own suite, example app tools `stack_stats`, `plane_blur`, `frame_points`): open a 5x3 TZ stack, run whole-stack and per-plane; check that dims sliders / hyperstack / z-t planes show the result, that points land on the right plane, that Cancel stops within one plane, that the QuPath guard refuses 600 planes and a tiny-budget run, and that Copy as command contains the placeholder and note.

---

## 2. `FigureOut`: a figure or report

```python
@tool("Report")
def report(table: Table) -> Annotated[FigureOut, Name("summary"), Format("png"), Replace()]:
    fig = ...            # a matplotlib Figure, or a Path / str of a finished file
    return fig
```

### 2.1 Manifest and schema
* **Types:** `FigureOut`. **Look:** `Format("png" | "svg" | "html" | "pdf")` on the output, default `png`. The format is a **promise to the host** (so it can choose a viewer without opening the file); the worker verifies it.
* What a tool may return: a `matplotlib.figure.Figure` (saved by the worker: png at 150 dpi, svg, pdf; `html` is refused for it), a `Path` to a finished file whose suffix matches the format, or, for `html`, an HTML `str` (the worker writes `<name>.html`). Plotly figures: return `fig.to_html(include_plotlyjs=True)`; Tools has no dependency on either library.
* Output schema: `{"name", "type": "figure", "format": "png|svg|html|pdf", "replace"?}`.
* Result: `{type: "figure", name, path, format, width?, height?}` (`width`/`height` in pixels, png only, so hosts can lay out without decoding).
* Declaration errors: `output 'summary': Format('gif') is not valid; use one of 'png', 'svg', 'html', 'pdf'`; `Format applies to a FigureOut output`.
* `FigureOut` does **not** work with `PerPlane` (1.6).

### 2.2 Host behaviour
| Format | Napari | Fiji | QuPath | CLI | Notebook |
|---|---|---|---|---|---|
| `png` | docked viewer widget under the form (image label, zoom to fit, "Save as...") | an ImagePlus window titled `<app>: <name>` | window with an `ImageView`, "Save as..." | path printed | inline (`IPython.display.Image`) |
| `svg` | docked `QSvgWidget` (QtSvg) | rendered to a PNG by the host and shown like png; the SVG file is listed in the Log | `WebView` (JS off) | path | inline SVG |
| `html` | docked `QWebEngineView` when available (napari[all] / PyQt), else an "Open" button that uses `Open()` rules (2.3 / section 3) | **not shown in Fiji**; the Log gets `Report written: <path>` and Open (section 3) offers the browser | `WebView`, JS on only for the local file, no network (2.5) | path | `IFrame` with `sandbox="allow-scripts"` |
| `pdf` | "Open" button (system viewer, through `Open()` rules) | Log line + Open | Open button | path | link |
| `Replace()` | replaces the dock content / window | closes the previous window | reuses the window | n/a | n/a |
| Unknown host / old host | lists `path` as a file result | same | same | same | same |
Copy as command: not affected (a figure is an output).

### 2.3 Limits
`MAX_FIGURE_BYTES` = 25 MiB (worker refuses larger files); png wider than 8192 px is shown scaled to fit by hosts; hosts show one figure per output name (`Replace()` or a numbered title).

### 2.4 Failure modes
| Code | When | Message (exact) |
|---|---|---|
| `bad_figure` | returned object is not a Figure / Path / str, or the file is missing | `output 'summary' must return a matplotlib Figure or the path of a .png file; got <type>` |
| `figure_format_mismatch` | suffix or magic bytes differ from `Format` | `output 'summary' says Format('png') but the file is an SVG` |
| `figure_too_large` | > `MAX_FIGURE_BYTES` | `output 'summary' is <n> MiB (limit 25 MiB); reduce the dpi or simplify the plot` |
| `unsupported_format` (existing) | Figure and `Format("html")` | `a matplotlib Figure cannot be saved as html; use png, svg or pdf` |
Display failures (no WebEngine, no SVG support) are never errors: the host falls back to the file listing and says why once.

### 2.5 Security
HTML is arbitrary code: hosts show it only from the run folder; the viewer gets **no network** (block all requests except the figure file), **no navigation away**, no file access beyond the figure file, no popups; external links open in the system browser only after a click. SVG is shown through an image renderer or a JS-off WebView (SVG can carry script).

### 2.6 Tests
| Case | Expect |
|---|---|
| `fig_png` | `figure` result, `format png`, width/height set, PNG magic bytes |
| `fig_svg_from_path`, `fig_pdf_from_path`, `fig_html_str` | file written with the right suffix |
| `fig_mismatch` | `figure_format_mismatch` |
| `fig_too_large` | `figure_too_large` (limit lowered by env `LC_MAX_FIGURE_BYTES`) |
| `fig_bad_return` | `bad_figure` |
Host checks: the figure appears (docked / window / WebView), `Replace()` reuses it, an `html` figure with an `<img src="http://...">` makes no request, a `javascript:` link does nothing, old-host listing shows the path.

---

## 3. `Open()`: ask the host to open a result

### 3.1 Manifest and schema
* **Behaviour:** `Open()` on an output of type `FileOut` or `FigureOut`: after a successful run the host opens that result in its native viewer. **Types:** a new `LinkOut` (the tool returns an `https://` URL string) for web pages; `Open()` is implied on it.
```python
-> tuple[
    Annotated[FileOut, Name("results folder"), Open()],     # returns a Path to a directory or a file
    Annotated[LinkOut, Name("documentation")],               # returns "https://..."
]
```
* Output schema: `"open": true` (on `file` / `figure`); `LinkOut` has `type: "link"` and result `{type: "link", name, url}`.
* `Open()` is a **request, not a command**: the worker only describes what to open; **the host decides and does it**, after the task completed (never during a run). The tool cannot choose the program.
* Declaration errors: `output 'x': Open() applies to a FileOut or FigureOut output`; `LinkOut cannot be combined with Replace`.

### 3.2 Safety rules (all hosts, tested)
| Rule | Detail |
|---|---|
| Location | the `realpath` of the target (symlinks resolved) must be **inside the run folder (`job_dir`)**, or equal to / inside a path the person chose in this run's form (a `File` or `Folder` input value). Anything else: refused |
| Kind | a regular file or a directory; devices, sockets and broken links refused |
| Allowed file types | `png jpg jpeg tif tiff svg html htm pdf csv tsv txt md json geojson log`; a directory opens in the file manager. Other suffixes are **not opened**; the host offers "Show in folder" instead |
| Never | executables or scripts (`exe bat cmd com msi ps1 vbs js sh py jar app lnk desktop scr`), shell commands, arguments, `file://` URLs from tools, custom protocols |
| URLs | `https://` only (no `http`, `file`, `javascript`, `data`); the host asks **once per host session per host name** ("<tool> wants to open example.org in your browser. Open?") |
| Opening method | the host's own API, never a shell string: Napari `QDesktopServices.openUrl(QUrl.fromLocalFile(...))`, Fiji `Desktop.open` / `ij.plugin.BrowserLauncher`, QuPath `QuPathGUI.launchBrowserWindow` / `Desktop.open`, CLI `webbrowser.open` / `os.startfile` only with `--open` |
| Automatic vs button | opening is automatic only for results in the run folder; the result list always has an **Open** button too. A host setting "Allow tools to open results automatically" (default **on**) turns the automatic part off |
| Several `Open()` outputs | at most 3 are opened automatically per run (the rest get buttons) |
| Logging | every open, refusal and reason is written to the log (`labconstrictor` logger) |

### 3.3 Host behaviour
| | Napari | Fiji | QuPath | CLI | Notebook |
|---|---|---|---|---|---|
| File / figure | system viewer (or the figure dock for png/svg/html when the output is a `FigureOut`) | system viewer; tables and images that Fiji can open natively open **in Fiji** (`IJ.open`) instead | system viewer; images open as a QuPath image only on the button ("Open in QuPath", existing) | prints `Open: <path>`; with `--open` calls the OS opener | shows a link / `FileLink`, `FileLinks` for a folder; no auto-open |
| Folder | file manager | file manager | file manager | printed | `FileLinks` |
| URL | browser after consent | browser after consent | browser after consent | printed (`--open` opens after a y/N prompt) | link (click) |
| Refused target | message under the status, button disabled | Log line | message in results window | `open refused:` line | warning |
| Old host | the file / folder is listed as a normal result; `link` is shown as a text message with the URL | same | same | same | same |

### 3.4 Failure modes
Refusals never fail the run (the results are valid); they are reported as a warning line and in `Details`.
| Code (in `diagnostics` / warning) | When | Message (exact) |
|---|---|---|
| `open_refused` | outside the allowed locations | `'<name>' was not opened: <path> is outside the run folder and the files you chose` |
| `open_refused` | type not allowed | `'<name>' was not opened: .<ext> files are not opened automatically (use Show in folder)` |
| `open_refused` | URL not https | `'<name>' was not opened: only https links can be opened` |
| `open_missing` | the path does not exist after the run | `'<name>' was not opened: <path> does not exist` |
| `open_failed` | the OS has no handler | `'<name>' could not be opened: no program is set for .<ext> files` |
| `bad_link` (worker, fails the run) | `LinkOut` value is not a string URL of at most 2048 characters | `output 'documentation' must return an https:// URL (a text of up to 2048 characters)` |

### 3.5 Tests
| Case | Expect |
|---|---|
| `open_in_jobdir` | result `open: true` for a file in `job_dir` |
| `open_outside` | tool returns `/etc/passwd`; the run completes, results flag it, host test sees `open_refused` and no process started |
| `open_symlink` | symlink in `job_dir` to outside: refused |
| `open_script` | `run.sh`, `run.exe`: refused |
| `open_http`, `open_javascript` | refused; `https://example.org` accepted |
| `link_too_long` | `bad_link` |
Host checks: with a stubbed opener (a recording hook, never the real OS), automatic open for run-folder results, no open when the setting is off, one consent prompt per host name, the Open button works and is disabled for a refused target.

---

## 4. Cross-cutting

### 4.1 Schema and protocol additions (all additive, `protocol: 1`)
```
inputs[]:  "axes"? (string, or list of strings when several are accepted), "pick_channel"? (existing),
           "time_interval_of"?, "z_step_of"?, "per_plane"? (string such as "TZ")
outputs[]: "type" may now also be "figure" | "link";  "axes"? (existing; now any valid axes), "format"? ("png|svg|html|pdf"), "open"? (bool)
results[]: image/labels {path, axes};  points/shapes: optional t, z;  figure {path, format, width?, height?};  link {url}
reserved inputs: "_axes"? {param: "TZCYX"}
```
A schema's `axes` as a list is the only shape change; hosts that read it as a string treat a list as "not declared" (they show the plain chooser, the worker still validates).

### 4.2 Back-compat: what an older host ignores
| New | Older host does | Result |
|---|---|---|
| `axes` with T/Z, list form | ignores; sends the image as it is | worker gives `wrong_dimensions` with the clear message (never a crash inside the tool) |
| `time_interval_of`, `z_step_of` | plain float fields | person types the value |
| `per_plane` | plain input; sends a stack or a plane | stack into 2D tool: `wrong_dimensions`; with `PerPlane` the worker iterates when it receives a stack |
| `t`, `z` columns / properties | host that places points ignores them | points appear on one plane (flat 2D hosts) |
| `figure`, `link` results, `open` | unknown result type: lists the `path` / the URL text | usable, no viewer |
| `Format`, `Open()` | ignored | as above |
A new Tools with an old host and an old tools with a new host both stay usable: hosts read missing keys as "not declared", and an app that needs a feature states it in its description.

### 4.3 Constants (Tools unless noted)
`MAX_STACK_BYTES` 4 GiB, `MAX_FIGURE_BYTES` 25 MiB, `MAX_LINK_CHARS` 2048, `MAX_AUTO_OPEN` 3, `MAX_POINTS_HINT` 1 000 000, `MAX_LABELS_HINT` 50 000 (existing), `PROGRESS_MAXIMUM` 100 (existing), `AXES_LETTERS` "TZCYX", `OPEN_SUFFIXES` (3.2). QuPath: `lc.qupath.max_export_planes`, `lc.qupath.max_export_bytes`. Every constant has a name in code and an env/property override where a person could hit it.

### 4.4 Security summary
Nothing here lets a tool run a command: `Open()` is a description, checked and executed by the host with fixed rules; HTML runs without network and navigation; the worker never trusts `_axes`, `apply_to` or a returned path (all resolved inside `job_dir` or refused); a request line is still bounded by the 16 MiB rule, and large stacks always travel as files, never inline.

### 4.5 Docs that change with the code
`MANIFEST.md` (rows: `Axes` extended, `TimeIntervalOf`, `ZStepOf`, `PerPlane`, `FigureOut`, `Format`, `Open()`, `LinkOut`), `PROTOCOL.md` (4.1), `HOST_FEATURES.md` (rows from 1.7, 2.2, 3.3; remove "time-lapse and 3D axes, figure output" from the "not yet" line), `AUTHORING.md` (a recipe each), example app `interactions.py` (`stack_stats`, `plane_blur`, `frame_points`, `figure`, `open_demo`), QuPath README ("Planes" under Large images).

---

## 5. Work breakdown (PR-sized, in order)
| # | Repo | PR | Depends on |
|---|---|---|---|
| 1 | LabConstrictor-Tools | Axes validation (new letters, order, list form), reading axes from OME/ImageJ TIFF, transposing, `unknown_axes`, `wrong_dimensions` text, `PickChannel` relaxed | none |
| 2 | LabConstrictor-Tools | `TimeIntervalOf`, `ZStepOf` (types, schema, errors, `check` line) | 1 |
| 3 | LabConstrictor-Tools | `t` / `z` in points, shapes and tables (helpers, `test` contract checks, `RESULT_KEYS`) | 1 |
| 4 | LabConstrictor-Tools | `PerPlane` (plane iteration, merge, progress, cancel, plane-wise writing, `MAX_STACK_BYTES`), example tools, generated round-trip cases | 1-3 |
| 5 | napari-labconstrictor | stacks: axes chooser, export, dims sliders, N-D points/shapes, "Run on" | 4 |
| 6 | LabConstrictor-Fiji | hyperstack export/import, ROI positions, "Run on" | 4 |
| 7 | labconstrictor-qupath | Planes chooser, z/t annotations, plane/byte guards, Copy as command note | 4 |
| 8 | LabConstrictor-Tools | `FigureOut`, `Format`, limits, errors, notebook + CLI display | none (parallel to 5-7) |
| 9 | napari / Fiji / qupath (3 PRs) | figure viewers and `Replace` | 8 |
| 10 | LabConstrictor-Tools | `Open()`, `LinkOut`, safety checker `labconstrictor_tools.openpolicy` (one function every host's tests can call), CLI `--open`, notebook links | 8 |
| 11 | napari / Fiji / qupath (3 PRs) | opener, consent prompt, setting, Open button | 10 |
| 12 | apps | CellTracksColab (time-lapse input, per-frame points), NucleiSky (movie, `PerPlane`), report tools (`FigureOut`) | 4, 8 |
Hosts for 5-7 can start as soon as 4 is merged and the example tools exist; 8 and 10 can overlap with them.

---

## 6. Open questions for the maintainers (recommended answers)
1. **Who decides axis order, tool or file?** Recommended: the tool's declaration; the worker transposes from the file's metadata (1.1, 1.3). The tool never branches on file order.
2. **Several accepted axes (`Axes("TYX", "YX")`) or only one per input?** Recommended: allow the list form but document `PerPlane` as the better way to accept both 2D and stacks.
3. **Fixed canonical order `TCZYX`-subset (C before Z)?** Recommended: yes, with `Y`, `X` last; one rule to document, matches tifffile/OME-Zarr practice.
4. **Calibration units: fixed (s, um) or host-native?** Recommended: fixed s and um; hosts convert; `Unit` stays display-only.
5. **Per-plane iteration in the worker or in the hosts?** Recommended: in the worker (`PerPlane`): one task, one progress bar, one cancel path, same behaviour in CLI/notebook, memory bounded.
6. **Missing `t` / `z` on points of a stack: frame 0, all frames, or an error?** Recommended: frame 0 plus a status note and a `test` contract warning; "all frames" would hide a tool bug.
7. **Zero- or one-based plane indices?** Recommended: zero-based in the protocol (like pixel coordinates); hosts show their own numbering.
8. **Default stack limit 4 GiB?** Recommended: 4 GiB whole-stack and 500 planes in QuPath, both overridable; tune after the first real movie.
9. **QuPath default "Planes" choice?** Recommended: current plane (never silently sends a whole movie); "all" is explicit and guarded.
10. **Napari axes of an untagged 3D layer (T or Z?)** Recommended: a small chooser defaulting to the tool's declared third axis, remembered per layer.
11. **`FigureOut` formats in Wave 2?** Recommended: png (default), svg, html, pdf as listed; no gif/video yet.
12. **Is HTML with JavaScript acceptable?** Recommended: yes, only from the run folder, no network, no navigation (2.5); hosts without a safe web view fall back to Open.
13. **Should Fiji show svg/html/pdf itself?** Recommended: no; png window, everything else through Open (the browser), to avoid shipping a web view.
14. **`Open()` automatic or only a button?** Recommended: automatic for run-folder results with a setting to turn it off, plus always a button; max 3 automatic opens per run.
15. **Allow URLs at all?** Recommended: yes, `LinkOut` https only, one consent per host name per session.
16. **Allow opening a path outside the run folder?** Recommended: only the paths the person chose in the form; never a path invented by the tool.
17. **Open allowlist vs denylist of suffixes?** Recommended: allowlist (3.2); a denylist always misses something.
18. **A reusable policy function for all hosts?** Recommended: yes, `openpolicy.check(path, job_dir, chosen)` in Tools, with the test vectors in 3.5; Java hosts port the same table and run the same vectors.
19. **GEFF and `TracksOut` later?** Recommended: nothing in Wave 2 blocks them; `t` / `z` columns and `PerPlane` are the shared base, and a track table is just a table with `track_id`, `t`, `y`, `x`.
20. **Where do the generated round-trip cases live?** Recommended: `tests/roundtrip_cases.py` in Tools writing a cases JSON the existing `testing` runner reads, and each host runs the same file against the example app.
