# Where the LabConstrictor tools live

The project has a shared Python toolkit, host-specific interfaces and applications that expose scientific analyses. They are separate repositories because they solve different problems.

| Repository | What it contains |
|---|---|
| [LabConstrictor-Tools](https://github.com/CellMigrationLab/LabConstrictor-Tools) | Python declarations (`@tool`, types and annotations), schema generation, registry, worker, CLI, notebook helpers, diagnostics and tests |
| [napari-labconstrictor](https://github.com/CellMigrationLab/napari-labconstrictor) | Napari dock widget, layer conversion and presentation of results |
| [LabConstrictor-Fiji](https://github.com/CellMigrationLab/LabConstrictor-Fiji) | Fiji menu command, SciJava forms, ImageJ ROI handling and Appose-based worker connection |
| [LabConstrictor-QuPath](https://github.com/CellMigrationLab/LabConstrictor-QuPath) | QuPath extension, image-area export, annotation coordinates and result presentation |
| [LabConstrictor-Playground](https://github.com/CellMigrationLab/LabConstrictor-Playground) | An installable test application: diagnostics, synthetic image analysis and deliberately difficult cases for hosts |

Two other kinds of repository have different jobs:

- [LabConstrictor](https://github.com/CellMigrationLab/LabConstrictor) is the **notebook-to-desktop-application packaging template**, not another graphical host for the tools.
- Scientific applications such as NucleiSky, CellTracksColab and VLab4Mic own their analysis code and tool declarations. Their installers register the installed application's interpreter and tool module.

## What is shared

The toolkit defines the [schema and worker protocol](PROTOCOL.md). Hosts read cached schemas to build forms without importing scientific application packages. When a user runs a tool, the host starts or reuses a worker in that application's Python environment.

Hosts do **not** need to install the application's scientific dependencies. The application does **not** need to import Napari, Fiji or QuPath.

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

The project remains in testing. The host READMEs record their tested platforms, installation steps and current limitations. The [human testing protocol](HUMAN_TEST_PROTOCOL.md) explains how to help check the integrations on real machines.
