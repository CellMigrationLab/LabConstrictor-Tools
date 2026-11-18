# Tool markers

Every type and marker a tool can use to declare its inputs and outputs. Hosts (napari, Fiji, QuPath) build the form and show the results from what you declare. This page is about markers on tools; the app's own description file, `labconstrictor-app.yaml`, has its guide in [Describe your app](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/app-manifest/), and the last two sections below give the technical rules for the two keys of that file that the plugins read.

`labconstrictor-tools check --module <your module>` prints what each parameter and output will do. `labconstrictor_tools/examples/interactions.py` is a copy-and-adapt example that uses every marker. What each host does with each marker is in [HOST_FEATURES.md](HOST_FEATURES.md), and a step-by-step introduction is [AUTHORING.md](AUTHORING.md).

**Everything beyond the types is optional.** A host that does not know a marker shows a plain, working form, so a tool must never depend on a marker to be correct.

## Types: what goes in and out

| Name | Use | Your function or the host gets |
|---|---|---|
| `str`, `int`, `float`, `bool`, `Literal[...]`, `Enum` | plain parameters | text, numbers, a checkbox, a dropdown |
| `Image`, `Labels` | an image or label image | a NumPy array |
| `Table`, `File`, `Folder` | a CSV file, a file, a folder | a DataFrame, a `Path`, a `Path` |
| `Optional[T]` or default `None` | optional and unset by default | a "set" box; your function gets `None` |
| `ImageOut`, `LabelsOut` | return an array | a layer or window |
| `TableOut` | return a DataFrame, list of dicts or dict of lists | a table |
| `Scalars` | return a dict of numbers or text | the values shown to the person |
| `MessageOut` | return a short text | a message |
| `PointsOut` | return a table with columns `y`, `x` (and properties) | points on the image |
| `ShapesOut` | return `labels_to_shapes(labels)`, a GeoJSON FeatureCollection or a list of polygons | outlines on the image |
| `FileOut` | return a path | a file the host lists |
| `Affine` (with `ApplyTo`) | return a 3x3 matrix | the moved image as an overlay |

`labels_to_shapes(labels, simplify=..., min_area=1)` gives one feature per label with at least `min_area` pixels, holes kept. An outline that simplification would collapse keeps its unsimplified shape, so a single pixel becomes a 4-vertex diamond.

## Links: how a parameter relates to another or to an image

| Marker | Meaning |
|---|---|
| `PixelSizeOf("image")` | this number is the pixel size of that image; hosts prefill it |
| `ApplyTo("image", "reference")` | an output (matrix, points, outlines) belongs to that image |
| `EnabledWhen("other", ...)` | the parameter only applies when another parameter is set or has one of the values |
| `ChoicesFrom("tool", depends=[...])` | a text parameter whose options another tool provides, as a dropdown |
| `PickChannel()` | the person chooses one channel of a multi-channel image; the tool gets only that channel |
| `RegionOf("image")` | on an optional `Labels` input: the host fills it from the current selection (labels 1..N, 0 outside), behind a "use the selection" box. The tool treats `None` as the whole image and can crop with `region.bbox(mask, image)` |

## Look: how it is shown

| Marker | Meaning |
|---|---|
| `Label`, `Description`, `Unit` | the name, help text and unit of the parameter |
| `Min`, `Max` | bounds, enforced everywhere |
| `Axes("YX")`, `Name("...")` | what the dimensions are; what the output is called |
| `Group("...")` | the parameters of a group are shown together under a heading |
| `Collapsed()` | the group starts folded |
| `Widget("slider")`, `Widget("radio")` | a bounded number as a slider (needs `Min` and `Max`); 2 to 5 choices as radio buttons |
| `Advanced()` | listed last, under "Advanced settings" |

## Behaviour: what the host does around a run

| Marker | Meaning |
|---|---|
| `ClearAfterRun()` | after a successful run the parameter goes back to its default (or unset) |
| `Replace()` | a new run replaces the previous result of this output instead of adding another |

## Errors and progress

These are function calls, not markers. `ToolError("code", "message")` gives the person a readable message; the codes `no_result` and `no_match` are shown as notices, not failures. `progress(fraction, "text")` updates the progress bar. `check_cancel()` lets Cancel stop the tool between steps.

## Mistakes refused at registration

Misused markers are refused when the app is registered, with a `DeclarationError` that names the parameter and the fix:

- `Min` or `Max` on anything but an `int` or `float`, a bound that is not a finite number, or `Min` above `Max`;
- `PixelSizeOf` on anything but a `float`;
- `Axes` on anything but an image or labels input or output;
- the output markers `Name`, `Replace` and `ApplyTo` on an input;
- two outputs with the same `Name`.

## `hosts`: which hosts list the app

Not a tool marker: a line of the app's `labconstrictor-app.yaml`, for example `hosts: [notebook, napari, fiji]`. It is binding: a host never lists an app that does not name it ([PROTOCOL.md](PROTOCOL.md#app-hosts-which-host-lists-an-app)).

- Write the hosts you have tested the app in. `[notebook]` alone means no host lists the app; its tools still work from the notebook and the command line.
- An empty list, a misspelt or capitalised name and a repeated name are refused at registration. A form the reader does not understand is refused, never read as "no hosts". The key may be quoted, and a UTF-8 byte order mark is accepted.
- Without a `hosts:` line the app is accepted and listed in every host, with a warning in the log and in `check --app-manifest`. Say what you mean instead.
- The installer passes the file to `register --app-manifest`, so the file must be one of the installer's bundled files (`extra_files` in `construct.yaml`).

`labconstrictor-tools check --module M --app-manifest labconstrictor-app.yaml` prints what will be registered.

## `host_requirements`: which plugin version the app needs

Also optional, also in `labconstrictor-app.yaml`. It is a request, not a filter: write it when the app relies on a fix or a feature that older plugins lack.

```yaml
host_requirements:
  qupath:
    min_version: 0.1.0-alpha.6
    features: [shapes_owner_v1]
    why: Replace keeps your own annotations
  fiji:
    min_version: 0.1.0-alpha.6
```

Each of `napari`, `fiji` and `qupath` takes:

- `min_version`: a plugin release tag, `v` optional; and/or
- `features`: host feature ids ([HOST_FEATURES.md](HOST_FEATURES.md#host-feature-ids-for-host_requirements));
- `why` (optional): one line shown to the person;
- `required: true` (optional): refuse instead of warn. Use it only when the tools really fail on older plugins.

A host with an older plugin keeps listing the app and says once which plugin to update and where ([PROTOCOL.md](PROTOCOL.md#host-requirements-which-plugin-an-app-needs)). Write it as a block, as above: the inline form `{fiji: {...}}` is refused, and so are an unknown host, the notebook, an unknown key and a version such as `latest`. `check --app-manifest` prints what was read.

## Adding a marker

A new marker joins one of the four families and follows the naming pattern (`XxxOf("param")` for links, `XxxOut` for outputs). It is merged only with: a row on this page, a recipe in [AUTHORING.md](AUTHORING.md), a line in `check`, a use in the example app, a clear declaration error for misuse, and a test in every host (or a documented fallback in [HOST_FEATURES.md](HOST_FEATURES.md)).
