# LabConstrictor-VLab4Mic: synthetic datasets (source of the generator)

Tools covered: compare_images, simulate_sample. The spot images are generic; the modality table (pixel size per modality) and the structure file are VLab4Mic-specific.

    python make_vlab4mic.py OUT_DIR

Needs `make_vlab4mic.py`, plus `common.py` and `check_ground_truth.py` (next to the script or one folder up); numpy, scipy, pandas and tifffile only.
Writes `cases.json` (the format of `lc_tests/cases.json`), `fixtures/`, `ground_truth.json`, `README.md` (the dataset list) and `check_ground_truth.py` into OUT_DIR.
See `../README.md` for the layout of the output, the checker and which files are generic.
