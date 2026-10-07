# What each host does with each feature

Hosts: **Napari** (dock widget), **Fiji** (SciJava dialog, Groovy script or jar), **QuPath** (JavaFX window). "plain" = shown as an ordinary field, nothing is lost.

| Feature | Napari | Fiji | QuPath |
|---|---|---|---|
| Plain parameters, bounds, units, tooltips | yes | yes | yes |
| `Optional` / "set" box | yes | yes ("Set <name>") | yes |
| `Group` headings, `Advanced` section | yes (checkbox toggles it) | headings in the dialog | heading, folded section |
| `Collapsed` (accordion) | yes (click the heading) | plain heading (SciJava cannot fold) | yes (titled pane) |
| `Widget("slider")` / `Widget("radio")` | planned | planned | planned |
| `EnabledWhen` | greys out | ignored: every field stays editable | greys out |
| `PixelSizeOf` | prefilled from the layer | prefilled from the calibration | prefilled from the image |
| `ChoicesFrom` (dropdown) | yes, updates when its inputs change | yes, from the previous run's values; text field the first time | yes, updates when its inputs change |
| `ClearAfterRun` | yes | not needed (a fresh dialog every run) | yes |
| `Replace` | updates the layer or dock in place | closes the previous window, overlay or ROIs | reuses the results window, replaces the annotation |
| `PickChannel` | RGB colours, channels of a TIFF file | a channel number | channel names |
| `ImageOut`, `LabelsOut` | layer | window | preview and "Open in QuPath" |
| `TableOut` | table dock | Results table | table in the results window |
| `Scalars` | in the status line | in the Log | in the results window and status |
| `MessageOut` | quoted block under the status | Log and a dialog | label under the status and in the results |
| `PointsOut` | points layer (scaled like its image) | point ROIs, ROI Manager, table | point annotation on the open image, else a table |
| `Affine` | overlay layer | overlay window | matrix shown |
| Progress, Cancel, kept worker, run details | yes | progress and Esc | yes |
| Macro / command recording | no | yes (macro recorder, replay) | no |

Not yet in any host (see the roadmap): shapes outputs, run on the selected region, tracks, slider and radio styles, time-lapse and 3D axes, figure output, Repeat, batch.

How this table is kept honest: each row has a test in the host's own suite that runs the example app (`labconstrictor_tools.examples.interactions`); a change that breaks a row fails that suite.
