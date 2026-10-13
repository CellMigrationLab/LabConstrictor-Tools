"""Cross-version read test: this checkout (NEW) against another labconstrictor-tools install (OLD, the last git tag).

    python tests/compat_matrix.py --old-python /path/to/old/venv/python

Both directions, each one a real subprocess of the real code (no mocks):
  1. old-schema / new-host : the schema OLD's `describe` writes, and the frozen 0.1, 0.2 and 0.3 fixtures, are read by NEW's
                             registry loader and judged by NEW's `compat.check_schema` (a 0.1 schema must be refused by a
                             host that needs 0.2, and still load for one that needs nothing).
  2. new-schema / old-host : the schema NEW's `describe` writes and the frozen 0.2 and 0.3 fixtures are read by OLD's registry loader:
                             extra fields (`tools_version`, `features`) must not break a host of protocol 1.
  3. worker                : OLD's worker accepts a request that carries reserved inputs (new host / old worker) and NEW's worker
                             accepts a request without any (old host / new worker): both end in COMPLETION.
Prints one line per check and exits 1 on the first failure. OLD may be the same interpreter as NEW (the local self-test).
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures" / "schemas"
MODULE = "labconstrictor_tools.examples.synthetic"
READ_OLD = (
    "import json, sys\n"
    "from labconstrictor_tools import registry\n"
    "schema = registry._validated_schema(json.load(open(sys.argv[1], encoding='utf-8')))\n"
    "print(json.dumps([t['id'] for t in schema['tools']]))\n"
)  # what a host of protocol 1 does with a cached schema


def clean_env(**extra):
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "PYTHONSAFEPATH")}
    env.update(LC_HOME=tempfile.mkdtemp(prefix="lc_compat_"), PYTHONUTF8="1", **extra)
    return env


def run_python(python, args, cwd, new):
    """Run `python args` from a neutral folder; NEW also sees this checkout, OLD only its own site-packages."""
    env = clean_env(**({"PYTHONPATH": str(ROOT)} if new else {}))
    return subprocess.run(
        [str(python), *args], capture_output=True, text=True, encoding="utf-8", env=env, cwd=cwd, timeout=120
    )  # noqa: S603


def ids(schema):
    return [t["id"] for t in schema["tools"]]


def step(name, ok, detail=""):
    print("%s  %s%s" % ("ok  " if ok else "FAIL", name, ("  -- " + detail) if detail else ""))
    if not ok:
        sys.exit(1)


def worker_completes(python, new, inputs):
    """EXECUTE scalar_echo with `inputs` on that interpreter's worker -> the terminal response type."""
    proc = subprocess.Popen(  # noqa: S603
        [str(python), "-m", "labconstrictor_tools", "serve", "--module", MODULE],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8",
        env=clean_env(**({"PYTHONPATH": str(ROOT)} if new else {})), cwd=tempfile.mkdtemp(),
    )  # fmt: skip
    request = {"task": "t", "requestType": "EXECUTE", "script": "lc:scalar_echo", "inputs": inputs}
    assert proc.stdin and proc.stdout
    proc.stdin.write(json.dumps(request) + "\n")
    proc.stdin.flush()
    last = None
    for line in proc.stdout:
        message = json.loads(line)
        if message.get("task") == "t" and message["responseType"] in ("COMPLETION", "FAILURE", "CANCELATION"):
            last = message
            break
    proc.stdin.close()
    try:
        proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        proc.kill()
    return last


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--old-python", required=True)
    old = parser.parse_args().old_python
    sys.path.insert(0, str(ROOT))
    from labconstrictor_tools import compat, registry

    work = Path(tempfile.mkdtemp(prefix="lc_compat_work_"))
    fixture = {
        n: json.loads((FIXTURES / ("tools_%s.schema.json" % n)).read_text("utf-8"))
        for n in ("0.1", "0.2", "0.3")
    }

    # 1. old schema, new host
    result = run_python(old, ["-m", "labconstrictor_tools", "describe", "--module", MODULE], work, new=False)
    step("old describe runs", result.returncode == 0, result.stderr[-300:])
    old_schema = json.loads(result.stdout)
    loaded = registry._validated_schema(old_schema)
    step(
        "new host loads the schema the old Tools wrote (tools_version=%r)" % old_schema.get("tools_version"),
        bool(ids(loaded)),
    )
    step(
        "new host loads the frozen 0.1 fixture", ids(registry._validated_schema(fixture["0.1"])) == ["scale"]
    )
    refused = compat.check_schema(fixture["0.1"], "0.2.0rc1", ["reserved_inputs_v1"])
    step("host needing 0.2 refuses the 0.1 fixture: " + refused.reason, refused.status == compat.REFUSE)
    tolerant = compat.check_schema(fixture["0.1"])
    step(
        "host needing nothing only warns about the 0.1 fixture: " + tolerant.reason,
        tolerant.status == compat.WARN,
    )
    step(
        "new host accepts the 0.2 fixture",
        compat.check_schema(fixture["0.2"], "0.2.0rc1", ["reserved_inputs_v1"]).status == compat.OK,
    )

    step(
        "new host accepts the 0.3 fixture and its features (0.3.0a1, shm_order_v1)",
        compat.check_schema(
            fixture["0.3"], "0.3.0a1", ["reserved_inputs_v1", "retention_prune", "shm_order_v1"]
        ).status
        == compat.OK,
    )
    step(
        "host needing 0.3.0a1 refuses the frozen 0.2 fixture (0.2.0rc1)",
        compat.check_schema(fixture["0.2"], "0.3.0a1").status == compat.REFUSE,
    )

    # 2. new schema, old host
    new_text = run_python(
        sys.executable, ["-m", "labconstrictor_tools", "describe", "--module", MODULE], work, new=True
    )
    step("new describe runs", new_text.returncode == 0, new_text.stderr[-300:])
    new_path = work / "new.schema.json"
    new_path.write_text(new_text.stdout, encoding="utf-8")
    for label, path in (
        ("the schema the new Tools writes", new_path),
        ("the frozen 0.2 fixture", FIXTURES / "tools_0.2.schema.json"),
        ("the frozen 0.3 fixture", FIXTURES / "tools_0.3.schema.json"),
    ):
        read = run_python(old, ["-c", READ_OLD, str(path)], work, new=False)
        step(
            "old host reads " + label,
            read.returncode == 0 and bool(json.loads(read.stdout)),
            read.stderr[-300:],
        )

    # 3. workers
    reserved = {"a": 1, "b": 2, "_calibration": {"pixel_size": {}}, "_axes": {"image": "YX"}, "_next": 1}
    done = worker_completes(old, False, reserved)
    step(
        "old worker accepts a request with reserved inputs",
        bool(done) and done["responseType"] == "COMPLETION",
        str(done)[:300],
    )
    done = worker_completes(sys.executable, True, {"a": 1, "b": 2})
    step(
        "new worker accepts a request without reserved inputs",
        bool(done) and done["responseType"] == "COMPLETION",
        str(done)[:300],
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
