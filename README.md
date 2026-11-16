# LabConstrictor Tools

**Write a Python analysis once. Use it in napari, Fiji, QuPath, a notebook or the command line.**

A [LabConstrictor](https://github.com/CellMigrationLab/LabConstrictor) app can offer **tools**: Python functions with typed inputs and outputs. LabConstrictor Tools is the small Python package every app carries. It describes each tool so that a plugin can build a form for it, run it in the app's own Python environment, and put the results back into your image software.

![napari with the LabConstrictor tools panel: a form for the NucleiSky tool "Relocalize 2D", built from the tool's declaration](https://raw.githubusercontent.com/CellMigrationLab/LabConstrictor-Tools/main/docs/img/N2_napari_form.png)

**Guides for people who use apps: <https://cellmigrationlab.github.io/LabConstrictor-Site/>** · Developer reference: <https://cellmigrationlab.github.io/LabConstrictor-Tools/>

## Who is it for?

- **You use an app** and want its tools inside napari, Fiji or QuPath. Start with [Use apps in napari, Fiji and QuPath](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/image-software/) and [What works where](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/capabilities/).
- **You make an app** and want its functions to appear in every host without writing interface code. Start with [Writing tools](https://github.com/CellMigrationLab/LabConstrictor-Tools/blob/main/docs/AUTHORING.md).

You do not install this package yourself to use an app: the app's installer brings it.

## Try it

1. Install the [LabConstrictor Playground](https://github.com/CellMigrationLab/LabConstrictor-Playground/releases) app, as [Install an app](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/install/) says. It makes its own test image, so you need no data.
2. Install the plugin for your software. Each guide has the steps: [napari](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/napari/), [Fiji](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/fiji/) or [QuPath](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/qupath/).
3. Open the plugin, pick **Playground** and run **Feature tour**. It returns a label image, outlines, points, a table and a message.

## Write a tool

```python
from typing import Annotated
from labconstrictor_tools import Image, ImageOut, Min, tool

@tool("Gaussian blur")
def blur(image: Image, sigma: Annotated[float, Min(0)] = 2.0) -> ImageOut:
    from skimage.filters import gaussian
    return gaussian(image, sigma, preserve_range=True)
```

That is the whole declaration: an image input, a number that cannot be negative, and an image result. Every host builds its form from it. Check and test your tools with:

```bash
labconstrictor-tools check --module myapp_lc_tools --pythonpath .
labconstrictor-tools test  --module myapp_lc_tools --pythonpath .
```

Tools run from the command line too:

```bash
labconstrictor-tools list
labconstrictor-tools run myapp blur image=cells.tif sigma=3 --out results/
```

## How it works

1. An app declares tools. Its installer registers them on your computer.
2. A plugin reads the registered descriptions and builds a form. It never imports the app's packages.
3. When you press Run, the tool runs in a separate process, in the app's own Python. Apps with conflicting packages can sit side by side.
4. Results come back as files (TIFF, CSV, GeoJSON) and the plugin shows them.

The separate process is **not a security sandbox**. Install and run only apps you trust.

## Status

Alpha. The newest release of Tools is on the [Releases page](https://github.com/CellMigrationLab/LabConstrictor-Tools/releases); each plugin has its own Releases page. Automated tests run on Linux, Windows and macOS; people have also tested it on Windows and macOS. The details are in [What works where](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/capabilities/).

Found a problem? [Open an issue](https://github.com/CellMigrationLab/LabConstrictor-Tools/issues) with the host, the operating system, the app and the steps.

## Install the package on its own

Only needed for development, or to add Tools to an environment by hand. Nothing is on PyPI yet: install the source archive of a release tag, as [Install LabConstrictor Tools](https://cellmigrationlab.github.io/LabConstrictor-Tools/INSTALL/#install-labconstrictor-tools-by-hand) says.

## Development

```bash
python -m pip install -e ".[test]" black ruff mypy
black --check .
ruff check .
python scripts/check_annotations.py
mypy
cd tests && python -m unittest discover -p "test_*.py"
```

The test suites are described in [tests/README.md](tests/README.md) and in [Automated testing](https://cellmigrationlab.github.io/LabConstrictor-Tools/TESTING/).

License: MIT.
