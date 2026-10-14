"""Kernel-side helpers of the notebook family: exec'd into the kernel (as module `lcnb`) by the worker, never imported by the app.

* `install_audit` logs network, subprocess and write-opens under watched folders to a JSON-lines file (an observer: it never blocks or changes anything).
* `find` / `set_value` / `click` / `wait_until` drive widgets by simulated clicks; `check` / `note` / `human` print the result lines the worker turns into rows."""

import json
import os
import re
import sys
import time
import traceback
from typing import Any, Callable

INPUTS: dict[str, Any] = {}
LINES_PATH = ""  # set by the worker: result lines also go to this JSON-lines file, because a notebook's clear_output() wipes the printed copy
LAST_OUTPUT: dict[str, Any] = {}
_LOG_FAILURES = 0


class WidgetNotFound(LookupError):
    """No widget matches the description (the message lists the candidates, so that a wrong script is easy to fix)."""


class CallbackFailed(RuntimeError):
    """A click handler raised: ipywidgets swallows the exception and prints a traceback, which `click` turns back into an error."""


def install_audit(log_path: str, watch: list[str], ignore: list[str]) -> None:
    """Record DNS lookups, connections, subprocesses and writes under `watch` (outside `ignore`) of this process and its forks."""

    def log(kind: str, **fields: Any) -> None:
        global _LOG_FAILURES
        try:
            with open(log_path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps({"t": round(time.time(), 2), "kind": kind, **fields}) + "\n")
        except OSError:
            _LOG_FAILURES += 1

    def writing(args: tuple[Any, ...]) -> bool:
        mode, flags = str(args[1] or ""), args[2] if len(args) > 2 and isinstance(args[2], int) else 0
        return any(c in mode for c in "wax+") or bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT))

    def hook(event: str, args: tuple[Any, ...]) -> None:
        if event == "socket.getaddrinfo":
            log("dns", host=str(args[0]), port=str(args[1]))
        elif event == "socket.connect":
            log("connect", addr=str(args[1]))
        elif event == "subprocess.Popen":
            log("popen", argv=str(args[1])[:300])
        elif event in ("os.system", "os.posix_spawn", "os.exec"):
            log(event, argv=str(args[0])[:300] if event == "os.system" else str(args[1:2])[:300])
        elif event == "open" and isinstance(args[0], str) and args[0].startswith(tuple(watch)) and not args[0].startswith(tuple(ignore)) and writing(args):
            log("write", path=args[0])

    sys.addaudithook(hook)
    try:
        import requests

        original = requests.sessions.Session.request

        def logged(self: Any, method: str, url: str, *a: Any, **kw: Any) -> Any:
            try:
                response = original(self, method, url, *a, **kw)
            except Exception as problem:  # the observer records and re-raises: the notebook sees the same failure
                log("http", method=method, url=str(url)[:200], error="%s: %s" % (type(problem).__name__, str(problem)[:150]))
                raise
            log("http", method=method, url=str(url)[:200], status=response.status_code)
            return response

        requests.sessions.Session.request = logged
    except ImportError:
        log("note", text="requests is not installed in this environment: HTTP calls are only seen as socket events")


def all_widgets() -> list[Any]:
    """Every live ipywidgets widget of the kernel."""
    import warnings

    from ipywidgets.widgets import widget

    registry = getattr(widget, "_instances", None)  # ipywidgets 8: module-level registry of live widgets
    if registry is None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            registry = getattr(widget.Widget, "widgets", None)  # ipywidgets 7: class attribute
    if registry is None:
        raise RuntimeError("this ipywidgets version has neither widget._instances nor Widget.widgets: the click helpers must be adapted")
    return list(registry.values())


def _describe(w: Any) -> str:
    text = getattr(w, "description", "") or getattr(w, "placeholder", "") or ""
    return "%s(%r)" % (type(w).__name__, str(text)[:40])


def find(kind: str | None = None, description: str | None = None, var: str | None = None, contains: str | None = None, index: int = 0) -> Any:
    """A widget by notebook variable name (`var`), or by class name (`kind`) and the description/placeholder text it contains (`description`), or by
    text of an HTML/Label value (`contains`); `index` picks among several matches. Raises WidgetNotFound listing what exists."""
    if var is not None:
        space = get_ipython().user_ns  # noqa: F821 - defined in the kernel
        if var not in space:
            raise WidgetNotFound("variable %r is not defined in the notebook; widget variables: %s" % (var, sorted(k for k, v in space.items() if hasattr(v, "model_id"))))
        return space[var]
    hits = []
    for w in all_widgets():
        if kind is not None and type(w).__name__ != kind:
            continue
        label = str(getattr(w, "description", "") or getattr(w, "placeholder", "") or "")
        if description is not None and description.lower() not in label.lower():
            continue
        if contains is not None and contains.lower() not in str(getattr(w, "value", "")).lower():
            continue
        hits.append(w)
    if len(hits) <= index:
        raise WidgetNotFound(
            "no widget with kind=%r description=%r contains=%r (match %d); live widgets: %s"
            % (kind, description, contains, index, ", ".join(sorted({_describe(w) for w in all_widgets()})[:40]))
        )
    return hits[index]


def set_value(widget: Any, value: Any) -> None:
    """Set a widget value the way a user would (an observer fires), refusing a disabled widget."""
    if getattr(widget, "disabled", False):
        raise RuntimeError("%s is disabled: a user could not set it" % _describe(widget))
    widget.value = value


def click(button: Any) -> dict[str, Any]:
    """Click a button (refusing a disabled one) and return what its handler printed and displayed: {'stdout', 'stderr', 'outputs'}. A handler that raised
    (ipywidgets prints the traceback instead of raising) becomes CallbackFailed."""
    from IPython.utils.capture import capture_output

    if getattr(button, "disabled", False):
        raise RuntimeError("%s is disabled: a user could not click it" % _describe(button))
    with capture_output() as captured:
        button.click()
    result = {"stdout": captured.stdout, "stderr": captured.stderr, "outputs": [o.data for o in captured.outputs]}
    LAST_OUTPUT.clear()
    LAST_OUTPUT.update(result)
    if "Traceback (most recent call last)" in captured.stderr + captured.stdout or any("Traceback (most recent call last)" in str(o) for o in result["outputs"]):
        raise CallbackFailed(("callback of %s raised: " % _describe(button)) + (captured.stderr + captured.stdout)[-600:])
    return result


def wait_until(predicate: Callable[[], bool], timeout: float, what: str, poll: float = 0.2) -> None:
    """Poll until `predicate()` is true; TimeoutError naming `what` otherwise."""
    end = time.time() + timeout
    while time.time() < end:
        if predicate():
            return
        time.sleep(poll)
    raise TimeoutError("timed out after %.0f s waiting for %s" % (timeout, what))


def _line(kind: str, ident: str, verdict: str, detail: str) -> None:
    clean = re.sub(r"\x1b\[[0-9;]*[A-Za-z]|\r", "", detail).replace("\n", " | ").strip()[:400]
    print("LCNB %s %s %s %s" % (kind, ident, verdict, clean))
    if LINES_PATH:
        with open(LINES_PATH, "a", encoding="utf-8") as handle:
            handle.write(json.dumps({"kind": kind, "ident": ident, "verdict": verdict, "detail": clean}) + "\n")


def check(ident: str, ok: bool, detail: str = "") -> None:
    _line("CHECK", ident, "PASS" if ok else "FAIL", detail)


def note(ident: str, detail: str) -> None:
    _line("NOTE", ident, "NOTE", detail)


def human(ident: str, detail: str) -> None:
    _line("HUMAN", ident, "HUMAN", detail)


def guarded(ident: str, action: Callable[[], Any]) -> Any:
    """Run one scripted action; any exception becomes a FAIL line with its type and message and the script goes on (None is returned)."""
    try:
        return action()
    except Exception as problem:  # a failed action is a result, never a stop
        _line("CHECK", ident, "FAIL", "%s: %s | %s" % (type(problem).__name__, problem, traceback.format_exc().splitlines()[-3:-1]))
        return None
