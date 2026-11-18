# What each host does with each feature

For app authors and plugin developers: how napari, Fiji and QuPath present each marker of a tool's declaration. For a plain summary of what a person can do in each host, read [What works where](CAPABILITIES.md) first; the notebook form and the command line are covered [below](#in-a-notebook-and-on-the-command-line).

The hosts are the napari plugin (a dock widget), the Fiji plugin (a SciJava dialog, from the jar or the script) and the QuPath extension (a JavaFX window). All three need an app whose Tools is 0.3.0a1 or newer ([INSTALL.md](INSTALL.md#what-the-plugins-need-from-an-app)). How to install and open each plugin is in its own guide: [napari](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/napari/), [Fiji](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/fiji/), [QuPath](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/qupath/).

## Feature by feature

"Plain" means the host shows an ordinary field and nothing is lost.

| Feature | napari | Fiji | QuPath |
|---|---|---|---|
| Plain parameters, bounds, units, help | yes | yes | yes |
| Input help (ⓘ after the label of each input with a description) | the description on hover and on keyboard focus; a click keeps it open | the description on hover | the description on hover and on keyboard focus; a click keeps it open |
| `Optional` ("set" box) | yes | yes ("Set <name>") | yes |
| `Group`, `Advanced` | headings; a "Show advanced settings" box | headings, including "Advanced settings" | headings; a folded "Advanced settings" section |
| `Collapsed` | yes (click the heading) | plain heading (SciJava cannot fold) | yes (titled pane) |
| `Widget("slider")`, `Widget("radio")` | slider, radio buttons | slider and radio styles | slider beside the box, radio buttons |
| `EnabledWhen` | greys out | ignored: every field stays editable | greys out |
| `PixelSizeOf` | prefilled from the layer's scale and length unit; a scale in pixel units counts as not calibrated (blank, run blocked) | prefilled from the calibration; not calibrated: blank, run blocked | prefilled from the image; not calibrated: blank, run blocked |
| `ChoicesFrom` | dropdown, updated when its inputs change | dropdown from the values of the previous run; a text field the first time | dropdown, updated when its inputs change |
| `ClearAfterRun` | yes | yes, in the form that comes back after a run | yes |
| `PickChannel` | the colours of an RGB layer, the channels of a TIFF file | a channel number | channel names |
| `RegionOf` | "use the selection" box: the selected Shapes layer | "Use the selection" box: the ROI Manager selection, else the image's ROI | "use the selection" box: the selected annotations |
| `ImageOut`, `LabelsOut` | a layer | a window | a preview with "Open in QuPath" |
| `TableOut` | a table dock | a Results table | a table in the results window |
| `Scalars` | the status line | the Log window | the results window and the status line |
| `MessageOut` | a quoted block under the status | the Log window and a dialog | a label under the status and in the results |
| `PointsOut` | a points layer, scaled like its image | point ROIs, the ROI Manager and a table | a point annotation on the open image, else a table |
| `ShapesOut` | a shapes layer (outer boundary of each part; a note when holes are dropped) | an overlay and ROI Manager entries, holes kept | annotations with measurements, holes kept |
| `Affine` | an overlay layer | an overlay window | the matrix is shown |
| `Replace` | updates the layer or dock in place | closes the previous window, overlay or ROIs | reuses the results window; replaces only the annotations the tool drew |
| Copy as command | a menu: terminal line or Python snippet | printed in the Log window after each run; menu command "Copy last run as command" | a menu: terminal line or Python snippet |
| Progress, Cancel, run details | yes; the worker is kept for repeat runs | progress, Esc to cancel, an error dialog; a new worker for each run | yes; the worker is kept for repeat runs |
| Fiji macros | — | a macro line typed by hand runs the tool without a dialog (jar only); the Macro Recorder does not record it | — |

Not available in any host yet: tracks, time and depth axes of inputs, figures as outputs, repeating a run, and batch runs. A result with known axes does open in Fiji as a hyperstack (`result_axes_v1`).

**Fiji limits.** A pixel-size field linked to an image follows that image's calibration by itself; there is no "use the image's calibration" button. A SciJava dialog cannot tell whether the person retyped the value the box already shows, so that field is cleared and the run is blocked with a message, rather than sending a value that might be wrong.

Each row has a test in the host's own suite that runs the example app `labconstrictor_tools.examples.interactions`; a change that breaks a row fails that suite.

## Behaviour shared by every host

These come from Tools and the worker, so every host behaves the same:

- **Which apps a host lists.** A host lists an app only if the app's `hosts:` line names it; an app installed with an older installer has no such line and is listed everywhere, with a sentence in the log ([PROTOCOL.md](PROTOCOL.md#app-hosts-which-host-lists-an-app)). A host also leaves out an app whose Tools is too old, with a sentence saying why.
- **Data travels as files.** Images and label images go as TIFF files: the host writes an open image to a temporary TIFF, or passes the path of the person's file. Tables and points go as CSV files, outlines as GeoJSON files, and results always come back as files. The app and the host must be on the same computer.
- **Big TIFF inputs are memory-mapped** (Tools 0.3.0a1 and later). An uncompressed, contiguous TIFF of 8 MiB or more is mapped copy-on-write; any other big TIFF is read whole, and the worker says why in the log. There is no tile-by-tile reading. `LC_TIFF_MEMMAP=0` turns it off. On Windows, a tool that keeps a reference to its input keeps the file locked until the worker ends ([OPERATIONS.md](OPERATIONS.md#troubleshooting)).
- **Shared-memory images** (`shm_order_v1`): the worker reads `C` and `F` blocks in the order they were written and refuses any other `order`. A host that sends F-ordered blocks requires `shm_order_v1` ([PROTOCOL.md](PROTOCOL.md#shared-memory-images)). The worker can read an image from a shared-memory block, but no host sends shared memory today.

## In a notebook and on the command line

"Notebook" is the form a notebook shows for a tool (`labconstrictor_tools.notebook.form`). "Command line" is `labconstrictor-tools run`. Neither is filtered by `hosts` or `host_requirements`: every registered tool runs there.

| Input | Notebook | Command line |
|---|---|---|
| Image, label image | type the path of a file | the path of a file |
| Table | type the path of a CSV file | the path of a CSV file |
| File, folder | type the path | the path |
| Number, text, yes/no, choice | yes | yes |
| Optional value left unset | a "set" box | leave it out |
| Choices filled by another tool (`ChoicesFrom`) | a text field | type the value |
| Selection as a region (`RegionOf`) | give a label image file | give a label image file |
| One channel of an image (`PickChannel`) | no: the whole image is sent | no: the whole image is sent |
| Pixel size read from the image (`PixelSizeOf`) | no: type it | no: type it |
| Part of a large image | no | no |

| Result | Notebook | Command line |
|---|---|---|
| Image, label image | a picture of the first plane | a TIFF file |
| Table | yes | a CSV file |
| Numbers and short values, message | yes | yes |
| Points | a table | a CSV file |
| Outlines | the file is named, nothing is drawn | a GeoJSON file |
| Alignment | the matrix is printed | the matrix is printed |
| File | its path is printed | yes |
| `Replace` | — | — |

| Running | Notebook | Command line |
|---|---|---|
| Runs in the app's own Python, in a separate process | no: in the notebook's own kernel | yes |
| Progress | yes | printed lines |
| Cancel | interrupt the kernel | Ctrl+C |
| Faster repeat runs (kept worker) | — | no |
| Shared log file | yes | yes |
| A run record (`run.json`), and cleanup of old results and records | no | yes |
| Details after a failure | the error line | yes |
| Run without a window (scripts, batch) | — | yes |

The notebook form shows ranges and tooltips, but no groups or "advanced" section (one flat list), no greyed-out fields, no sliders or radio buttons, and it does not clear `ClearAfterRun` fields after a run.

## How each host is tested

| | Linux | Windows | macOS |
|---|---|---|---|
| Tools (worker, command line) | automated tests | automated tests | automated tests |
| napari plugin | automated tests, full set | automated tests, full set | automated tests, full set |
| Fiji plugin | automated tests, full set | a short automated check at each release (the menu entry exists, the dialog lists an app) | the same short check, Apple silicon |
| QuPath extension | automated tests, full set | short automated checks at each release | the same short checks, Apple silicon |
| App installers | the release check installs and runs a released app on a fresh machine | the same | the same |
| Tested by people | napari and Fiji; QuPath not yet | app installs and the three plugins | app installs and the three plugins |

Automated tests run on GitHub's machines.

## Host feature ids (for host_requirements)

An app can require a host feature by id in `host_requirements.<host>.features` ([PROTOCOL.md](PROTOCOL.md#host-requirements-which-plugin-an-app-needs)). Each host declares its ids next to its version and passes both to the rule. An id is never renamed or reused; it is added in the release that implements it.

| Host | Id | Meaning | Since |
|---|---|---|---|
| every host | `host_requirements_v1` | the host applies the `host_requirements` rule (a host without it ignores the field) | napari v0.1.0-alpha.5, Fiji v0.1.0-alpha.7, QuPath v0.1.0-alpha.7 |
| QuPath | `shapes_owner_v1` | Replace removes only the annotations tagged with the run's `labconstrictor.output` | v0.1.0-alpha.6 |
| Fiji | `log_progress_v1` | progress and a heartbeat in the Log window during long runs | v0.1.0-alpha.6 |

| Host | Its version, as passed to `check` |
|---|---|
| napari | `importlib.metadata.version("napari-labconstrictor")` |
| Fiji | the jar manifest's `Implementation-Version` (the release tag). The loose script has none: `None` (unknown). The system property `lc.fiji.plugin_version` replaces it in tests |
| QuPath | the jar's `Implementation-Version` (the release tag). The system property `lc.qupath.plugin_version` replaces it in tests |

## Copy as command: the format every host produces

The reference implementation is `labconstrictor_tools.command` (`command_line`, `python_snippet`). Fiji and QuPath build the same text.

- **Terminal line:** `<app python> -m labconstrictor_tools run <App> <tool id> name=value ...`, one `name=value` per parameter that is set (unset optional parameters are left out), booleans as `true`/`false`. Each argument is quoted for the person's shell: POSIX `shlex.quote` rules, or on Windows the C runtime (`CommandLineToArgvW`) rules for cmd.exe:
  - a text with only letters, digits and `-_.:/\=+,` stays bare; anything else, and the empty text, goes in double quotes;
  - backslashes are literal, except a run in front of a `"` (doubled, then `\"`) and a run at the end of the text (doubled, in front of the closing quote);
  - inside the quotes `^ & | < >` are literal for cmd.exe;
  - limits that cannot be escaped without breaking the C runtime rules: cmd.exe expands `%NAME%` even inside quotes when NAME is a defined variable; a text with an odd number of `"` upsets cmd.exe's quote tracking later in the line; a line break cannot be pasted into cmd.exe; PowerShell reads quotes by other rules (use the Python snippet there).

  Every host must produce exactly the strings in `tests/quote_vectors.json` (a list of `{text, posix, windows}`).
- **Images, labels, tables, files:** a layer or window cannot be named on a command line, so each required one gets a placeholder (`image=image.tif`) and the text starts with `# replace the file for: image`. Where a host knows the file behind the input, it uses that path.
- **Python snippet:** `client.run_once("<App>", "<tool id>", {...})` with the same values as Python literals, then a print of the status and results.
