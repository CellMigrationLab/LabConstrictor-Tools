# Writing tools

A *tool* is a Python function with type hints. napari, Fiji, QuPath, notebooks and the command line all build their forms from its signature, so you write no interface code and no JSON.

Every marker is listed in [Tool markers](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/tool-markers/). What each host does with each one is in [What each host does with each feature](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/host-features/).

## A first tool

```python
# src/my_app_lc_tools/__init__.py  (next to your package `my_app`; the name must be <package>_lc_tools)
from typing import Annotated
from labconstrictor_tools import Image, ImageOut, Min, Name, progress, check_cancel, tool

@tool("Gaussian blur")
def blur(image: Image, sigma: Annotated[float, Min(0)] = 2.0) -> Annotated[ImageOut, Name("blurred")]:
    """Smooth an image.

    Args:
        image: The image to smooth.
        sigma: Width of the Gaussian in pixels.
    """
    from skimage.filters import gaussian        # heavy imports go inside the function
    progress(0.1, "smoothing")
    check_cancel()                              # lets the Cancel button stop long loops
    return gaussian(image, sigma, preserve_range=True)
```

To get a starter file, let `init` write it:

```bash
labconstrictor-tools init src/my_app_lc_tools/__init__.py
```

The starter is this example without `Name("blurred")`, so its output is named `image`, after its type. `init` creates the folder and prints the `check` and `register` commands for it.

**Name the module `<package>_lc_tools`.** The app's installer registers its tools only if the app's Python package `<package>` comes with a module named exactly `<package>_lc_tools`. For the package `nucleisky` that is `src/nucleisky_lc_tools/__init__.py`. Any other name works from the command line but is never registered by the installer. The app's release bundles everything under `src/` automatically, so you do not edit `construct.yaml` or `setup.py`.

## Inputs

| You write | The person sees, your function receives |
|---|---|
| `x: int`, `float`, `bool`, `str` | a number, a checkbox or a text field |
| `x: Literal["a", "b"]` or an `Enum` | a dropdown |
| `x: Image`, `x: Labels` | an open image or a file; you receive a NumPy array |
| `x: Table` | a CSV file; you receive a pandas DataFrame read exactly as written (the details are in the [protocol reference](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/protocol/)) |
| `x: Path`, `x: File` | a file; you receive a `Path` |
| `x: Folder` | a folder chooser; you receive a `Path` to a folder that exists |
| a default value | the form's default; no default means required |
| `Optional[T]`, `T \| None` or a default of `None` | optional and unset by default: a "set" box. If it stays unticked your function receives `None`, never 0 or an empty string |
| `Annotated[float, Min(0), Max(1), Unit("um/px"), Description("..."), Label("...")]` | bounds (enforced everywhere), a unit, the input's help, a label |
| `Annotated[Image, Axes("YX")]` | the tool takes exactly that many dimensions; anything else is refused with a clear error |
| `Annotated[float, PixelSizeOf("image")]` | prefilled from the image's calibration, converted to µm |
| `Annotated[..., Group("Segmentation")]` | the parameter is listed under that heading, with the rest of its group |
| `Annotated[..., Advanced()]` | listed last, under "Advanced settings" (in napari behind a "Show advanced settings" box) |
| `Annotated[..., Group("Advanced options"), Collapsed()]` | the group starts folded where the host can fold it |
| `Annotated[float, Min(0), Max(1), Widget("slider")]`, `Annotated[Literal[...], Widget("radio")]` | a slider (with a typed box) for a bounded number; radio buttons for 2 to 5 choices |
| `Annotated[Image, Axes("YX"), PickChannel()]` | the person chooses one channel of a multi-channel image; you receive that channel as a 2D array |
| `Annotated[Optional[Labels], RegionOf("image")] = None` | the person's selection (napari Shapes layer, Fiji ROI, QuPath annotations) as a label image; `from labconstrictor_tools.region import bbox` gives the box to crop to |
| `Annotated[str, ChoicesFrom("list_conditions", depends=["results_folder", "user_name"])]` | a dropdown filled by another tool, which returns `Scalars` with a `choices` list. It is a text field when that tool cannot answer, so accept any string |
| `Annotated[str, ClearAfterRun()]` | the field goes back to its default after a successful run, so a stale answer is not sent twice |
| `Annotated[..., EnabledWhen("other")]` or `EnabledWhen("other", "a", "b")` | greyed out unless `other` is set or true, or equals one of the values (Fiji ignores it) |
| a docstring `Args:` section | the inputs' help, as `Description` (`Description` wins when both are given) |

## Outputs

Return one value or a tuple, and annotate the return type:

| Return annotation | What you return, what the person gets |
|---|---|
| `ImageOut`, `LabelsOut` | a NumPy array, saved as TIFF (types ImageJ cannot open, such as float64, are converted) |
| `TableOut` | a DataFrame, a list of dicts or a dict of lists, shown as a table |
| `Scalars` | a dict of numbers or text, shown to the person |
| `MessageOut` | a short text (plain; `**bold**` is fine): instructions, a readout, a warning |
| `FileOut` | a file path |
| `Annotated[PointsOut, ApplyTo("image")]` | a DataFrame or list of dicts with columns `y` and `x` in pixels of that image (other columns become properties): points on the image |
| `Annotated[ShapesOut, ApplyTo("image")]` | `labels_to_shapes(labels)` from `labconstrictor_tools.shapes` (needs scikit-image), a GeoJSON FeatureCollection, or a list of polygons (arrays of `(y, x)` vertices, or dicts with `polygon` plus properties): outlines on the image |
| `Affine` with `ApplyTo("query", "reference")` | a 3x3 matrix mapping query pixels to reference pixels, in (y, x) order |
| `Annotated[ImageOut, Name("view"), Replace()]` | each run replaces the previous result named `view` instead of adding "view [1]" |
| `Annotated[ImageOut, Name("aligned"), Axes("YX")]` | names the output and states its axes |
| `return WithAxes(array, axes)` for an `ImageOut` or `LabelsOut` | the axes of this result, when they depend on the input. With axes in ImageJ order (`TYX`, `TZYX`, `ZCYX`, `TZCYX`, ...), from `Axes` or `WithAxes`, Fiji opens the result as a hyperstack; the array is never reordered |

How each host shows each output is in [What works where](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/capabilities/).

## Rules for fast, pleasant tools

1. **Keep module-level imports light.** Import only `labconstrictor_tools` and the standard library at the top of the file. Hosts load the declarations to show the tool list; `labconstrictor-tools check` warns about numpy, torch and other heavy imports at module level.
2. **Raise `ToolError(code, "what the person should do")`** for problems the person can fix. Any other exception is reported with its traceback.
3. **Call `check_cancel()` in long loops** and `progress(fraction, "message")` as work advances. The hosts stop a tool that does not react to Cancel after 3 seconds, which is wasteful for a long tool.
4. **Keep no state between runs in module globals.** Hosts may reuse the worker for faster repeat runs, so a stale global leaks into the next run. Caching a loaded model is fine if the cache is keyed by its settings.
5. **Write outputs through the return value**, not into the app folder, which may be read-only (for example on a network share).
6. **"Nothing found" is not an error.** When the honest answer is "no result", raise `ToolError("no_match", "No match found: ...say what to try...")` or use the code `no_result`. Hosts show it as a notice, not as an error.
7. **Treat presentation markers as hints.** A host may ignore `Group`, `Advanced` or `EnabledWhen`, so the function must accept every parameter whether or not it is "enabled".
8. **Describe every input.** The description is the input's help: hosts show it when the person points at the field, with an ⓘ after the label. Write one line that says what the value does and gives a typical value, for example `Description("Fraction of the intensity range that separates blobs from background; 0.3 suits most images")`, or put it in the docstring's `Args:` section. `labconstrictor-tools check` and `test` warn about inputs without one:
   `⚠ tool find_spots: 2 inputs have no description (threshold, min_size): add Description("...") or an Args: entry in the docstring`.

## Where images come from

You do not decide: every `Image` or `Labels` parameter offers an open image or a file in every host, and a path on the command line. Your function always receives a NumPy array. TIFF and OME-TIFF are read with `tifffile`. Other formats (PNG, JPEG, ...) are read only if the app's environment has `imageio`; otherwise the person sees `'<file>' is not a TIFF and this app has no imageio to read it; save it as TIFF`. The pixel size stored in a TIFF prefills a linked `PixelSizeOf` parameter, as for open images.

## Try it without a host

Run these from the repository root:

```bash
labconstrictor-tools check --module my_app_lc_tools --pythonpath src
labconstrictor-tools register --name myapp --prefix <app prefix> --module my_app_lc_tools --pythonpath src   # the installer does this for real apps
labconstrictor-tools run myapp blur image=cells.tif sigma=3 --out results/
labconstrictor-tools run myapp blur --usage
```

Without `--out`, `run` writes to a new folder under `<LC_HOME>/results/`; the newest 20 are kept. With `--pythonpath`, the folder you give is searched before anything installed in the same Python, so you test your working copy.

In a notebook: `from labconstrictor_tools.notebook import form; form(blur)`.

**Long texts on Windows.** A Windows command line cannot be longer than about 32,000 characters, so a terminal line, including one copied from a host, cannot carry a longer text parameter. The notebook form, the Python snippet (`client.run_once`) and the hosts' forms have no such limit. If your inputs can get that long, say so in the tool's description.

## Declare a tool in your notebook: `%%lc_tool`

LabConstrictor apps are notebooks, so you can declare a tool where you already write the code:

```python
%load_ext labconstrictor_tools.notebook_magic
```
```python
%%lc_tool "Gaussian blur" --export ../src/my_app_lc_tools/__init__.py
def blur(image: Image, sigma: Annotated[float, Min(0)] = 2.0) -> ImageOut:
    from skimage.filters import gaussian
    return gaussian(image, sigma)
```

`Image`, `Annotated`, `Min`, `tool` and the other markers are already available in the notebook. The magic adds `@tool`, checks the cell as a stand-alone module and shows the form the hosts will build (`--no-form` skips it). With `--export` it writes the function to the module as a managed block (`# >>> lc-tool: blur` ... `# <<< lc-tool: blur`); running the cell again replaces that block. Use `--function NAME` when the cell defines several functions. The path is relative to the notebook's folder (in an app repository, `notebooks/`, hence `../src/`), and the folder must exist. `--export` alone writes `lc_tools.py` next to the notebook, a name the installer does not pick up.

The check catches, before the tool ever runs in a worker: a function that uses a name defined in another cell (`uses 'helper', defined elsewhere in the notebook`), invalid declarations and heavy module-level imports. Only imports, function and class definitions and literal constants are exported; other top-level statements are listed as "not exported". A cell with problems is not run and nothing is written.

Without Jupyter (in CI, or for a notebook someone else wrote): `labconstrictor-tools export-notebook notebooks/analysis.ipynb --out src/my_app_lc_tools/__init__.py`.

## Test your tools: `labconstrictor-tools test`

`test` runs each tool through a real worker, as the hosts do, on small samples:

```bash
labconstrictor-tools test --module my_app_lc_tools --pythonpath src --cases tests.json
labconstrictor-tools test --module my_app_lc_tools --pythonpath src --sample image=small.tif   # a smoke test of every tool
```

For every run that completes, with no configuration, it checks that the results match the declared outputs, files exist, images use a type ImageJ can open, tables parse, affines are finite 3x3 matrices and values are plain JSON. `--check-cancel` also cancels each running tool and fails the case if the tool ignores the request for 10 seconds. The exit status is non-zero when anything fails, so `test` can run in CI. Tools without a case, and tools skipped because a required `--sample` is missing, are listed.

`tests.json` for the first tool (paths are relative to the file; `blurred` is the output's `Name`):

```json
[
  {"tool": "blur", "inputs": {"image": "small.tif", "sigma": 1.5},
   "expect": {"results": {"blurred": {"shape": [64, 64], "dtype": "float32"}}, "max_seconds": 30, "progress_events_min": 1}},
  {"tool": "blur", "inputs": {"image": "small.tif", "sigma": -1},
   "expect": {"status": "FAILED", "code": "invalid_parameter", "message_contains": "Sigma"}}
]
```

A case with `"cancel_after_s": 1.0` cancels the run after one second and expects the status `CANCELED`.

Expectations per output type: images `shape`, `dtype`, `mean`, `max`, `n_labels`; tables `columns`, `rows`, `cells` (`{"speed[0]": 1.5}`); values `{key: value}` or `{key: {"approx": 12.0, "tol": 0.5}}`; affines `matrix` (3x3). Floats compare with a relative tolerance of 1e-6.

The cases file is checked before anything runs: an unknown or misspelled key (`max_secods`, `row` instead of `rows`, an expectation that does not exist for that output type) is an error that names it. Relative file names are resolved only for image, labels, table, file and folder parameters; a text parameter is passed exactly as written.

## Recipes

`labconstrictor_tools/examples/interactions.py` uses every marker; `labconstrictor-tools check --module labconstrictor_tools.examples.interactions` shows what each parameter does in a host.

| I want to... | Declare |
|---|---|
| a dropdown whose options depend on earlier input | a `str` parameter with `ChoicesFrom("tool_that_lists_them", depends=[...])`; that tool returns `Scalars` with `{"choices": [...]}` |
| a field that must not keep its last value | `ClearAfterRun()` |
| each run to replace the last result instead of piling up layers or windows | `Replace()` on the output (people keep a result by renaming it) |
| to work on one channel of a multi-channel image | `Annotated[Image, Axes("YX"), PickChannel()]`; without it, a multi-channel image reaches a 2D tool as 3D and is refused |
| a long form with optional sections | `Group("...")` and `Collapsed()`, or `Advanced()` for rarely used settings |
| to mark objects found in an image | return `PointsOut` (columns `y`, `x`, then any properties) |
| to give the outlines of segmented objects | return `LabelsOut` and `ShapesOut` (`labels_to_shapes(labels)`) |
| to tell the person something | return `MessageOut` |

A host that does not know a marker shows a plain, working form, so a tool must never depend on a marker to be correct.

## A "Check this installation" tool

`labconstrictor_tools.diagnostics` tests the machine (memory, free disk, write access, paths), the worker, the GPU tools (`nvidia-smi`, Apple silicon) and PyTorch (CUDA, MPS, ROCm), optionally with a small CPU-versus-GPU benchmark. Each failure comes with its fix. An app offers it like this:

```python
@tool("Check this installation")
def check_installation() -> tuple[Annotated[MessageOut, Name("readout")], Annotated[TableOut, Name("details")]]:
    from labconstrictor_tools import diagnostics
    checks = diagnostics.run_checks(benchmark=False)       # benchmark=True adds a CPU-versus-device timing
    return diagnostics.summary(checks), diagnostics.rows(checks)
```

The probes look only at libraries already installed in the app; they never import something heavy just to find it missing, and never install anything. `diagnostics.torch_devices()` gives a list such as `["cpu", "cuda:0", "mps"]` for a device dropdown. To add a probe, write a function that returns a list of `diagnostics.Check` and pass it as `run_checks(extra=[...])`.
