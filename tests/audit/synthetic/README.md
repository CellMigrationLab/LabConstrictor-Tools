# Synthetic datasets with known ground truth

Audit run of 14 Oct 2026 and its re-runs (alpha.2 to alpha.4) (see `docs/TEST_STRATEGY.md`, sections 0, 3.1 and 3.8). For every LabConstrictor app the generator writes input data
whose right answer is computed by the generator itself (an independent oracle), so wrong-science bugs (calibration, axes, frame, units, off-by-one,
silent rounding) show up as a disagreement instead of a green run.

## Run it

    python make_synthetic.py --out SYN_DIR [--app NucleiSky ...]       # about 1 minute, 174 MB
    python prove_generators.py SYN_DIR                                  # reload the files, redo the arithmetic (PYTHONPATH=<Tools repo> also validates cases.json)
    python negative_controls.py SYN_DIR                                 # the checker must fail seeded errors
    PYTHONPATH=<Tools repo> python validate_against_declarations.py SYN_DIR APP_SOURCES_DIR   # every case against the DECLARED inputs of the tool (source checkouts, no install)
    python run_cli_cases.py --app NAME --data SYN_DIR/NAME --reports REPORTS_DIR [--python APP_PYTHON]   # all cases through the worker, no GUI
    python check_ground_truth.py SYN_DIR/NAME/ground_truth.json --reports REPORTS_DIR --data WORK_DIR

The raw outputs of the proofs of 14 Oct 2026 are not kept in the repository (they predate the alpha.4 truths); regenerate them with the commands above.

Interpreters: `PYTHON_WITH_NUMPY` (numpy, scipy, pandas, tifffile) or any Python that has those four; nothing else is installed.

## What is written, per app, in `<out>/<AppName>/`

| file | what |
|---|---|
| `cases.json` | exactly the format of the app's own `lc_tests/cases.json` (a list of `{tool, inputs, comment, expect}`); every comment starts with `[dataset id]`. Use it through `LC_APP_TESTS` in `sandbox_checks.py cases` and the UI-audit drivers |
| `fixtures/` | the generated files; calibrated images are ImageJ TIFFs (spacing, unit, resolution tags), copies in `fixtures/ome/` are OME-TIFF (PhysicalSize*); "uncalibrated" ones are plain TIFFs |
| `ground_truth.json` | per dataset: purpose, expected outcome (`works` / `refused` / `HUMAN`), how the truth was derived, files, the primary case, `checks` (machine oracle) and `host_checks` (what a host form must show) |
| `truth/` | truth tables (CSV) too large to inline |
| `check_ground_truth.py` | compares run reports with the truth (see below) |
| `README.md` | the dataset table: id, purpose, expected outcome, tool, files |
| `no_case.json` | only where the suite has no case for a tool (Playground: tools without data), as the sandbox `cases` check expects |

Cases that depend on earlier ones (a game of Guess the Condition) must run **in order** and in a **copy** of the folder (fixtures are written into).

## The checker

`check_ground_truth.py ground_truth.json --reports DIR [--data RUNDIR] [--only ID] [--with-host]` reads `DIR/<dataset id>.json`, the JSON that
`labconstrictor-tools run` prints (`run_cli_cases.py` writes them; a host driver or the notebook runner writes the same shape and may add
`"host_observed": {"<field>": value}`). One `CHECK` line per assertion; exit 0 only if everything passed; a dataset with checks and no report is
`NOT_RUN` and fails. Kinds: `status` (status, code, sentence), `value` (number within tolerance / range / text contains), `absent_value`, `matrix`
(linear part and translation separately), `table` (against a truth CSV, by key), `table_bound`, `message`, `points_map` (query points moved by the
TRUTH matrix must land on reference points: a frame check independent of the tool's matrix), `image_stat`, `centroid`, `tiff_slice_means`,
`host_param`. `host_checks` are judged only with `--with-host`.

## Liftable layout (each app folder can move into its app repository)

Generic (copy as they are): `common.py`, `check_ground_truth.py`, `run_cli_cases.py`, and `NucleiSky/ns_scene.py` (an analytic nuclei scene with exact similarity
transforms, reusable for any registration data). App-specific: everything else in an app folder (`make_<app>.py` and its helper modules `ns_helpers.py`, `ns_masks.py`,
`pg_common.py`, `pg_discs.py`, `pg_images.py`, `vm_common.py`, `vm_compare.py`, `gtc_core.py`, `gtc_views.py`): they hold the tool names, inputs, units, expectations and truth of that
app. An app folder depends only on numpy, scipy, pandas, tifffile and the two generic files next to it (or one folder up); it imports nothing from the Tools repository or from
`tests/audit`, and runs alone: `python make_<app>.py OUT_DIR`. Only `make_synthetic.py` (all apps at once), `prove_generators.py` and `negative_controls.py` are specific to this run.

## Datasets per app

* **NucleiSky** (`relocalize`, 2D only; no 3D tool exists in the bridge): analytic nuclei fields with a known similarity transform (rotation, 2x magnification, exact crop, pure rotation), exact masks and region
  boxes with non-zero origins, calibration written in um / nm / micro sign / micron / none / pixel unit / anisotropic, 8/16/32-bit, stacks and RGB (refused), NaN, flat, unrelated images, a 3000x3000 stress field.
* **LabConstrictor-Playground** (feature_tour, count_above_level, bright_area, align_centres, summarise_table, look_inside_file, make_test_data): lattice discs with exact centres and areas, ramps with exact counts and percentiles, rectangles with counted pixels
  in every calibration, sub-pixel centroids, tables and files at their limits (1 000 000 bytes exact), NaN and all-zero images, a 3000x3000 stress pair.
* **LabConstrictor-VLab4Mic** (compare_images, simulate_sample): spot images with exact Pearson (1, 1, -1), the same field at half resolution with right and wrong pixel sizes, refusals, a 2500x2500 stress pair; simulations offline on a synthetic ring structure with image size = sample / pixel.
* **GuessTheCondition**: experiment folders (conditions x repeats x images) played with a constant guess, so accuracy, chance, tables and p-values follow by counting; percentage rounding, scan rules, a corrupt file, every axes/bit-depth variant, a 3000x3000 stress image.
* **CellTracksColab** (`calculate_metrics`, hidden from every host: CLI/worker and notebooks only): tracks built from steps of known length and direction (straight 2D/3D, time in seconds, irregular steps, zigzag, circle, speed ramp), unsorted rows, single spots, NaN rows, 2D without Z, 100 000-row stress, and the refusals.

Truth that is a **convention** and not independent is said so in the dataset's `derivation` (for example the mean of per-step speeds, population SD). Predictions that were not verified against the app are labelled as such.
