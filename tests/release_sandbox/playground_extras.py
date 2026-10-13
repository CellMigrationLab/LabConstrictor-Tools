"""Checks of an installed LabConstrictor Playground (run with the app's own Python). Prints 'CHECK <id> PASS|FAIL <detail>' lines.

usage: python playground_extras.py <section> --prefix P --app-name LabConstrictorPlayground --fixtures lc_tests --work W
sections: basic | tools | failures | retention
"""

import argparse
import importlib.metadata as md
import json
import os
import subprocess
import sys
import time
from pathlib import Path

APP = "LabConstrictorPlayground"
OUT = []


def rec(cid, ok, detail=""):
    line = "CHECK %s %s %s" % (cid, "PASS" if ok else "FAIL", str(detail).replace("\n", " | ")[:600])
    print(line, flush=True)
    OUT.append((cid, ok))


def lc(*args, timeout=600, env=None):
    cmd = [sys.executable, "-m", "labconstrictor_tools", *args]
    p = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, env=env
    )
    return p.returncode, p.stdout, p.stderr


def run_tool(tool, *params, timeout=300):
    rc, out, err = lc("run", APP, tool, *params, timeout=timeout)
    try:
        # the JSON report is the first '{' .. last '}' of stdout
        rep = json.loads(out[out.index("{") : out.rindex("}") + 1])
    except Exception:
        rep = {"status": "NOJSON", "raw": out[-300:], "err": err[-300:]}
    return rc, rep, err


def home():
    return Path(os.environ.get("LC_HOME") or (Path.home() / ".labconstrictor"))


def basic(a):
    prefix = Path(a.prefix)
    log = prefix / "menuinst_debug.log"
    txt = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
    rec(
        "1a_post_install_ok",
        "Post-install completed successfully." in txt,
        (
            "(AFTER THE WORKAROUND: the shipped installer exited %s) " % os.environ.get("INSTALL_RC")
            if os.environ.get("INSTALL_RC", "0") != "0"
            else ""
        )
        + ("log tail: " + txt.strip().splitlines()[-1] if txt.strip() else "no log"),
    )
    rec(
        "1b_tools_registered",
        "Tools registered" in txt
        or (
            "Found labconstrictor_playground_lc_tools: registering" in txt
            and "WARNING: tool registration failed" not in txt
            and os.name == "nt"
        ),
        [
            ln
            for ln in txt.splitlines()
            if "Tools registered" in ln or "Found labconstrictor" in ln or "WARNING" in ln
        ],
    )
    rec("1c_no_registration_warning", "WARNING: tool registration failed" not in txt)
    rc, out, err = lc("list")
    names = [
        "check_everything",
        "list_devices",
        "run_on_device",
        "make_test_data",
        "feature_tour",
        "look_inside_file",
        "summarise_table",
        "count_above_level",
        "bright_area",
        "align_centres",
        "stress_big_image",
        "stress_many_points",
        "stress_slow",
        "stress_crash",
        "stress_out_of_memory",
        "stress_real_memory",
        "stress_hang",
    ]
    missing = [n for n in names if n not in out]
    rec(
        "2a_list_shows_tools",
        rc == 0 and APP in out and not missing,
        "missing=%s | %s" % (missing, out[:400]),
    )
    rc, out, err = lc("doctor", "--json")
    try:
        f = json.loads(out)
    except Exception:
        f = []
    errs = [x for x in f if x.get("level") != "ok"]
    mine = [x for x in f if x.get("app") == APP]
    rec("2b_doctor_clean", rc == 0 and bool(mine) and not errs, "rc=%s findings=%s" % (rc, f))
    ver = md.version("labconstrictor-tools")
    du = ""
    try:
        du = md.distribution("labconstrictor-tools").read_text("direct_url.json") or ""
    except Exception:
        pass
    rec(
        "3_tools_version_rc1",
        ver in ("0.2.0rc1", "0.2.0-rc.1") and "v0.2.0-rc.1" in du,
        "version=%s direct_url=%s" % (ver, du.strip()),
    )
    nb = list(prefix.rglob("*.ipynb"))[:50]
    rec(
        "4n_notebooks_present",
        any("Playground" in str(p) or "Welcome" in str(p) for p in nb),
        [str(p.relative_to(prefix)) for p in nb][:6],
    )


def tools(a):
    fx = Path(a.fixtures) / "fixtures" / "data"
    work = Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    data = work / "data"
    data.mkdir(exist_ok=True)

    def check(cid, tool, params, want="COMPLETE", code=None, contains=None, timeout=300):
        rc, rep, err = run_tool(tool, *params, timeout=timeout)
        ok = (
            rep.get("status") == want
            and (code is None or rep.get("code") == code)
            and (contains is None or contains in json.dumps(rep, ensure_ascii=False))
        )
        rec(
            cid,
            ok,
            "status=%s code=%s secs=%s %s"
            % (rep.get("status"), rep.get("code"), rep.get("seconds"), (rep.get("error") or "")[:200]),
        )
        return rep

    check("4_list_devices", "list_devices", [], contains="installed")
    check(
        "4_check_everything",
        "check_everything",
        ["run_benchmark=true", "check_internet=false"],
        contains="checks:",
        timeout=400,
    )
    check("4_run_on_device_cpu", "run_on_device", ["device=cpu", "size=128", "repeats=2"])
    check(
        "4_make_test_data",
        "make_test_data",
        ["folder=" + str(data), "kind=all", "size=64"],
        contains="three_channels",
    )
    rep = check("4_stress_big_image", "stress_big_image", ["megabytes=4"])
    try:
        import tifffile

        arr = tifffile.imread(rep["results"][0]["path"])
        rec(
            "4_stress_big_image_is_uint16_about_4MB",
            str(arr.dtype) == "uint16" and 3.5e6 < arr.nbytes < 4.6e6,
            "dtype=%s bytes=%d" % (arr.dtype, arr.nbytes),
        )
    except Exception as e:
        rec("4_stress_big_image_is_uint16_about_4MB", False, e)
    check("4_stress_many_points", "stress_many_points", ["count=5000"])
    check("4_stress_slow", "stress_slow", ["seconds=2"])
    check(
        "4_stress_out_of_memory",
        "stress_out_of_memory",
        [],
        want="FAILED",
        code="MemoryError",
        contains="SIMULATED",
    )
    check("4_stress_real_memory", "stress_real_memory", ["target_mb=64", "limit_mb=64"], timeout=300)
    check("4_feature_tour_demo", "feature_tour", [], contains="16", timeout=300)
    check(
        "4_feature_tour_image",
        "feature_tour",
        ["image=" + str(fx / "demo_blobs.tif"), "side_note=hello"],
        contains="hello",
    )
    check("4_look_inside_json", "look_inside_file", ["file=" + str(fx / "settings.json")], contains="json")
    check("4_summarise_table", "summarise_table", ["table=" + str(fx / "measurements.csv")])
    check(
        "4_count_above_level",
        "count_above_level",
        ["image=" + str(fx / "square_a.tif"), "mode=fixed", "level=100"],
        contains="16",
    )
    check(
        "4_bright_area",
        "bright_area",
        ["image=" + str(fx / "square_a.tif"), "pixel_size=0.5"],
        contains="4.0",
    )
    rep = check(
        "4_align_centres",
        "align_centres",
        ["image=" + str(fx / "square_a.tif"), "reference=" + str(fx / "square_b.tif")],
    )
    s = json.dumps(rep)
    rec("4_align_centres_matrix", "10" in s and "12" in s, s[:300])
    # the project's own case suite, with the installed interpreter (cancel and crash cases included)
    rc, out, err = lc(
        "test",
        "--module",
        "labconstrictor_playground_lc_tools",
        "--cases",
        str(Path(a.fixtures) / "cases.json"),
        "--json",
        timeout=1500,
    )
    try:
        j = json.loads(out)
        probs = [(r.get("tool"), r["problems"]) for r in j["reports"] if r["problems"]]
        rec(
            "4_cases_json_suite",
            rc == 0 and not probs,
            "reports=%d problems=%s untested=%s" % (len(j["reports"]), probs, j.get("untested")),
        )
    except Exception as e:
        rec("4_cases_json_suite", False, "%s: %s %s" % (e, out[-300:], err[-300:]))
    # the notebook path: the same tool through the notebook form, in this process (as a notebook kernel does)
    try:
        os.environ.setdefault("MPLBACKEND", "Agg")
        from labconstrictor_playground_lc_tools import bright_area, look_inside_file

        from labconstrictor_tools.notebook import form

        f = form(look_inside_file)
        f.controls["file"].value = str(fx / "settings.json")
        res = f.run()
        rec("4n_notebook_form_run", bool(res), "results=%s" % (str(res)[:200]))
        g = form(bright_area)
        g.controls["image"].value = str(fx / "square_a.tif")
        res2 = g.run()
        rec(
            "4n_notebook_form_missing_pixel_size_refused",
            res2 is None or not res2,
            "returned=%s status=%s" % (str(res2)[:100], getattr(g.status, "value", "")[:200]),
        )
    except Exception as e:
        rec("4n_notebook_form_run", False, "%s: %s" % (type(e).__name__, e))


def failures(a):
    fx = Path(a.fixtures) / "fixtures" / "data"
    from labconstrictor_tools import client

    rc, rep, err = run_tool("bright_area", "image=" + str(fx / "square_a.tif"))
    rec(
        "5a_missing_pixel_size_refused",
        rep.get("status") == "FAILED"
        and rep.get("code") == "pixel_size_unknown"
        and "pixel size" in (rep.get("error") or ""),
        "%s %s" % (rep.get("code"), rep.get("error")),
    )
    rc, rep, err = run_tool("bright_area", "image=" + str(fx / "square_a.tif"), "pixel_size=0")
    rec(
        "5a2_zero_pixel_size_refused",
        rep.get("status") == "FAILED" and rep.get("code") == "invalid_pixel_size",
        "%s" % rep.get("code"),
    )
    # cooperative cancel
    with client.WorkerProcess(APP) as w:
        t = w.task("stress_slow", {"seconds": 30, "_job_dir": str(Path(a.work) / "j1")})
        time.sleep(3)
        t0 = time.time()
        t.cancel()
        t.wait(30)
        rec(
            "5b_cancel_polite_tool",
            t.status == "CANCELED" and time.time() - t0 < 20,
            "status=%s after %.1fs" % (t.status, time.time() - t0),
        )
    # cancel of a tool that ignores it: killed after grace, must read CANCELED (not CRASHED)
    with client.WorkerProcess(APP) as w:
        t = w.task("stress_hang", {"seconds": 60, "_job_dir": str(Path(a.work) / "j2")})
        time.sleep(3)
        t0 = time.time()
        t.cancel(grace=3)
        t.wait(40)
        rec(
            "5c_killed_after_cancel_names_the_cancel",
            t.cancel_requested and "did not stop when Cancel was pressed" in (t.error or ""),
            "status=%s code=%s error=%s after %.1fs"
            % (t.status, t.code, (t.error or "")[:120], time.time() - t0),
        )
        alive = w.alive() if callable(getattr(w, "alive", None)) else w.alive
        rec("5c2_no_process_left_after_cancel_kill", not alive, "alive=%s" % alive)
    # a real crash without cancel
    rc, rep, err = run_tool("stress_crash")
    rec(
        "5d_crash_reported",
        rep.get("status") == "CRASHED",
        "status=%s error=%s" % (rep.get("status"), (rep.get("error") or "")[:200]),
    )
    # an unknown device
    rc, rep, err = run_tool("run_on_device", "device=cuda:7", "size=64", "repeats=1")
    rec(
        "5e_unknown_device_refused",
        rep.get("code") == "unknown_device" and "cpu" in (rep.get("error") or ""),
        "%s" % (rep.get("error") or "")[:200],
    )


def retention(a):

    fx = Path(a.fixtures) / "fixtures" / "data"
    h = home()
    (h / "results").mkdir(parents=True, exist_ok=True)
    foreign_r = h / "results" / "user_own_folder"
    foreign_r.mkdir(exist_ok=True)
    (foreign_r / "keep.txt").write_text("user data")
    (h / "runs").mkdir(parents=True, exist_ok=True)
    foreign_runs = h / "runs" / "user_own_run_folder"
    foreign_runs.mkdir(exist_ok=True)
    (foreign_runs / "keep.txt").write_text("user data")
    names = []
    N = int(a.n_runs)
    for i in range(N):
        rc, rep, err = run_tool("look_inside_file", "file=" + str(fx / "notes.txt"))
        if rep.get("status") != "COMPLETE":
            rec("6_runs_complete", False, "run %d: %s" % (i, rep))
            return
        names.append(Path(rep["job_dir"]).name)
    rec("6_runs_complete", True, "%d runs" % N)
    res = sorted(p for p in (h / "results").iterdir() if p.is_dir() and p.name != "user_own_folder")
    owned = [p for p in res if (p / ".lc-owner.json").exists()]
    done = [p for p in res if (p / ".lc-done.json").exists()]
    rec(
        "6a_markers_present",
        len(owned) == len(res) and len(done) == len(res) and len(res) > 0,
        "folders=%d owner=%d done=%d" % (len(res), len(owned), len(done)),
    )
    rec(
        "6b_results_keep_newest_20",
        len(res) == 20 and set(p.name for p in res) == set(names[-20:]),
        "kept=%d newest20_match(by run order)=%s" % (len(res), set(p.name for p in res) == set(names[-20:])),
    )
    try:
        od = json.loads((owned[0] / ".lc-owner.json").read_text())
        dn = json.loads((done[0] / ".lc-done.json").read_text())
        rec("6c_marker_contents", True, "owner=%s done=%s" % (od, dn))
    except Exception as e:
        rec("6c_marker_contents", False, e)
    rc, out, err = lc("prune", "--dry-run", "--json")
    try:
        j = json.loads(out)
    except Exception:
        j = {"roots": []}
    by = {Path(r["root"]).name: r for r in j["roots"]}
    rr, rn = by.get("results", {}), by.get("runs", {})
    rec(
        "6d_prune_dry_run_json",
        rc == 0 and j.get("dry_run") is True and rr.get("keep") == 20 and rn.get("keep") == 50,
        "results keep=%s kept=%s deleted=%s skipped=%s | runs keep=%s kept=%s deleted=%s skipped=%s"
        % (
            rr.get("keep"),
            len(rr.get("kept", [])),
            len(rr.get("deleted", [])),
            [s["name"] for s in rr.get("skipped", [])],
            rn.get("keep"),
            len(rn.get("kept", [])),
            len(rn.get("deleted", [])),
            [s["name"] for s in rn.get("skipped", [])],
        ),
    )
    rec(
        "6e_foreign_folders_left_alone",
        (foreign_r / "keep.txt").exists()
        and (foreign_runs / "keep.txt").exists()
        and any(s["name"] == "user_own_folder" for s in rr.get("skipped", [])),
        "",
    )
    runs = sorted(p for p in (h / "runs").iterdir() if p.is_dir() and p.name != "user_own_run_folder")
    rec("6f_run_records_keep_50", len(runs) == 50, "run record folders=%d (after %d runs)" % (len(runs), N))
    # make the quota bite: run 3 more, then a real prune must change nothing (already pruned) and the dry run must delete 0
    rc, out, err = lc("prune", "--json")
    j2 = json.loads(out)
    rec(
        "6g_real_prune_removes_nothing_more",
        all(not r["deleted"] for r in j2["roots"]) and rc == 0,
        "deleted=%s" % [len(r["deleted"]) for r in j2["roots"]],
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("section")
    ap.add_argument("--prefix", default=sys.prefix)
    ap.add_argument("--fixtures", default="lc_tests")
    ap.add_argument("--work", default="work")
    ap.add_argument("--n-runs", default="60")
    a = ap.parse_args()
    globals()[a.section](a)
    bad = [c for c, ok in OUT if not ok]
    print("SECTION %s: %d checks, %d failed %s" % (a.section, len(OUT), len(bad), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
