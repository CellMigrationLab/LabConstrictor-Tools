# Writing tools for LabConstrictor apps (10 minutes)

> The whole manifest on one page: [MANIFEST.md](MANIFEST.md). What each host does with each feature: [HOST_FEATURES.md](HOST_FEATURES.md).

A *tool* is a normal Python function with type hints. Napari, Fiji, notebooks and the command line all build their
forms from the signature - you write no GUI code and no JSON.

```python
# src/my_app_lc_tools/__init__.py  (next to your package `my_app`; the name MUST be <package>_lc_tools, see below)
from typing import Annotated
from labconstrictor_tools import Image, ImageOut, Min, progress, check_cancel, tool

@tool("Gaussian blur")
def blur(image: Image, sigma: Annotated[float, Min(0)] = 2.0) -> ImageOut:
    """Smooth an image.

    Args:
        image: The image to smooth.
        sigma: Width of the Gaussian in pixels.
    """
    from skimage.filters import gaussian        # heavy imports go INSIDE the function
    progress(0.1, "smoothing")
    check_cancel()                              # lets the Cancel button stop long loops cleanly
    return gaussian(image, sigma, preserve_range=True)
```

`labconstrictor-tools init my_app_lc_tools.py` writes this starter for you.

**Naming rule.** The LabConstrictor installer registers an app's tools only if the app's Python package `<package>` is
accompanied by a module named exactly **`<package>_lc_tools`** (for the package `nucleisky`: `src/nucleisky_lc_tools/__init__.py`, which the
app lists in `construct.yaml` under `extra_files` like the rest of `src/`). Any other name works from the command line but is never registered by the installer.

## What you declare, what is inferred

| You write | Becomes |
|---|---|
| `x: int / float / bool / str` | number / checkbox / text field |
| `x: Literal["a", "b"]` or an `Enum` | dropdown |
| `x: Image` / `Labels` | an image chosen from the host (you receive a numpy array) |
| `x: Table` | a CSV file (you receive a pandas DataFrame; floats exact, column names as written even if duplicated or empty, empty cells NaN, texts such as `NA` or `None` stay text unless the column is numeric: see PROTOCOL.md) |
| `x: Path` / `File` | a file (you receive a `Path`) |
| `x: Folder` | a folder (you receive a `Path`; the worker checks that it exists; hosts show a folder chooser) |
| a default value | the form's default; no default = required |
| `Optional[T]`, `T \| None`, or a default of `None` | optional **and unset by default**: Napari shows a "set" checkbox, Fiji "Set <name>"; if it stays unticked your function receives `None` (never 0 or an empty string) |
| `Annotated[float, Min(0), Max(1), Unit("um/px"), Description("..."), Label("...")]` | bounds (enforced everywhere), unit, tooltip, label |
| `Annotated[Image, Axes("YX")]` | the tool wants exactly that many dimensions; a clear error otherwise |
| `Annotated[float, PixelSizeOf("image")]` | hosts prefill this from the image's calibration (converted to um) |
| `Annotated[..., Group("Segmentation")]` | the parameter is listed under that heading; the parameters of a group are shown together |
| `Annotated[..., Advanced()]` | listed last, behind "Show advanced settings" (Napari) / under "Advanced settings" (Fiji) |
| `Annotated[Image, Axes("YX"), PickChannel()]` | the person chooses a channel of a multi-channel image in the host (QuPath: the channel names; Fiji: the channel number) and your function receives only that channel as a 2D array. Napari layers are one channel each, so it only offers R/G/B for an RGB layer or the channels of a TIFF file given as "or file"; the command line and notebooks pass the image as it is |
| `Annotated[Optional[Labels], RegionOf("image")] = None` | run on the selection: Napari the selected Shapes layer, Fiji the ROI, QuPath the selected annotations arrive as a label image; `from labconstrictor_tools.region import bbox` gives the box to crop to (an empty selection raises a readable error) |
| `Annotated[float, Min(0), Max(1), Widget("slider")]` / `Annotated[Literal[...], Widget("radio")]` | a slider (with a typed box) for a bounded number; radio buttons for 2 to 5 choices |
| `Annotated[..., Group("Advanced options"), Collapsed()]` | the group is an accordion section that starts folded (Napari); Fiji shows the heading and the fields |
| `Annotated[str, ChoicesFrom("list_conditions", depends=["results_folder", "user_name"])]` | a dropdown filled by another tool (which returns `Scalars` with a `choices` list); a text field when it cannot be answered, so the tool accepts any string |
| `Annotated[str, ClearAfterRun()]` | Napari empties/resets the field after a successful run (a stale answer cannot be sent twice) |
| `Annotated[..., EnabledWhen("other")]` or `EnabledWhen("other", "a", "b")` | greyed out in Napari unless `other` is set/true or equals one of the values; **Fiji ignores it** (all fields stay editable) |
| docstring `Args:` section | tooltips |

Return one value or a tuple. Annotate the return type with what it is:

| Return annotation | Meaning |
|---|---|
| `ImageOut`, `LabelsOut` | numpy array -> TIFF (Fiji-unsafe dtypes such as float64 are converted) |
| `TableOut` | DataFrame / list of dicts / dict of lists -> table |
| `Scalars` | dict of numbers/strings shown to the user |
| `Affine` + `ApplyTo("query", "reference")` | 3x3 matrix mapping *query pixels -> reference pixels* (y, x order); hosts apply it for you |
| `FileOut` | a file path |
| `MessageOut` | a short text for the user (plain; `**bold**` is fine): instructions, a readout, a warning. Shown in a dialog / the status line, never in the log |
| `Annotated[PointsOut, ApplyTo("image")]` | a DataFrame / list of dicts with columns `y` and `x` (pixels of that image; other columns become properties) -> Napari points layer, Fiji point ROIs, QuPath point annotations |
| `Annotated[ShapesOut, ApplyTo("image")]` | `labels_to_shapes(labels)` from `labconstrictor_tools.shapes` (needs scikit-image), a GeoJSON FeatureCollection, or a list of polygons (arrays of `(y, x)` vertices, or dicts with `polygon` plus properties) -> Napari shapes layer, Fiji polygon ROIs, QuPath annotations |
| `Annotated[ImageOut, Name("view"), Replace()]` | each run replaces the previous result named `view` (Napari layer / Fiji window) instead of adding "view [1]" |
| `Annotated[ImageOut, Name("aligned"), Axes("YX")]` | name the output / say what its axes are |

## Rules that keep it fast and pleasant

1. **Light module-level imports.** Only `labconstrictor_tools` and the standard library at the top of the file. Hosts load the
   declarations to show the tool list; `labconstrictor-tools check` warns if you import numpy/torch/... at module level.
2. **Raise `ToolError(code, "what the user should do")`** for problems the user can fix. Any other exception is reported with its traceback.
3. **Call `check_cancel()` in long loops** and `progress(fraction, "message")` as work advances. A tool that never checks is
   killed after 3 s when the user cancels - fine for short tools, wasteful for long ones.
4. **Do not keep state between runs in module globals** - hosts may reuse the worker (faster repeat runs), so a stale global will
   leak into the next run. (Caching a loaded model is fine if it is keyed by its settings.)
5. **Write outputs through the return value**, not into the app folder (it may be read-only, e.g. on a network share).
6. **"Nothing found" is not an error.** When the honest answer is "no result" (no match, no nuclei), raise `ToolError("no_match", "No match found: ...say what to try...")` (or code `no_result`). Napari shows it as a notice (a warning sign, not a red cross) and Fiji as a plain message window instead of an error dialog.
7. **Presentation hints are only hints.** `Group`, `Advanced` and `EnabledWhen` may be ignored by a host (Fiji ignores `EnabledWhen`; older hosts ignore all three), so the function must accept every parameter whether or not it is "enabled".

## Where do images come from?

You do not decide: every `Image`/`Labels` parameter offers **an open image or a file** in every front-end (command line: a path).
Napari shows the layer chooser plus an "or file" row (a chosen file wins and greys the layer out); Fiji shows the open-image
chooser plus "(or file)", and with no image open only the file field. Your function always receives a NumPy array. TIFF/OME-TIFF are
read with `tifffile`; other formats (PNG, JPEG, ...) are read if the app environment has `imageio`, otherwise the user gets
"not a TIFF ... save it as TIFF". Pixel size stored in a TIFF is used to pre-fill a linked `PixelSizeOf` parameter, as for open images.

## Try it without any GUI

```
labconstrictor-tools check --module my_app_lc_tools --pythonpath .
labconstrictor-tools register --name myapp --prefix <app prefix> --module my_app_lc_tools --pythonpath .   # by hand; the installer does it
labconstrictor-tools run myapp blur image=cells.tif sigma=3 --out results/      # without --out: <LC_HOME>/results/<time>_<app>_<tool> (newest 20 kept)
labconstrictor-tools run myapp blur --usage
```

In a notebook: `from labconstrictor_tools.notebook import form; form(blur)`.

Note: with `--pythonpath`, the folder you give is searched **before** anything installed in the same Python, so you test your working copy, not an older installed copy of the same module.

## Keep the logic in your notebook: `%%lc_tool`

LabConstrictor apps are notebooks, so you can declare a tool where you already write the code:

```python
%load_ext labconstrictor_tools.notebook_magic
```
```python
%%lc_tool "Gaussian blur" --export my_app_lc_tools.py
def blur(image: Image, sigma: Annotated[float, Min(0)] = 2.0) -> ImageOut:
    from skimage.filters import gaussian
    return gaussian(image, sigma)
```

`Image`, `Annotated`, `Min`, `tool`, ... are already available in the notebook. The magic adds `@tool`, checks the cell
as a stand-alone module, shows the same form Napari/Fiji will generate (`--no-form` to skip), and with `--export` writes the
function to a module as a managed block (`# >>> lc-tool: blur` ... `# <<< lc-tool: blur`); running the cell again
replaces that block. Options: `--function NAME` when the cell defines several functions, `--export` alone means `lc_tools.py` (a name the installer does not pick up: use `<package>_lc_tools.py`).

What the check catches, **before** the tool ever runs in a worker: a function that uses a name defined in another notebook cell
(`uses 'helper', defined elsewhere in the notebook`), invalid declarations, module-level numpy/torch imports. Only imports,
function/class definitions and literal constants are exported; other top-level statements are listed as "not exported".
A cell with problems is not run and nothing is written.

Without Jupyter (CI, a notebook someone else wrote): `labconstrictor-tools export-notebook analysis.ipynb --out my_app_lc_tools.py`.

## Test the tool: `labconstrictor-tools test`

Runs each tool through the real worker (the same process model as Napari/Fiji), on small samples:

```
labconstrictor-tools test --module my_app_lc_tools --pythonpath . --cases tests.json
labconstrictor-tools test --module my_app_lc_tools --pythonpath . --sample image=small.tif   # smoke test of every tool
```

Checked for every run that completes, with no configuration: results match the declared outputs, files exist, images use
a dtype ImageJ can open, tables parse, affines are finite 3x3, values are plain JSON. `--check-cancel` additionally cancels a
running tool and FAILS the case if the tool ignores the request for 10 s (`check_cancel()` missing). Exit status is non-zero when anything fails, so it
can run in CI. Tools without a case, and tools skipped because a required `--sample` is missing, are listed.

`tests.json` (paths are relative to the file):

```json
[
  {"tool": "blur", "inputs": {"image": "small.tif", "sigma": 1.5},
   "expect": {"results": {"blurred": {"shape": [64, 64], "dtype": "float32"}}, "max_seconds": 30, "progress_events_min": 1}},
  {"tool": "blur", "inputs": {"image": "small.tif", "sigma": -1},
   "expect": {"status": "FAILED", "code": "invalid_parameter", "message_contains": "Sigma"}},
  {"tool": "slow_tool", "inputs": {}, "cancel_after_s": 1.0}
]
```

Expectations per output type: images `shape`, `dtype`, `mean`, `max`, `n_labels`; tables `columns`, `rows`, `cells`
(`{"speed[0]": 1.5}`); values `{key: value}` (or `{key: {"approx": 12.0, "tol": 0.5}}`); affine `matrix`. Floats compare with a relative tolerance of 1e-6.

The cases file is validated before anything runs: an unknown or misspelled key (`max_secods`, `row` instead of `rows`, a result
expectation that does not exist for that output type) is an error that names it, never an assertion that is quietly skipped. An
affine `matrix` must be 3x3. Relative file names are resolved only for parameters declared as image, labels, table, file or
folder: a text parameter is passed exactly as written.


## Recipes: interaction hints at a glance

A copy-and-adapt example that uses every hint lives in `labconstrictor_tools/examples/interactions.py`
(`labconstrictor-tools check --module labconstrictor_tools.examples.interactions` lists what each parameter will do in a host).

| I want to... | Declare |
|---|---|
| a dropdown whose options depend on earlier input | a `str` parameter with `ChoicesFrom("tool_that_lists_them", depends=[...])`; that tool returns `Scalars` with `{"choices": [...]}`. Accept any string: hosts without the hint show a text field |
| a field that must not keep its last value | `ClearAfterRun()` |
| each run to replace the last result instead of piling up layers / windows | `Replace()` on the output (users keep one by renaming it) |
| to work on one channel of a multi-channel image | `Annotated[Image, Axes("YX"), PickChannel()]` (without it a multi-channel image reaches a 2D tool as 3D and is refused) |
| a long form with optional sections | `Group("...")` and `Collapsed()` (or `Advanced()` for the rarely used) |
| to mark objects found in an image | return `PointsOut` (columns `y`, `x`, then any properties) |
| to give the outlines of segmented objects | return `LabelsOut` and `ShapesOut` (`labels_to_shapes(labels)`) |
| to tell the user something | return `MessageOut` |

Every hint is optional and additive: a host that does not know it shows a plain, still working form, so the tool never depends on a hint to be correct.

## A "Check this installation" tool in three lines
`labconstrictor_tools.diagnostics` tests the machine (memory, free disk, write access, paths), the worker, the GPU tools (`nvidia-smi`, Apple chip) and PyTorch (CUDA, MPS, ROCm), optionally with a small CPU-versus-GPU benchmark. Each failure comes with the fix beside it. An app offers it to its users like this:

```python
@tool("Check this installation")
def check_installation() -> tuple[Annotated[MessageOut, Name("readout")], Annotated[TableOut, Name("details")]]:
    from labconstrictor_tools import diagnostics
    checks = diagnostics.run_checks(benchmark=False)       # benchmark=True adds a CPU-versus-device timing
    return diagnostics.summary(checks), diagnostics.rows(checks)
```
Probes only look at libraries that are already installed in the app; they never import something heavy to find it missing and never install anything. `diagnostics.torch_devices()` gives `["cpu", "cuda:0", "mps"]` for a device dropdown (`ChoicesFrom`). To add a probe, write a function returning a list of `diagnostics.Check` and pass it as `run_checks(extra=[...])`.
