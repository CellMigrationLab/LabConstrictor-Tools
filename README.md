# LabConstrictor Tools

**Write an analysis in Python. Use it in Napari, Fiji, QuPath or from the command line.**

LabConstrictor Tools exposes Python analysis functions to Fiji, Napari, QuPath and the command line. The application runs in its own Python environment; each host handles the inputs and results.

An application exposes ordinary Python functions with declared inputs and outputs. The host builds a form, passes the data to the application, and shows what comes back. **The scientific code runs in the application's own Python environment**, not inside Fiji, QuPath or Napari.

This repository provides the Python declaration API, schema, application registry, worker, command-line tools and tests. The graphical interfaces live in separate repositories.

## See it working

To try the bridge, install [LabConstrictor Playground](https://github.com/CellMigrationLab/LabConstrictor-Playground). Its **Feature tour** can generate its own small image, find objects, and return a label image, outlines, points, a measurements table and a short report. You can use it to check how your chosen host handles each result without needing microscopy data of your own.

With an installed and registered LabConstrictor application, you can also:

- **Fiji:** run analysis on an open image, choose a channel, use a selection as a region, and receive images, ROIs or tables. [Fiji bridge](https://github.com/CellMigrationLab/LabConstrictor-Fiji)
- **Napari:** run tools from a dock widget using image layers or files, and receive new layers and measurements. [Napari plugin](https://github.com/CellMigrationLab/napari-labconstrictor)
- **QuPath:** run analysis on a selected annotation or viewport, then place returned points and outlines at their original slide coordinates. [QuPath extension](https://github.com/CellMigrationLab/LabConstrictor-QuPath)
- **Command line:** run the same registered tools in a script or batch workflow.

The hosts do not yet support every input, output and interaction hint in exactly the same way. Check their READMEs before relying on a particular workflow.

## How it works

1. **Declare a tool.** A Python function specifies its inputs and outputs using types and optional annotations.
2. **Register the application.** The installer records its Python interpreter, tool module and a cached description of the available tools. Hosts can list them without importing the application's scientific packages.
3. **Run from a host.** Napari, Fiji, QuPath or the CLI passes inputs to a worker running in the application's own environment.
4. **Use the results.** Images, labels, tables, points, outlines, transforms, files and messages are returned in formats the host can handle.

The worker uses a restricted, Appose-compatible protocol: it runs **declared tool IDs**, not arbitrary Python supplied by a host. It supports progress reporting and cancellation. The separate process helps keep incompatible scientific dependencies apart; **it is not a security sandbox**. Install and run applications you trust.

## Write a tool

A simple image-processing tool:

```python
from typing import Annotated
from labconstrictor_tools import Image, ImageOut, Min, tool

@tool("Gaussian blur")
def blur(image: Image, sigma: Annotated[float, Min(0)] = 2.0) -> ImageOut:
    from skimage.filters import gaussian
    return gaussian(image, sigma, preserve_range=True)
```

The declaration describes a required image and a non-negative blur radius. The host can build its controls from that information. The import of `skimage` stays inside the function so that listing available tools does not have to load the scientific stack.

The application still needs to install its dependencies, package the declaration module and register itself. The [authoring guide](docs/AUTHORING.md) covers those steps, including the expected `<package>_lc_tools` module layout, richer types, selections, outputs and tests.

## Install and inspect

The toolkit is currently installed from GitHub:

```bash
python -m pip install https://github.com/CellMigrationLab/LabConstrictor-Tools/archive/refs/heads/main.zip
```

The applications you want to use must be installed and registered separately. Their installers normally handle registration.

```bash
labconstrictor-tools list
labconstrictor-tools doctor
```

`list` shows registered applications and tools; `doctor` reports installation problems. To run a registered tool without a GUI:

```bash
labconstrictor-tools run myapp blur image=cells.tif sigma=3 --out results/
```

Here `myapp` is an example application name, not an application installed by this repository.

## For application authors

```bash
labconstrictor-tools init myapp_lc_tools.py
labconstrictor-tools check --module myapp_lc_tools --pythonpath .
labconstrictor-tools test --module myapp_lc_tools --pythonpath .
```

The `check` command validates declarations; `test` runs declared tools with samples and reports problems. For custom fixtures and expected results, use `--cases lc_tests/cases.json`. The toolkit also supports `%%lc_tool` notebook cells and `export-notebook`; see the [authoring guide](docs/AUTHORING.md).

## Applications

The bridge lists tools registered by installed applications. The following repositories provide applications or test tools; they are not bundled with this toolkit.

- [Playground](https://github.com/CellMigrationLab/LabConstrictor-Playground) ([releases](https://github.com/CellMigrationLab/LabConstrictor-Playground/releases)): synthetic images, example outputs and installation diagnostics.
- [Guess the Condition](https://github.com/CellMigrationLab/GuessTheCondition) ([releases](https://github.com/CellMigrationLab/GuessTheCondition/releases), [Colab](https://colab.research.google.com/github/CellMigrationLab/GuessTheCondition/blob/main/notebooks/GuessTheCondition/GuessTheCondition.ipynb)): blinded classification of microscopy images across biological repeats. Its code declares six tools: five game actions and a helper that supplies condition choices. The application documents Napari, Fiji and CLI use.
- [VLab4Mic desktop](https://github.com/CellMigrationLab/LabConstrictor-VLab4Mic) ([releases](https://github.com/CellMigrationLab/LabConstrictor-VLab4Mic/releases)): fluorescence image simulation; the application documents Napari and Fiji use.
- [NucleiSky](https://github.com/CellMigrationLab/NucleiSky) ([releases](https://github.com/CellMigrationLab/NucleiSky/releases)): image registration from nuclei landmarks. The Fiji bridge includes NucleiSky integration tests.
- [CellTracksColab desktop](https://github.com/CellMigrationLab/CellTracksColab_LabConstrictor) ([releases](https://github.com/CellMigrationLab/CellTracksColab_LabConstrictor/releases)): tracking-data analysis. Check which tools are available in the installed version.

A desktop installer does not guarantee that a particular tool works in every host. Run `labconstrictor-tools list` to see what your installation registers. QuPath compatibility should be checked independently.

## Documentation

- [Authoring tools](docs/AUTHORING.md) — declarations, input and output types, notebook integration, tests
- [Operations](docs/OPERATIONS.md) — registration, shared installs, diagnostics, logs and security boundaries
- [Protocol](docs/PROTOCOL.md) — schema, data formats and worker messages
- [Repository map](docs/REPOSITORIES.md) — where the toolkit, hosts and example application fit
- [Human testing](docs/HUMAN_TEST_PROTOCOL.md) — help test host integrations on real machines
- [Python tests](tests/README.md) — test suites and development checks

All front-ends write to the shared LabConstrictor log under `~/.labconstrictor/logs/` by default. `labconstrictor-tools logs` and `labconstrictor-tools support-bundle` help collect details when something fails.

## Development

```bash
python -m pip install -e ".[test]" black ruff mypy
black --check .
ruff check .
mypy labconstrictor_tools
cd tests && python -m unittest discover -p "test_*.py"
```

## Status

**Testing phase.** The toolkit and the Napari/Fiji integrations have been exercised on Linux with real LabConstrictor applications. The existing test record does not establish native Windows or macOS compatibility across the hosts. QuPath is also a prototype. Please report the host, operating system, application and steps needed to reproduce a problem.

License: MIT.
