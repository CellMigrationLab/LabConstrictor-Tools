"""Family `multi` of the audit (session S2): several installed apps registered in ONE private LC_HOME, the way a user who installs a second app next to the first
looks. CLI/registry level; the per-host chooser checks are done by the host UI audit drivers with LC_APPS.

    python run_multi_family.py --apps NAME:PREFIX:SRC [NAME:PREFIX:SRC ...] --results DIR --private-home EMPTY_DIR

Rows (family multi, host cli, app 'all'): multi_lists_<app> (list shows every tool of the app's schema), multi_hosts_<app> (registry hosts equal expected_hosts.json),
multi_doctor_clean, multi_run_<app> (the first COMPLETE case of the app runs while the others are registered), multi_unregister_<A>_keeps_<B> (removing one app leaves the
other listed and runnable)."""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "release_sandbox"))

import expected_hosts as table  # noqa: E402
from matrix import Matrix  # noqa: E402
from run_sandbox_family import run_step  # noqa: E402


def lc(py: str, env: dict[str, str], *args: str, timeout: int = 900) -> tuple[int, str]:
    return run_step([py, "-m", "labconstrictor_tools", *args], env, timeout)


def first_complete_case(src: Path) -> dict[str, Any] | None:
    cases = json.loads((src / "lc_tests" / "cases.json").read_text(encoding="utf-8"))
    cases = cases if isinstance(cases, list) else cases.get("cases", [])
    return next(
        (
            c
            for c in cases
            if c.get("expect", {}).get("status", "COMPLETE") == "COMPLETE"
            and not c.get("skip")
            and c.get("cancel_after_s") is None
        ),
        None,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apps", nargs="+", required=True, help="NAME:PREFIX:SRC (SRC = checkout with lc_tests)"
    )
    parser.add_argument("--results", required=True)
    parser.add_argument("--private-home", required=True)
    args = parser.parse_args()
    apps = [a.split(":", 2) for a in args.apps]
    names = [a[0] for a in apps]
    home = Path(args.private_home)
    matrix = Matrix(Path(args.results) / "multi", "multi", "cli", "all")
    if home.exists():
        matrix.add("multi_private_home", "FAIL", "%s already exists; refusing to reuse it" % home)
        matrix.finish()
        return 0
    env = dict(os.environ, LC_HOME=str(home), PYTHONIOENCODING="utf-8")
    data = table.load()
    py0 = str(Path(apps[0][1]) / "bin" / "python")
    for name, prefix, src in apps:
        py = str(Path(prefix) / "bin" / "python")
        module = next((p.name for p in (Path(src) / "src").glob("*_lc_tools")), "")
        manifests = sorted(Path(prefix).glob("*/labconstrictor-app.yaml"))
        command = [
            "register",
            "--name",
            name,
            "--prefix",
            prefix,
            "--module",
            module,
            "--version",
            "0",
            "--display-name",
            name,
        ] + (["--app-manifest", str(manifests[0])] if manifests else [])
        code, out = lc(py, env, *command, timeout=300)
        matrix.add(
            "multi_register_%s" % name, "PASS" if code == 0 else "FAIL", "exit %d %s" % (code, out[-200:])
        )
    code, listing = lc(py0, env, "list")
    for name, prefix, src in apps:
        schema = (
            json.loads((home / "apps" / (name + ".schema.json")).read_text(encoding="utf-8"))
            if (home / "apps" / (name + ".schema.json")).exists()
            else {"tools": []}
        )
        tools = [t["id"] for t in schema.get("tools", [])]
        missing = [t for t in tools if t not in listing]
        matrix.add(
            "multi_lists_%s" % name,
            "PASS" if tools and name in listing and not missing else "FAIL",
            "tools=%d missing=%s" % (len(tools), missing),
        )
        entry = json.loads((home / "apps" / (name + ".json")).read_text(encoding="utf-8"))
        wanted = data["apps"].get(name, {}).get("hosts")
        matrix.add(
            "multi_hosts_%s" % name,
            "PASS" if wanted and entry.get("hosts") == wanted else "FAIL",
            "registry %s expected %s" % (entry.get("hosts"), wanted),
        )
    code, out = lc(py0, env, "doctor", "--json")
    try:
        findings = json.loads(out)
        matrix.add(
            "multi_doctor_clean",
            "PASS" if code == 0 and findings and all(f.get("level") == "ok" for f in findings) else "FAIL",
            "rc=%d findings=%d" % (code, len(findings)),
        )
    except json.JSONDecodeError:
        matrix.add("multi_doctor_clean", "FAIL", "doctor --json not JSON: " + out[-200:])
    run_ok: dict[str, bool] = {}
    for name, prefix, src in apps:
        case = first_complete_case(Path(src))
        py = str(Path(prefix) / "bin" / "python")
        if case is None:
            matrix.add("multi_run_%s" % name, "NOT_RUN", "no COMPLETE case in lc_tests/cases.json")
            continue
        started = time.time()
        sys.path.insert(0, str(HERE.parent / "release_sandbox"))
        import sandbox_checks as sc  # noqa: E402

        code, out = lc(py, env, "run", name, case["tool"], *sc.cli_params(case, Path(src) / "lc_tests"))
        run_ok[name] = code == 0 and '"status": "COMPLETE"' in out
        matrix.add(
            "multi_run_%s" % name,
            "PASS" if run_ok[name] else "FAIL",
            "tool %s exit %d: %s" % (case["tool"], code, out[-200:]),
            seconds=time.time() - started,
        )
    if len(apps) >= 2:
        for victim, keeper in ((names[0], names[1]), (names[1], names[0])):
            code, out = lc(py0, env, "unregister", "--name", victim)
            code2, listing2 = lc(py0, env, "list")
            matrix.add(
                "multi_unregister_%s_keeps_%s" % (victim, keeper),
                "PASS" if code == 0 and keeper in listing2 and (victim not in listing2) else "FAIL",
                "unregister exit %d; list now: %s" % (code, " ".join(listing2.split())[:200]),
            )
            vprefix, vsrc = next((a[1], a[2]) for a in apps if a[0] == victim)
            manifests = sorted(Path(vprefix).glob("*/labconstrictor-app.yaml"))
            vmodule = next((p.name for p in (Path(vsrc) / "src").glob("*_lc_tools")), "")
            lc(
                str(Path(vprefix) / "bin" / "python"),
                env,
                "register",
                "--name",
                victim,
                "--prefix",
                vprefix,
                "--module",
                vmodule,
                "--version",
                "0",
                "--display-name",
                victim,
                *(["--app-manifest", str(manifests[0])] if manifests else []),
            )
    print("multi family: %s" % matrix.finish())
    return 0


if __name__ == "__main__":
    sys.exit(main())
