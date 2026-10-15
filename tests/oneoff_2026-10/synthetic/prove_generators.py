#!/usr/bin/env python3
"""Validate the generated datasets WITHOUT running any app: load every file back and redo the arithmetic of the truth with other code.

    python prove_generators.py /home/user/synthetic [--app NAME]

For every app: all files of every dataset exist and open; the calibration read back from each TIFF (what Fiji, Napari and QuPath read) equals the
`calibration` of the truth; `cases.json` passes the case validator of the Tools repository when it is importable (PYTHONPATH); and per app an
independent recomputation: NucleiSky (the query warped by the truth matrix correlates with the reference, a shifted matrix does not; mask counts),
Playground (counts, areas, centroids, summaries recomputed from the files), CellTracksColab (metrics recomputed with vectorised numpy from the CSV),
VLab4Mic (Pearson from the files), Guess the Condition (experiment trees and display shapes). Exit 1 on the first disagreement of any app.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
import tifffile
from scipy import ndimage

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import UNIT_FACTOR, read_calibration  # noqa: E402

Problems = list[str]


def load(app_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    truth = json.loads((app_dir / "ground_truth.json").read_text(encoding="utf-8"))
    return json.loads((app_dir / "cases.json").read_text(encoding="utf-8")), truth


def by_id(truth: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {d["id"]: d for d in truth["datasets"]}


def generic(app_dir: Path, cases: list[dict[str, Any]], truth: dict[str, Any]) -> Problems:
    """Files exist and open, calibration read back equals the truth, the cases file is valid for the Tools."""
    problems: Problems = []
    opened = 0
    for d in truth["datasets"]:
        for rel in d["files"]:
            path = app_dir / rel
            if not path.exists():
                problems.append("%s: missing file %s" % (d["id"], rel))
            elif path.suffix.lower() in (".tif", ".tiff") and path.name not in (
                "broken.tif",
            ):  # broken.tif is an undecodable file on purpose
                try:
                    info = read_calibration(path)
                except Exception as error:  # noqa: BLE001
                    problems.append("%s: %s does not open: %s" % (d["id"], rel, error))
                    continue
                opened += 1
                cal = d.get("calibration")
                if (
                    cal
                    and ".ome." not in path.name
                    and "mask" not in path.name
                    and "region" not in path.name
                    and path.name == Path(d["files"][0]).name
                ):
                    unit = (info["unit"] or "").replace("\\u00B5", "µ").replace("micron", "um")
                    if unit not in UNIT_FACTOR or info["x_size"] is None:
                        problems.append(
                            "%s: %s has no readable calibration (unit %r)" % (d["id"], rel, info["unit"])
                        )
                        continue
                    f = UNIT_FACTOR[unit]
                    got = (info["x_size"] / f, info["y_size"] / f)
                    if abs(got[0] - cal["x_um"]) > 1e-6 or abs(got[1] - cal["y_um"]) > 1e-6:
                        problems.append(
                            "%s: %s calibration x=%.6g um y=%.6g um, truth x=%g y=%g"
                            % (d["id"], rel, got[0], got[1], cal["x_um"], cal["y_um"])
                        )
    try:
        from labconstrictor_tools.testing import load_cases

        load_cases(app_dir / "cases.json")
    except ImportError:
        print(
            "  (labconstrictor_tools not importable: cases.json not validated by the Tools; PYTHONPATH it to do so)"
        )
    except ValueError as error:
        problems.append("cases.json invalid for the Tools: %s" % error)
    ids = [d["id"] for d in truth["datasets"]]
    if len(ids) != len(set(ids)):
        problems.append("duplicate dataset ids")
    for d in truth["datasets"]:
        if d["primary_case"] is not None and cases[d["primary_case"]]["tool"] != d["tool"]:
            problems.append(
                "%s: primary case %d is tool %s, not %s"
                % (d["id"], d["primary_case"], cases[d["primary_case"]]["tool"], d["tool"])
            )
    print(
        "  generic: %d datasets, %d cases, %d TIFFs opened with calibration read back"
        % (len(ids), len(cases), opened)
    )
    return problems


# ------------------------------------------------------------------------------------------------ NucleiSky
def warp_correlation(ref: np.ndarray, query: np.ndarray, matrix: np.ndarray) -> float:
    """Pearson correlation between the query and the reference sampled at A @ q + b (bilinear), over the query pixels that fall inside the reference."""
    qy, qx = np.mgrid[0 : query.shape[0], 0 : query.shape[1]].astype(float)
    ry = matrix[0, 0] * qy + matrix[0, 1] * qx + matrix[0, 2]
    rx = matrix[1, 0] * qy + matrix[1, 1] * qx + matrix[1, 2]
    ok = (ry >= 0) & (ry <= ref.shape[0] - 1) & (rx >= 0) & (rx <= ref.shape[1] - 1)
    sampled = ndimage.map_coordinates(ref.astype(np.float64), [ry[ok], rx[ok]], order=1)
    return float(np.corrcoef(sampled, query.astype(np.float64)[ok])[0, 1])


def nucleisky(app_dir: Path, cases: list[dict[str, Any]], truth: dict[str, Any]) -> Problems:
    problems: Problems = []
    checked = 0
    for d in truth["datasets"]:
        mats = [c for c in d["checks"] if c["kind"] == "matrix"]
        if not mats:
            continue
        inputs = cases[d["primary_case"]]["inputs"]
        ref, query = tifffile.imread(app_dir / inputs["reference"]), tifffile.imread(
            app_dir / inputs["query"]
        )
        m = np.array(mats[0]["expected"])
        good = warp_correlation(ref, query, m)
        wrong = np.array(m)
        wrong[:2, 2] += 6.0  # a 6 px error of the offset
        bad = warp_correlation(ref, query, wrong)
        swapped = np.array(m)
        swapped[:2, :2] = swapped[:2, :2].T  # rotation of the opposite sign
        bad2 = warp_correlation(ref, query, swapped) if abs(m[0, 1]) > 1e-9 else -1.0
        print(
            "  %-26s corr(truth matrix) %.3f  corr(offset +6 px) %.3f  corr(opposite rotation) %.3f"
            % (d["id"], good, bad, bad2)
        )
        if good < 0.9:
            problems.append(
                "%s: the query warped by the truth matrix correlates only %.3f with the reference"
                % (d["id"], good)
            )
        if not bad < good - 0.15:
            problems.append(
                "%s: a 6 px offset error still correlates %.3f (truth %.3f): the check cannot tell"
                % (d["id"], bad, good)
            )
        if not bad2 < good - 0.15:
            problems.append(
                "%s: the opposite rotation still correlates %.3f (truth %.3f)" % (d["id"], bad2, good)
            )
        # the declared pixel sizes are consistent with the transform: query pixel = reference pixel / zoom
        zoom = 1.0 / np.sqrt(abs(np.linalg.det(m[:2, :2])))
        ratio = inputs["reference_pixel_size_um"] / inputs["query_pixel_size_um"]
        if abs(zoom - ratio) > 1e-6:
            problems.append("%s: zoom from the matrix %.6f, pixel size ratio %.6f" % (d["id"], zoom, ratio))
        checked += 1
        for c in d["checks"]:
            if c["kind"] == "value" and c["key"] in ("n_nuclei_reference", "n_nuclei_query"):
                mask = tifffile.imread(
                    app_dir / inputs["reference_mask" if c["key"].endswith("reference") else "query_mask"]
                )
                n = (
                    int(len(np.unique(mask)) - (1 if (mask == 0).any() else 0))
                    if mask.max() > 1
                    else int(ndimage.label(mask > 0)[1])
                )
                inside = "region" in d["id"]
                if not inside and n != c["expected"]:
                    problems.append(
                        "%s: %s expects %d, the mask holds %d objects" % (d["id"], c["key"], c["expected"], n)
                    )
    if checked < 5:
        problems.append("only %d transform datasets verified" % checked)
    return problems


# ------------------------------------------------------------------------------------------------ Playground
def playground(app_dir: Path, cases: list[dict[str, Any]], truth: dict[str, Any]) -> Problems:
    problems: Problems = []
    n_checked = 0
    for d in truth["datasets"]:
        if d["primary_case"] is None or d["expected"] == "refused":
            continue
        case = cases[d["primary_case"]]
        inputs = case["inputs"]
        values = {c["key"]: c for c in d["checks"] if c["kind"] == "value"}
        if d["tool"] == "count_above_level":
            image = tifffile.imread(app_dir / inputs["image"])
            level = (
                inputs["level"]
                if inputs["mode"] == "fixed"
                else float(np.percentile(image, inputs["percentile"]))
            )
            pixels = int((image >= level).sum())
            if pixels != values["pixels"]["expected"] or abs(level - values["level_used"]["expected"]) > 1e-4:
                problems.append(
                    "%s: recomputed pixels %d level %.6f, truth %s %s"
                    % (d["id"], pixels, level, values["pixels"]["expected"], values["level_used"]["expected"])
                )
        elif d["tool"] == "bright_area" and "bright_pixels" in values:
            image = tifffile.imread(app_dir / inputs["image"])
            n = int((image > 0.5 * image.max()).sum()) if image.max() > 0 else 0
            area_ok = (
                "area_um2" not in values
                or abs(n * inputs["pixel_size"] ** 2 - values["area_um2"]["expected"]) <= 1e-9
            )
            if n != values["bright_pixels"]["expected"] or not area_ok:
                problems.append(
                    "%s: recomputed %d bright pixels, truth %s"
                    % (d["id"], n, values["bright_pixels"]["expected"])
                )
        elif d["tool"] == "feature_tour":
            tab = [c for c in d["checks"] if c["kind"] == "table"]
            if not tab:
                continue
            image = tifffile.imread(app_dir / inputs["image"]).astype(float)
            scaled = (image - image.min()) / (image.max() - image.min())
            labels, count = ndimage.label(scaled >= inputs.get("threshold", 0.5))
            sizes = ndimage.sum(scaled >= inputs.get("threshold", 0.5), labels, range(1, count + 1))
            keep = [i + 1 for i, a in enumerate(sizes) if a >= inputs.get("min_size_px", 20)]
            centres = ndimage.center_of_mass(labels > 0, labels, keep)
            truth_rows = pd.read_csv(app_dir / tab[0]["truth_csv"])
            if "region" in inputs:
                region = tifffile.imread(app_dir / inputs["region"]) > 0
                centres = [c for c in centres if region[int(round(c[0])), int(round(c[1]))]]
                keep = [
                    k
                    for k, c in zip(keep, ndimage.center_of_mass(labels > 0, labels, keep))
                    if region[int(round(c[0])), int(round(c[1]))]
                ]
            if len(centres) != len(truth_rows):
                problems.append(
                    "%s: %d blobs recomputed from the file, truth has %d"
                    % (d["id"], len(centres), len(truth_rows))
                )
                continue
            got = np.array(centres)
            want = truth_rows[["y", "x"]].to_numpy()
            if np.abs(got - want).max() > 1e-6:
                problems.append(
                    "%s: centroids recomputed from the file differ from the truth by %.3g px"
                    % (d["id"], np.abs(got - want).max())
                )
            if sorted(int((labels == k).sum()) for k in keep) != sorted(truth_rows["area_px"].tolist()):
                problems.append("%s: areas recomputed from the file differ from the truth" % d["id"])
        elif d["tool"] == "align_centres":
            a, b = (tifffile.imread(app_dir / inputs[k]).astype(float) for k in ("image", "reference"))
            ca, cb = (np.array(ndimage.center_of_mass(x)) for x in (a, b))
            want = np.array(d["checks"][1]["expected"])[:2, 2]
            if np.abs((cb - ca) - want).max() > 1e-3:
                problems.append("%s: centroid difference %s, truth %s" % (d["id"], cb - ca, want))
        elif d["tool"] == "summarise_table":
            tab = tifffile_free_csv(app_dir / inputs["table"])
            truth_rows = pd.read_csv(
                app_dir / [c for c in d["checks"] if c["kind"] == "table"][0]["truth_csv"]
            )
            numeric = tab.select_dtypes("number")
            for _, row in truth_rows.iterrows():
                col = numeric[row["column"]]
                if (
                    col.count() != row["count"]
                    or abs(col.mean() - row["mean"]) > 1e-9 * max(1, abs(row["mean"]))
                    or col.min() != row["min"]
                    or col.max() != row["max"]
                ):
                    problems.append(
                        "%s: column %s recomputed differently from the truth" % (d["id"], row["column"])
                    )
        n_checked += 1
    print("  playground: %d datasets recomputed from their files" % n_checked)
    return problems


def tifffile_free_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


# ------------------------------------------------------------------------------------------------ CellTracksColab
def numpy_metrics(group: pd.DataFrame, has_z: bool) -> dict[str, float]:
    """Metrics of one track from the CSV rows with plain numpy (not the notebook's code): sorted by time, step lengths, per-step speeds."""
    g = group.sort_values("POSITION_T")
    cols = ["POSITION_X", "POSITION_Y"] + (["POSITION_Z"] if has_z else [])
    p, t = g[cols].to_numpy(float), g["POSITION_T"].to_numpy(float)
    step = np.sqrt((np.diff(p, axis=0) ** 2).sum(axis=1))
    speed = step / np.diff(t)
    return {
        "Track Duration": t[-1] - t[0],
        "Median Speed": float(np.median(speed)),
        "Mean Speed": float(speed.mean()),
        "Max Speed": float(speed.max()),
        "Min Speed": float(speed.min()),
        "Speed Standard Deviation": float(speed.std()),
        "Total Distance Traveled": float(step.sum()),
        "Directionality": float(np.linalg.norm(p[-1] - p[0]) / step.sum()),
    }


def celltracks(app_dir: Path, cases: list[dict[str, Any]], truth: dict[str, Any]) -> Problems:
    problems: Problems = []
    n = 0
    for d in truth["datasets"]:
        tabs = [c for c in d["checks"] if c["kind"] == "table"]
        if d["expected"] != "works" or not tabs:
            continue
        inputs = cases[d["primary_case"]]["inputs"]
        idc = inputs.get("track_id_column", "Unique_ID")
        data = pd.read_csv(app_dir / inputs["tracks"])
        for col in ("POSITION_T", "POSITION_X", "POSITION_Y", "POSITION_Z"):
            if col in data.columns:
                data[col] = pd.to_numeric(data[col], errors="coerce")
        has_z = "POSITION_Z" in data.columns and not data["POSITION_Z"].isna().all()
        data = data.dropna(
            subset=["POSITION_T", "POSITION_X", "POSITION_Y"] + (["POSITION_Z"] if has_z else [])
        )
        sizes = data.groupby(idc).size()
        data = data[data[idc].isin(sizes.index[sizes >= 2])]
        truth_rows = pd.read_csv(app_dir / tabs[0]["truth_csv"]).set_index(idc)
        truth_rows.index = truth_rows.index.astype(str)
        worst = 0.0
        seen = set()
        for ident, group in data.groupby(idc):
            got = numpy_metrics(group, has_z)
            seen.add(str(ident))
            for key, value in got.items():
                want = float(truth_rows.loc[str(ident), key])
                err = abs(value - want) / max(1.0, abs(want))
                worst = max(worst, err)
                if err > 1e-9:
                    problems.append(
                        "%s: track %s %s recomputed from the CSV %.12g, truth %.12g"
                        % (d["id"], ident, key, value, want)
                    )
                    break
        if seen != set(truth_rows.index):
            problems.append(
                "%s: tracks with 2+ complete spots %d, truth has %d" % (d["id"], len(seen), len(truth_rows))
            )
        n += 1
    print("  celltracks: %d datasets, metrics recomputed with numpy from the CSV files" % n)
    return problems


# ------------------------------------------------------------------------------------------------ VLab4Mic
def vlab4mic(app_dir: Path, cases: list[dict[str, Any]], truth: dict[str, Any]) -> Problems:
    problems: Problems = []
    for d in truth["datasets"]:
        if d["tool"] != "compare_images" or d["expected"] != "works":
            continue
        inputs = cases[d["primary_case"]]["inputs"]
        a, b = (tifffile.imread(app_dir / inputs[k]).astype(float) for k in ("reference", "simulated"))
        scale = inputs["reference_pixel_size_um"] / inputs["simulated_pixel_size_um"]
        if (
            b.shape != a.shape and abs(scale - 1.0) > 1e-9
        ):  # bring the simulated image to the reference grid (zoom by the pixel size ratio)
            b = ndimage.zoom(b, 1.0 / scale, order=1)
        h, w = min(a.shape[0], b.shape[0]), min(a.shape[1], b.shape[1])
        r = float(np.corrcoef(a[:h, :w].ravel(), b[:h, :w].ravel())[0, 1])
        for c in d["checks"]:
            if c["kind"] == "value" and c["key"] == "pearson":
                lo, hi = c.get("minimum", c.get("expected", 0) - c["tol"] if "expected" in c else -2), c.get(
                    "maximum", c.get("expected", 0) + c["tol"] if "expected" in c else 2
                )
                if "expected" in c:
                    lo, hi = c["expected"] - c["tol"], c["expected"] + c["tol"]
                if not lo <= r <= hi:
                    problems.append(
                        "%s: Pearson recomputed from the files %.4f, truth range [%.3f, %.3f]"
                        % (d["id"], r, lo, hi)
                    )
                print("  %-26s pearson from the files %.4f  (truth range %.3f..%.3f)" % (d["id"], r, lo, hi))
    return problems


# ------------------------------------------------------------------------------------------------ Guess the Condition
def display_shape(shape: tuple[int, ...], axes: str, x_gap_fraction: float = 0.02) -> tuple[int, int]:
    """The shape the game shows (images.py rule, rewritten here from its docstring): drop Z/T/other axes by max, tile channels with a gap."""
    sizes = dict(zip(axes, shape))
    y, x = sizes["Y"], sizes["X"]
    c = sizes.get("C", 1)
    return (y, x) if c == 1 else (y, c * x + (c - 1) * max(1, round(x_gap_fraction * x)))


def guessthecondition(app_dir: Path, cases: list[dict[str, Any]], truth: dict[str, Any]) -> Problems:
    problems: Problems = []
    for d in truth["datasets"]:
        if d["id"].startswith("gtc_view_") and d["primary_case"] is not None and d["expected"] != "refused":
            shape_checks = {
                c["stat"]: c["expected"]
                for c in d["checks"]
                if c["kind"] == "image_stat" and c["stat"].startswith("shape")
            }
            tif = [app_dir / f for f in d["files"] if f.endswith(".tif")][0]
            with tifffile.TiffFile(tif) as t:
                s = t.series[0]
                axes, shape = s.axes, s.shape
            if (
                len(shape) == 3 and axes[0] in "QS"
            ):  # no axis metadata: a short leading axis (at most 5 planes) is read as channels, a longer one as z
                axes = ("C" if shape[0] <= 5 else "Z") + axes[1:]
            got = display_shape(shape, axes)
            if "shape0" in shape_checks and (got[0], got[1]) != (
                shape_checks["shape0"],
                shape_checks["shape1"],
            ):
                problems.append(
                    "%s: display shape from the file %s, truth %s"
                    % (d["id"], got, (shape_checks["shape0"], shape_checks["shape1"]))
                )
        if d["id"].startswith("gtc_balanced") or d["id"].startswith("gtc_unbalanced"):
            root = app_dir / "fixtures" / d["id"] / "experiment"
            counts = {
                (c.name, r.name): len(list(r.glob("*.tif"))) for c in root.iterdir() for r in c.iterdir()
            }
            total = sum(counts.values())
            acc = [c for c in d["checks"] if c["kind"] == "value" and c["key"] == "accuracy"][0]["expected"]
            guess = "Control" if "balanced_const" in d["id"] and "un" not in d["id"] else "Mutant"
            correct = sum(n for (c, _), n in counts.items() if c == guess)
            if abs(correct / total - acc) > 1e-9:
                problems.append(
                    "%s: accuracy from the folder counts %.6f, truth %.6f" % (d["id"], correct / total, acc)
                )
    print("  guessthecondition: experiment trees and display shapes recomputed")
    return problems


CHECKS: dict[str, Callable[[Path, list[dict[str, Any]], dict[str, Any]], Problems]] = {
    "NucleiSky": nucleisky,
    "LabConstrictor-Playground": playground,
    "CellTracksColab": celltracks,
    "LabConstrictor-VLab4Mic": vlab4mic,
    "GuessTheCondition": guessthecondition,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    parser.add_argument("root", type=Path)
    parser.add_argument("--app", action="append", default=[])
    args = parser.parse_args(argv)
    failed = 0
    for app, check in CHECKS.items():
        if args.app and app not in args.app:
            continue
        app_dir = args.root / app
        print("== %s" % app)
        cases, truth = load(app_dir)
        problems = generic(app_dir, cases, truth) + check(app_dir, cases, truth)
        for p in problems:
            print("  PROBLEM %s" % p)
        print("  %s: %s" % (app, "OK" if not problems else "%d PROBLEM(S)" % len(problems)))
        failed += len(problems)
    print("TOTAL problems: %d" % failed)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
