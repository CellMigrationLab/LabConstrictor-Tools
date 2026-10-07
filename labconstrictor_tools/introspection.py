"""Python signature -> portable JSON schema (protocol 1). Never calls the tool."""

import enum
import inspect
import math
import re
from typing import Annotated, Literal, Union, get_args, get_origin, get_type_hints

from . import types as T
from .decorators import Tool, tools_in
from .structures import AppSchema, ToolSchema

PROTOCOL = 1
SCALARS = {str: "string", int: "integer", float: "float", bool: "boolean"}


class DeclarationError(Exception):
    pass


def _docstring_args(doc):
    """Google-style 'Args:' section -> {name: text}."""
    out, sec, cur, base = {}, False, None, None
    for line in inspect.cleandoc(doc or "").splitlines():
        s = line.strip()
        ind = len(line) - len(line.lstrip())
        if s.lower() in ("args:", "arguments:", "parameters:"):
            sec, base = True, None
            continue
        if not sec or not s:
            continue
        if ind == 0:
            sec = False
            continue
        if base is None:
            base = ind
        m = re.match(r"^(\w+)\s*(\([^)]*\))?\s*:\s*(.*)$", s)
        if ind <= base and m:
            cur = m.group(1)
            out[cur] = m.group(3)
        elif cur:
            out[cur] += " " + s
    return out


def _unwrap(ann):
    """-> (base type, [metadata], optional?)"""
    meta, optional = [], False
    while True:
        o = get_origin(ann)
        if o is Annotated:
            args = get_args(ann)
            ann, meta = args[0], meta + list(args[1:])
            continue
        if o in (Union, getattr(__import__("types"), "UnionType", Union)):
            a = [x for x in get_args(ann) if x is not type(None)]
            if len(a) != len(get_args(ann)) and len(a) == 1:
                ann, optional = a[0], True
                continue
        return ann, meta, optional


def _m(meta, cls):
    for x in meta:
        if isinstance(x, cls):
            return x
    return None


def _check_default(name, d):
    """A default is passed to the tool as it is: it must be valid for the declared type (a host cannot be expected to catch it)."""
    if "default" not in d:
        return
    value, kind = d["default"], d["type"]
    ok = {
        "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
        "float": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v),
        "string": lambda v: isinstance(v, str),
        "boolean": lambda v: isinstance(v, bool),
        "choice": lambda v: any(type(v) is type(c) and v == c for c in d["choices"]),
    }.get(kind)
    if ok and not ok(value):
        raise DeclarationError(
            "parameter %r: default %r is not a valid %s%s"
            % (name, value, kind, " (choices %s)" % d["choices"] if kind == "choice" else "")
        )


def _param(name, p, hint, argdoc):
    base, meta, optional = _unwrap(hint)
    d = {
        "name": name,
        "label": (_m(meta, T.Label).value if _m(meta, T.Label) else name.replace("_", " ").capitalize()),
    }
    has_default = p.default is not inspect.Parameter.empty
    if optional and has_default and p.default is not None:
        raise DeclarationError(
            "parameter %r: Optional[...] with the default %r cannot be expressed (a host can only leave it at its default "
            "or unset). Use `= None` for 'unset', or drop Optional" % (name, p.default)
        )
    d["required"] = not (has_default or optional)
    if has_default and p.default is not None:
        d["default"] = p.default.value if isinstance(p.default, enum.Enum) else p.default
    if base in T.INPUT_TYPES:
        d["type"] = T.INPUT_TYPES[base]
        if _m(meta, T.Axes):
            d["axes"] = _m(meta, T.Axes).value
        if _m(meta, T.PickChannel) and _m(meta, T.PickChannel).value:
            if d["type"] != "image":
                raise DeclarationError("parameter %r: PickChannel applies to an Image input" % name)
            if d.get("axes") not in (None, "YX"):
                raise DeclarationError("parameter %r: PickChannel gives the tool a 2D channel, so Axes must be YX (or absent)" % name)
            d["pick_channel"] = True
    elif get_origin(base) is Literal:
        ch = list(get_args(base))
        d["type"] = "choice"
        d["choices"] = ch
    elif isinstance(base, type) and issubclass(base, enum.Enum):
        d["type"] = "choice"
        d["choices"] = [e.value for e in base]
        if has_default and isinstance(p.default, enum.Enum):
            d["default"] = p.default.value
    elif base is bool:
        d["type"] = "boolean"
    elif base in SCALARS:
        d["type"] = SCALARS[base]
    elif base is __import__("pathlib").Path:
        d["type"] = "file"
    else:
        raise DeclarationError("parameter %r: unsupported annotation %r" % (name, hint))
    _check_default(name, d)
    if d["type"] in ("integer", "float"):
        for key, cls in (("minimum", T.Min), ("maximum", T.Max)):
            if _m(meta, cls):
                d[key] = _m(meta, cls).value
        for k in ("minimum", "maximum"):
            if (
                k in d
                and "default" in d
                and ((k == "minimum" and d["default"] < d[k]) or (k == "maximum" and d["default"] > d[k]))
            ):
                raise DeclarationError(
                    "parameter %r: default %r violates %s %r" % (name, d["default"], k, d[k])
                )
        if _m(meta, T.Unit):
            d["unit"] = _m(meta, T.Unit).value
        if _m(meta, T.PixelSizeOf):
            d["pixel_size_of"] = _m(meta, T.PixelSizeOf).value
    desc = _m(meta, T.Description).value if _m(meta, T.Description) else argdoc.get(name)
    if desc:
        d["description"] = desc
    if _m(meta, T.Group):
        d["group"] = _m(meta, T.Group).value
    if _m(meta, T.Advanced) and _m(meta, T.Advanced).value:
        d["advanced"] = True
    if _m(meta, T.Collapsed) and _m(meta, T.Collapsed).value:
        if "group" not in d:
            raise DeclarationError("parameter %r: Collapsed needs a Group" % name)
        d["group_collapsed"] = True
    wid = _m(meta, T.Widget)
    if wid:
        if wid.value == "slider":
            if d["type"] not in ("integer", "float") or "minimum" not in d or "maximum" not in d:
                raise DeclarationError("parameter %r: Widget('slider') needs a number with both Min and Max" % name)
        elif not (d["type"] == "choice" and 2 <= len(d["choices"]) <= 5):
            raise DeclarationError("parameter %r: Widget('radio') needs a Literal or Enum with 2 to 5 options" % name)
        d["widget"] = wid.value
    if _m(meta, T.ClearAfterRun) and _m(meta, T.ClearAfterRun).value:
        d["clear_after_run"] = True
    if _m(meta, T.PickChannel) and _m(meta, T.PickChannel).value and "pick_channel" not in d:
        raise DeclarationError("parameter %r: PickChannel applies to an Image input" % name)
    src = _m(meta, T.ChoicesFrom)
    if src:
        if d["type"] != "string":
            raise DeclarationError("parameter %r: ChoicesFrom only applies to a string parameter" % name)
        d["choices_from"] = {"tool": src.tool, "depends": src.depends, "field": src.field}
    when = _m(meta, T.EnabledWhen)
    if when:
        d["enabled_when"] = {"param": when.param, **({"equals": when.equals} if when.equals else {})}
    if not d["required"] and "default" not in d:
        # "unset" is a real value (default None / Optional[...]): hosts must be able to leave it unset and then omit it
        d["nullable"] = True
    if d["type"] == "choice" and "default" not in d and d["required"]:
        d["default"] = d["choices"][0]
    return d


def _outputs(ret, tool_id):
    if ret in (inspect.Signature.empty, None, type(None)):
        return []
    base, meta, _ = _unwrap(ret)
    items = [ret] if get_origin(base) is not tuple else list(get_args(base))
    outs = []
    for i, it in enumerate(items):
        b, m, _ = _unwrap(it)
        if b not in T.OUTPUT_TYPES:
            raise DeclarationError("tool %r output %d: unsupported return annotation %r" % (tool_id, i, it))
        o = {"name": _m(m, T.Name).value if _m(m, T.Name) else T.OUTPUT_TYPES[b], "type": T.OUTPUT_TYPES[b]}
        if _m(m, T.Replace) and _m(m, T.Replace).value:
            if o["type"] not in ("image", "labels", "table", "affine", "points", "shapes"):
                raise DeclarationError("tool %r output %d: Replace applies to an image, labels, table, points, shapes or affine output" % (tool_id, i))
            o["replace"] = True
        if _m(m, T.Axes):
            o["axes"] = _m(m, T.Axes).value
        a = _m(m, T.ApplyTo)
        if a:
            o["display"] = {"apply_to": a.source, **({"relative_to": a.target} if a.target else {})}
        outs.append(o)
    seen = {}
    for o in outs:  # unnamed outputs of the same type get a numeric suffix
        seen[o["name"]] = seen.get(o["name"], 0) + 1
        if seen[o["name"]] > 1:
            o["name"] += str(seen[o["name"]])
    names = [o["name"] for o in outs]
    if len(set(names)) != len(names):
        raise DeclarationError("tool %r: duplicate output names %s" % (tool_id, names))
    return outs


def describe_tool(t: Tool) -> ToolSchema:
    fn = t.fn
    sig = inspect.signature(fn)
    try:
        hints = get_type_hints(fn, include_extras=True)
    except Exception as e:
        raise DeclarationError("tool %r: cannot resolve annotations (%s)" % (t.id, e)) from e
    argdoc = _docstring_args(fn.__doc__)
    ins = []
    for name, p in sig.parameters.items():
        if name not in hints:
            raise DeclarationError("tool %r: parameter %r has no type annotation" % (t.id, name))
        ins.append(_param(name, p, hints[name], argdoc))
    names = {i["name"] for i in ins}
    for i in ins:
        if "pixel_size_of" in i and i["pixel_size_of"] not in names:
            raise DeclarationError("tool %r: PixelSizeOf(%r) names no parameter" % (t.id, i["pixel_size_of"]))
    for i in ins:
        rule = i.get("enabled_when")
        if rule and rule["param"] not in names:
            raise DeclarationError(
                "tool %r: EnabledWhen(%r) on %r names no parameter" % (t.id, rule["param"], i["name"])
            )
        if rule and rule["param"] == i["name"]:
            raise DeclarationError("tool %r: parameter %r cannot be enabled by itself" % (t.id, i["name"]))
    outs = _outputs(hints.get("return", inspect.Signature.empty), t.id)
    for o in outs:
        for k in ("apply_to", "relative_to"):
            if k in o.get("display", {}) and o["display"][k] not in names:
                raise DeclarationError(
                    "tool %r: output %r refers to unknown parameter %r" % (t.id, o["name"], o["display"][k])
                )
    desc = (inspect.getdoc(fn) or "").split("\n\n")[0].replace("\n", " ").strip()
    schema: ToolSchema = {"id": t.id, "label": t.label, "inputs": ins, "outputs": outs}
    if desc:
        schema["description"] = desc
    return schema


def describe_tools(
    module_name: str | None = None, application: str | None = None, version: str | None = None
) -> AppSchema:
    """Deterministic JSON-compatible schema for all tools declared by `module_name`."""
    ts = sorted(tools_in(module_name), key=lambda t: t.id)
    out: AppSchema = {"protocol": PROTOCOL, "tools": [describe_tool(t) for t in ts]}
    _check_choice_sources(out["tools"])
    if application:
        out["application"] = application
    if version:
        out["version"] = version
    return out


def _check_choice_sources(tools):
    """ChoicesFrom must point at a tool of the app that can be called with the declared `depends` alone."""
    by_id = {t["id"]: t for t in tools}
    for t in tools:
        for p in t["inputs"]:
            src = p.get("choices_from")
            if not src:
                continue
            where = "tool %r parameter %r: ChoicesFrom(%r)" % (t["id"], p["name"], src["tool"])
            source = by_id.get(src["tool"])
            if source is None:
                raise DeclarationError("%s names no tool of this app" % where)
            if source["id"] == t["id"]:
                raise DeclarationError("%s cannot be the tool itself" % where)
            if not any(o["type"] == "values" for o in source["outputs"]):
                raise DeclarationError("%s: the source tool must return Scalars" % where)
            mine = {i["name"] for i in t["inputs"]}
            theirs = {i["name"]: i for i in source["inputs"]}
            for name in src["depends"]:
                if name not in mine or name not in theirs:
                    raise DeclarationError("%s: depends %r must be a parameter of both tools" % (where, name))
            for name, i in theirs.items():
                if name not in src["depends"] and i["required"]:
                    raise DeclarationError("%s: the source tool's required parameter %r is not in depends" % (where, name))
