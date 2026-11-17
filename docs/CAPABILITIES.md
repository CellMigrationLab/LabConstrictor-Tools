# What works where

A LabConstrictor app can offer **tools**: analysis steps that you run from napari, Fiji, QuPath, a notebook or the command line. This page lists what each of them supports today, so you can check before you plan your work.

**Yes** works. **Partial** works with the limit written next to it. **No** is not available. **—** does not apply. Nothing on this page is a promise for the future unless it says *planned*.

This page describes Tools `v0.3.0-alpha.4`, the napari plugin `v0.1.0-alpha.5`, and the Fiji and QuPath plugins `v0.1.0-alpha.7`.

"Notebook" is the form a notebook shows for a tool (`labconstrictor_tools.notebook.form`). "Command line" is `labconstrictor-tools run`.

## What you can give a tool

| Input | napari | Fiji | QuPath | Notebook | Command line |
|---|---|---|---|---|---|
| Image | Yes: an open layer or a file | Yes: an open image or a file | Yes: the open image, an image of the project, or a file | Partial: type the path of a file | Yes: the path of a file |
| Label image | Yes: an open layer or a file | Yes: an open image or a file | Yes, as for images | Partial: type the path of a file | Yes: the path of a file |
| Table | Partial: a CSV file, not an open table | Partial: a CSV file, not an open table | Partial: a CSV file | Partial: type the path of a CSV file | Yes: the path of a CSV file |
| File, folder | Yes | Yes | Yes | Partial: type the path | Yes |
| Number, text, yes/no, choice | Yes | Yes | Yes | Yes | Yes |
| Optional value left unset | Yes: a "set" box | Yes: a "Set" box | Yes: a "set" box | Yes: a "set" box | Yes: leave it out |
| Choices filled by another tool | Yes | Partial: from the values of the previous run; a text field the first time | Yes | No: a text field | No: type the value |
| Selection as a region | Yes: the selected Shapes layer | Yes: the ROI Manager selection, or the ROI of the image | Yes: the selected annotations | No: give a label image file | No: give a label image file |
| One channel of an image | Yes: a colour of an RGB layer, a channel of a TIFF file | Yes: by channel number | Yes: by channel name | No: the whole image is sent | No: the whole image is sent |
| Pixel size read from the image | Yes | Yes | Yes | No: type it | No: type it |
| Part of a large image | No: the whole image | No: the whole image | Yes: the whole image, the selected annotations or the current view | No | No |

Good to know:

- **Image files** are TIFF or OME-TIFF. Other formats work only if the app includes the `imageio` package.
- **Pixel size is never guessed.** If the image has no usable calibration, the field stays empty and the run is refused until you type a value. A value you type is always kept.
- **A tool made for 2D images refuses a stack.** No host picks a plane for you. In QuPath, choosing an image area sends the plane you are looking at.
- **QuPath sends at most 100 000 000 pixels** of one plane. Choose a smaller area for a whole-slide image.

## What a tool can give back

| Result | napari | Fiji | QuPath | Notebook | Command line |
|---|---|---|---|---|---|
| Image, label image | Yes: a new layer | Yes: a new window; a time-lapse or stack opens with its dimensions when the tool states its axes | Partial: a preview, with an "Open in QuPath" button | Partial: a picture of the first plane | Yes: a TIFF file |
| Table | Yes: a table panel | Yes: a Results table | Yes: a table in the results window | Yes | Yes: a CSV file |
| Numbers and short values | Yes: in the status line | Yes: in the Log window | Yes: in the results window | Yes | Yes |
| Message | Yes | Yes: the Log window and a dialog | Yes | Yes | Yes |
| Points | Yes: a points layer on the image | Yes: point ROIs, the ROI Manager and a table | Yes: a point annotation on the open image, otherwise a table | Partial: a table | Yes: a CSV file |
| Outlines | Partial: a shapes layer; holes are not drawn | Yes: an overlay and ROI Manager entries, holes kept | Yes: annotations with measurements, holes kept | Partial: the file is named, nothing is drawn | Yes: a GeoJSON file |
| Alignment (how to move one image onto another) | Yes: an overlay layer | Yes: an overlay window | Partial: the matrix is shown | Partial: the matrix is printed | Partial: the matrix is printed |
| File | Yes: its path is shown | Yes: its path is in the Log window | Yes | Yes: its path is printed | Yes |
| A new run replaces the previous result | Yes | Yes | Yes: only the annotations the tool drew itself | — | — |

Good to know:

- **Points and outlines land on the image they belong to**, also when the napari layer is scaled or moved, or when QuPath sent only an area.
- **Very large results are cut for display, never in the files.** napari and QuPath show the first 100 000 rows of a table. napari draws at most 50 000 outlines and does not load a result image over 4 GiB. The tool's own files hold everything.

## Running a tool

| | napari | Fiji | QuPath | Notebook | Command line |
|---|---|---|---|---|---|
| Runs in the app's own Python, in a separate process | Yes | Yes | Yes | No: in the notebook's own kernel | Yes |
| Progress | Yes | Yes: a bar, and lines in the Log window | Yes | Yes | Yes: printed lines |
| Cancel | Yes | Yes: press Esc | Yes | No: interrupt the kernel | Yes: Ctrl+C |
| Faster repeat runs (the worker stays open) | Yes: on by default, closed after 10 idle minutes | No: a new worker for each run | Yes: can be switched off | — | No |
| Shared log file | Yes | Yes | Yes | Yes | Yes |
| A record of each run (`run.json`) | Yes | Yes | Yes | No | Yes |
| Old results and records removed automatically | Yes | Yes | Yes | No | Yes |
| Details after a failure | Yes: a Details button | Yes: an error dialog | Yes: a Details button | Partial: the error line | Yes |
| Copy the run as a command | Yes: a terminal line or a Python snippet | Yes: printed in the Log window after each run; also the menu command *Copy last run as command* | Yes: a terminal line or a Python snippet | — | — |
| Fiji macros | — | Partial: a macro line you write by hand runs a tool without a dialog (jar install only). The Macro Recorder does not record it yet | — | — | — |
| Run without a window (scripts, batch) | No | No | No | — | Yes |

Good to know:

- **Cancel always ends the run.** A tool that does not react is stopped after 3 seconds, and nothing it started is left running.
- **The log** is `~/.labconstrictor/logs/labconstrictor.log`. Every front-end writes to it.
- **Run records** are in `~/.labconstrictor/runs/`. Each holds the app, the tool, the values you used, the status and the error if there was one. It never holds pixel data.
- **Cleanup** keeps the newest 20 result folders and the newest 50 run records. It removes only folders that LabConstrictor made and finished. You can look first with `labconstrictor-tools prune --dry-run`.
- **A copied command repeats the run outside the host.** It cannot name an unsaved image, a selection or a single channel: it says so in a comment line and uses the file instead.

## The form

| | napari | Fiji | QuPath | Notebook |
|---|---|---|---|---|
| Ranges, units and help text | Yes | Yes: help on hover only | Yes | Partial: ranges and tooltips |
| Groups and an "advanced" section | Yes | Partial: headings, nothing folds | Yes | No: one flat list |
| Fields greyed out when they do not apply | Yes | No: every field stays editable | Yes | No |
| Sliders and radio buttons | Yes | Yes | Yes | No |
| A field goes back to its default after a run | Yes | Yes | Yes | No |

A number you type outside the allowed range is refused with a sentence. It is never changed to fit.

## How data travels

| | Status |
|---|---|
| Images and label images | As **TIFF files**. The host writes an open image to a temporary TIFF, or passes the path of your file. Results come back as TIFF files. |
| Tables and points | As CSV files. |
| Outlines | As GeoJSON files. |
| Large TIFF files | The worker maps an uncompressed TIFF of 8 MiB or more into memory instead of reading it whole. Other files are read whole; there is no tile-by-tile reading. |
| Shared memory | **Not used by any host.** The worker can read an image from a shared-memory block, and Tools tests this on Linux, Windows and macOS. napari, Fiji and QuPath all send TIFF files, and results are always files. In our measurements (Linux only) shared memory gave no gain for napari; it could help Fiji with images above about 256 MiB. Not planned for a release yet. |
| Remote computers | No. The app and the host must be on the same computer. |

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
- All three plugins need Tools `0.3.0a1` or newer inside the app.
- The notebook and the command line are never filtered: every registered tool runs there.

## Operating systems

| | Linux | Windows | macOS |
|---|---|---|---|
| Tools (worker, command line) | Automated tests | Automated tests | Automated tests |
| napari plugin | Automated tests, full set | Automated tests, full set | Automated tests, full set |
| Fiji plugin | Automated tests, full set | A short automated check at each release (the menu entry exists, the dialog lists an app) | The same short check, Apple silicon |
| QuPath extension | Automated tests, full set | Short automated checks at each release | The same short checks, Apple silicon |
| App installers | The release check installs and runs a released app on a fresh machine | The same | The same |
| Tested by people | napari and Fiji: yes. QuPath: not yet | Yes: app installs and the three plugins | Yes: app installs and the three plugins |

Automated tests run on GitHub's machines; people have also installed apps and used the plugins on Windows and macOS. If something does not work for you, please [tell us what you find](https://github.com/CellMigrationLab/LabConstrictor-Tools/issues).

## Not yet available

- Time-lapse, 3D data and tracks as such: hosts do not yet tell a tool which axis is time or depth, and no host shows tracks.
- Figures as a result type.
- Running one tool over many images from a host (use the command line).
- A Fiji update site, a napari plugin on PyPI and a QuPath catalog. See [Publish the plugins and apps](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/publishing/).

## More detail

- For app authors, the marker behind each row and each host's exact behaviour: [What each host does with each feature](https://cellmigrationlab.github.io/LabConstrictor-Tools/HOST_FEATURES/).
- How to install an app: [Install an app](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/install/). How to install each plugin: the [napari](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/napari/), [Fiji](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/fiji/) and [QuPath](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/qupath/) guides.
- Logs, shared installs and known limits: [Operations and troubleshooting](https://cellmigrationlab.github.io/LabConstrictor-Tools/OPERATIONS/).
