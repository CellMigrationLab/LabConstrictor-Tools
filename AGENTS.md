# AGENTS.md

Notes for people and coding agents who change this repository.

## Documentation

Each topic of the LabConstrictor documentation has one owner page; every other page links to it instead of copying it. The table of owners is in LabConstrictor-Site's `AGENTS.md`, section "Sources of truth" (<https://github.com/CellMigrationLab/LabConstrictor-Site/blob/main/AGENTS.md#sources-of-truth>).

This repository owns these pages. LabConstrictor-Site fetches them and publishes them, so links in them must be absolute:

| Page | On the LabConstrictor website |
|---|---|
| `docs/user-guide.md`, "Use apps inside napari, Fiji and QuPath" | <https://cellmigrationlab.github.io/LabConstrictor-Site/guides/image-software/> |
| `docs/CAPABILITIES.md`, "What works where" | <https://cellmigrationlab.github.io/LabConstrictor-Site/guides/capabilities/> |
| `docs/PUBLISHING.md`, "Publish the plugins and apps" | <https://cellmigrationlab.github.io/LabConstrictor-Site/guides/publishing/> |
| `docs/AUTHORING.md`, "Writing tools" | the "Build an app" track (being added) |

It also owns the developer topics: the protocol, the manifest, what each host does with each feature, testing, releases and tags, shared and network installs, security, and the install of `labconstrictor-tools` itself.

Pages owned elsewhere, which pages here link to and never copy:

- Install an app (installer steps, the Windows and macOS warnings, updating): the template, <https://cellmigrationlab.github.io/LabConstrictor-Site/guides/install/>.
- Install and open each plugin (commands, menu paths, current release): `docs/user-guide.md` of LabConstrictor-napari, LabConstrictor-Fiji and LabConstrictor-QuPath, at <https://cellmigrationlab.github.io/LabConstrictor-Site/guides/napari/>, `/guides/fiji/` and `/guides/qupath/`.
- The Tools tag that app installers pin: `LC_TOOLS_PIN` in the template's `app/bash_bat_scripts/post_install.sh` and `post_install.bat`.

This repository's own docs site (<https://cellmigrationlab.github.io/LabConstrictor-Tools/>, built from `mkdocs.yml`) is the developer reference only. Pages for people who use apps live on LabConstrictor-Site.
