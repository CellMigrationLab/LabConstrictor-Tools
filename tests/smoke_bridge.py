"""A short end-to-end check that the bridge can be established with one registered app, on any operating system.

Run it with the app's own Python (the one that has labconstrictor_tools installed):

    python smoke_bridge.py --app synthetic --tool scalar_echo --fail-tool explode --slow-tool slow
    python smoke_bridge.py --app CellTracksColab --tool calculate_metrics --param tracks=tracks.csv \
        --bad-param tracks=/nonexistent/none.csv

Every check runs even if an earlier one fails. A table goes to stdout (and to $GITHUB_STEP_SUMMARY when set); the exit
code is 1 if any check failed. It changes nothing except the temporary results folder of the runs it starts.
"""

import argparse
import json
import os
import subprocess
import sys
import time

RESULTS = []


def record(name, ok, note=""):
    RESULTS.append((name, "PASS" if ok else "FAIL", " ".join(str(note).split())[:300]))


def cli(*args, timeout=180):
    return subprocess.run(
        [sys.executable, "-m", "labconstrictor_tools", *args],
        capture_output=True, text=True, timeout=timeout, env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )  # fmt: skip


def first_json(text):
    start = text.find("{")
    if start < 0:
        raise ValueError("no JSON object in the output: %r" % text[:200])
    return json.JSONDecoder().raw_decode(text[start:])[0]


def pid_alive(pid):
    if os.name == "nt":
        out = subprocess.run(["tasklist", "/FI", "PID eq %d" % pid], capture_output=True, text=True).stdout
        return str(pid) in out
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    state = subprocess.run(
        ["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True
    ).stdout.strip()
    return bool(state) and not state.startswith("Z")


def wait_gone(pid, seconds=15):
    end = time.time() + seconds
    while pid_alive(pid) and time.time() < end:
        time.sleep(0.2)
    return not pid_alive(pid)


def check_environment():
    import labconstrictor_tools

    record("environment", True, "python %s on %s, labconstrictor_tools %s" % (
        sys.version.split()[0], sys.platform, getattr(labconstrictor_tools, "__version__", "?")))  # fmt: skip


def check_list(args):
    done = cli("list")
    ok = done.returncode == 0 and args.app in done.stdout and args.tool in done.stdout
    record(
        "list shows the app and its tool",
        ok,
        "rc=%s %s" % (done.returncode, (done.stdout + done.stderr)[:200]),
    )


def check_doctor():
    done = cli("doctor", timeout=300)
    record("doctor finds nothing wrong", done.returncode == 0, "rc=%s %s" % (done.returncode, (done.stdout + done.stderr)[-250:]))  # fmt: skip


def check_run(args):
    done = cli("run", args.app, args.tool, *args.param, "--no-record")
    try:
        report = first_json(done.stdout)
        ok = report.get("status") == "COMPLETE" and done.returncode == 0
        record("run: a tool answers", ok, "rc=%s status=%s %s" % (done.returncode, report.get("status"), (report.get("error") or "")[:150]))  # fmt: skip
    except Exception as error:  # noqa: BLE001 - the report must say what was seen
        record(
            "run: a tool answers",
            False,
            "%s: %s | stderr: %s" % (type(error).__name__, error, done.stderr[-200:]),
        )


def check_failing_run(args):
    if args.fail_tool:
        arguments = [args.fail_tool]
    elif args.bad_param:
        arguments = [args.tool, *args.bad_param]
    else:
        return
    done = cli("run", args.app, *arguments, "--no-record")
    try:
        report = first_json(done.stdout)
        ok = report.get("status") == "FAILED" and bool(report.get("error"))
        record("run: a failing tool is explained", ok, "status=%s error=%s" % (report.get("status"), (report.get("error") or "")[:150]))  # fmt: skip
    except Exception as error:  # noqa: BLE001
        record("run: a failing tool is explained", False, "%s: %s | stderr: %s" % (type(error).__name__, error, done.stderr[-200:]))  # fmt: skip


def check_worker_lifecycle(args):
    from labconstrictor_tools import client

    try:
        worker = client.WorkerProcess(args.app)
        pid = worker.proc.pid
        note = "worker pid %s started" % pid
        if args.fast_tool:
            task = worker.task(args.fast_tool, {}).wait(120)
            note += ", %s -> %s" % (args.fast_tool, task.status)
            ok_task = task.status == "COMPLETE"
        else:
            ok_task = True
        worker.close()
        gone = wait_gone(pid)
        record(
            "worker: starts, answers, closes and leaves no process",
            ok_task and gone,
            note + ", gone=%s" % gone,
        )
    except Exception as error:  # noqa: BLE001
        record(
            "worker: starts, answers, closes and leaves no process",
            False,
            "%s: %s" % (type(error).__name__, error),
        )


def check_kill(args):
    if not args.slow_tool:
        return
    from labconstrictor_tools import client

    try:
        worker = client.WorkerProcess(args.app)
        pid = worker.proc.pid
        task = worker.task(args.slow_tool, {"seconds": 30.0, "steps": 30})
        time.sleep(2)
        worker.kill()
        gone = wait_gone(pid)
        task.wait(30)
        record("worker: a killed worker leaves no process and the task ends", gone and task.status in ("CRASHED", "FAILED", "CANCELLED"), "gone=%s status=%s" % (gone, task.status))  # fmt: skip
        if task.status != "CRASHED":
            record("note: killed worker reports CRASHED", False, "status=%s (informational: the message after a forced cancel differs)" % task.status)  # fmt: skip
    except Exception as error:  # noqa: BLE001
        record("worker: a killed worker leaves no process and the task ends", False, "%s: %s" % (type(error).__name__, error))  # fmt: skip


def check_log():
    done = cli("logs")
    record("logs: the log file is readable", done.returncode == 0 and bool((done.stdout + done.stderr).strip()), "rc=%s" % done.returncode)  # fmt: skip


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", required=True)
    parser.add_argument("--tool", required=True, help="a tool id that works with --param")
    parser.add_argument("--param", action="append", default=[], help="name=value for --tool")
    parser.add_argument("--bad-param", action="append", default=[], help="name=value that makes --tool fail")
    parser.add_argument("--fail-tool", help="a tool that always fails")
    parser.add_argument("--fast-tool", help="a tool without inputs, run in the worker lifecycle check")
    parser.add_argument(
        "--slow-tool", help="a cooperative long task with seconds/steps, killed in the kill check"
    )
    args = parser.parse_args()
    for step in (
        check_environment,
        lambda: check_list(args),
        check_doctor,
        lambda: check_run(args),
        lambda: check_failing_run(args),
        lambda: check_worker_lifecycle(args),
        lambda: check_kill(args),
        check_log,
    ):
        try:
            step()
        except Exception as error:  # noqa: BLE001 - one broken check must not hide the others
            record("check crashed", False, "%s: %s" % (type(error).__name__, error))
    width = max(len(name) for name, _, _ in RESULTS)
    lines = ["%-*s  %s  %s" % (width, name, status, note) for name, status, note in RESULTS]
    print("\n".join(lines))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write("### Bridge smoke test: %s\n\n| check | result | note |\n|---|---|---|\n" % args.app)
            for name, status, note in RESULTS:
                handle.write("| %s | %s | %s |\n" % (name, status, note.replace("|", "/")))
    return (
        1 if any(status == "FAIL" for name, status, _note in RESULTS if not name.startswith("note:")) else 0
    )


if __name__ == "__main__":
    sys.exit(main())
