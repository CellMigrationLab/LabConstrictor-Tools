#!/usr/bin/env python3
"""Synthetic datasets for the VLab4Mic tools `compare_images` and `simulate_sample` (derived from their declared inputs).

    python make_vlab4mic.py OUT_DIR       # standalone: numpy, scipy, tifffile; common.py and check_ground_truth.py next to it or one folder up

`compare_images`: images built from spots at known positions, so that the right similarity is known without running anything:
the same image (SSIM 1, Pearson 1), a gain and offset (Pearson 1), an inverted image (Pearson -1), the same field at half the resolution
with the right pixel sizes (high Pearson) and with the pixel sizes of a unit mistake (the field no longer matches: low Pearson).
`simulate_sample` runs offline on a synthetic structure file (`mini_ring.cif`, a ring of 24 lysines): the image size and pixel size
follow from the modality and the sample size alone (size = sample / pixel). Needs no PDB download.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
from common import (
    Suite,
    chk_centroid,
    chk_image_stat,
    chk_status,
    chk_value,
    standalone_main,
)  # noqa: E402

APP, VERSION = "LabConstrictor-VLab4Mic", "0.1.6"
SIZE = 160
PIXEL_NM = 20


from vm_common import mini_ring_cif  # noqa: E402
from vm_compare import add_compare  # noqa: E402


def add_simulate(s: Suite) -> None:
    cif = s.fixtures / "vm_mini_ring.cif"
    cif.write_text(mini_ring_cif(), encoding="utf-8")
    base = {"structure_file": s.rel(cif), "number_of_particles": 1, "random_seed": 3, "noise": False}
    rows: tuple[tuple[str, float, int, dict[str, Any]], ...] = (
        ("STED", 15.0, 1000, {}),
        ("Widefield", 100.0, 2000, {"exposure_time_s": 0.01}),
        ("Confocal", 70.0, 1000, {}),
        ("AiryScan", 40.0, 1000, {}),
        ("SMLM", 2.0, 1000, {}),
    )
    for modality, pixel, sample, extra in rows:
        n = sample / pixel
        exact = float(n).is_integer()
        inputs = {**base, "modality": modality, "sample_size_xy_nm": sample, **extra}
        shape = int(n)
        expect_values: dict[str, Any] = {
            "modality": modality,
            "pixel_size_nm": {"approx": pixel, "tol": 0.01},
            "particles_requested": 1,
            "particles_placed": 1,
        }
        if exact:
            expect_values["image_size_px"] = "%d x %d" % (shape, shape)
        s.dataset(
            "vm_sim_%s" % modality.lower(),
            "%s, structure file mini_ring.cif, sample %d nm: image size = sample / pixel = %.2f"
            % (modality, sample, n),
            "works",
            derivation="The pixel size of %s is %g nm; the image has sample/pixel = %.3f pixels per side (%s). Only the arithmetic of the declared modality table is used."
            % (
                modality,
                pixel,
                n,
                (
                    "exact"
                    if exact
                    else "not a whole number: the app may truncate or round, either is accepted: %d or %d"
                    % (int(n), int(n) + 1)
                ),
            ),
            files=[cif],
            tool="simulate_sample",
            inputs=inputs,
            expect={"max_seconds": 240, "results": {"values": expect_values}},
            checks=[
                chk_status("COMPLETE"),
                chk_value("modality", modality),
                chk_value("pixel_size_nm", pixel, 0.01),
                chk_value("pixel_size_um", pixel / 1000, 1e-6),
                chk_value("particles_placed", 1),
                chk_image_stat("simulated", "shape0", n, 0.99),
                chk_image_stat("simulated", "shape1", n, 0.99),
                chk_image_stat("noiseless", "shape0", n, 0.99),
            ],
        )
    centred = {
        **base,
        "modality": "Widefield",
        "sample_size_xy_nm": 2000,
        "random_positions": False,
        "random_orientations": False,
        "random_rotations": False,
        "exposure_time_s": 0.01,
    }
    s.dataset(
        "vm_sim_centred",
        "one ring placed at a fixed position (random positions off): the noiseless image is centred on the sample",
        "works",
        derivation="PREDICTION, not verified against the app: with random positions off a single particle is put at the middle of the sample (1000 nm of 2000 nm), so the intensity centroid "
        "of the noiseless 20x20 image is at (9.5-10, 9.5-10) px; tolerance 3 px.",
        files=[cif],
        tool="simulate_sample",
        inputs=centred,
        expect={"max_seconds": 240, "results": {"values": {"particles_placed": 1}}},
        checks=[chk_status("COMPLETE"), chk_centroid("noiseless", [9.75, 9.75], 3.0)],
        outcome_text="works; centroid of the noiseless image within 3 px of the centre (a prediction)",
    )
    refusals: list[tuple[str, dict[str, Any], str, str]] = [
        ("vm_sim_sample_too_small", {"sample_size_xy_nm": 50}, "invalid_parameter", "Sample size XY"),
        ("vm_sim_pixel_too_big", {"pixel_size_nm": 2000}, "invalid_parameter", "Pixel size"),
        ("vm_sim_seed_negative", {"random_seed": -1}, "invalid_parameter", "Random seed"),
        ("vm_sim_exposure_too_long", {"exposure_time_s": 11.0}, "invalid_parameter", "Exposure time"),
        ("vm_sim_wobble_too_big", {"wobble_cone_degrees": 60.0}, "invalid_parameter", "Wobble cone"),
        (
            "vm_sim_efficiency_negative",
            {"labelling_efficiency": -0.1},
            "invalid_parameter",
            "Labelling efficiency",
        ),
        (
            "vm_sim_too_many_particles",
            {"number_of_particles": 21},
            "invalid_parameter",
            "Number of particles",
        ),
        (
            "vm_sim_pixel_not_multiple",
            {"modality": "Widefield", "pixel_size_nm": 105},
            "pixel_size_not_multiple",
            "multiple of the PSF sampling",
        ),
    ]
    for ident, extra, code, text in refusals:
        s.dataset(
            ident,
            "simulate_sample with %s" % ", ".join("%s=%s" % kv for kv in extra.items()),
            "refused",
            derivation="A value outside the declared range (or an impossible combination) is refused with the field's name.",
            files=[cif],
            tool="simulate_sample",
            inputs={**base, **extra},
            expect={"status": "FAILED", "code": code, "message_contains": text},
            checks=[chk_status("FAILED", code, text)],
            outcome_text="refused: %s" % code,
        )
    garbage = s.fixtures / "vm_garbage.cif"
    garbage.write_text("this is not a structure file\n", encoding="utf-8")
    empty = s.fixtures / "vm_empty.cif"
    empty.write_text("", encoding="utf-8")
    for ident, path, why in (
        ("vm_structure_garbage", garbage, "a text file that is not a structure"),
        ("vm_structure_empty", empty, "an empty structure file"),
        ("vm_structure_missing", s.fixtures / "no_such.cif", "a structure file that does not exist"),
    ):
        s.dataset(
            ident,
            "structure_file = %s" % why,
            "refused",
            derivation="No structure to image: the run must end with a sentence that names the file, never a bare traceback or an empty image.",
            files=[p for p in [path] if path.exists()],
            tool="simulate_sample",
            inputs={**base, "structure_file": s.rel(path)},
            expect={"status": "FAILED"},
            checks=[chk_status("FAILED")],
            outcome_text="refused with a sentence that names the structure file",
        )


def build(out: Path) -> Suite:
    s = Suite(APP, out, VERSION)
    add_compare(s)
    add_simulate(s)
    return s


if __name__ == "__main__":
    sys.exit(standalone_main(build, HERE, __doc__ or ""))
