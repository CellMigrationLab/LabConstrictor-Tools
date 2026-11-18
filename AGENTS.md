# AGENTS.md

Notes for people and coding agents who change this repository.

## Documentation

Each topic of the LabConstrictor documentation has one owner page; every other page links to it instead of copying it. The table of owners is in LabConstrictor-Site's `AGENTS.md`, section "Sources of truth" (<https://github.com/CellMigrationLab/LabConstrictor-Site/blob/main/AGENTS.md#sources-of-truth>).

This repository owns these pages. LabConstrictor-Site fetches them and publishes them. Their first heading is the menu title on the site. Relative links are fine: the site resolves them (a link to another published page becomes that page, a link to any other file becomes the file on GitHub).

| Page | Track | On the LabConstrictor website |
|---|---|---|
| `docs/user-guide.md`, "Use apps inside napari, Fiji and QuPath" | Use an app | <https://cellmigrationlab.github.io/LabConstrictor-Site/guides/image-software/> |
| `docs/CAPABILITIES.md`, "What works where" | Use an app | <https://cellmigrationlab.github.io/LabConstrictor-Site/guides/capabilities/> |
| `docs/AUTHORING.md`, "Writing tools" | Connect an app | <https://cellmigrationlab.github.io/LabConstrictor-Site/guides/writing-tools/> |
| `docs/MANIFEST.md`, "Tool markers" | Connect an app | <https://cellmigrationlab.github.io/LabConstrictor-Site/guides/tool-markers/> |
| `docs/HOST_FEATURES.md`, "What each host does with each feature" | Connect an app | <https://cellmigrationlab.github.io/LabConstrictor-Site/guides/host-features/> |
| `docs/INSTALL.md`, "Install LabConstrictor Tools" | Connect an app | <https://cellmigrationlab.github.io/LabConstrictor-Site/guides/tools-install/> |
| `docs/OPERATIONS.md`, "Operations: shared installs, security, troubleshooting" | Connect an app | <https://cellmigrationlab.github.io/LabConstrictor-Site/guides/tools-operations/> |
| `docs/PUBLISHING.md`, "Publish the plugins and apps" | Connect an app | <https://cellmigrationlab.github.io/LabConstrictor-Site/guides/publishing/> |
| `docs/REPOSITORIES.md`, "Where the LabConstrictor tools live" | Connect an app | <https://cellmigrationlab.github.io/LabConstrictor-Site/guides/repositories/> |
| `docs/LABCONSTRICTOR_INTEGRATION.md`, "How the template registers an app's tools" | Connect an app | <https://cellmigrationlab.github.io/LabConstrictor-Site/guides/template-registration/> |
| `docs/PROTOCOL.md`, "Protocol reference" | Connect an app | <https://cellmigrationlab.github.io/LabConstrictor-Site/guides/protocol/> |

It also owns the developer topics: the protocol, the manifest, what each host does with each feature, testing, releases and tags, shared and network installs, security, and the install of `labconstrictor-tools` itself.

Pages owned elsewhere, which pages here link to and never copy:

- Install an app (installer steps, the Windows and macOS warnings, updating): the template, <https://cellmigrationlab.github.io/LabConstrictor-Site/guides/install/>.
- Install and open each plugin (commands, menu paths, current release): `docs/user-guide.md` of LabConstrictor-napari, LabConstrictor-Fiji and LabConstrictor-QuPath, at <https://cellmigrationlab.github.io/LabConstrictor-Site/guides/napari/>, `/guides/fiji/` and `/guides/qupath/`.
- The Tools tag that app installers pin: `LC_TOOLS_PIN` in the template's `app/bash_bat_scripts/post_install.sh` and `post_install.bat`.

Every page a user or a tool author needs is on LabConstrictor-Site; maintainers' material (TESTING.md, REGRESSION_LEDGER.md, SPEC_WRONG_SCIENCE.md, CONFORMANCE.md) stays on GitHub. This repository's GitHub Pages site (<https://cellmigrationlab.github.io/LabConstrictor-Tools/>) is only redirects: `scripts/build_redirect_site.py` sends each address of the old docs site to the page's new home (keeping a `#section`). A new page in docs/ needs a line there (its website address, or `NOT_PUBLISHED` for a maintainers' page), or that build fails.
