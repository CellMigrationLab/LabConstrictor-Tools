# Spec (proposal): the "wrong-science" fix wave

Status: **for review, nothing is implemented.** Maintainer decisions are recorded in section 7. Same conventions as [SPEC_WAVE2.md](SPEC_WAVE2.md) and [HOST_PARITY.md](HOST_PARITY.md): additive within `protocol: 1`, rules are host-neutral, a rule is "done" when its fixtures pass in every host that claims the feature. The fixtures below are data, meant to live in `labconstrictor_tools/conformance.json` under the key `wrong_science` and to be reused by the conformance suite (Tools #87).

These rules exist because a tool run can succeed and still be scientifically wrong: a mask on the wrong pixels, a result drawn away from its image, a pixel size from another image, a researcher's folder deleted. Each host fixes its own code, but all of them implement **the same rule**, so a fix in one host cannot leave another one behind.

| # | Theme | Rule set | Issues it settles |
|---|---|---|---|
| 1 | Coordinate frame | section 1 | Napari #31 #33 #34, Fiji #30, QuPath #21 (and the plane/offset half of QuPath #16) |
| 2 | Calibration | section 2 | Napari #35 #38, Fiji #26, QuPath #15 |
| 3 | Retention | section 3 | Tools #55, Napari #32, Fiji #28, QuPath #14 |
| 4 | Run identity | section 4 | QuPath #16 (and the same hazard in Napari and Fiji) |
| 5 | Async lookups | section 5 | Napari #36 #37, QuPath #19 |

Out of scope here (tracked in their own issues): Fiji #29 (macro replay of required scalars), Fiji #31 (optional warp comparison blocking the overlay), Fiji #33 (Appose completion ordering). They are host bugs with no cross-host rule.

Words: **MUST** and **MUST NOT** are tested by a fixture; **SHOULD** is not. "Source" is the input named by `ApplyTo` (else the first `Image` or `Labels` input in manifest order, never "the first value of any type", never the active, last shown or topmost image). "Refuse" means: do not start the run (inputs) or do not draw the result (outputs), say why in one sentence, keep every output file, never fall back to another image.

---

## 1. Coordinate frame

### 1.1 The rule
1. **A result lives in the data space of its source, as it was exported.** `PointsOut`, `ShapesOut`, `ImageOut` and `LabelsOut` coordinates are pixel coordinates of the image file the host wrote for the source (after any crop or plane choice), pixel centres at integers, `(y, x)` for points and `[x, y]` for shapes, as in PROTOCOL.md and HOST_PARITY H06. The worker never sees a world, viewer, slide or calibrated coordinate.
2. **The host owns the mapping back.** It records, at run start (section 4), a *frame* for each exported image: `{source, shape, plane, offset, transform}`. `offset` is the pixel origin of the exported area inside the source's full data grid (`(0, 0)` unless the host exports a crop); `plane` is the exported `(t, z)`.
3. **Placement invariant (the one test every host runs).** For every result coordinate `p`: the place where the host draws it equals the place where the host draws pixel `p + offset` of the source. Napari: `result.data_to_world(p) == source.data_to_world(p + offset)`. Fiji and QuPath: the ROI vertex is at `p + offset + 0.5` pixels of the source image, on the exported plane.
4. **No lossy resampling.** The host never resamples a result to fit; it carries the source transform over. Conversion is exact, so "refuse" is reserved for cases where an exact mapping does not exist (1.4).
5. **No silent fallback.** A result whose source cannot be resolved, is gone, or has no display (a file) is never drawn on another image or layer. It is shown as a table (points), listed as a file (shapes, images), and the status says where the files are.
6. **Outputs without a source.** `ImageOut` / `LabelsOut` with no `ApplyTo` keep the documented default: pixel origin, identity transform, no units. `PointsOut` / `ShapesOut` with no `ApplyTo` use the first `Image` input (H05); with no image input they are a table or file.
7. **Size mismatch is stated, not hidden.** If an `ImageOut` / `LabelsOut` that declares `ApplyTo` has a Y/X shape different from the exported frame, the host shows it at the default pixel origin (rule 6) and says once: `'name' is W x H but 'source' was exported as W2 x H2; shown at the pixel origin, not aligned`.
8. **`Replace()` recomputes the frame.** Replacing a result layer or window sets the transform again from the new result; it never keeps the previous one.

### 1.2 Input selections (`RegionOf`, QuPath "Image area")
1. A selection is converted **into the exported image's pixel grid**, then rasterised there. The mask has exactly the exported image's Y/X shape.
2. Rasterisation: a mask pixel is set if its centre lies inside the polygon (boundary pixels are never used in fixtures, so hosts need not agree on them).
3. Napari: vertices go `shapes.data_to_world` then `image.world_to_data` (full transform: scale, translate, rotate, shear, affine), at level 0 of a multiscale image. The mask is in the image's data grid whatever the shapes layer's own transform.
4. A selection MUST NOT be rasterised in its own raw data coordinates.
5. All vertices of one selection must land on one plane of the image. Otherwise refuse with `selection_mixed_planes`.
6. QuPath: the crop is the integer bounding box of the selected annotations (floor of the minimum, ceil of the maximum, clamped to the image); `offset` is its top-left corner; the mask is the annotations translated by `-offset`.
7. **QuPath planes.** Every selected annotation MUST be on one `ImagePlane`, and that plane MUST be the one exported (the viewer's plane at run start). Different planes among the selection: refuse `selection_mixed_planes`. One plane that is not the exported one: refuse `selection_plane_mismatch` (the host does not switch planes behind the person's back). The exported TIFF, the mask and the restored annotations all carry that one plane.

### 1.3 How each host maps
| | frame comes from | result drawn with | file input | transform that cannot be mapped |
|---|---|---|---|---|
| Napari | the Image layer (level 0 of a multiscale one) | new layer gets the source's `scale`, `translate`, `rotate`, `shear`, `affine` (and units); N-D: the transform acts on the trailing axes the result has, leading axes of the source must not move the plane (note below), else refuse | pixel frame of the file: identity, no units; the layer is named after the file; no layer is searched | refuse `frame_unsupported_transform` (non-invertible YX block, or a leading-axes coupling that cannot be expressed on a lower-dimensional result) |
| Fiji | the `ImagePlus` (by object, not by title) | ROI or overlay in the pixel space of that image, `setPosition(c, z, t)` of the exported plane; calibration origin and scale are not applied (ROIs are pixel based) | the file is opened in its own window (titled with the file name) and the result goes there; if it cannot be opened: table and file | Fiji images have no transform: identity by construction |
| QuPath | the `ImageData` of the run (section 4), plane and `offset` above | annotation on the exported plane, vertices `p + offset + 0.5` in full-resolution pixels (downsample 1.0) | not displayable: table plus file, status `file input: results are in the file's pixel frame` | QuPath images have no transform: identity by construction |
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
Base image `ASYM`: uint16, 8 rows by 12 columns, `value(y, x) = 100*y + x`. Rectangles have vertices on half pixels, so no pixel centre lies on an edge. `world` is Napari only; `target_px` is the position on the target image in its own data pixels (before the +0.5 of Fiji/QuPath), the check in every host.

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
         {"selection": [{"z": 0, "t": 0}, {"z": 1, "t": 0}], "expect": "refuse selection_mixed_planes"}]},
      {"id": "CF-11", "name": "size mismatch is stated",
       "result": {"type": "labels", "shape": [4, 6], "apply_to": "image"}, "source_export_shape": [8, 12],
       "expect": {"transform": "identity", "status_contains": "not aligned"}},
      {"id": "CF-12", "name": "Replace recomputes the transform",
       "sequence": ["labels result on source translate [100,0]", "Replace with result for source translate [0,0]"],
       "expect": {"world_of_0_0": [0, 0]}},
      {"id": "CF-13", "name": "non-invertible source transform",
       "source": {"affine": [[0,0,0],[0,0,0],[0,0,1]]}, "expect": "refuse frame_unsupported_transform"}
    ]}}
}
```
Checks that every case also makes: the **worker's input file** (exported pixels equal `ASYM` or its crop, mask pixels equal `rect_mask_pixels`), the **actual drawn coordinates** (not only "no error"), and that nothing was drawn on any image other than `target`.

---

## 2. Calibration

### 2.1 What "calibrated" means
1. A source is **calibrated** only if the host can state a physical length per pixel **from explicit metadata**: a length unit plus a numeric size. The number alone (`1.0`, `0.25`) is never evidence, in either direction.
2. **Unknown is a first-class value.** Pixel, empty, dimensionless or missing units give *unknown*, whatever the number. The host never assumes 1 um/px, never assumes um for a bare number.
3. Explicit units win even when the scale is exactly 1: `1 micrometer` is 1.0 um/px; `1 millimeter` is 1000.0 um/px.
4. Unit conversion is to **micrometres per pixel** (the contract of `PixelSizeOf`, SPEC_WAVE2 1.4). Length units known to the host: at least `um`, `micron(s)`, `micrometer/-metre`, `nm`, `mm`, `cm`, `m`.
5. Anisotropic pixels (Y and X differ by more than 1e-3 relative) and non-length units give *unknown* plus the existing warning (`pixels are not square` / `unit 's' is not a length`); the scalar field is not filled.
6. Sources: Napari layer `scale` + `units`; Fiji `Calibration` (`scaled()`, `getUnit()`, `pixelWidth`); QuPath `PixelCalibration` (`hasPixelSizeMicrons()`); a file input by its TIFF/OME metadata with a length unit (`ResolutionUnit` NONE is unknown).

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
1. **Run is blocked while a required linked field is `unset`.** Message: `'pixel_size' needs a value: 'image' has no pixel size. Enter it in um.` A declared default on a linked field is **not** used as a stand-in (it was written for an author's example image).
2. `Optional[float]` linked field: `unset` sends `null`. Nothing is blocked.
3. A value outside `(0, inf)` or not finite is refused as today.
4. The request carries two things. The value in the manifest parameter, in um/px (unchanged). And a reserved input `_calibration`, like `_job_dir` and `_axes`, which tools never see:
```json
{"_calibration": {"pixel_size": {"source": "image|file|user", "of": "image", "unit": "micrometer", "scale": 1.0, "um_per_px": 1.0}}}
```
   `source` is `user` for any entered value. The worker only copies it into `run.json`; hosts write it into the run record too. A request with a `PixelSizeOf` value and no `_calibration` entry is a host bug and a test failure.
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

### 3.1 What may be deleted
Only two roots are ever pruned: `<LC_HOME>/results` and `<LC_HOME>/runs`. Nothing else, ever (not `--out` folders, not `state`, not `logs`, not temporary job folders of a host).

An entry of a root is **eligible for deletion** only if **all** hold:
1. it is a direct child of the root, its name uses only `A-Za-z0-9_.-`, and `lstat` says it is a real directory (not a symlink, not a Windows junction or other reparse point);
2. its real path's parent is the real path of the root;
3. it contains `.lc-owner.json`, written first when the folder was created, with `"lc_marker": 1`, the right `kind` (`result` or `run`), and `"name"` equal to the folder name (a copied or renamed folder is therefore foreign);
4. it contains `.lc-done.json` (written last, atomically: temp file then rename) with `status` of `ok`, `failed` or `cancelled`;
5. the retention lock is held by this process (3.3).

`.lc-owner.json`: `{"lc_marker": 1, "kind": "result", "name": "...", "host": "cli|napari|fiji|qupath|notebook", "pid": 1234, "created": "2026-10-12T09:30:00.123Z", "token": "<uuid4>"}`. `.lc-done.json`: `{"finished": "<UTC ISO-8601>", "status": "ok"}`.

Not eligible, never touched: foreign folders (any name, even `20261008T120000_reanalysis_backup`), **legacy folders from older versions (no marker)**, folders without `.lc-done.json` (active or crashed), symlinks, files.

### 3.2 How many are kept and which go
1. Constants shared by every host and the CLI: `RESULTS_KEPT = 20`, `RUN_RECORDS_KEPT = 50`. They count **eligible** entries only; foreign, legacy and active folders do not use up the quota and are never evicted to make room.
2. Order is by `created` in the owner file (then folder name), **not by directory name**, so a host with another naming scheme does not skew it.
3. Pruning happens **after** a run has written its own `.lc-done.json`, never before the run's folder exists, so a run cannot evict its own or a concurrent run's folder.
4. Delete = rename the folder to `.lc-deleting-<token>` inside the root (still owner-marked), then remove it without following symlinks inside it. A leftover `.lc-deleting-*` that passes 3.1 (3) is removed at the next prune.
5. Names: result folders `<YYYYMMDDTHHMMSS>_<6 hex>_<app>_<tool>` (slug of `A-Za-z0-9_.-`) in every host; run records any slug. The name is a convenience; **the marker is the authority**.
6. A folder the host reports to the person as holding a result (`FileOut`, an undisplayed `ImageOut`) is never deleted by the host that reported it, within the session or after.

### 3.3 Concurrency, hosts, CLI
1. One lock file, `<LC_HOME>/.retention.lock`, held with an OS file lock (`fcntl.flock` / `msvcrt.locking`; `FileChannel.tryLock` on the JVM) for the whole prune. **Non-blocking:** if it cannot be taken, skip pruning silently; retention is best effort and never delays or fails a run.
2. Creation needs no lock: writing the owner file first and `.lc-done.json` last makes a half-written folder ineligible by construction.
3. Every host and the CLI use **one policy**: the Python reference is `labconstrictor_tools.retention` (functions `create_owned(root, kind, host, name)`, `mark_done(folder, status)`, `prune(root, kind, keep)`); Fiji and QuPath port it line by line and run the fixtures of 3.5. A host that cannot guarantee 3.1 for a root MUST NOT prune it.
4. Crashed or abandoned runs (no `.lc-done.json`) are never deleted automatically. A later explicit command may list them; automatic cleanup of them is out of scope.
5. Temporary job folders outside `LC_HOME` (Napari `lcin_*`, Fiji `lcjob_fiji_*`, notebook `lcnb_*`) are the host's own and may be deleted by it, **but** before deleting, the host moves every output file it will report (a `FileOut` inside the job folder; an image or labels result it did not or could not display) into an owned folder `<LC_HOME>/results/...` (3.1) and reports **that** path. A reported path never points into a folder that is about to be deleted. Files outside the job folder are never moved or modified. Cancelled and failed runs still remove their temporary folder. The notebook stops leaving `lcnb_*` for ever by using the same owned folder.

### 3.4 Where the reference changes
| today | rule |
|---|---|
| CLI: start-anchored `^\d{8}T\d{6}_`, prunes before creating (Tools #55) | marker, eligible-only, prune after done (3.1, 3.2) |
| `runs._prune`: every sub-folder | the same `prune(root, "run", 50)` |
| Fiji `writeRunRecord`: every sub-folder, sorted by name | the same, with the Fiji stamp allowed (any slug) |
| QuPath `newJobDir`: every sub-folder beyond 20, by name | the same; and QuPath adopts the CLI folder name (HOST_PARITY L01) |
| Napari / Fiji `rmtree(job_dir)` | 3.3.5 |

### 3.5 Fixtures: retention
All use a temporary `LC_HOME`; every survivor is checked **by file contents** (a sentinel file with fixed bytes), not only by count. `done(n)` means n owned folders with markers and `.lc-done.json`, `created` increasing.

| id | setup | action | expected |
|---|---|---|---|
| RET-01 | foreign `results/20261008T120000_reanalysis_backup/x.txt` ("keep") + done(300) one by one | 300 runs via CLI | foreign folder and `x.txt` intact; exactly 20 owned remain, the newest 20 by `created` |
| RET-02 | foreign `runs/0000_keep_this_analysis/x.txt` + done(120) | record a task | foreign intact; exactly 50 owned records |
| RET-03 | 25 results with no `.lc-done.json` (concurrent, started) | a 26th run finishes and prunes | all 25 still present, with their files |
| RET-04 | done(30) | prune | the 20 with the latest `created` remain; the 10 oldest are gone |
| RET-05 | `results/<valid name>` is a symlink to `outside/` that contains an owner marker and done file | prune with 40 owned | symlink and everything in `outside/` intact |
| RET-06 | owned folder copied and renamed (marker `name` differs) | prune | not deleted |
| RET-07 | 30 legacy folders (valid names, no marker) + done(25) | prune | all 30 legacy remain; 20 owned remain |
| RET-08 | CLI, Fiji, Napari and QuPath writers (or their ports) each add done(20) to the same `LC_HOME`; four processes prune at once | concurrently | no foreign or active entry lost; total owned = 20 per root; no process error |
| RET-09 | lock held by another process | prune | returns without deleting, no error |
| RET-10 | Napari-style job folder with `report.txt` ("data") returned as `FileOut` | run to success, close the widget | reported path exists under `results/`, contents "data"; job folder gone |
| RET-11 | failed or cancelled run | finish | temporary job folder removed; its owned folder (if any) has `.lc-done.json` `failed` / `cancelled` |
| RET-12 | owned crashed folder (no done file), 30 done | prune | the crashed folder survives |
| RET-13 | two `created` values equal | prune | order is by `created` then name, deterministic |
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

## 6. Order of work and acceptance
1. Tools PR: `retention` module (3.1-3.3), fixtures from sections 1-5 in `conformance.json` (`wrong_science`), new `host_internal_codes`, the `_calibration` reserved input (2.3.4) and `PixelSizeOf` wording in AUTHORING.md/PROTOCOL.md. Replaces HOST_PARITY L01-L03 and H05.
2. One PR per host, each closing the issues in the table at the top, each running the fixtures of its themes through a real GUI or harness (never only the helper function).
3. Tools #87 imports `wrong_science` as its first known-answer fixtures; Napari #31-#38, Fiji #26-#30 and QuPath #14-#21 become regressions when fixed.

## 7. Decisions and follow-ups
Decided by the maintainers: a linked pixel-size field with an unknown source blocks the run (2.3.1; SPEC_WAVE2 1.4 amended); a bare scale with default pixel units is unknown, never um (2.1.2); QuPath refuses an ROI on another plane and never switches the viewer (1.2.7); legacy unmarked folders are never auto-deleted (3.1).

Follow-up item: an explicit `labconstrictor-tools clean --legacy` command with a dry run (lists, then deletes only on confirmation). Not part of this wave.

Working decisions, **default, not yet confirmed** (open for the maintainers to change):
1. `_calibration` reserved input is added (2.3.4), additive; tools never see it. (default, not yet confirmed)
2. Fiji with a file source opens the file in its own window; QuPath uses table plus file (1.3). (default, not yet confirmed)
3. Napari with a file source: pixel-frame layer only, no extra image layer (1.3). (default, not yet confirmed)
4. Napari lower-dimensional results on N-D sources only when dropped axes do not move the plane; confirm against the Wave 2 time-lapse work (1.3). (default, not yet confirmed)
5. Crashed runs (no `.lc-done.json`) are never auto-deleted (3.3.4). (default, not yet confirmed)
6. Retention quota counts only eligible folders (3.2.1). (default, not yet confirmed)
7. Lookup limits: one in flight, 8 pending, 60 s timeout (section 5). (default, not yet confirmed)
8. Java hosts port `retention` line by line, governed by the RET fixtures; no shared helper binary (3.3.3). (default, not yet confirmed)
9. `LC_HOME` on a network share: hosts skip pruning when the lock cannot be verified. (default, not yet confirmed)
10. Napari snapshot identity is the object reference plus a still-in-`viewer.layers` check, not names or `unique_id` (section 4). (default, not yet confirmed)
