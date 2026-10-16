"""Shared pieces of the CellTracksColab click scripts: a synthetic tracking dataset of KNOWN tracks (straight lines at a constant speed, so every metric has an exact value that is
computed here from the construction, not by the notebook), the loader stage, and the oracles on the files the notebooks save in their Results folder.

Dataset: folder/<Condition>/<experiment>/FOV1.csv, conditions Control (step 1.0 per frame) and Mutant (step 2.0 per frame), experiments exp1..exp3, 8 straight tracks of 20 spots per file,
frame time 1, directions in the first quadrant: 2 x 3 files, 48 tracks, 960 spots. Expected after the loading steps: Track Duration 19, Mean Speed 1.0 / 2.0, Total Distance Traveled 19 / 38,
Directionality 1 (a straight line). The same tracks are also written as CellTracksColab tables (merged_Tracks / merged_Spots, with the columns the app's own loader adds) for the notebooks
that start from tables, and as ROI masks `<File_name>_<ROI>.tif` for the Distance_to_ROI notebook."""

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

STEPS = {"Control": 1.0, "Mutant": 2.0}
EXPERIMENTS = ("exp1", "exp2", "exp3")
N_TRACKS, N_SPOTS = 8, 20
ROI_NAME = "nuclei"
ROI_CAL = 0.5
ROI_SHAPE = (200, 200)
ROI_CENTRE, ROI_RADIUS = (100, 100), 20


def make_dataset(work: Path, dims: str = "2D", fmt: str = "custom") -> dict[str, Any]:
    """Write the folder tree (fmt "custom": FOV1.csv; fmt "trackmate": FOV1_spots.csv and FOV1_tracks.csv with the three descriptive rows TrackMate writes) and the CellTracksColab tables; returns the paths and the truth."""
    rng = np.random.default_rng(21)
    root = work / ("ctc_data_" + fmt)
    spots_rows: list[pd.DataFrame] = []
    for condition, step in STEPS.items():
        for experiment in EXPERIMENTS:
            frames = []
            for track in range(1, N_TRACKS + 1):
                angle = rng.uniform(0.1, np.pi / 2 - 0.1)
                x0, y0 = rng.uniform(5, 50, 2)
                t = np.arange(N_SPOTS, dtype=float)
                frame = pd.DataFrame(
                    {
                        "TRACK_ID": track,
                        "POSITION_X": x0 + step * np.cos(angle) * t,
                        "POSITION_Y": y0 + step * np.sin(angle) * t,
                        "POSITION_T": t,
                    }
                )
                if dims == "3D":
                    frame["POSITION_Z"] = 5.0
                frames.append(frame)
            table = pd.concat(frames, ignore_index=True)
            folder = root / condition / experiment
            folder.mkdir(parents=True, exist_ok=True)
            if fmt == "trackmate":
                _write_trackmate(folder, table)
            else:
                table.to_csv(folder / "FOV1.csv", index=False)
            table = table.assign(
                Condition=condition,
                experiment_nb=experiment,
                File_name_raw="FOV1",
                File_name="%s_%s_FOV1" % (condition, experiment),
            )
            spots_rows.append(table)
    spots = pd.concat(spots_rows, ignore_index=True)
    spots["Repeat"] = spots["experiment_nb"].map({e: i + 1 for i, e in enumerate(EXPERIMENTS)})
    spots["Unique_ID"] = spots["File_name"] + "_" + spots["TRACK_ID"].astype(str)
    spots["FRAME"] = spots["POSITION_T"].astype(int)
    if dims == "2D":
        spots["POSITION_Z"] = 0
    tracks = (
        spots[["Unique_ID", "TRACK_ID", "File_name", "Condition", "experiment_nb", "File_name_raw", "Repeat"]]
        .drop_duplicates("Unique_ID")
        .reset_index(drop=True)
    )
    # metric columns with a little noise per track: the notebooks that start from tables (UMAP, t-SNE) need numeric metrics that differ between tracks; the notebooks that recompute the
    # metrics from the spots (Part 4) replace these columns and are then checked against the exact values
    jitter = np.random.default_rng(29)
    base = tracks["Condition"].map(STEPS).to_numpy(float)
    for name, factor in (
        ("Mean Speed", 1.0),
        ("Median Speed", 1.0),
        ("Max Speed", 1.1),
        ("Min Speed", 0.9),
        ("Speed Standard Deviation", 0.05),
        ("Total Distance Traveled", N_SPOTS - 1.0),
    ):
        tracks[name] = base * factor * (1 + 0.03 * jitter.standard_normal(len(tracks)))
    tracks["Track Duration"] = (N_SPOTS - 1) * (1 + 0.03 * jitter.standard_normal(len(tracks)))
    tables = work / "ctc_tables"
    tables.mkdir(parents=True, exist_ok=True)
    spots.to_csv(tables / "merged_Spots.csv", index=False)
    tracks.to_csv(tables / "merged_Tracks.csv", index=False)
    roi = work / "ctc_roi"
    roi.mkdir(parents=True, exist_ok=True)
    yy, xx = np.mgrid[0 : ROI_SHAPE[0], 0 : ROI_SHAPE[1]]
    mask = (((yy - ROI_CENTRE[0]) ** 2 + (xx - ROI_CENTRE[1]) ** 2) <= ROI_RADIUS**2).astype(np.uint8)
    import tifffile

    for name in spots["File_name"].unique():
        tifffile.imwrite(roi / ("%s_%s.tif" % (name, ROI_NAME)), mask)
    return {
        "folder": str(root),
        "tables": str(tables),
        "track_table": str(tables / "merged_Tracks.csv"),
        "spot_table": str(tables / "merged_Spots.csv"),
        "roi": str(roi),
        "results": str(work / "ctc_results"),
        "n_tracks": len(tracks),
        "n_spots": len(spots),
        "dims": dims,
    }


def _write_trackmate(folder: Path, table: pd.DataFrame) -> None:
    """FOV1_spots.csv and FOV1_tracks.csv: a header, three descriptive rows (names, short names, units) that the loader skips (skiprows 1-3), then the data."""
    spots = table.assign(
        LABEL="ID" + table["TRACK_ID"].astype(str),
        ID=range(len(table)),
        QUALITY=1.0,
        POSITION_Z=0.0,
        FRAME=table["POSITION_T"].astype(int),
    )
    spots = spots[
        [
            "LABEL",
            "ID",
            "TRACK_ID",
            "QUALITY",
            "POSITION_X",
            "POSITION_Y",
            "POSITION_Z",
            "POSITION_T",
            "FRAME",
        ]
    ]
    descriptive = [
        ["Label", "Spot ID", "Track ID", "Quality", "X", "Y", "Z", "T", "Frame"],
        [
            "Label",
            "ID",
            "TRACK_ID",
            "QUALITY",
            "POSITION_X",
            "POSITION_Y",
            "POSITION_Z",
            "POSITION_T",
            "FRAME",
        ],
        ["", "", "", "", "(micron)", "(micron)", "(micron)", "(sec)", ""],
    ]
    tracks = pd.DataFrame(
        {
            "LABEL": ["Track_%d" % i for i in sorted(table["TRACK_ID"].unique())],
            "TRACK_ID": sorted(table["TRACK_ID"].unique()),
            "NUMBER_SPOTS": N_SPOTS,
        }
    )
    track_descriptive = [
        ["Label", "Track ID", "Number of spots"],
        ["Label", "TRACK_ID", "NUMBER_SPOTS"],
        ["", "", "(count)"],
    ]
    for frame, rows, name in (
        (spots, descriptive, "FOV1_spots.csv"),
        (tracks, track_descriptive, "FOV1_tracks.csv"),
    ):
        with open(folder / name, "w", encoding="utf-8", newline="") as handle:
            handle.write(",".join(frame.columns) + "\n")
            for row in rows:
                handle.write(",".join(row) + "\n")
            frame.to_csv(handle, header=False, index=False)


def read_table(path: Path) -> pd.DataFrame:
    """A CSV table whatever its name: the app writes gzip content even into files called .csv (checked by the gzip magic bytes, not by the extension)."""
    with open(path, "rb") as handle:
        gzipped = handle.read(2) == b"\x1f\x8b"
    return pd.read_csv(path, low_memory=False, compression="gzip" if gzipped else None)


def load_stage(fields: dict[str, Any], note: str = "") -> str:
    """Kernel code for the loading cell: set the widgets by variable name, untick 'Use test dataset' (its default downloads a Zenodo archive), press every new button (Submit; the native
    Find folder / Find file buttons become HUMAN lines)."""
    code = "I = lcnb.INPUTS\n"
    for name, value in fields.items():
        code += "lcnb.set_value(lcnb.find(var=%r), %s)\n" % (
            name,
            value if isinstance(value, str) and value.startswith("I[") else repr(value),
        )
    code += (
        "if 'Use_test_dataset_widget' in get_ipython().user_ns:\n"
        "    lcnb.set_value(lcnb.find(var='Use_test_dataset_widget'), False)\n"
        "    lcnb.human('click_zenodo_test_dataset', 'the default \"Use test dataset\" downloads T_Cells_spots_only.zip from Zenodo (up to 10 minutes): not used, the synthetic dataset is loaded instead')\n"
        "lcnb.auto_drive('load')\n"
    )
    return code + note


def truth_metrics(dataset: dict[str, Any]) -> pd.DataFrame:
    """Expected per-track metrics from the construction (speed = step, dt = 1)."""
    rows = []
    spots = pd.read_csv(dataset["spot_table"])
    for unique_id, group in spots.groupby("Unique_ID"):
        step = STEPS[group["Condition"].iloc[0]]
        rows.append(
            {
                "Unique_ID": unique_id,
                "Track Duration": N_SPOTS - 1,
                "Mean Speed": step,
                "Total Distance Traveled": step * (N_SPOTS - 1),
                "Directionality": 1.0,
            }
        )
    return pd.DataFrame(rows).set_index("Unique_ID")


def spots_rows(results: Path, dataset: dict[str, Any], label: str = "load") -> list[tuple[str, str, str]]:
    """The loaded spots table saved by the loader: all the spots and only the conditions that exist."""
    path = results / "merged_Spots.csv.gz"
    if not path.is_file():
        return [(label + "_spots_file", "FAIL", "%s was not written by the loading step" % path)]
    spots = pd.read_csv(path, low_memory=False)
    ok = (
        len(spots) == dataset["n_spots"]
        and set(spots["Condition"].astype(str)) == set(STEPS)
        and spots["Unique_ID"].nunique() == dataset["n_tracks"]
    )
    return [
        (
            label + "_spots_file",
            "PASS" if ok else "FAIL",
            "%s: %d rows (expected %d), conditions %s, %d tracks (expected %d)"
            % (
                path.name,
                len(spots),
                dataset["n_spots"],
                sorted(set(spots["Condition"].astype(str))),
                spots["Unique_ID"].nunique(),
                dataset["n_tracks"],
            ),
        )
    ]


def metric_rows(results: Path, dataset: dict[str, Any], label: str = "metrics") -> list[tuple[str, str, str]]:
    """merged_Tracks.csv.gz after Part 4: duration, mean speed, distance and directionality equal the values known from the construction."""
    path = results / "merged_Tracks.csv.gz"
    if not path.is_file():
        return [(label + "_tracks_file", "FAIL", "%s was not written" % path)]
    tracks = read_table(path).set_index("Unique_ID")
    truth = truth_metrics(dataset)
    rows = []
    for column in truth.columns:
        if column not in tracks.columns:
            rows.append(
                (
                    label + "_" + column.replace(" ", "_"),
                    "FAIL",
                    "column %r is not in %s (columns: %s)" % (column, path.name, list(tracks.columns)[:12]),
                )
            )
            continue
        joined = tracks[column].reindex(truth.index)
        ok = bool(
            np.allclose(
                joined.to_numpy(float), truth[column].to_numpy(float), rtol=1e-6, atol=1e-9, equal_nan=False
            )
        )
        rows.append(
            (
                label + "_" + column.replace(" ", "_"),
                "PASS" if ok else "FAIL",
                "%s: max abs error %.3g over %d tracks"
                % (
                    column,
                    float(np.nanmax(np.abs(joined.to_numpy(float) - truth[column].to_numpy(float)))),
                    len(truth),
                ),
            )
        )
    return rows


def files_rows(results: Path, patterns: dict[str, int], label: str) -> list[tuple[str, str, str]]:
    """Each glob of `patterns` (relative to the Results folder) must match at least that many non-empty files."""
    rows = []
    for pattern, minimum in patterns.items():
        found = [p for p in results.glob(pattern) if p.is_file() and p.stat().st_size > 0]
        rows.append(
            (
                "%s_%s" % (label, pattern.replace("/", "_").replace("*", "x").replace(".", "_")),
                "PASS" if len(found) >= minimum else "FAIL",
                "%d non-empty files match %s under %s (need %d)" % (len(found), pattern, results, minimum),
            )
        )
    return rows


WELLS = {"A01": "Control", "A02": "Control", "B01": "Mutant", "B02": "Mutant"}


def make_plate(work: Path) -> dict[str, Any]:
    """A TrackMate plate export: <Well>_1-spots.csv and <Well>_1-tracks.csv in one folder (wells A01 A02 -> Control, B01 B02 -> Mutant, to be mapped by the notebook's own widgets)."""
    rng = np.random.default_rng(23)
    root = work / "ctc_plate"
    root.mkdir(parents=True, exist_ok=True)
    for well, condition in WELLS.items():
        step = STEPS[condition]
        frames = []
        for track in range(1, N_TRACKS + 1):
            angle = rng.uniform(0.1, np.pi / 2 - 0.1)
            x0, y0 = rng.uniform(5, 50, 2)
            t = np.arange(N_SPOTS, dtype=float)
            frames.append(
                pd.DataFrame(
                    {
                        "TRACK_ID": track,
                        "POSITION_X": x0 + step * np.cos(angle) * t,
                        "POSITION_Y": y0 + step * np.sin(angle) * t,
                        "POSITION_T": t,
                    }
                )
            )
        table = pd.concat(frames, ignore_index=True)
        folder = root
        spots = table.assign(
            LABEL="ID" + table["TRACK_ID"].astype(str),
            ID=range(len(table)),
            QUALITY=1.0,
            POSITION_Z=0.0,
            FRAME=table["POSITION_T"].astype(int),
        )
        spots = spots[
            [
                "LABEL",
                "ID",
                "TRACK_ID",
                "QUALITY",
                "POSITION_X",
                "POSITION_Y",
                "POSITION_Z",
                "POSITION_T",
                "FRAME",
            ]
        ]
        tracks = pd.DataFrame(
            {
                "LABEL": ["Track_%d" % i for i in range(1, N_TRACKS + 1)],
                "TRACK_ID": range(1, N_TRACKS + 1),
                "NUMBER_SPOTS": N_SPOTS,
            }
        )
        for frame, rows, name in (
            (
                spots,
                [
                    ["Label", "Spot ID", "Track ID", "Quality", "X", "Y", "Z", "T", "Frame"],
                    [
                        "Label",
                        "ID",
                        "TRACK_ID",
                        "QUALITY",
                        "POSITION_X",
                        "POSITION_Y",
                        "POSITION_Z",
                        "POSITION_T",
                        "FRAME",
                    ],
                    ["", "", "", "", "(micron)", "(micron)", "(micron)", "(sec)", ""],
                ],
                "%s_1-spots.csv" % well,
            ),
            (
                tracks,
                [
                    ["Label", "Track ID", "Number of spots"],
                    ["Label", "TRACK_ID", "NUMBER_SPOTS"],
                    ["", "", "(count)"],
                ],
                "%s_1-tracks.csv" % well,
            ),
        ):
            with open(folder / name, "w", encoding="utf-8", newline="") as handle:
                handle.write(",".join(frame.columns) + "\n")
                for row in rows:
                    handle.write(",".join(row) + "\n")
                frame.to_csv(handle, header=False, index=False)
    return {
        "folder": str(root),
        "results": str(work / "ctc_plate_results"),
        "n_tracks": N_TRACKS * len(WELLS),
        "n_spots": N_TRACKS * N_SPOTS * len(WELLS),
    }


def condition_speed_rows(results: Path, label: str = "plate_metrics") -> list[tuple[str, str, str]]:
    """Plate notebook: mean speed per mapped Condition equals the speed the wells were built with (Control 1.0, Mutant 2.0), 16 tracks each."""
    paths = sorted(results.glob("merged_Tracks.csv*"))
    if not paths:
        return [(label + "_tracks_file", "FAIL", "no merged_Tracks.csv* under %s" % results)]
    tracks = read_table(paths[-1])
    if "Mean Speed" not in tracks.columns:
        return [
            (
                label + "_mean_speed",
                "FAIL",
                "%s has no 'Mean Speed' column (columns %s)" % (paths[-1].name, list(tracks.columns)[:12]),
            )
        ]
    by = tracks.groupby("Condition")["Mean Speed"].agg(["mean", "count"])
    ok = set(by.index) == set(STEPS) and all(
        abs(by.loc[c, "mean"] - STEPS[c]) < 1e-6 and by.loc[c, "count"] == 16 for c in STEPS if c in by.index
    )
    return [
        (
            label + "_mean_speed_by_condition",
            "PASS" if ok else "FAIL",
            "per Condition mean speed / tracks: %s (expected Control 1.0 and Mutant 2.0, 16 tracks each)"
            % by.round(4).to_dict("index"),
        )
    ]
