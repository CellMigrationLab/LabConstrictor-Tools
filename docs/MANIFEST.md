# The manifest in one page

A tool declares itself with Python types and a few markers; hosts (Napari, Fiji, QuPath) build the form and show the results from the schema that comes out (`docs/PROTOCOL.md`). Everything is in four families. If you are looking for a feature, find the question it answers.

`labconstrictor-tools check --module <your module>` prints what each parameter and output will do. A copy-and-adapt example that uses every feature is `labconstrictor_tools/examples/interactions.py`. What each host does with each feature is in [HOST_FEATURES.md](HOST_FEATURES.md).

**Rule of thumb: everything beyond the types is optional.** A host that does not know a marker shows a plain, working form, so a tool must never depend on a marker to be correct.

## 1. Types: what goes in and out

| Name | Use | Gives your function / host |
|---|---|---|
| `str`, `int`, `float`, `bool`, `Literal[...]`, `Enum` | plain parameters | text, numbers, checkbox, dropdown |
| `Image`, `Labels` | an image or label layer | a NumPy array |
| `Table`, `File`, `Folder` | a CSV, a file, a folder | a DataFrame, a `Path`, a `Path` |
| `Optional[T]` or default `None` | optional and unset by default | a "set" box; your function gets `None` |
| `ImageOut`, `LabelsOut` | return an array | a layer or window |
| `TableOut` | return a DataFrame, list of dicts or dict of lists | a table |
| `Scalars` | return a dict of numbers or text | the values shown to the person |
| `MessageOut` | return a short text | a message block, dialog or label |
| `PointsOut` | return a table with columns `y`, `x` (+ properties) | a points layer, point ROIs, point annotations |
| `ShapesOut` | return `labels_to_shapes(labels)`, a GeoJSON FeatureCollection or a list of polygons | a shapes layer, polygon ROIs, annotations (planned in the hosts; until then it is listed as a file) |
| `FileOut` | return a path | a file the host lists |
| `Affine` (+ `ApplyTo`) | return a 3x3 matrix | an overlay of the moved image |

## 2. Links: how a parameter relates to another or to an image

| Marker | Meaning |
|---|---|
| `PixelSizeOf("image")` | this number is the pixel size of that image; hosts prefill it |
| `ApplyTo("image", "reference")` | an output (matrix, points) belongs to that image |
| `EnabledWhen("other", ...)` | only meaningful when another parameter is set or has a value |
| `ChoicesFrom("tool", depends=[...])` | a text parameter whose options another tool provides (dropdown) |
| `PickChannel()` | the person chooses a channel of a multi-channel image; the tool gets only that channel |
| `RegionOf("image")` | on an optional `Labels` input: the host fills it from the current selection (labels 1..N, 0 outside), behind a "use the selection" box; the tool treats `None` as the whole image and can use `region.bbox(mask, image)` to crop |

## 3. Look: how it is shown

| Marker | Meaning |
|---|---|
| `Label`, `Description`, `Unit` | name, tooltip, unit of the parameter |
| `Min`, `Max` | bounds, enforced everywhere |
| `Axes("YX")`, `Name("...")` | what the dimensions are, what the output is called |
| `Group("...")` | parameters of a group are shown together under a heading |
| `Collapsed()` | the group starts folded (an accordion section) |
| `Widget("slider")`, `Widget("radio")` | a bounded number as a slider (needs `Min` and `Max`), 2 to 5 choices as radio buttons; other hosts show the plain field |
| `Advanced()` | listed last, behind "Show advanced settings" |

## 4. Behaviour: what the host does around a run

| Marker | Meaning |
|---|---|
| `ClearAfterRun()` | after a successful run the parameter goes back to its default (or unset) |
| `Replace()` | a new run replaces the previous result of this output (one layer, window or table) instead of adding another |

## Errors and progress (not markers)
`ToolError("code", "message")` gives the person a readable message (`no_result` and `no_match` are shown as notices, not failures); `progress(fraction, "text")` updates the progress bar; `check_cancel()` lets Cancel stop the tool between steps.

## Adding something to the manifest
A feature joins one family, follows the naming pattern (`XxxOf("param")` for links, `XxxOut` for outputs), and is not merged until it has: a row here, a recipe row in `AUTHORING.md`, a line in `check`, a use in the example app, a clear declaration error for misuse, and a test in every host (or a documented fallback in `HOST_FEATURES.md`).
