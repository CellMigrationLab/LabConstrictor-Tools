# LabConstrictor Tools

**Declare a Python analysis once; use it in napari, Fiji, QuPath, a notebook or the command line.**

A LabConstrictor app can declare **tools**: Python functions with typed inputs and outputs. LabConstrictor Tools turns those declarations into a description that every host reads to build a form, run the tool in the app's own Python environment, and put the results back: images become layers or windows, outlines become overlays or annotations, points become point ROIs, numbers go to a table or a message.

The tool runs in a separate process, so your image software never imports the app's packages and apps with conflicting dependencies live side by side. The separate process is not a security sandbox: install and run apps you trust.

!!! note "This site is the developer reference"
    It is for people who write tools, build a plugin or maintain LabConstrictor. If you use an app, go to the [LabConstrictor website](https://cellmigrationlab.github.io/LabConstrictor-Site/): it has the guides to [install an app](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/install/), to [use apps in napari, Fiji and QuPath](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/image-software/), and [what works where](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/capabilities/).

<div class="lc-doors" markdown>

<div class="lc-door" markdown>
### Write tools
You make an app and want its functions to appear in every host.

[Writing tools](AUTHORING.md) · [What each host does](HOST_FEATURES.md) · [The manifest](MANIFEST.md)
</div>

<div class="lc-door" markdown>
### Build a host
You change a plugin or the bridge between hosts and apps.

[Protocol](PROTOCOL.md) · [Where the tools live](REPOSITORIES.md) · [Conformance data](CONFORMANCE.md)
</div>

<div class="lc-door" markdown>
### Test and maintain
You check a release or run shared installs.

[Automated testing](TESTING.md) · [Operations](OPERATIONS.md) · [Publish the plugins and apps](PUBLISHING.md)
</div>

</div>

## The hosts

| Host | What it is | Repository | Install and use |
|---|---|---|---|
| [napari](https://napari.org) | A dock widget: pick an app and a tool, the form is generated from the tool's declaration | [LabConstrictor-napari](https://github.com/CellMigrationLab/LabConstrictor-napari) | [napari guide](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/napari/) |
| [Fiji](https://fiji.sc) | A menu command with a dialog generated from the declaration | [LabConstrictor-Fiji](https://github.com/CellMigrationLab/LabConstrictor-Fiji) | [Fiji guide](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/fiji/) |
| [QuPath](https://qupath.github.io) | An extension that also runs on selected annotations or the viewport of large images | [LabConstrictor-QuPath](https://github.com/CellMigrationLab/LabConstrictor-QuPath) | [QuPath guide](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/qupath/) |
| Command line | `labconstrictor-tools run`: the same registered tools in a script or batch workflow | this repository | [Install LabConstrictor Tools](INSTALL.md) |

## Try it

Install the [LabConstrictor Playground](https://github.com/CellMigrationLab/LabConstrictor-Playground) app. Its **Feature tour** makes its own small image and returns every kind of result, so you can see how your host handles each one without data of your own; **Check everything** tests your machine and writes a report you can attach to an issue.
