"""Playground datasets of the tool feature_tour: lattice discs with exact centres and areas, regions, refusals and a stress image."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
from common import (  # noqa: E402
    Suite,
    chk_host,
    chk_message,
    chk_status,
    chk_table,
    chk_value,
    disc_pixels,
)

BACKGROUND, FOREGROUND = 20, 200


from pg_common import count_case, put  # noqa: E402


# ------------------------------------------------------------------------------------------------ discs for feature_tour
def disc_scene(
    shape: tuple[int, int],
    discs: Sequence[tuple[int, int, float]],
    rings: Sequence[tuple[int, int, float, float]],
    seed: int,
) -> tuple[np.ndarray, list[dict[str, Any]]]:
    """uint8 image: background 20, discs and rings 200, Gaussian noise (sd 3). Returns the image and the truth rows in the raster order
    of scipy.ndimage.label (the blob whose first pixel comes first in row-major order gets label 1)."""
    clean = np.full(shape, BACKGROUND, np.float64)
    blobs: list[np.ndarray] = []
    for cy, cx, r in discs:
        blobs.append(disc_pixels(shape, cy, cx, r))
    for cy, cx, outer, inner in rings:
        blobs.append(disc_pixels(shape, cy, cx, outer) & ~disc_pixels(shape, cy, cx, inner))
    for mask in blobs:
        clean[mask] = FOREGROUND
    noisy = np.clip(clean + np.random.default_rng(seed).normal(0, 3, shape), 0, 255).round().astype(np.uint8)
    centres = [(cy, cx) for cy, cx, _ in discs] + [(cy, cx) for cy, cx, _, _ in rings]
    order = sorted(range(len(blobs)), key=lambda i: int(np.argmax(blobs[i].ravel())))
    rows = [
        {
            "label": rank + 1,
            "y": float(centres[i][0]),
            "x": float(centres[i][1]),
            "area_px": int(blobs[i].sum()),
        }
        for rank, i in enumerate(order)
    ]
    return noisy, rows


def tour_checks(
    s: Suite, ident: str, rows: list[dict[str, Any]], count: int
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Checks and cases-expectation of a feature_tour run that must find the blobs `rows` (the truth CSV is written next to the dataset)."""
    truth = s.out / "truth" / (ident + "_measurements.csv")
    truth.parent.mkdir(exist_ok=True)
    pd.DataFrame(rows).to_csv(truth, index=False)
    checks = [
        chk_status("COMPLETE"),
        chk_table(
            "measurements", "label", s.rel(truth), ["y", "x", "area_px"], rtol=0.0, atol=1e-6, rows=count
        ),
        chk_message("summary", "Found **%d** blob(s)" % count),
    ]
    expect = {
        "max_seconds": 120,
        "results": {
            "summary": {"contains": "Found **%d** blob(s)" % count},
            "outlines": {"features": count},
            "centres": {"rows": count, "columns": ["y", "x", "label"]},
            "measurements": {"rows": count},
        },
    }
    return checks, expect


def add_discs(s: Suite) -> None:
    shape = (256, 256)
    discs = [
        (30, 40, 7),
        (28, 120, 9),
        (35, 210, 6),
        (80, 25, 8),
        (95, 150, 10),
        (110, 230, 7),
        (150, 70, 6),
        (160, 190, 9),
        (200, 30, 10),
        (215, 120, 7),
        (230, 215, 8),
        (130, 20, 5),
    ]
    rings = [(60, 80, 14, 6), (190, 160, 14, 6)]
    image, rows = disc_scene(shape, discs, rings, seed=101)
    files = put(s, "pg_discs", image, "YX", px=(0.5, 0.5), ome=True)
    checks, expect = tour_checks(s, "pg_discs", rows, len(rows))
    s.dataset(
        "pg_discs",
        "14 blobs (12 discs radius 5-10 and 2 rings with a hole) at known integer centres, noise sd 3",
        "works",
        derivation="Lattice discs: area = number of lattice points with d^2 <= r^2 (computed here), centre exactly the integer centre, ring = annulus (hole is background). Default threshold 0.5 "
        "and minimum size 20 keep all 14 (the smallest disc has 81 px). Labels are in the raster order of scipy.ndimage.label.",
        files=files,
        tool="feature_tour",
        inputs={"image": s.rel(files[0])},
        expect=expect,
        checks=checks,
        host={
            "calibration": {"pixel_um": 0.5, "unit": "um"},
            "points_layer": "centres must sit on the discs: world position = pixel index x 0.5 um (y, x); the centre of the first blob is (%g, %g) px"
            % (rows[0]["y"], rows[0]["x"]),
            "centres_px": [[r["y"], r["x"]] for r in rows],
        },
        calibration={"x_um": 0.5, "y_um": 0.5, "unit": "um"},
    )
    # region with a non-zero origin on both axes: only the blobs whose centre lies inside
    region = np.zeros(shape, np.int32)
    r0, r1, c0, c1 = 90, 250, 70, 240
    region[r0:r1, c0:c1] = 1
    rpath = s.fixtures / "pg_region_box.tif"
    from tifffile import imwrite

    imwrite(rpath, region)
    inside = [r for r in rows if r0 <= r["y"] < r1 and c0 <= r["x"] < c1]
    renum = [{**r, "label": i + 1} for i, r in enumerate(inside)]
    checks, expect = tour_checks(s, "pg_region_offset", renum, len(inside))
    checks[1]["key"] = None
    checks[1]["atol"] = 1e-6
    expect["results"]["summary"] = {"contains": "inside the region"}
    checks[2] = chk_message("summary", "inside the region")
    s.dataset(
        "pg_region_offset",
        "the same blobs, region = box rows 90-249, columns 70-239 (origin not at 0,0)",
        "works",
        derivation="A blob is kept when its centre lies inside the region: %d of %d. The reported centres stay in the pixels of the WHOLE image (not of the region's crop): a frame error "
        "would shift every centre by (90, 70)." % (len(inside), len(rows)),
        files=[files[0], rpath],
        tool="feature_tour",
        inputs={"image": s.rel(files[0]), "region": s.rel(rpath)},
        expect=expect,
        checks=checks,
        host={
            "selection": "draw a rectangle rows 90-249, columns 70-239 in the host and tick 'use the selection': the same %d blobs, centres in whole-image pixels"
            % len(inside)
        },
    )
    # blobs smaller than min_size are removed
    kept = [r for r in rows if r["area_px"] >= 150]
    kept = [{**r, "label": i + 1} for i, r in enumerate(kept)]
    checks, expect = tour_checks(s, "pg_discs_min_size", kept, len(kept))
    checks[1]["key"] = None
    s.dataset(
        "pg_discs_min_size",
        "min_size_px = 150 removes the small discs (areas known exactly)",
        "works",
        derivation="Blobs with area >= 150 px: %d of %d (areas from the rasterisation)."
        % (len(kept), len(rows)),
        files=[files[0]],
        tool="feature_tour",
        inputs={"image": s.rel(files[0]), "min_size_px": 150},
        expect=expect,
        checks=checks,
    )
    # dark blobs: the background is one component, every ring hole another
    dark_n = 1 + len(rings)
    s.dataset(
        "pg_discs_dark",
        "look_for = dark: the background and the two ring holes",
        "works",
        derivation="Pixels at or below the middle of the range are the background (one connected component) and the two ring holes (113 px each, enclosed by the 8 px wall): %d blobs."
        % dark_n,
        files=[files[0]],
        tool="feature_tour",
        inputs={"image": s.rel(files[0]), "look_for": "dark"},
        expect={"results": {"outlines": {"features": dark_n}, "centres": {"rows": dark_n}}},
        checks=[chk_status("COMPLETE"), chk_message("summary", "Found **%d** blob(s)" % dark_n)],
    )
    s.dataset(
        "pg_discs_none_found",
        "threshold 1.0 and min size 500: nothing qualifies",
        "refused",
        derivation="No blob reaches the top of the range with 500 px.",
        files=[files[0]],
        tool="feature_tour",
        inputs={"image": s.rel(files[0]), "threshold": 1.0, "min_size_px": 500},
        expect={"status": "FAILED", "code": "no_result", "message_contains": "No blob found"},
        checks=[chk_status("FAILED", "no_result", "No blob found")],
        outcome_text="refused: no_result 'No blob found'",
    )
    empty = s.fixtures / "pg_region_empty.tif"
    imwrite(empty, np.zeros(shape, np.int32))
    wrong = s.fixtures / "pg_region_wrong_size.tif"
    imwrite(wrong, np.ones((100, 100), np.int32))
    for ident, path, code, text in (
        ("pg_region_empty", empty, "empty_region", "empty"),
        ("pg_region_wrong_size", wrong, "bad_input", "size of the image"),
    ):
        s.dataset(
            ident,
            "a selection that is %s"
            % ("empty" if "empty" in ident else "of the wrong size (100x100 for a 256x256 image)"),
            "refused",
            derivation="The region must be non-empty and the size of the image.",
            files=[path],
            tool="feature_tour",
            inputs={"image": s.rel(files[0]), "region": s.rel(path)},
            expect={"status": "FAILED", "code": code, "message_contains": text},
            checks=[chk_status("FAILED", code, text)],
            outcome_text="refused: %s" % code,
        )
    s.dataset(
        "pg_threshold_out_of_range",
        "threshold 1.5 (declared range 0..1)",
        "refused",
        derivation="A value beyond the declared maximum is refused before the tool runs.",
        files=[files[0]],
        tool="feature_tour",
        inputs={"image": s.rel(files[0]), "threshold": 1.5},
        expect={"status": "FAILED", "code": "invalid_parameter", "message_contains": "must be <="},
        checks=[chk_status("FAILED", "invalid_parameter", "must be <=")],
        outcome_text="refused: invalid_parameter",
    )
    flat = put(s, "pg_flat_zero", np.zeros(shape, np.uint8), "YX", px=(0.5, 0.5))[0]
    s.dataset(
        "pg_flat_zero",
        "an all-zero image",
        "refused",
        derivation="Nothing to find in a flat image.",
        files=[flat],
        tool="feature_tour",
        inputs={"image": s.rel(flat)},
        expect={"status": "FAILED", "code": "no_result", "message_contains": "flat"},
        checks=[chk_status("FAILED", "no_result", "flat")],
        outcome_text="refused: no_result 'flat'",
    )
    nan_img = image.astype(np.float32)
    nan_img[10:14, 10:14] = np.nan
    nan = put(s, "pg_nan_float", nan_img, "YX", px=(0.5, 0.5))[0]
    s.dataset(
        "pg_nan_float",
        "a float image with a block of NaN",
        "refused",
        derivation="NaN is not a measurement: the run must be refused (or the NaN pixels excluded and said so), never silently give 'No blob found' or a wrong count.",
        files=[nan],
        tool="feature_tour",
        inputs={"image": s.rel(nan)},
        expect={"status": "FAILED"},
        checks=[chk_status("FAILED")],
        outcome_text="refused with a sentence that names NaN",
    )
    # three channels: channel k holds k+1 discs (PickChannel truth for the hosts), CLI refuses the 3D file
    chans = np.stack(
        [
            disc_scene((128, 128), [(30 + 25 * i, 30 + 30 * i, 8) for i in range(k + 1)], [], seed=7 + k)[0]
            for k in range(3)
        ]
    )
    cf = put(s, "pg_channels_cyx", chans, "CYX", px=(0.5, 0.5), ome=True)
    s.dataset(
        "pg_channels_cyx",
        "a 3-channel image: channel k (0, 1, 2) holds k+1 discs",
        "works",
        derivation="Pick channel k in the host: the blob count must be k+1. A tool that gets the wrong channel is caught.",
        files=cf,
        host={"pick_channel_blob_counts": {"0": 1, "1": 2, "2": 3}},
        host_checks=[chk_host("blobs_channel_%d" % k, k + 1) for k in range(3)],
        outcome_text="host: pick channel k -> k+1 blobs; CLI/worker: refused (see pg_channels_cyx_cli)",
    )
    s.dataset(
        "pg_channels_cyx_cli",
        "the same 3-channel file given whole to the worker",
        "refused",
        derivation="The input is declared YX: a 3D array is refused with wrong_dimensions.",
        files=cf[:1],
        tool="feature_tour",
        inputs={"image": s.rel(cf[0])},
        expect={"status": "FAILED", "code": "wrong_dimensions", "message_contains": "2D"},
        checks=[chk_status("FAILED", "wrong_dimensions", "2D")],
        outcome_text="refused: wrong_dimensions",
    )
    rgb = np.stack(
        [
            disc_scene((128, 128), [(30 + 25 * i, 30 + 30 * i, 8) for i in range(k + 1)], [], seed=17 + k)[0]
            for k in range(3)
        ],
        axis=-1,
    )
    rf = put(s, "pg_rgb", rgb, "YXS", px=(0.5, 0.5))
    s.dataset(
        "pg_rgb",
        "an RGB image: red, green, blue hold 1, 2, 3 discs",
        "works",
        derivation="Pick the colour channel in the host: 1, 2 or 3 blobs.",
        files=rf,
        host={"pick_channel_blob_counts": {"red": 1, "green": 2, "blue": 3}},
        host_checks=[chk_host("blobs_channel_%d" % k, k + 1) for k in range(3)],
        outcome_text="host: pick colour -> 1/2/3 blobs; the worker refuses the 3D file (wrong_dimensions)",
    )


def add_stress(s: Suite) -> None:
    shape = (3000, 3000)
    discs = [(70 + 140 * i, 70 + 140 * j, 12) for i in range(20) for j in range(20)]
    image, rows = disc_scene(shape, discs, [], seed=303)
    files = put(s, "pg_stress_discs", image, "YX", px=(0.1, 0.1))
    checks, expect = tour_checks(s, "pg_stress_discs", rows, len(rows))
    s.dataset(
        "pg_stress_discs",
        "stress: 3000x3000 uint8 with a 20x20 grid of 400 discs (radius 12)",
        "works",
        derivation="400 non-touching lattice discs on a grid (spacing 140 px); counts, centres and areas are exact.",
        files=files,
        tool="feature_tour",
        inputs={"image": s.rel(files[0])},
        expect=expect,
        checks=checks,
        host={"note": "a host must show or refuse a 9 MB image, never freeze"},
    )
    big = np.zeros(shape, np.uint16)
    big[:, 1500:] = 1000
    bf = put(s, "pg_stress_halves", big, "YX", px=(0.1, 0.1))
    n = 3000 * 1500
    count_case(
        s,
        "pg_stress_halves",
        "stress: 3000x3000 uint16 (18 MB, memory-mapped by the worker), left half 0, right half 1000",
        bf,
        {"image": s.rel(bf[0]), "mode": "fixed", "level": 500.0},
        n,
        500.0,
        3000 * 3000,
        "Pixels >= 500 are the right half: 3000 x 1500 = 4 500 000.",
    )
    s.dataset(
        "pg_stress_halves_area",
        "the same image: area of the bright region at 0.1 um per pixel",
        "works",
        derivation="Bright = above half the maximum = the right half: 4 500 000 px x 0.01 um2 = 45 000 um2.",
        files=bf,
        tool="bright_area",
        inputs={"image": s.rel(bf[0]), "pixel_size": 0.1},
        expect={"results": {"values": {"bright_pixels": n, "area_um2": {"approx": n * 0.01, "tol": 1e-6}}}},
        checks=[
            chk_status("COMPLETE"),
            chk_value("bright_pixels", n),
            chk_value("area_um2", n * 0.01, 1e-6, rtol=1e-12),
        ],
    )
