# Publish the plugins and apps

Where each LabConstrictor plugin and app is released today. For maintainers of the plugins and for app authors.

If you only want to install something, use [Install an app](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/install/) or the guide of your plugin: [napari](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/napari/), [Fiji](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/fiji/) or [QuPath](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/qupath/).

## Where things stand

| What | How people install it today |
|---|---|
| Fiji plugin | The jar from the GitHub release, installed by hand ([Fiji guide](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/fiji/)) |
| napari plugin | `pip install` from the GitHub tag ([napari guide](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/napari/)) |
| QuPath extension | The jar from the GitHub release, installed by hand ([QuPath guide](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/qupath/)) |
| Apps | The installer from the app's GitHub release, found through its page in the LabConstrictor App Centre |

Every release is a GitHub release made by a maintainer. None of the plugins is in a Fiji update site, on PyPI or in a QuPath extension catalog yet.

## Fiji

Each release of [LabConstrictor-Fiji](https://github.com/CellMigrationLab/LabConstrictor-Fiji/releases) carries `labconstrictor-fiji-<tag>.jar`, a script zip and `SHA256SUMS`. People install the jar by hand, as the [Fiji guide](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/fiji/) says, and replace it by hand to update.

## napari

The plugin is a Python package, `napari-labconstrictor`, in the repository [LabConstrictor-napari](https://github.com/CellMigrationLab/LabConstrictor-napari). It is installed with `pip` from the source archive of a GitHub tag, together with Tools; the command is in the [napari guide](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/napari/).

Neither `napari-labconstrictor` nor `labconstrictor-tools` is on PyPI.

## QuPath

Each release of [LabConstrictor-QuPath](https://github.com/CellMigrationLab/LabConstrictor-QuPath/releases) carries `labconstrictor-qupath-<tag>.jar`, a single-file script and `SHA256SUMS`. People install the jar by hand, as the [QuPath guide](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/qupath/) says.

## Apps

App authors do not publish to any store. To make an app available through the App Centre:

1. **Release.** A GitHub release of the app's repository builds the installers and attaches them ([Create executable installers](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/executable-creation/)).
2. **Describe.** The repository holds a small file, `labconstrictor-app.yaml`, that says what the app is ([Describe your app](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/app-manifest/)).
3. **List.** The author sends the repository address through the [submission form](https://cellmigrationlab.github.io/LabConstrictor-Site/submit/). A check runs on the file and the release; a maintainer then adds the app to the App Centre.

After that, the app's page always shows the latest release. The installers stay on the app's own GitHub release; the App Centre hosts no files.

The apps' tools need no publishing of their own. The installer registers them on the user's computer, and the plugins find them there.
