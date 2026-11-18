# Install LabConstrictor Tools

You do not install `labconstrictor-tools` to use an app: the app's installer brings it. To install an app or a plugin, follow [Install an app](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/install/) and the [napari](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/napari/), [Fiji](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/fiji/) or [QuPath](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/qupath/) guide.

This page covers what the plugins need from an installed app, how to check an app, and how to install `labconstrictor-tools` by hand. Shared and network installs are in [Operations](OPERATIONS.md#many-apps-many-users-network-shares).

## What the plugins need from an app

* **labconstrictor-tools 0.3.0a1 or newer in the app** (tag `v0.3.0-alpha.1` or later). Fiji and QuPath leave out an app with an older or unknown Tools, or one without the features they need, and say why in their Log, for example: `this app's labconstrictor-tools 0.2.0rc1 is older than the 0.3.0a1 this host needs: update it`. The napari plugin itself requires `labconstrictor-tools>=0.3.0a1`. An app whose installer pins an older Tools works in the plugins only after a new release of the app ([Pinning Tools in app installers](OPERATIONS.md#pinning-tools-in-app-installers)).
* **At least one registered app.** A plugin with no app says so. Install an app, then rescan or restart the host.
* **The host named in the app's `hosts:` line** ([PROTOCOL.md](PROTOCOL.md#app-hosts-which-host-lists-an-app)). Installing a plugin does not install any app.

## Check an installed app

Run these with the app's own Python:

    <install folder>/bin/python -m labconstrictor_tools list      # Windows: <install folder>\python.exe
    <install folder>/bin/python -m labconstrictor_tools doctor

`list` shows the app and its tools; `doctor` should show no cross. If a plugin's list is empty or an app is missing, these commands say why (an interpreter that is gone, a Tools that is too old). The log is `~/.labconstrictor/logs/labconstrictor.log` ([Operations](OPERATIONS.md#when-something-goes-wrong-logs)).

## Install labconstrictor-tools by hand

For development, or to add Tools to an environment yourself. The package is not on PyPI: install the source archive of a release tag, never `main` ([Releases and tags](OPERATIONS.md#releases-and-tags)). Take the newest tag from the [Releases page](https://github.com/CellMigrationLab/LabConstrictor-Tools/releases):

    python -m pip install https://github.com/CellMigrationLab/LabConstrictor-Tools/archive/refs/tags/<tag>.zip

The address is a source archive, so no `git` is needed. For an editable install of a checkout, see the [README](https://github.com/CellMigrationLab/LabConstrictor-Tools#development).
