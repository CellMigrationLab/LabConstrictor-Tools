# NucleiSky: synthetic datasets (source of the generator)

Tools covered: relocalize (2D). The scene module is generic (analytic nuclei, exact similarity transforms); the dataset list, units and expectations are NucleiSky-specific.

    python make_nucleisky.py OUT_DIR

Needs `make_nucleisky.py` and `ns_scene.py`, plus `common.py` and `check_ground_truth.py` (next to the script or one folder up); numpy, scipy, pandas and tifffile only.
Writes `cases.json` (the format of `lc_tests/cases.json`), `fixtures/`, `ground_truth.json`, `README.md` (the dataset list) and `check_ground_truth.py` into OUT_DIR.
See `../README.md` for the layout of the output, the checker and which files are generic.
