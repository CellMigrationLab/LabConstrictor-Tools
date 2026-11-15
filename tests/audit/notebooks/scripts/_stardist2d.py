"""Shared pieces of the StarDist2D click scripts: synthetic images of KNOWN content (bright discs on a noisy background, so the number of nuclei is known
from the construction, not from the model under test), the reader of the executed notebook the harness saves before the oracle runs, and the version of the
checkout's construct.yaml.

Images (written by `make_inputs` into the scratch work folder):
* small/small_blobs.tif: 256x256 uint16, SMALL_COUNT discs of radius 9 (section 6.1, single images);
* big/stack.tif: a TWO-frame 1024x1024 uint16 stack, FRAME_COUNTS discs in frame 0 and frame 1 (section 6.2 with Is_stack and block_size 512: each frame
  is split into blocks, and the two frames have different counts so that frame 1 cannot pass by repeating frame 0).
"""

import json
from pathlib import Path
from typing import Any

SMALL_SHAPE = (256, 256)
SMALL_COUNT = 12
BIG_SHAPE = (1024, 1024)
FRAME_COUNTS = (40, 80)
RADIUS = 9
SPACING = 34  # minimum distance between disc centres: no two discs touch, so a good model finds each one
TOLERANCE = 0.3  # a pretrained fluorescence model must find the known count within +/- 30 %


def blobs(shape: tuple[int, int], count: int, seed: int) -> Any:
    """A uint16 image of `count` soft-edged discs (radius RADIUS, +900 over a background of 100 +/- 6), centres at least SPACING apart."""
    import numpy as np

    rng = np.random.default_rng(seed)
    image = rng.normal(100.0, 6.0, shape)
    margin = RADIUS + 4
    centres: list[tuple[int, int]] = []
    tries = 0
    while len(centres) < count and tries < 200000:
        tries += 1
        cy = int(rng.integers(margin, shape[0] - margin))
        cx = int(rng.integers(margin, shape[1] - margin))
        if all((cy - a) ** 2 + (cx - b) ** 2 >= SPACING**2 for a, b in centres):
            centres.append((cy, cx))
    if len(centres) < count:
        raise RuntimeError("could not place %d discs in %s" % (count, shape))
    half = RADIUS + 2
    yy, xx = np.mgrid[-half : half + 1, -half : half + 1]
    disc = np.clip(RADIUS + 0.5 - np.hypot(yy, xx), 0.0, 1.0) * 900.0
    for cy, cx in centres:
        image[cy - half : cy + half + 1, cx - half : cx + half + 1] += disc
    return image.clip(0, 65535).astype(np.uint16)


def make_inputs(work: Path) -> dict[str, Any]:
    """Write the synthetic images and return every path the script types into the forms (all under the scratch work folder, inputs apart from outputs)."""
    import numpy as np
    import tifffile

    root = work / "sd2d_inputs"
    small, big = root / "small", root / "big"
    small.mkdir(parents=True, exist_ok=True)
    big.mkdir(parents=True, exist_ok=True)
    tifffile.imwrite(small / "small_blobs.tif", blobs(SMALL_SHAPE, SMALL_COUNT, 3))
    stack = np.stack([blobs(BIG_SHAPE, n, 5 + i) for i, n in enumerate(FRAME_COUNTS)])
    tifffile.imwrite(big / "stack.tif", stack)
    results = work / "sd2d_results"
    return {
        "base": str(work / "sd2d"),
        "small_dir": str(small),
        "big_dir": str(big),
        "pred_trained": str(results / "pred_trained"),
        "pred_fluo": str(results / "pred_fluo"),
        "pred_cml": str(results / "pred_cml"),
        "big_out": str(results / "big"),
        "small_count": SMALL_COUNT,
        "frame_counts": list(FRAME_COUNTS),
    }


def construct_version(ctx: Any) -> str:
    """The `version:` of construct.yaml in the checkout at the tag (what the installed app must say about itself)."""
    import yaml

    return str(yaml.safe_load((ctx.src / "construct.yaml").read_text(encoding="utf-8"))["version"])


def output_text(output: dict[str, Any]) -> str:
    """Every text an output of an executed cell carries: stream text, and each mimetype of display data or results (text/plain, text/markdown, text/html...)."""
    parts = []
    if "text" in output:
        parts.append("".join(output["text"]) if isinstance(output["text"], list) else str(output["text"]))
    for value in (output.get("data") or {}).values():
        parts.append("".join(value) if isinstance(value, list) else str(value))
    if output.get("output_type") == "error":
        parts.append("%s: %s" % (output.get("ename"), output.get("evalue")))
    return "\n".join(parts)


def executed_cells(ctx: Any, relative: str) -> tuple[Path, list[tuple[int, list[dict[str, Any]]]] | None]:
    """The executed notebook the harness wrote (results/<app>/executed/<notebook>.ipynb, written before the oracle runs) and (index, outputs) of each of its
    ORIGINAL cells (the harness appends its stage cells after them, so the first N cells are the notebook's own, N counted in the checkout at the tag).
    None when the file does not exist (check_scripts, or the run did not reach the end)."""
    from nb_common import read_cells, sanitise

    path = Path(ctx.results) / ctx.app / "executed" / (sanitise(ctx.notebook) + ".ipynb")
    if not path.is_file():
        return path, None
    original = len(read_cells(Path(ctx.src) / relative))
    document = json.loads(path.read_text(encoding="utf-8"))
    return path, [(i, cell.get("outputs", [])) for i, cell in enumerate(document["cells"][:original])]
