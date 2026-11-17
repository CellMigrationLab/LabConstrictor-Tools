# Use apps inside napari, Fiji and QuPath

Some apps declare **tools**: scientific functions with typed inputs. A plugin for your image software turns each tool into a form, runs it, and puts the result back into your software: images become layers or windows, outlines become overlays, points become point ROIs, numbers go to a log or a table.

The tool runs in the app's own Python environment, in a separate process. Your image software never imports the app's packages, so apps with conflicting dependencies can live side by side. Fiji (ImageJ) and QuPath need no Python at all; napari is itself a Python program, and its plugin is installed into the environment where napari runs.

> [!NOTE]
> **What each plugin supports.** The napari, Fiji and QuPath plugins have been tested on Linux, Windows and macOS. [What works where](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/capabilities/) lists what each one supports today.

## Three steps

1. **Install the app** you want to use: [Install an app](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/install/). The installer registers the app on your computer, which is how the plugins find it.
2. **Install the plugin** for your software and open it. Each guide has the steps and the menu where the plugin appears: [napari](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/napari/), [Fiji](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/fiji/) or [QuPath](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/qupath/).
3. **Pick an app and a tool.** Parameters become fields with their ranges and units, and each image input accepts an image you have open or a file.

A first run needs step 1: an installed LabConstrictor app that declares tools. With none registered, the plugin has no app to list.

Found a problem? [Open an issue](https://github.com/CellMigrationLab/LabConstrictor-Tools/issues) with the host, operating system, app and the steps that show it.

## Check that everything works

Install the **LabConstrictor Playground** app and press **Check everything**. It tests your machine and every plugin feature, and writes a report you can attach to an issue.

## Make your own tools

App authors declare tools once, in Python, and get all of this without writing any interface code. See [Writing tools](https://github.com/CellMigrationLab/LabConstrictor-Tools/blob/main/docs/AUTHORING.md).
