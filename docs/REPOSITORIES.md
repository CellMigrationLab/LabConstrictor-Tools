# Where the LabConstrictor tools live

The project has a shared Python toolkit, host-specific interfaces and applications that expose scientific analyses. They are separate repositories because they solve different problems.

| Repository | What it contains |
|---|---|
| [LabConstrictor-Tools](https://github.com/CellMigrationLab/LabConstrictor-Tools) | Python declarations (`@tool`, types and annotations), schema generation, registry, worker, CLI, notebook helpers, diagnostics and tests |
| [LabConstrictor-napari](https://github.com/CellMigrationLab/LabConstrictor-napari) | Napari dock widget, layer conversion and presentation of results (pip package `napari-labconstrictor`; the link name `napari-labconstrictor` redirects to this repository; installed from the source archive of a release tag) |
| [LabConstrictor-Fiji](https://github.com/CellMigrationLab/LabConstrictor-Fiji) | Fiji menu command, SciJava forms, ImageJ ROI handling and the worker connection. Release files (made by its release workflow when the maintainer publishes a release): `labconstrictor-fiji-<tag>.jar`, `labconstrictor-fiji-script-<tag>.zip` (script and its `lib` folder) and `SHA256SUMS` |
| [LabConstrictor-QuPath](https://github.com/CellMigrationLab/LabConstrictor-QuPath) | QuPath extension (QuPath 0.7.0), image-area export, annotation coordinates and result presentation. Release files: `labconstrictor-qupath-<tag>.jar`, the single script `LabConstrictorTools-all.groovy` (the only form the Script Editor can run) and `SHA256SUMS` |
| [LabConstrictor-Playground](https://github.com/CellMigrationLab/LabConstrictor-Playground) | An installable test application (17 tools): diagnostics, synthetic image analysis and deliberately difficult cases for hosts (the repository's canonical name is lower case, `labconstrictor-playground`; the link works either way) |

Two other kinds of repository have different jobs:

- [LabConstrictor](https://github.com/CellMigrationLab/LabConstrictor) is the **notebook-to-desktop-application packaging template**, not another graphical host for the tools.
- Scientific applications own their analysis code and tool declarations. LabConstrictor installers register the applications' tool modules automatically when they are packaged; the toolkit also supports manual registration. The applications:

| Application | Repository | Tools registered for hosts | Latest release |
|---|---|---|---|
| NucleiSky | [NucleiSky](https://github.com/CellMigrationLab/NucleiSky) | 2 (List the devices, Relocalize 2D) | 0.1.6 |
| Guess the Condition | [GuessTheCondition](https://github.com/CellMigrationLab/GuessTheCondition) | 6 (five game actions and one helper) | 0.0.2 |
| Playground | the Playground row above | 17 | 0.0.7 |
| VLab4Mic | [LabConstrictor-VLab4Mic](https://github.com/CellMigrationLab/LabConstrictor-VLab4Mic) | 2 (Simulate imaging of a virtual sample, Compare an image with a reference) | 0.1.8 |
| StarDist2D | [Stardist2D](https://github.com/CellMigrationLab/Stardist2D) | yes | 1.2.1 |
| CellTracksColab | [CellTracksColab](https://github.com/CellMigrationLab/CellTracksColab) (its desktop app is released from this repository) | 1 (Calculate Track Metrics), registered but listed in no host (`hosts: [notebook]`) | 1.1.5 |
| LabConstrictor Demo | [LabConstrictor_Demo](https://github.com/CellMigrationLab/LabConstrictor_Demo) | none (notebook only) | 0.0.4 |

Each app's installer pins a Tools tag (`LC_TOOLS_PIN`); an app gets a new pin by the template sync and its next release ([OPERATIONS.md](OPERATIONS.md#pinning-tools-in-app-installers)). An app's latest release is on its page in the [App Centre](https://cellmigrationlab.github.io/LabConstrictor-Site/) and on its GitHub Releases page.

## What is shared

The toolkit defines the [schema and worker protocol](PROTOCOL.md). Hosts read cached schemas to build forms without importing scientific application packages. When a user runs a tool, the host starts or reuses a worker in that application's Python environment.

Hosts do **not** need to install the application's scientific dependencies. The application does **not** need to import Napari, Fiji or QuPath.

**Which host shows which app is a rule, not a side effect of registration.** An application with a valid registered manifest is discoverable by every host its `hosts:` line names; no other host lists it ([PROTOCOL.md](PROTOCOL.md#app-hosts-which-host-lists-an-app)). The rule is in Tools (feature `app_hosts_v1`) and the three hosts honour it; an app with no declaration (installed with an installer older than template 0.1.18) is listed in every host, with the 'declares no hosts' sentence in the Tools log. The practical value of a particular tool still depends on the host's workflow and on whether its inputs and outputs are relevant there.

| App | Napari | Fiji | QuPath | Notebook |
|---|---|---|---|---|
| NucleiSky, Guess the Condition, Playground, StarDist2D | listed | listed | listed | yes |
| VLab4Mic | listed | listed | **not listed** | yes |
| CellTracksColab | hidden | hidden | hidden | yes (notebook only: the release sandbox expects "not listed" in all three) |
| LabConstrictor Demo | (no tools) | (no tools) | (no tools) | yes |

The `hosts:` line of an app's `labconstrictor-app.yaml` (App-Centre metadata, schema `.tools/schema/labconstrictor-app.schema.json` of the template) is the binding rule; installers pass it to Tools (`--app-manifest` or `--hosts`) from template 0.1.18.

This is a shared contract, **not a promise that every host implements every presentation hint**. For example, an image selection, a dynamic dropdown or an output table may be handled differently by each host. Consult the relevant host README for current behavior and limits.

## Where to make changes

- New tool declaration, validation, serialization or protocol behavior: **Toolkit**.
- Napari layer selection, MagicGUI form or layer presentation: **Napari plugin**.
- Fiji image windows, SciJava fields, ROIs or macro replay: **Fiji bridge**.
- QuPath image regions, coordinate offsets, annotations or slide export: **QuPath extension**.
- Test fixtures, diagnostics or deliberate worker stress cases: **Playground**.
- Installer registration hooks: **LabConstrictor packaging template or the individual application**, depending on where the installer is defined.

The protocol is versioned. Hosts must reject and report incompatible schema versions rather than silently guessing how to interpret them. See [PROTOCOL.md](PROTOCOL.md) and [OPERATIONS.md](OPERATIONS.md).

## Distribution and testing

The repositories have different packaging requirements: a Python package for the toolkit and Napari plugin, a Fiji jar or script, a QuPath extension or script, and platform-specific Playground installers. Do not assume they share a release schedule.

The project remains in testing. How to install an app and each plugin is on the LabConstrictor website ([Install an app](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/install/), and the [napari](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/napari/), [Fiji](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/fiji/) and [QuPath](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/qupath/) guides); what Tools needs is in [INSTALL.md](INSTALL.md). The host READMEs record their tested platforms and current limitations. Released apps are checked on fresh runners by the release sandbox ([TESTING.md](TESTING.md#release-sandbox-a-released-app-on-fresh-runners)).
