# Use apps inside napari, Fiji and QuPath

Some apps declare **tools**: scientific functions with typed inputs. A plugin for your image software turns each tool into a form, runs it, and puts the result back into your software: images become layers or windows, outlines become overlays, points become point ROIs, numbers go to a log or a table.

The tool runs in the app's own Python environment, in a separate process. Your image software never imports the app's packages, so apps with conflicting dependencies can live side by side. Fiji and QuPath need no Python at all; napari is itself a Python program, and its plugin is installed into the environment where napari runs.

> [!WARNING]
> **Under heavy construction.** The napari, Fiji and QuPath plugins are untested and unlikely to be stable. Expect bugs, missing features and changes without notice. Each plugin's own guide says what stage it is at.

## Three steps

1. **Install the app** you want to use. The installer registers the app on your computer, which is how the plugins find it.
2. **Install the plugin** for your software: [napari](https://github.com/CellMigrationLab/napari-labconstrictor/blob/main/docs/user-guide.md), [Fiji](https://github.com/CellMigrationLab/LabConstrictor-Fiji/blob/main/docs/user-guide.md) or [QuPath](https://github.com/CellMigrationLab/LabConstrictor-QuPath/blob/main/docs/user-guide.md).
3. **Open it**:
   - napari: Plugins > LabConstrictor tools
   - Fiji: Plugins > LabConstrictor > LabConstrictor Tools...
   - QuPath: Extensions > LabConstrictor tools...

Then pick an app and a tool. Parameters become fields with their ranges and units, and each image input accepts an image you have open or a file.

Help with testing is welcome: the [human test protocol](https://github.com/CellMigrationLab/LabConstrictor-Tools/blob/main/docs/HUMAN_TEST_PROTOCOL.md) says what to try.

## Check that everything works

Install the **LabConstrictor Playground** app and press **Check everything**. It tests your machine and every plugin feature, and writes a report you can attach to an issue.

## Make your own tools

App authors declare tools once, in Python, and get all of this without writing any interface code. See the [authoring guide](https://github.com/CellMigrationLab/LabConstrictor-Tools/blob/main/docs/AUTHORING.md).
