# Host parity inventory

Status: analysis, read-only on code. Generated from a reading of merged code, not from running every host. Where a cell says
"predicted" the behaviour follows from the code but was not executed; where it says "not determined" it depends on a toolkit
(Qt, SciJava, JavaFX, ipywidgets, Appose) whose source is not in these repositories.

This page answers one question: **for every rule a person can notice, does each place that runs a LabConstrictor tool do the same thing?**
The places are the three hosts (Napari, Fiji, QuPath), the command line (CLI) and the notebook form (notebook). The reference is
this repository (`docs/PROTOCOL.md`, `docs/MANIFEST.md`, `docs/HOST_FEATURES.md` and the code of `labconstrictor_tools`).

## Summary

* **164 rows**: 41 `same`, 71 `DIVERGES`, 52 `intended`.
* Most `DIVERGES` rows are in QuPath (trust checks, hints, messages, support trail), a second group in Fiji (macro text, paths, results), a few in Napari (the 2D plane, region limit, notices) and in the notebook form (nullable parameters, notices, units).
* One defect is shared by all four places that quote a command: on Windows a path that contains a space and ends in a backslash comes out with an escaped closing quote (row N03).
* Section 2 proposes `labconstrictor_tools/conformance.json`; section 3 ranks the 15 divergences a person meets first; section 4 lists the 78 changes (70 of size S, 8 of size M, none L) that remove the divergences.

## Code that was read

| Part | Repository | Commit (origin/main) | Files |
|---|---|---|---|
| Reference | LabConstrictor-Tools | `86a840f` | `labconstrictor_tools/{types,convert,worker,client,cli,__main__,command,notebook,notebook_magic,testing,log,runs,registry,introspection,shapes,region}.py`, `docs/{MANIFEST,PROTOCOL,HOST_FEATURES,OPERATIONS}.md` |
| Napari | napari-labconstrictor | `d736804` | `napari_labconstrictor/{_widget,_results,_export,_schema,_units,_workers}.py`, `README.md`, `docs/HOST_FEATURES.md` |
| Fiji | LabConstrictor-Fiji | `116269d` | `src/main/resources/.../LabConstrictor_Tools.groovy`, `LabConstrictorCommand.java`, `LabConstrictorCopyCommand.java`, `README.md` |
| QuPath | labconstrictor-qupath | `54f1164` | `src/main/resources/.../qupath/LabConstrictorTools.groovy`, `LabConstrictorExtension.java`, `README.md` |

All host files were read with `git archive origin/main`, so working trees are irrelevant.

## How to read the tables

Cell citations: **T** `file:line` = this repository, `labconstrictor_tools/`; **N** = `napari_labconstrictor/` (`_widget.py:920`);
**F** `:line` = the Fiji Groovy script; **Q** `:line` = the QuPath Groovy script; **CLI** = `cli.py`; **NB** = `notebook.py`.
In quoted messages "X" stands for the cross sign and "after a warning sign" for the warning glyph that the host prints. "n/a" = the host has no such notion; "ignored" = the host shows a plain form (allowed by the manifest rule of thumb).

Status: `same` = a person would not notice a difference. `intended` = differs on purpose (host's object model, or written in
`HOST_FEATURES.md` or a host README). `DIVERGES` = a difference a person can notice that is not documented as intended. Every `DIVERGES`
row names which behaviour should be the reference and why, and the change that would align it (host and size: S under half a day,
M one to three days, L more).

The proposed alignment changes are collected in section 4 (they have short names such as `QP-3`).

## 1. The inventory

Columns: id, rule, reference, Napari, Fiji, QuPath, CLI, notebook, status, note.

### A. Types and how each is entered

| id | rule | reference | Napari | Fiji | QuPath | CLI | notebook | status | note |
|---|---|---|---|---|---|---|---|---|---|
| A01 | Image / Labels input from the host's own objects | path to a TIFF, or shared-memory array; worker reads it (T:convert.py:55-62, 121-135) | layer chooser, one per layer class: an Image parameter lists Image layers, a Labels parameter lists Labels layers (N _schema.py:80-81, _widget.py:922-925) | chooser of every open window, for both types (F:522) | combo: "Current image", every project image, "File..." (Q:845-886) | n/a, a path | n/a, a path typed in a text box (NB:67-72) | intended | native object models. Only Napari filters by layer class |
| A02 | Image / Labels from a file | any path text; TIFF always, others only if the app has imageio (T:convert.py:121-135) | "or file" row under the chooser, a chosen file wins (N _widget.py:372-391, 913) | "(or file)" field, a file wins; with no window open the file field is the only input (F:523-533, 731-732) | "File..." entry plus text field and browse button (Q:854-862, 881) | `image=path` (cli.py:103) | text box (NB:67) | same | |
| A03 | Table input | CSV path, worker reads it with pandas (T:convert.py:65-67) | file picker filtered to `*.csv` (N _schema.py:82-87, _widget.py:926) | file field, no filter (F:485-486, 796-798) | text field plus file chooser, no filter (Q:952-963) | `table=path` | text box, hint "path to a CSV file" (NB:67-72) | same | only Napari filters the file dialog. No host can pass an open Fiji Results table or QuPath table |
| A04 | File input | a `Path`, no existence check (T:convert.py:68-69) | file picker, filter `*` (N _schema.py:86) | file field (F:485, 796-798) | text field plus chooser (Q:952-963) | path text | text box | same | |
| A05 | Folder input | a `Path`; worker refuses a non-folder with `[folder_not_found] 'L': folder not found: P` (T:convert.py:70-74) | folder picker, no host check (N _schema.py:83-84; _widget.py:926-927) | directory field; host check, same text as the worker (F:487-488, 799-803) | directory chooser; host check is `exists()`: a regular file passes, a missing path says "file not found: P" (Q:952-963, 1288-1291) | worker check | worker check | DIVERGES | reference: the worker text, one source. Fix: QP-2b (QuPath S): `isDirectory()` and the folder template |
| A06 | Integer input, field with no declared Min/Max | worker accepts any integer; a host box needs finite limits | Qt int box, +-(2^31-1) (N _schema.py:12, 99-107) | Integer item, Java int range (F:496-500) | Spinner of int, +-1 000 000 000 (Q:58, 793-804) | any Python int (cli.py:88-89) | BoundedIntText +-10^9 (NB:21, 74-80) | DIVERGES | reference: +-(2^31-1), the largest value every toolkit's integer box holds. Fix: QP-2c (QuPath S), NB-1 (notebook S). A bound declared above 2^31-1 is cut by `lo as int` in QuPath (Q:797) and in Fiji `as Integer` (F:498) |
| A07 | Float input, field with no declared Min/Max | worker accepts any finite number | +-1e15 (N _schema.py:13, 100-102) | Double item, no limits (F:558) | +-1e12 (Q:59, 807-819) | any finite (cli.py:90-91) | +-1e9 (NB:22, 82-88) | DIVERGES | reference: +-1e15 (largest, keeps every realistic calibration or area). Fix: QP-2c (QuPath S), NB-1 (notebook S) |
| A08 | Float arrow step | cosmetic | 1e-4 when a unit is declared or the default is under 1, else 0.01 (N _schema.py:14-15, 103-107) | 1e-4 (F:54, 558) | (max-min)/100 if the range is bounded and at most 100, else 1 (Q:811) | n/a | 1e-4 (NB:23, 86) | intended | affects arrow keys only. QuPath arrow on an unbounded float moves by 1 |
| A09 | Boolean input | JSON `true`/`false` only; text and numbers refused (T:convert.py:86-90) | checkbox (N _schema.py:90-91) | checkbox (F:490-491) | checkbox (Q:757-762) | `1 0 true false yes no`, any case; else `name: expected true/false, got 'x'` (cli.py:94-97) | checkbox (NB:89-90) | same | |
| A10 | Boolean as text (macro line / command line) | n/a | n/a | macro: absent = default, bare flag = true, `true 1 yes` / `false 0 no` (F:1292-1297) | n/a | `name=` (empty) is refused (cli.py:94-97) | n/a | intended | the macro convention of ImageJ: a bare flag is true |
| A11 | String input | any text, kept as is (T:convert.py:98) | line edit (N _schema.py:88-89) | text field (F:543) | text field (Q:966-985) | text as typed | text box (NB:67-72) | same | |
| A12 | Choice input whose choices are numbers (Literal[1, 2, 3]) | worker needs same type and value: 2 is accepted, "2" and 2.0 are refused (T:convert.py:91-96) | combo with typed choices (N _schema.py:92-96) | String item: sends the text "2"; a macro `x=2` fails the `text in p.choices` test (F:493, 1325) | combo of text, getter returns `p.choices[i]`, but Gson reads JSON numbers as Double, so 2 goes out as 2.0 (Q:766-775, 128) | matches `str(c) == text` and sends the typed value (cli.py:98-102) | Dropdown, typed options (NB:91-96) | DIVERGES | predicted from code, not run. Reference: the typed value (CLI, Napari, notebook). Fix: FJ-5 (Fiji S: map the chosen text back to the declared choice), QP-2d (QuPath S: parse JSON integers as integers) |
| A13 | Choice as radio buttons, `Widget("radio")` | 2 to 5 options, never when nullable | RadioButtons (N _schema.py:94-95) | radioButtonHorizontal (F:494) | RadioButton row driving a hidden combo (Q:771, 778-790) | plain | plain | same | CLI and notebook show no radios (allowed) |
| A14 | Enum parameter reaches the tool as the member | worker restores the Enum (T:convert.py:39-52) | worker side | worker side | worker side | worker side | worker side | same | |
| A15 | Slider, `Widget("slider")` | needs Min and Max, not nullable | Slider / FloatSlider plus readout box (N _schema.py:108-116) | slider widget style (F:499, 559) | slider beside a spinner kept in step (Q:802, 817, 822-842) | plain | plain | same | same preconditions in the three hosts |

### B. Required, optional, nullable, defaults

| id | rule | reference | Napari | Fiji | QuPath | CLI | notebook | status | note |
|---|---|---|---|---|---|---|---|---|---|
| B01 | Required input left empty (image, table, file or folder) | `[missing_parameter] 'L' is required` (T:convert.py:30-32) | `'L' is required` after a warning sign, no code (N _widget.py:918-920) | image from dialog: `'L' is required: open an image or choose a file` (F:771); macro: `'L' is required: give name=<window title> or name_file=<path> (a macro never guesses the current image)` (F:1285); table/file in a macro: not set, worker answers (F:1315) | `'L' is required.` (Q:1148) | worker text inside the JSON (cli.py:181) | worker text, shown as `missing_parameter: 'L' is required` (NB:127) | DIVERGES | reference: the worker template `'{label}' is required`, a host may append a hint after it. Fix: NP-2 (Napari S), FJ-6 (Fiji S), QP-2e (QuPath S) |
| B02 | Required string left empty | empty text is a value and is sent (T:convert.py:30, 98) | `""` sent (N _widget.py:918) | `""` sent (F:1329) | `""` sent; the "is required" test never fires for strings because the getter returns text, not null (Q:967, 984, 1147-1150) | `name=` sends `""` | `""` sent (NB:107) | same | the dead branch in Q:1148 is harmless but misleading |
| B03 | Optional with a default | the default is sent when untouched | default shown (N _schema.py:66-68) | default shown (F:491, 493, 497, 543) | default shown (Q:761, 768, 796, 810, 968) | omitted: worker applies the default (T:convert.py:33) | shown (NB:71-97) | same | |
| B04 | Nullable scalar (optional, no default): can be left unset | omitted from the request; tool receives None; "showing 0 or an empty string instead is a bug" (PROTOCOL.md; T:convert.py:33) | "set" checkbox, greyed until ticked, omitted when unticked (N _widget.py:452-480, 915-917; _schema.py:61-65) | "Set <label>" box, omitted when unticked (F:478-480, 806); macro: absent = unset (F:1307-1310) | "set" box, getter returns null when unticked (Q:738-747) | name not given = unset (cli.py:155-162) | no "set" box: always sends 0, `""`, False or the first choice (NB:74-96, 102-110) | DIVERGES | reference: the protocol rule. Fix: NB-2 (notebook S: a "set" checkbox per nullable control, omit when off). Silent wrong value today |
| B05 | Nullable boolean | unset, true and false are three states | set box + checkbox (N _widget.py:458-464) | set box + checkbox (F:478) | set box + checkbox (Q:738) | omit, `true`, `false` | always sends False or True | DIVERGES | covered by B04 |
| B06 | Optional image / path | empty = omitted | None state of the widget (N _schema.py:59-60, _widget.py:918-921) | image: "Use <label>" box, default off (F:519-521); path: empty = omitted (F:797) | image: "(none)" item (Q:849); path: empty field = null (Q:962) | omit | empty text = omitted (NB:107-109) | same | |
| B07 | Required number with no default: starting value | not specified (schema has no default) | widget default (not determined) | 0, even when 0 is outside the bounds (F:497, 558) | 0 moved into [min, max] (Q:796, 810) | n/a | 0 moved into the bounds by the Bounded widget (NB:76, 83) | DIVERGES | reference: nearest allowed value to 0 (QuPath rule). Fix: FJ-7 (Fiji S). Napari not determined |
| B08 | Required choice with no default | schema fills in the first choice (T introspection.py:117) | first | first (F:493) | first (Q:768) | n/a | first (NB:93) | same | |
| B09 | JSON `null` for a given parameter | treated as not given (PROTOCOL.md; T:convert.py:29-34) | never sent | never sent | never sent | never sent | never sent | same | |
| B10 | Order of the parameters in the form | parameters of one group together at the group's first appearance; Advanced after all others (PROTOCOL.md "Group names are shown where they first appear"; MANIFEST) | `presentation_order` (N _schema.py:21-37) | `presentationOrder` (F:407-414) | not reordered: non-advanced rows in declared order with a heading whenever the group changes, folded groups appended after all normal rows, advanced last (Q:655-717) | declared order (cli.py:70-81) | declared order | DIVERGES | reference: Napari and Fiji. Fix: QP-5 (QuPath S): reuse the same ordering function |

### C. Hints

| id | rule | reference | Napari | Fiji | QuPath | CLI | notebook | status | note |
|---|---|---|---|---|---|---|---|---|---|
| C01 | Min / Max, value typed outside the range | "bounds, enforced everywhere" (MANIFEST.md); worker refuses with `[invalid_parameter] 'L' must be >= m` / `<= M` (T:convert.py:100-105) | Qt box limited to [min, max] (N _schema.py:101-102) | dialog: SciJava widget (not in the script, not determined); macro: refused (F:1270-1271) | JavaFX spinner with the limits (Q:793-819; clamping of typed text not verified) | refused by the worker, JSON error | Bounded*Text widget keeps the value inside (NB:74-88) | intended | GUIs cannot hold an out-of-range number, text paths refuse. Fix: TOOLS-3 (Tools S): say so in MANIFEST.md |
| C02 | Unit | label gets ` (unit)` | N _schema.py:58 | F:477 | Q:706 | not shown by `run --usage` (cli.py:65-82) | not shown (NB:60-66) | DIVERGES | reference: the three hosts. Fix: NB-1 (notebook S), TOOLS-4 (CLI S: show the unit in usage) |
| C03 | Description | tooltip / help text | tooltip on the field (N _schema.py:56-57) | item description (F:375) | tooltip on the label only (Q:708-713) | after the default in usage (cli.py:80) | `control.tooltip` (NB:99) | same | |
| C04 | Label | schema label | label (N _schema.py:58) | label; "Set"/"Use"/"selection" boxes use it lowercased (F:479, 514, 520) | label (Q:706) | the parameter name, not the label (cli.py:156) | label (NB:60-62) | intended | the CLI addresses parameters by name |
| C05 | Group heading | heading above the group | bold label (N _widget.py:573-578) | message item "- Group -" (F:469) | bold label (Q:701-704) | ignored | ignored | intended | flat form allowed for CLI and notebook |
| C06 | Advanced | listed last, behind a toggle where the host can | "Show advanced settings" checkbox, hidden by default (N _widget.py:561-571) | always visible under a heading "Advanced settings" (F:428); documented | folded TitledPane (Q:670-676) | ignored | ignored | intended | HOST_FEATURES.md |
| C07 | Collapsed group | accordion, starts folded | button heading, starts folded (N _widget.py:581-600) | plain heading, SciJava cannot fold (documented) | TitledPane, collapsed, placed after all normal rows (Q:663-668) | ignored | ignored | intended | position problem is B10 |
| C08 | EnabledWhen | a parameter applies when the controlling one is set (not None, not False, not `""`) or equals one of the listed values | greys out; "set" test `value is not None and not False and != ""`; `equals` uses Python equality (N _schema.py:40-44, _widget.py:743-766) | ignored (documented) | greys out, but listeners exist only for ComboBox and CheckBox drivers: a spinner or text driver never re-evaluates, ticking a "set" box never re-evaluates, and `""` counts as set; `equals` compares text so 1 equals "1" (Q:1004-1017) | ignored | ignored | DIVERGES | reference: Napari (it is the PROTOCOL wording). Fix: QP-4 (QuPath S): listen to every driver kind and to `checks[...]`, treat `""` as unset |
| C09 | ChoicesFrom | dropdown filled by another tool, text field when it cannot answer (PROTOCOL.md) | asks live; debounce 400 ms, retry 1500 ms while a run is busy, ask again 200 ms after a run (N _widget.py:55-57, 628-730) | asks with the values of the previous run kept in `<LC_HOME>/state/<app>.json`; text field the first time (F:562-659) | same three timings as Napari (Q:65-67, 533-623) | plain string | plain text box | intended | Fiji: documented. The three timing constants belong in the conformance file |
| C10 | ChoicesFrom: entry rules | blank entry for nullable or empty field; a value the field already holds stays selectable; stale answers dropped | N _widget.py:718-730, 703 | F:539-542 | Q:614-622, 604 | n/a | n/a | same | |
| C11 | ClearAfterRun | after a successful run the parameter returns to its default or unset | resets the "set" box, the value to its default (string: `""`), the dropdown (N _widget.py:1099-1116) | not needed, fresh dialog; only ChoicesFrom dependencies are remembered (F:588-598) | resets only text fields, "set" boxes and dropdowns; a number, yes/no or fixed choice keeps the old value (Q:626-633) | n/a | ignored, although the form keeps its values between runs | DIVERGES | reference: Napari. Fix: QP-3 (QuPath S), NB-3 (notebook S) |
| C12 | Replace: image or labels | a new run replaces the previous result of this output | updates the layer in place when type and ndim match (keeps contrast and view), else removes and re-adds (N _results.py:107-114) | closes the previous window, opens a new one (F:992-996) | the whole results window of the tool is reused if any output has Replace (Q:1539-1549); images are previews | n/a | n/a | intended | QuPath replaces per window, not per output: a tool with one Replace output and one plain output loses both |
| C13 | Replace: table | replace the previous table | dock swapped, keyed by app and name (N _results.py:153-168) | `ResultsTable.show(name)`: ImageJ reuses a window of the same title, with or without Replace (F:1108-1112) | same results window as C12 | n/a | n/a | DIVERGES | predicted from ImageJ behaviour. Without Replace, Napari adds a second dock, Fiji overwrites the first. Reference: MANIFEST (add unless Replace). Fix: FJ-8 (Fiji S: title `name [n]` unless Replace) |
| C14 | PickChannel: what can be chosen | the person chooses a channel; the tool gets that channel as a 2D array (types.py:198-202) | colours of an RGB layer; "Channel n" of a TIFF given as a file; multi-channel layers are single channels already (N _widget.py:415-441) | integer 1..1000, default = current channel; checked when the run starts (F:47, 417-422, 694-701) | channel names of the server, chooser hidden when one channel (Q:917-940) | n/a, file as is (types.py:201-202) | n/a, file as is | intended | HOST_FEATURES.md |
| C15 | PickChannel: which plane of Z and T | the tool gets a 2D array | Napari: layer: RGB colour only; file: all other axes kept, so a Z-stack comes out 3D (N _export.py:93, 109-110) | the plane on screen (F:697, 775) | plane z 0, t 0 (viewer z, t only if an area is chosen) (Q:160, 1340-1341, 1371-1374) | n/a | n/a | DIVERGES | reference: the plane the person sees, said in the log (Fiji). Fix: NP-1 (Napari M: use `viewer.dims.current_step`; file: first plane plus a note), QP-9 (QuPath S: viewer plane for the whole image too) |
| C16 | Axes("YX") given a stack or multi-channel image | `[wrong_dimensions] 'L' must be a 2D image (YX) but got 3D with shape (...)` (T:convert.py:109-117); "a host passes the image as it is" (types.py:200) | passes the array, worker refuses | sends the plane on screen and logs "needs a single 2D plane - using the current plane (i of n)" (F:777-781) | sends plane z 0, t 0 with every channel (Q:1374) | worker refuses | worker refuses | DIVERGES | reference: refuse (no silent choice of data). Fix: FJ-9 (Fiji S: drop the silent plane or gate it behind a documented hint; the durable fix is a PickPlane hint, TOOLS-5 M). Maintainers may prefer to promote Fiji's behaviour: either way write it in PROTOCOL |
| C17 | PixelSizeOf: prefill | prefilled with the pixel size of the named image in micrometres | follows the layer or the file header until the person edits the field (N _widget.py:773-789) | at dialog build and on every change of the image or file; overwrites a typed value (F:107-139, 551-557) | on image change: overwrites a typed value; a file is not read at all: `imageSources()[box.value]` is null for "File..." (Q:1019-1038) | n/a | n/a | DIVERGES | reference: Napari. Fix: QP-8 (QuPath S: read the file header through `ImageServers.buildServer`, keep edited values), FJ-10 (Fiji S) |
| C18 | PixelSizeOf: unit conversion to micrometres | micrometres per pixel | any length unit pint knows (N _units.py:138-158) | um, micron(s), micrometer/-metre, nm, mm, cm, m (and inch for files only) (F:78-80, 97) | what QuPath calibration reports in micrometres (`hasPixelSizeMicrons`) (Q:1033) | n/a | n/a | intended | different toolkits. Conformance vector: 0.325 um, 325 nm, 0.000325 mm all give 0.325 |
| C19 | PixelSizeOf: layer with a scale but no length unit | not specified | scale taken as micrometres, status line "calibration assumed to be in um (layer has no unit)" (N _units.py:138-172, _widget.py:806-809; HOST_FEATURES) | unit "pixel" or unknown: field left alone, a Log line when none (F:82-87, 556-557) | `hasPixelSizeMicrons` false: field left alone | n/a | n/a | intended | documented in napari HOST_FEATURES. Reference should state the rule: assume micrometres only with a visible note |
| C20 | PixelSizeOf: anisotropic pixels | one value; Y and X can differ | warns "pixel size differs: Y .. um, X .. um - the tool takes one value and gets X" (N _units.py:184-188) | silent, uses X (F:87) | silent, uses X (Q:1033) | n/a | n/a | DIVERGES | reference: Napari (a wrong calibration is silent otherwise). Fix: FJ-10 (Fiji S), QP-8 (QuPath S) |
| C21 | PixelSizeOf: TIFF header units | ImageJ unit text, else TIFF ResolutionUnit | inch and centimetre (N _units.py:193, 229-233) | inch only (F:97) | n/a (no file read, see C17) | n/a | n/a | DIVERGES | reference: Napari. Fix: FJ-10 (Fiji S: add `cm` = 10000 um) |
| C22 | RegionOf: where the region comes from | the current selection as labels 1..N, 0 outside, behind a "use the selection" box, off by default (types.py:132-137) | selected Shapes layer; its scale must equal the image's (N _export.py:23-76) | ROI Manager selection, else the ROI of the image (F:705-722) | selected annotations, points excluded; only for the image open in QuPath (Q:1237-1255) | n/a | n/a | intended | HOST_FEATURES.md |
| C23 | RegionOf: image given as a file | not specified | allowed, reads the TIFF shape (N _export.py:36-48) | refused: "the selection belongs to an open image, but a file was chosen for 'L': open the image, or untick the selection" (F:707-708) | refused: "choose 'Current image' for the image, or untick the selection" (Q:1241-1242) | n/a | n/a | DIVERGES | reference: refuse (a selection of a window cannot be mapped onto an unknown file). Fix: NP-3 (Napari S) |
| C24 | RegionOf: number of objects and label type | labels 1..N | no limit, int32 TIFF (N _export.py:71) | at most 65 535, "N objects are selected; at most 65535 are supported", 16-bit (F:48, 715-717) | at most 65 535 (Q:48, 1245), and 100 000 000 pixels of the image or area (Q:49, 1248-1249), 16-bit | n/a | n/a | DIVERGES | reference: 65 535 (the lowest limit every consumer can honour). Fix: NP-4 (Napari S: same check and message) |
| C25 | RegionOf: errors | clear sentence, never guess | nothing selected: "select a Shapes layer in the layer list, or untick 'use the selection'"; empty layer; "lie outside the image"; scale mismatch (N _export.py:29-33, 67-73) | "nothing is selected: draw a region on 'T' or select entries in the ROI Manager, or untick the selection"; "the selection lies outside the image" (F:714, 718) | "no annotation is selected: select one or more annotations, or untick the selection"; "cover no pixel" (Q:1244, 1251) | n/a | n/a | intended | same intent, host vocabulary; "outside the image" wording differs (N: "lie outside", F: "lies outside", Q: "cover no pixel") |
| C26 | Output hints Name, Axes, ApplyTo | name = layer / window / table name; ApplyTo = frame of the result | `app:name`; axes not used for display (N _results.py:88-89) | image `app:name`, table `name`, points table `app:name`, ROI `app:name` (F:991, 1109, 1035, 1027) | results section titled `name`, annotation `app:name` (Q:1594) | JSON | print | intended | tables are not prefixed with the app in Napari or Fiji, the Fiji points table is |
| C27 | Hint markers a host does not know | plain, working form (MANIFEST rule of thumb) | n/a | n/a | n/a | n/a | ignores every layout and behaviour hint | intended | HOST_FEATURES.md has no notebook or CLI column: TOOLS-6 (Tools S: add them) |

### D. Number parsing

| id | rule | reference | Napari | Fiji | QuPath | CLI | notebook | status | note |
|---|---|---|---|---|---|---|---|---|---|
| D01 | Typed text in a number box: decimal separator and grouping by locale | not specified | Qt box (locale of the widget, not determined) | SciJava spinner (not determined) | JavaFX Spinner; unparseable text keeps the old value and says "Check 'L': 'x' is not a number; v is used." (Q:988-1001) | `float()` is locale free: `0,5` refused (cli.py:90-93) | browser-side parsing (not determined) | DIVERGES | cannot be settled from the code. Needs a hand test on a German or French locale (HUMAN_TEST_PROTOCOL). Reference: dot only, with a clear message |
| D02 | Integer text grammar | digits with optional sign, nothing else | box rejects other keystrokes | macro: `[+-]?\d+`, ASCII, trimmed (F:1262-1263); dialog: SciJava box | box | `int(text)`: accepts `1_000`, ` 5 ` and non-ASCII digits (cli.py:88-93) | n/a | DIVERGES | reference: Fiji macro grammar (strict). Fix: TOOLS-7 (CLI S: strict regex before `int`) |
| D03 | Float text grammar | decimal number with optional exponent | box | macro: `Double.parseDouble` accepts `1.5f`, `2d`, hex floats and `NaN` (then refused as not finite) (F:1267-1268); dialog: SciJava box | box | `float(text)`: accepts `1_0`, `nan`, `inf`, `infinity` (then the worker refuses) (cli.py:90-91) | n/a | DIVERGES | reference: optional sign, digits with an optional fraction (or only a fraction), optional exponent; nothing else (the regex is in the conformance file). Fix: TOOLS-7 (CLI S), FJ-11 (Fiji S) |
| D04 | NaN and infinity | `[invalid_parameter] 'L' must be a finite number` (T:convert.py:82-84) | cannot be typed (not determined) | macro: `'L' must be a finite number, got 'x'` (F:1268) | JavaFX may parse `NaN`; Gson then refuses to write it: `host_error` `IllegalArgumentException: JSON forbids NaN` (predicted, Q:126, 1224-1227) | worker refusal | box rejects | DIVERGES | predicted for QuPath. Reference: the worker text. Fix: QP-2f (QuPath S: finite check before sending) |
| D05 | Huge integers | any Python int | clamped to +-(2^31-1) when unbounded | macro: `'L' is out of range: text` beyond Java int (F:1264) | clamped to +-1e9 when unbounded | accepted, worker range-checks | clamped +-1e9 | DIVERGES | see A06. Reference: accept anything the declared bounds allow in text paths; GUI limit +-(2^31-1) |
| D06 | Fractional text for an integer | refused: `'L' must be an integer` (T:convert.py:75-78; `2.0` is accepted because `int(2.0) == 2.0`) | box cannot | macro: `'L' must be a whole number, got 'x'` (F:1262) | box | `name: expected a integer, got 'x'` (cli.py:93) | box | same | outcome the same, wording differs: see I06 |

### E. Text handling

| id | rule | reference | Napari | Fiji | QuPath | CLI | notebook | status | note |
|---|---|---|---|---|---|---|---|---|---|
| E01 | Whitespace around a path typed in a text field | not specified | FileEdit, as typed | SciJava file field, as typed | trimmed (Q:881, 962) | as typed | emptiness is tested after `strip()` but the value is sent untrimmed (NB:107-109) | DIVERGES | reference: trim (a trailing space is almost always a paste accident). Fix: NB-4 (notebook S), others use pickers |
| E02 | Unicode in text values | UTF-8 both ways; workers run with PYTHONIOENCODING=utf-8 (client.py `_worker_env`) | JSON UTF-8; test with "opt 00001 e-acute CJK" options (napari tests/test_adversarial_hints.py) | env set (F:818); typed unicode untested | UTF-8 explicit (Q:261, 265, 340); 5000 unicode options tested (README) | UTF-8 | in process | same | Fiji typed-text case not covered by a test: add a vector |
| E03 | Newline, tab or other control characters inside a string value in Copy as command | Python snippet uses `repr`, so `\n` is escaped (command.py:85) | uses `command.py` (N _widget.py:975-984) | own `pythonLiteral` escapes only backslash and quote: a newline breaks the pasted literal (F:1393-1397) | same defect (Q:1103-1107) | n/a | n/a | DIVERGES | reference: `repr`. Fix: FJ-1 (Fiji S), QP-6 (QuPath S): escape `\n \r \t` and non-printables, vectors in conformance |
| E04 | Message output rendering | plain text; `**bold**` and lists are fine (types.py:50) | Qt Markdown label under the status (N _widget.py:189-196) | `**` removed, `- ` becomes a bullet, Log plus dialog when a person runs it (F:1005-1008) | `**` removed, list markers kept, label under the status (Q:1488-1491) | JSON, raw | printed raw (NB:160) | DIVERGES | reference: Markdown subset bold + bullet lists. Fix: QP-7 (QuPath S: bullets), NB-5 (notebook S: render with `IPython.display.Markdown`). Napari alone renders links and other Markdown |
| E05 | Empty or whitespace-only message | worker refuses: `[bad_return] the message output 'N' is empty` (T:convert.py:206-209) | worker | worker | worker | worker | worker | same | |
| E06 | Very long message | not specified | scroll box, 110-320 px high (N _widget.py:59-60, 255-271) | dialog (grows) | wrapped label, width 560 (Q:76, 461-463), no scroll | JSON | print | intended | adversarial tests exist for Napari and QuPath |

### F. Files and folders

| id | rule | reference | Napari | Fiji | QuPath | CLI | notebook | status | note |
|---|---|---|---|---|---|---|---|---|---|
| F01 | Image file that does not exist | `[file_not_found] image file not found: P` (T:convert.py:124-126) | `'L': file not found: P` after a warning sign, host check (N _widget.py:930-932) | `'L': file not found: P` dialog (F:750) | `FileNotFoundException`: the status reads `failed: FileNotFoundException: file not found: P`, code `host_error` (Q:1387-1391, 1224-1227) | worker text in JSON | worker text | DIVERGES | reference: the worker template with code. Fix: NP-2 (Napari S), FJ-6 (Fiji S), QP-2 (QuPath S) |
| F02 | Table or file that does not exist | file: no check (T:convert.py:68-69); table: pandas raises, shown as `[FileNotFoundError] [Errno 2] No such file or directory: 'x.csv'` (T:convert.py:65-67, worker.py:213-228) | no check, worker answers | no check, worker answers | host check for file, table and folder: `file not found: P` (Q:1288-1291) | worker | worker | DIVERGES | reference: a worker code. Fix: TOOLS-8 (Tools S: table -> `[file_not_found] table file not found: P`), QP-2 (QuPath S: drop or use the same text) |
| F03 | Spaces in paths | paths travel as JSON strings, no shell | works | works | works | works | works | same | only Copy as command quotes (section N) |
| F04 | Unicode in paths | JSON UTF-8 | tifffile, pathlib | IJ FileSaver on a unicode temp path: Windows not verified | ImageWriterTools: not verified on Windows | works | works | same | not verified on Windows in any host (HUMAN_TEST_PROTOCOL) |
| F05 | Relative paths | resolved against the worker's working directory | a relative path typed in the picker resolves against Napari's directory, which is also the worker's (client.py `_spawn`) | host checks the path against Fiji's directory, then sends it as typed; the worker's directory is the app prefix (F:750, 765, 797, 819), so a relative path resolves somewhere else | sent absolute (Q:1291, 1367) | relative to the shell directory, the worker inherits it | relative to the kernel directory | DIVERGES | predicted from code, not run. Reference: absolute path sent to the worker. Fix: FJ-2 (Fiji S: `.absolutePath`) |
| F06 | `FileOut` result: does the file exist | host looks before listing it | `FileNotFoundError("the tool reported the file P but it does not exist")` shown as `(could not display file: ...)` (N _results.py:256-260) | `could not show the result 'N': the tool reported the file P but it does not exist` (F:970-971) | no check; "name (file)" and the path (Q:1503-1504) | JSON path, no check | prints the path (NB:176) | DIVERGES | reference: Napari / Fiji check. Fix: QP-2 (QuPath S) |
| F07 | File dialogs | n/a | Qt dialogs (modal) | SciJava file widgets | JavaFX FileChooser / DirectoryChooser | n/a | n/a | intended | |

### G. Image export to the tool

| id | rule | reference | Napari | Fiji | QuPath | CLI | notebook | status | note |
|---|---|---|---|---|---|---|---|---|---|
| G01 | dtype of an exported image | worker reads any TIFF the tifffile reader reads | raw numpy dtype: float64, int64, bool are written as they are (N _export.py:108-111) | ImageJ types only: 8, 16, 32-bit and RGB (F:782) | the server's pixel type (Q:1374) | file as it is | file as it is | intended | outputs are narrowed by `portable_dtype` (T:convert.py:385-428): uint8 uint16 int16 float32 |
| G02 | Channels and axes of an exported image | tool declares Axes | the whole array (channels are separate layers; an RGB layer is HxWx3) (N _export.py:108-111) | stack saved with ImageJ metadata, RGB as RGB (F:782) | all channels of the plane, RGB as RGB (README) | file | file | intended | axis order of a QuPath multi-channel export: not determined |
| G03 | Size limit of an export | a limit with a clear message, never a silent crop | 4 GiB of data: `layer 'L' is 5.0 GB; exporting more than 4 GB is not supported` (N _export.py:15, 102-107) | none | 100 000 000 pixels per plane: `'L': the image 'n' would be sent as W x H = P pixels (whole image), above the limit of B pixels per plane (system property lc.qupath.max_export_pixels). Choose 'Image area: Selected annotation(s)' ...` (Q:50-51, 1379-1385) | none | none | DIVERGES | reference: bytes (dtype-aware), 4 GiB, one named limit. Fix: QP-10 (QuPath M: convert the pixel budget to bytes with channels and pixel type, keep the property), FJ-12 (Fiji S: add the check) |
| G04 | Size limit of a displayed result | a limit with a message | refuses above 4 GiB uncompressed: `(could not display image: the image is X GB; showing more than 4 GB is not supported (it is in P))` (N _results.py:20-22, 99-103) | none | preview is downsampled to 560 px, no limit (Q:1666-1668) | n/a | first plane only (NB:176-190) | intended | |
| G05 | Export of a part of the image | not specified | RegionOf mask only | none | "Image area": whole image, bounding box of the selected annotations, current viewport; results move back by the offset (Q:891-914, 1563-1574) | n/a | n/a | intended | README of QuPath |
| G06 | Calibration inside the exported TIFF | calibration travels only as a PixelSizeOf parameter (F:786, N _widget.py:897 comments) | none written (`imwrite(data)`) | ImageJ TIFF keeps unit and pixel width (F:782) | writer default (not determined) | file | file | intended | a tool must not read resolution tags from its input: add to AUTHORING.md |
| G07 | Multiscale or pyramidal image | full resolution | level 0 (N _export.py:101) | n/a | downsample 1.0 (Q:52) | n/a | n/a | same | |
| G08 | Empty image | `[empty_image] 'L' contains no image data (shape (...))` (T:convert.py:59-62) | worker | worker | worker | worker | worker | same | |

### H. Results: what each host does with each result type

| id | rule | reference | Napari | Fiji | QuPath | CLI | notebook | status | note |
|---|---|---|---|---|---|---|---|---|---|
| H01 | `values`: where shown and how numbers are written | values `{k: v}`, NaN and infinity become null (PROTOCOL.md) | in the status line after `done in X s`, floats rounded to 4 decimals (N _results.py:250-254, _widget.py:1097) | Log line `<App> <name>: {k=v, ...}`, full precision (F:966) | status line plus a grid in the results window; a whole float is written without ".0" (Q:375-379, 1432-1433, 1509-1514) | JSON `results[].values` (cli.py:178) | `print(name, dict)` (NB:158) | intended | formatting is cosmetic. Round trip is the same |
| H02 | `values`: a null (not a finite number) | "a host must treat null in a numeric value as not a finite number" (PROTOCOL.md) | prints `None` | prints `null` | prints `(not a finite number)` (Q:378) | JSON null | `None` | DIVERGES | reference: QuPath wording (it follows the protocol sentence). Fix: NP-5 (Napari S), FJ-13 (Fiji S), NB-6 (notebook S) |
| H03 | `table`: where and how many rows | the whole CSV is the result | bottom dock, up to 100 000 rows, status `table 'n' (N rows, first M shown)` (N _results.py:23, 139-174) | Results window, all rows, no notice (F:1108-1112) | table in the results window, first 2 000 rows, `(first 2000 shown; the full table is in P)` (Q:54, 1694-1709) | JSON path | `display(pd.read_csv)`, pandas shortens the display (NB:154-156) | DIVERGES | reference: Napari (100 000, with a notice). Fix: QP-11 (QuPath S: 100 000 rows, a TableView is virtualized). Q also splits CSV by hand (no multi-line cells) (Q:1711-1725) |
| H04 | `points`: where | points layer / ROIs / annotation / table | points layer, size 8, yellow, other columns kept as properties, scaled like the image (N _results.py:179-201) | multi-point ROI on the image, entry in the ROI Manager, and a table; no image open: table plus a Log line (F:1013-1037) | one point annotation on the open image holding every point; only when the image was "Current image", else a table (Q:1577-1602); properties not attached | JSON path | `display(pd.read_csv)` (NB:165) | intended | HOST_FEATURES.md. No host caps the number of points (tests use 50 000 and 200 000) |
| H05 | `points`: image used when `apply_to` is absent | "the frame of the image named by apply_to, else of the first image" (PROTOCOL.md) | the first value in the inputs, of any type: if the first parameter is not an image the scale is (1, 1) (N _results.py:185-186) | last image shown by this run, else the current image (F:955, 1016) | the first image input (Q:1556-1561) | n/a | n/a | DIVERGES | reference: PROTOCOL (first image input). Fix: NP-6 (Napari S), FJ-14 (Fiji S) |
| H06 | `points`: pixel-centre convention | coordinates are pixel centres at integers | data (y, x) used as they are (N _results.py:183-186) | +0.5 (F:53, 1025) | +0.5 (Q:1591-1592) | n/a | n/a | same | conformance vector: (y=0, x=0) is the centre of the first pixel |
| H07 | `shapes`: polygons with holes | holes are part of the data | outer boundary only; `**N**: k outline(s) have holes; the layer draws only the outer boundary.` (N _results.py:242-246) | holes kept (composite ROI), Log line `'N': k outline(s) have holes (kept in the overlay and the ROI Manager)` (F:1103) | holes kept, text `k outline(s) have holes (kept).` (Q:1635) | JSON path | `name n outline(s): path` (NB:167) | intended | Napari polygons cannot have holes (documented) |
| H08 | `shapes`: cap and what is counted | hosts show up to 50 000 outlines and say how many were left out (shapes.py:20); `n` in the result = features (T:convert.py:358) | counts polygon parts; `**N**: showing the first 50000 of T outlines.` (N _results.py:26, 219-221, 238-241) | counts polygon parts; Log `'N': showing the first 50000 of T outlines` (F:49, 1059-1060, 1101) | counts features; `Showing the first 50000 of T.` (Q:47, 1625, 1634, 1646) | n/a | n/a | DIVERGES | reference: features (the author's objects), wording `showing the first {shown} of {total} outlines`. Fix: NP-7 (Napari S), FJ-15 (Fiji S), QP-12 (QuPath S: wording) |
| H09 | `shapes`: ROI Manager entries | n/a | n/a | the first 1 000 entries also go to the ROI Manager (F:50, 1100-1102) | n/a | n/a | n/a | intended | Fiji README |
| H10 | `shapes`: no matching image open | not specified | always a layer (scale from the first input) | Log line "no image is open to place them on" (F:1088-1092) | text "Not placed on an image (the outlines were not found in the image open in QuPath)." (Q:1615-1620) | n/a | n/a | intended | |
| H11 | `shapes`: properties and names | feature properties are kept, `label` links an outline to a label | all properties become layer properties (N _results.py:222-223) | only `label` goes into the ROI name `app:name label[.part]` (F:1063-1064) | `label` in the name `app:name label`, numeric properties become measurements (Q:1655-1658) | n/a | n/a | intended | |
| H12 | `image` / `labels` result | a layer or window | layer `app:name`; ndim-matching replace keeps the view; Labels become a Labels layer (N _results.py:91-114) | window `app:name`, ` [n]` when the title is taken; labels are an ordinary image window (F:988-1001) | preview of the first plane and channel, the path, an "Open in QuPath" button; the file stays in the results folder (Q:1517-1527, 1666-1689) | JSON path | gray matplotlib figure of the first plane (NB:176-190) | intended | |
| H13 | `affine`: guard against bad matrices | worker only checks the shape (T:convert.py:374-381) | applies whatever it gets | refuses non-finite and singular matrices: `the alignment matrix is singular (determinant d): it cannot be applied` (F:1151-1154) | prints it with 5 decimals; a null element is not handled (predicted, Q:1531-1536) | JSON | prints 4 decimals (NB:166-172) | DIVERGES | reference: finite required in the worker (`bad_return`), singular allowed with a warning. Fix: TOOLS-9 (Tools S), FJ-16 (Fiji S: warn, not refuse) |
| H14 | `affine`: how shown | overlay of the moved image on the target | overlay layer, magenta, additive, opacity 0.8, target calibration multiplied in (N _results.py:29, 116-137) | resampled overlay window, aligned structures white, cross-checked against the worker's own warp (F:1123-1144) | matrix only (documented) | JSON | matrix | intended | conformance vector: a known matrix maps a known point |
| H15 | Result type a host does not know | PROTOCOL: "a host that does not know `shapes` lists the file" | `(could not display T: 'T')` with the key error text (N _results.py:76-86) | `the tool returned a result of the type 'T', which this version of Fiji LabConstrictor cannot show` (F:974) | name, type and path or raw map (Q:1503-1504) | JSON | name and path (NB:176) | DIVERGES | reference: list the file plus one clear sentence (Fiji text). Fix: NP-8 (Napari S), QP-12 (QuPath S) |
| H16 | `message` result with several outputs | each message is shown | joined with a blank line under the status (N _widget.py:1085-1087) | one Log line and one dialog each (F:1004-1008) | joined with a blank line under the status (Q:1488-1491) | JSON | printed one after another | same | |
| H17 | Names of table windows | name of the output | dock `name` (N _results.py:167) | `name` (F:1109), points table `app:name` (F:1035) | section `name` | n/a | n/a | intended | see C26 |
| H18 | Result kept after the run | n/a | image data copied into the viewer, temp folder removed (N _widget.py:1080-1083) | images opened, temp folder removed (F:1485-1487) | files stay in `<LC_HOME>/results` (Q:1395-1402) | files stay in `<LC_HOME>/results` (cli.py:206-237) | temp folder `lcnb_*` stays for ever (NB:123) | intended | notebook leak: NB-7 (notebook S: use `LC_HOME/results` and the pruning of the CLI) |

### I. Errors: codes and wording

| id | rule | reference | Napari | Fiji | QuPath | CLI | notebook | status | note |
|---|---|---|---|---|---|---|---|---|---|
| I01 | Shape of a failure | `[code] message` as the error text, `code` separate (worker.py:182) | status `X <first line> - click Details... for the full report (log: P)` (N _widget.py:76-77) | error dialog: crash hint (if crashed), error, last 8 worker lines, run record, log path (F:913-920) | status `failed: <error>` (Q:1450) | JSON `{status, seconds, error, code, log}`, exit 1 (cli.py:172-184) | `X <b>code</b>: message` without brackets (NB:127) | intended | each UI has its own frame; notebook drops the brackets |
| I02 | `no_match` / `no_result` | a notice, not a failure (MANIFEST.md) | warning line, no dialog (N _widget.py:64, 83-84) | message dialog and status bar (F:1185-1189) | status `no result: m` and an information dialog (Q:1443-1448) | status FAILED, exit code 1 (cli.py:148) | shown as an error `X no_match: m` (NB:127) | DIVERGES | reference: notice. Fix: NB-8 (notebook S). The CLI exit code 1 is deliberate: scripts can test the code |
| I03 | A refusal made by the host before running (missing file, size guard, region, area) | a sentence the person can act on | warning sign plus the sentence (N _widget.py:829-831) | error dialog with the sentence (F:1478-1480) | status `failed: IllegalStateException: <sentence>`, code `host_error` (a code not in the Tools list) (Q:1224-1227, 1450) | n/a | n/a | DIVERGES | reference: the sentence alone (Napari, Fiji). Fix: QP-2 (QuPath S: no class name, keep `host_error` internal) |
| I04 | A worker that dies: hint wording | `hint_for_exit`: missing package / killed (OOM) / segfault / import failed (log.py:127-138) | Tools text (N via client) | `The worker was killed (out of memory? the OS OOM killer ends big image jobs this way).` etc., capitalised (F:900-910) | `The worker was killed (out of memory? the OS ends big image jobs this way).` (shorter), no "package is missing" rule, exit code appended (Q:300-310) | Tools text | n/a | DIVERGES | reference: Tools wording. Fix: QP-13 (QuPath S: same sentences and ModuleNotFoundError rule) |
| I05 | A worker that dies: exit codes recognised | killed 137 / -9; segfault 139 / -11 / 3221225477 (log.py:132-135) | same | killed -9 137; segfault -11 139 3221225477; import failed 3 (F:65-67) | killed -9 137; segfault -11 139 -1073741819 (Q:304-306) | same | n/a | DIVERGES | Windows reports the access violation unsigned in Python and signed in Java. Fix: TOOLS-1 (conformance file lists both forms), QP-13, FJ-17 (Fiji S: add the signed form) |
| I06 | Invalid number: wording | `'L' must be an integer` / `'L' must be a finite number` / `'L' must be >= m` / `'L' must be <= M` / `'L' must be one of [...]` (the last uses the name, not the label) (T:convert.py:77, 84, 96, 103, 105) | box prevents it | macro: `'L' must be a whole number, got 'x'`, `must be a number, got 'x'`, `must be a finite number, got 'x'`, `must be >= m, got x`, `must be one of [...], got 'x'` (F:1262-1271, 1325) | `Check 'L': 'x' is not a number; v is used.` (Q:999) | `name: expected a integer, got 'x'` (cli.py:93) | worker text | DIVERGES | reference: worker templates; hosts append `, got 'x'` only after the template. Fix: TOOLS-1 (templates in conformance), FJ-18 (Fiji S), TOOLS-7 (CLI S: "an integer") |
| I07 | Unknown app or tool | names the valid choices | chooser | macro: `unknown tool 'x' in A (tools: label, label)` lists labels (F:1349-1352) | chooser | `no such tool 'x'; available: id, id` lists ids (cli.py:62); `unknown app 'x'; installed: ...` (cli.py:114); worker `[unknown_tool] only declared tools may be executed; got 'lc:x'` (worker.py:167-170) | n/a | intended | a macro and a command line are addressed by different names (label vs id): both accept both (F:1351, cli.py:60) |
| I08 | Unsupported parameter type in a schema | refuse clearly | refuses that tool: `this tool cannot be shown: parameter 'x' has the unknown type 't'` (N _widget.py:328-333, _schema.py:97-98) | skips the whole app: `tool 't': parameter 'x' has the unsupported type T` (F:310) | shows a plain text box (Q:734 default branch) | n/a | `unsupported parameter type` raised (NB:98) | DIVERGES | reference: Napari (that tool only). Fix: FJ-19 (Fiji S: skip the tool, not the app), QP-14 (QuPath S) |
| I09 | Unsupported schema protocol | `schema protocol 2 is not supported (this host speaks [1])` (registry.py:320-323) | via Tools | `schema protocol 2 is not supported` (F:302) | `unsupported protocol 2.0` (Q:235) | via Tools | n/a | DIVERGES | wording only. Fix: QP-14 (QuPath S), conformance message template |
| I10 | App skipped: interpreter missing | `not available on this machine (interpreter P is missing)` (registry.py, F:332) | via Tools | same text (F:332) | `interpreter not found: P` (Q:224) | via Tools | n/a | DIVERGES | wording only. Fix: QP-14 |
| I11 | Channel that does not exist | clear sentence | `'L': channel 4 was asked for, but the file has 3` (N _export.py:89-92) | `'L': channel 4 was asked for, but the image has 3 channels` (F:696) | n/a (list of valid names) | n/a | n/a | DIVERGES | wording only (file vs image, plural). Fix: NP-2 (Napari S), conformance template |
| I12 | ChoicesFrom could not be answered | text field stays, person told why | `X <problem>: type the value` in status and tooltip (N _widget.py:709-716) | Log `LabConstrictor: could not get the choices of 'L' (e); type the value instead` (F:644) | status `The choices for 'p' could not be loaded (type the value): why`, first time only (Q:609-611) | n/a | n/a | intended | same intent three wordings |
| I13 | Copy to the clipboard impossible | say so, never pretend | status `X there is no clipboard to copy to` (N _widget.py:992-997) | prints the command to the Log with the reason (F:1447-1450) | no handling: the exception escapes the button handler (Q:1132-1134) | n/a | n/a | DIVERGES | reference: Napari / Fiji. Fix: QP-15 (QuPath S) |

### J. Status, progress, cancel, timings

| id | rule | reference | Napari | Fiji | QuPath | CLI | notebook | status | note |
|---|---|---|---|---|---|---|---|---|---|
| J01 | Progress display | `progress(fraction, text)`; `None` = indeterminate | bar 0-100, indeterminate with no fraction, text in the status, first text "starting worker..." (N _widget.py:1016, 1036-1042) | status bar text, progress bar only when the maximum is above 0 (F:826-832) | bar with the fraction or indeterminate, first text "starting..." (Q:1175, 1218-1223) | stderr `[ 42%] text`, `[ ?%] text` (cli.py:240-244) | `FloatProgress` set only when a fraction is given (NB:143-147) | same | |
| J02 | How to cancel | cooperative `check_cancel()`, then kill | Cancel button | Esc key (F:842) | Cancel button | Ctrl-C: the worker is closed, `interrupted; the worker was asked to stop`, exit 130 (cli.py:136-138) | none: `cancelled=lambda: False` (NB:118) | intended | |
| J03 | Time a tool gets to honour Cancel before its worker is killed | not in PROTOCOL; `Task.cancel` default 10 s (client.py:29, 446) | 3 s (N _widget.py:53, 1034) | 3 s (F:34, 847) | 3 s (Q:63, 345-352) | no cancel request: stdin is closed, 5 s then kill (client.py:31, 214-229); the worker would allow 10 s (worker.py:32) | n/a | intended | the three hosts agree, the library default differs. Both numbers go in the conformance file |
| J04 | Run timeout | `--timeout` kills the worker, `timed out after X s`, CRASHED (client.py `run_once`) | none | none | none | `--timeout` (__main__.py:96) | none | intended | |
| J05 | A second run while one is running | refused | ignored, button disabled (N _widget.py:814-817, 1024) | modal dialog | ignored, Run disabled (Q:1159, 1171) | n/a | button disabled (NB:117) | same | |
| J06 | Cancel with nothing running | ignored | ignored (N _widget.py:1027-1028) | n/a | ignored (Q:346-347) | n/a | n/a | same | |
| J07 | Status after Cancel when the tool stopped by itself | `cancelled` | `cancelled` (N _widget.py:62, 89) | status bar `LabConstrictor: canceled`, Log "the run was cancelled" (F:1194-1195) | `cancelled` (Q:1419) | n/a | n/a | same | |
| J08 | Status after Cancel when the worker had to be killed | the person asked for it: say "cancelled" | `cancelled (worker stopped)` (N _widget.py:85-86) | status bar `LabConstrictor: crashed`, Log "the run was cancelled"; the sentence "The tool did not stop when Cancel was pressed, so its worker was stopped." exists (F:901) but only the error dialog uses it, and that branch is skipped after Cancel (F:1190-1195) | `the worker stopped: The worker was killed (out of memory? ...) (exit code 137)`: reads as an out-of-memory crash (Q:1420-1422) | n/a | n/a | DIVERGES | reference: Napari (the person asked for the stop; never an out-of-memory text). Fix: QP-16 (QuPath S: remember that Cancel was sent). Fiji's status bar word `crashed` is a smaller instance: FJ-20 (Fiji S) |
| J09 | Time shown for a finished run | n/a | `done in 1.2s` (N _widget.py:1097) | none | `done in 1.2s` (Q:1433) | `seconds` in the JSON (cli.py:174) | none | intended | |

### K. Worker lifecycle

| id | rule | reference | Napari | Fiji | QuPath | CLI | notebook | status | note |
|---|---|---|---|---|---|---|---|---|---|
| K01 | Is a worker kept between runs | not specified | one per app, kept; the box "Keep the worker running between runs" is on by default (N _widget.py:200-201, _workers.py:261-314) | a fresh worker for every run, closed afterwards (F:866-889) | one for the whole window, replaced when the app changes; same box, on by default (Q:393, 443, 1188-1194) | a fresh worker per run (client.py `run_once`) | none: the tool runs in the kernel | intended | Fiji README: "not yet" |
| K02 | Idle timeout of a kept worker | OPERATIONS.md: "Napari keeps the worker for 10 minutes" | 600 s, checked every 30 s, so the worker goes 600-630 s after its last use (N _workers.py:257, _widget.py:54, 279-281) | n/a | none: it stays until the window closes or Restart is pressed | n/a | n/a | DIVERGES | reference: Napari (a torch worker holds gigabytes). Fix: QP-17 (QuPath S: a 600 s idle timer) |
| K03 | How long a worker gets to exit after its input is closed | PROTOCOL.md: "exits within 10 s" (worker.py:32) | 2 s, then killed (N _workers.py:258) | 15 s, then killed (F:35, 892-896) | 10 s, then killed (Q:64, 366) | 5 s, then killed (client.py:31) | n/a | DIVERGES | reference: 10 s (the worker's own promise; killing earlier can cut its clean-up). Fix: NP-9 (Napari S), TOOLS-10 (client S). Fiji's 15 s is for torch and numba (comment F:35): keep, or measure |
| K04 | "Restart worker" | stop the kept worker | button, disabled while running (N _widget.py:277, 1022) | n/a | button: kills at once (Q:483-484) | n/a | n/a | same | |
| K05 | Stop on exit | no worker left behind | `atexit`, widget destruction and `closeEvent` (kills a running one and removes its folder) (N _workers.py:270, _widget.py:284, 1152-1166) | closed in `finally` after each run (F:880-882) | `stage.onHidden` closes it in the background (Q:436); closing QuPath with the window open relies on the worker's own orphan rule | context manager, Ctrl-C (cli.py:136) | n/a | same | |
| K06 | Orphan: host disappears | stdin closed: running tool asked to cancel, worker exits after 10 s, removing its temporary folders (worker.py:97-104, 141-145) | worker rule | worker rule | worker rule | worker rule | n/a | same | |
| K07 | Killing a worker also kills what the tool started | process group (POSIX), `taskkill /T` (Windows) (client.py:231-290) | via client | `service.kill()`; descendants not determined | `descendants()` then the process (Q:356-360) | via client | n/a | intended | Fiji not determined: Appose's behaviour |
| K08 | A worker after Cancel or a crash is not reused | never reuse a worker that may be mid-task | only COMPLETE or FAILED workers are kept (N _widget.py:1053-1057) | n/a | after CANCELATION the worker is kept; after a crash it is killed (Q:1418-1423) | n/a | n/a | intended | the honoured cancel leaves a clean worker |
| K09 | Environment of the worker | scrubs PYTHONHOME, VIRTUAL_ENV, CONDA_PREFIX, QT_PLUGIN_PATH, PYTHONPATH; sets PYTHONPATH, PYTHONNOUSERSITE=1, PYTHONSAFEPATH=1, PYTHONIOENCODING=utf-8, PYTHONUNBUFFERED=1; keeps the host's working directory (client.py `_worker_env`) | via client | sets PYTHONPATH, NOUSERSITE, IOENCODING, UNBUFFERED only; does not scrub, no SAFEPATH; working directory = app prefix (F:818-819) | scrubs the same list and sets all five (Q:198, 260-261) | via client | n/a | DIVERGES | reference: client. Fix: FJ-3 (Fiji M: Appose's `Service` takes extra variables only, so the removal needs a wrapper or a patch) |

### L. Results folders, run records

| id | rule | reference | Napari | Fiji | QuPath | CLI | notebook | status | note |
|---|---|---|---|---|---|---|---|---|---|
| L01 | Where results go | CLI: `<LC_HOME>/results/<YYYYMMDDTHHMMSS>_<6 hex>_<app>_<tool>`, names made of `A-Za-z0-9_.-` (cli.py:197-237) | temp folder `lcin_*`, removed after the run (N _widget.py:818, 841-843, 1080-1083) | temp folder `lcjob_fiji_*`, removed after the run (F:1473, 1485-1487) | same folder as the CLI, name `<ts>_<6 digits>_<app>_<tool>` with the app and tool text as they are (Q:1395-1402) | as reference | `lcnb_*` in the temp area, never removed (NB:123) | DIVERGES | reference: CLI naming (slug). Napari and Fiji removal is documented (OPERATIONS.md). Fix: QP-18 (QuPath S: slug and 6-hex), NB-7 (notebook S) |
| L02 | Pruning | keeps the newest 20; only folders whose name matches `^\d{8}T\d{6}_`, never symlinks (cli.py:187, 197, 206-221) | n/a | n/a | keeps 20 but removes every folder in `results/` beyond the newest 20 by name, whatever it is (Q:1400) | as reference | none | DIVERGES | reference: CLI (it never touches a folder it did not create). Fix: QP-18 |
| L03 | Run record | `<LC_HOME>/runs/<time>_<app>_<tool>/run.json`, newest 50 kept (runs.py:18) | written for every run (N _widget.py:1126) | own writer, same folder and count, `host: "fiji"`, millisecond stamp, prunes every sub-folder of `runs/` (F:46, 923-941) | none (the Details window shows the outcome) | written unless `--no-record` (cli.py:132) | none | DIVERGES | reference: `runs.record`. Fix: QP-19 (QuPath M), FJ-4 (Fiji S: prune only its own pattern) |
| L04 | State files | n/a | none | `<LC_HOME>/state/<app>.json` (ChoicesFrom values) and `last_command.json` (F:571, 1438, 1461) | none | none | none | intended | |

### M. Logging

| id | rule | reference | Napari | Fiji | QuPath | CLI | notebook | status | note |
|---|---|---|---|---|---|---|---|---|---|
| M01 | Where the log goes | one file for every front-end: `<LC_HOME>/logs/labconstrictor.log` (log.py:17-34; OPERATIONS.md) | that file (N via `log`) | that file, own writer (F:157-177) | QuPath's own log through an SLF4J logger named `labconstrictor`, not the shared file (Q:95) | that file | stdlib logger `labconstrictor.notebook` (NB:129-131); the handler of the shared file exists only after `log.logger()` ran: probably stderr (not determined) | DIVERGES | reference: the shared file, so that `labconstrictor-tools logs` and `support-bundle` see QuPath. Fix: QP-20 (QuPath M: append lines in the same format), NB-9 (notebook S: call `log.logger()`) |
| M02 | Rotation | 1 000 000 bytes, 5 backups (log.py:18-19) | via Tools | above 1 000 000 bytes the file is renamed to `.log.1`: one backup; `renameTo` does not replace an existing file on Windows, so rotation can fail and the file grow (F:40, 167) | n/a | via Tools | n/a | DIVERGES | reference: Tools. Fix: FJ-4 (Fiji S: five numbered backups, `Files.move` with REPLACE_EXISTING) |
| M03 | Line format | `%(asctime)s.%(msecs)03d %(levelname)-7s pid=%(process)d %(message)s` (log.py:24) | via Tools | `yyyy-MM-dd HH:mm:ss.SSS LEVEL pid=N fiji: text`; level names `WARN` and `WARNING` both occur (F:102, 168-169, 279) | n/a | via Tools | n/a | DIVERGES | cosmetic. Reference: Tools levels (`WARNING`). Fix: FJ-4 |
| M04 | Concurrent writers | no lock (OPERATIONS.md) | same | same | n/a | same | n/a | intended | documented |

### N. Copy as command

| id | rule | reference | Napari | Fiji | QuPath | CLI | notebook | status | note |
|---|---|---|---|---|---|---|---|---|---|
| N01 | Terminal line | `<python> -m labconstrictor_tools run <App> <tool id> name=value ...`, unset parameters left out, booleans `true`/`false` (command.py:66-79) | calls `command.command_line` with the app's interpreter (N _widget.py:984) | own copy (F:1407-1415) | own copy (Q:1117-1126) | n/a | none | same | the three read the same schema; conformance vectors keep the copies honest |
| N02 | POSIX quoting | `shlex.quote` (command.py:40) | via command.py | regex safe set `[A-Za-z0-9_@%+=:,./-]`, else single quotes with `'"'"'` (F:1373) | same (Q:1048) | `command.quote` (cli.py:26) | n/a | same | the ASCII safe sets are the same as shlex's |
| N03 | Windows quoting | safe: letters, digits (Unicode `isalnum`) and `-_.:/\=+,`, else double quotes with `\"` (command.py:37-39) | via command.py | ASCII only safe set (F:1372) | ASCII only (Q:1047) | via command.py | n/a | DIVERGES | cosmetic: a name with a non-ASCII letter is quoted by the hosts, not by command.py. Reference: ASCII only (hosts, safer). Fix: TOOLS-2 (Tools S). Shared defect in all four: a path ending in a backslash and containing a space becomes `"C:\my dir\"`, whose last quote is escaped; add a vector and fix |
| N04 | Python snippet literals | `repr` (command.py:85, 93) | via command.py | `pythonLiteral`: True/False, numbers as `toString`, text in single quotes escaping only `\` and `'` (F:1393-1397) | same (Q:1103-1107) | n/a | n/a | DIVERGES | see E03. Also cosmetic: `repr` picks double quotes for text holding a single quote, the hosts always write `'it\'s'` |
| N05 | Number text | `str(value)`: `1e-05`, `0.325` | via command.py | `Double.toString`: `1.0E-5` | same | n/a | n/a | same | both parse back to the same number: "run for real gives the same values as the form" is the rule (tests/test_command.py) |
| N06 | Placeholders and the first note | `image.tif`, `labels.tif`, `table.csv`, `file`, `folder`; first line `# replace the file for: a, b` (command.py:15-22, 57-63, 76-79) | via command.py | same (F:1368, 1387, 1420) | same (Q:1043, 1062, 1096) | n/a | n/a | same | |
| N07 | Notes for what a command cannot say | not specified | selection: `# n: the selection cannot be copied; save it as a label image and put its path here`, put before the placeholder line (N _widget.py:985-990); no note for a chosen channel | selection: copies the path of the temporary mask, which is deleted after the run, without a note (F:727-729, 1383-1385); no note for a channel | selection note (same sentence, after the placeholder line), channel note, Image-area note, unreadable-value note (Q:1070-1089, 1096) | n/a | n/a | DIVERGES | reference: QuPath (every lost modifier is named). Fix: NP-10 (Napari S: channel note, same order), FJ-21 (Fiji S: `region.tif` placeholder and notes); sentences go to the conformance file |
| N08 | What is copied | the values of the form | the current form, before running (N _widget.py:938-971) | the values of the last run: printed to the Log after every run and by the menu entry "Copy last run as command" (F:1436-1468) | the current form (Q:1051-1065) | n/a | n/a | intended | HOST_FEATURES.md |
| N09 | File behind an image | the path of the source file, else a placeholder | the layer's `source.path` (N _widget.py:965-966) | the file of the window (original file info) (F:1383) | the file URI of the server (Q:1077) | n/a | n/a | same | |
| N10 | `=` inside a value | split at the first `=` | n/a | n/a | n/a | `name=a=b` is `a=b` (cli.py:156) | n/a | same | |

### O. Security: trust checks of registry entries

| id | rule | reference | Napari | Fiji | QuPath | CLI | notebook | status | note |
|---|---|---|---|---|---|---|---|---|---|
| O01 | Entry is a JSON object with the five text fields, `pythonpath` a list of text, `runtime_path` text | `_validated_entry` (registry.py:299-312) | via Tools | `entryProblem` (F:288-297) | none: fields are cast and a missing one fails with a null-pointer text (Q:222-241) | via Tools | n/a | DIVERGES | reference: Tools. Fix: QP-1 (QuPath M: one change for O01-O06, port the Fiji functions) |
| O02 | Interpreter inside the install prefix; prefix not a filesystem root | registry.py:262-273 | via Tools | F:252-256 | inside check only, lexical; no root check (Q:226-228) | via Tools | n/a | DIVERGES | QP-1 |
| O03 | Entry and schema files: owned by the user (shared folders: user or root), not group- or world-writable | `_file_reason` (registry.py:240-251; POSIX only) | via Tools | `fileReason` (F:236-246, 263-271) | only "writable by group or others" on the entry file; no owner check; the schema file is not checked (Q:229-233) | via Tools | n/a | DIVERGES | QP-1 |
| O04 | Interpreter, its folder and the prefix not writable by everybody (sticky folders excepted) | registry.py:254-257, 290-295 | via Tools | F:227-233, 273-276 | none | via Tools | n/a | DIVERGES | QP-1 |
| O05 | Schema file in the same folder as the entry | registry.py:280-283 | via Tools | F:265-267 | none | via Tools | n/a | DIVERGES | QP-1 |
| O06 | Names that become file names or item names (app, tool id, parameter name) | app name must be plain at registration (registry.py:81) | via Tools | app name plain, tool id `[A-Za-z0-9_][A-Za-z0-9_.-]*`, parameter name an identifier (F:201-209, 292, 305-310) | none: a parameter name is used in `new File(tmp, name + ".tif")` (Q:1252, 1373) and an app or tool name in the results path (Q:1398), so a hostile schema can write outside the temporary folder | via Tools | n/a | DIVERGES | reference: Fiji (stricter than Tools: TOOLS-11 moves the same checks into `_validated_schema`). Fix: QP-1 |
| O07 | Search order and priority | `$LC_HOME/apps`, `$LC_APPS_PATH`, system folder; the first wins (registry.py) | via Tools | F:191-198, 321-331 | Q:201-221 | via Tools | n/a | same | |
| O08 | Windows | the POSIX checks are skipped, the others stay (registry.py:242, 274) | same | F:215, 257 | POSIX attribute view only (Q:229) | same | n/a | same | documented |
| O09 | Skipped apps are reported, once per session in the log | registry.py:380-386 | status line `skipped: ...` (N _widget.py:302-303) | Log and `lcLog` (F:348) | status text and a log line each time the registry is read (Q:238, 507) | doctor, log | n/a | same | |
| O10 | The worker never runs host-supplied code | only `lc:<id>` of declared tools (worker.py:165-170) | same | same | same | same | n/a | same | |

### P. Settings, system properties, defaults that change results

| id | rule | reference | Napari | Fiji | QuPath | CLI | notebook | status | note |
|---|---|---|---|---|---|---|---|---|---|
| P01 | Environment variables and system properties | `LC_HOME`, `LC_APPS_PATH`, `ProgramData` | via Tools | same (F:158, 193-196); `LC_FIJI_HARNESS` (tests, F:153); system property `lc.macro.options` between the menu command and the script (LabConstrictorCommand.java:33) | same (Q:202-209); `lc.qupath.max_export_pixels` (Q:51); `lc.noshow`, `lc.qupath.test.script` (tests) | options `--out --no-record --timeout --keep` (__main__.py:89-96) | none | intended | Napari has no setting at all; the limits are constants. A uniform "settings" story does not exist |
| P02 | Form values kept between runs | n/a | kept while the same tool stays selected; rebuilt (and lost) when the tool changes or on Rescan (N _widget.py:318-359) | none: fresh dialog, `setPersisted(false)`; only ChoicesFrom dependencies are remembered (F:377, 588-598) | kept while the same tool stays selected (Q:518-529) | n/a | kept | intended | |
| P03 | Which image a parameter starts on | not specified | magicgui default (not determined) | the i-th image parameter starts on the i-th open window, the last one repeating (F:443-451) | the first source for a required image, "(none)" for an optional one (Q:864) | n/a | empty | intended | |
| P04 | Name of a new layer or window when the name is taken | not specified | Napari's own numbering | ` [n]` (F:996) | a new window each run | n/a | n/a | intended | |
| P05 | Two tools with the same label | never pick the wrong one | the chooser shows `label (id)` (N _widget.py:67-73) | the second tool cannot be chosen: the first label match wins (F:679) | same (Q:520) | label or id, first match (cli.py:58-62) | n/a | DIVERGES | reference: Napari. Fix: FJ-22 (Fiji S), QP-21 (QuPath S) |
| P06 | Order of the app list, and the app shown first | not specified | sorted by name (N _widget.py:300) | discovery order: folder priority, then file name (F:321-325, 674) | discovery order (Q:215-241, 438) | sorted (cli.py:48) | n/a | DIVERGES | cosmetic. Reference: sorted. Fix: FJ-22, QP-21 |
| P07 | The tool's description | shown above the form | label (N _widget.py:325) | not shown anywhere (F:459-473) | label (Q:524) | first line of `run --usage` (cli.py:67) | bold title and italic description (NB:49-51) | DIVERGES | Fix: FJ-22 (Fiji S: put it into the dialog's message item) |
| P08 | Keyboard | n/a | none | Esc cancels (F:842) | Enter presses Run (`defaultButton`, Q:454); a number box commits on focus loss (Q:988-1001) | Ctrl-C | none | intended | |

## 2. Proposed conformance file

**One machine-readable file in this repository: `labconstrictor_tools/conformance.json`** (inside the package, so that every environment that already has `labconstrictor-tools` installed has it; add `[tool.setuptools.package-data] labconstrictor_tools = ["conformance.json"]` to `pyproject.toml`; `tests/conformance.json` would not reach the Napari, Fiji and QuPath test environments). It holds the values and test vectors the rows above show to be copied by hand into four code bases: named limits, error codes, message templates, number grammar, quoting, command vectors, coordinate vectors, result sentences, trust cases. Hosts keep their own constants; their tests read this file and compare. A change of a rule becomes a change of this file and a failing test in every host that has not followed.

Two keys carry the migration: `value` is the reference and `today` is what each host has now, so the first run of the new tests prints exactly the `DIVERGES` rows of section 1 and nothing else.

### Sketch (about 130 lines, 10 KB)

```json
{
  "conformance": 1,
  "_about": "Rules every host must agree on. Each host test loads this file and compares its own constants and functions with it. 'value' is the reference; 'today' lists what each host has now, so the first test run shows the drift.",
  "limits": {
    "max_shapes": {"value": 50000, "unit": "outlines", "counts": "features", "today": {"napari": 50000, "fiji": 50000, "qupath": 50000, "tools": 50000}},
    "table_rows_shown": {"value": 100000, "today": {"napari": 100000, "fiji": null, "qupath": 2000}},
    "region_max_objects": {"value": 65535, "today": {"napari": null, "fiji": 65535, "qupath": 65535}},
    "max_export_bytes": {"value": 4294967296, "today": {"napari": 4294967296, "fiji": null, "qupath": "100000000 pixels per plane"}},
    "max_display_bytes": {"value": 4294967296, "today": {"napari": 4294967296}},
    "unbounded_integer": {"value": [-2147483648, 2147483647], "today": {"napari": [-2147483648, 2147483647], "qupath": [-1000000000, 1000000000], "notebook": [-1000000000, 1000000000]}},
    "unbounded_float": {"value": [-1000000000000000, 1000000000000000], "today": {"napari": [-1000000000000000, 1000000000000000], "qupath": [-1000000000000, 1000000000000], "notebook": [-1000000000, 1000000000]}},
    "cancel_grace_s": {"value": 3, "library_default": 10, "today": {"napari": 3, "fiji": 3, "qupath": 3}},
    "worker_close_timeout_s": {"value": 10, "today": {"napari": 2, "fiji": 15, "qupath": 10, "client": 5}},
    "worker_orphan_grace_s": {"value": 10, "today": {"worker": 10}},
    "worker_idle_s": {"value": 600, "today": {"napari": 600, "qupath": null}},
    "choices_debounce_ms": {"value": 400},
    "choices_busy_retry_ms": {"value": 1500},
    "choices_after_run_ms": {"value": 200},
    "results_kept": {"value": 20},
    "run_records_kept": {"value": 50},
    "log_file_bytes": {"value": 1000000},
    "log_backups": {"value": 5},
    "request_line_bytes": {"value": 16777216},
    "fiji_manager_shapes": {"value": 1000, "host": "fiji"}
  },
  "error_codes": ["missing_parameter", "invalid_parameter", "file_not_found", "folder_not_found", "empty_image", "unreadable_image", "unsupported_format", "wrong_dimensions", "unsupported_dtype", "bad_return", "bad_input", "empty_region", "unknown_tool", "bad_request", "unserializable_result", "SystemExit", "KeyboardInterrupt"],
  "notice_codes": ["no_match", "no_result"],
  "host_internal_codes": ["host_error"],
  "messages": {
    "missing_parameter": "'{label}' is required",
    "invalid_integer": "'{label}' must be an integer",
    "invalid_float_not_finite": "'{label}' must be a finite number",
    "below_minimum": "'{label}' must be >= {minimum}",
    "above_maximum": "'{label}' must be <= {maximum}",
    "invalid_boolean": "'{label}' must be true or false, got {value!r}",
    "invalid_choice": "'{label}' must be one of {choices}",
    "file_not_found": "image file not found: {path}",
    "table_not_found": "table file not found: {path}",
    "folder_not_found": "'{label}': folder not found: {path}",
    "wrong_dimensions": "'{label}' must be a {n}D image ({axes}) but got {m}D with shape {shape}",
    "channel_missing": "'{label}': channel {asked} was asked for, but the image has {have}",
    "message_empty": "the message output '{name}' is empty",
    "shapes_cap": "showing the first {shown} of {total} outlines",
    "shapes_holes": "{count} outline(s) have holes",
    "table_truncated": "{total} rows, first {shown} shown",
    "unknown_result_type": "the tool returned a result of the type '{type}', which this host cannot show",
    "value_null": "(not a finite number)",
    "protocol_unsupported": "schema protocol {protocol} is not supported (this host speaks {supported})",
    "interpreter_missing": "not available on this machine (interpreter {python} is missing)",
    "file_result_missing": "the tool reported the file {path} but it does not exist",
    "cancelled_after_kill": "cancelled (worker stopped)",
    "copy_selection_note": "# {names}: the selection cannot be copied; save it as a label image and put its path here",
    "copy_channel_note": "# {name}: the host sent only channel {channel}; the command sends the whole file",
    "copy_area_note": "# {name}: the host sent only the Image area '{area}' (the command line has no area); the command sends the whole file",
    "copy_placeholder_note": "# replace the file for: {names}"
  },
  "worker_exit_hints": {
    "killed": {"codes": [-9, 137], "text": "the worker was killed (out of memory? the OS OOM killer ends big image jobs this way)"},
    "segfault": {"codes": [-11, 139, 3221225477, -1073741819], "text": "the worker crashed natively (segmentation fault in a compiled library)"},
    "import_failed": {"codes": [3], "text": "the app's tool module failed to import (see the traceback above)"},
    "missing_package": {"stderr_contains": ["ModuleNotFoundError", "ImportError"], "text": "a Python package is missing or broken in the app's environment (see the traceback above)", "checked": "first"}
  },
  "number_text": {
    "integer_regex": "^[+-]?[0-9]+$",
    "float_regex": "^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?$",
    "integer": {"accept": ["5", "-5", "+5", "007"], "reject": ["", " 5", "5 ", "5.0", "1e3", "1_000", "0x10", "٥", "nan", "5,0"]},
    "float": {"accept": ["5", "-5.5", ".5", "5.", "1e3", "1E-5", "0.325"], "reject": ["", " 0.5", "1,5", "1_0", "1.5f", "2d", "0x1p3", "nan", "inf", "Infinity"]},
    "non_finite_after_parse": ["nan", "inf"],
    "note": "text paths (macro, command line) refuse out-of-range values with below_minimum / above_maximum; GUI fields may hold the value inside the range instead"
  },
  "quoting": {
    "posix": [
      {"text": "plain", "quoted": "plain"},
      {"text": "with space", "quoted": "'with space'"},
      {"text": "it's", "quoted": "'it'\"'\"'s'"},
      {"text": "", "quoted": "''"},
      {"text": "x=y", "quoted": "x=y"},
      {"text": "$HOME", "quoted": "'$HOME'"},
      {"text": "a\nb", "quoted": "'a\nb'"},
      {"text": "naïve", "quoted": "'naïve'"}
    ],
    "windows": [
      {"text": "plain", "quoted": "plain"},
      {"text": "with space", "quoted": "\"with space\""},
      {"text": "a\"b", "quoted": "\"a\\\"b\""},
      {"text": "", "quoted": "\"\""},
      {"text": "50%", "quoted": "\"50%\""},
      {"text": "naïve", "quoted": "\"naïve\"", "note": "today command.py leaves it bare (isalnum); reference is ASCII only"},
      {"text": "C:\\my dir\\", "quoted": "TO DECIDE: a trailing backslash before the closing quote", "note": "defect shared by all four"}
    ],
    "python_literal": [
      {"value": "plain", "literal": "'plain'"},
      {"value": "a\nb", "literal": "'a\\nb'"},
      {"value": "tab\t", "literal": "'tab\\t'"},
      {"value": "back\\slash", "literal": "'back\\\\slash'"},
      {"value": true, "literal": "True"},
      {"value": 0.325, "literal": "0.325"},
      {"value": 3, "literal": "3"},
      {"value": "it's", "literal": "any valid literal that evaluates back to it's", "check": "evaluate"}
    ]
  },
  "command_vectors": [
    {"tool": {"id": "blur", "inputs": [{"name": "image", "type": "image", "required": true}, {"name": "sigma", "type": "float", "required": false, "default": 2.0}, {"name": "label", "type": "string", "required": false}, {"name": "fast", "type": "boolean", "required": false, "default": false}]}, "app": "Demo", "python": "/opt/app/bin/python", "platform": "posix", "values": {"sigma": 0.325, "label": "my cells", "fast": true}, "terminal": "# replace the file for: image\n/opt/app/bin/python -m labconstrictor_tools run Demo blur image=image.tif sigma=0.325 'label=my cells' fast=true", "python_evaluates_to": {"app": "Demo", "tool": "blur", "inputs": {"image": "image.tif", "sigma": 0.325, "label": "my cells", "fast": true}}}
  ],
  "coordinates": {
    "pixel_centres_at_integers": true,
    "points": [
      {"yx": [0, 0], "napari_data": [0, 0], "fiji_roi_xy": [0.5, 0.5], "qupath_xy": [0.5, 0.5]},
      {"yx": [2, 5], "napari_data": [2, 5], "fiji_roi_xy": [5.5, 2.5], "qupath_xy": [5.5, 2.5]}
    ],
    "polygon_geojson_xy": {"ring": [[1, 1], [4, 1], [4, 3], [1, 3], [1, 1]], "fiji_xy": [[1.5, 1.5], [4.5, 1.5], [4.5, 3.5], [1.5, 3.5]], "area_px": 6},
    "image_area_offset": {"qupath_x0_y0": [10, 20], "result_xy": [3, 4], "slide_xy": [13.5, 24.5]},
    "affine": {"matrix_yx": [[1, 0, 2], [0, 1, 3], [0, 0, 1]], "maps": {"source_yx": [5, 5], "target_yx": [7, 8]}},
    "region_mask": {"image_shape_yx": [8, 8], "rectangles_xywh": [[2, 2, 3, 2], [5, 5, 2, 2]], "labels": {"1": 6, "2": 4}, "note": "pixel-edge cases differ between three rasterisers: this vector finds out"}
  },
  "results_text": {
    "values": [{"values": {"a": 1.5, "b": null}, "must_contain": ["a=", "b=(not a finite number)"]}],
    "shapes_cap": {"features": 50001, "shown": 50000, "message": "showing the first 50000 of 50001 outlines"},
    "table_truncated": {"rows": 100001, "shown": 100000, "message": "100001 rows, first 100000 shown"}
  },
  "trust_vectors": [
    {"case": "interpreter outside the prefix", "expect": "refused", "reason_contains": "not inside the install prefix"},
    {"case": "prefix is a filesystem root", "expect": "refused", "reason_contains": "filesystem root"},
    {"case": "entry file writable by group", "expect": "refused", "reason_contains": "writable by other users", "posix_only": true},
    {"case": "entry file owned by another user", "expect": "refused", "reason_contains": "not owned by the current user", "posix_only": true},
    {"case": "interpreter folder writable by everybody (not sticky)", "expect": "refused", "reason_contains": "writable by everybody", "posix_only": true},
    {"case": "schema file in another folder", "expect": "refused", "reason_contains": "not in the same folder as the entry", "posix_only": true},
    {"case": "tool id with a path separator", "expect": "refused"},
    {"case": "parameter name that is not an identifier", "expect": "refused"},
    {"case": "entry missing a required field", "expect": "refused", "reason_contains": "must be a non-empty string"},
    {"case": "schema protocol 2", "expect": "refused", "reason_contains": "protocol"}
  ]
}
```

`messages` use `{name}` placeholders, written for Python `str.format`; Groovy hosts replace `{name}` with a one-line helper. The vectors in `command_vectors` are produced by `command.py` when the file is written (a Tools test regenerates them and fails if the file is stale), so the reference implementation is the only place a quoting rule is decided.

### How each host's test would load it

| Host | Where the test lives | Loading | What it checks |
|---|---|---|---|
| CLI, `command.py`, `convert.py`, notebook | `tests/test_conformance.py` in this repository | `json.loads(importlib.resources.files("labconstrictor_tools").joinpath("conformance.json").read_text("utf-8"))` | `cli.parse_value` against `number_text`; `convert.load_inputs` messages against `messages`; `command.quote` and `command_line` against `quoting` and `command_vectors`; `cli.RESULTS_KEPT`, `runs.KEEP`, `log.LOG_FILE_BYTES`, `client.CANCEL_GRACE_S` against `limits`; `registry` against `trust_vectors`; `ToolForm` unbounded limits and nullable "set" controls |
| Napari | `tests/test_conformance.py` (a plain script like the others, no Qt needed for most of it) | same call (Tools is a dependency of the plugin) | `_results.MAX_SHAPES`, `_results.MAX_TABLE_ROWS`, `_export.MAX_EXPORT_BYTES`, `_widget.CANCEL_GRACE_S`, `_workers.IDLE_SECONDS`, `_schema._INT_RANGE`, `_schema._FLOAT_RANGE` against `limits`; `ResultPresenter` sentences against `messages`; point and polygon vectors through a fake viewer (`viewer.add_points` receives `napari_data`); region mask vector through `selection_mask` |
| Fiji | a case type `conformance` in `tests/run_cases.py`; the Groovy side is `tests/conformance_check.groovy` | the Python driver finds the file with `python -c "import labconstrictor_tools, pathlib; print(pathlib.Path(labconstrictor_tools.__file__).with_name('conformance.json'))"` and passes it in the environment variable `LC_CONFORMANCE`; Groovy reads it with `new JsonSlurper().parse(new File(System.getenv("LC_CONFORMANCE")))` | the harness parses the script text without its last line (`labConstrictorMain()`) with `new GroovyShell().parse(...)` and calls `shellQuote`, `pythonLiteral`, `macroNumber`, `commandText`, `polygonRoi`, `outlinesOf`, `selectionMask` and reads the `@Field` constants (`MAX_SHAPES`, `CANCEL_GRACE_MS`, `EXIT_WAIT_MS`...) |
| QuPath | `tests/gui_test_conformance_body.groovy`, run by `tests/run_gui_test.sh` like the others (or `tests/headless_core.groovy` for the parts that need no GUI) | `LcJson.parse(new File(System.getenv("LC_CONFORMANCE")))` (the script already has `LcJson`; the test bodies already have `expect(name, ok, detail)`) | the static members: `LcConst.*`, `LcDialog.shellQuote`, `LcDialog.pythonLiteral`, `LcDialog.show`, `LcArea.clamped`, `LcDialog.paintLabelMask`, `LcRegistry.load` against a registry built from `trust_vectors`, and the sentences produced by `placeShapes` and `tableView` |

Two rules for the file itself: it never contains a value that only one host needs (those stay in that host; the Fiji ROI Manager cap is marked `"host": "fiji"` only so that the test can see it), and a host test must fail when a key it knows is missing (no silent skip, the lesson of `docs/HOST_FEATURES.md` "Fallbacks").


## 3. The 15 most user-visible divergences, ranked

Ranked by how many people meet it, how silent the harm is (a wrong result before a wrong message before a different look), and how much of the work a person has to redo. Row ids point into section 1; change names into section 4.

1. B04 - Optional parameters without a default (a seed, a time limit): the notebook form always sends 0, an empty text, False or the first choice; Napari, Fiji, QuPath and the command line leave them unset and the tool receives None. PROTOCOL.md calls showing 0 a bug. A silent wrong value. Fix NB-2 (notebook S).
2. O01-O06 - QuPath accepts registry entries that Tools, Napari and Fiji refuse: no owner check, no permission check of interpreter, its folder and the prefix, no check that the schema sits next to the entry, no check of names (a parameter name is used inside a file path). Fix QP-1 (QuPath M, port the Fiji functions; do it first).
3. I03, F01, F02 - Every refusal QuPath makes before a run reads `failed: IllegalStateException: ...` or `FileNotFoundException: ...` with an internal code `host_error`; Napari and Fiji show the sentence alone. Fix QP-2 (QuPath S).
4. C15, C16 - A Z-stack or multi-channel image given to a 2D tool: Fiji silently sends the plane on screen, QuPath sends plane 0 with every channel, Napari, the command line and the notebook refuse with `wrong_dimensions`. Fix FJ-9 (Fiji S), QP-9 (QuPath S), NP-1 (Napari M); durable fix TOOLS-5 (a PickPlane hint, Tools M).
5. H03 - Result tables: Napari shows up to 100 000 rows with a notice, QuPath only 2 000, Fiji all rows with no notice. Fix QP-11 (QuPath S).
6. C17, C20, C21 - Pixel-size field: Napari follows the layer or the file header until the person edits it and warns about non-square pixels; Fiji and QuPath overwrite a typed value whenever the image changes; QuPath never reads a file's header; Fiji ignores a centimetre TIFF unit. Fix QP-8 (QuPath S), FJ-10 (Fiji S).
7. C11 - ClearAfterRun: QuPath resets only text fields; numbers, yes/no boxes and fixed choices keep their old values, so the next run silently reuses them (the notebook resets nothing). Fix QP-3 (QuPath S), NB-3 (notebook S).
8. C08 - EnabledWhen: QuPath has listeners only for dropdown and checkbox drivers, so a field driven by a number, a text or a "set" box never greys out or wakes up, and an empty text counts as set. Fix QP-4 (QuPath S).
9. A12 - A choice whose options are numbers (Literal[1, 2, 3]): Fiji sends the text "2" and QuPath sends 2.0, and the worker refuses both; Napari, the command line and the notebook work (predicted from code, not run). Fix FJ-5 (Fiji S), QP-2d (QuPath S).
10. B10 - Parameter order: QuPath does not gather the parameters of a group that are not next to each other and moves every Collapsed group below all other rows; Napari and Fiji gather them at the group's first appearance. Fix QP-5 (QuPath S).
11. J08 - After a Cancel that needed a kill: Napari says "cancelled (worker stopped)"; QuPath says "the worker stopped: The worker was killed (out of memory? ...)"; Fiji's status bar says "crashed". Fix QP-16 (QuPath S), FJ-20 (Fiji S).
12. F05 - Relative paths: Fiji checks them against Fiji's folder and sends them as typed to a worker whose folder is the app prefix, so a file the dialog accepted may not be found or may be another file (predicted from code, not run). Fix FJ-2 (Fiji S).
13. H05 - Points without `apply_to`: Napari uses the first input of any type (scale 1, 1 when it is not an image), Fiji the last image shown or the current one, QuPath the first image input as PROTOCOL.md says. Fix NP-6 (Napari S), FJ-14 (Fiji S).
14. M01, L03, M02 - Support trail: QuPath's log never reaches the shared log file and QuPath keeps no run records, so `labconstrictor-tools logs` and `support-bundle` miss QuPath runs; Fiji's log keeps one backup and its rotation can fail on Windows. Fix QP-20 and QP-19 (QuPath M each), FJ-4 (Fiji S).
15. G03 - Too-large images: Napari refuses an export above 4 GiB of data, QuPath above 100 million pixels per plane, Fiji never; the sentences differ. Fix QP-10 (QuPath M), FJ-12 (Fiji S).

## 4. The changes that would align the hosts

Each `DIVERGES` row names one or more of these. `NB-*` changes are in this repository (the notebook form lives here). Sizes: S under half a day, M one to three days. Suggested bundles: **QP-1 first and alone** (security); then QuPath S-items in three PRs (form hints: QP-3, 4, 5; messages and results: QP-2, 6, 7, 11, 12, 13, 15, 16; lifecycle: QP-17, 18, 21), the two M-items QP-19 and QP-20 together; Fiji as one PR per theme (messages FJ-6 FJ-18, results FJ-13 FJ-14 FJ-15 FJ-16, pixel size FJ-10, paths and environment FJ-2 FJ-3); Napari as two PRs (behaviour NP-1 NP-3 NP-4 NP-6, messages NP-2 NP-5 NP-7 NP-8 NP-10 NP-9); Tools: TOOLS-1 first (every other host change should land with its vectors), then the rest.

| change | where | size | what | rows |
|---|---|---|---|---|
| TOOLS-1 | Tools | M | add `labconstrictor_tools/conformance.json` (section 2), package-data entry, `tests/test_conformance.py` that reads it for CLI, command.py, convert.py, notebook | I05, I06 |
| TOOLS-2 | Tools | S | `command.quote` on Windows: ASCII-only safe set; fix the trailing-backslash case; vectors | N03 |
| TOOLS-3 | Tools | S | MANIFEST.md: say what "bounds, enforced everywhere" means (GUIs hold the value inside the range, text paths refuse) | C01 |
| TOOLS-4 | Tools | S | `run --usage` shows the unit | C02 |
| TOOLS-5 | Tools | M | a `PickPlane` hint (the person chooses Z/T), so that 2D tools get a plane on purpose in every host (hosts: another S each) | C16 |
| TOOLS-6 | Tools | S | HOST_FEATURES.md: add notebook and CLI columns and the rows of this page that are `intended` | C27 |
| TOOLS-7 | Tools | S | `cli.parse_value`: strict number grammar, "an integer" | D02, D03, I06 |
| TOOLS-8 | Tools | S | a table that does not exist: `[file_not_found] table file not found: P` | F02 |
| TOOLS-9 | Tools | S | affine: refuse non-finite matrices in `_as_3x3` (`bad_return`) | H13 |
| TOOLS-10 | Tools | S | `client.CLOSE_TIMEOUT_S` 5 to 10 (the worker promises 10) | K03 |
| TOOLS-11 | Tools | S | `_validated_schema`: check tool ids, parameter names (identifiers) and parameter types like Fiji does | O06 |
| NB-1 | Tools (notebook) | S | unbounded limits +-(2^31-1) / +-1e15; unit in the label | A06, A07, C02 |
| NB-2 | Tools (notebook) | S | "set" checkbox for every nullable control, omit when off | B04 |
| NB-3 | Tools (notebook) | S | honour ClearAfterRun | C11 |
| NB-4 | Tools (notebook) | S | trim typed paths | E01 |
| NB-5 | Tools (notebook) | S | render message results as Markdown | E04 |
| NB-6 | Tools (notebook) | S | print a null value as `(not a finite number)` | H02 |
| NB-7 | Tools (notebook) | S | results into `<LC_HOME>/results` with the CLI pruning, not an unremoved temp folder | H18, L01 |
| NB-8 | Tools (notebook) | S | `no_match` / `no_result` as a notice | I02 |
| NB-9 | Tools (notebook) | S | call `log.logger()` so the form writes the shared log | M01 |
| NP-1 | Napari | M | PickChannel and 2D tools: send the plane on screen (`viewer.dims.current_step`), say so in the status; file: first plane plus a note | C15 |
| NP-2 | Napari | S | messages: `missing_parameter`, `file_not_found`, channel templates from the conformance file | B01, F01, I11 |
| NP-3 | Napari | S | RegionOf with an image given as a file: refuse | C23 |
| NP-4 | Napari | S | RegionOf: at most 65 535 shapes | C24 |
| NP-5 | Napari | S | show a null value as `(not a finite number)` | H02 |
| NP-6 | Napari | S | results without `apply_to`: the first IMAGE input | H05 |
| NP-7 | Napari | S | shapes cap counts features | H08 |
| NP-8 | Napari | S | unknown result type: name, type and path plus one sentence | H15 |
| NP-9 | Napari | S | worker close timeout 2 to 10 s | K03 |
| NP-10 | Napari | S | Copy as command: channel note and the order of notes | N07 |
| FJ-1 | Fiji | S | `pythonLiteral`: escape `\n \r \t` and non-printables | E03 |
| FJ-2 | Fiji | S | send absolute paths (`File.absolutePath`) | F05 |
| FJ-3 | Fiji | M | worker environment as the client (scrub, PYTHONSAFEPATH, working directory) | K09 |
| FJ-4 | Fiji | S | log: five numbered backups with replace-on-move, level names as Tools; prune only its own run records | L03, M02, M03 |
| FJ-5 | Fiji | S | a choice returns the declared (typed) choice | A12 |
| FJ-6 | Fiji | S | messages: `missing_parameter`, `file_not_found` templates | B01, F01 |
| FJ-7 | Fiji | S | starting value of a required number: nearest allowed to 0 | B07 |
| FJ-8 | Fiji | S | table title `name [n]` unless Replace | C13 |
| FJ-9 | Fiji | S | stack into a YX tool: refuse (or document and test the plane choice) | C16 |
| FJ-10 | Fiji | S | pixel size: keep typed values, anisotropy warning, `cm` TIFF unit | C17, C20, C21 |
| FJ-11 | Fiji | S | macro number grammar: strict | D03 |
| FJ-12 | Fiji | S | export size guard (bytes) | G03 |
| FJ-13 | Fiji | S | show a null value as `(not a finite number)` | H02 |
| FJ-14 | Fiji | S | results without `apply_to`: the first image input | H05 |
| FJ-15 | Fiji | S | shapes cap counts features, same sentence | H08 |
| FJ-16 | Fiji | S | singular matrix: warn, apply | H13 |
| FJ-17 | Fiji | S | exit codes: add the signed Windows access violation | I05 |
| FJ-18 | Fiji | S | macro number messages: worker template first, `got x` after | I06 |
| FJ-19 | Fiji | S | unsupported parameter type: skip the tool, not the app | I08 |
| FJ-20 | Fiji | S | after Cancel the status bar says cancelled, not crashed | J08 |
| FJ-21 | Fiji | S | Copy as command: `region.tif` placeholder and notes for a selection and a channel | N07 |
| FJ-22 | Fiji | S | tool chooser: `label (id)` for duplicates, sorted apps, tool description in the dialog | P05, P06, P07 |
| QP-1 | QuPath | M | trust checks: port `entryProblem`, `untrustedReason`, `plainName`, `identifier`, `toolId` from the Fiji script (rows O01-O06). Do this first | O01, O02, O03, O04, O05, O06 |
| QP-2 | QuPath | S | host-side refusals: message only, no class name; file/folder/table checks with the shared templates (sub-items b to f below) | F01, F02, F06, I03 |
| QP-2b | QuPath | S | folder: `isDirectory()` and the folder template | A05 |
| QP-2c | QuPath | S | unbounded integer and float limits from the conformance file | A06, A07 |
| QP-2d | QuPath | S | parse JSON integers as integers (a `ToNumberPolicy`) | A12 |
| QP-2e | QuPath | S | `missing_parameter` template | B01 |
| QP-2f | QuPath | S | refuse non-finite numbers before sending | D04 |
| QP-3 | QuPath | S | ClearAfterRun for every control type | C11 |
| QP-4 | QuPath | S | EnabledWhen: listen to every driver and to the "set" box; `""` is unset | C08 |
| QP-5 | QuPath | S | use the same `presentationOrder` as Napari and Fiji | B10 |
| QP-6 | QuPath | S | `pythonLiteral` escaping | E03 |
| QP-7 | QuPath | S | message results: bullets | E04 |
| QP-8 | QuPath | S | pixel size: read a file header, keep typed values, anisotropy warning | C17, C20 |
| QP-9 | QuPath | S | a 2D export uses the viewer plane for the whole image too | C15 |
| QP-10 | QuPath | M | export guard in bytes (channels and pixel type), property kept | G03 |
| QP-11 | QuPath | S | table rows 2 000 to 100 000; multi-line CSV cells | H03 |
| QP-12 | QuPath | S | shapes sentence as the conformance template; unknown result type sentence | H08, H15 |
| QP-13 | QuPath | S | crash hints: Tools wording, ModuleNotFoundError rule | I04, I05 |
| QP-14 | QuPath | S | registry/schema messages as Tools (protocol, interpreter missing), unsupported parameter type refused | I08, I09, I10 |
| QP-15 | QuPath | S | clipboard failure reported | I13 |
| QP-16 | QuPath | S | a kill after Cancel is reported as cancelled | J08 |
| QP-17 | QuPath | S | idle timeout 600 s for the kept worker | K02 |
| QP-18 | QuPath | S | results folder: slugged name, 6 hex, prune only `^\d{8}T\d{6}_` folders | L01, L02 |
| QP-19 | QuPath | M | run records under `<LC_HOME>/runs`, newest 50 | L03 |
| QP-20 | QuPath | M | append to the shared `<LC_HOME>/logs/labconstrictor.log` in the Tools line format with rotation | M01 |
| QP-21 | QuPath | S | tool chooser: `label (id)` for duplicates, sorted apps | P05, P06 |

## 5. What could not be determined from the code

None of these was run; the first group needs a toolkit's source or a real screen, the second needs a person with the operating system.

* Typed decimal separators and grouping in a number box (Qt, SciJava, JavaFX, ipywidgets): D01. Needs a hand test on a German or French locale.
* Whether a number typed outside Min..Max is clamped, refused or rejected keystroke by keystroke in the SciJava dialog and in the JavaFX spinner (C01); `NaN` typed into a QuPath or Fiji box (D04).
* The starting value of a required number without a default in Napari (B07), the layer a Napari chooser starts on (P03), the number of decimals of a magicgui float box.
* Whether magicgui's file box can return a relative path (F05, Napari cell).
* Whether `ResultsTable.show(name)` replaces the window in Fiji without `Replace()` (C13), whether a relative path really misses in Fiji (F05) and whether numeric choices fail in Fiji and QuPath (A12): all three predicted from code.
* Whether Appose's `Service.kill()` ends the processes a tool started (K07, Fiji), and whether its environment map can remove a variable (K09).
* The axis order and the embedded calibration of a QuPath multi-channel export (G02, G06).
* Where the notebook's log lines go when `log.logger()` was never called (M01).
* The pixel-edge behaviour of the three region rasterisers (Napari `to_labels`, ImageJ `fill`, Java2D `fill`) (C22): the region vector in section 2 is meant to find out.
* Windows and macOS in every host (the host READMEs say untested): unicode paths (F04), the unsigned or signed access-violation exit code (I05), the log rotation of Fiji (M02), the `taskkill` path (K07).
* Which of these rows are already covered by a host test that I did not map: I read the code and the READMEs, not every test file.
