"""Shared pieces of the NucleiSky click scripts: tiny synthetic data of known geometry (a large image or volume of bright blobs, and a crop cut at a known offset with no
rotation and the same pixel size), stage-code helpers, and the oracle that compares a saved NucleiSky transform with that known geometry.

Why synthetic and generated here: the oracle is the geometry we cut the crop with (offset in pixels times the pixel size, scale 1.0), independent of the matcher under test.
The segmentation method of every GUI is set to the classical threshold: Cellpose and InstanSeg need model files (a download) and a GPU for any useful speed (HUMAN rows).
"""

import json
import math
from pathlib import Path
from typing import Any

PIXEL_UM = 0.65
OFFSET_2D = (300, 500)  # (y, x) in pixels of the crop inside the large image
OFFSET_3D = (8, 30, 40)  # (z, y, x) in voxels
CROP_2D = 400
SHAPE_2D = 1200
SHAPE_3D = (64, 200, 200)
CROP_3D = (48, 128, 128)


def setvars(values: dict[str, Any]) -> str:
    """Kernel code that sets notebook widgets by variable name: `{var: value}`."""
    return "".join(
        "lcnb.set_value(lcnb.find(var=%r), %r)\n" % (name, value) for name, value in values.items()
    )


def make_2d(work: Path) -> dict[str, Any]:
    """full.tif (1200x1200) and crop.tif (400x400 cut at OFFSET_2D), pixel size 0.65 um in the TIFF resolution tags."""
    import numpy as np
    import tifffile

    folder = work / "ns2d"
    folder.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(11)
    yy, xx = np.mgrid[0:SHAPE_2D, 0:SHAPE_2D]
    image = rng.normal(100, 5, (SHAPE_2D, SHAPE_2D))
    centres: list[tuple[int, int]] = []
    while len(centres) < 300:
        cy, cx = rng.integers(20, SHAPE_2D - 20, 2)
        if all((cy - a) ** 2 + (cx - b) ** 2 > 45**2 for a, b in centres):
            centres.append((cy, cx))
            image += 900 * np.exp(-((yy - cy) ** 2 + (xx - cx) ** 2) / (2 * 7.0**2))
    full = image.clip(0, 65535).astype(np.uint16)
    oy, ox = OFFSET_2D
    crop = full[oy : oy + CROP_2D, ox : ox + CROP_2D].copy()
    meta = dict(imagej=True, resolution=(1 / PIXEL_UM, 1 / PIXEL_UM), metadata={"unit": "um", "axes": "YX"})
    tifffile.imwrite(folder / "full.tif", full, **meta)
    tifffile.imwrite(folder / "crop.tif", crop, **meta)
    inside = sum(1 for cy, cx in centres if oy <= cy < oy + CROP_2D and ox <= cx < ox + CROP_2D)
    margin = sum(
        1 for cy, cx in centres if oy - 12 <= cy < oy + CROP_2D + 12 and ox - 12 <= cx < ox + CROP_2D + 12
    )
    return {
        "full": str(folder / "full.tif"),
        "crop": str(folder / "crop.tif"),
        "out": str(folder / "out"),
        "nuclei": len(centres),
        "nuclei_in_crop": inside,
        "nuclei_in_crop_with_margin": margin,
    }


def make_3d(work: Path) -> dict[str, Any]:
    """full.tif (48x160x160) and crop.tif (32x96x96 cut at OFFSET_3D), isotropic 1 um voxels (the GUIs are given the voxel size by hand)."""
    import numpy as np
    import tifffile

    folder = work / "ns3d"
    folder.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(13)
    zz, yy, xx = np.mgrid[0 : SHAPE_3D[0], 0 : SHAPE_3D[1], 0 : SHAPE_3D[2]]
    volume = rng.normal(100, 3, SHAPE_3D)
    centres: list[tuple[int, int, int]] = []
    tries = 0
    while len(centres) < 60 and tries < 20000:
        tries += 1
        c = (
            int(rng.integers(10, SHAPE_3D[0] - 10)),
            int(rng.integers(14, SHAPE_3D[1] - 14)),
            int(rng.integers(14, SHAPE_3D[2] - 14)),
        )
        if all(sum((p - q) ** 2 for p, q in zip(c, o)) > 14**2 for o in centres):
            centres.append(c)
            volume += 900 * np.exp(-((zz - c[0]) ** 2 + (yy - c[1]) ** 2 + (xx - c[2]) ** 2) / (2 * 4.5**2))
    full = volume.clip(0, 65535).astype(np.uint16)
    oz, oy, ox = OFFSET_3D
    crop = full[oz : oz + CROP_3D[0], oy : oy + CROP_3D[1], ox : ox + CROP_3D[2]].copy()
    meta = dict(imagej=True, metadata={"spacing": 1.0, "unit": "um", "axes": "ZYX"}, resolution=(1.0, 1.0))
    tifffile.imwrite(folder / "full.tif", full, **meta)
    tifffile.imwrite(folder / "crop.tif", crop, **meta)
    return {
        "full": str(folder / "full.tif"),
        "crop": str(folder / "crop.tif"),
        "out": str(folder / "out"),
        "nuclei": len(centres),
    }


def _find(document: Any, names: tuple[str, ...]) -> Any:
    """The first value stored under any of `names` anywhere in a nested JSON document, or None."""
    if isinstance(document, dict):
        for key, value in document.items():
            if key in names:
                return value
        for value in document.values():
            found = _find(value, names)
            if found is not None:
                return found
    elif isinstance(document, list):
        for value in document:
            found = _find(value, names)
            if found is not None:
                return found
    return None


def transform_rows(
    out_dir: Path, expected_scale: float, expected_shift_um: float, tolerance_um: float, label: str
) -> list[tuple[str, str, str]]:
    """Oracle rows for the newest saved transform JSON under `out_dir`: found, scale equal to `expected_scale` (2 %), length of the translation vector equal to
    `expected_shift_um` (the offset we cut the crop at, times the pixel size) within `tolerance_um`. Sign and axis order are not assumed: only the length is compared.
    """
    import numpy as np

    found = (
        sorted(out_dir.rglob("*transform*.json"), key=lambda p: p.stat().st_mtime) if out_dir.is_dir() else []
    )
    if not found:
        return [
            (
                label + "_transform_json",
                "FAIL",
                "no *transform*.json under %s (the matching step wrote no saved transform)" % out_dir,
            )
        ]
    document = json.loads(found[-1].read_text(encoding="utf-8"))
    rows = [
        (
            label + "_transform_json",
            "PASS",
            "saved transform %s (%d bytes)" % (found[-1].name, found[-1].stat().st_size),
        )
    ]
    scale = _find(document, ("best_scale", "scale"))
    shift = _find(document, ("best_t", "t", "translation", "translation_um", "t_um_yx", "t_um_zyx"))
    rows.append(
        (
            label + "_scale",
            (
                "PASS"
                if isinstance(scale, (int, float))
                and abs(float(scale) - expected_scale) <= 0.02 * expected_scale
                else "FAIL"
            ),
            "scale %r, expected %.3f (the crop was cut at the same pixel size)" % (scale, expected_scale),
        )
    )
    try:
        length = float(np.linalg.norm(np.asarray(shift, dtype=float)))
    except (TypeError, ValueError):
        length = math.nan
    rows.append(
        (
            label + "_translation",
            "PASS" if abs(length - expected_shift_um) <= tolerance_um else "FAIL",
            "translation %r has length %.2f um, expected %.2f um (offset of the cut times the pixel size, +/- %.1f)"
            % (shift, length, expected_shift_um, tolerance_um),
        )
    )
    return rows


def status_check(var: str, ident: str, good: str | None = None) -> str:
    """Kernel code asserting that the status widget `var` of the notebook shows no error wording (and contains `good`, when given): the NucleiSky handlers catch their own
    exceptions and write them into a status HTML, so 'the click did not raise' proves nothing."""
    positive = (" and %r in _t" % good) if good else ""
    return (
        "import re\n_t = str(get_ipython().user_ns[%r].value)\n"
        "lcnb.check(%r, bool(_t.strip()) and not re.search(r'(?i)error|failed|not found|invalid|no confident', _t)%s, '%s: ' + re.sub('<[^>]+>', ' ', _t)[:220])\n"
        % (var, ident, positive, var)
    )
