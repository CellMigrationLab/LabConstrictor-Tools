"""A synthetic nuclei field with an exactly known geometry, rendered from an ANALYTIC scene (no interpolation): GENERIC (numpy, scipy).

Nuclei are Gaussian blobs at known continuous positions. The reference is the scene sampled on the pixel grid; the query is the same scene
sampled on a grid that is rotated, scaled and shifted by a KNOWN similarity transform, so the transform the tool must find is known exactly:

    reference_px(y, x) = A @ query_px(y, x) + b,        A = R(theta) / zoom,  R = [[cos, -sin], [sin, cos]]  (rows: y, x)

`b = centre - A @ query_centre` with the query centre at ((ph - 1) / 2, (pw - 1) / 2) in its own pixels. Pixel centres sit at integer coordinates.
The query's pixel size is the reference's divided by `zoom`, so the PHYSICAL scale of the transform is 1 and its rotation is theta.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import ndimage

MIN_SEPARATION_PX = 36.0  # nuclei never touch: every nucleus stays one connected object at the mask threshold
MASK_LEVEL = 0.25  # mask = scene above this level (amplitudes are 0.5..1, so every nucleus is above it)
NOISE_SD = 0.01


@dataclass(frozen=True)
class Nuclei:
    y: np.ndarray
    x: np.ndarray
    sigma: np.ndarray
    amp: np.ndarray

    def __len__(self) -> int:
        return len(self.y)


@dataclass(frozen=True)
class Transform:
    """query pixel -> reference pixel."""

    theta_deg: float
    zoom: float
    centre: tuple[float, float]  # in reference pixels
    shape: tuple[int, int]  # query shape

    @property
    def A(self) -> np.ndarray:
        t = np.deg2rad(self.theta_deg)
        return np.array([[np.cos(t), -np.sin(t)], [np.sin(t), np.cos(t)]]) / self.zoom

    @property
    def b(self) -> np.ndarray:
        q_centre = np.array([(self.shape[0] - 1) / 2, (self.shape[1] - 1) / 2])
        return np.array(self.centre) - self.A @ q_centre

    def matrix(self) -> list[list[float]]:
        m = np.eye(3)
        m[:2, :2], m[:2, 2] = self.A, self.b
        return m.tolist()

    def to_reference(self, points_yx: np.ndarray) -> np.ndarray:
        return points_yx @ self.A.T + self.b


def sample_nuclei(
    rng: np.random.Generator, shape: tuple[int, int], count: int, margin: float = 45.0
) -> Nuclei:
    """`count` nuclei at random positions at least MIN_SEPARATION_PX apart (rejection sampling on a grid), sigma 5-9 px, amplitude 0.5-1."""
    cell = MIN_SEPARATION_PX
    grid: dict[tuple[int, int], list[tuple[float, float]]] = {}
    points: list[tuple[float, float]] = []
    while len(points) < count:
        y, x = rng.uniform(margin, shape[0] - margin), rng.uniform(margin, shape[1] - margin)
        gy, gx = int(y // cell), int(x // cell)
        near = (p for dy in (-1, 0, 1) for dx in (-1, 0, 1) for p in grid.get((gy + dy, gx + dx), ()))
        if all((y - py) ** 2 + (x - px) ** 2 >= cell**2 for py, px in near):
            grid.setdefault((gy, gx), []).append((y, x))
            points.append((y, x))
    p = np.array(points)
    return Nuclei(p[:, 0], p[:, 1], rng.uniform(5, 9, count), rng.uniform(0.5, 1.0, count))


def render_reference(n: Nuclei, shape: tuple[int, int]) -> np.ndarray:
    """The noise-free scene on the reference grid (float, 0..1)."""
    clean = np.zeros(shape)
    for y, x, s, a in zip(n.y, n.x, n.sigma, n.amp):
        y0, y1, x0, x1 = (
            max(0, int(y - 4 * s)),
            min(shape[0], int(y + 4 * s) + 2),
            max(0, int(x - 4 * s)),
            min(shape[1], int(x + 4 * s) + 2),
        )
        yy, xx = np.ogrid[y0:y1, x0:x1]
        clean[y0:y1, x0:x1] = np.maximum(
            clean[y0:y1, x0:x1], a * np.exp(-((yy - y) ** 2 + (xx - x) ** 2) / (2 * s * s))
        )
    return clean


def render_query(n: Nuclei, t: Transform) -> np.ndarray:
    """The noise-free scene on the query grid (float, 0..1): every query pixel is evaluated at its exact reference position."""
    qy, qx = np.mgrid[0 : t.shape[0], 0 : t.shape[1]].astype(float)
    ry = t.A[0, 0] * qy + t.A[0, 1] * qx + t.b[0]
    rx = t.A[1, 0] * qy + t.A[1, 1] * qx + t.b[1]
    lo_y, hi_y, lo_x, hi_x = ry.min() - 40, ry.max() + 40, rx.min() - 40, rx.max() + 40
    clean = np.zeros(t.shape)
    for y, x, s, a in zip(n.y, n.x, n.sigma, n.amp):
        if lo_y <= y <= hi_y and lo_x <= x <= hi_x:
            clean = np.maximum(clean, a * np.exp(-((ry - y) ** 2 + (rx - x) ** 2) / (2 * s * s)))
    return clean


def to_image(clean: np.ndarray, rng: np.random.Generator, dtype: type = np.uint16) -> np.ndarray:
    """Add noise (sd 0.01 of the amplitude) and scale: uint16 0..4000, uint8 0..200, float32 0..1."""
    noisy = clean + rng.normal(0, NOISE_SD, clean.shape)
    if dtype == np.float32:
        return noisy.astype(np.float32)
    top = 4000.0 if dtype == np.uint16 else 200.0
    return np.clip(noisy * top, 0, top * 1.2).round().astype(dtype)


def labels_of(clean: np.ndarray, dtype: type = np.uint16) -> np.ndarray:
    """The truth segmentation: connected objects of the noise-free scene above MASK_LEVEL (labels 1..n in raster order)."""
    return ndimage.label(clean > MASK_LEVEL)[0].astype(dtype)


def label_centroids(labels: np.ndarray) -> np.ndarray:
    n = int(labels.max())
    return np.array(ndimage.center_of_mass(labels > 0, labels, range(1, n + 1))) if n else np.zeros((0, 2))


def inside(points_yx: np.ndarray, box: tuple[int, int, int, int]) -> np.ndarray:
    """Which points lie in the box rows r0:r1, columns c0:c1 (half-open, as a mask slice)."""
    r0, r1, c0, c1 = box
    return (
        (points_yx[:, 0] >= r0 - 0.5)
        & (points_yx[:, 0] < r1 - 0.5)
        & (points_yx[:, 1] >= c0 - 0.5)
        & (points_yx[:, 1] < c1 - 0.5)
    )


def box_clear_of(points_yx: np.ndarray, box: tuple[int, int, int, int], margin: float = 3.0) -> bool:
    """True when no point is within `margin` px of an edge of the box (so whether it is inside does not depend on rounding)."""
    r0, r1, c0, c1 = box
    y, x = points_yx[:, 0], points_yx[:, 1]
    near = lambda v, edge: np.abs(v - (edge - 0.5)) < margin  # noqa: E731
    return not bool((near(y, r0) | near(y, r1) | near(x, c0) | near(x, c1)).any())
