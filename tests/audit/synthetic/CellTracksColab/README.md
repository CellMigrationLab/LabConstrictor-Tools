# CellTracksColab: synthetic datasets (source of the generator)

Tools covered: calculate_metrics. The track builder (tracks made of steps with known length and direction) is reusable for any tracking-table tool; the metric names are CellTracksColab's.

    python make_celltracks.py OUT_DIR

Needs `make_celltracks.py`, plus `common.py` and `check_ground_truth.py` (next to the script or one folder up); numpy, scipy, pandas and tifffile only.
Writes `cases.json` (the format of `lc_tests/cases.json`), `fixtures/`, `ground_truth.json`, `README.md` (the dataset list) and `check_ground_truth.py` into OUT_DIR.
See `../README.md` for the layout of the output, the checker and which files are generic.
