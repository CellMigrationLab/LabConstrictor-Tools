# Where the LabConstrictor tools live

The project has a shared Python toolkit, host-specific interfaces and applications that expose scientific analyses. They are separate repositories because they solve different problems.

| Repository | What it contains |
|---|---|
| [LabConstrictor-Tools](https://github.com/CellMigrationLab/LabConstrictor-Tools) | Python declarations (`@tool`, types and annotations), schema generation, registry, worker, CLI, notebook helpers, diagnostics and tests |
| [LabConstrictor-napari](https://github.com/CellMigrationLab/LabConstrictor-napari) | Napari dock widget, layer conversion and presentation of results (pip package `napari-labconstrictor`; the old link name `napari-labconstrictor` redirects to this repository, checked 14 Oct 2026; Qt6 backend, `napari[pyqt6]`; no tag or release when this was written) |
| [LabConstrictor-Fiji](https://github.com/CellMigrationLab/LabConstrictor-Fiji) | Fiji menu command, SciJava forms, ImageJ ROI handling and the worker connection. Release files (made by its release workflow when the maintainer publishes a release): `labconstrictor-fiji-<tag>.jar`, `labconstrictor-fiji-script-<tag>.zip` (script and its `lib` folder) and `SHA256SUMS` |
| [LabConstrictor-QuPath](https://github.com/CellMigrationLab/LabConstrictor-QuPath) | QuPath extension (QuPath 0.7.0), image-area export, annotation coordinates and result presentation. Release files: `labconstrictor-qupath-<tag>.jar`, the single script `LabConstrictorTools-all.groovy` (the only form the Script Editor can run) and `SHA256SUMS` |
| [LabConstrictor-Playground](https://github.com/CellMigrationLab/LabConstrictor-Playground) | An installable test application (17 tools): diagnostics, synthetic image analysis and deliberately difficult cases for hosts (the repository's canonical name is lower case, `labconstrictor-playground`; the link works either way) |

Two other kinds of repository have different jobs:

- [LabConstrictor](https://github.com/CellMigrationLab/LabConstrictor) is the **notebook-to-desktop-application packaging template**, not another graphical host for the tools.
- Scientific applications own their analysis code and tool declarations. LabConstrictor installers register the applications' tool modules automatically when they are packaged; the toolkit also supports manual registration. The applications of the first human-test round:

| Application | Repository | Tools registered for hosts | Tag of the next release (planned) |
|---|---|---|---|
| NucleiSky | [NucleiSky](https://github.com/CellMigrationLab/NucleiSky) | 2 (List the devices, Relocalize 2D) | 0.1.4 (latest 0.1.3) |
| Guess the Condition | [GuessTheCondition](https://github.com/CellMigrationLab/GuessTheCondition) | 6 (five game actions and one helper) | 0.0.1 (latest 0.0.0) |
| Playground | the Playground row above | 17 | 0.0.4 (latest 0.0.3) |
| VLab4Mic | [LabConstrictor-VLab4Mic](https://github.com/CellMigrationLab/LabConstrictor-VLab4Mic) | 2 (Simulate imaging of a virtual sample, Compare an image with a reference) | 0.1.6 (latest 0.1.5) |
| CellTracksColab | [CellTracksColab](https://github.com/CellMigrationLab/CellTracksColab) (its desktop app is released from this repository; the repository name `CellTracksColab_LabConstrictor` that this page and the README used to link was not reachable from here: not verified that it exists) | none on `main` (a bridge exists on the held branch `bridge-test`) | 1.1.2, held until the bridge decision (latest 1.1.1) |

Tool counts and latest releases are as of 14 Oct 2026 (the code of each repository's `main`, the GitHub release lists); "planned" numbers are the next free ones after the pin pull requests ([OPERATIONS.md](OPERATIONS.md#pinning-tools-in-app-installers)).

## What is shared

The toolkit defines the [schema and worker protocol](PROTOCOL.md). Hosts read cached schemas to build forms without importing scientific application packages. When a user runs a tool, the host starts or reuses a worker in that application's Python environment.

Hosts do **not** need to install the application's scientific dependencies. The application does **not** need to import Napari, Fiji or QuPath.

**Which host shows which app is a rule, not a side effect of registration.** An application with a valid registered manifest is discoverable by a host that supports the protocol, unless the discovery rule says that host must not offer it. Decided 14 Oct 2026 (the rule is added by Tools PR #133, feature `app_hosts_v1`; until it is merged and tagged every host lists every registered app that passes its compatibility check, which is the behaviour of `v0.3.0-alpha.1` as far as this repository's code shows at 535450d: not verified for the hosts):

| App | Napari | Fiji | QuPath | Notebook |
|---|---|---|---|---|
| NucleiSky, Guess the Condition, Playground | listed | listed | listed | yes |
| VLab4Mic | listed | listed | **not listed** | yes |
| CellTracksColab | hidden | hidden | hidden | yes (notebook only; tested in the release sandbox as "must be hidden") |

discovery rule: see PROTOCOL.md, section "App hosts (which host lists an app)"

The `hosts:` line of an app's `labconstrictor-app.yaml` (App-Centre metadata, schema `.tools/schema/labconstrictor-app.schema.json` of the template) is binding: the installer passes it to registration (`--app-manifest` or `--hosts`) and Napari, Fiji and QuPath list the app only if it names them (see PROTOCOL.md, section "App hosts (which host lists an app)"). The practical value of a particular tool still depends on the host's workflow and on whether its inputs and outputs are relevant there.

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

The project remains in testing. How to install an app and the three hosts is on one page, [INSTALL.md](INSTALL.md): tagged versions only, no space in the install path, Linux `-u` only after a finished install. The host READMEs record their tested platforms and current limitations. The [human testing protocol](HUMAN_TEST_PROTOCOL.md) explains how to help check the integrations on real machines, with a record sheet that ties every result to the versions tested; the automated counterpart is the release sandbox ([TESTING.md](TESTING.md#release-sandbox-a-released-app-on-fresh-runners)).
