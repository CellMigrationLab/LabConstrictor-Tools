"""@tool registration. Registration only records the function; nothing scientific runs or is imported."""

from collections.abc import Callable
from typing import Any, cast

_REGISTRY: dict[str, "Tool"] = {}


class Tool:
    """One registered function; `module` is kept so a module's tools can be dropped together (`forget_module`)."""

    def __init__(self, fn: Callable[..., Any], id: str, label: str) -> None:
        self.fn, self.id, self.label, self.module = fn, id, label, fn.__module__


def tool(label: str | Callable[..., Any] | None = None, *, id: str | None = None) -> Any:
    """@tool("Calculate Track Metrics")   or   @tool()   (label defaults to the function name)."""
    if callable(label) and id is None:  # bare @tool
        fn, label = label, None
        return _register(fn, None, None)

    def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
        # `label` is text here: a callable label took the bare-@tool branch above
        return _register(fn, cast("str | None", label), id)

    return deco


def _register(fn: Callable[..., Any], label: str | None, id: str | None) -> Callable[..., Any]:
    tid = id or fn.__name__
    if (
        tid in _REGISTRY
        and _REGISTRY[tid].fn is not fn
        and (_REGISTRY[tid].module, _REGISTRY[tid].fn.__qualname__) != (fn.__module__, fn.__qualname__)
    ):
        raise ValueError("duplicate tool id %r (already declared in %s)" % (tid, _REGISTRY[tid].module))
    _REGISTRY[tid] = Tool(fn, tid, label or fn.__name__.replace("_", " ").capitalize())
    fn.__lc_tool__ = _REGISTRY[tid]  # type: ignore[attr-defined]  # functions accept new attributes; notebook.ToolForm reads it back
    return fn


def tools_in(module_name: str | None = None) -> list[Tool]:
    return [t for t in _REGISTRY.values() if module_name is None or t.module == module_name]


def clear() -> None:
    _REGISTRY.clear()


def forget_module(module_name: str) -> None:
    """Drop the registrations of one module (temporary modules created while checking notebook cells)."""
    for tid in [t.id for t in tools_in(module_name)]:
        del _REGISTRY[tid]
