"""Shared pieces of the VLab4Mic datasets: spot images, the synthetic structure file and the case builders. VLab4Mic-specific except `spots_image` and `block_mean`."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import numpy as np
from scipy.ndimage import gaussian_filter

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
from common import (
    Suite,
    chk_status,
)  # noqa: E402

APP, VERSION = "LabConstrictor-VLab4Mic", "0.1.6"
SIZE = 160
PIXEL_NM = 20


def spots_image(size: int = SIZE, seed: int = 21, sigma: float = 3.0, count: int = 14) -> np.ndarray:
    """Bright spots (sigma 3 px) at known random positions, scaled to a maximum of 4000 (uint16)."""
    rng = np.random.default_rng(seed)
    field = np.zeros((size, size))
    for y, x in rng.uniform(15, size - 15, (count, 2)):
        field[int(y), int(x)] = rng.uniform(0.6, 1.0)
    out = gaussian_filter(field, sigma)
    return (out / out.max() * 4000).astype(np.uint16)


def block_mean(image: np.ndarray, k: int = 2) -> np.ndarray:
    """The same field seen with k times larger pixels: the mean of each k x k block (exact, no interpolation)."""
    h, w = image.shape[0] // k * k, image.shape[1] // k * k
    return (
        image[:h, :w]
        .reshape(h // k, k, w // k, k)
        .astype(np.float64)
        .mean(axis=(1, 3))
        .round()
        .astype(np.uint16)
    )


def mini_ring_cif(n_atoms: int = 24, radius_a: float = 150.0) -> str:
    """A minimal mmCIF: `n_atoms` lysine CA atoms (the target of the default probe, an NHS ester) on a ring of `radius_a` angstroms in one chain."""
    lines = [
        "data_MINIRING",
        "_entity.id 1",
        "_entity.pdbx_description 'mini ring'",
        "_entity_poly.pdbx_strand_id A",
        "loop_",
        "_atom_site.group_PDB",
        "_atom_site.id",
        "_atom_site.type_symbol",
        "_atom_site.label_atom_id",
        "_atom_site.label_alt_id",
        "_atom_site.label_comp_id",
        "_atom_site.label_asym_id",
        "_atom_site.label_entity_id",
        "_atom_site.label_seq_id",
        "_atom_site.pdbx_PDB_ins_code",
        "_atom_site.Cartn_x",
        "_atom_site.Cartn_y",
        "_atom_site.Cartn_z",
        "_atom_site.occupancy",
        "_atom_site.B_iso_or_equiv",
        "_atom_site.auth_seq_id",
        "_atom_site.auth_asym_id",
        "_atom_site.pdbx_PDB_model_num",
    ]
    for i in range(n_atoms):
        a = 2 * np.pi * i / n_atoms
        lines.append(
            f"ATOM {i + 1} C CA . LYS A 1 {i + 1} ? {radius_a * np.cos(a):.3f} {radius_a * np.sin(a):.3f} 0.000 1.00 20.00 {i + 1} A 1"
        )
    return "\n".join(lines) + "\n"


def compare(
    s: Suite,
    ident: str,
    purpose: str,
    ref: Path,
    sim: Path,
    px_ref: float,
    px_sim: float,
    checks: list[dict[str, Any]],
    values: dict[str, Any],
    derivation: str,
    files: list[Path] | None = None,
    outcome: str = "works",
    host: dict[str, Any] | None = None,
) -> None:
    s.dataset(
        ident,
        purpose,
        outcome,
        derivation=derivation,
        files=files or [ref, sim],
        tool="compare_images",
        inputs={
            "reference": s.rel(ref),
            "simulated": s.rel(sim),
            "reference_pixel_size_um": px_ref,
            "simulated_pixel_size_um": px_sim,
        },
        expect={"max_seconds": 120, "results": {"values": values}},
        checks=[chk_status("COMPLETE")] + checks,
        host=host,
    )


def refused(
    s: Suite,
    ident: str,
    purpose: str,
    ref: Path,
    sim: Path,
    px_ref: float,
    px_sim: float,
    code: str | None,
    contains: str | None,
    derivation: str,
    text: str = "",
) -> None:
    expect: dict[str, Any] = {
        "status": "FAILED",
        **({"code": code} if code else {}),
        **({"message_contains": contains} if contains else {}),
    }
    s.dataset(
        ident,
        purpose,
        "refused",
        derivation=derivation,
        files=[ref, sim],
        tool="compare_images",
        inputs={
            "reference": s.rel(ref),
            "simulated": s.rel(sim),
            "reference_pixel_size_um": px_ref,
            "simulated_pixel_size_um": px_sim,
        },
        expect=expect,
        checks=[chk_status("FAILED", code, contains)],
        outcome_text=text or "refused%s" % (": " + code if code else ""),
    )
