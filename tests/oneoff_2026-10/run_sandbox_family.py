"""Family `sandbox` of the one-off run: the existing release-sandbox checks (tests/release_sandbox) against ONE installed app, every step guarded, every CHECK line a
matrix row, nothing stops at a failure.

    python run_sandbox_family.py --app NAME --prefix PREFIX --src APP_SRC --tag TAG --results DIR --lc-home LC_HOME [--sections basic,hosts,cases,retention]

PREFIX is the install prefix (its bin/python runs the checks), APP_SRC a checkout of the app at TAG (for lc_tests/cases.json), LC_HOME the scratch registry the
installer registered the app in."""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
RS = HERE.parent / "release_sandbox"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(RS))

import verdict  # noqa: E402
from matrix import Matrix  # noqa: E402

STEP_TIMEOUT_S = int(os.environ.get("LC_STEP_TIMEOUT", "1800"))


def run_step(command: list[str], env: dict[str, str], timeout: int, cwd: Path | None = None) -> tuple[int, str]:
    """Run one step; a crash or a timeout is returned as text, never raised."""
    try:
        done = subprocess.run(command, env=env, capture_output=True, text=True, timeout=timeout, errors="replace", cwd=cwd)
        return done.returncode, done.stdout + (("\n[stderr]\n" + done.stderr[-2000:]) if done.stderr.strip() else "")
    except subprocess.TimeoutExpired as late:
        partial = (late.stdout or b"").decode("utf-8", "replace") if isinstance(late.stdout, bytes) else (late.stdout or "")
        return 124, partial + "\n[timeout after %d s]" % timeout
    except OSError as problem:
        return 127, "[could not start: %s]" % problem


def expected_hosts(app: str) -> str:
    """The comma list of hosts the matrix expects for this app (expected_hosts.json), or '' when the app has no row."""
    import expected_hosts as table

    data: dict[str, Any] = table.load()
    row = data["apps"].get(app)
    return ",".join(row["hosts"]) if row else ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--src", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--results", required=True)
    parser.add_argument("--lc-home", required=True)
    parser.add_argument("--sections", default="basic,hosts,cases,retention")
    parser.add_argument("--tools-pin", default="v0.3.0-alpha.1")
    parser.add_argument("--install-log", default="", help="the installer's log, ending in a line exit=<code> (written by the orchestrator)")
    args = parser.parse_args()

    sections = [s for s in args.sections.split(",") if s]
    py = str(Path(args.prefix) / "bin" / "python")
    cases = Path(args.src) / "lc_tests" / "cases.json"
    module = next((p.name for p in (Path(args.src) / "src").glob("*_lc_tools")), "")
    has_tools = bool(module)
    spec = json.loads((RS / "required_checks.json").read_text(encoding="utf-8"))
    wanted = verdict.required_ids({"sections": {k: v for k, v in spec["sections"].items() if k in sections}}, has_tools, "Linux")
    matrix = Matrix(Path(args.results) / args.app, "sandbox", "cli", args.app, expected=wanted)
    env = dict(os.environ, LC_HOME=args.lc_home, PYTHONIOENCODING="utf-8")
    hosts = expected_hosts(args.app)
    if args.install_log:
        log = Path(args.install_log).read_text(encoding="utf-8", errors="replace") if Path(args.install_log).is_file() else ""
        ended = [line for line in log.splitlines() if line.startswith("exit=")]
        matrix.add("1_installer_succeeds", "PASS" if ended and ended[-1] == "exit=0" else "FAIL", ended[-1] if ended else "no exit line in the installer log")
    maker = Path(args.src) / "lc_tests" / "make_fixtures.py"
    if maker.is_file():  # the workflow does the same: apps such as NucleiSky and Guess the Condition generate their fixtures
        (Path(args.src) / "lc_tests" / "fixtures").mkdir(exist_ok=True)
        code, out = run_step([py, "make_fixtures.py", "fixtures"], env | {"PWD": str(maker.parent)}, 600, cwd=maker.parent)
        matrix.add("sandbox_make_fixtures", "PASS" if code == 0 else "FAIL", "exit %d: %s" % (code, out[-300:]))

    steps: dict[str, list[str]] = {
        "basic": [py, str(RS / "sandbox_checks.py"), "basic", "--app", args.app, "--prefix", args.prefix, "--expect-version", args.tag, "--tools-pin", args.tools_pin]
        + ([] if has_tools else ["--no-tools"]),
        "hosts": [py, str(RS / "hosts_check.py"), "entry", "--app", args.app] + (["--expect-hosts", hosts] if has_tools else ["--no-tools"]),
        "cases": [py, str(RS / "sandbox_checks.py"), "cases", "--app", args.app, "--module", module, "--cases", str(cases)],
        "retention": [py, str(RS / "sandbox_checks.py"), "retention", "--app", args.app, "--cases", str(cases), "--n-runs", "60"],
    }
    for name in sections:
        if name not in steps:
            matrix.add("sandbox_step_%s" % name, "FAIL", "unknown section %r" % name)
            continue
        if name in ("cases", "retention") and not has_tools:
            continue
        started = time.time()
        code, out = run_step(steps[name], env, STEP_TIMEOUT_S)
        added = matrix.add_output(out)
        if added == 0 or code in (124, 127):
            matrix.add("sandbox_step_%s" % name, "FAIL", "step %s produced %d CHECK lines, exit %d: %s" % (name, added, code, out[-300:]), seconds=time.time() - started)
        (Path(args.results) / args.app / ("log_sandbox_%s.txt" % name)).write_text(out, encoding="utf-8")
    counts = matrix.finish()
    print("sandbox family for %s: %s" % (args.app, counts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
