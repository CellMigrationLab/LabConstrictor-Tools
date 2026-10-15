"""NucleiSky datasets with label masks and selection regions: exact nucleus counts, boxes that do not start at the origin, invalid masks. NucleiSky-specific."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import tifffile

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
from common import (
    chk_value,
)  # noqa: E402
from ns_scene import (
    Transform,
    box_clear_of,
    inside,
    label_centroids,
    labels_of,
    render_query,
)

APP, VERSION = "NucleiSky", "0.1.4"
PS_REF = 0.65


from ns_helpers import Maker, Scene  # noqa: E402


def clear_edge(values: np.ndarray, start: int, margin: float = 3.0) -> int:
    """The first edge position >= start (a half-open slice bound) with no centre coordinate within `margin` px of it."""
    for edge in range(start, start + 200):
        if not (np.abs(values - (edge - 0.5)) < margin).any():
            return edge
    raise RuntimeError("no clear edge near %d" % start)


def add_masks(m: Maker, scene: Scene, t: Transform, base: tuple[list[Path], list[Path]]) -> None:
    ref_labels, q_clean = labels_of(scene.clean), render_query(scene.nuclei, t)
    q_labels = labels_of(q_clean)
    rm = m.f / "ns_small_reference_mask.tif"
    qm = m.f / "ns_small_query_mask.tif"
    tifffile.imwrite(rm, ref_labels)
    tifffile.imwrite(qm, q_labels)
    n_ref, n_q = int(ref_labels.max()), int(q_labels.max())
    assert n_ref == len(scene.nuclei), "nuclei merged or lost in the reference mask: %d of %d" % (
        n_ref,
        len(scene.nuclei),
    )
    rf, qf = base
    both = {"reference_mask": m.s.rel(rm), "query_mask": m.s.rel(qm)}
    exact = [chk_value("n_nuclei_reference", n_ref), chk_value("n_nuclei_query", n_q)]
    m.works(
        "ns_masks_exact",
        "the same pair with exact label masks (no segmentation): %d reference and %d query nuclei"
        % (n_ref, n_q),
        rf,
        qf,
        t,
        (1200, 1200),
        "With the exact masks the tool counts the nuclei it was given: n_nuclei_reference = %d, n_nuclei_query = %d (labels of the noise-free scene)."
        % (n_ref, n_q),
        tol=2.0,
        extra=both,
        extra_files=[rm, qm],
        checks_extra=exact,
        points_tol=2.0,
        fraction=0.9,
    )
    rbin, qbin = m.f / "ns_small_reference_mask_binary.tif", m.f / "ns_small_query_mask_binary.tif"
    tifffile.imwrite(rbin, (ref_labels > 0).astype(np.uint8))
    tifffile.imwrite(qbin, (q_labels > 0).astype(np.uint8))
    m.works(
        "ns_masks_binary",
        "binary masks (0/1): the tool must label the connected objects itself, not count one nucleus",
        rf,
        qf,
        t,
        (1200, 1200),
        "Binary masks hold one value for every nucleus: the connected objects are the nuclei, so the counts are %d and %d."
        % (n_ref, n_q),
        tol=2.0,
        extra={"reference_mask": m.s.rel(rbin), "query_mask": m.s.rel(qbin)},
        extra_files=[rbin, qbin],
        checks_extra=exact,
        points_tol=2.0,
        fraction=0.9,
    )
    ref_pts, q_pts = label_centroids(ref_labels), label_centroids(q_labels)
    rbox = (
        clear_edge(ref_pts[:, 0], 200),
        clear_edge(ref_pts[:, 0], 1000),
        clear_edge(ref_pts[:, 1], 150),
        clear_edge(ref_pts[:, 1], 1050),
    )
    qbox = (
        clear_edge(q_pts[:, 0], 60),
        clear_edge(q_pts[:, 0], 420),
        clear_edge(q_pts[:, 1], 50),
        clear_edge(q_pts[:, 1], 430),
    )
    assert box_clear_of(ref_pts, rbox) and box_clear_of(q_pts, qbox)
    for name, box, shape in (("reference", rbox, scene.shape), ("query", qbox, q_labels.shape)):
        region = np.zeros(shape, np.int32)
        region[box[0] : box[1], box[2] : box[3]] = 1
        tifffile.imwrite(m.f / ("ns_small_%s_region.tif" % name), region)
    n_ref_in, n_q_in = int(inside(ref_pts, rbox).sum()), int(inside(q_pts, qbox).sum())
    both_regions = {
        **both,
        "reference_region": m.s.rel(m.f / "ns_small_reference_region.tif"),
        "query_region": m.s.rel(m.f / "ns_small_query_region.tif"),
    }
    m.works(
        "ns_region_nonzero_origin",
        "selection regions that do not start at the origin: reference rows %d-%d columns %d-%d, query rows %d-%d columns %d-%d"
        % (rbox[0], rbox[1] - 1, rbox[2], rbox[3] - 1, qbox[0], qbox[1] - 1, qbox[2], qbox[3] - 1),
        rf,
        qf,
        t,
        (1200, 1200),
        "Only the nuclei whose centre lies in the region are used: %d of %d (reference) and %d of %d (query), counted from the truth centroids (no centre within 3 px of a region edge). The matrix is still "
        "the full-image one: a region must not shift the frame (a crop-origin error would add (%d, %d) px)."
        % (n_ref_in, n_ref, n_q_in, n_q, rbox[0], rbox[2]),
        tol=3.0,
        extra=both_regions,
        extra_files=[rm, qm, m.f / "ns_small_reference_region.tif", m.f / "ns_small_query_region.tif"],
        checks_extra=[chk_value("n_nuclei_reference", n_ref_in), chk_value("n_nuclei_query", n_q_in)],
        points_tol=2.5,
        fraction=0.9,
        host={
            "selection": "draw the two boxes as shapes/ROIs/annotations (rows r0..r1-1, columns c0..c1-1) and tick 'use the selection': same counts and the same matrix",
            "reference_box": list(rbox),
            "query_box": list(qbox),
        },
    )
    empty, wrong = m.f / "ns_region_empty.tif", m.f / "ns_region_wrong_size.tif"
    tifffile.imwrite(empty, np.zeros(scene.shape, np.int32))
    tifffile.imwrite(wrong, np.ones((100, 100), np.int32))
    for ident, path, text, why in (
        ("ns_region_empty", empty, "empty", "an empty selection"),
        ("ns_region_wrong_size", wrong, "size", "a selection of the wrong size (100x100)"),
    ):
        m.refused(
            ident,
            "reference_region = %s" % why,
            {
                "reference": m.s.rel(rf[0]),
                "query": m.s.rel(qf[0]),
                "reference_pixel_size_um": PS_REF,
                "query_pixel_size_um": PS_REF / 2,
                "reference_region": m.s.rel(path),
            },
            [path],
            "The region must be non-empty and the size of its image.",
            None,
            None,
            "refused with a sentence",
        )
    # invalid masks
    bad: dict[str, tuple[Path | None, str, str, str]] = {
        "ns_mask_wrong_size": (
            rm,
            "the REFERENCE mask given as the query mask (sizes differ)",
            "mask_shape_mismatch",
            "same size",
        ),
        "ns_mask_fractions": (
            None,
            "a query mask with fractional labels (label + 0.5)",
            "bad_mask",
            "whole-number",
        ),
        "ns_mask_negative": (None, "a query mask with a negative label", "bad_mask", "negative"),
        "ns_mask_nan": (None, "a float query mask with a NaN", "bad_mask", "NaN"),
    }
    frac = (q_labels + 0.5).astype(np.float32)
    neg = q_labels.astype(np.int16)
    neg[0, 0] = -1
    nan = q_labels.astype(np.float32)
    nan[5, 5] = np.nan
    arrays = {"ns_mask_fractions": frac, "ns_mask_negative": neg, "ns_mask_nan": nan}
    for ident, (maybe_path, why, code, text) in bad.items():
        file = maybe_path if maybe_path is not None else m.f / (ident + ".tif")
        if maybe_path is None:
            tifffile.imwrite(file, arrays[ident])
        m.refused(
            ident,
            why,
            {
                "reference": m.s.rel(rf[0]),
                "query": m.s.rel(qf[0]),
                "reference_pixel_size_um": PS_REF,
                "query_pixel_size_um": PS_REF / 2,
                "query_mask": m.s.rel(file),
            },
            [file],
            "A mask must be a whole-number, non-negative label image of the size of its image.",
            code,
            text,
        )
