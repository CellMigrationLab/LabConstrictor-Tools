# LabConstrictor-Playground: synthetic datasets (source of the generator)

Tools covered: feature_tour, count_above_level, bright_area, align_centres, summarise_table, look_inside_file, make_test_data. Everything here is specific to these tools.

    python make_playground.py OUT_DIR

Needs `make_playground.py` and `pg_images.py`, plus `common.py` and `check_ground_truth.py` (next to the script or one folder up); numpy, scipy, pandas and tifffile only.
Writes `cases.json` (the format of `lc_tests/cases.json`), `fixtures/`, `ground_truth.json`, `README.md` (the dataset list) and `check_ground_truth.py` into OUT_DIR.
See `../README.md` for the layout of the output, the checker and which files are generic.
