"""Runs inside the app's interpreter: reads [{module, names}] from stdin, imports each and checks the names, prints one JSON line per entry (flushed, so a hang
loses only the entry it hangs on). Standard library only."""

import importlib
import json
import sys
import traceback


def resolve(module: str, names: list[str]) -> str | None:
    """None when `module` imports and every name is an attribute or a submodule, else the error text."""
    try:
        loaded = importlib.import_module(module)
        missing = []
        for name in names:
            if hasattr(loaded, name):
                continue
            try:
                importlib.import_module(module + "." + name)
            except ImportError:
                missing.append(name)
        return ("cannot import name(s) %s from %s" % (", ".join(missing), module)) if missing else None
    except Exception as problem:  # any failure of an import is the result, not a crash of the probe
        return "%s: %s" % (
            type(problem).__name__,
            str(problem)[:300] or traceback.format_exc().splitlines()[-1],
        )


def main() -> int:
    for entry in json.loads(sys.stdin.read()):
        error = resolve(entry["module"], entry["names"])
        print(
            json.dumps(
                {
                    "module": entry["module"],
                    "names": entry["names"],
                    "status": "ok" if error is None else "fail",
                    "error": error or "",
                }
            ),
            flush=True,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
