# What each host does with each feature

Hosts: **Napari** (dock widget), **Fiji** (SciJava dialog, Groovy script or jar), **QuPath** (JavaFX window). "plain" = shown as an ordinary field, nothing is lost.

| Feature | Napari | Fiji | QuPath |
|---|---|---|---|
| Plain parameters, bounds, units, tooltips | yes | yes | yes |
| `Optional` / "set" box | yes | yes ("Set <name>") | yes |
| `Group` headings, `Advanced` section | yes (checkbox toggles it) | headings in the dialog | heading, folded section |
| `Collapsed` (accordion) | yes (click the heading) | plain heading (SciJava cannot fold) | yes (titled pane) |
| `Widget("slider")` / `Widget("radio")` | `FloatSlider`, `Slider`, radio buttons | slider and radio styles | slider beside the box, radio buttons |
| `Copy as command` (host feature, no manifest change) | button with a menu: terminal line or Python snippet | the Log after each run; menu entry "Copy last run as command" | menu button: terminal line or Python snippet |
| `EnabledWhen` | greys out | ignored: every field stays editable | greys out |
| `PixelSizeOf` | prefilled from the layer's scale and length unit; a bare scale with pixel units is *not calibrated* (blank, run blocked) | prefilled from the calibration; uncalibrated: blank, run blocked | prefilled from the image; uncalibrated: blank, run blocked |
| `ChoicesFrom` (dropdown) | yes, updates when its inputs change | yes, from the previous run's values; text field the first time | yes, updates when its inputs change |
| `ClearAfterRun` | yes | not needed (a fresh dialog every run) | yes |
| `Replace` | updates the layer or dock in place | closes the previous window, overlay or ROIs | reuses the results window, replaces the annotation |
| `PickChannel` | RGB colours, channels of a TIFF file | a channel number | channel names |
| `RegionOf` (run on the selection) | "use the selection" box: the selected Shapes layer (labels 1..N) | "Use the selection" box: ROI Manager selection, else the image ROI (labels 1..N) | "use the selection" box: selected annotations (labels 1..N) |
| `ImageOut`, `LabelsOut` | layer | window | preview and "Open in QuPath" |
| `TableOut` | table dock | Results table | table in the results window |
| `Scalars` | in the status line | in the Log | in the results window and status |
| `MessageOut` | quoted block under the status | Log and a dialog | label under the status and in the results |
| `PointsOut` | points layer (scaled like its image) | point ROIs, ROI Manager, table | point annotation on the open image, else a table |
| `ShapesOut` | shapes layer (outer boundary per part, note for holes) | overlay and ROI Manager entries (holes kept) | annotations with measurements (holes kept) |
| `Affine` | overlay layer | overlay window | matrix shown |
| Shared-memory image `order` (feature id `shm_order_v1`, Tools 0.3.0a1) | Worker side, same for every host: `C` / `F` (and Appose's `C_ORDER` / `F_ORDER`) are read in the order they were written, anything else is refused with `unreadable_image`. A host that sends an F-ordered block must require `shm_order_v1` ([PROTOCOL.md](PROTOCOL.md#tools-version-and-features)). Which host sends which order is not checked in this repository | same | same |
| Big TIFF inputs are memory-mapped (Tools 0.3.0a1, no feature id) | Worker side, same for every host, nothing to do: a TIFF of 8 MiB or more that is uncompressed and contiguous is mapped copy-on-write; any other big TIFF is read the plain way and the worker says why in the log and on stderr (`LC_TIFF_MEMMAP=0` turns it off). On Windows a tool that keeps its input keeps the file locked until the worker ends ([OPERATIONS.md](OPERATIONS.md#troubleshooting)) | same | same |
| Per-host listing of apps (`hosts` of the app, feature id `app_hosts_v1`, Tools 0.3.0a1) | lists an app only if its registry entry names `napari` (or has no `hosts`, logged); an excluded app is skipped with the sentence of [PROTOCOL.md](PROTOCOL.md#app-hosts-which-host-lists-an-app) | same, for `fiji` | same, for `qupath` |
| Progress, Cancel, kept worker, run details | yes | progress and Esc | yes |
| Macro / command recording | no | yes (macro recorder, replay) | no |

Not yet in any host (see the roadmap): shapes outputs, run on the selected region, tracks, slider and radio styles, time-lapse and 3D axes, figure output, Repeat, batch.

How this table is kept honest: each row has a test in the host's own suite that runs the example app (`labconstrictor_tools.examples.interactions`); a change that breaks a row fails that suite.

## Copy as command: the format every host produces

Reference implementation: `labconstrictor_tools.command` (`command_line`, `python_snippet`). Fiji and QuPath build the same text.

- **Terminal line:** `<app python> -m labconstrictor_tools run <App> <tool id> name=value ...`, one `name=value` per parameter that is set (unset optional parameters are left out), booleans as `true`/`false`, each argument quoted for the person's shell: POSIX `shlex.quote` rules, or on Windows the C runtime / CommandLineToArgvW rules for **cmd.exe**. Windows rules: a text with only letters, digits and `-_.:/\=+,` stays bare; anything else (and the empty text) goes in double quotes; backslashes are literal except a run in front of a `"` (doubled, then `\"`) and a run at the end of the text (doubled, in front of the closing quote). Inside the quotes `^ & | < >` are literal for cmd.exe and need nothing. Known limits, not escapable without breaking the C runtime rules: cmd.exe expands `%NAME%` even inside quotes when NAME is a defined variable; a text with an odd number of `"` upsets cmd.exe's own quote tracking for operators later in the line; a line break cannot be pasted into cmd.exe; PowerShell reads quotes by other rules (use the Python snippet there). Every host must produce exactly the strings in `tests/quote_vectors.json` (list of `{text, posix, windows}`); Tools tests `command.quote` against it (`tests/test_quote_vectors.py`).
- **Images, labels, tables, files:** a layer or window cannot be named on a command line, so each required one gets a placeholder (`image=image.tif`) and the text starts with `# replace the file for: image`. Where a host knows the file behind the input, it uses that path.
- **Python snippet:** `client.run_once("<App>", "<tool id>", {...})` with the same values as Python literals, then a print of the status and results.
- Test: the copied line and the copied snippet, run for real, give the same values as the form (`tests/test_command.py`).
