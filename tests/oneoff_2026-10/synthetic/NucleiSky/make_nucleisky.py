#!/usr/bin/env python3
"""Synthetic nuclei images with a KNOWN transform between two of them, for NucleiSky `relocalize` (the only tool of the app's bridge).

    python make_nucleisky.py OUT_DIR      # standalone: numpy, scipy, tifffile; common.py, check_ground_truth.py and ns_scene.py next to it or one folder up

The reference and the query are sampled from one analytic scene (ns_scene.py), the query on a rotated, scaled and shifted grid, so the matrix
the tool must report (query pixels -> reference pixels, y then x), the rotation, the physical scale (1) and the offset are known exactly. With
exact label masks the number of nuclei is known too. NucleiSky has no 3D tool in its bridge: the 3D/stack datasets are the refusals of a
wrong dimensionality. The tool runs are pending the install of NucleiSky (about 9 GB): the datasets are validated by `prove_generators.py`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
from common import (
    Suite,
    chk_host,
    chk_status,
    standalone_main,
    write_tiff,
)  # noqa: E402
from ns_scene import (
    Transform,
)

APP, VERSION = "NucleiSky", "0.1.4"
PS_REF = 0.65


from ns_helpers import Maker, Scene  # noqa: E402
from ns_masks import add_masks  # noqa: E402


def add_main(m: Maker) -> None:
    big = Scene(1, (1600, 1600), 450)
    t = Transform(-20.0, 2.0, (790.0, 840.0), (520, 520))
    ref_path = m.f / "ns_big_reference.tif"
    rf = [write_tiff(ref_path, big.reference(), "YX", pixel_um=(PS_REF, PS_REF), unit="um")]
    q, _ = big.query(t)
    qf = [write_tiff(m.f / "ns_normal_query.tif", q, "YX", pixel_um=(PS_REF / 2, PS_REF / 2), unit="um")]
    m.works(
        "ns_normal",
        "1600x1600 field of 450 nuclei (0.65 um/px) and a 520x520 query rotated -20 degrees at 2x magnification (0.325 um/px)",
        rf,
        qf,
        t,
        (1600, 1600),
        "A normal case that must work.",
        host={
            "calibration": {"reference_um": PS_REF, "query_um": PS_REF / 2},
            "landmarks_note": "the overlay of the query on the reference must coincide with the nuclei",
        },
        host_checks=[
            chk_host("reference_pixel_size_um", PS_REF, 1e-9),
            chk_host("query_pixel_size_um", PS_REF / 2, 1e-9),
        ],
    )
    shift = Transform(
        0.0, 1.0, (333 + 209.5, 517 + 209.5), (420, 420)
    )  # A = I, b = (333, 517): an exact crop
    q2, _ = big.query(shift)
    qf2 = [write_tiff(m.f / "ns_shift_query.tif", q2, "YX", pixel_um=(PS_REF, PS_REF), unit="um")]
    m.works(
        "ns_pure_shift",
        "a 420x420 crop of the field at the same pixel size, shifted by exactly (333, 517) pixels, no rotation",
        rf,
        qf2,
        shift,
        (1600, 1600),
        "The simplest known transform: identity matrix and a translation of (333, 517) px.",
        tol=2.0,
        points_tol=2.5,
    )
    rot = Transform(35.0, 1.0, (800.0, 800.0), (420, 420))
    q3, _ = big.query(rot)
    qf3 = [write_tiff(m.f / "ns_rotation_query.tif", q3, "YX", pixel_um=(PS_REF, PS_REF), unit="um")]
    m.works(
        "ns_rotation_only",
        "a 420x420 query rotated by +35 degrees at the same pixel size (a sign or axis-order error shows as -35 or a transposed matrix)",
        rf,
        qf3,
        rot,
        (1600, 1600),
        "A pure rotation: the matrix is R(35 deg) with A[0,1] = -sin, A[1,0] = +sin in (y, x) rows.",
        tol=3.0,
    )
    other = Scene(99, (600, 600), 90)
    q4, _ = other.query(Transform(0.0, 2.0, (300.0, 300.0), (300, 300)))
    qp = [write_tiff(m.f / "ns_unrelated_query.tif", q4, "YX", pixel_um=(PS_REF / 2, PS_REF / 2), unit="um")]
    m.refused(
        "ns_no_overlap",
        "a query from a different field of nuclei (nothing in common with the reference)",
        {
            "reference": m.s.rel(rf[0]),
            "query": m.s.rel(qp[0]),
            "reference_pixel_size_um": PS_REF,
            "query_pixel_size_um": PS_REF / 2,
        },
        rf + qp,
        "No match exists: the tool must say so (no_match), never return a transform.",
        "no_match",
        "No match found",
    )
    flat = write_tiff(
        m.f / "ns_flat_zero_reference.tif",
        np.zeros((256, 256), np.uint16),
        "YX",
        pixel_um=(PS_REF, PS_REF),
        unit="um",
    )
    m.refused(
        "ns_flat_zero_reference",
        "an all-zero reference image",
        {
            "reference": m.s.rel(flat),
            "query": m.s.rel(qf[0]),
            "reference_pixel_size_um": PS_REF,
            "query_pixel_size_um": PS_REF / 2,
        },
        [flat],
        "There is nothing to find in an all-zero image.",
        None,
        None,
        "refused with a sentence (no nuclei)",
    )
    st = Scene(7, (3000, 3000), 1600)
    ts = Transform(8.0, 2.0, (1500.0, 1450.0), (600, 600))
    sf = [
        write_tiff(
            m.f / "ns_stress_reference.tif", st.reference(), "YX", pixel_um=(PS_REF, PS_REF), unit="um"
        )
    ]
    q5, _ = st.query(ts)
    sq = [write_tiff(m.f / "ns_stress_query.tif", q5, "YX", pixel_um=(PS_REF / 2, PS_REF / 2), unit="um")]
    m.works(
        "ns_stress_3000",
        "stress: a 3000x3000 uint16 field (18 MB, memory-mapped) of 1600 nuclei and a 600x600 query rotated 8 degrees at 2x",
        sf,
        sq,
        ts,
        (3000, 3000),
        "Same as ns_normal on a larger field.",
        tol=4.0,
    )


def add_small(m: Maker) -> None:
    scene = Scene(2, (1200, 1200), 250)
    t = Transform(25.0, 2.0, (600.0, 640.0), (480, 480))
    ps_q = PS_REF / 2
    variants = [
        ("ns_small_um", np.uint16, "um", True, "calibration in um (ImageJ), plus an OME copy"),
        ("ns_small_nm", np.uint16, "nm", False, "calibration in nm (650 nm and 325 nm per pixel)"),
        ("ns_small_micro", np.uint16, "µm", False, "calibration unit written as the micro sign"),
        ("ns_small_micron", np.uint16, "micron", False, "calibration unit 'micron'"),
        ("ns_small_u8", np.uint8, "um", False, "8-bit images"),
        ("ns_small_f32", np.float32, "um", False, "32-bit float images"),
    ]
    base: tuple[list[Path], list[Path]] | None = None
    for ident, dtype, unit, ome, what in variants:
        rf, qf, _ = m.pair(ident, scene, t, dtype=dtype, unit=unit, ome=ome)
        base = base or (rf, qf)
        host_checks = [
            chk_host("reference_pixel_size_um", PS_REF, 1e-6),
            chk_host("query_pixel_size_um", ps_q, 1e-6),
        ]
        m.works(
            ident,
            "a 1200x1200 field of 250 nuclei and a rotated (25 degrees) 2x query: %s" % what,
            rf,
            qf,
            t,
            (1200, 1200),
            "The same geometry in another encoding of the file.",
            host_checks=host_checks,
            host={"calibration": {"unit": unit, "reference_um": PS_REF, "query_um": ps_q}},
            calibration={"x_um": PS_REF, "y_um": PS_REF, "unit": unit},
        )
    rf, qf, _ = m.pair("ns_small_nocal", scene, t, calibrated=False, fmt="plain")
    m.refused(
        "ns_small_nocal",
        "the same images with no calibration and no pixel size given",
        {"reference": m.s.rel(rf[0]), "query": m.s.rel(qf[0])},
        rf + qf,
        "No pixel size anywhere: refused with missing_parameter (no default, never guessed); a host leaves both fields blank and blocks Run.",
        "missing_parameter",
        "no calibration",
    )
    m.s.datasets[-1]["host_checks"] = [
        chk_host("reference_pixel_size_um", None),
        chk_host("query_pixel_size_um", None),
    ]
    rf, qf, _ = m.pair("ns_small_pixelunit", scene, t, pixel_unit=True)
    m.refused(
        "ns_small_pixelunit",
        "calibration with the unit 'pixel' (a scale in pixels, not a length), no pixel size given",
        {"reference": m.s.rel(rf[0]), "query": m.s.rel(qf[0])},
        rf + qf,
        "A scale in pixels is not a length: not calibrated.",
        "missing_parameter",
        "no calibration",
    )
    m.s.datasets[-1]["host_checks"] = [
        chk_host("reference_pixel_size_um", None),
        chk_host("query_pixel_size_um", None),
    ]
    ref = write_tiff(
        m.f / "ns_small_aniso_reference.tif", scene.reference(), "YX", pixel_um=(0.5, PS_REF), unit="um"
    )
    m.s.dataset(
        "ns_small_aniso",
        "anisotropic pixels: 0.5 um in Y, 0.65 um in X",
        "HUMAN",
        derivation="The tool takes ONE pixel size per image: a host that fills 0.65 (X) silently distorts the match in Y by 30%. "
        "A host should refuse or warn.",
        files=[ref],
        calibration={"x_um": PS_REF, "y_um": 0.5, "unit": "um"},
        host={"pixel_size_y_um": 0.5, "pixel_size_x_um": PS_REF},
        outcome_text="HUMAN: what the host shows for the pixel size of an anisotropic image",
    )
    assert base is not None
    for kind, data, axes, extra in (
        ("cyx", np.stack([np.ones((64, 64), np.uint16)] * 3), "CYX", {}),
        ("tyx", np.stack([np.ones((64, 64), np.uint16)] * 4), "TYX", {"t_s": 5.0}),
        ("zyx", np.stack([np.ones((64, 64), np.uint16)] * 5), "ZYX", {"z_um": 1.5}),
        ("tzcyx", np.ones((2, 3, 2, 64, 64), np.uint16), "TZCYX", {"z_um": 1.5, "t_s": 5.0}),
        ("rgb", np.ones((64, 64, 3), np.uint8), "YXS", {}),
    ):
        p = write_tiff(
            m.f / ("ns_axes_%s.tif" % kind),
            data,
            axes,
            pixel_um=(PS_REF, PS_REF),
            unit="um",
            z_um=extra.get("z_um"),
            t_s=extra.get("t_s"),
        )
        m.refused(
            "ns_axes_%s" % kind,
            "a %s image (%s) as the reference" % (axes, "x".join(map(str, data.shape))),
            {
                "reference": m.s.rel(p),
                "query": m.s.rel(base[1][0]),
                "reference_pixel_size_um": PS_REF,
                "query_pixel_size_um": PS_REF / 2,
            },
            [p],
            "relocalize is 2D (YX): any other dimensionality is refused with wrong_dimensions.",
            "wrong_dimensions",
            "2D",
        )
    nan = scene.reference(np.float32)
    nan[100:140, 100:140] = np.nan
    pn = write_tiff(m.f / "ns_small_nan_reference.tif", nan, "YX", pixel_um=(PS_REF, PS_REF), unit="um")
    m.refused(
        "ns_nan_reference",
        "a float reference with a 40x40 block of NaN",
        {
            "reference": m.s.rel(pn),
            "query": m.s.rel(base[1][0]),
            "reference_pixel_size_um": PS_REF,
            "query_pixel_size_um": PS_REF / 2,
        },
        [pn],
        "NaN is not a measurement: refuse (or exclude the block and say so); a silent wrong or failed match is the bug.",
        None,
        None,
        "refused with a sentence that names NaN",
    )
    add_masks(m, scene, t, base)
    s = m.s
    s.dataset(
        "ns_list_devices",
        "the device list that feeds the dropdown of the deep-learning segmentation",
        "works",
        derivation="No data: the tool lists 'auto' plus the devices PyTorch can use here.",
        tool="list_devices",
        inputs={},
        expect={"status": "COMPLETE"},
        checks=[chk_status("COMPLETE")],
    )


def build(out: Path) -> Suite:
    s = Suite(APP, out, VERSION)
    m = Maker(s)
    add_main(m)
    add_small(m)
    return s


if __name__ == "__main__":
    sys.exit(standalone_main(build, HERE, __doc__ or ""))
