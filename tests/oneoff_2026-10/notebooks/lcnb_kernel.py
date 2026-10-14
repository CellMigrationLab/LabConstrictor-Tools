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
        except OSError as problem:
            _LOG_FAILURES += 1
            if _LOG_FAILURES == 1:
                print("LCNB audit log not writable (%s): side effects of this run may be incomplete" % problem, file=sys.stderr)

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
            log("http", method=method, url=str(url)[:200], status=response.status_code, size=str(response.headers.get("Content-Length", "unknown")))
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


def _hidden(w: Any) -> bool:
    """A widget a user cannot see: layout display none or visibility hidden (a click would skip hit-testing, so refuse it)."""
    layout = getattr(w, "layout", None)
    return getattr(layout, "display", None) == "none" or getattr(layout, "visibility", None) == "hidden"


def find(kind: str | None = None, description: str | None = None, var: str | None = None, contains: str | None = None, index: int = 0, exact: bool = False) -> Any:
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
        if description is not None and (description.lower() != label.lower().strip() if exact else description.lower() not in label.lower()):
            continue
        if contains is not None and contains.lower() not in str(getattr(w, "value", "")).lower():
            continue
        hits.append(w)
    if not hits or index >= len(hits) or index < -len(hits):
        raise WidgetNotFound(
            "no widget with kind=%r description=%r contains=%r (match %d); live widgets: %s"
            % (kind, description, contains, index, ", ".join(sorted({_describe(w) for w in all_widgets()})[:40]))
        )
    return hits[index]


def set_value(widget: Any, value: Any) -> None:
    """Set a widget value the way a user would (an observer fires), refusing a disabled widget."""
    if getattr(widget, "disabled", False):
        raise RuntimeError("%s is disabled: a user could not set it" % _describe(widget))
    if _hidden(widget):
        raise RuntimeError("%s is hidden by its own layout: a user could not set it" % _describe(widget))
    widget.value = value


def click(button: Any) -> dict[str, Any]:
    """Click a button (refusing a disabled one) and return what its handler printed and displayed: {'stdout', 'stderr', 'outputs'}. A handler that raised
    (ipywidgets prints the traceback instead of raising) becomes CallbackFailed."""
    from IPython.utils.capture import capture_output

    if getattr(button, "disabled", False):
        raise RuntimeError("%s is disabled: a user could not click it" % _describe(button))
    if _hidden(button):
        raise RuntimeError("%s is hidden by its own layout: a user could not click it" % _describe(button))
    shell = get_ipython()  # noqa: F821 - defined in the kernel
    original, raised = shell.showtraceback, []

    def record(*args: Any, **kwargs: Any) -> None:
        exc_tuple = args[0] if args and isinstance(args[0], tuple) else kwargs.get("exc_tuple")  # Output.capture passes the exception it caught
        raised.append("".join(traceback.format_exception(*exc_tuple)) if exc_tuple else traceback.format_exc())

    shell.showtraceback = record  # ipywidgets reports a handler's exception through showtraceback() instead of raising it
    try:
        with capture_output() as captured:
            button.click()
    finally:
        shell.showtraceback = original
    result = {"stdout": captured.stdout, "stderr": captured.stderr, "outputs": [o.data for o in captured.outputs]}
    LAST_OUTPUT.clear()
    LAST_OUTPUT.update(result)
    if raised:
        raise CallbackFailed("callback of %s raised: %s" % (_describe(button), " | ".join(raised[0].strip().splitlines()[-3:])))
    printed = captured.stderr + captured.stdout
    if "Traceback (most recent call last)" in printed:  # a handler that catches its own error and prints it (traceback.print_exc) has still failed
        raise CallbackFailed("callback of %s printed a traceback: %s" % (_describe(button), " | ".join(printed.strip().splitlines()[-3:])))
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


NATIVE_PICKER = re.compile(r"^(find (file|folder)|select from file|load structure from file|select structure from file|upload .*)$", re.I)
NEVER_CLICK = re.compile(r"update source code", re.I)
_CLICKED: set[str] = set()
_SEEN: set[str] = set()


def auto_drive(stage: str, skip: tuple[str, ...] = ()) -> int:
    """Click, once and in creation order, every enabled and visible Button that appeared since the last call (a user pressing the buttons of the cell that just ran).
    Native pickers are HUMAN lines, the source-update button (pip install into the app) is never clicked; a handler that raises is a FAIL line. Returns the number clicked."""
    clicked = 0
    for w in all_widgets():
        if type(w).__name__ != "Button" or w.model_id in _SEEN:
            continue
        _SEEN.add(w.model_id)
        label = (w.description or w.tooltip or "button").strip()
        slug = re.sub(r"[^A-Za-z0-9]+", "_", label).strip("_")[:30] or "button"
        ident = "click_auto_%s_%s" % (stage, slug)
        if NATIVE_PICKER.match(label):
            human(ident, "button %r opens a native or upload dialog: not clicked, the path or file is set directly in the field" % label)
        elif NEVER_CLICK.search(label) or any(label.lower().startswith(x.lower()) for x in skip):
            human(ident, "button %r is not clicked on purpose (it changes the installed app or is listed as skipped by the script)" % label)
        elif w.disabled or _hidden(w):
            note(ident, "button %r is %s: a user could not press it at this point" % (label, "disabled" if w.disabled else "hidden"))
        else:
            try:
                result = click(w)
                _CLICKED.add(w.model_id)
                clicked += 1
                check(ident, True, "clicked %r: %s" % (label, (result["stdout"] or result["stderr"]).strip()[-100:]))
            except Exception as problem:  # a failing handler is a result, the drive goes on
                check(ident, False, "%r: %s: %s" % (label, type(problem).__name__, str(problem)[-250:]))
    return clicked
