#!/usr/bin/env python3
"""Negative controls of `check_ground_truth.py`: it must PASS a right result and FAIL a deliberately wrong one, for every kind of truth.

    python negative_controls.py SYN_DIR

A right result is built from the truth itself (an oracle report), so this proves only the checker, not any app. For each case a right report
must give exit 0 and the same report with ONE seeded error must give exit 1: a shifted transform, a rotated or transposed one, a changed speed,
a wrong unit (nm read as um, a pixel size 1000 times off), a doubled area, an accuracy off by a few points, a wrong status or error code, a table
with a missing row, a shifted point cloud, a shifted centroid, a wrong image shape, a missing channel mean, an absurd speed. Exit 1 when a control
behaves wrongly (a wrong result that passes, or a right one that fails).
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import tifffile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_ground_truth as cgt  # noqa: E402

Report = dict[str, Any]
SUPPORTED = {"status", "value", "matrix", "table", "message", "absent_value", "host_param"}


def oracle(dataset: dict[str, Any], base: Path, with_host: bool = False) -> Report:
    """A report that satisfies every supported check of the dataset (built only from the truth)."""
    report: Report = {"status": "COMPLETE", "results": []}
    values: dict[str, Any] = {}
    for check in dataset["checks"]:
        kind = check["kind"]
        if kind == "status":
            report["status"] = check["status"]
            if check["status"] == "FAILED":
                report.update(
                    code=check.get("code"), error=(check.get("message_contains") or "refused") + " (oracle)"
                )
        elif kind == "value":
            values[check["key"]] = (
                check["expected"]
                if "expected" in check
                else (
                    check["contains"]
                    if "contains" in check
                    else (
                        (check.get("minimum", 0) + check.get("maximum", 0)) / 2
                        if "minimum" in check and "maximum" in check
                        else check.get("minimum", check.get("maximum", 0))
                    )
                )
            )
        elif kind == "matrix":
            report["results"].append(
                {"type": "affine", "name": check["result"], "matrix_yx": check["expected"]}
            )
        elif kind == "table":
            report["results"].append(
                {
                    "type": "table",
                    "name": check["result"],
                    "path": str(base / check["truth_csv"]) if check.get("truth_csv") else "",
                }
            )
        elif kind == "message":
            report["results"].append(
                {"type": "message", "name": check["result"], "text": "oracle: " + check["contains"]}
            )
    if values:
        report["results"].append({"type": "values", "name": "values", "values": values})
    if with_host:
        report["host_observed"] = {c["param"]: c["expected"] for c in dataset.get("host_checks", [])}
    return report


def verdict(dataset: dict[str, Any], report: Report | None, base: Path, with_host: bool = False) -> list[str]:
    rows = cgt.check_dataset(dataset, report, base, with_host)
    return [r["status"] for r in rows]


class Controls:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.tmp = Path(tempfile.mkdtemp(prefix="negctl_"))
        self.failures: list[str] = []
        self.n_positive = 0
        self.n_negative = 0
        self.truth = {
            app.name: json.loads((app / "ground_truth.json").read_text(encoding="utf-8"))
            for app in sorted(root.iterdir())
            if (app / "ground_truth.json").exists()
        }

    def dataset(self, app: str, ident: str) -> dict[str, Any]:
        return next(d for d in self.truth[app]["datasets"] if d["id"] == ident)

    def positive(
        self, name: str, dataset: dict[str, Any], report: Report, base: Path, with_host: bool = False
    ) -> None:
        statuses = verdict(dataset, report, base, with_host)
        ok = bool(statuses) and all(s == "PASS" for s in statuses)
        self.n_positive += 1
        print(
            "  [right result] %-44s %s"
            % (name, "passes (%d checks)" % len(statuses) if ok else "WRONGLY FAILS: %s" % statuses)
        )
        if not ok:
            self.failures.append("right result failed: " + name)

    def negative(
        self, name: str, dataset: dict[str, Any], report: Report, base: Path, with_host: bool = False
    ) -> None:
        rows = cgt.check_dataset(dataset, report, base, with_host)
        failed = [r for r in rows if r["status"] == "FAIL"]
        self.n_negative += 1
        print(
            "  [wrong result] %-44s %s"
            % (name, ("FAILS as required: " + failed[0]["detail"][:110]) if failed else "WRONGLY PASSES")
        )
        if not failed:
            self.failures.append("wrong result passed: " + name)

    def result(self, report: Report, name: str) -> dict[str, Any]:
        return next(r for r in report["results"] if r["name"] == name)


def run_app_controls(c: Controls) -> None:
    root = c.root
    # --- a shifted / rotated / transposed transform (NucleiSky)
    d = c.dataset("NucleiSky", "ns_normal")
    d = {
        **d,
        "checks": [k for k in d["checks"] if k["kind"] in SUPPORTED],
    }  # the points check is exercised below with real point files
    base = root / "NucleiSky"
    good = oracle(d, base)
    c.positive("NucleiSky ns_normal truth matrix", d, good, base)
    shifted = copy.deepcopy(good)
    c.result(shifted, "alignment")["matrix_yx"][0][2] += 10.0
    c.negative("transform shifted by 10 px in y", d, shifted, base)
    rotated = copy.deepcopy(good)
    m = np.array(c.result(rotated, "alignment")["matrix_yx"])
    t = np.deg2rad(3.0)
    m[:2, :2] = m[:2, :2] @ np.array([[np.cos(t), -np.sin(t)], [np.sin(t), np.cos(t)]])
    c.result(rotated, "alignment")["matrix_yx"] = m.tolist()
    c.negative("transform rotated by a further 3 degrees", d, rotated, base)
    transposed = copy.deepcopy(good)
    m = np.array(c.result(transposed, "alignment")["matrix_yx"])
    m[:2, :2] = m[:2, :2].T
    c.result(transposed, "alignment")["matrix_yx"] = m.tolist()
    c.negative("rotation of the opposite sign (matrix transposed)", d, transposed, base)
    bad_scale = copy.deepcopy(good)
    c.result(bad_scale, "values")["values"]["scale"] = 0.5
    c.negative("physical scale 0.5 instead of 1 (unit slip)", d, bad_scale, base)
    c.negative(
        "an unrelated image matched (status COMPLETE for a refusal)",
        c.dataset("NucleiSky", "ns_no_overlap"),
        {"status": "COMPLETE", "results": []},
        base,
    )
    wrong_code = oracle(c.dataset("NucleiSky", "ns_axes_cyx"), base)
    wrong_code["code"] = "bad_input"
    c.negative("refusal with another error code", c.dataset("NucleiSky", "ns_axes_cyx"), wrong_code, base)
    # --- a changed speed / a missing row (CellTracksColab)
    d, base = c.dataset("CellTracksColab", "ct_linear_2d"), root / "CellTracksColab"
    good = oracle(d, base)
    c.positive("CellTracksColab ct_linear_2d truth table", d, good, base)
    truth_csv = pd.read_csv(base / d["checks"][1]["truth_csv"])
    for label, edit in (
        ("a Mean Speed 10% too high", lambda t: t.assign(**{"Mean Speed": t["Mean Speed"] * 1.1})),
        ("one track missing", lambda t: t.iloc[1:]),
        (
            "Track Duration in frames instead of seconds (x 2.5)",
            lambda t: t.assign(**{"Track Duration": t["Track Duration"] * 2.5}),
        ),
        (
            "Directionality 1 changed to 0.99 on one track",
            lambda t: t.assign(Directionality=[0.99] + [1.0] * (len(t) - 1)),
        ),
    ):
        path = c.tmp / ("ct_" + label.split()[0] + str(len(label)) + ".csv")
        edit(truth_csv).to_csv(path, index=False)
        wrong = copy.deepcopy(good)
        c.result(wrong, "table")["path"] = str(path)
        c.negative("table with " + label, d, wrong, base)
    d2 = c.dataset("CellTracksColab", "ct_duplicate_time")
    refusal: Report = {
        "status": "FAILED",
        "code": "same_time_twice",
        "error": "[same_time_twice] 2 spot(s) share a time with another spot of the same track",
        "results": [],
    }
    absurd = {
        "status": "COMPLETE",
        "results": [
            {
                "type": "table",
                "name": "table",
                "path": str(_csv(c.tmp / "absurd.csv", {"Max Speed": [1.0, 1e10]})),
            }
        ],
    }
    c.positive("ct_duplicate_time refused same_time_twice", d2, refusal, base)
    c.negative("a completed run with a speed of 1e10", d2, absurd, base)
    c.negative("refused with another code", d2, dict(refusal, code="bad_input"), base)
    # --- a wrong unit (VLab4Mic, Playground host calibration)
    d, base = c.dataset("LabConstrictor-VLab4Mic", "vm_identical"), root / "LabConstrictor-VLab4Mic"
    good = oracle(d, base, True)
    c.positive("VLab4Mic vm_identical (incl. host field)", d, good, base, True)
    nm_as_um = copy.deepcopy(good)
    c.result(nm_as_um, "values")["values"]["reference_pixel_size_nm"] = 20000.0
    c.negative("pixel size echoed 1000 times too big (um read as nm)", d, nm_as_um, base)
    host_wrong = copy.deepcopy(good)
    host_wrong["host_observed"]["reference_pixel_size_um"] = 20.0
    c.negative("host filled 20 (nm) into the um field", d, host_wrong, base, True)
    host_missing = copy.deepcopy(good)
    host_missing["host_observed"] = {}
    c.negative("host reported nothing for the field", d, host_missing, base, True)
    d, base = c.dataset("LabConstrictor-Playground", "pg_area_u8"), root / "LabConstrictor-Playground"
    good = oracle(d, base)
    c.positive("Playground pg_area_u8 (600 px, 150 um2)", d, good, base)
    doubled = copy.deepcopy(good)
    c.result(doubled, "values")["values"]["area_um2"] = 300.0
    c.negative("area doubled (anisotropic pixel taken as isotropic)", d, doubled, base)
    off_by_one = copy.deepcopy(good)
    c.result(off_by_one, "values")["values"]["bright_pixels"] = 601
    c.negative("one bright pixel too many", d, off_by_one, base)
    # --- an accuracy off by a few points (Guess the Condition)
    d, base = c.dataset("GuessTheCondition", "gtc_unbalanced_const"), root / "GuessTheCondition"
    good = oracle(d, base)
    c.positive("GuessTheCondition gtc_unbalanced_const", d, good, base)
    for key, wrong_value in (("accuracy", 0.4), ("chance", 0.5), ("repeats_above_chance", 1)):
        wrong = copy.deepcopy(good)
        c.result(wrong, "values")["values"][key] = wrong_value
        c.negative("%s = %s" % (key, wrong_value), d, wrong, base)
    present = copy.deepcopy(good)
    c.result(present, "values")["values"]["p_across_repeats"] = 0.03
    d3 = c.dataset("GuessTheCondition", "gtc_balanced_const")
    wrong_p = oracle(d3, base)
    c.result(wrong_p, "values")["values"]["p_across_repeats"] = 0.03
    c.negative("a p-value across repeats where the truth has none", d3, wrong_p, base)


def _csv(path: Path, columns: dict[str, list[float]]) -> Path:
    pd.DataFrame(columns).to_csv(path, index=False)
    return path


def run_file_controls(c: Controls) -> None:
    """The check kinds that read files: points, centroid, image statistics, slice means."""
    tmp = c.tmp
    rng = np.random.default_rng(0)
    matrix = [[0.5, 0.0, 100.0], [0.0, 0.5, 200.0], [0.0, 0.0, 1.0]]
    ref = rng.uniform(150, 900, (40, 2))
    query = (ref - np.array([100.0, 200.0])) / 0.5
    p_ref, p_q, p_shift = tmp / "ref.csv", tmp / "q.csv", tmp / "q_shift.csv"
    pd.DataFrame(ref, columns=["y", "x"]).to_csv(p_ref, index=False)
    pd.DataFrame(query, columns=["y", "x"]).to_csv(p_q, index=False)
    pd.DataFrame(query + 12.0, columns=["y", "x"]).to_csv(p_shift, index=False)
    check = {
        "kind": "points_map",
        "source": "query_nuclei",
        "target": "reference_nuclei",
        "matrix": matrix,
        "target_shape": [1100, 1100],
        "tol_px": 4.0,
        "min_fraction": 0.8,
    }
    dataset = {"id": "points", "checks": [check]}

    def points(q: Path) -> Report:
        return {
            "status": "COMPLETE",
            "results": [
                {"type": "points", "name": "query_nuclei", "path": str(q)},
                {"type": "points", "name": "reference_nuclei", "path": str(p_ref)},
            ],
        }

    c.positive("points: query nuclei moved by the truth matrix", dataset, points(p_q), tmp)
    c.negative("points: query nuclei 12 px off (a frame error)", dataset, points(p_shift), tmp)
    blob = np.zeros((60, 80), np.float32)
    blob[28:33, 38:43] = 1.0  # centroid (30, 40)
    img_path, img_wrong = tmp / "blob.tif", tmp / "blob_wrong.tif"
    tifffile.imwrite(img_path, blob)
    shifted = np.roll(blob, 9, axis=1)
    tifffile.imwrite(img_wrong, shifted)
    cdata = {
        "id": "centroid",
        "checks": [
            {"kind": "centroid", "result": "img", "expected": [30.0, 40.0], "tol_px": 2.0},
            {"kind": "image_stat", "result": "img", "stat": "shape0", "expected": 60, "tol": 0},
            {"kind": "image_stat", "result": "img", "stat": "max", "expected": 1.0, "tol": 1e-6},
        ],
    }
    c.positive(
        "image: centroid, shape and maximum",
        cdata,
        {"status": "COMPLETE", "results": [{"type": "image", "name": "img", "path": str(img_path)}]},
        tmp,
    )
    c.negative(
        "image: centroid 9 px off",
        cdata,
        {"status": "COMPLETE", "results": [{"type": "image", "name": "img", "path": str(img_wrong)}]},
        tmp,
    )
    tall = tmp / "tall.tif"
    tifffile.imwrite(tall, np.zeros((61, 80), np.float32) + blob[:1].max())
    c.negative(
        "image: shape 61 instead of 60",
        {"id": "shape", "checks": [cdata["checks"][1]]},
        {"status": "COMPLETE", "results": [{"type": "image", "name": "img", "path": str(tall)}]},
        tmp,
    )
    stack_ok, stack_bad = tmp / "three_channels_ok.tif", tmp / "three_channels_bad.tif"
    tifffile.imwrite(stack_ok, np.stack([np.full((8, 8), v, np.uint16) for v in (10, 20, 30)]))
    tifffile.imwrite(stack_bad, np.stack([np.full((8, 8), v, np.uint16) for v in (10, 20, 43)]))
    sdata: dict[str, Any] = {
        "id": "slices",
        "checks": [
            {
                "kind": "tiff_slice_means",
                "glob": "three_channels_ok.tif",
                "means": [10, 20, 30],
                "tol": 1.0,
                "axis": 0,
            }
        ],
    }
    c.positive("files: channel means 10, 20, 30", sdata, {"status": "COMPLETE", "results": []}, tmp)
    sdata_bad: dict[str, Any] = {
        "id": "slices",
        "checks": [{**sdata["checks"][0], "glob": "three_channels_bad.tif"}],
    }
    c.negative("files: third channel mean 43", sdata_bad, {"status": "COMPLETE", "results": []}, tmp)


def cli_exit_codes(c: Controls) -> None:
    """The command line itself: exit 0 for right reports, 1 for a wrong one, 1 when a report is missing (NOT_RUN is a failure)."""
    app = c.root / "LabConstrictor-Playground"
    d = c.dataset("LabConstrictor-Playground", "pg_area_u8")
    folder = c.tmp / "reports"
    folder.mkdir()
    good = oracle(d, app)
    (folder / "pg_area_u8.json").write_text(json.dumps(good), encoding="utf-8")
    command = [
        sys.executable,
        str(HERE / "check_ground_truth.py"),
        str(app / "ground_truth.json"),
        "--reports",
        str(folder),
        "--only",
        "pg_area_u8",
    ]
    right = subprocess.run(command, capture_output=True, text=True)
    c.result(good, "values")["values"]["area_um2"] = 300.0
    (folder / "pg_area_u8.json").write_text(json.dumps(good), encoding="utf-8")
    wrong = subprocess.run(command, capture_output=True, text=True)
    (folder / "pg_area_u8.json").unlink()
    missing = subprocess.run(command, capture_output=True, text=True)
    for name, proc, want in (
        ("right report", right, 0),
        ("wrong area", wrong, 1),
        ("missing report", missing, 1),
    ):
        ok = proc.returncode == want
        print(
            "  [exit code]   %-44s exit %d (required %d)%s"
            % (name, proc.returncode, want, "" if ok else "  <-- WRONG")
        )
        if not ok:
            c.failures.append("exit code of " + name)


def main(argv: list[str] | None = None) -> int:
    root = Path((argv or sys.argv[1:])[0])
    c = Controls(root)
    print("== checks that read results")
    run_app_controls(c)
    print("== checks that read files")
    run_file_controls(c)
    print("== command line")
    cli_exit_codes(c)
    print(
        "SUMMARY %d right results passed, %d wrong results failed as required, %d control problem(s)"
        % (c.n_positive, c.n_negative, len(c.failures))
    )
    for f in c.failures:
        print("PROBLEM", f)
    return 1 if c.failures else 0


if __name__ == "__main__":
    sys.exit(main())
