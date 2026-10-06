# LabConstrictor-Tools

`labconstrictor-tools` lets a LabConstrictor app declare its scientific functions once, as typed Python, and get a graphical
interface in **Napari**, **Fiji**, **Jupyter notebooks** and the **command line** without writing any GUI code.

```python
# src/myapp_lc_tools/__init__.py in your app (the module must be called <package>_lc_tools, see docs/AUTHORING.md)
from typing import Annotated
from labconstrictor_tools import Image, ImageOut, Min, check_cancel, progress, tool

@tool("Gaussian blur")
def blur(image: Image, sigma: Annotated[float, Min(0)] = 2.0) -> ImageOut:
    from skimage.filters import gaussian      # heavy imports go inside the function
    return gaussian(image, sigma)
```

* The declaration is turned into a deterministic JSON schema (`protocol: 1`) **without running the tool**.
* Hosts read the schema and build forms (numbers with units and ranges, choices, optional images, file or open-image inputs).
* The tool runs in the app's **own Python** in a separate worker process (Appose-compatible JSON-lines protocol, cooperative
  cancel, progress, host-owned temp folders). Hosts never import the app's packages, so apps with conflicting dependencies coexist.
* The package has **no dependencies** (standard library only): it is installed into every app environment.

## The three repositories
| Repository | Role |
|---|---|
| **LabConstrictor-Tools** (this one) | declaration API, schema, worker, client, registry, logging, CLI, notebook helper, test command |
| [napari-labconstrictor](https://github.com/CellMigrationLab/napari-labconstrictor) | generic Napari dock widget |
| [LabConstrictor-Fiji](https://github.com/CellMigrationLab/LabConstrictor-Fiji) | generic Fiji command (jar) |

The contract between them is the schema and the worker protocol only ([docs/PROTOCOL.md](docs/PROTOCOL.md),
[docs/REPOSITORIES.md](docs/REPOSITORIES.md)).

## Install
    pip install labconstrictor-tools                 # (not on PyPI yet) pip install git+https://github.com/CellMigrationLab/LabConstrictor-Tools

## For app authors
    labconstrictor-tools init myapp_lc_tools.py      # starter declaration module
    labconstrictor-tools check --module myapp_lc_tools --pythonpath .     # validate declarations, warn about slow imports
    labconstrictor-tools test  --module myapp_lc_tools --pythonpath . --cases lc_tests/cases.json    # run tools on small samples, check results
    labconstrictor-tools register --name myapp --prefix <app prefix> --module myapp_lc_tools --pythonpath .   # by hand; the installer does it (without --pythonpath: the module is installed in the app)
    labconstrictor-tools run myapp blur image=cells.tif sigma=3 --out results/  # no GUI needed (without --out: ~/.labconstrictor/results/<time>_<app>_<tool>, newest 20 kept)

In a notebook: `%load_ext labconstrictor_tools.notebook_magic`, then `%%lc_tool "Label" --export myapp_lc_tools.py` on a cell with a function.
Full guide: [docs/AUTHORING.md](docs/AUTHORING.md).

## For users and administrators
    labconstrictor-tools list | doctor | logs | support-bundle

All front-ends write to one log, `~/.labconstrictor/logs/labconstrictor.log`. See [docs/OPERATIONS.md](docs/OPERATIONS.md)
(shared/network installs, security model, troubleshooting).

## Layout
    labconstrictor_tools/        the package (types, decorators, introspection = schema, convert, protocol, worker, client,
                                 registry, runs, log, cli, testing, exporter, notebook, notebook_magic)
    labconstrictor_tools/examples/synthetic.py    example app exercising every type; used by all host test suites
    docs/                        AUTHORING, PROTOCOL, OPERATIONS, LABCONSTRICTOR_INTEGRATION, REPOSITORIES,
                                 HUMAN_TEST_PROTOCOL (checklist for people), TESTING_PROMPT (prompt for an AI agent)
    tests/                       python test suites (see tests/README.md); tests/windows for a native Windows run
    fixtures/                    small test data (large images are generated on demand)

## Development
    pip install -e ".[test]" black ruff
    black --check . && ruff check . && mypy labconstrictor_tools      # pip install mypy
    cd tests && python -m unittest discover -p "test_*.py"      # about 80 s; no real apps needed (78 tests, 2 skipped)

Status: **testing phase**. Demonstrated on Linux with real NucleiSky and CellTracksColab installers (Napari and Fiji); Windows only under Wine
(the `.bat` install hooks have never run on real Windows); macOS untested. To help test on Windows or macOS follow
[docs/HUMAN_TEST_PROTOCOL.md](docs/HUMAN_TEST_PROTOCOL.md). See also the "Known limits" section of docs/OPERATIONS.md.

License: MIT.
