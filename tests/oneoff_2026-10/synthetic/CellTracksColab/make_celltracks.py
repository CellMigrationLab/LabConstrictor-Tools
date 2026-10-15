#!/usr/bin/env python3
"""Synthetic tracking tables with KNOWN speed, direction and length for CellTracksColab `calculate_metrics`.

    python make_celltracks.py OUT_DIR            # standalone (needs numpy, pandas, tifffile; common.py and check_ground_truth.py next to it or one folder up)

Every track is BUILT from its steps (a step length, a direction, a time gap), so the right answer is known by construction and is
computed here with plain Python (`statistics`), not with the code under test. Truth per track: Track Duration, the speeds of the
steps (mean, median, max, min, population standard deviation: the definition of the notebooks' `Track_Metrics.py`), the path length
and Directionality = |net displacement| / path length.
"""

from __future__ import annotations

import math
import random
import statistics
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
from common import Suite, chk_message, chk_status, chk_table, standalone_main  # noqa: E402

APP, VERSION = "CellTracksColab", "1.1.2"
METRIC_COLUMNS = [
    "Track Duration",
    "Median Speed",
    "Mean Speed",
    "Max Speed",
    "Min Speed",
    "Speed Standard Deviation",
    "Total Distance Traveled",
    "Directionality",
]
COMPARED = list(METRIC_COLUMNS)


class Track:
    """A track built from steps: `lengths[k]` and `directions[k]` (a unit vector) for the step k, taken in `dts[k]` time units."""

    def __init__(
        self,
        ident: Any,
        start: Sequence[float],
        t0: float,
        dts: Sequence[float],
        lengths: Sequence[float],
        directions: Sequence[Sequence[float]],
    ) -> None:
        self.ident, self.dts, self.lengths = ident, list(dts), list(lengths)
        self.times = [t0]
        self.points = [tuple(float(v) for v in start)]
        for dt, length, d in zip(dts, lengths, directions):
            self.times.append(self.times[-1] + dt)
            self.points.append(tuple(p + length * c for p, c in zip(self.points[-1], d)))

    def truth(self) -> dict[str, float]:
        speeds = [length / dt for length, dt in zip(self.lengths, self.dts)]
        path = math.fsum(self.lengths)
        net = math.dist(self.points[0], self.points[-1])
        return {
            "Track Duration": math.fsum(self.dts),
            "Median Speed": statistics.median(speeds),
            "Mean Speed": math.fsum(speeds) / len(speeds),
            "Max Speed": max(speeds),
            "Min Speed": min(speeds),
            "Speed Standard Deviation": statistics.pstdev(speeds),
            "Total Distance Traveled": path,
            "Directionality": net / path if path else 0.0,
        }


def unit(azimuth_deg: float, elevation_deg: float = 0.0) -> tuple[float, float, float]:
    """Unit vector (x, y, z) from an azimuth in the XY plane and an elevation towards Z."""
    a, e = math.radians(azimuth_deg), math.radians(elevation_deg)
    return math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)


def straight(
    ident: Any,
    n: int,
    speed: float,
    azimuth: float,
    elevation: float = 0.0,
    dt: float = 1.0,
    t0: float = 0.0,
    start: Sequence[float] = (0.0, 0.0, 0.0),
) -> Track:
    return Track(
        ident, start, t0, [dt] * (n - 1), [speed * dt] * (n - 1), [unit(azimuth, elevation)] * (n - 1)
    )


def frame(tracks: Sequence[Track], id_column: str = "Unique_ID", with_z: bool = True) -> pd.DataFrame:
    rows = [
        {
            id_column: tr.ident,
            "POSITION_T": t,
            "POSITION_X": p[0],
            "POSITION_Y": p[1],
            **({"POSITION_Z": p[2]} if with_z else {}),
        }
        for tr in tracks
        for t, p in zip(tr.times, tr.points)
    ]
    return pd.DataFrame(rows)


def truth_frame(tracks: Sequence[Track], id_column: str) -> pd.DataFrame:
    return pd.DataFrame([{id_column: tr.ident, **tr.truth()} for tr in tracks])


def message_for(tracks: int, skipped: int, dropped: int, no_z: bool = False) -> str:
    text = "%d tracks, %d skipped (fewer than 2 spots), %d rows dropped (NaN)" % (tracks, skipped, dropped)
    return text + (". No POSITION_Z: treated as 2D (Z = 0)" if no_z else "")


def cells(tracks: Sequence[Track], rows: Sequence[int] = (0, 1)) -> dict[str, float]:
    """`cells` of a table expectation for the given row positions (tracks in the order of the table: sorted by id)."""
    out: dict[str, float] = {}
    for row in rows:
        t = tracks[row].truth()
        for column in ("Track Duration", "Mean Speed", "Total Distance Traveled", "Directionality"):
            out["%s[%d]" % (column, row)] = t[column]
    return out


class Builder:
    """Writes one CSV + its truth CSV and registers the dataset."""

    def __init__(self, suite: Suite) -> None:
        self.s = suite
        (suite.out / "truth").mkdir(exist_ok=True)

    def csv(self, name: str, table: pd.DataFrame) -> Path:
        path = self.s.fixtures / (name + ".csv")
        table.to_csv(path, index=False)
        return path

    def works(
        self,
        ident: str,
        purpose: str,
        tracks: Sequence[Track],
        derivation: str,
        table: pd.DataFrame | None = None,
        *,
        id_column: str = "Unique_ID",
        skipped: int = 0,
        dropped: int = 0,
        no_z: bool = False,
        text: str = "",
        extra_inputs: dict[str, Any] | None = None,
    ) -> None:
        tracks = sorted(tracks, key=lambda t: str(t.ident))
        data = frame(tracks, id_column, with_z=not no_z) if table is None else table
        path = self.csv(ident, data)
        truth_path = self.s.out / "truth" / (ident + "_metrics.csv")
        truth_frame(tracks, id_column).to_csv(truth_path, index=False)
        message = message_for(len(tracks), skipped, dropped, no_z)
        expect = {
            "progress_events_min": 1,
            "results": {
                "table": {
                    "columns": [id_column] + METRIC_COLUMNS,
                    "rows": len(tracks),
                    "cells": cells(tracks, range(min(3, len(tracks)))),
                },
                "summary": {"contains": message},
            },
        }
        inputs = {"tracks": self.s.rel(path), **(extra_inputs or {})}
        checks = [
            chk_status("COMPLETE"),
            chk_table(
                "table", id_column, self.s.rel(truth_path), COMPARED, rtol=1e-9, atol=1e-9, rows=len(tracks)
            ),
            chk_message("summary", message),
        ]
        self.s.dataset(
            ident,
            purpose,
            "works",
            derivation=derivation,
            files=[path, truth_path],
            tool="calculate_metrics",
            inputs=inputs,
            expect=expect,
            checks=checks,
            outcome_text=text or "table equals the truth; " + message,
        )

    def refused(
        self,
        ident: str,
        purpose: str,
        text: str,
        derivation: str,
        code: str | None,
        contains: str | None,
        *,
        table: pd.DataFrame | None = None,
        raw: str | None = None,
        extra_inputs: dict[str, Any] | None = None,
        outcome: str = "refused",
    ) -> None:
        path = self.s.fixtures / (ident + ".csv")
        if raw is not None:
            path.write_text(raw, encoding="utf-8")
        else:
            assert table is not None
            table.to_csv(path, index=False)
        expect: dict[str, Any] = {"status": "FAILED"}
        if code:
            expect["code"] = code
        if contains:
            expect["message_contains"] = contains
        self.s.dataset(
            ident,
            purpose,
            outcome,
            derivation=derivation,
            files=[path],
            tool="calculate_metrics",
            inputs={"tracks": self.s.rel(path), **(extra_inputs or {})},
            expect=expect,
            checks=[chk_status("FAILED", code, contains)],
            outcome_text=text,
        )


def build(out: Path) -> Suite:
    suite = Suite(APP, out, VERSION)
    b = Builder(suite)
    rng = random.Random(20261014)

    speeds, azimuths, ns = [0.5, 1.0, 2.0, 3.5, 7.0, 10.0], [0, 30, 90, 135, 225, 300], [5, 8, 10, 3, 20, 50]
    linear = [
        straight("T%02d" % i, ns[i], speeds[i], azimuths[i], start=(10 * i, -5 * i, 0)) for i in range(6)
    ]
    b.works(
        "ct_linear_2d",
        "straight tracks in the XY plane, speeds 0.5..10, 3..50 spots, one time unit per frame",
        linear,
        "Each track is a straight line walked at constant speed v: Duration = (n-1) dt, every step speed = v (mean = median = max = min, SD = 0), path = (n-1) v dt, "
        "Directionality = 1.",
    )
    b.works(
        "ct_linear_3d",
        "straight tracks with a Z component (azimuth and elevation), POSITION_Z present",
        [straight("T%02d" % i, 6 + i, 1.5 + i, 40 * i, 15 * i + 10, start=(i, i, i)) for i in range(5)],
        "A straight 3D line at speed v: the step length is v dt in 3D, so a tool that ignores POSITION_Z would report v cos(elevation) instead.",
    )
    b.works(
        "ct_time_units",
        "time in seconds (dt = 2.5 s, start 10 s), positions in micrometres: speeds are um per second",
        [straight("S%d" % i, 7, v, 20 * i, dt=2.5, t0=10.0) for i, v in enumerate([0.2, 0.8, 1.6])],
        "Speed = step length / time step in the units of the file (um/s). A tool that divided by frames instead would report 2.5 times too much. Duration = 6 x 2.5 = 15 s.",
    )
    # irregular time steps: speeds of the steps are exactly 1..5
    irregular = Track(
        "I1", (0, 0, 0), 0.0, [0.5, 1, 2, 0.25, 1], [0.5 * 1, 1 * 2, 2 * 3, 0.25 * 4, 1 * 5], [unit(10)] * 5
    )
    b.works(
        "ct_irregular_dt",
        "irregular time steps (0.5, 1, 2, 0.25, 1) with per-step speeds exactly 1, 2, 3, 4, 5",
        [irregular],
        "Convention (the notebooks' Track_Metrics.py, not independent): Mean Speed is the MEAN OF THE PER-STEP SPEEDS = 3, median 3, max 5, min 1, population SD sqrt(2); "
        "path/duration would give 3.0526. Total distance = 0.5+2+6+1+5 = 14.5, Duration 4.75, Directionality 1.",
    )
    b.works(
        "ct_zigzag",
        "out-and-back tracks: net displacement 0 (even steps) and s (odd steps)",
        [
            Track("Z4", (0, 0, 0), 0, [1] * 4, [2.0] * 4, [(1, 0, 0), (-1, 0, 0)] * 2),
            Track("Z3", (0, 0, 0), 0, [1] * 3, [2.0] * 3, [(1, 0, 0), (-1, 0, 0), (1, 0, 0)]),
        ],
        "Steps of 2 alternating +x/-x: after 4 steps the track is back at the start (Directionality 0, path 8); after 3 steps net = 2, path = 6 (Directionality 1/3).",
    )
    r, dtheta = 10.0, 15.0
    chord = 2 * r * math.sin(math.radians(dtheta / 2))

    def arc(ident: str, steps: int) -> Track:
        dirs = [
            unit(dtheta * k + 90 + dtheta / 2) for k in range(steps)
        ]  # chord k points along the tangent at the middle of its arc
        return Track(ident, (r, 0, 0), 0, [1.0] * steps, [chord] * steps, dirs)

    b.works(
        "ct_circle",
        "tracks on a circle of radius 10 (15 degrees per step): a full turn and a half turn",
        [arc("C_full", 24), arc("C_half", 12)],
        "Chord = 2 R sin(dtheta/2) = %.6f per step. Full turn: 24 chords, net displacement 0 -> Directionality 0. Half turn: net = 2R = 20, path = 12 chords -> Directionality %.6f."
        % (chord, 20 / (12 * chord)),
    )
    ramp = Track("R1", (0, 0, 0), 0, [1.0] * 10, [float(k) for k in range(1, 11)], [unit(0)] * 10)
    b.works(
        "ct_speed_ramp",
        "step lengths 1, 2, ..., 10 at dt = 1 (acceleration): mean 5.5, median 5.5, max 10, min 1, population SD sqrt(8.25)",
        [ramp],
        "Speeds 1..10: mean 5.5, median 5.5, max 10, min 1; SD with ddof = 0 (numpy's default, as in the notebook) = sqrt((10^2-1)/12) = 2.8723; the sample SD (ddof 1) would be 3.0277. "
        "Path 55 = Total Distance.",
    )
    shuffled = frame(linear)
    shuffled = shuffled.sample(frac=1.0, random_state=7).reset_index(drop=True)
    b.works(
        "ct_unsorted",
        "the rows of ct_linear_2d shuffled (time not sorted inside the file)",
        linear,
        "Same tracks as ct_linear_2d, rows in random order: the tool must order the spots by POSITION_T inside each track, so the truth is identical.",
        table=shuffled,
    )

    four_single = [straight("T%02d" % i, 2 + i, 1.0 + i, 50 * i) for i in range(3)]
    singles = [Track("U%d" % i, (i, i, 0), 0, [], [], []) for i in range(4)]
    b.works(
        "ct_single_spot",
        "three normal tracks and four tracks with a single spot (no speed exists)",
        four_single,
        "A speed needs two spots: the four single-spot tracks are skipped (not in the table, counted in the message). The three others are straight lines.",
        table=frame(four_single + singles),
        skipped=4,
    )
    a = straight("A", 6, 2.0, 0)
    nan_a = frame([a])
    nan_a.loc[[1, 3], "POSITION_X"] = np.nan
    bt = straight("B", 2, 1.0, 90)
    nan_b = frame([bt])
    nan_b.loc[1, "POSITION_Y"] = np.nan
    c = straight("C", 4, 1.0, 45)
    nan_a_expected = Track(
        "A", (0, 0, 0), 1.0 - 1.0, [2, 2, 1], [4.0, 4.0, 2.0], [unit(0)] * 3
    )  # the spots at t = 0, 2, 4, 5 remain
    b.works(
        "ct_nan_rows",
        "empty positions in some rows: 2 rows of track A (6 spots, speed 2) and 1 row of the 2-spot track B",
        [nan_a_expected, c],
        "Rows with an empty position are dropped first (3 rows). A keeps t = 0, 2, 4, 5: steps of 4 in 2 frames, 4 in 2, 2 in 1 -> every speed 2, Duration 5, path 10, Directionality 1. "
        "B keeps 1 spot -> skipped. C is a straight line.",
        table=pd.concat([nan_a, nan_b, frame([c])], ignore_index=True),
        skipped=1,
        dropped=3,
    )
    flat2d = [straight("T%02d" % i, 5 + i, 1.0 + i, 60 * i) for i in range(3)]
    b.works(
        "ct_no_z",
        "2D data without a POSITION_Z column",
        flat2d,
        "No POSITION_Z: Z = 0 for every spot; the speeds are the 2D speeds.",
        no_z=True,
    )
    zempty = frame(flat2d)
    zempty["POSITION_Z"] = np.nan
    b.works(
        "ct_z_column_empty",
        "a POSITION_Z column that is empty everywhere (TrackMate 2D export)",
        flat2d,
        "A POSITION_Z column with no value at all is treated as absent (2D); the rows are not dropped.",
        table=zempty,
        no_z=True,
    )
    big_tracks = [
        straight(
            "T%04d" % i,
            50,
            rng.uniform(0.05, 20.0),
            rng.uniform(0, 360),
            rng.uniform(-60, 60),
            dt=rng.choice([0.5, 1.0, 2.0]),
            t0=rng.uniform(0, 10),
            start=(rng.uniform(-100, 100), rng.uniform(-100, 100), rng.uniform(-20, 20)),
        )
        for i in range(2000)
    ]
    b.works(
        "ct_large",
        "stress: 2000 straight 3D tracks of 50 spots (100 000 rows, random speed, direction, time step)",
        big_tracks,
        "Every track is a straight line at a random constant speed: the full table is compared with the construction (2000 rows).",
        id_column="Unique_ID",
    )

    # ---- raw TrackMate-like columns
    tm = frame(linear[:3], "TRACK_ID", with_z=True).rename(columns={"POSITION_T": "POSITION_T"})
    tm.insert(0, "LABEL", ["ID%d" % i for i in range(len(tm))])
    tm["FRAME"] = tm["POSITION_T"].astype(int)
    b.works(
        "ct_trackmate_columns",
        "TrackMate-like columns (LABEL, TRACK_ID, FRAME, extra columns) with track_id_column = TRACK_ID",
        linear[:3],
        "Extra columns are ignored; the id column is chosen by the parameter. The truth is that of the three straight tracks.",
        table=tm,
        id_column="TRACK_ID",
        extra_inputs={"track_id_column": "TRACK_ID"},
    )
    header_rows = tm.copy().astype(object)
    desc = [
        {
            "LABEL": "Label",
            "TRACK_ID": "Track ID",
            "POSITION_T": "T",
            "POSITION_X": "X",
            "POSITION_Y": "Y",
            "POSITION_Z": "Z",
            "FRAME": "Frame",
        },
        {
            "LABEL": "Label",
            "TRACK_ID": "TRACK_ID",
            "POSITION_T": "POSITION_T",
            "POSITION_X": "POSITION_X",
            "POSITION_Y": "POSITION_Y",
            "POSITION_Z": "POSITION_Z",
            "FRAME": "FRAME",
        },
        {
            "LABEL": "",
            "TRACK_ID": "",
            "POSITION_T": "frame",
            "POSITION_X": "pixel",
            "POSITION_Y": "pixel",
            "POSITION_Z": "pixel",
            "FRAME": "",
        },
    ]
    raw = pd.concat([pd.DataFrame(desc), header_rows], ignore_index=True)
    b.refused(
        "ct_trackmate_raw_header_rows",
        "a raw TrackMate spot export: three descriptive rows (names, short names, units) below the header; the units row has an empty TRACK_ID",
        "HUMAN: product decision. Prediction from the source: refused with missing_track_id (the descriptive rows have no usable id); the notebook loader drops these rows",
        "The correct behaviour is not defined by the spec: a raw TrackMate file either works (the 3 rows dropped, truth = ct_trackmate_columns) or is refused with a sentence that names those rows. "
        "Silent wrong tracks are the failure to look for.",
        "missing_track_id",
        "empty TRACK_ID",
        table=raw,
        extra_inputs={"track_id_column": "TRACK_ID"},
        outcome="HUMAN",
    )

    # ---- must be refused
    two = frame(linear[:2])
    b.refused(
        "ct_missing_column",
        "the POSITION_Y column is missing",
        "refused: missing_columns, names POSITION_Y",
        "A required column is absent.",
        "missing_columns",
        "POSITION_Y",
        table=two.drop(columns=["POSITION_Y"]),
    )
    blank = two.copy().astype(object)
    blank.loc[[0, 2], "Unique_ID"] = None
    b.refused(
        "ct_empty_id",
        "two rows without a track id",
        "refused: missing_track_id, counts the rows",
        "Rows without an id would silently vanish from a group-by.",
        "missing_track_id",
        "2 row(s) have an empty Unique_ID",
        table=blank,
    )
    b.refused(
        "ct_wrong_id_column",
        "a TRACK_ID file given with the default id column (Unique_ID)",
        "refused: missing_columns, hint to set track_id_column",
        "The default id column is absent.",
        "missing_columns",
        "track_id_column",
        table=frame(linear[:2], "TRACK_ID"),
    )
    b.refused(
        "ct_all_single_spot",
        "every track has one spot",
        "refused: no_result",
        "No track has two spots: nothing to compute.",
        "no_result",
        "No track has 2 or more spots",
        table=frame(singles),
    )
    b.refused(
        "ct_header_only",
        "a table with the header and no row",
        "refused with a sentence",
        "Zero rows: nothing to compute.",
        None,
        None,
        table=two.iloc[0:0],
    )
    b.refused(
        "ct_empty_file",
        "an empty file (0 bytes)",
        "refused: unreadable_table",
        "No header, no data.",
        "unreadable_table",
        None,
        raw="",
    )
    text = two.copy().astype(object)
    for col in ("POSITION_X", "POSITION_Y"):
        text[col] = text[col].map(lambda v: ("%.2f" % v).replace(".", ","))
    b.refused(
        "ct_decimal_comma",
        "numbers written with a decimal comma inside quotes (a European spreadsheet export)",
        "refused (or read correctly): not silently dropped to nothing",
        "'1,50' is not a number for the reader: the positions become empty and every row is dropped; a clear refusal is expected, never a table.",
        None,
        None,
        table=text,
    )
    nan_all = two.copy()
    nan_all[["POSITION_X", "POSITION_Y", "POSITION_Z"]] = np.nan
    b.refused(
        "ct_all_nan_positions",
        "every position is empty",
        "refused: no_result",
        "All rows are dropped.",
        "no_result",
        "dropped because of empty values",
        table=nan_all,
    )
    inf = frame([straight("A", 5, 1.0, 0)])
    inf.loc[2, "POSITION_X"] = np.inf
    b.refused(
        "ct_inf_position",
        "one position is infinite",
        "refused (or the row dropped and said so): an infinite speed must never be returned",
        "An infinite coordinate is not a measurement. A table with inf or NaN speeds is a silent wrong result.",
        None,
        None,
        table=inf,
    )
    dup = Track(
        "D", (0, 0, 0), 0, [1.0, 0.0, 1.0], [1.0, 1.0, 1.0], [unit(0)] * 3
    )  # the middle step has no time
    dup_path = b.csv("ct_duplicate_time", frame([dup]))
    suite.dataset(
        "ct_duplicate_time",
        "two spots of one track at the same time (the middle step has dt = 0)",
        "HUMAN",
        derivation="A speed over a zero time step is undefined (1 / 0). A sane tool refuses, drops the repeated spot or says so; the notebook code replaces dt = 0 by 1e-10 "
        "(a speed of 1e10). The check only requires that no absurd speed is reported (Max Speed below 1e6).",
        files=[dup_path],
        tool="calculate_metrics",
        inputs={"tracks": suite.rel(dup_path)},
        expect={"status": "COMPLETE"},
        checks=[{"kind": "table_bound", "result": "table", "column": "Max Speed", "maximum": 1e6}],
        outcome_text="HUMAN: whether to refuse or to drop the repeated spot is a product decision; the check fails on a 1e10 speed",
    )
    return suite


if __name__ == "__main__":
    sys.exit(standalone_main(build, HERE, __doc__ or ""))
