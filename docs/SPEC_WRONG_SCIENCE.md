# Spec (proposal): the "wrong-science" fix wave

Status: **for review, nothing is implemented.** Maintainer decisions are recorded in section 8.

**v1: 2D. N-D (T/Z stacks) and the QuPath resolution (downsample) choice follow in Wave 2.** The frame (1.1.2) and the placement formula (1.1.3) already have their final shape, so Wave 2 adds fixtures, not rules. Wave 2 fixtures still needed: `TYX` and `ZYX` results with `t`/`z` columns, a 2D result on a `TYX` layer (Napari), a per-axis `_calibration` with z and t, and QuPath export at downsample 2 and 4 on a real pyramid (CF-14 is the data, the GUI harness is the missing part). Same conventions as [SPEC_WAVE2.md](SPEC_WAVE2.md) and [HOST_PARITY.md](HOST_PARITY.md): additive within `protocol: 1`, rules are host-neutral, a rule is "done" when its fixtures pass in every host that claims the feature. The fixtures below are data, meant to live in `labconstrictor_tools/conformance.json` under the key `wrong_science` and to be reused by the conformance suite (Tools #87).

These rules exist because a tool run can succeed and still be scientifically wrong: a mask on the wrong pixels, a result drawn away from its image, a pixel size from another image, a researcher's folder deleted. Each host fixes its own code, but all of them implement **the same rule**, so a fix in one host cannot leave another one behind.

| # | Theme | Rule set | Issues it settles |
|---|---|---|---|
| 1 | Coordinate frame | section 1 | Napari #31 #33 #34, Fiji #30, QuPath #21 (and the plane/offset half of QuPath #16) |
| 2 | Calibration | section 2 | Napari #35 #38, Fiji #26, QuPath #15 |
| 3 | Retention (hosts write markers, only Tools prunes) | section 3 | Tools #55, Napari #32, Fiji #28, QuPath #14 |
| 4 | Run identity | section 4 | QuPath #16 (and the same hazard in Napari and Fiji) |
| 5 | Async lookups | section 5 | Napari #36 #37, QuPath #19 |
| 6 | Number limits | section 6 | HOST_PARITY A06, A07, C01, D05 |

Out of scope here (tracked in their own issues): Fiji #29 (macro replay of required scalars), Fiji #31 (optional warp comparison blocking the overlay), Fiji #33 (Appose completion ordering). They are host bugs with no cross-host rule.

Words: **MUST** and **MUST NOT** are tested by a fixture; **SHOULD** is not. "Source" is the input named by `ApplyTo` (else the first `Image` or `Labels` input in manifest order, never "the first value of any type", never the active, last shown or topmost image). "Refuse" means: do not start the run (inputs) or do not draw the result (outputs), say why in one sentence, keep every output file, never fall back to another image.

---

## 1. Coordinate frame

### 1.1 The rule
1. **A result lives in the data space of its source, as it was exported.** `PointsOut`, `ShapesOut`, `ImageOut` and `LabelsOut` coordinates are pixel coordinates of the image file the host wrote for the source (after any crop or plane choice), pixel centres at integers, `(y, x)` for points and `[x, y]` for shapes, as in PROTOCOL.md and HOST_PARITY H06. The worker never sees a world, viewer, slide or calibrated coordinate.
2. **The host owns the mapping back.** It records, at run start (section 4), a *frame* for each exported image: `{source, shape, axes_offset, plane, downsample, transform}`. `axes_offset` is `(t, z, y, x)`: the origin of the exported area inside the source's full-resolution grid (all zero unless the host exports a crop; `t` and `z` are the exported plane's indices); `plane` is the exported `(t, z)`; `downsample` is the factor between exported and full-resolution pixels (1 unless the host exports a reduced copy); `transform` is the source's spatial transform (identity where the host has none). `shape` is the exported Y/X (and T/Z) shape.
3. **Placement formula (stated once).** A result coordinate `x` (likewise `y`) is in exported-pixel units with the centre of pixel `i` at integer `i`. Its **continuous full-resolution coordinate** is `c = x0 + (x + 0.5) * downsample`, where `x0` is `axes_offset` for that axis and full-resolution pixel `i` spans `[i, i+1)`. Hosts draw at `c` as follows: Fiji and QuPath use `c` as the ROI vertex; Napari uses the data coordinate `c - 0.5` and its layer transform does the rest (`result.data_to_world(p) == source.data_to_world(c - 0.5)`). At `downsample = 1` and `x0 = 0` this is today's `x + 0.5` (Fiji, QuPath) and `x` (Napari). Shapes `[x, y]` use the same formula per vertex.
4. **No lossy resampling.** The host never resamples a result to fit; it carries the source transform over. Conversion is exact, so "refuse" is reserved for cases where an exact mapping does not exist (1.4).
5. **No silent fallback.** A result whose source cannot be resolved, is gone, or has no display (a file) is never drawn on another image or layer. It is shown as a table (points), listed as a file (shapes, images), and the status says where the files are.
6. **Outputs without a source.** `ImageOut` / `LabelsOut` with no `ApplyTo` keep the documented default: pixel origin, identity transform, no units. `PointsOut` / `ShapesOut` with no `ApplyTo` use the first `Image` input (H05); with no image input they are a table or file.
7. **Size mismatch is stated, not hidden.** If an `ImageOut` / `LabelsOut` that declares `ApplyTo` has a Y/X shape different from the exported frame, the host shows it at the default pixel origin (rule 6) and says once: `'name' is W x H but 'source' was exported as W2 x H2; shown at the pixel origin, not aligned`.
8. **`Replace()` recomputes the frame.** Replacing a result layer or window sets the transform again from the new result; it never keeps the previous one.
9. **No `t` / `z` means the exported plane.** A point or shape with no `t` / `z` lands on `frame.plane` (the plane that was exported), **not on plane 0**. This amends SPEC_WAVE2 1.5.

### 1.2 Input selections (`RegionOf`, QuPath "Image area")
1. A selection is converted **into the exported image's pixel grid**, then rasterised there. The mask has exactly the exported image's Y/X shape.
2. Rasterisation: a mask pixel is set if its centre lies inside the polygon (boundary pixels are never used in fixtures, so hosts need not agree on them).
3. Napari: vertices go `shapes.data_to_world` then `image.world_to_data` (full transform: scale, translate, rotate, shear, affine), at level 0 of a multiscale image. The mask is in the image's data grid whatever the shapes layer's own transform.
4. A selection MUST NOT be rasterised in its own raw data coordinates.
5. All vertices of one selection must land on one plane of the image. Otherwise refuse with `selection_mixed_planes`.
6. QuPath: the crop is the integer bounding box of the selected annotations in full-resolution pixels (floor of the minimum, ceil of the maximum, clamped to the image); `axes_offset` is its top-left corner; with `downsample` d the exported shape is `ceil(size / d)` and a mask pixel centre `(i + 0.5) * d + offset` is tested against the annotation (1.1.3). v1 exports at `downsample = 1`.
7. **QuPath planes.** Every selected annotation MUST be on one `ImagePlane`, and that plane MUST be the one exported (the viewer's plane at run start). Different planes among the selection: refuse `selection_mixed_planes`. One plane that is not the exported one: refuse `selection_plane_mismatch` (the host does not switch planes behind the person's back). The exported TIFF, the mask and the restored annotations all carry that one plane. **Whole-image export uses the same plane as the viewport and selection export** (the viewer's plane at run start). Today whole-image export uses `z=0, t=0` while the viewport area uses the viewer plane; that is a defect (QuPath #16, #21) and fixture CF-10 covers it.

### 1.3 How each host maps
| | frame comes from | result drawn with | file input | transform that cannot be mapped |
|---|---|---|---|---|
| Napari | the Image layer (level 0 of a multiscale one) | new layer gets the source's `scale`, `translate`, `rotate`, `shear`, `affine` (and units); N-D: the transform acts on the trailing axes the result has, leading axes of the source must not move the plane (note below), else refuse | pixel frame of the file: identity, no units; the layer is named after the file; no layer is searched | refuse `frame_unsupported_transform` (non-invertible YX block, or a leading-axes coupling that cannot be expressed on a lower-dimensional result) |
| Fiji | the `ImagePlus` (by object, not by title) | ROI or overlay in the pixel space of that image at `c` (1.1.3), `setPosition(channel, z, t)` of the exported plane; calibration origin and scale are not applied (ROIs are pixel based) | the file is opened in its own window (titled with the file name) and the result goes there; if it cannot be opened: table and file | Fiji images have no transform: identity by construction |
| QuPath | the `ImageData` of the run (section 4), plane, `axes_offset` and `downsample` above | annotation on the exported plane, vertices at `c` (1.1.3) in full-resolution pixels | not displayable: table plus file, status `file input: results are in the file's pixel frame` | QuPath images have no transform: identity by construction |
| CLI, notebook | n/a | files; a table carries `frame` columns only if the tool wrote them | n/a | n/a |

Note on the Napari row: a lower-dimensional result on a higher-dimensional source is allowed only if the dropped leading axes of the source have identity scale/translate in the world (they do not move the plane); otherwise `frame_unsupported_transform`.

### 1.4 Refusal versus conversion, in one table
| situation | decision |
|---|---|
| any invertible affine on the source (translate, scale, rotate, shear) | convert (exact), never refuse |
| `RegionOf` shapes layer with a different transform than the image | convert through world (1.2.3) |
| multiscale image | level 0; transform is the layer's |
| non-invertible transform, or axes that cannot be expressed | refuse `frame_unsupported_transform` |
| selection on several planes, or on a plane other than the exported one | refuse (1.2.5, 1.2.7) |
| source layer removed, image closed or changed during the run | outputs kept, not drawn: `target_unavailable` (section 4) |
| source is a file | pixel frame of the file (1.3), never another image |

New host-side codes `frame_unsupported_transform`, `selection_mixed_planes`, `selection_plane_mismatch`, `target_unavailable` go into `host_internal_codes` of the conformance file; wording is one sentence naming the source and the reason, always followed by `(nothing was changed; files are in <path>)` when files exist.

### 1.5 Fixtures: coordinate frame
Base image `ASYM`: uint16, 8 rows by 12 columns, `value(y, x) = 100*y + x`. Rectangles have vertices on half pixels, so no pixel centre lies on an edge. `world` is Napari only; `target_px` is `c - 0.5` on the target image in its own full-resolution data pixels (so Fiji and QuPath draw at `target_px + 0.5`), the check in every host.

```json
{
  "wrong_science": {"coordinate": {
    "image": {"id": "ASYM", "shape": [8, 12], "dtype": "uint16", "value": "100*y + x"},
    "rect": [[1.5, 2.5], [1.5, 5.5], [3.5, 5.5], [3.5, 2.5]],
    "rect_mask_pixels": [[2,3],[2,4],[2,5],[3,3],[3,4],[3,5]],
    "rect_mask_values": [203, 204, 205, 303, 304, 305],
    "cases": [
      {"id": "CF-01", "name": "identity", "source": {},
       "point": [2, 3], "expect": {"world": [2, 3], "target_px": [2, 3], "mask": "rect_mask_pixels"}},
      {"id": "CF-02", "name": "translate only (scale equal, origin different)",
       "source": {"translate": [100, 0]}, "shapes_layer": {"translate": [0, 0], "vertices_world": "rect + [100, 0]"},
       "point": [2, 3], "expect": {"world": [102, 3], "target_px": [2, 3], "mask": "rect_mask_pixels"}},
      {"id": "CF-03", "name": "scale and translate",
       "source": {"scale": [0.5, 0.25], "translate": [10, 20]},
       "point": [2, 3], "expect": {"world": [11.0, 20.75], "target_px": [2, 3]}},
      {"id": "CF-04", "name": "rotation by 90 degrees",
       "source": {"affine": [[0,-1,0],[1,0,0],[0,0,1]]},
       "shapes_layer": {"vertices_world": [[-2.5,1.5],[-5.5,1.5],[-5.5,3.5],[-2.5,3.5]]},
       "point": [2, 3], "expect": {"world": [-3, 2], "target_px": [2, 3], "mask": "rect_mask_pixels"}},
      {"id": "CF-05", "name": "shear",
       "source": {"affine": [[1,0.5,0],[0,1,0],[0,0,1]]},
       "point": [2, 4], "expect": {"world": [4, 4], "target_px": [2, 4]}},
      {"id": "CF-06", "name": "multiscale, level 0 carries the transform",
       "source": {"levels": [[8,12],[4,6]], "translate": [100, 0]},
       "point": [2, 3], "expect": {"world": [102, 3], "export_shape": [8, 12]}},
      {"id": "CF-07", "name": "file input with a decoy open image",
       "inputs": {"image": {"file": "ASYM.tif"}}, "open_image": {"id": "DECOY", "translate": [100, 0]},
       "point": [2, 3], "expect": {"target": "file:ASYM.tif", "napari_world": [2, 3],
         "decoy_gets_nothing": true, "fiji_new_window_titled": "ASYM.tif", "qupath": "table_and_file"}},
      {"id": "CF-08", "name": "earlier output must not become the target",
       "sequence": ["run A -> ImageOut shown", "run B (file input) -> PointsOut ApplyTo"],
       "expect": {"target": "file:ASYM.tif", "last_shown_image_gets_nothing": true}},
      {"id": "CF-09", "name": "QuPath crop offset",
       "source": {"server_wh": [12, 8]}, "selection_annotation": {"x": [4, 10], "y": [2, 6], "plane": [0, 0]},
       "expect": {"export_offset_yx": [2, 4], "export_shape": [4, 6], "export_value_0_0": 204, "export_value_3_5": 509,
                  "regionof_mask": "all ones, shape [4, 6]"},
       "point": [1, 2], "result_expect": {"target_px": [3, 6]}},
      {"id": "CF-10", "name": "QuPath planes",
       "source": {"z": 2, "t": 1}, "viewer": {"z": 0, "t": 0},
       "variants": [
         {"selection": [{"z": 0, "t": 0}], "expect": "run, results on z=0 t=0"},
         {"selection": [{"z": 1, "t": 0}], "expect": "refuse selection_plane_mismatch"},
         {"selection": [{"z": 0, "t": 0}, {"z": 1, "t": 0}], "expect": "refuse selection_mixed_planes"},
         {"selection": [], "viewer": {"z": 1, "t": 0}, "export": "whole image", "expect": "exported plane z=1 t=0, results on z=1 t=0"},
         {"point_without_t_z": true, "viewer": {"z": 1, "t": 0}, "expect": "lands on z=1 t=0, not on plane 0"}]},
      {"id": "CF-11", "name": "size mismatch is stated",
       "result": {"type": "labels", "shape": [4, 6], "apply_to": "image"}, "source_export_shape": [8, 12],
       "expect": {"transform": "identity", "status_contains": "not aligned"}},
      {"id": "CF-12", "name": "Replace recomputes the transform",
       "sequence": ["labels result on source translate [100,0]", "Replace with result for source translate [0,0]"],
       "expect": {"world_of_0_0": [0, 0]}},
      {"id": "CF-13", "name": "non-invertible source transform",
       "source": {"affine": [[0,0,0],[0,0,0],[0,0,1]]}, "expect": "refuse frame_unsupported_transform"},
      {"id": "CF-14", "name": "QuPath downsample 2 and 4 (c = x0 + (x + 0.5) * d); needs a host that exports at d != 1",
       "variants": [
         {"server_wh": [24, 16], "downsample": 2, "offset_yx": [0, 0], "export_shape": [8, 12], "point": [2, 3], "expect": {"c_yx": [5.0, 7.0]}},
         {"server_wh": [48, 32], "downsample": 4, "offset_yx": [0, 0], "export_shape": [8, 12], "point": [2, 3], "expect": {"c_yx": [10.0, 14.0]}},
         {"server_wh": [48, 32], "downsample": 2, "offset_yx": [4, 8], "export_shape": [8, 12], "point": [2, 3], "expect": {"c_yx": [9.0, 15.0]}},
         {"downsample": 1, "offset_yx": [0, 0], "point": [2, 3], "expect": {"c_yx": [2.5, 3.5]}}],
       "unsupported_ok": "a host that only exports at downsample 1 reports the first three as unsupported, never as passed"}
    ]}}
}
```
Checks that every case also makes: the **worker's input file** (exported pixels equal `ASYM` or its crop, mask pixels equal `rect_mask_pixels`), the **actual drawn coordinates** (not only "no error"), and that nothing was drawn on any image other than `target`.

---

## 2. Calibration

### 2.1 What "calibrated" means
1. A source is **calibrated** only if the host can state a physical length per pixel **from explicit metadata**: a length unit plus a numeric size. The number alone (`1.0`, `0.25`) is never evidence, in either direction.
2. **Unknown is a first-class value.** Pixel, empty, dimensionless or missing units give *unknown*, whatever the number. The host never assumes 1 um/px, and **a bare scale with default pixel units is unknown, never assumed to be um** (this removes the Napari behaviour recorded in HOST_PARITY C19).
3. Explicit units win even when the scale is exactly 1: `1 micrometer` is 1.0 um/px; `1 millimeter` is 1000.0 um/px.
4. Unit conversion is to **micrometres per pixel** (the contract of `PixelSizeOf`, SPEC_WAVE2 1.4). Length units known to the host: at least `um`, `micron(s)`, `micrometer/-metre`, `nm`, `mm`, `cm`, `m`, and the Angstrom (`Angstrom`, `angstrom`, U+00C5, U+212B; 1 Angstrom = 1e-4 um). The micro sign has three accepted spellings: U+00B5 (micro sign), U+03BC (Greek mu) and ASCII `u`, each followed by `m`. **U+FFFD (the replacement character, a damaged micro sign) followed by `m` is not accepted**: the result is unknown with the warning `unit text 'X' is damaged; enter the pixel size`.
5. Anisotropic pixels (Y and X differ by more than 1e-3, relative to the larger) and non-length units give *unknown* plus a warning (`pixels are not square` / `unit 's' is not a length`); the scalar field is not filled (within the tolerance the field takes the mean of the X and Y sizes). **This is a behaviour change** in every host that fills the field from one axis today. Release-note line: *"A pixel size is no longer filled in automatically when the image's pixels are not square (X and Y differ by more than 0.1 %) or its unit is not a length; enter the pixel size yourself."*
6. Sources: Napari layer `scale` + `units`; Fiji `Calibration` (`scaled()`, `getUnit()`, `pixelWidth`); QuPath `PixelCalibration` (`hasPixelSizeMicrons()`); a file input by its TIFF/OME metadata with a length unit (`ResolutionUnit` NONE is unknown). **TIFF resolution tags alone are not a calibration when they look like a default:** `ResolutionUnit` INCH or CENTIMETER with a resolution equal (within 0.5 %) to 72 or 96 dpi (28.35 or 37.80 per cm) is unknown, not 352.8 or 264.6 um/px. An ImageJ `unit=` or OME `PhysicalSizeX` unit in the file wins over the tags.

### 2.2 The field, its states, and the transitions
A `PixelSizeOf` field has one of three states: `unset`, `auto(source, value)`, `user(value)`. The state is kept by the host as a **flag set by user edit events**, never inferred by comparing the value with the last auto value. A programmatic set does not make it `user`.

| event | state before | state after |
|---|---|---|
| source changes (image, file set or cleared, project image switched) and the new source is calibrated | `unset` or `auto` | `auto(new source, new value)` |
| same, and the new source is **unknown** | `unset` or `auto` | `unset`, field **cleared**, tooltip `not calibrated: 'image' has no pixel size` |
| source changes (any) | `user` | unchanged; the tooltip names the entered value and that it overrides the image |
| person types or pastes a value | any | `user(value)` |
| person clears the field, or presses "use the image's calibration" | any | `unset`, then re-derived from the current source (may become `auto` or stay `unset`) |
| file input is set | any non-`user` | derived from the **file** (the file is the exported source and wins over the open image) |
| file input is cleared | any non-`user` | derived from the open image again |

Precedence of the source is the precedence of what is exported: file input first, then the chosen image (Fiji #26 asks the same for the initial prefill).

### 2.3 Submitting, and what the request carries
1. **Run is blocked while a required linked field (`PixelSizeOf`, and in Wave 2 `TimeIntervalOf`, `ZStepOf`) is `unset`.** Message: `'pixel_size' needs a value: 'image' has no pixel size. Enter it in um.` A declared default on a linked field is **not** used as a stand-in (it was written for an author's example image).
2. `Optional[float]` linked field: `unset` sends `null`. Nothing is blocked.
3. A value outside `(0, inf)` or not finite is refused as today.
4. The request carries two things. The value in the manifest parameter, in um/px (unchanged). And a reserved input `_calibration`, like `_job_dir` and `_axes`, which tools never see. It is **per axis**, keyed by manifest parameter, with overall provenance:
```json
{"_calibration": {"pixel_size": {"of": "image", "source": "image|file|user",
  "axes": {"x": {"value": 1.0, "unit": "um", "source": "image", "raw": {"scale": 1.0, "unit": "micrometer"}},
           "y": {"value": 1.0, "unit": "um", "source": "image", "raw": {"scale": 1.0, "unit": "micrometer"}}}}}}
```
   `value` is in the canonical unit of the link (`um` per pixel for x, y and z; `s` for t); `unit` is that canonical unit; `source` is `image`, `file` or `user` per axis (an entered value is `user`); `raw` keeps the original scale and unit text when there was one. **Phase 1 fills `x` and `y` only** (a scalar `PixelSizeOf` needs an isotropic pair, 2.1.5); `z` (`ZStepOf`) and `t` (`TimeIntervalOf`) are added by Wave 2 with the same entry shape. The worker only copies the object into `run.json`; hosts write it into the run record too. A request with a `PixelSizeOf` value and no `_calibration` entry is a host bug and a test failure.
5. CLI and notebook: the same rule. The value comes from `--pixel-size` / the argument, or from the file's own calibration if linking is implemented; otherwise the run fails with the sentence of 2.3.1. They never default silently.

### 2.4 Fixtures: calibration
Known answers (`um_per_px`, or `unknown`); the first run of the form must produce them **in the request**, not only in the field.

| id | source | expected |
|---|---|---|
| CAL-01 | Napari scale (1,1), units (micrometer, micrometer) | 1.0, source image |
| CAL-02 | Napari scale (1,1), units default (pixel) | unknown |
| CAL-03 | Napari scale (1,1), units millimeter | 1000.0 |
| CAL-04 | Napari scale (0.25,0.25), units pixel or none | unknown (never read as um) |
| CAL-05 | 0.325 um, 325 nm, 0.000325 mm (any host) | 0.325 each (relative error < 1e-9) |
| CAL-06 | scale (0.5, 0.25), units um | unknown + `not square` warning |
| CAL-07 | scale (1,1), units second | unknown + `not a length` warning |
| CAL-08 | Fiji unit `micron`, pixelWidth 1.0 / unit `pixel`, width 1.0 / unit empty | 1.0 / unknown / unknown |
| CAL-09 | QuPath `hasPixelSizeMicrons()` true with 1.0 / false | 1.0 / unknown |
| CAL-10 | TIFF with ImageJ `unit=micron` spacing 1.0 / no resolution tags / `ResolutionUnit` NONE | 1.0 / unknown / unknown |
| CAL-11 | TIFF `ResolutionUnit` INCH, 72 dpi, no ImageJ/OME unit | unknown (not 352.78) |
| CAL-12 | TIFF `ResolutionUnit` INCH, 96 dpi, no ImageJ/OME unit | unknown (not 264.58) |
| CAL-13 | TIFF `ResolutionUnit` CENTIMETER, 28.35 and 37.80 per cm, no unit text | unknown, unknown |
| CAL-14 | TIFF `ResolutionUnit` INCH, 25400 dpi (not default-looking), no unit text | 1.0, source file |
| CAL-15 | unit text `"\u00B5m"` (micro sign), `"\u03BCm"` (Greek mu), `"um"`, each with scale 0.5 | 0.5 for all three |
| CAL-16 | unit text `"\uFFFDm"`, scale 0.5 | unknown + `damaged` warning |
| CAL-17 | unit text `"Angstrom"`, `"\u00C5"`, `"\u212B"`, scale 1.0 | 0.0001 each |
| CAL-18 | scale (0.5, 0.5004) um / scale (0.5, 0.5006) um | 0.5002 (difference 8e-4 is within 1e-3, the field takes the mean of x and y) / unknown + warning (difference 1.2e-3) |

Transitions (each asserts the field **and** the request/worker input):

| id | sequence | expected |
|---|---|---|
| CAL-T1 | A (0.25) -> B (0.5) | field 0.5, request 0.5, source image of B |
| CAL-T2 | A (0.25) -> uncalibrated B | field empty, run blocked with 2.3.1; Optional: request `null`; A's value is in no request |
| CAL-T3 | A (0.25), person types 0.3, switch to B (0.5) | 0.3, source user |
| CAL-T4 | state user(0.3), person clears field, source B (0.5) | auto 0.5 |
| CAL-T5 | open image A (0.25), file B uncalibrated | unset, run blocked (not A's value) |
| CAL-T6 | CAL-T5, then file cleared | auto 0.25 (A) |
| CAL-T7 | QuPath project image A -> file image uncalibrated | unset |
| CAL-T8 | required linked field with default 1.0, source unknown | blocked, the default is not sent |
| CAL-T9 | user types 0.25 equal to the last auto value, then switch to uncalibrated B | stays 0.25, source user (flag, not comparison) |

---

## 3. Retention under `LC_HOME`

### 3.1 Who does what
1. **Hosts never prune and never delete anything under `<LC_HOME>/results` or `<LC_HOME>/runs`.** Napari, Fiji and QuPath only *create* folders there and write two marker files (3.2). There is no retention code in any host.
2. **Only Tools prunes**: the reference `labconstrictor_tools.retention` and the CLI command `labconstrictor-tools prune [--root results|runs|all] [--dry-run]`. One implementation, in Python, so there is one policy and one place to test it.
3. **How a host triggers cleanup.** After a host has written `.lc-done.json` it starts `labconstrictor-tools prune` **in a subprocess** (user-approved), detached: it does not wait, ignores the exit code, logs a failure to the shared log, and a failure never fails or delays the run. The executable is the one in the app's worker environment (the same environment that runs the tools). A CLI run calls `prune` itself after writing its done file.
4. **GUI-only users get cleanup through the Tools CLI.** Nobody has to open a terminal: the host's subprocess is what runs it. If the subprocess cannot start, folders accumulate; **no host falls back to deleting them itself**.
5. Never touched by `prune`: `--out` folders, `state`, `logs`, and anything outside the two roots. Temporary job folders of a host live outside `LC_HOME` and are the host's own (3.4).

### 3.2 Markers, written by hosts and the CLI
`.lc-owner.json` is written first, when the folder is created: `{"lc_marker": 1, "kind": "result|run", "name": "<folder name>", "host": "cli|napari|fiji|qupath|notebook", "pid": 1234, "created": "2026-10-12T09:30:00.123Z", "token": "<uuid4>"}`. `.lc-done.json` is written last, atomically (temp file then rename): `{"finished": "<UTC ISO-8601>", "status": "ok|failed|cancelled"}`. A half-written folder has no done file and is therefore never eligible. Result folders are named `<YYYYMMDDTHHMMSS>_<6 hex>_<app>_<tool>` (slug of `A-Za-z0-9_.-`) in every host; run records may use any slug (Fiji's millisecond stamp stays). The name is a convenience; the marker is the authority.

### 3.3 What `prune` may delete
Only two roots are ever pruned: `<LC_HOME>/results` and `<LC_HOME>/runs`. An entry is **eligible** only if **all** hold:
1. a direct child of the root, name made of `A-Za-z0-9_.-`, a real directory by `lstat` (not a symlink, not a Windows junction or other reparse point), and its real path's parent is the real path of the root;
2. it has a valid `.lc-owner.json` (`lc_marker` 1, right `kind`, `name` equal to the folder name, so a copied or renamed folder is foreign);
3. it has `.lc-done.json`;
4. `prune` holds the retention lock (3.5).

Never eligible: foreign folders (any name, even `20261008T120000_reanalysis_backup`), **legacy folders from older versions (no marker)**, folders with no done file (active or crashed), symlinks, junctions, files.

Counting: `RESULTS_KEPT = 20`, `RUN_RECORDS_KEPT = 50`, counted over **eligible** entries only (foreign, legacy and active ones do not use up the quota and are never evicted to make room), ordered by `created` in the owner file then by name, not by directory name. Delete = rename to `.lc-deleting-<token>` inside the root, then remove without following links inside it; a leftover `.lc-deleting-*` that passes (2) is removed at the next prune. A folder a host reported to the person as holding a result is eligible like any other once it is past the quota; hosts therefore keep the reported path in the run record, and the status says that older results are cleaned up by `labconstrictor-tools prune`.

### 3.4 Files a host reports, and temporary job folders (not pruning)
Temporary job folders outside `LC_HOME` (Napari `lcin_*`, Fiji `lcjob_fiji_*`, notebook `lcnb_*`) are the host's own and the host may delete them. **Before deleting**, the host moves every output file it will report (a `FileOut` inside the job folder; an image or labels result it did not or could not display) into an owned folder `<LC_HOME>/results/...` (3.2) and reports **that** path, so a reported path never points into a folder about to be deleted. Files outside the job folder are never moved or modified. Cancelled and failed runs still remove their temporary folder (their owned folder, if one was made, gets `.lc-done.json` `failed` / `cancelled`). The notebook stops leaving `lcnb_*` for ever by using the same owned folder.

### 3.5 Concurrency (Tools only)
`prune` takes one exclusive, non-blocking lock on `<LC_HOME>/.retention.lock`, implemented once in `labconstrictor_tools.retention`. If it cannot take the lock it exits 0 without deleting (another prune is running, or the share does not support locks). Creation needs no lock: owner first, done last. Several hosts starting `prune` at once is therefore safe.

### 3.6 Where the reference changes
| today | rule |
|---|---|
| CLI: start-anchored `^\d{8}T\d{6}_`, prunes before creating (Tools #55) | `retention.prune` after done, marker-based (3.3); CLI `prune` command |
| `runs._prune`: every sub-folder | `retention.prune(root, "run", 50)`, eligible only |
| Fiji `writeRunRecord`: prunes every sub-folder | no pruning; writes markers; starts `prune` (3.1.3) |
| QuPath `newJobDir`: deletes every sub-folder beyond 20 | no pruning; adopts the CLI folder name (HOST_PARITY L01), markers, `prune` |
| Napari / Fiji `rmtree(job_dir)` | allowed outside `LC_HOME`, after 3.4 |

### 3.7 Fixtures: retention
All use a temporary `LC_HOME`; every survivor is checked **by file contents** (a sentinel file with fixed bytes), not only by count. `done(n)` = n owned folders with both markers, `created` increasing. **Windows note:** a plain symlink needs administrator rights or developer mode; a directory junction is made with `mklink /J`. RET-05 creates a symlink and, on Windows, also a junction; if a link kind cannot be created the fixture reports `unsupported` for it, never `pass`.

**A. Prune eligibility (run against the Tools reference `retention.prune` and the CLI `prune`; not a host test)**

| id | setup | action | expected |
|---|---|---|---|
| RET-01 | foreign `results/20261008T120000_reanalysis_backup/x.txt` ("keep") + done(300) | `prune` after each | foreign folder and `x.txt` intact; exactly 20 owned remain, the newest 20 by `created` |
| RET-02 | foreign `runs/0000_keep_this_analysis/x.txt` + done(120) | `prune --root runs` | foreign intact; exactly 50 owned |
| RET-03 | 25 results with no `.lc-done.json` | `prune` | all 25 present, with files |
| RET-04 | done(30) | `prune` | the 20 latest by `created` remain |
| RET-05 | `results/<valid name>` is a symlink (and on Windows a junction) to `outside/` holding an owner marker and done file; 40 owned | `prune` | link and all of `outside/` intact |
| RET-06 | owned folder copied and renamed (marker `name` differs) | `prune` | not deleted |
| RET-07 | 30 legacy folders (valid names, no marker) + done(25) | `prune` | all 30 legacy remain; 20 owned remain |
| RET-08 | done(100); four `prune` processes started at once (CLI only) | concurrently | exactly 20 owned remain; no foreign entry lost; every process exits 0 |
| RET-09 | lock held by another process | `prune` | exits 0, deletes nothing |
| RET-12 | owned crashed folder (no done file) + done(30) | `prune` | the crashed folder survives |
| RET-13 | two equal `created` values | `prune` | order by `created` then name, deterministic |

**B. Hosts never delete (Napari, Fiji, QuPath, notebook; the real host, with the `prune` subprocess replaced by a recorder)**

| id | setup | action | expected |
|---|---|---|---|
| HRET-01 | foreign `results/20261008T120000_reanalysis_backup/x.txt` and foreign `runs/0000_keep_this_analysis/x.txt` | the host does 60 runs | both foreign folders and `x.txt` intact |
| HRET-02 | done(60) owned results and done(120) owned run records already present | the host does 5 runs | none of the old folders is gone (counts only grow) |
| HRET-03 | none | one run | the folder has a valid `.lc-owner.json` (name equals folder name) and, after the run, a valid `.lc-done.json` with the right status |
| HRET-04 | `prune` replaced by a recorder, then by a command that fails | one run each | the recorder saw `labconstrictor-tools prune` started after the done file exists; a failing command does not fail the run |
| RET-10 | job folder with `report.txt` ("data") returned as `FileOut` | run to success, close the widget | reported path exists under `results/`, contents "data"; job folder gone |
| RET-11 | failed or cancelled run | finish | temporary job folder removed; an owned folder, if any, has `failed` / `cancelled` |
| RET-14 | undisplayable (over the display limit) `ImageOut` | run | file stays at a stable owned path, the path is shown |

---

## 4. Run identity

1. **Snapshot at run start, on the UI thread, before any worker call.** The host builds one immutable record and carries it through export, worker call and result placement: `run_id` (uuid4), `app`, `tool`, parameter values, calibration states (2.3), and for every `Image` / `Labels` / `RegionOf` input the **source identity** and **frame** (1.1.2): the selected selection geometry copied by value (vertices, planes), not a live reference.
2. **Source identity is an object, not a label.** Napari: the layer object (not its name). Fiji: the `ImagePlus` object and its window id (not its title). QuPath: the `ImageData` object plus project entry id. A chooser text such as `Current image: slide A` and the prefix test `startsWith("Current image")` are never identity.
3. **Export reads the snapshot.** Changing the active image, layer selection or selected annotations after the click cannot change what is exported or which selection is used.
4. **Placement checks identity first.** Results are placed only if the source is the same object, still open (Napari: still in `viewer.layers`; Fiji: window still open; QuPath: the same `ImageData` still accessible), and its exported shape is unchanged. If so the host applies the **current** transform of that same layer (so the result follows the layer), through 1.1.3. If not, `target_unavailable`: outputs are kept, nothing is drawn on another image, and the status says `run <run_id> on 'A': 'A' is no longer open; results are in <path>`.
5. **Output metadata binds to the snapshot, not the widget.** The app and tool recorded on a result (layer metadata, window property, annotation property, run record) come from the snapshot; a tool or app change while running cannot rebind them. Every result drawn carries `run_id`.
6. Fixtures:

| id | sequence | expected |
|---|---|---|
| RUN-01 | start on A (delayed tool), activate B, tool returns points | nothing on B; `target_unavailable` if A is gone, else points on A |
| RUN-02 | start on A with a selection, change the selection during export | exported crop and mask are those of the click |
| RUN-03 | start tool X, switch the widget to tool Y while running | result metadata app/tool are X's |
| RUN-04 | start on A, close A | outputs kept, status names `run_id` and path, no exception |
| RUN-05 | Napari: layer A is moved (translate changed) during the run | points follow A's transform at placement |
| RUN-06 | two runs in a row on A then B | each result carries its own `run_id` and lands on its own source |

---

## 5. Asynchronous lookups (`ChoicesFrom`)

1. **Identity of a lookup.** Every request captures `(form_gen, app, tool, param, deps, request_id)`.
   `form_gen` is a **process-wide monotonic integer that is never reset**; it increases whenever a form is built or destroyed (app change, tool change, widget close). `request_id` is a monotonic integer per widget, never reset. `deps` is the serialised snapshot of the values the lookup depends on (including the source image identity and calibration if it uses them).
2. **A reply is applied only if all of these still hold at reply time:** `form_gen` equals the current one; `app` and `tool` equal the current ones; `request_id` is the latest issued for `param`; `deps` equals the dependencies **now** (recomputed, not remembered). Otherwise it is dropped, including its error and tooltip.
3. **A dependency change invalidates immediately.** The moment a dependency changes, the parameter's latest `request_id` is advanced and its choices marked pending; the debounce (400 ms) only delays the new request, it does not delay the invalidation.
4. **Bounded work.** At most one lookup is in flight per widget (per host window). Pending lookups are coalesced: one pending slot per parameter, a newer request replaces an older pending one; at most 8 pending in all (oldest dropped and logged). A lookup that exceeds 60 s is cancelled and its worker discarded. No unbounded thread creation: one worker thread (executor) per widget.
5. **One owner for the worker.** A single controller per window owns the worker cache; every start, reuse, release, reap and close goes through it (one lock, or one thread). Each job (run or lookup) captures the worker instance and its app at submission and uses only that one. A lookup never uses or replaces a worker held by a running tool; while a run is active, lookups wait (existing retry, 1500 ms). An app switch during a run never replaces the run's worker; the new app's worker is created after the run ends.
6. **Shutdown.** On widget close: set `closed`, drop pending lookups, cancel the in-flight one, close workers within the close timeout (10 s, HOST_PARITY K03), then kill. A worker created after `closed` was set is closed by the thread that created it. After close there are no live workers and no live threads of the widget.
7. Fixtures (deterministic barriers; the delayed source tool blocks on an event the test releases):

| id | sequence | expected |
|---|---|---|
| ASY-01 | tool A and B both have `ChoicesFrom` param `mode`; A's lookup is delayed; switch to B; release A | B's dropdown shows only B's choices; displayed choices and value checked |
| ASY-02 | change the dependency of `mode`, release the old reply before the debounce fires | old reply dropped; `mode` is pending, not showing old choices |
| ASY-03 | A's lookup fails after switch to B | no tooltip or error on any B field |
| ASY-04 | change a dependency 50 times in 1 s | at most 1 in flight, at most 1 pending per param; worker processes started <= 1 |
| ASY-05 | two parameters each with `ChoicesFrom`, both lookups requested at once | one worker process; each reply goes to its own control |
| ASY-06 | start a run, switch app, request a lookup | run uses its worker to the end; the lookup runs after, in the new app's worker |
| ASY-07 | close the widget with a lookup in flight | no worker process or thread of the widget alive afterwards; no worker created after close survives |
| ASY-08 | interleave acquire/release/reap/close from three threads with barriers | cache consistent (each worker owned once), no double close |

---

## 6. Number limits for form fields
1. A form field with no declared `Min` / `Max` accepts integers up to **+-(2^53 - 1) = +-9007199254740991** (the largest integer every double and every JSON number holds exactly) and floats up to **+-1e15**. This replaces the `+-(2^31-1)` and `+-1e9` limits of HOST_PARITY A06, A07.
2. A typed, pasted or macro value beyond a limit (declared or default) is **refused, never clamped**: no run starts, nothing is sent, the message names the field and the limit: `'L' must be <= 9007199254740991` (or `>= -9007199254740991`), the worker templates of HOST_PARITY I06. A GUI box that cannot hold such a number uses a text-backed or `long` / `double` widget; it must not silently shorten a value.
3. Conformance key `limits.form_integer_max = 9007199254740991` (replaces `unbounded_integer`), and `limits.unbounded_float = 1e15`.
4. Fixture per host (Napari, Fiji dialog, Fiji macro, QuPath, notebook; the CLI is the worker's reference): `NUM-01` typed `9007199254740991` is accepted and the request carries exactly that integer; `NUM-02` typed `9007199254740992` is refused with the message above, no clamp (the value never becomes `9007199254740991` or `2147483647`), no run, no request; `NUM-03` typed `-9007199254740992` likewise; `NUM-04` float `1e15` accepted, `1.0000000000000002e15` refused; `NUM-05` a declared `Max` of 10 refuses 11 (unchanged).

---

## 7. Order of work and acceptance
1. Tools PR: `retention` module and CLI `prune` (3.1-3.5), fixtures from sections 1-6 in `conformance.json` (`wrong_science`), new `host_internal_codes`, the per-axis `_calibration` reserved input (2.3.4), `PixelSizeOf` wording in AUTHORING.md and PROTOCOL.md, the number limits. Replaces HOST_PARITY L01-L03 and H05.
2. One PR per host, each closing the issues in the table at the top and running its themes' fixtures through a real GUI or harness (never only the helper function).
3. Tools #87 imports `wrong_science` as its first known-answer fixtures; Napari #31-#38, Fiji #26-#30 and QuPath #14-#21 become regressions when fixed.

## 8. Decisions and follow-ups
Decided by the maintainers:
* A linked pixel-size field with an unknown source blocks the run (2.3.1; SPEC_WAVE2 1.4 amended).
* A bare scale with default pixel units is unknown, never assumed um (2.1.2).
* QuPath refuses an ROI on another plane and never switches the viewer (1.2.7).
* Legacy unmarked folders are never auto-deleted (3.3).
* **Hosts never prune.** Hosts write markers and start `labconstrictor-tools prune` in a subprocess; only Tools deletes (3.1). Final: the retention and hosts-prune-subprocess decisions (section 3) are not open for change in this wave.
* Form integers up to +-(2^53-1), floats +-1e15; beyond is refused, never clamped (section 6).
* The per-axis `_calibration` shape (x, y, z, t; phase 1 fills x, y) is final.
* Decided (user, 12 Oct): a damaged micro sign (U+FFFD followed by `m`) is unknown with a warning, never read as micrometres (2.1.4).
* Decided (user, 12 Oct): TIFF resolution tags equal to 72 or 96 dpi (within 0.5 %) with INCH units are unknown (2.1.6).
* Decided (user, 12 Oct): the unknown-calibration rule applies to `TimeIntervalOf` and `ZStepOf` as well as `PixelSizeOf` (2.3.1; SPEC_WAVE2 1.4).

Follow-up item: an explicit `labconstrictor-tools clean --legacy` command with a dry run (lists, then deletes only on confirmation). Not part of this wave.

Working decisions, **default, not yet confirmed**:
1. Fiji with a file source opens the file in its own window; QuPath uses table plus file (1.3). (default, not yet confirmed)
2. Napari with a file source: pixel-frame layer only, no extra image layer (1.3). (default, not yet confirmed)
3. Napari lower-dimensional results on N-D sources only when dropped axes do not move the plane; confirm in Wave 2 (1.3). (default, not yet confirmed)
4. Crashed runs (no `.lc-done.json`) are never pruned (3.3). (default, not yet confirmed)
5. Retention quota counts only eligible folders (3.3). (default, not yet confirmed)
6. Lookup limits: one in flight, 8 pending, 60 s timeout (section 5). (default, not yet confirmed)
7. `prune` skips silently when it cannot take the lock, e.g. on a network share (3.5). (default, not yet confirmed)
8. Napari snapshot identity is the object reference plus a still-in-`viewer.layers` check, not names or `unique_id` (section 4). (default, not yet confirmed)
