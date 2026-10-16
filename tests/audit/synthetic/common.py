"""Shared helpers of the synthetic data generators (numpy, tifffile and the standard library only).

GENERIC: nothing here knows an app. Each app folder may copy this file next to its `make_<app>.py`.

* `write_tiff`: a TIFF with the scale written the way ImageJ/Fiji (spacing, unit), OME (PhysicalSize*) or plain TIFF resolution
  tags express it, so that Fiji, Napari and QuPath open it with a known calibration.
* `Suite`: collects datasets and cases and writes `cases.json` (the format of the apps' own `lc_tests/cases.json`),
  `ground_truth.json`, `README.md` and a copy of `check_ground_truth.py`.
* check builders (`chk_*`): the entries of the `checks` list of a dataset in `ground_truth.json`; `check_ground_truth.py` reads them.
"""

from __future__ import annotations

import json
import shutil
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Callable

import numpy as np
import tifffile

UNIT_FACTOR = {"um": 1.0, "µm": 1.0, "micron": 1.0, "nm": 1000.0, "mm": 0.001}  # length of 1 um in each unit
OME_UNIT = {"um": "µm", "µm": "µm", "micron": "µm", "nm": "nm", "mm": "mm"}
FORMATS = ("imagej", "ome", "plain")
OUTCOMES = ("works", "refused", "HUMAN")


def _rational(value: float) -> tuple[int, int]:
    """A positive number as an exact-enough TIFF rational (numerator, denominator)."""
    return 10**6, max(1, round(value * 10**6))


def write_tiff(
    path: Path,
    data: np.ndarray,
    axes: str,
    *,
    pixel_um: tuple[float, float] | None = None,
    z_um: float | None = None,
    t_s: float | None = None,
    unit: str = "um",
    fmt: str = "imagej",
    channel_names: Sequence[str] | None = None,
) -> Path:
    """Write `data` (axes named by `axes`, e.g. "CYX") with a calibration; returns the path actually written.

    pixel_um = (size of a pixel in Y, in X) in micrometres, converted to `unit` for the file; None = no calibration (plain TIFF
    resolution tags, nothing a host can read as a length). fmt "imagej" needs axes in the order TZCYXS and dtype uint8/uint16/float32;
    fmt "ome" writes `<stem>.ome.tif`; fmt "plain" writes only the axes (tifffile's own description) and no unit.
    """
    if fmt not in FORMATS:
        raise ValueError("fmt must be one of %s, got %r" % (FORMATS, fmt))
    if len(axes) != data.ndim:
        raise ValueError("axes %r do not match shape %s" % (axes, data.shape))
    path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "ome":
        path = path.with_name(path.name.replace(".tif", "") + ".ome.tif")
    if pixel_um is None or fmt == "plain":
        tifffile.imwrite(path, data, metadata={"axes": axes})
        return path
    if unit not in UNIT_FACTOR:
        raise ValueError("unknown unit %r" % unit)
    py, px = (v * UNIT_FACTOR[unit] for v in pixel_um)
    if fmt == "imagej":
        meta: dict[str, Any] = {
            "axes": axes,
            "unit": unit.replace("µ", "\\u00B5"),
        }  # the ImageJ description is ASCII: ImageJ itself writes micro as \u00B5
        if z_um is not None:
            meta["spacing"] = z_um * UNIT_FACTOR[unit]
        if t_s is not None:
            meta["finterval"] = t_s
        if channel_names:
            meta["Labels"] = list(channel_names)
        tifffile.imwrite(path, data, imagej=True, resolution=(_rational(px), _rational(py)), metadata=meta)
        return path
    meta = {
        "axes": axes,
        "PhysicalSizeX": px,
        "PhysicalSizeXUnit": OME_UNIT[unit],
        "PhysicalSizeY": py,
        "PhysicalSizeYUnit": OME_UNIT[unit],
    }
    if z_um is not None:
        meta.update(PhysicalSizeZ=z_um * UNIT_FACTOR[unit], PhysicalSizeZUnit=OME_UNIT[unit])
    if t_s is not None:
        meta.update(TimeIncrement=t_s, TimeIncrementUnit="s")
    if channel_names:
        meta["Channel"] = {"Name": list(channel_names)}
    tifffile.imwrite(path, data, ome=True, metadata=meta)
    fix_ome_uuid(path)
    return path


def fix_ome_uuid(path: Path) -> None:
    """tifffile writes a random UUID into the OME XML: replace it by one derived from the file name (same length, so every offset stays valid)
    and the output is the same bytes on every run."""
    import hashlib
    import re

    raw = path.read_bytes()
    fixed = raw
    for match in set(re.findall(rb"urn:uuid:[0-9a-f\-]{36}", raw)):
        digest = hashlib.sha1(path.name.encode() + match[:0]).hexdigest()
        new = (
            "%s-%s-%s-%s-%s" % (digest[:8], digest[8:12], digest[12:16], digest[16:20], digest[20:32])
        ).encode()
        fixed = fixed.replace(match, b"urn:uuid:" + new)
    if fixed != raw:
        path.write_bytes(fixed)


def read_calibration(path: Path) -> dict[str, Any]:
    """What a host can read back from a TIFF: shape, axes, dtype, pixel size (x, y), unit, z spacing, format. Independent of any app."""
    with tifffile.TiffFile(path) as tif:
        series = tif.series[0]
        page = tif.pages[0]
        out: dict[str, Any] = {
            "shape": list(series.shape),
            "axes": series.axes,
            "dtype": str(series.dtype),
            "format": "plain",
            "unit": None,
            "x_size": None,
            "y_size": None,
            "z_size": None,
        }
        if tif.is_ome:
            import xml.etree.ElementTree as ET

            pixels = next(e for e in ET.fromstring(tif.ome_metadata or "").iter() if e.tag.endswith("Pixels"))
            out.update(
                format="ome",
                unit=pixels.get("PhysicalSizeXUnit"),
                x_size=_f(pixels.get("PhysicalSizeX")),
                y_size=_f(pixels.get("PhysicalSizeY")),
                z_size=_f(pixels.get("PhysicalSizeZ")),
            )
        elif tif.is_imagej:
            meta = tif.imagej_metadata or {}
            xr, yr = page.tags["XResolution"].value, page.tags["YResolution"].value  # type: ignore[union-attr]
            out.update(
                format="imagej",
                unit=meta.get("unit"),
                x_size=xr[1] / xr[0],
                y_size=yr[1] / yr[0],
                z_size=meta.get("spacing"),
            )
        return out


def _f(text: str | None) -> float | None:
    return None if text is None else float(text)


# ------------------------------------------------------------------------------------------------ checks (read by check_ground_truth.py)
def chk_status(status: str, code: str | None = None, message_contains: str | None = None) -> dict[str, Any]:
    """The run ended with `status` (and error code / sentence for a refusal)."""
    out: dict[str, Any] = {"kind": "status", "status": status}
    if code:
        out["code"] = code
    if message_contains:
        out["message_contains"] = message_contains
    return out


def chk_value(
    key: str,
    expected: float | str | int | None = None,
    tol: float = 0.0,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
    rtol: float = 0.0,
    contains: str | None = None,
) -> dict[str, Any]:
    """A scalar of the `values` result: |actual - expected| <= tol + rtol*|expected|, or minimum <= actual <= maximum, or a text containing `contains`."""
    out: dict[str, Any] = {"kind": "value", "key": key, "tol": tol, "rtol": rtol}
    for name, v in (
        ("expected", expected),
        ("minimum", minimum),
        ("maximum", maximum),
        ("contains", contains),
    ):
        if v is not None:
            out[name] = v
    return out


def chk_matrix(
    expected: Sequence[Sequence[float]],
    atol_linear: float,
    atol_translation: float,
    result: str = "alignment",
) -> dict[str, Any]:
    """The 3x3 matrix_yx of an affine result: the linear 2x2 part within atol_linear, the translation column within atol_translation (px)."""
    return {
        "kind": "matrix",
        "result": result,
        "expected": [list(map(float, r)) for r in expected],
        "atol_linear": atol_linear,
        "atol_translation": atol_translation,
    }


def chk_table(
    result: str,
    key: str | None,
    truth_csv: str | None,
    columns: Sequence[str],
    rtol: float = 1e-9,
    atol: float = 1e-9,
    rows: int | None = None,
) -> dict[str, Any]:
    """A table result against a truth CSV (path relative to the dataset folder), row by `key`; only `columns` are compared."""
    out: dict[str, Any] = {
        "kind": "table",
        "result": result,
        "key": key,
        "truth_csv": truth_csv,
        "columns": list(columns),
        "rtol": rtol,
        "atol": atol,
    }
    if rows is not None:
        out["rows"] = rows
    return out


def chk_points_map(
    source: str,
    target: str,
    matrix: Sequence[Sequence[float]],
    target_shape: Sequence[int],
    tol_px: float,
    min_fraction: float,
) -> dict[str, Any]:
    """Points of result `source` moved by `matrix` (source px -> target px) must land within tol_px of points of result `target`."""
    return {
        "kind": "points_map",
        "source": source,
        "target": target,
        "matrix": [list(map(float, r)) for r in matrix],
        "target_shape": list(target_shape),
        "tol_px": tol_px,
        "min_fraction": min_fraction,
    }


def chk_message(result: str, contains: str) -> dict[str, Any]:
    return {"kind": "message", "result": result, "contains": contains}


def chk_host(param: str, expected: float | str | None, tol: float = 0.0) -> dict[str, Any]:
    """What a host showed in a form field or layer after opening the file (the driver writes it to report["host_observed"])."""
    return {"kind": "host_param", "param": param, "expected": expected, "tol": tol}


def chk_image_stat(result: str, stat: str, expected: float, tol: float) -> dict[str, Any]:
    """A statistic of an image result (stat: mean, max, min, shape0, shape1): used for pixel-exact claims."""
    return {"kind": "image_stat", "result": result, "stat": stat, "expected": expected, "tol": tol}


def chk_centroid(result: str, expected_yx: Sequence[float], tol_px: float) -> dict[str, Any]:
    """The intensity-weighted centroid (y, x) of an image result, in pixels."""
    return {"kind": "centroid", "result": result, "expected": list(expected_yx), "tol_px": tol_px}


def chk_files(pattern: str, means: Sequence[float], tol: float, axis: int = 0) -> dict[str, Any]:
    """Files written by the run (glob under the dataset folder) whose mean along `axis` slices are `means`."""
    return {"kind": "tiff_slice_means", "glob": pattern, "means": list(means), "tol": tol, "axis": axis}


# ------------------------------------------------------------------------------------------------ the suite
class Suite:
    """One app: its cases (`cases.json`) and the truth of every dataset (`ground_truth.json`)."""

    def __init__(self, app: str, out: Path, version: str) -> None:
        self.app, self.out, self.version = app, out, version
        self.fixtures = out / "fixtures"
        self.cases: list[dict[str, Any]] = []
        self.datasets: list[dict[str, Any]] = []
        self.no_case: dict[str, str] = (
            {}
        )  # tool id -> why this suite has no case for it (written as no_case.json, read by the sandbox `cases` check)
        self.fixtures.mkdir(parents=True, exist_ok=True)

    def rel(self, path: Path) -> str:
        """A path as the cases file writes it (relative to the folder of cases.json, with /)."""
        return path.relative_to(self.out).as_posix()

    def case(self, tool: str, inputs: dict[str, Any], expect: dict[str, Any], comment: str) -> int:
        """Add one case (a step of a dataset that has no truth of its own); returns its index in cases.json."""
        self.cases.append({"tool": tool, "inputs": inputs, "comment": comment, "expect": expect})
        return len(self.cases) - 1

    def dataset(
        self,
        ident: str,
        purpose: str,
        outcome: str,
        *,
        derivation: str,
        files: Sequence[Path] = (),
        tool: str | None = None,
        inputs: dict[str, Any] | None = None,
        expect: dict[str, Any] | None = None,
        checks: Sequence[dict[str, Any]] = (),
        host: dict[str, Any] | None = None,
        calibration: dict[str, Any] | None = None,
        outcome_text: str = "",
        host_checks: Sequence[dict[str, Any]] = (),
    ) -> None:
        """Register a dataset; with `tool` its primary case is added too (the one whose result `checks` judge)."""
        if outcome not in OUTCOMES:
            raise ValueError("outcome must be one of %s" % (OUTCOMES,))
        if any(d["id"] == ident for d in self.datasets):
            raise ValueError("duplicate dataset id %s" % ident)
        case_index = None
        if tool is not None:
            case_index = self.case(tool, inputs or {}, expect or {}, "[%s] %s" % (ident, purpose))
        record = {
            "id": ident,
            "app": self.app,
            "purpose": purpose,
            "expected": outcome,
            "expected_text": outcome_text,
            "derivation": derivation,
            "files": [self.rel(f) for f in files],
            "tool": tool,
            "primary_case": case_index,
            "checks": list(checks),
            "host_checks": list(host_checks),
        }
        if host:
            record["host"] = host  # type: ignore[assignment]
        if calibration:
            record["calibration"] = calibration  # type: ignore[assignment]
        self.datasets.append(record)

    def write(self, checker: Path) -> None:
        """cases.json, ground_truth.json, README.md and the checker next to them."""
        (self.out / "cases.json").write_text(
            json.dumps(self.cases, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        truth = {
            "app": self.app,
            "app_version": self.version,
            "format": 1,
            "how_to_check": "python check_ground_truth.py ground_truth.json --reports DIR  (DIR/<dataset id>.json = the JSON `labconstrictor-tools run` prints)",
            "datasets": self.datasets,
        }
        (self.out / "ground_truth.json").write_text(
            json.dumps(truth, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        if self.no_case:
            (self.out / "no_case.json").write_text(
                json.dumps(self.no_case, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )
        shutil.copy(checker, self.out / "check_ground_truth.py")
        (self.out / "README.md").write_text(readme(self), encoding="utf-8")


def readme(suite: Suite) -> str:
    """The README of the generated folder: one row per dataset."""
    lines = [
        "# Synthetic datasets for %s %s" % (suite.app, suite.version),
        "",
        "Generated by `make_synthetic.py` (deterministic: fixed seeds). `cases.json` has the format of the app's own `lc_tests/cases.json`;",
        "`ground_truth.json` says for every dataset what the right answer is and how it was derived; `check_ground_truth.py` compares a run to it.",
        "",
        "Outcomes: **works** = the run must complete with the stated numbers; **refused** = the run must fail with a clear sentence;",
        "**HUMAN** = the right behaviour is a judgement (or only a host can show it): a person looks.",
        "",
        "| id | purpose | expected | tool | files |",
        "|---|---|---|---|---|",
    ]
    for d in suite.datasets:
        outcome = d["expected"] + (": " + d["expected_text"] if d["expected_text"] else "")
        files = ", ".join("`%s`" % f.split("/", 1)[-1] for f in d["files"][:3]) + (
            " ..." if len(d["files"]) > 3 else ""
        )
        lines.append(
            "| %s | %s | %s | %s | %s |"
            % (d["id"], d["purpose"], outcome.replace("|", "/"), d["tool"] or "host only", files)
        )
    return "\n".join(lines) + "\n"


def disc_pixels(shape: tuple[int, int], cy: int, cx: int, radius: float) -> np.ndarray:
    """Boolean mask of the lattice points within `radius` of the integer centre (cy, cx): symmetric, so its centroid is exactly (cy, cx)."""
    yy, xx = np.ogrid[: shape[0], : shape[1]]
    return (yy - cy) ** 2 + (xx - cx) ** 2 <= radius**2


def standalone_main(build: Callable[[Path], Suite], here: Path, doc: str) -> int:
    """`python make_<app>.py OUT_DIR`: build the suite into OUT_DIR and write it (the checker is copied from next to the script or one folder up)."""
    if len(sys.argv) != 2:
        print(doc)
        return 2
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    checker = here / "check_ground_truth.py"
    build(out).write(checker if checker.exists() else here.parent / "check_ground_truth.py")
    return 0
