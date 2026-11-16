# Publish the plugins and apps

Where each LabConstrictor plugin and app is released today, and what it takes to make it installable from inside Fiji, napari and QuPath. This page is for maintainers of the plugins and for app authors.

If you only want to install something, use [Install an app](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/install/) or the guide of your plugin: [napari](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/napari/), [Fiji](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/fiji/) or [QuPath](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/qupath/).

## Where things stand

| What | How people install it today | The easier route | Status of the easier route |
|---|---|---|---|
| Fiji plugin | The jar from the GitHub release, installed by hand ([Fiji guide](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/fiji/)) | An ImageJ update site | Not yet available |
| napari plugin | `pip install` from the GitHub tag ([napari guide](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/napari/)) | PyPI, which also lists it in napari's plugin installer and on the napari hub | Not yet available |
| QuPath extension | The jar from the GitHub release, installed by hand ([QuPath guide](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/qupath/)) | A catalog for QuPath's extension manager | Not yet available |
| Apps | Download the installer from the app's GitHub release | A page in the LabConstrictor App Centre | Available |

Every release is a GitHub release made by a maintainer. Nothing below has been registered anywhere yet, except the apps listed in the App Centre.

## Fiji

### Today

Each release of [LabConstrictor-Fiji](https://github.com/CellMigrationLab/LabConstrictor-Fiji/releases) carries `labconstrictor-fiji-<tag>.jar`, a script zip and `SHA256SUMS`. People install the jar by hand, as the [Fiji guide](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/fiji/) says, and replace it by hand to update.

### Next step: an update site

With an update site, people tick one box in Fiji and get updates automatically. The steps below follow the ImageJ documentation.

**Create the site** ([imagej.net/update-sites/setup](https://imagej.net/update-sites/setup)):

1. Ask for an update site and an upload account in the [request thread on the Image.sc forum](https://forum.image.sc/t/requests-for-creating-imagej-update-sites/40051/). A group can ask for a shared site and name the people who may upload.
2. In a clean Fiji, put the release jar into `plugins/`.
3. Open *Help > Update...*, click *Manage Update Sites*, then *Add Unlisted Site*. Enter the address of the new site in the URL column and `webdav:<your upload name>` in the Host column.
4. Back in the Updater, click *Advanced Mode* and choose *View local-only files*.
5. Select the jar, choose *Upload to <site name>*, then click *Apply Changes (upload)*.

For each later release, replace the jar in that Fiji, choose *View locally modified files only*, and upload again.

**Get it listed** ([imagej.net/list-of-update-sites](https://imagej.net/list-of-update-sites/)): open a pull request on [imagej/list-of-update-sites](https://github.com/imagej/list-of-update-sites) that adds the site to `sites.yml`, in alphabetical order. Until then, people can still add the site by its address.

**What users do then** ([imagej.net/update-sites/following](https://imagej.net/update-sites/following)): open *Help > Update...*, click *Manage Update Sites*, tick the LabConstrictor site (or *Add Unlisted Site* with its address), close the dialog, click *Apply Changes* and restart Fiji.

**To decide or check first:**

- The jar is the only file to upload. It needs nothing beyond what Fiji already ships.
- The release jar has the tag in its name. Check with one test upload that the Updater treats a new jar as an update of the old one, and not as a second plugin. We have not tested this.
- Upload the jar or the script, never both: with both, the menu shows the tool twice.
- An update site has no "alpha" channel. Everyone who ticks the box gets every upload.

## napari

### Today

The plugin is a Python package, `napari-labconstrictor`, in the repository [LabConstrictor-napari](https://github.com/CellMigrationLab/LabConstrictor-napari). It is installed with `pip` from the source archive of a GitHub tag, together with Tools; the command is in the [napari guide](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/napari/).

Neither `napari-labconstrictor` nor `labconstrictor-tools` is on PyPI.

### Next step: PyPI and the napari hub

napari finds plugins on PyPI. A package on PyPI that carries the classifier `Framework :: napari` can be installed from napari's own plugin installer and is shown on the napari hub ([napari.org: deploy your plugin](https://napari.org/stable/plugins/testing_and_publishing/deploy.html)).

What the plugin has already:

- A plugin manifest (`napari_labconstrictor/napari.yaml`) with one widget, *LabConstrictor tools*.
- The entry point that tells napari where the manifest is (`[project.entry-points."napari.manifest"]` in `pyproject.toml`).
- A version in `pyproject.toml` that a workflow compares with every pushed tag.

What is missing:

1. **`labconstrictor-tools` on PyPI.** The plugin depends on `labconstrictor-tools>=0.3.0a1`. `pip` cannot resolve that from PyPI today, so Tools has to be published first.
2. **The classifier.** Add `classifiers = ["Framework :: napari", ...]` to the plugin's `pyproject.toml`. Without it the plugin is not shown in napari's installer or on the hub.
3. **A publish step.** Build the sdist and wheel and upload them when a release is published. PyPI's trusted publishing lets a GitHub Actions workflow upload without a stored token ([docs.pypi.org/trusted-publishers](https://docs.pypi.org/trusted-publishers/)).
4. **More project links.** `pyproject.toml` has only the repository link. Add the issue tracker and the user guide, so the PyPI page and the hub can show them.

**To decide or check first:**

- Both names were free on PyPI when this page was written. Register them before announcing.
- Releases are alphas. `pip install napari-labconstrictor` skips pre-releases unless people add `--pre` or name the exact version.
- App installers install Tools from a pinned GitHub tag ([Operations](https://cellmigrationlab.github.io/LabConstrictor-Tools/OPERATIONS/#pinning-tools-in-app-installers)). Publishing on PyPI does not change that by itself; moving the installers to PyPI would be a separate change in the template.

## QuPath

### Today

Each release of [LabConstrictor-QuPath](https://github.com/CellMigrationLab/LabConstrictor-QuPath/releases) carries `labconstrictor-qupath-<tag>.jar`, a single-file script and `SHA256SUMS`. People install the jar by hand, as the [QuPath guide](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/qupath/) says.

### Next step: a catalog for the extension manager

QuPath 0.6 and 0.7 have an extension manager, *Extensions > Manage extensions*. It lists extensions by **catalog**. Only the QuPath team's own catalog is there by default; people add another one by its address under *Manage extension catalogs*. The address is usually a GitHub repository that holds a `catalog.json` file ([QuPath documentation: extensions](https://qupath.readthedocs.io/en/0.7/docs/intro/extensions.html)).

**Create the catalog** ([QuPath extension catalog model](https://qupath.github.io/extension-catalog-model/)):

1. Write a `catalog.json` that names the extension and its releases. The QuPath team provides a Python package and a QuPath script that write and check the file. A release entry looks like this:

    ```json
    {
      "name": "v0.1.0-alpha.7",
      "main_url": "https://github.com/CellMigrationLab/LabConstrictor-QuPath/releases/download/v0.1.0-alpha.7/labconstrictor-qupath-v0.1.0-alpha.7.jar",
      "version_range": {"min": "v0.7.0"}
    }
    ```

2. Put `catalog.json` in a public GitHub repository.
3. Add one release entry for each new release of the extension.

**What users do then:** open *Extensions > Manage extensions*, click *Manage extension catalogs*, paste the address of the catalog repository and click *Add*. LabConstrictor then appears in the list: the **+** button installs it and the cog button updates it. QuPath recommends a restart after each change.

**To decide or check first:**

- Which repository holds `catalog.json`: the extension's own repository or a small separate one.
- People who installed the jar by hand should remove it before installing from the catalog. The QuPath documentation advises against having both.
- We have not tested the extension through the extension manager.

## Apps

App authors do not publish to any store. This part is in place:

1. **Release.** A GitHub release of the app's repository builds the installers and attaches them ([Create executable installers](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/executable-creation/)).
2. **Describe.** The repository holds a small file, `labconstrictor-app.yaml`, that says what the app is ([Describe your app](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/app-manifest/)).
3. **List.** The author sends the repository address through the [submission form](https://cellmigrationlab.github.io/LabConstrictor-Site/submit/). A check runs on the file and the release; a maintainer then adds the app to the App Centre.

After that, the app's page always shows the latest release. The installers stay on the app's own GitHub release; the App Centre hosts no files.

The apps' tools need no publishing of their own. The installer registers them on the user's computer, and the plugins find them there.

## Recommended order

1. Publish `labconstrictor-tools` on PyPI, then `napari-labconstrictor` with the classifier.
2. Request the Fiji update site, upload the jar, and ask for it to be listed.
3. Add a `catalog.json` for QuPath and document its address in the QuPath guide.
4. Update the install steps in the three plugin guides, each kept in the plugin's own `docs/user-guide.md`.
