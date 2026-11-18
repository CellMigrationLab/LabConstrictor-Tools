# Where the LabConstrictor tools live

LabConstrictor's tools are spread over separate repositories: a shared Python toolkit, one plugin per host, and the apps that declare the tools.

| Repository | What it contains |
|---|---|
| [LabConstrictor-Tools](https://github.com/CellMigrationLab/LabConstrictor-Tools) | the Python declarations (`@tool`, types and markers), schema generation, registry, worker, command line, notebook helpers, diagnostics and tests |
| [LabConstrictor-napari](https://github.com/CellMigrationLab/LabConstrictor-napari) | the napari dock widget, layer conversion and result display (Python package `napari-labconstrictor`, installed from the source archive of a release tag) |
| [LabConstrictor-Fiji](https://github.com/CellMigrationLab/LabConstrictor-Fiji) | the Fiji menu command, SciJava forms, ImageJ ROI handling and the worker connection. Release files: `labconstrictor-fiji-<tag>.jar`, `labconstrictor-fiji-script-<tag>.zip` (the script and its `lib` folder) and `SHA256SUMS` |
| [LabConstrictor-QuPath](https://github.com/CellMigrationLab/LabConstrictor-QuPath) | the QuPath extension: image-area export, annotation coordinates and result display. Release files: `labconstrictor-qupath-<tag>.jar`, the single script `LabConstrictorTools-all.groovy` (the only form the Script Editor can run) and `SHA256SUMS` |
| [LabConstrictor-Playground](https://github.com/CellMigrationLab/LabConstrictor-Playground) | an installable test app with 17 tools: diagnostics, synthetic image analysis and deliberately difficult cases for hosts |
| [LabConstrictor](https://github.com/CellMigrationLab/LabConstrictor) | the template that turns notebooks into installable desktop apps; its installers register an app's tools. It is not a host |

## The apps

Each app owns its analysis code and its tool declarations. Its installer registers the tools on the user's computer.

| App | Repository | Tools | Listed in napari | Fiji | QuPath |
|---|---|---|---|---|---|
| NucleiSky | [NucleiSky](https://github.com/CellMigrationLab/NucleiSky) | 2 (List the devices, Relocalize 2D) | yes | yes | yes |
| Guess the Condition | [GuessTheCondition](https://github.com/CellMigrationLab/GuessTheCondition) | 6 (five game actions and one helper) | yes | yes | yes |
| Playground | the Playground row above | 17 | yes | yes | yes |
| StarDist2D | [Stardist2D](https://github.com/CellMigrationLab/Stardist2D) | 7 | yes | yes | yes |
| VLab4Mic | [LabConstrictor-VLab4Mic](https://github.com/CellMigrationLab/LabConstrictor-VLab4Mic) | 2 (Simulate imaging of a virtual sample, Compare an image with a reference) | yes | yes | no |
| CellTracksColab | [CellTracksColab](https://github.com/CellMigrationLab/CellTracksColab) | 1 (Calculate Track Metrics) | no | no | no (`hosts: [notebook]`) |

The listing follows each app's `hosts:` line ([PROTOCOL.md](PROTOCOL.md#app-hosts-which-host-lists-an-app)). Every app's tools also run from its notebook and the command line. Each app's latest release is on its page in the [App Centre](https://cellmigrationlab.github.io/LabConstrictor-Site/) and on its GitHub Releases page. Each installer pins a Tools tag (`LC_TOOLS_PIN`); an app gets a new pin through the template sync and its next release ([OPERATIONS.md](OPERATIONS.md#pinning-tools-in-app-installers)).

## What they share

The toolkit defines the [schema and worker protocol](PROTOCOL.md). Hosts read cached schemas to build forms without importing the app's packages. When a person runs a tool, the host starts or reuses a worker in the app's own Python environment. So hosts never install an app's scientific dependencies, and apps never import napari, Fiji or QuPath.

The protocol is a shared contract, not a promise that every host shows every presentation hint the same way: [What each host does with each feature](HOST_FEATURES.md) lists the differences. Hosts must refuse and report a schema version they do not support rather than guess.

## Where to make a change

- A new marker, validation, serialisation or protocol behaviour: **LabConstrictor-Tools**.
- napari layer selection, the form or how layers are shown: **LabConstrictor-napari**.
- Fiji image windows, SciJava fields, ROIs or macros: **LabConstrictor-Fiji**.
- QuPath image regions, coordinate offsets, annotations or slide export: **LabConstrictor-QuPath**.
- Test fixtures, diagnostics or deliberate stress cases for workers: **LabConstrictor-Playground**.
- Installer registration: **the LabConstrictor template**, or the app if it changed its own installer.

The repositories are packaged differently (a Python package for Tools and the napari plugin, a jar or script for Fiji and QuPath, installers for the apps) and are released on their own schedules. How to install an app and each plugin is in [Install an app](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/install/) and the [napari](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/napari/), [Fiji](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/fiji/) and [QuPath](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/qupath/) guides; what Tools needs is in [INSTALL.md](INSTALL.md).
