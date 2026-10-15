"""Guess the Condition datasets about what the game reads and shows: scan rules, a corrupt file, every axes and bit depth, a big image."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import numpy as np
import tifffile

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
from common import (
    chk_image_stat,
    chk_status,
    chk_value,
    write_tiff,
)  # noqa: E402

APP, VERSION = "GuessTheCondition", "0.0.1"
Counts = dict[tuple[str, str], int]  # (condition, repeat) -> images
SEED = 11


from gtc_core import Games, picture  # noqa: E402


def add_scan(g: Games) -> None:
    s = g.s
    root = s.fixtures / "gtc_scan_rules" / "experiment"
    rng = np.random.default_rng(3)
    files = []
    layout = {
        "Control/R1/a.tif": 1,
        "Control/R1/b.TIF": 1,
        "Control/R1/c.tiff": 1,
        "Mutant/R1/x.tif": 1,
        "Mutant/R1/y.tif": 1,
        "Mutant/R2/z.tif": 1,
    }
    for name in layout:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        tifffile.imwrite(path, picture(rng, 300))
        files.append(path)
    ignored = {
        "Control/R1/._a.tif": b"AppleDouble junk",
        "Control/R1/.hidden.tif": b"x",
        "Control/R1/notes.txt": b"text",
        "Control/R1/preview.png": b"\x89PNG",
        "Control/_skipped/R1/q.tif": b"x",
        "Mutant/.git/R1/q.tif": b"x",
        "Mutant/R1/Thumbs.db": b"x",
    }
    for name, raw in ignored.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    s.dataset(
        "gtc_scan_rules",
        "hidden files, non-TIFF files, a folder starting with _ and upper-case/.tiff extensions around 6 real images",
        "works",
        derivation="Counted by construction: 6 images (.tif, .TIF, .tiff count; ._x, .hidden, .txt, .png, Thumbs.db and folders starting with . or _ do not).",
        files=files,
        tool="prepare_game",
        inputs={
            "experiment_folder": s.rel(root),
            "results_folder": s.rel(g.results),
            "user_name": "scan",
            "restart": True,
            "random_seed": SEED,
        },
        expect={"results": {"values": {"images": 6, "to_guess": 2}}},
        checks=[chk_status("COMPLETE"), chk_value("images", 6), chk_value("to_guess", 2)],
    )
    bad = s.fixtures / "gtc_corrupt" / "experiment"
    rng = np.random.default_rng(4)
    for cond in ("Control", "Mutant"):
        folder = bad / cond / "R1"
        folder.mkdir(parents=True, exist_ok=True)
        tifffile.imwrite(folder / "good.tif", picture(rng, 300 if cond == "Control" else 900, (16, 16)))
        (folder / "broken.tif").write_bytes(b"II*\x00this is not a tiff at all")
    root_files = [bad / c / "R1" / n for c in ("Control", "Mutant") for n in ("good.tif", "broken.tif")]
    g.prepare(bad, "corrupt", 100, "[gtc_corrupt] prepare: 4 files, 2 of them broken")
    s.dataset(
        "gtc_corrupt",
        "two conditions, each with a good and an undecodable .tif: the broken ones are skipped, the game goes on",
        "works",
        derivation="An unreadable file must not stop the game: the first readable image is served (16x16, one channel, normalised float32), the broken ones are left out and named.",
        files=root_files,
        tool="play_round",
        inputs={"results_folder": s.rel(g.results), "user_name": "corrupt"},
        expect={"results": {"image": {"shape": [16, 16], "dtype": "float32"}}},
        checks=[
            chk_status("COMPLETE"),
            chk_image_stat("image", "shape0", 16, 0),
            chk_image_stat("image", "shape1", 16, 0),
        ],
    )


def add_image_kinds(g: Games) -> None:
    s = g.s
    rng = np.random.default_rng(9)
    y, x = 30, 50
    gap = max(1, round(0.02 * x))
    ramp = np.linspace(100, 4000, y * x).reshape(y, x)

    def stack(shape: tuple[int, ...], dtype: Any) -> np.ndarray:
        top = float(np.iinfo(dtype).max) if np.issubdtype(dtype, np.integer) else 1000.0
        planes = ramp / 4000 * top * 0.8 * rng.uniform(0.8, 1.2, shape[:-2] + (1, 1))
        return np.clip(planes + rng.normal(0, top * 0.01, shape), 0, top).astype(dtype)

    kinds: list[tuple[str, np.ndarray, str, tuple[int, int], str]] = [
        ("yx_u8", stack((y, x), np.uint8), "YX", (y, x), "an 8-bit 2D image"),
        ("yx_u16", stack((y, x), np.uint16), "YX", (y, x), "a 16-bit 2D image"),
        ("yx_f32", stack((y, x), np.float32), "YX", (y, x), "a 32-bit float 2D image"),
        (
            "cyx3",
            stack((3, y, x), np.uint16),
            "CYX",
            (y, 3 * x + 2 * gap),
            "3 channels (shown side by side, 1 px gap)",
        ),
        ("tyx", stack((4, y, x), np.uint16), "TYX", (y, x), "a time series (maximum projection)"),
        ("zyx", stack((5, y, x), np.uint16), "ZYX", (y, x), "a z-stack (maximum projection)"),
        (
            "tzcyx",
            stack((2, 3, 2, y, x), np.uint16),
            "TZCYX",
            (y, 2 * x + gap),
            "T x Z x 2 channels (T and Z projected, channels side by side)",
        ),
        (
            "rgb",
            np.moveaxis(stack((3, y, x), np.uint8), 0, -1),
            "YXS",
            (y, x),
            "an RGB image: the colour axis S is not C, so it is max-projected (colour is lost)",
        ),
    ]
    for name, data, axes, shape, what in kinds:
        ident = "gtc_view_" + name
        root = s.fixtures / ident / "experiment"
        paths = []
        for cond in ("Control", "Mutant"):
            path = root / cond / "R1" / "img.tif"
            paths.append(
                write_tiff(
                    path,
                    data,
                    axes,
                    pixel_um=(0.5, 0.5),
                    unit="um",
                    fmt="imagej" if data.dtype != np.float64 else "plain",
                )
            )
        user = "view_" + name
        g.prepare(root, user, 100, "[%s] prepare" % ident)
        hostnote = (
            "RGB: whether the colour axis should be shown as colour is a design question"
            if name == "rgb"
            else None
        )
        s.dataset(
            ident,
            "the first image shown for %s" % what,
            "works" if name != "rgb" else "HUMAN",
            derivation="Documented display rule (images.py): Z and T are max-projected, other non-C axes dropped by max, "
            "channels tiled side by side with a gap of max(1, round(0.02 X)) px; the output is float32 scaled to [0, 1] (1st..99.99th percentile): shape %s, max 1.0."
            % (shape,),
            files=paths,
            tool="play_round",
            inputs={"results_folder": s.rel(g.results), "user_name": user},
            expect={"results": {"image": {"shape": list(shape), "dtype": "float32"}}},
            checks=[
                chk_status("COMPLETE"),
                chk_image_stat("image", "shape0", shape[0], 0),
                chk_image_stat("image", "shape1", shape[1], 0),
                chk_image_stat("image", "max", 1.0, 1e-6),
                chk_image_stat("image", "min", 0.0, 1e-6),
            ],
            outcome_text=("HUMAN: " + hostnote) if hostnote else "",
        )
    for name, data, shape, what in (
        (
            "unlabelled_3planes",
            stack((3, y, x), np.uint16),
            (y, 3 * x + 2 * gap),
            "3 planes, no axis metadata: a short leading axis is read as channels",
        ),
        (
            "unlabelled_8planes",
            stack((8, y, x), np.uint16),
            (y, x),
            "8 planes, no axis metadata: read as a z-stack (maximum)",
        ),
    ):
        ident = "gtc_view_" + name
        root = s.fixtures / ident / "experiment"
        paths = []
        for cond in ("Control", "Mutant"):
            path = root / cond / "R1" / "img.tif"
            path.parent.mkdir(parents=True, exist_ok=True)
            tifffile.imwrite(path, data)  # no metadata at all
            paths.append(path)
        user = "view_" + name
        g.prepare(root, user, 100, "[%s] prepare" % ident)
        s.dataset(
            ident,
            "the first image shown for %s" % what,
            "works",
            derivation="images.py: unnamed 3D data with at most 5 planes is read as channels, longer as z. Shape %s."
            % (shape,),
            files=paths,
            tool="play_round",
            inputs={"results_folder": s.rel(g.results), "user_name": user},
            expect={"results": {"image": {"shape": list(shape), "dtype": "float32"}}},
            checks=[
                chk_status("COMPLETE"),
                chk_image_stat("image", "shape0", shape[0], 0),
                chk_image_stat("image", "shape1", shape[1], 0),
            ],
        )
    flat = s.fixtures / "gtc_view_flat" / "experiment"
    fp = []
    for cond in ("Control", "Mutant"):
        path = flat / cond / "R1" / "img.tif"
        path.parent.mkdir(parents=True, exist_ok=True)
        tifffile.imwrite(path, np.full((y, x), 500, np.uint16))
        fp.append(path)
    g.prepare(flat, "view_flat", 100, "[gtc_view_flat] prepare")
    s.dataset(
        "gtc_view_flat",
        "a flat (all-equal) image",
        "works",
        derivation="images.py: a flat channel becomes all zeros instead of dividing by zero: max 0.",
        files=fp,
        tool="play_round",
        inputs={"results_folder": s.rel(g.results), "user_name": "view_flat"},
        expect={"results": {"image": {"shape": [y, x], "dtype": "float32", "max": 0.0}}},
        checks=[chk_status("COMPLETE"), chk_image_stat("image", "max", 0.0, 1e-9)],
    )
    nan = stack((y, x), np.float32)
    nan[5:9, 5:9] = np.nan
    npaths = []
    nroot = s.fixtures / "gtc_view_nan" / "experiment"
    for cond in ("Control", "Mutant"):
        npaths.append(write_tiff(nroot / cond / "R1" / "img.tif", nan, "YX", pixel_um=(0.5, 0.5)))
    g.prepare(nroot, "view_nan", 100, "[gtc_view_nan] prepare")
    s.dataset(
        "gtc_view_nan",
        "a float image with a block of NaN",
        "HUMAN",
        derivation="Not specified: NaN pixels may be shown black, the image skipped or refused. The check only requires that the picture is not wholly NaN "
        "(a normalisation that turned everything to NaN would show a blank game).",
        files=npaths,
        tool="play_round",
        inputs={"results_folder": s.rel(g.results), "user_name": "view_nan"},
        expect={"results": {"image": {"shape": [y, x], "dtype": "float32"}}},
        checks=[
            chk_status("COMPLETE"),
            chk_image_stat("image", "shape0", y, 0),
            chk_image_stat("image", "shape1", x, 0),
        ],
        outcome_text="HUMAN: how a NaN block is displayed",
    )


def add_stress(g: Games) -> None:
    s = g.s
    rng = np.random.default_rng(12)
    root = s.fixtures / "gtc_stress_big" / "experiment"
    paths = []
    for cond, level in (("Control", 800), ("Mutant", 1600)):
        path = root / cond / "R1" / "img.tif"
        path.parent.mkdir(parents=True, exist_ok=True)
        tifffile.imwrite(path, rng.normal(level, 60, (3000, 3000)).clip(0, 65535).astype(np.uint16))
        paths.append(path)
    g.prepare(root, "stress", 100, "[gtc_stress_big] prepare: two 3000x3000 16-bit images")
    s.dataset(
        "gtc_stress_big",
        "stress: two 3000x3000 uint16 images (18 MB each)",
        "works",
        derivation="The displayed image keeps the full size: shape (3000, 3000), float32 in [0, 1].",
        files=paths,
        tool="play_round",
        inputs={"results_folder": s.rel(g.results), "user_name": "stress"},
        expect={"max_seconds": 120, "results": {"image": {"shape": [3000, 3000], "dtype": "float32"}}},
        checks=[
            chk_status("COMPLETE"),
            chk_image_stat("image", "shape0", 3000, 0),
            chk_image_stat("image", "shape1", 3000, 0),
        ],
    )
