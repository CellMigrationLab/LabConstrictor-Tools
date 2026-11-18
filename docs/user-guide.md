# Use apps inside napari, Fiji and QuPath

Some apps come with **tools**: analyses you can run from napari, Fiji or QuPath, with a form for their settings. The napari and Fiji plugins and the QuPath extension show that form, run the tool, and put the result back into your software: images become layers or windows, outlines become overlays, points become point ROIs, numbers go to a log or a table.

The tool runs in the app's own Python environment, in a separate process. Your image software never imports the app's packages, so apps with conflicting dependencies can live side by side. Fiji (ImageJ) and QuPath need no Python at all; napari is itself a Python program, and its plugin is installed into the environment where napari runs.

> [!NOTE]
> The napari, Fiji and QuPath plugins are tested on Linux, Windows and macOS. [What works where](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/capabilities/) lists what each one supports today.

## Three steps

1. **Install the app** you want to use: [Install an app](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/install/). The installer registers the app on your computer, which is how the plugins find it.
2. **Install the plugin** for your software and open it. Each guide has the steps and the menu where the plugin appears: [napari](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/napari/), [Fiji](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/fiji/) or [QuPath](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/qupath/).
3. **Pick an app and a tool.** Parameters become fields with their ranges and units, and each image input accepts an image you have open or a file.

A first run needs step 1: an installed LabConstrictor app that declares tools. With none registered, the plugin has no app to list.

Found a problem? [Open an issue](https://github.com/CellMigrationLab/LabConstrictor-Tools/issues) with the host, operating system, app and the steps that show it.

## Check that everything works

Install the **LabConstrictor Playground** app and run its **Check everything** tool. It checks your computer, the installation and the GPU libraries, and writes a report you can attach to an issue. It does not test the napari, Fiji or QuPath plugins.

To check a plugin, run the Playground's **Feature tour** tool in that program. It uses every kind of setting and result the plugins support. See the guide for [napari](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/napari/), [Fiji](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/fiji/) or [QuPath](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/qupath/).

## Make your own tools

To make an app's analyses run in napari, Fiji and QuPath, see [Connect an app](https://cellmigrationlab.github.io/LabConstrictor-Site/connect/).
