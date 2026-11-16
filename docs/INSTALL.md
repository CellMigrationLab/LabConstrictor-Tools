# Install LabConstrictor Tools

You do not install this package to use an app: the app's installer brings it. The install guides for people who use apps are on the LabConstrictor website, and each is kept in one place:

- [Install an app](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/install/)
- [Install the napari plugin](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/napari/)
- [Install the Fiji plugin](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/fiji/)
- [Install the QuPath extension](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/qupath/)

This page keeps what belongs to Tools itself: what the plugins need from an installed app, how to check one, and how to install `labconstrictor-tools` by hand. Shared and network installs are in [Operations](OPERATIONS.md#many-apps-many-users-network-shares).

## What the plugins need from an app

* **labconstrictor-tools 0.3.0a1 or newer in the app** (tag `v0.3.0-alpha.1` or later). Fiji and QuPath leave out an app with an older Tools (version below 0.3.0a1, or missing, or without the feature `reserved_inputs_v1`) with a sentence in the Log (`this app's labconstrictor-tools 0.2.0rc1 is older than the 0.3.0a1 this host needs: update it`); QuPath also refuses the run with it. The napari plugin requires `labconstrictor-tools>=0.3.0a1`. Apps released with an older pin (`v0.2.0-rc.1`) are therefore not usable in Fiji and QuPath until they are re-released ([Pinning Tools in app installers](OPERATIONS.md#pinning-tools-in-app-installers)).
* **At least one registered app.** A plugin with no app says so; install an app, then rescan or restart the host.
* Which host shows which app is the app's own `hosts:` declaration ([PROTOCOL.md](PROTOCOL.md#app-hosts-which-host-lists-an-app)); installing a host plugin does not install any app.

## Check an installed app

The installer registers the app's tools. With the app's own Python:

    <install folder>/bin/python -m labconstrictor_tools list      # Windows: <install folder>\python.exe
    <install folder>/bin/python -m labconstrictor_tools doctor

`list` shows the app and its tools; `doctor` shows no cross. If a plugin's list is empty or an app is missing, these two commands say why (an interpreter that is gone, a Tools that is too old), and the log is `~/.labconstrictor/logs/labconstrictor.log` ([Operations](OPERATIONS.md#when-something-goes-wrong-logs)).

## Install labconstrictor-tools by hand

For development, or to add Tools to an environment yourself. Nothing is on PyPI yet: install the source archive of a release tag, never `main` ([Releases and tags](OPERATIONS.md#releases-and-tags)). Take the newest tag from the [Releases page](https://github.com/CellMigrationLab/LabConstrictor-Tools/releases):

    python -m pip install https://github.com/CellMigrationLab/LabConstrictor-Tools/archive/refs/tags/<tag>.zip

The address is a source archive, so no `git` program is needed. An editable install of a checkout for development is in the [README](https://github.com/CellMigrationLab/LabConstrictor-Tools#development).
