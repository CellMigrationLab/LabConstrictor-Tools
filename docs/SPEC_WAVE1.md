# Spec (proposal): Wave 1 of the manifest roadmap

Status: **for review, nothing is implemented.** Decisions already taken: outlines are GeoJSON, QuPath makes annotations from shapes, segmentation comes first. The manifest stays organised in four families ([MANIFEST.md](MANIFEST.md)); every item below says which family it joins.

| # | Item | Family | New name | Hosts |
|---|---|---|---|---|
| 1 | Slider and radio styles | Look | `Widget("slider")`, `Widget("radio")` | all three |
| 2 | Copy as command | none (host feature) | none | all three |
| 3 | Shape outlines | Types | `ShapesOut` | all three |
| 4 | Run on the selected region | Links | `RegionOf("image")` | all three |

Order of work: 1 and 2 (small, visible at once), then 3, then 4. Each item ships as a Tools PR (spec made real: schema, validation, docs, example, `check` line, tests), then one PR per host, then the apps that use it.

## 1. `Widget("slider")` and `Widget("radio")` (Look)
```python
labelling_efficiency: Annotated[float, Min(0), Max(1), Widget("slider")] = 1.0
modality: Annotated[Literal["STED", "Widefield", "Confocal"], Widget("radio")] = "STED"
```
- Schema: `widget: "slider"` or `"radio"` on the parameter.
- Declaration rules (clear errors): a slider needs `Min` and `Max` and a numeric type; radio applies to a `Literal` or `Enum` with 2 to 5 options; any other `Widget` name is refused and the error lists the valid ones.
- Hosts: Napari `FloatSlider` / `IntSlider` / `RadioButtons`; Fiji SciJava widget styles (`slider`, `radioButtonHorizontal`); QuPath `Slider` with a value label / `ToggleGroup`. A host that does not know the hint shows the number field or the dropdown.
- Fallback: always the plain widget. The slider keeps a typed value box beside it so a precise value can be entered.

## 2. Copy as command (host feature)
A button in each host copies what is needed to repeat the current form:
- **all hosts:** a terminal line `<python> -m labconstrictor_tools run <App> <tool> name=value ...` (strings quoted for the person's shell; image inputs cannot be named by a layer, so the line has `image=<a TIFF file>` with a note), and a Python snippet using `labconstrictor_tools.client`;
- **Fiji:** also the macro line (the recorder already produces it);
- **QuPath:** a Groovy line is not offered (the bridge is not scriptable from Groovy yet).
Nothing in the manifest changes. Test: the copied line, run in a terminal, gives the same values as the form.

## 3. `ShapesOut`: outlines (Types)
```python
@tool("Segment")
def segment(image: Annotated[Image, Axes("YX")]) -> tuple[
    Annotated[LabelsOut, Name("labels")],
    Annotated[ShapesOut, Name("outlines"), ApplyTo("image"), Replace()],
]:
    labels = ...
    return labels, shapes.labels_to_shapes(labels)       # helper in labconstrictor_tools.shapes
```
- **Wire format:** a GeoJSON `FeatureCollection` file. Result `{type: "shapes", name, path, n, apply_to?}`.
- **Coordinates:** pixel units of the image named by `ApplyTo`, `[x, y]` order (GeoJSON), with pixel centres at integers, the same convention as `PointsOut` (hosts add the half pixel their own tools need). Polygons and multipolygons, holes allowed, other geometry types refused with a clear message.
- **Properties** (label, area, score, ...) are kept; a `label` property links an outline to its label.
- **What a tool may return:** a GeoJSON dict, a list of polygons (each an array of (y, x) vertices) with optional properties, or the helper's output. `labels_to_shapes(labels, simplify=0.5)` traces each label (uses scikit-image when the app has it; otherwise it says what to install; not a Tools dependency).
- **Limits:** the helper simplifies to keep files small; hosts show up to 50 000 outlines and say how many were left out.
- **Hosts:** Napari: a shapes layer with the properties (holes are drawn as the outer boundary, with a note); Fiji: polygon ROIs in the ROI Manager (holes kept as composite ROIs) and an overlay; QuPath: annotations named `<app>:<output>`, replaced by the next run when the output declares `Replace()` (QuPath reads GeoJSON natively).
- **Fallback:** a host that does not know `shapes` lists the file as a file result.

## 4. `RegionOf("image")`: run on the selected region (Links)
```python
region: Annotated[Optional[Labels], Axes("YX"), RegionOf("image")] = None
```
- The host fills this optional mask input from the **current selection**: Napari the shapes of the selected Shapes layer, Fiji the current ROI, QuPath the selected annotation(s). A "use the selection" box next to it (off by default) decides whether it is sent. Several selected objects become labels 1..N.
- The tool receives a `Labels` array the size of the image (0 outside); a helper `labconstrictor_tools.region.bbox(mask)` gives the box to crop to. A tool must treat `None` as "the whole image".
- Declaration rules: `RegionOf` applies to an optional `Labels` input and names an image parameter of the same tool.
- Fallback: the plain optional Labels chooser, which still lets a person pick a mask layer or file.

## Tests (every item)
The example app (`labconstrictor_tools.examples.interactions`) gets one tool per item; each host's own suite drives it with a normal case, an adversarial case (no selection, an empty result, 50 000 outlines, holes, a slider at its limits, a value typed outside the bounds, unicode names) and a screenshot, and the whole existing suites are re-run. `HOST_FEATURES.md` gets the new rows.

## Order of PRs
Tools (slider and radio, then shapes, then region) → Napari, Fiji, QuPath for each → apps: NucleiSky (outlines and a region to match inside), VLab4Mic (sliders and radio), the StarDist app when it exists (outlines).

## Decisions (answered by the maintainer)
1. Host limit: 50 000 outlines (hosts say how many were left out).
2. `labels_to_shapes` lives in Tools (`labconstrictor_tools.shapes`); scikit-image is needed only when it is called.
3. Several selected objects reach the tool as labels 1..N, not one merged region.
4. Build order: slider and radio plus Copy as command first, then `ShapesOut`, then `RegionOf`.
