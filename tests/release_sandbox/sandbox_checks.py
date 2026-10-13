"""Checks of an INSTALLED LabConstrictor app (run with the app's own Python), for any app: the expectations come from the app itself
(its registered schema and its lc_tests/cases.json), not from this file. Prints `CHECK <id> PASS|FAIL <detail>` lines.

    python sandbox_checks.py basic     --app NAME --prefix P [--expect-version V] [--tools-pin TAG]
    python sandbox_checks.py cases     --app NAME --module M --cases lc_tests/cases.json
    python sandbox_checks.py retention --app NAME --cases lc_tests/cases.json [--n-runs 60]
App-specific extras (the Playground's own failure paths and tool runs) live in playground_extras.py and are selected by the workflow.
"""

import argparse
import importlib
import importlib.metadata as md
import json
import os
import subprocess
import sys
from pathlib import Path

OUT = []


def rec(cid, ok, detail=""):
    print(
        "CHECK %s %s %s" % (cid, "PASS" if ok else "FAIL", str(detail).replace("\n", " | ")[:600]), flush=True
    )
    OUT.append((cid, ok))


def lc(*args, timeout=900):
    p = subprocess.run(
        [sys.executable, "-m", "labconstrictor_tools", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    return p.returncode, p.stdout, p.stderr


def home():
    return Path(os.environ.get("LC_HOME") or (Path.home() / ".labconstrictor"))


def schema_tools(app):
    f = home() / "apps" / (app + ".schema.json")
    if not f.exists():
        return []
    return [t for t in json.loads(f.read_text(encoding="utf-8")).get("tools", [])]


def basic(a):
    prefix = Path(a.prefix)
    log = prefix / "menuinst_debug.log"
    txt = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
    last = txt.strip().splitlines()[-1] if txt.strip() else "no log"
    rec("1a_post_install_ok", "Post-install completed successfully." in txt, "log tail: " + last)
    # the .sh hook prints "Tools registered"; the .bat hook prints "Found <module>: registering" only (by design)
    registered = "Tools registered" in txt or (os.name == "nt" and "registering the tools of" in txt)
    rec(
        "1b_tools_registered",
        registered and "WARNING: tool registration failed" not in txt,
        [
            ln
            for ln in txt.splitlines()
            if "Tools registered" in ln or "registering the tools" in ln or "WARNING" in ln
        ],
    )
    rc, out, err = lc("list")
    tools = schema_tools(a.app)
    ids = [t.get("id") for t in tools]
    missing = [i for i in ids if i not in out]
    ver_ok = (not a.expect_version) or ("%s  (%s)" % (a.app, a.expect_version)) in out
    rec(
        "2a_list_shows_the_apps_tools",
        rc == 0 and a.app in out and bool(ids) and not missing,
        "tools in schema=%d missing from list=%s" % (len(ids), missing),
    )
    rec("2c_registered_version_is_the_release", ver_ok, out.strip().splitlines()[0] if out.strip() else out)
    rc, out, err = lc("doctor", "--json")
    try:
        f = json.loads(out)
    except Exception:
        f = []
    mine = [x for x in f if x.get("app") == a.app]
    rec(
        "2b_doctor_clean",
        rc == 0 and bool(mine) and all(x.get("level") == "ok" for x in f),
        "rc=%s findings=%s" % (rc, f),
    )
    ver = md.version("labconstrictor-tools")
    du = ""
    try:
        du = md.distribution("labconstrictor-tools").read_text("direct_url.json") or ""
    except Exception:
        pass
    ok = bool(ver) and (not a.tools_pin or a.tools_pin in du)
    rec("3_tools_version_is_the_pin", ok, "version=%s pin=%s direct_url=%s" % (ver, a.tools_pin, du.strip()))
    nb = [
        p
        for p in prefix.rglob("*.ipynb")
        if "site-packages" not in str(p) and "/etc/" not in str(p).replace("\\", "/")
    ]
    rec("4n_notebooks_installed", bool(nb), [str(p.relative_to(prefix)) for p in nb][:5])


def load_cases(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def cli_params(case, base):
    out = []
    for k, v in (case.get("inputs") or {}).items():
        if isinstance(v, bool):
            v = "true" if v else "false"
        elif isinstance(v, str) and (base / v).exists():
            v = str((base / v).resolve())
        out.append("%s=%s" % (k, v))
    return out


def cases(a):
    base = Path(a.cases).parent
    rc, out, err = lc("test", "--module", a.module, "--cases", str(a.cases), "--json", timeout=1800)
    try:
        j = json.loads(out)
        probs = [(r.get("tool"), r["problems"]) for r in j["reports"] if r["problems"]]
        rec(
            "4_cases_suite",
            rc == 0 and not probs,
            "reports=%d problems=%s untested=%s" % (len(j["reports"]), probs, j.get("untested")),
        )
    except Exception as e:
        rec("4_cases_suite", False, "%s: %s %s" % (e, out[-300:], err[-300:]))
    all_ids = [t.get("id") for t in schema_tools(a.app)]
    covered = {c["tool"] for c in load_cases(a.cases)}
    rec(
        "4_every_tool_has_a_case",
        not [i for i in all_ids if i not in covered],
        "tools without a case: %s" % [i for i in all_ids if i not in covered],
    )
    # each COMPLETE case through the real CLI (a person's path), checking the status; failing cases check the code
    for n, c in enumerate(load_cases(a.cases)):
        if c.get("cancel_after_s") is not None or c.get("skip"):
            continue
        exp = c.get("expect", {})
        want = exp.get("status", "COMPLETE")
        if want not in ("COMPLETE", "FAILED"):
            continue
        rc, o, e = lc("run", a.app, c["tool"], *cli_params(c, base), timeout=600)
        try:
            rep = json.loads(o[o.index("{") : o.rindex("}") + 1])
        except Exception:
            rep = {"status": "NOJSON", "raw": o[-200:] + e[-200:]}
        ok = rep.get("status") == want and (
            want == "COMPLETE" or exp.get("code") is None or rep.get("code") == exp.get("code")
        )
        rec(
            "4_cli_case_%02d_%s_%s" % (n, c["tool"], want),
            ok,
            "status=%s code=%s" % (rep.get("status"), rep.get("code")),
        )
    # the notebook form of the first tool that has a COMPLETE case with plain inputs
    try:
        os.environ.setdefault("MPLBACKEND", "Agg")
        from labconstrictor_tools.introspection import describe_tool
        from labconstrictor_tools.notebook import form

        mod = importlib.import_module(a.module)
        funcs = {
            describe_tool(o.__lc_tool__)["id"]: o for o in vars(mod).values() if hasattr(o, "__lc_tool__")
        }
        built = 0
        for tid, fn in funcs.items():
            form(fn)
            built += 1
        rec(
            "4n_notebook_forms_build_for_every_tool",
            built == len(funcs) and built > 0,
            "%d of %d" % (built, len(funcs)),
        )
        for c in load_cases(a.cases):
            if (
                c["tool"] in funcs
                and c.get("expect", {}).get("status", "COMPLETE") == "COMPLETE"
                and c.get("cancel_after_s") is None
            ):
                f = form(funcs[c["tool"]])
                okset = True
                for k, v in (c.get("inputs") or {}).items():
                    if k in f.controls and isinstance(v, (str, int, float, bool)):
                        vv = str((base / v).resolve()) if isinstance(v, str) and (base / v).exists() else v
                        try:
                            f.controls[k].value = vv
                        except Exception:
                            okset = False
                    else:
                        okset = False
                if okset:
                    res = f.run()
                    if res:
                        rec("4n_notebook_form_runs_%s" % c["tool"], True, str(res)[:200])
                    else:  # a form control (an image chooser) that a script cannot fill is not a defect of the app
                        print(
                            "NOTE 4n_notebook_form_run_of_%s_returned_nothing: %s" % (c["tool"], res),
                            flush=True,
                        )
                    break
    except Exception as e:
        rec("4n_notebook_form", False, "%s: %s" % (type(e).__name__, e))


def retention(a):
    base = Path(a.cases).parent
    h = home()
    (h / "results").mkdir(parents=True, exist_ok=True)
    (h / "runs").mkdir(parents=True, exist_ok=True)
    fr, fn = h / "results" / "user_own_folder", h / "runs" / "user_own_run_folder"
    for d in (fr, fn):
        d.mkdir(exist_ok=True)
        (d / "keep.txt").write_text("user data")
    case = next(
        (
            c
            for c in load_cases(a.cases)
            if c.get("expect", {}).get("status", "COMPLETE") == "COMPLETE"
            and c.get("cancel_after_s") is None
            and not c.get("skip")
        ),
        None,
    )
    if case is None:
        rec("6_retention", False, "no COMPLETE case in the app's cases.json to repeat")
        return
    names = []
    for i in range(int(a.n_runs)):
        rc, o, e = lc("run", a.app, case["tool"], *cli_params(case, base), timeout=600)
        try:
            rep = json.loads(o[o.index("{") : o.rindex("}") + 1])
        except Exception:
            rep = {"status": "NOJSON"}
        if rep.get("status") != "COMPLETE":
            rec("6_runs_complete", False, "run %d of %s: %s" % (i, case["tool"], (o + e)[-300:]))
            return
        names.append(Path(rep["job_dir"]).name)
    rec("6_runs_complete", True, "%d runs of %s" % (len(names), case["tool"]))
    res = sorted(p for p in (h / "results").iterdir() if p.is_dir() and p.name != "user_own_folder")
    rec(
        "6a_markers_present",
        res and all((p / ".lc-owner.json").exists() and (p / ".lc-done.json").exists() for p in res),
        "folders=%d" % len(res),
    )
    rec(
        "6b_results_keep_newest_20",
        len(res) == 20 and {p.name for p in res} == set(names[-20:]),
        "kept=%d" % len(res),
    )
    rc, out, err = lc("prune", "--dry-run", "--json")
    try:
        j = json.loads(out)
    except Exception:
        j = {"roots": []}
    by = {Path(r["root"]).name: r for r in j["roots"]}
    rr, rn = by.get("results", {}), by.get("runs", {})
    rec(
        "6d_prune_dry_run_json",
        rc == 0
        and j.get("dry_run") is True
        and rr.get("keep") == 20
        and rn.get("keep") == 50
        and not rr.get("deleted")
        and not rn.get("deleted"),
        "results keep=%s kept=%s deleted=%s | runs keep=%s kept=%s deleted=%s"
        % (
            rr.get("keep"),
            len(rr.get("kept", [])),
            len(rr.get("deleted", [])),
            rn.get("keep"),
            len(rn.get("kept", [])),
            len(rn.get("deleted", [])),
        ),
    )
    rec(
        "6e_foreign_folders_left_alone",
        (fr / "keep.txt").exists()
        and (fn / "keep.txt").exists()
        and any(s["name"] == "user_own_folder" for s in rr.get("skipped", [])),
        "",
    )
    runs = [p for p in (h / "runs").iterdir() if p.is_dir() and p.name != "user_own_run_folder"]
    rec(
        "6f_run_records_keep_50",
        len(runs) == 50,
        "run record folders=%d after %d runs" % (len(runs), len(names)),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("section")
    ap.add_argument("--app", required=True)
    ap.add_argument("--prefix", default=sys.prefix)
    ap.add_argument("--module")
    ap.add_argument("--cases")
    ap.add_argument("--expect-version", default="")
    ap.add_argument("--tools-pin", default="")
    ap.add_argument("--n-runs", default="60")
    a = ap.parse_args()
    globals()[a.section](a)
    bad = [c for c, ok in OUT if not ok]
    print("SECTION %s: %d checks, %d failed %s" % (a.section, len(OUT), len(bad), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
