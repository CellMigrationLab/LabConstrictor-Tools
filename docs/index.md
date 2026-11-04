# LabConstrictor Tools

**Declare a Python analysis once; use it in napari, Fiji, QuPath, a notebook or the command line.**

A LabConstrictor app can declare **tools**: Python functions with typed inputs and outputs. LabConstrictor Tools turns those declarations into a description that every host reads to build a form, run the tool in the app's own Python environment, and put the results back: images become layers or windows, outlines become overlays or annotations, points become point ROIs, numbers go to a table or a message.

The tool runs in a separate process, so your image software never imports the app's packages and apps with conflicting dependencies live side by side. The separate process is not a security sandbox: install and run apps you trust.

<div class="lc-doors" markdown>

<div class="lc-door" markdown>
### Use apps
You have an app and want to run its tools in your image software.

[Use apps in napari, Fiji and QuPath](user-guide.md)
</div>

<div class="lc-door" markdown>
### Write tools
You make an app and want its functions to appear in every host.

[Writing tools](AUTHORING.md) · [What each host does](HOST_FEATURES.md)
</div>

<div class="lc-door" markdown>
### Test and maintain
You test a release or change the bridge.

[Testing: start here](TESTER_START_HERE.md) · [Protocol](PROTOCOL.md)
</div>

</div>

## The hosts

| Host | What it is | Repository |
|---|---|---|
| [napari](https://napari.org) | A dock widget: pick an app and a tool, the form is generated from the tool's declaration | [LabConstrictor-napari](https://github.com/CellMigrationLab/LabConstrictor-napari) |
| [Fiji](https://fiji.sc) | A command, *Plugins > LabConstrictor > LabConstrictor Tools...*, with a dialog generated from the declaration | [LabConstrictor-Fiji](https://github.com/CellMigrationLab/LabConstrictor-Fiji) |
| [QuPath](https://qupath.github.io) | An extension, *Extensions > LabConstrictor tools...*, that also runs on selected annotations or the viewport of large images | [LabConstrictor-QuPath](https://github.com/CellMigrationLab/LabConstrictor-QuPath) |
| Command line | `labconstrictor-tools run`: the same registered tools in a script or batch workflow | this repository |

## Try it

Install the [LabConstrictor Playground](https://github.com/CellMigrationLab/LabConstrictor-Playground) app. Its **Feature tour** makes its own small image and returns every kind of result, so you can see how your host handles each one without data of your own; **Check everything** tests your machine and writes a report you can attach to an issue.
