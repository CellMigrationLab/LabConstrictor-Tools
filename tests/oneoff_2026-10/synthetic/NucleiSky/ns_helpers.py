"""Shared pieces of the NucleiSky datasets: the scene wrapper, the expectations of a relocalisation and the writer of image pairs. NucleiSky-specific."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import numpy as np
import tifffile

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
from common import (
    Suite,
    chk_matrix,
    chk_points_map,
    chk_status,
    chk_value,
    write_tiff,
)  # noqa: E402
from ns_scene import (
    Nuclei,
    Transform,
    render_query,
    render_reference,  # noqa: E402
    sample_nuclei,
    to_image,
)

APP, VERSION = "NucleiSky", "0.1.4"
PS_REF = 0.65


class Scene:
    """A reference field, its nuclei, and the helpers to write images of it."""

    def __init__(self, seed: int, shape: tuple[int, int], count: int) -> None:
        self.rng = np.random.default_rng(seed)
        self.shape = shape
        self.nuclei: Nuclei = sample_nuclei(self.rng, shape, count)
        self.clean = render_reference(self.nuclei, shape)

    def reference(self, dtype: type = np.uint16) -> np.ndarray:
        return to_image(self.clean, self.rng, dtype)

    def query(self, t: Transform, dtype: type = np.uint16) -> tuple[np.ndarray, np.ndarray]:
        clean = render_query(self.nuclei, t)
        return to_image(clean, self.rng, dtype), clean


def expect_for(t: Transform, tol: float) -> dict[str, Any]:
    b = t.b
    return {
        "max_seconds": 600,
        "progress_events_min": 2,
        "results": {
            "values": {
                "rotation_deg": {"approx": t.theta_deg, "tol": 1.0},
                "scale": {"approx": 1.0, "tol": 0.05},
                "offset_y_px": {"approx": float(b[0]), "tol": tol},
                "offset_x_px": {"approx": float(b[1]), "tol": tol},
            }
        },
    }


def checks_for(
    t: Transform, tol: float, ref_shape: tuple[int, int], points_tol: float = 4.0, fraction: float = 0.8
) -> list[dict[str, Any]]:
    return [
        chk_status("COMPLETE"),
        chk_value("rotation_deg", t.theta_deg, 1.0),
        chk_value("scale", 1.0, 0.05),
        chk_value("offset_y_px", float(t.b[0]), tol),
        chk_value("offset_x_px", float(t.b[1]), tol),
        chk_matrix(t.matrix(), atol_linear=0.02 / t.zoom, atol_translation=tol),
        chk_points_map("query_nuclei", "reference_nuclei", t.matrix(), ref_shape, points_tol, fraction),
    ]


def derivation_for(t: Transform, what: str) -> str:
    return (
        "%s Both images are sampled from one analytic scene, the query on the grid reference = A @ query + b with A = R(%g deg) / %g and b = %s (reference pixels, y then x). "
        "Pixel sizes: reference %g um, query %g um, so the physical scale is 1 and the rotation %g degrees (atan2(A[1,0], A[0,0])). Tolerances (rotation 1 deg, scale 0.05, offsets in px) are those of the app's own cases."
        % (what, t.theta_deg, t.zoom, np.round(t.b, 3).tolist(), PS_REF, PS_REF / t.zoom, t.theta_deg)
    )


class Maker:
    def __init__(self, suite: Suite) -> None:
        self.s = suite
        self.f = suite.fixtures

    def pair(
        self,
        ident: str,
        scene: Scene,
        t: Transform,
        *,
        dtype: type = np.uint16,
        unit: str = "um",
        fmt: str = "imagej",
        calibrated: bool = True,
        ome: bool = False,
        pixel_unit: bool = False,
    ) -> tuple[list[Path], list[Path], np.ndarray]:
        """Write <ident>_reference.tif and <ident>_query.tif (with the calibration of the scene) and return (reference files, query files, query clean)."""
        ref = scene.reference(dtype)
        query, q_clean = scene.query(t, dtype)
        ps_q = PS_REF / t.zoom
        px_ref, px_q = ((PS_REF, PS_REF), (ps_q, ps_q)) if calibrated else (None, None)
        if pixel_unit:
            files = []
            for name, data in (("reference", ref), ("query", query)):
                p = self.f / ("%s_%s.tif" % (ident, name))
                tifffile.imwrite(
                    p, data, imagej=True, resolution=(1.0, 1.0), metadata={"axes": "YX", "unit": "pixel"}
                )
                files.append([p])
            return files[0], files[1], q_clean
        rf = [
            write_tiff(self.f / ("%s_reference.tif" % ident), ref, "YX", pixel_um=px_ref, unit=unit, fmt=fmt)
        ]
        qf = [write_tiff(self.f / ("%s_query.tif" % ident), query, "YX", pixel_um=px_q, unit=unit, fmt=fmt)]
        if ome and calibrated:
            rf.append(
                write_tiff(
                    self.f / "ome" / ("%s_reference.tif" % ident),
                    ref,
                    "YX",
                    pixel_um=px_ref,
                    unit=unit,
                    fmt="ome",
                )
            )
            qf.append(
                write_tiff(
                    self.f / "ome" / ("%s_query.tif" % ident),
                    query,
                    "YX",
                    pixel_um=px_q,
                    unit=unit,
                    fmt="ome",
                )
            )
        return rf, qf, q_clean

    def works(
        self,
        ident: str,
        purpose: str,
        rf: list[Path],
        qf: list[Path],
        t: Transform,
        ref_shape: tuple[int, int],
        what: str,
        tol: float = 4.0,
        extra: dict[str, Any] | None = None,
        extra_files: list[Path] | None = None,
        checks_extra: list[dict[str, Any]] | None = None,
        host: dict[str, Any] | None = None,
        host_checks: list[dict[str, Any]] | None = None,
        calibration: dict[str, Any] | None = None,
        points_tol: float = 4.0,
        fraction: float = 0.8,
    ) -> None:
        inputs = {
            "reference": self.s.rel(rf[0]),
            "query": self.s.rel(qf[0]),
            "reference_pixel_size_um": PS_REF,
            "query_pixel_size_um": PS_REF / t.zoom,
            **(extra or {}),
        }
        expect = expect_for(t, tol)
        checks = checks_for(t, tol, ref_shape, points_tol, fraction) + (checks_extra or [])
        if checks_extra:
            for key, value in {c["key"]: c["expected"] for c in checks_extra if c["kind"] == "value"}.items():
                expect["results"]["values"][key] = value
        self.s.dataset(
            ident,
            purpose,
            "works",
            derivation=derivation_for(t, what),
            files=rf + qf + (extra_files or []),
            tool="relocalize",
            inputs=inputs,
            expect=expect,
            checks=checks,
            host=host,
            host_checks=host_checks or [],
            calibration=calibration,
        )

    def refused(
        self,
        ident: str,
        purpose: str,
        inputs: dict[str, Any],
        files: list[Path],
        derivation: str,
        code: str | None = None,
        contains: str | None = None,
        text: str = "",
    ) -> None:
        expect: dict[str, Any] = {
            "status": "FAILED",
            **({"code": code} if code else {}),
            **({"message_contains": contains} if contains else {}),
        }
        self.s.dataset(
            ident,
            purpose,
            "refused",
            derivation=derivation,
            files=files,
            tool="relocalize",
            inputs=inputs,
            expect=expect,
            checks=[chk_status("FAILED", code, contains)],
            outcome_text=text or "refused%s" % (": " + code if code else ""),
        )
