"""VLab4Mic datasets of the tool compare_images: exact Pearson, calibration encodings, refusals and a stress pair."""

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
    chk_value,
    write_tiff,
)  # noqa: E402

APP, VERSION = "LabConstrictor-VLab4Mic", "0.1.6"
SIZE = 160
PIXEL_NM = 20


from vm_common import block_mean, compare, refused, spots_image  # noqa: E402


def add_compare(s: Suite) -> None:
    ref_img = spots_image()
    f = s.fixtures
    ref = write_tiff(f / "vm_ref_20nm.tif", ref_img, "YX", pixel_um=(0.02, 0.02), unit="nm")
    ref_ome = write_tiff(
        f / "ome" / "vm_ref_20nm.tif", ref_img, "YX", pixel_um=(0.02, 0.02), unit="nm", fmt="ome"
    )
    one = {
        "ssim": {"approx": 1.0, "tol": 1e-3},
        "pearson": {"approx": 1.0, "tol": 1e-3},
        "reference_pixel_size_nm": 20.0,
        "simulated_pixel_size_nm": 20.0,
    }
    compare(
        s,
        "vm_identical",
        "the same 160x160 spot image twice, 20 nm per pixel (written in nm)",
        ref,
        ref,
        0.02,
        0.02,
        [
            chk_value("ssim", 1.0, 1e-3),
            chk_value("pearson", 1.0, 1e-3),
            chk_value("reference_pixel_size_nm", 20.0, 1e-6),
            chk_value("simulated_pixel_size_nm", 20.0, 1e-6),
        ],
        one,
        "A similarity of an image with itself is 1 (SSIM and Pearson). The tool echoes the pixel sizes in nm: 0.02 um = 20 nm (a unit slip would show 20000 or 0.02).",
        files=[ref, ref_ome],
        host={"calibration": {"pixel_nm": 20, "pixel_um": 0.02}},
    )
    s.datasets[-1]["host_checks"] = [
        chk_host("reference_pixel_size_um", 0.02, 1e-9),
        chk_host("simulated_pixel_size_um", 0.02, 1e-9),
    ]
    s.datasets[-1]["calibration"] = {"x_um": 0.02, "y_um": 0.02, "unit": "nm"}
    gain = write_tiff(
        f / "vm_gain_offset_20nm.tif",
        (ref_img.astype(np.uint32) * 3 + 100).astype(np.uint16),
        "YX",
        pixel_um=(0.02, 0.02),
        unit="nm",
    )
    compare(
        s,
        "vm_gain_offset",
        "the image times 3 plus 100 (a brighter, offset copy)",
        ref,
        gain,
        0.02,
        0.02,
        [chk_value("pearson", 1.0, 1e-3)],
        {"pearson": {"approx": 1.0, "tol": 1e-3}},
        "Pearson correlation is invariant to gain and offset: exactly 1 (SSIM depends on the dynamic range and is not asserted).",
    )
    inv = write_tiff(
        f / "vm_inverted_20nm.tif",
        (4000 - ref_img.astype(np.int32)).astype(np.uint16),
        "YX",
        pixel_um=(0.02, 0.02),
        unit="nm",
    )
    compare(
        s,
        "vm_inverted",
        "the inverted image (4000 minus the image)",
        ref,
        inv,
        0.02,
        0.02,
        [chk_value("pearson", -1.0, 1e-3)],
        {"pearson": {"approx": -1.0, "tol": 1e-3}},
        "A negative copy is perfectly anti-correlated: Pearson = -1.",
    )
    half = write_tiff(f / "vm_half_res_40nm.tif", block_mean(ref_img), "YX", pixel_um=(0.04, 0.04), unit="nm")
    compare(
        s,
        "vm_half_res_right_units",
        "the same field with 2x2 blocks averaged: 80x80 pixels of 40 nm, pixel sizes entered correctly",
        ref,
        half,
        0.02,
        0.04,
        [chk_value("pearson", minimum=0.95), chk_value("simulated_pixel_size_nm", 40.0, 1e-6)],
        {"pearson": {"approx": 1.0, "tol": 0.05}, "simulated_pixel_size_nm": 40.0},
        "The block-averaged copy is the same scene: after matching the pixel sizes (40 -> 20 nm) it must correlate at 0.95 or more.",
    )
    compare(
        s,
        "vm_half_res_wrong_units",
        "the same two files with the pixel size of the half-resolution image entered as 20 nm too (a calibration mistake)",
        ref,
        half,
        0.02,
        0.02,
        [chk_value("pearson", maximum=0.5)],
        {"pearson": {"approx": 0.0, "tol": 0.5}},
        "With equal pixel sizes the 80x80 image is taken as a quarter of the field: the spots do not line up, so a match must NOT be reported (Pearson at most 0.5).",
    )
    aniso = write_tiff(f / "vm_cal_anisotropic.tif", ref_img, "YX", pixel_um=(0.01, 0.02), unit="nm")
    s.dataset(
        "vm_cal_anisotropic",
        "anisotropic pixels: 10 nm in Y and 20 nm in X",
        "HUMAN",
        derivation="The tool takes one pixel size per image; an image with different Y and X sizes cannot be compared "
        "correctly with one number. A host should refuse or warn rather than silently take X.",
        files=[aniso],
        host={"pixel_size_y_nm": 10, "pixel_size_x_nm": 20},
        calibration={"x_um": 0.02, "y_um": 0.01, "unit": "nm"},
        outcome_text="HUMAN: what the host shows for an anisotropic calibration",
    )
    for unit, value, tag in (("um", 0.02, "um"), ("nm", 20.0, "nm"), ("µm", 0.02, "micro")):
        p = write_tiff(f / ("vm_cal_%s.tif" % tag), ref_img, "YX", pixel_um=(0.02, 0.02), unit=unit)
        s.dataset(
            "vm_cal_%s" % tag,
            "calibration written in %s (%g %s per pixel)" % (unit, value, unit),
            "works",
            derivation="The file says %g %s = 20 nm: a host must fill 0.02 um." % (value, unit),
            files=[p],
            host_checks=[chk_host("reference_pixel_size_um", 0.02, 1e-9)],
            host={"pixel_size_um": 0.02},
            calibration={"x_um": 0.02, "y_um": 0.02, "unit": unit},
        )
    nocal = write_tiff(f / "vm_cal_none.tif", ref_img, "YX", pixel_um=None)
    s.dataset(
        "vm_cal_none",
        "no calibration in the file",
        "refused",
        derivation="No pixel size: the field stays blank and Run is blocked in a host; in the worker the pixel sizes are required inputs.",
        files=[nocal],
        tool="compare_images",
        inputs={"reference": s.rel(nocal), "simulated": s.rel(nocal)},
        expect={"status": "FAILED"},
        checks=[chk_status("FAILED")],
        host_checks=[chk_host("reference_pixel_size_um", None)],
        outcome_text="refused (missing pixel sizes); host: blank field, Run blocked",
    )
    # the formats of 'wrong' images
    nan = ref_img.astype(np.float32)
    nan[5, 5] = np.nan
    pnan = write_tiff(f / "vm_nan_20nm.tif", nan, "YX", pixel_um=(0.02, 0.02), unit="nm")
    refused(
        s,
        "vm_nan_simulated",
        "the simulated image holds a NaN",
        ref,
        pnan,
        0.02,
        0.02,
        "bad_input",
        "NaN",
        "NaN is not a measurement.",
    )
    refused(
        s,
        "vm_nan_reference",
        "the reference image holds a NaN",
        pnan,
        ref,
        0.02,
        0.02,
        "bad_input",
        "NaN",
        "NaN is not a measurement.",
    )
    flat = write_tiff(
        f / "vm_flat_20nm.tif", np.full((SIZE, SIZE), 100, np.uint16), "YX", pixel_um=(0.02, 0.02), unit="nm"
    )
    zero = write_tiff(
        f / "vm_zero_20nm.tif", np.zeros((SIZE, SIZE), np.uint16), "YX", pixel_um=(0.02, 0.02), unit="nm"
    )
    refused(
        s,
        "vm_flat_simulated",
        "the simulated image is flat (100 everywhere)",
        ref,
        flat,
        0.02,
        0.02,
        "flat_image",
        "same value everywhere",
        "Similarity of a flat image is undefined.",
    )
    refused(
        s,
        "vm_zero_simulated",
        "the simulated image is all zero",
        ref,
        zero,
        0.02,
        0.02,
        "flat_image",
        "same value everywhere",
        "All-zero is flat.",
    )
    refused(
        s,
        "vm_flat_reference",
        "the REFERENCE image is flat",
        flat,
        ref,
        0.02,
        0.02,
        None,
        None,
        "Similarity with a flat reference is undefined (Pearson 0/0): refuse, never return NaN. The tool checks only the simulated image.",
        "refused with a sentence (a NaN or 0 similarity is the bug)",
    )
    refused(
        s,
        "vm_zero_reference",
        "the REFERENCE image is all zero",
        zero,
        ref,
        0.02,
        0.02,
        None,
        None,
        "As the flat reference.",
        "refused with a sentence",
    )
    for name, data, axes in (
        ("cyx", np.stack([ref_img] * 3), "CYX"),
        ("zyx", np.stack([ref_img] * 4), "ZYX"),
        ("tyx", np.stack([ref_img] * 3), "TYX"),
    ):
        p = write_tiff(
            f / ("vm_stack_%s.tif" % name),
            data,
            axes,
            pixel_um=(0.02, 0.02),
            unit="nm",
            z_um=0.1 if name == "zyx" else None,
            t_s=1.0 if name == "tyx" else None,
        )
        refused(
            s,
            "vm_stack_%s" % name,
            "a %s stack as the simulated image" % axes,
            ref,
            p,
            0.02,
            0.02,
            "wrong_dimensions",
            "2D",
            "Declared YX: 3D is refused.",
        )
    rgb = write_tiff(
        f / "vm_rgb.tif",
        np.stack([(ref_img / 16).astype(np.uint8)] * 3, axis=-1),
        "YXS",
        pixel_um=(0.02, 0.02),
        unit="nm",
    )
    refused(
        s,
        "vm_rgb",
        "an RGB image as the simulated image",
        ref,
        rgb,
        0.02,
        0.02,
        "wrong_dimensions",
        "2D",
        "Y x X x 3 is 3D.",
    )
    refused(
        s,
        "vm_pixel_zero",
        "pixel size 0",
        ref,
        ref,
        0.0,
        0.02,
        "invalid_pixel_size",
        "greater than 0",
        "A pixel size must be positive.",
    )
    refused(
        s,
        "vm_pixel_negative",
        "pixel size -0.02 (declared minimum 0)",
        ref,
        ref,
        -0.02,
        0.02,
        "invalid_parameter",
        "must be >=",
        "Below the declared minimum.",
    )
    other = write_tiff(
        f / "vm_other_size.tif", spots_image(100, seed=22), "YX", pixel_um=(0.02, 0.02), unit="nm"
    )
    s.dataset(
        "vm_different_fields",
        "two unrelated images of different sizes (160x160 and 100x100), same pixel size",
        "works",
        derivation="Unrelated spots: no similarity (Pearson near 0, SSIM near 0); a run must complete (sizes may differ) "
        "and must not report a match.",
        files=[ref, other],
        tool="compare_images",
        inputs={
            "reference": s.rel(ref),
            "simulated": s.rel(other),
            "reference_pixel_size_um": 0.02,
            "simulated_pixel_size_um": 0.02,
        },
        expect={"results": {"values": {"pearson": {"approx": 0.0, "tol": 0.3}}}},
        checks=[chk_status("COMPLETE"), chk_value("pearson", 0.0, 0.3), chk_value("ssim", 0.0, 0.3)],
    )
    big = spots_image(2500, seed=25, sigma=4.0, count=400)
    bp = write_tiff(f / "vm_stress_2500.tif", big, "YX", pixel_um=(0.02, 0.02), unit="nm")
    s.dataset(
        "vm_stress_identical",
        "stress: the same 2500x2500 uint16 image twice (12.5 MB, memory-mapped)",
        "works",
        derivation="An image against itself: SSIM 1, Pearson 1.",
        files=[bp],
        tool="compare_images",
        inputs={
            "reference": s.rel(bp),
            "simulated": s.rel(bp),
            "reference_pixel_size_um": 0.02,
            "simulated_pixel_size_um": 0.02,
        },
        expect={
            "max_seconds": 240,
            "results": {
                "values": {"ssim": {"approx": 1.0, "tol": 1e-3}, "pearson": {"approx": 1.0, "tol": 1e-3}}
            },
        },
        checks=[chk_status("COMPLETE"), chk_value("ssim", 1.0, 1e-3), chk_value("pearson", 1.0, 1e-3)],
    )
