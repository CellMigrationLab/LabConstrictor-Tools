# What works where

A LabConstrictor app can offer **tools**: analyses that you run from napari, Fiji or QuPath. This page lists what the napari and Fiji plugins and the QuPath extension support today, so you can check before you plan your work. For the newest versions, see each plugin's guide: [napari](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/napari/), [Fiji](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/fiji/), [QuPath](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/qupath/).

**Yes** works. **Partial** works with the limit written next to it. **No** is not available. **—** does not apply.

## What you can give a tool

| Input | napari | Fiji | QuPath |
|---|---|---|---|
| Image | Yes: an open layer or a file | Yes: an open image or a file | Yes: the open image, an image of the project, or a file |
| Label image | Yes: an open layer or a file | Yes: an open image or a file | Yes, as for images |
| Table | Partial: a CSV file, not an open table | Partial: a CSV file, not an open table | Partial: a CSV file |
| File, folder | Yes | Yes | Yes |
| Number, text, yes/no, choice | Yes | Yes | Yes |
| Optional value left unset | Yes: a "set" box | Yes: a "Set" box | Yes: a "set" box |
| Choices filled by another tool | Yes | Partial: from the values of the previous run; a text field the first time | Yes |
| Selection as a region | Yes: the selected Shapes layer | Yes: the ROI Manager selection, or the ROI of the image | Yes: the selected annotations |
| One channel of an image | Yes: a colour of an RGB layer, a channel of a TIFF file | Yes: by channel number | Yes: by channel name |
| Pixel size read from the image | Yes | Yes | Yes |
| Part of a large image | No: the whole image | No: the whole image | Yes: the whole image, the selected annotations or the current view |

Good to know:

- **Image files** are TIFF or OME-TIFF. Other formats work only if the app includes the `imageio` package.
- **Pixel size is never guessed.** If the image has no usable calibration, the field stays empty and the run is refused until you type a value. A value you type is always kept.
- **A tool made for 2D images refuses a stack.** No host picks a plane for you. In QuPath, choosing an image area sends the plane you are looking at.
- **QuPath sends at most 100 000 000 pixels** of one plane. Choose a smaller area for a whole-slide image.

## What a tool can give back

| Result | napari | Fiji | QuPath |
|---|---|---|---|
| Image, label image | Yes: a new layer | Yes: a new window; a time-lapse or stack opens with its dimensions when the tool states its axes | Partial: a preview, with an "Open in QuPath" button |
| Table | Yes: a table panel | Yes: a Results table | Yes: a table in the results window |
| Numbers and short values | Yes: in the status line | Yes: in the Log window | Yes: in the results window |
| Message | Yes | Yes: the Log window and a dialog | Yes |
| Points | Yes: a points layer on the image | Yes: point ROIs, the ROI Manager and a table | Yes: a point annotation on the open image, otherwise a table |
| Outlines | Partial: a shapes layer; holes are not drawn | Yes: an overlay and ROI Manager entries, holes kept | Yes: annotations with measurements, holes kept |
| Alignment (how to move one image onto another) | Yes: an overlay layer | Yes: an overlay window | Partial: the matrix is shown |
| File | Yes: its path is shown | Yes: its path is in the Log window | Yes |
| A new run replaces the previous result | Yes | Yes | Yes: only the annotations the tool drew itself |

Good to know:

- **Points and outlines land on the image they belong to**, also when the napari layer is scaled or moved, or when QuPath sent only an area.
- **Very large results are cut for display, never in the files.** napari and QuPath show the first 100 000 rows of a table. napari draws at most 50 000 outlines and does not load a result image over 4 GiB. The tool's own files hold everything.

## Running a tool

| | napari | Fiji | QuPath |
|---|---|---|---|
| Runs in the app's own Python, in a separate process | Yes | Yes | Yes |
| Progress | Yes | Yes: a bar, and lines in the Log window | Yes |
| Cancel | Yes | Yes: press Esc | Yes |
| Faster repeat runs (the worker stays open) | Yes: on by default, closed after 10 idle minutes | No: a new worker for each run | Yes: can be switched off |
| Shared log file | Yes | Yes | Yes |
| A record of each run (`run.json`) | Yes | Yes | Yes |
| Old results and records removed automatically | Yes | Yes | Yes |
| Details after a failure | Yes: a Details button | Yes: an error dialog | Yes: a Details button |
| Copy the run as a command | Yes: a terminal line or a Python snippet | Yes: printed in the Log window after each run; also the menu command *Copy last run as command* | Yes: a terminal line or a Python snippet |
| Fiji macros | — | Partial: a macro line you write by hand runs a tool without a dialog (jar install only). The Macro Recorder does not record it yet | — |
| Run without a window (scripts, batch) | No: use the command line | No: use the command line | No: use the command line |

Good to know:

- **Cancel always ends the run.** A tool that does not react is stopped after 3 seconds, and nothing it started is left running.
- **The log** is `~/.labconstrictor/logs/labconstrictor.log`. Every front-end writes to it.
- **Run records** are in `~/.labconstrictor/runs/`. Each holds the app, the tool, the values you used, the status and the error if there was one. It never holds pixel data.
- **Old results are removed automatically.** Only the newest 20 result folders and the newest 50 run records are kept. Copy a result you want to keep to a folder of your own.
- **A copied command repeats the run outside the host.** It cannot name an unsaved image, a selection or a single channel: it says so in a comment line and uses the file instead.
- **The app and the host must be on the same computer.** The host sends images to the tool as TIFF files and gets the results back as files.

## The form

| | napari | Fiji | QuPath |
|---|---|---|---|
| Ranges, units and help text | Yes | Yes: help on hover only | Yes |
| Groups and an "advanced" section | Yes | Partial: headings, nothing folds | Yes |
| Fields greyed out when they do not apply | Yes | No: every field stays editable | Yes |
| Sliders and radio buttons | Yes | Yes | Yes |
| A field goes back to its default after a run | Yes | Yes | Yes |

A number you type outside the allowed range is refused with a sentence. It is never changed to fit.

## Apps, plugins and versions

| | napari | Fiji | QuPath |
|---|---|---|---|
| One plugin for every app (no plugin per app) | Yes | Yes | Yes |
| Apps with conflicting Python packages side by side | Yes | Yes | Yes |
| The app chooses which hosts list it (`hosts`) | Yes | Yes | Yes |
| The app can ask for a newer plugin (`host_requirements`) | Yes | Yes | Yes |
| An app whose Tools is too old is left out, with a sentence saying why | Yes | Yes | Yes |

- The app's installer registers its tools. A host lists an app only if the app names that host. An app installed with an old installer names no host and is listed everywhere.
- With `host_requirements`, an older plugin still lists the app and tells you which plugin to update. The app author can make this a refusal.
- All three plugins need an app with Tools `0.3.0a1` or newer inside it.

## Operating systems

The napari and Fiji plugins and the QuPath extension work on Linux, Windows and macOS (on a Mac, also with Apple silicon). Automated tests check each of them on all three systems. People have installed apps and used the three plugins on Windows and macOS, and napari and Fiji on Linux; QuPath on Linux has automated tests only.

If something does not work for you, please [tell us what you find](https://github.com/CellMigrationLab/LabConstrictor-Tools/issues).

## Not yet available

- Time-lapse, 3D data and tracks as such: hosts do not yet tell a tool which axis is time or depth, and no host shows tracks.
- Figures as a result type.
- Running one tool over many images from a host (use the command line).
- A Fiji update site, a napari plugin on PyPI and a QuPath catalog. See [Publish the plugins and apps](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/publishing/).

## More detail

- For app authors and developers (the marker behind each row, the notebook form and the command line, how data travels, how each host is tested): [What each host does with each feature](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/host-features/).
- How to install an app: [Install an app](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/install/). How to install each plugin: the [napari](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/napari/), [Fiji](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/fiji/) and [QuPath](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/qupath/) guides.
- Logs, shared installs and known limits: [Operations and troubleshooting](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/tools-operations/).
