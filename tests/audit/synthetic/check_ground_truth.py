#!/usr/bin/env python3
"""Compare the results of a run with the ground truth of the synthetic datasets, independently of the host that produced them.

GENERIC: it reads only `ground_truth.json` (written by the generator) and report files; no app, no host, no LabConstrictor import
(numpy and pandas only).

    python check_ground_truth.py ground_truth.json --reports DIR [--only ID ...] [--json OUT.json]

DIR holds one `<dataset id>.json` per dataset: the JSON that `labconstrictor-tools run` prints (status, code, error, results), as the
host UI-audit drivers and the notebook runner write it. A driver may add `"host_observed": {"<field>": value}` (what the host form
or layer showed after opening the file). Prints one `CHECK` line per assertion; exit 0 only when every check of every selected
dataset passed. A dataset with checks and no report is NOT_RUN and counts as a failure (never a silent skip).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd

Report = dict[str, Any]
Verdict = tuple[bool, str]


def load_report(path: Path) -> Report:
    """The JSON object in a file, which may start with progress lines (as the CLI prints them)."""
    text = path.read_text(encoding="utf-8")
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("%s holds no JSON object" % path)
    return json.loads(text[start : end + 1])


def _result(report: Report, name: str | None, kind: str | None = None) -> dict[str, Any] | None:
    for item in report.get("results") or []:
        if (name is None or item.get("name") == name) and (kind is None or item.get("type") == kind):
            return item
    return None


def _close(actual: Any, expected: Any, tol: float, rtol: float) -> bool:
    if isinstance(expected, list):
        return (
            isinstance(actual, list)
            and len(actual) == len(expected)
            and all(_close(a, e, tol, rtol) for a, e in zip(actual, expected))
        )
    if isinstance(expected, bool) or not isinstance(expected, (int, float)):
        return actual == expected
    if isinstance(actual, bool) or not isinstance(actual, (int, float)):
        return False
    if math.isnan(expected):
        return math.isnan(actual)
    return abs(actual - expected) <= tol + rtol * abs(expected)


def check_status(check: dict[str, Any], report: Report, base: Path) -> Verdict:
    problems = []
    if report.get("status") != check["status"]:
        problems.append(
            "status %s, expected %s (error: %s)"
            % (report.get("status"), check["status"], report.get("error"))
        )
    elif check["status"] == "FAILED":
        if "code" in check and report.get("code") != check["code"]:
            problems.append("code %r, expected %r" % (report.get("code"), check["code"]))
        if "message_contains" in check and check["message_contains"] not in (report.get("error") or ""):
            problems.append("message %r lacks %r" % (report.get("error"), check["message_contains"]))
    return not problems, "; ".join(problems) or "status %s" % report.get("status")


def check_value(check: dict[str, Any], report: Report, base: Path) -> Verdict:
    result = _result(report, check.get("result"), "values")
    if result is None:
        return False, "no values result (status %s)" % report.get("status")
    values = result["values"]
    key = check["key"]
    if key not in values:
        return False, "no value %r (has: %s)" % (key, ", ".join(sorted(values)))
    actual = values[key]
    if "contains" in check:
        return isinstance(actual, str) and check["contains"] in actual, "%s = %r, expected to contain %r" % (
            key,
            actual,
            check["contains"],
        )
    if "expected" in check:
        ok = _close(actual, check["expected"], check.get("tol", 0.0), check.get("rtol", 0.0))
        return ok, "%s = %r, expected %r (tol %g, rtol %g)" % (
            key,
            actual,
            check["expected"],
            check.get("tol", 0.0),
            check.get("rtol", 0.0),
        )
    lo, hi = check.get("minimum", -math.inf), check.get("maximum", math.inf)
    ok = isinstance(actual, (int, float)) and not isinstance(actual, bool) and lo <= actual <= hi
    return ok, "%s = %r, expected between %s and %s" % (key, actual, lo, hi)


def check_absent_value(check: dict[str, Any], report: Report, base: Path) -> Verdict:
    result = _result(report, check.get("result"), "values")
    if result is None:
        return False, "no values result (status %s)" % report.get("status")
    present = check["key"] in result["values"]
    return not present, "%s is %s%s" % (
        check["key"],
        "present: %r" % result["values"][check["key"]] if present else "absent",
        "" if not present else " (the truth has no such value)",
    )


def check_matrix(check: dict[str, Any], report: Report, base: Path) -> Verdict:
    result = _result(report, check.get("result"), "affine")
    if result is None:
        return False, "no affine result (status %s)" % report.get("status")
    actual, expected = np.array(result["matrix_yx"], dtype=float), np.array(check["expected"], dtype=float)
    d_lin = float(np.abs(actual[:2, :2] - expected[:2, :2]).max())
    d_tr = float(np.abs(actual[:2, 2] - expected[:2, 2]).max())
    d_row = float(np.abs(actual[2] - expected[2]).max())
    ok = d_lin <= check["atol_linear"] and d_tr <= check["atol_translation"] and d_row <= 1e-9
    return (
        ok,
        "linear part off by %.4g (limit %g), translation off by %.4g px (limit %g), last row off by %.2g"
        % (d_lin, check["atol_linear"], d_tr, check["atol_translation"], d_row),
    )


def check_table(check: dict[str, Any], report: Report, base: Path) -> Verdict:
    result = _result(report, check.get("result"), "table")
    if result is None:
        return False, "no table result (status %s)" % report.get("status")
    actual = pd.read_csv(result["path"])
    problems = []
    if "rows" in check and len(actual) != check["rows"]:
        problems.append("%d rows, expected %d" % (len(actual), check["rows"]))
    missing = [c for c in check["columns"] if c not in actual.columns]
    if missing:
        problems.append("missing columns %s" % missing)
    if check.get("truth_csv") and not missing:
        truth = pd.read_csv(base / check["truth_csv"])
        key = check.get("key")
        if key:
            a, t = actual.set_index(actual[key].astype(str)), truth.set_index(truth[key].astype(str))
            gone = sorted(set(t.index) - set(a.index))
            extra = sorted(set(a.index) - set(t.index))
            if gone or extra:
                problems.append("rows missing %s, unexpected rows %s" % (gone[:5], extra[:5]))
            common = sorted(set(a.index) & set(t.index))
            a, t = a.loc[common], t.loc[common]
        else:
            a, t = actual, truth
            if len(a) != len(t):
                problems.append("%d rows, truth has %d" % (len(a), len(t)))
                n = min(len(a), len(t))
                a, t = a.iloc[:n], t.iloc[:n]
        for column in check["columns"]:
            if column in t.columns and column in a.columns:
                x, y = a[column].to_numpy(dtype=float), t[column].to_numpy(dtype=float)
                bad = ~np.isclose(x, y, rtol=check["rtol"], atol=check["atol"], equal_nan=True)
                if bad.any():
                    i = int(np.flatnonzero(bad)[0])
                    problems.append(
                        "%s: %d of %d rows differ, first at %s: %r, expected %r"
                        % (column, int(bad.sum()), len(x), t.index[i], float(x[i]), float(y[i]))
                    )
    return not problems, "; ".join(problems) or "%d rows, columns %s equal the truth" % (
        len(actual),
        check["columns"],
    )


def check_table_bound(check: dict[str, Any], report: Report, base: Path) -> Verdict:
    result = _result(report, check.get("result"), "table")
    if result is None:
        return False, "no table result (status %s)" % report.get("status")
    column = pd.read_csv(result["path"])[check["column"]].to_numpy(dtype=float)
    worst = float(np.nanmax(np.abs(column))) if len(column) else 0.0
    ok = bool(np.isfinite(column).all()) and worst <= check["maximum"]
    return ok, "%s: largest value %.6g (limit %g), all finite: %s" % (
        check["column"],
        worst,
        check["maximum"],
        bool(np.isfinite(column).all()),
    )


def check_points_map(check: dict[str, Any], report: Report, base: Path) -> Verdict:
    """The query nuclei (points, original pixels of the query), moved by the TRUTH matrix, must land on reference nuclei (points, original pixels
    of the reference): a frame check of the point outputs that does not depend on the matrix the tool found.
    """
    src, dst = _result(report, check["source"], "points"), _result(report, check["target"], "points")
    if src is None or dst is None:
        return False, "missing points result (status %s)" % report.get("status")
    q, r = pd.read_csv(src["path"])[["y", "x"]].to_numpy(float), pd.read_csv(dst["path"])[
        ["y", "x"]
    ].to_numpy(float)
    m = np.array(check["matrix"], dtype=float)
    moved = q @ m[:2, :2].T + m[:2, 2]
    inside = (
        (moved[:, 0] >= 0)
        & (moved[:, 0] < check["target_shape"][0])
        & (moved[:, 1] >= 0)
        & (moved[:, 1] < check["target_shape"][1])
    )
    moved = moved[inside]
    if not len(moved) or not len(r):
        return False, "no query nucleus lands inside the reference (%d query, %d reference points)" % (
            len(q),
            len(r),
        )
    nearest = np.sqrt(((moved[:, None, :] - r[None, :, :]) ** 2).sum(axis=2)).min(axis=1)
    fraction = float((nearest <= check["tol_px"]).mean())
    return fraction >= check[
        "min_fraction"
    ], "%.0f%% of %d query nuclei land within %g px of a reference nucleus (median distance %.2f px, need %.0f%%)" % (
        100 * fraction,
        len(moved),
        check["tol_px"],
        float(np.median(nearest)),
        100 * check["min_fraction"],
    )


def check_message(check: dict[str, Any], report: Report, base: Path) -> Verdict:
    result = _result(report, check.get("result"), "message")
    if result is None:
        return False, "no message result (status %s)" % report.get("status")
    found = check["contains"] in result["text"]
    return found, "message %r %s %r" % (
        result["text"][:120],
        "contains" if found else "lacks",
        check["contains"],
    )


def check_host_param(check: dict[str, Any], report: Report, base: Path) -> Verdict:
    observed = report.get("host_observed") or {}
    if check["param"] not in observed:
        return False, "the host reported nothing for %r (host_observed: %s)" % (
            check["param"],
            sorted(observed),
        )
    actual = observed[check["param"]]
    return _close(
        actual, check["expected"], check.get("tol", 0.0), 0.0
    ), "host showed %s = %r, expected %r" % (check["param"], actual, check["expected"])


def _image(report: Report, check: dict[str, Any]) -> np.ndarray | None:
    import tifffile

    result = _result(report, check.get("result"))
    if result is None or "path" not in result:
        return None
    return tifffile.imread(result["path"])


def check_image_stat(check: dict[str, Any], report: Report, base: Path) -> Verdict:
    array = _image(report, check)
    if array is None:
        return False, "no image result %r (status %s)" % (check.get("result"), report.get("status"))
    stats: dict[str, Callable[[np.ndarray], float]] = {
        "mean": lambda a: float(a.mean()),
        "max": lambda a: float(a.max()),
        "min": lambda a: float(a.min()),
        "shape0": lambda a: float(a.shape[0]),
        "shape1": lambda a: float(a.shape[1]),
    }
    actual = stats[check["stat"]](array)
    return abs(actual - check["expected"]) <= check["tol"], "%s of %s = %.6g, expected %s (tol %g)" % (
        check["stat"],
        check["result"],
        actual,
        check["expected"],
        check["tol"],
    )


def check_centroid(check: dict[str, Any], report: Report, base: Path) -> Verdict:
    array = _image(report, check)
    if array is None:
        return False, "no image result %r (status %s)" % (check.get("result"), report.get("status"))
    a = array.astype(np.float64)
    total = a.sum()
    if not total > 0:
        return False, "image has no signal"
    yy, xx = np.indices(a.shape)
    got = ((yy * a).sum() / total, (xx * a).sum() / total)
    dist = math.hypot(got[0] - check["expected"][0], got[1] - check["expected"][1])
    return dist <= check["tol_px"], "centroid (%.2f, %.2f), expected (%s, %s), %.2f px away (limit %g)" % (
        got[0],
        got[1],
        check["expected"][0],
        check["expected"][1],
        dist,
        check["tol_px"],
    )


def check_tiff_slice_means(check: dict[str, Any], report: Report, base: Path) -> Verdict:
    import tifffile

    files = sorted(base.glob(check["glob"]))
    if not files:
        return False, "no file matches %s under %s" % (check["glob"], base)
    array = tifffile.imread(files[0]).astype(np.float64)
    other = tuple(i for i in range(array.ndim) if i != check["axis"])
    got = array.mean(axis=other)
    ok = len(got) == len(check["means"]) and bool(np.allclose(got, check["means"], atol=check["tol"]))
    return ok, "%s: means %s, expected %s" % (files[0].name, np.round(got, 3).tolist(), check["means"])


CHECKS: dict[str, Callable[[dict[str, Any], Report, Path], Verdict]] = {
    "status": check_status,
    "value": check_value,
    "absent_value": check_absent_value,
    "matrix": check_matrix,
    "points_map": check_points_map,
    "table": check_table,
    "table_bound": check_table_bound,
    "message": check_message,
    "host_param": check_host_param,
    "image_stat": check_image_stat,
    "centroid": check_centroid,
    "tiff_slice_means": check_tiff_slice_means,
}


def check_dataset(
    dataset: dict[str, Any], report: Report | None, base: Path, with_host: bool = False
) -> list[dict[str, Any]]:
    """One row per check: {dataset, check, status PASS|FAIL|NOT_RUN, detail}. `host_checks` (what a host form showed) only with `with_host`."""
    rows = []
    for number, check in enumerate(dataset["checks"] + (dataset.get("host_checks", []) if with_host else [])):
        name = "%s_%d_%s" % (
            dataset["id"],
            number,
            check["kind"] + (":" + str(check["key"]) if check.get("key") else ""),
        )
        if report is None:
            rows.append(
                {
                    "dataset": dataset["id"],
                    "check": name,
                    "status": "NOT_RUN",
                    "detail": "no report file for this dataset",
                }
            )
            continue
        function = CHECKS.get(check["kind"])
        if function is None:
            rows.append(
                {
                    "dataset": dataset["id"],
                    "check": name,
                    "status": "FAIL",
                    "detail": "unknown check kind %r" % check["kind"],
                }
            )
            continue
        try:
            ok, detail = function(check, report, base)
        except (
            Exception
        ) as error:  # noqa: BLE001 - a check that cannot run is a failure with its reason, never a skip
            ok, detail = False, "%s: %s" % (type(error).__name__, error)
        rows.append(
            {"dataset": dataset["id"], "check": name, "status": "PASS" if ok else "FAIL", "detail": detail}
        )
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    parser.add_argument("truth", type=Path, help="ground_truth.json")
    parser.add_argument("--reports", type=Path, required=True, help="folder of <dataset id>.json run reports")
    parser.add_argument(
        "--data",
        type=Path,
        help="the folder the run actually used (default: the folder of ground_truth.json); only for checks that read files the run wrote",
    )
    parser.add_argument("--only", action="append", default=[], help="check only this dataset id (repeatable)")
    parser.add_argument(
        "--with-host", action="store_true", help="also judge `host_checks` (reports must carry host_observed)"
    )
    parser.add_argument("--json", type=Path, help="also write the rows here")
    args = parser.parse_args(argv)
    truth = json.loads(args.truth.read_text(encoding="utf-8"))
    base = args.truth.resolve().parent
    selected = [d for d in truth["datasets"] if not args.only or d["id"] in args.only]
    unknown = sorted(set(args.only) - {d["id"] for d in truth["datasets"]})
    if unknown:
        print("unknown dataset id(s): %s" % ", ".join(unknown), file=sys.stderr)
        return 2
    rows: list[dict[str, Any]] = []
    for dataset in selected:
        path = args.reports / (dataset["id"] + ".json")
        report = load_report(path) if path.is_file() else None
        if not dataset["checks"] and not (args.with_host and dataset.get("host_checks")):
            print(
                "NOTE %s has no machine oracle for this run (%s): judged by a person%s"
                % (
                    dataset["id"],
                    dataset["expected"],
                    " or by a host driver (--with-host)" if dataset.get("host_checks") else "",
                )
            )
            continue
        rows += check_dataset(dataset, report, args.data or base, args.with_host)
    for row in rows:
        print("CHECK %-70s %-7s %s" % (row["check"], row["status"], row["detail"]))
    counts = {s: sum(r["status"] == s for r in rows) for s in ("PASS", "FAIL", "NOT_RUN")}
    print("SUMMARY %s (%d checks, %d datasets)" % (counts, len(rows), len(selected)))
    if args.json:
        args.json.write_text(json.dumps({"summary": counts, "rows": rows}, indent=2) + "\n", encoding="utf-8")
    return 0 if counts["FAIL"] == 0 and counts["NOT_RUN"] == 0 and rows else 1


if __name__ == "__main__":
    sys.exit(main())
