"""Image datasets of the Playground tools (feature_tour, count_above_level, bright_area, align_centres). GENERIC helpers: `put`, `ramp`.

Every truth is built from the construction: blobs are lattice discs with integer centres (area = number of lattice points within the
radius, centroid exactly the centre), rectangles have a counted number of pixels, ramps have one value per column.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
from common import (  # noqa: E402
    Suite,
    chk_host,
    chk_matrix,
    chk_status,
    chk_value,
)

BACKGROUND, FOREGROUND = 20, 200


from pg_common import count_case, linear_percentile, put, ramp  # noqa: E402
from pg_discs import add_discs, add_stress  # noqa: E402


def add_ramps(s: Suite) -> None:
    shape = (40, 100)
    total = 4000
    for dtype, bits in ((np.uint8, "u8"), (np.uint16, "u16"), (np.float32, "f32")):
        files = put(s, "pg_ramp_%s" % bits, ramp(shape, dtype), "YX", px=(0.5, 0.5), ome=True)
        count_case(
            s,
            "pg_ramp_%s_fixed" % bits,
            "ramp 0..99 (%s), count pixels >= 50" % bits,
            files,
            {"image": s.rel(files[0]), "mode": "fixed", "level": 50.0},
            2000,
            50.0,
            total,
            "Each row is 0..99: columns 50..99 are >= 50: 50 x 40 = 2000.",
        )
        level = linear_percentile(40, 100, 90)
        count_case(
            s,
            "pg_ramp_%s_p90" % bits,
            "ramp 0..99 (%s), 90th percentile" % bits,
            files,
            {"image": s.rel(files[0]), "mode": "percentile", "percentile": 90.0},
            400,
            level,
            total,
            "Sorted values are floor(i/40); linear interpolation at 0.9 x 3999 = 3599.1 -> 89.1; pixels >= 89.1 are columns 90..99: 400.",
        )
    int32 = put(s, "pg_ramp_i32", ramp(shape, np.int32), "YX", fmt="plain")
    count_case(
        s,
        "pg_ramp_i32_fixed",
        "ramp 0..99 as int32 (plain TIFF, no calibration)",
        int32,
        {"image": s.rel(int32[0]), "mode": "fixed", "level": 50.0},
        2000,
        50.0,
        total,
        "As the uint8 ramp.",
    )
    small = ramp(shape, np.uint16)
    small = small % 12  # 16-bit data with a tiny dynamic range
    low = put(s, "pg_ramp_lowrange", small, "YX", px=(0.5, 0.5))
    count_case(
        s,
        "pg_ramp_lowrange",
        "16-bit values 0..11 only (a low dynamic range), count >= 6",
        low,
        {"image": s.rel(low[0]), "mode": "fixed", "level": 6.0},
        sum(1 for c in range(100) if c % 12 >= 6) * 40,
        6.0,
        total,
        "Column c has value c mod 12; values >= 6 occur in %d of 100 columns; x 40 rows."
        % sum(1 for c in range(100) if c % 12 >= 6),
    )
    # dimensionality: every stack is refused by a 2D tool
    stacks = {
        "pg_axes_cyx": (np.stack([ramp(shape)] * 3), "CYX", {}),
        "pg_axes_tyx": (np.stack([ramp(shape)] * 5), "TYX", {"t": 2.0}),
        "pg_axes_zyx": (np.stack([ramp(shape)] * 6), "ZYX", {"z": 2.0}),
        "pg_axes_tzcyx": (
            np.stack([np.stack([np.stack([ramp(shape)] * 2)] * 3)] * 2),
            "TZCYX",
            {"z": 1.5, "t": 30.0},
        ),
    }
    for ident, (data, axes, extra) in stacks.items():
        files = put(s, ident, data, axes, px=(0.5, 0.5), ome=True, z=extra.get("z"), t=extra.get("t"))
        s.dataset(
            ident,
            "a %s image (%s) given to a 2D tool" % (axes, "x".join(map(str, data.shape))),
            "refused",
            derivation="Declared YX: any other dimensionality is refused with wrong_dimensions.",
            files=files,
            tool="count_above_level",
            inputs={"image": s.rel(files[0]), "mode": "fixed", "level": 50.0},
            expect={"status": "FAILED", "code": "wrong_dimensions", "message_contains": "2D"},
            checks=[chk_status("FAILED", "wrong_dimensions", "2D")],
            outcome_text="refused: wrong_dimensions",
            host={"calibration": {"pixel_um": 0.5, **extra}} if extra else {"calibration": {"pixel_um": 0.5}},
        )
    rgbf = put(s, "pg_axes_rgb", np.stack([ramp(shape, np.uint8)] * 3, axis=-1), "YXS", px=(0.5, 0.5))
    s.dataset(
        "pg_axes_rgb",
        "an RGB image given to a 2D tool",
        "refused",
        derivation="Y x X x 3 is 3D.",
        files=rgbf,
        tool="count_above_level",
        inputs={"image": s.rel(rgbf[0]), "mode": "fixed", "level": 50.0},
        expect={"status": "FAILED", "code": "wrong_dimensions", "message_contains": "2D"},
        checks=[chk_status("FAILED", "wrong_dimensions", "2D")],
        outcome_text="refused: wrong_dimensions",
    )
    nanr = ramp(shape, np.float32)
    nanr[0, 0] = np.nan
    nf = put(s, "pg_nan_ramp", nanr, "YX", px=(0.5, 0.5))
    s.dataset(
        "pg_nan_count",
        "a float image with one NaN pixel, percentile mode",
        "refused",
        derivation="The 90th percentile of data with a NaN is NaN: counting pixels against it gives 0. The run must be refused, not return 0 pixels.",
        files=nf,
        tool="count_above_level",
        inputs={"image": s.rel(nf[0]), "mode": "percentile", "percentile": 90.0},
        expect={"status": "FAILED"},
        checks=[chk_status("FAILED")],
        outcome_text="refused with a sentence that names NaN (a silent 0 is the bug)",
    )


def add_area(s: Suite) -> None:
    def rect(dtype: Any, high: float) -> np.ndarray:
        a = np.zeros((64, 80), dtype)
        a[10:30, 20:50] = high  # 20 x 30 = 600 pixels
        return a

    n = 600

    def area(
        ident: str,
        purpose: str,
        files: Sequence[Path],
        pixel: float,
        derivation: str,
        host: dict[str, Any] | None = None,
        calibration: dict[str, Any] | None = None,
        count: int = n,
    ) -> None:
        s.dataset(
            ident,
            purpose,
            "works",
            derivation=derivation,
            files=files,
            tool="bright_area",
            inputs={"image": s.rel(files[0]), "pixel_size": pixel},
            expect={
                "results": {
                    "values": {"bright_pixels": count, "area_um2": {"approx": count * pixel**2, "tol": 1e-9}}
                }
            },
            checks=[
                chk_status("COMPLETE"),
                chk_value("bright_pixels", count),
                chk_value("area_um2", count * pixel**2, 1e-9, rtol=1e-12),
                chk_value("pixel_size_um", pixel, 1e-12),
            ],
            host=host,
            calibration=calibration,
        )

    for dtype, bits, high in ((np.uint8, "u8", 255), (np.uint16, "u16", 60000), (np.float32, "f32", 1.0)):
        files = put(s, "pg_area_%s" % bits, rect(dtype, high), "YX", px=(0.5, 0.5), ome=True)
        area(
            "pg_area_%s" % bits,
            "a 20x30 bright rectangle (%s), 0.5 um per pixel" % bits,
            files,
            0.5,
            "600 bright pixels x 0.25 um2 = 150 um2.",
            host={"pixel_size": 0.5},
            calibration={"x_um": 0.5, "y_um": 0.5, "unit": "um"},
        )
    u32 = put(s, "pg_area_u32", rect(np.uint32, 4_000_000_000), "YX", fmt="plain")
    area(
        "pg_area_u32",
        "the rectangle as uint32 with values near 4e9",
        u32,
        0.5,
        "As above; 32-bit unsigned must not overflow or lose the threshold.",
    )
    for unit, value, ident in (
        ("nm", 500.0, "pg_cal_nm"),
        ("um", 0.5, "pg_cal_um"),
        ("µm", 0.5, "pg_cal_micro_sign"),
        ("micron", 0.5, "pg_cal_micron"),
    ):
        files = put(s, ident, rect(np.uint8, 255), "YX", px=(0.5, 0.5), unit=unit, ome=(unit in ("nm", "um")))
        area(
            ident,
            "calibration written in %s (%g %s per pixel)" % (unit, value, unit),
            files,
            0.5,
            "The file says %g %s = 0.5 um: a host must fill 0.5 (not %g)." % (value, unit, value),
            host={"pixel_size": 0.5},
            calibration={"x_um": 0.5, "y_um": 0.5, "unit": unit},
        )
        s.datasets[-1]["host_checks"].append(chk_host("pixel_size", 0.5, 1e-9))
    nocal = put(s, "pg_cal_none", rect(np.uint8, 255), "YX", px=None)
    s.dataset(
        "pg_cal_none",
        "no calibration in the file",
        "refused",
        derivation="No pixel size anywhere: the tool must refuse, never invent one (the area would be wrong).",
        files=nocal,
        tool="bright_area",
        inputs={"image": s.rel(nocal[0])},
        expect={"status": "FAILED", "code": "pixel_size_unknown", "message_contains": "pixel size"},
        checks=[chk_status("FAILED", "pixel_size_unknown", "pixel size")],
        host_checks=[chk_host("pixel_size", None)],
        outcome_text="refused: pixel_size_unknown; a host leaves the field blank and blocks Run",
        host={"pixel_size": None},
    )
    # an ImageJ file whose unit is "pixel" is a scale in pixels, not a length
    import tifffile

    pixfile = s.fixtures / "pg_cal_pixel_unit.tif"
    tifffile.imwrite(
        pixfile,
        rect(np.uint8, 255),
        imagej=True,
        resolution=(1.0, 1.0),
        metadata={"axes": "YX", "unit": "pixel"},
    )
    s.dataset(
        "pg_cal_pixel_unit",
        "an ImageJ file whose unit is 'pixel' (scale 1)",
        "refused",
        derivation="A scale in pixels is not a length: the host must treat it as not calibrated (blank, Run blocked); the worker has no value.",
        files=[pixfile],
        tool="bright_area",
        inputs={"image": s.rel(pixfile)},
        expect={"status": "FAILED", "code": "pixel_size_unknown", "message_contains": "pixel size"},
        checks=[chk_status("FAILED", "pixel_size_unknown", "pixel size")],
        host_checks=[chk_host("pixel_size", None)],
        host={"pixel_size": None},
        outcome_text="refused: pixel_size_unknown; host: blank field",
    )
    aniso = put(s, "pg_cal_anisotropic", rect(np.uint8, 255), "YX", px=(0.25, 0.5), ome=True)
    s.dataset(
        "pg_cal_anisotropic",
        "anisotropic pixels: 0.25 um in Y, 0.5 um in X",
        "HUMAN",
        derivation="The true area is 600 x 0.25 x 0.5 = 75 um2. The tool takes ONE pixel size: whatever the host puts in the field (0.5 = X only) gives 150 um2, double the truth. "
        "A host should refuse or warn; a silent X-only value is the wrong-science case to look for.",
        files=aniso,
        tool="bright_area",
        inputs={"image": s.rel(aniso[0]), "pixel_size": 0.5},
        expect={"results": {"values": {"bright_pixels": n}}},
        checks=[chk_status("COMPLETE"), chk_value("bright_pixels", n)],
        host={"pixel_size_y_um": 0.25, "pixel_size_x_um": 0.5, "true_area_um2": 75.0},
        calibration={"x_um": 0.5, "y_um": 0.25, "unit": "um"},
        outcome_text="HUMAN: what the host shows for the pixel size of an anisotropic image",
    )
    zero = put(s, "pg_area_all_zero", np.zeros((64, 80), np.uint8), "YX", px=(0.5, 0.5))
    s.dataset(
        "pg_area_all_zero",
        "an all-zero image",
        "works",
        derivation="No pixel is bright: 0 pixels, 0 um2 (a defined answer, not an error).",
        files=zero,
        tool="bright_area",
        inputs={"image": s.rel(zero[0]), "pixel_size": 0.5},
        expect={"results": {"values": {"bright_pixels": 0, "area_um2": 0.0}}},
        checks=[chk_status("COMPLETE"), chk_value("bright_pixels", 0), chk_value("area_um2", 0.0, 1e-12)],
    )
    nanimg = rect(np.float32, 1.0)
    nanimg[0, 0] = np.nan
    nf = put(s, "pg_area_nan", nanimg, "YX", px=(0.5, 0.5))
    s.dataset(
        "pg_area_nan",
        "the rectangle with one NaN pixel",
        "refused",
        derivation="With a NaN the maximum is NaN: every comparison is False and the area is 0 um2. The truth is 150 um2 or a refusal; 0 is silently wrong.",
        files=nf,
        tool="bright_area",
        inputs={"image": s.rel(nf[0]), "pixel_size": 0.5},
        expect={"status": "FAILED"},
        checks=[chk_status("FAILED")],
        outcome_text="refused naming NaN (a silent 0 is the bug)",
    )
    base = put(s, "pg_area_for_pixel_cases", rect(np.uint8, 255), "YX", px=(0.5, 0.5))
    for ident, size, code, text in (
        ("pg_pixel_zero", 0.0, "invalid_pixel_size", "above 0"),
        ("pg_pixel_negative", -0.5, "invalid_pixel_size", "above 0"),
    ):
        s.dataset(
            ident,
            "pixel size %g" % size,
            "refused",
            derivation="A pixel size must be above 0.",
            files=base,
            tool="bright_area",
            inputs={"image": s.rel(base[0]), "pixel_size": size},
            expect={"status": "FAILED", "code": code, "message_contains": text},
            checks=[chk_status("FAILED", code, text)],
            outcome_text="refused: %s" % code,
        )


def add_align(s: Suite) -> None:
    def square(shape: tuple[int, int], r0: int, r1: int, c0: int, c1: int) -> np.ndarray:
        a = np.zeros(shape, np.uint8)
        a[r0 : r1 + 1, c0 : c1 + 1] = 255
        return a

    def gaussian(shape: tuple[int, int], cy: float, cx: float, sigma: float) -> np.ndarray:
        yy, xx = np.mgrid[: shape[0], : shape[1]]
        return (1000 * np.exp(-((yy - cy) ** 2 + (xx - cx) ** 2) / (2 * sigma**2))).astype(np.float32)

    def matrix(dy: float, dx: float) -> list[list[float]]:
        return [[1.0, 0.0, dy], [0.0, 1.0, dx], [0.0, 0.0, 1.0]]

    def case(
        ident: str,
        purpose: str,
        a: np.ndarray,
        b: np.ndarray,
        dy: float,
        dx: float,
        derivation: str,
        tol: float,
    ) -> None:
        fa, fb = put(s, ident + "_image", a, "YX", px=(0.5, 0.5)), put(
            s, ident + "_reference", b, "YX", px=(0.5, 0.5)
        )
        s.dataset(
            ident,
            purpose,
            "works",
            derivation=derivation,
            files=fa + fb,
            tool="align_centres",
            inputs={"image": s.rel(fa[0]), "reference": s.rel(fb[0])},
            expect={"results": {"alignment": {"matrix": matrix(dy, dx)}}} if tol <= 1e-6 else {},
            checks=[chk_status("COMPLETE"), chk_matrix(matrix(dy, dx), 1e-9, tol)],
        )

    a, b = square((96, 128), 20, 25, 30, 35), square((200, 64), 50, 57, 40, 47)
    case(
        "pg_align_squares",
        "a 6x6 square and an 8x8 square in images of different sizes",
        a,
        b,
        53.5 - 22.5,
        43.5 - 32.5,
        "Centres of a square of rows r0..r1 are (r0+r1)/2: (22.5, 32.5) and (53.5, 43.5): translation = reference centre - image centre = (31, 11). Image and reference may differ in size.",
        1e-6,
    )
    case(
        "pg_align_swapped",
        "the same two images swapped",
        b,
        a,
        22.5 - 53.5,
        32.5 - 43.5,
        "Opposite translation (-31, -11).",
        1e-6,
    )
    case(
        "pg_align_identity",
        "an image against itself",
        a,
        a,
        0.0,
        0.0,
        "Zero translation (identity matrix).",
        1e-9,
    )
    shape = (96, 128)
    case(
        "pg_align_subpixel",
        "two Gaussian spots at sub-pixel positions (30.3, 40.7) and (55.8, 90.2)",
        gaussian(shape, 30.3, 40.7, 4.0),
        gaussian(shape, 55.8, 90.2, 4.0),
        55.8 - 30.3,
        90.2 - 40.7,
        "The intensity centroid of a well-inside Gaussian is its centre: translation (25.5, 49.5), not an integer: silent rounding would show as 25 or 26.",
        1e-3,
    )
    zero = put(s, "pg_align_zero_image", np.zeros(shape, np.uint8), "YX", px=(0.5, 0.5))
    ref = put(s, "pg_align_zero_ref", a, "YX", px=(0.5, 0.5))
    s.dataset(
        "pg_align_zero",
        "an all-zero image has no centre",
        "refused",
        derivation="No signal, no centre.",
        files=zero + ref,
        tool="align_centres",
        inputs={"image": s.rel(zero[0]), "reference": s.rel(ref[0])},
        expect={"status": "FAILED", "code": "no_signal", "message_contains": "no signal"},
        checks=[chk_status("FAILED", "no_signal", "no signal")],
        outcome_text="refused: no_signal",
    )
    nan = a.astype(np.float32)
    nan[0, 0] = np.nan
    nf = put(s, "pg_align_nan", nan, "YX", px=(0.5, 0.5))
    s.dataset(
        "pg_align_nan",
        "an image with one NaN",
        "refused",
        derivation="A NaN makes every centroid NaN: the run must be refused, never return a matrix of NaN.",
        files=nf + ref,
        tool="align_centres",
        inputs={"image": s.rel(nf[0]), "reference": s.rel(ref[0])},
        expect={"status": "FAILED"},
        checks=[chk_status("FAILED")],
        outcome_text="refused naming NaN",
    )


def build_images(s: Suite) -> None:
    add_discs(s)
    add_ramps(s)
    add_area(s)
    add_align(s)
    add_stress(s)
