# GuessTheCondition: synthetic datasets (source of the generator)

Tools covered: the game (prepare, play, undo, analyse). The counting oracle for accuracy, chance and the tables is specific to the analysis of this app.

    python make_guessthecondition.py OUT_DIR

Needs `make_guessthecondition.py`, plus `common.py` and `check_ground_truth.py` (next to the script or one folder up); numpy, scipy, pandas and tifffile only.
Writes `cases.json` (the format of `lc_tests/cases.json`), `fixtures/`, `ground_truth.json`, `README.md` (the dataset list) and `check_ground_truth.py` into OUT_DIR.
See `../README.md` for the layout of the output, the checker and which files are generic.
